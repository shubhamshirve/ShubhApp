"""
Cron Job Services for Auto Invoice Generation and Reminders
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

class CronJobService:
    """Service for scheduled tasks like invoice generation and reminders"""
    
    def __init__(self, db, razorpay_service=None, whatsapp_service=None, pdf_service=None):
        self.db = db
        self.razorpay = razorpay_service
        self.whatsapp = whatsapp_service
        self.pdf = pdf_service
    
    async def generate_upcoming_invoices(self, days_before: int = 3) -> Dict[str, Any]:
        """
        Auto-generate invoices for subscribers with billing date approaching
        
        Args:
            days_before: Days before billing date to generate invoice (default 3)
        
        Returns:
            Summary of generated invoices
        """
        results = {
            "total_checked": 0,
            "invoices_generated": 0,
            "errors": []
        }
        
        now = datetime.now(timezone.utc)
        target_day = (now + timedelta(days=days_before)).day
        
        # Get all active operators
        operators = await self.db.operators.find({
            "status": {"$in": ["active", "trial"]},
            "deleted_at": None
        }, {"_id": 0}).to_list(1000)
        
        for operator in operators:
            try:
                # Get subscribers with matching billing date
                subscribers = await self.db.subscribers.find({
                    "operator_id": operator["id"],
                    "status": "active",
                    "billing_date": target_day,
                    "deleted_at": None
                }, {"_id": 0}).to_list(1000)
                
                results["total_checked"] += len(subscribers)
                
                for subscriber in subscribers:
                    try:
                        # Get subscriber's plan to know validity for duplicate check
                        plan_for_check = await self.db.operator_plans.find_one(
                            {"id": subscriber.get("plan_id"), "deleted_at": None}, {"_id": 0}
                        )
                        plan_validity = (plan_for_check or {}).get("validity", "monthly")

                        # Check if invoice already exists for this period
                        existing = await self._check_existing_invoice(
                            operator["id"],
                            subscriber["id"],
                            now,
                            validity=plan_validity,
                        )
                        
                        if existing:
                            continue
                        
                        # Generate new invoice
                        invoice = await self._create_auto_invoice(
                            operator,
                            subscriber
                        )
                        
                        if invoice:
                            results["invoices_generated"] += 1
                            logger.info(f"Generated invoice {invoice['invoice_number']} for {subscriber['name']}")
                        
                    except Exception as e:
                        error_msg = f"Error generating invoice for {subscriber['name']}: {str(e)}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        
            except Exception as e:
                logger.error(f"Error processing operator {operator['company_name']}: {str(e)}")
        
        return results
    
    async def send_overdue_reminders(self, days_overdue: int = 1) -> Dict[str, Any]:
        """
        Send reminders for overdue invoices
        
        Args:
            days_overdue: Minimum days overdue to send reminder
        
        Returns:
            Summary of reminders sent
        """
        results = {
            "total_overdue": 0,
            "reminders_sent": 0,
            "errors": []
        }
        
        now = datetime.now(timezone.utc)
        cutoff_date = (now - timedelta(days=days_overdue)).isoformat()
        
        # Find overdue invoices
        overdue_invoices = await self.db.invoices.find({
            "status": "pending",
            "due_date": {"$lt": cutoff_date},
            "deleted_at": None
        }, {"_id": 0}).to_list(1000)
        
        results["total_overdue"] = len(overdue_invoices)
        
        # Mark as overdue and send reminders
        for invoice in overdue_invoices:
            try:
                # Update status to overdue
                await self.db.invoices.update_one(
                    {"id": invoice["id"]},
                    {"$set": {"status": "overdue", "updated_at": now.isoformat()}}
                )
                
                # Get subscriber info
                subscriber = await self.db.subscribers.find_one(
                    {"id": invoice["subscriber_id"], "deleted_at": None},
                    {"_id": 0}
                )
                
                if subscriber and self.whatsapp:
                    # Calculate days overdue
                    due_date = datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00'))
                    days = (now - due_date).days
                    
                    # Send reminder
                    await self.whatsapp.send_payment_reminder(
                        recipient_phone=subscriber["whatsapp_number"],
                        customer_name=subscriber["name"],
                        invoice_number=invoice["invoice_number"],
                        amount_due=f"₹{invoice['final_amount']:,.2f}",
                        days_overdue=str(days),
                        payment_link=invoice.get("payment_link")
                    )
                    
                    results["reminders_sent"] += 1
                    
            except Exception as e:
                error_msg = f"Error sending reminder for invoice {invoice['invoice_number']}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        return results
    
    async def check_subscription_expiry(self) -> Dict[str, Any]:
        """
        Check and update operator subscription status
        """
        results = {
            "checked": 0,
            "expired": 0,
            "set_read_only": 0
        }
        
        now = datetime.now(timezone.utc)
        
        # Check trial expiry
        trial_operators = await self.db.operators.find({
            "status": "trial",
            "trial_ends_at": {"$lt": now.isoformat()},
            "deleted_at": None
        }, {"_id": 0}).to_list(1000)
        
        for op in trial_operators:
            await self.db.operators.update_one(
                {"id": op["id"]},
                {"$set": {"status": "expired", "is_read_only": True, "updated_at": now.isoformat()}}
            )
            results["expired"] += 1
        
        # Check subscription expiry
        active_operators = await self.db.operators.find({
            "status": "active",
            "subscription_ends_at": {"$lt": now.isoformat()},
            "deleted_at": None
        }, {"_id": 0}).to_list(1000)
        
        for op in active_operators:
            await self.db.operators.update_one(
                {"id": op["id"]},
                {"$set": {"is_read_only": True, "updated_at": now.isoformat()}}
            )
            results["set_read_only"] += 1
        
        results["checked"] = len(trial_operators) + len(active_operators)
        
        return results
    
    async def _check_existing_invoice(
        self,
        operator_id: str,
        subscriber_id: str,
        current_date: datetime,
        validity: str = "monthly",
    ) -> bool:
        """Check if invoice already exists for current billing period.
        Uses the plan validity to set an appropriate lookback window."""
        validity_days = {
            "monthly": 28,
            "quarterly": 85,
            "half_yearly": 175,
            "yearly": 360,
        }
        window = validity_days.get(validity, 28)
        cutoff = (current_date - timedelta(days=window)).isoformat()

        existing = await self.db.invoices.find_one({
            "operator_id": operator_id,
            "subscriber_id": subscriber_id,
            "status": {"$nin": ["cancelled"]},
            "service_start_date": {"$gte": cutoff},
            "deleted_at": None
        })
        return existing is not None
    
    async def _create_auto_invoice(
        self,
        operator: Dict,
        subscriber: Dict
    ) -> Dict[str, Any]:
        """Create an auto-generated invoice"""
        import uuid
        
        now = datetime.now(timezone.utc)
        
        # Get subscriber's plan
        plan = await self.db.operator_plans.find_one(
            {"id": subscriber["plan_id"], "deleted_at": None},
            {"_id": 0}
        )
        
        if not plan:
            return None
        
        # Calculate dates based on validity
        validity_days = {
            "monthly": 30,
            "quarterly": 90,
            "half_yearly": 180,
            "yearly": 365
        }
        
        service_days = validity_days.get(plan.get("validity", "monthly"), 30)
        # Set service_start to the subscriber's actual billing date this month
        billing_day = subscriber.get("billing_date", now.day)
        try:
            service_start = now.replace(day=billing_day, hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            # billing_day > days in current month (e.g., 31 in Feb) — use last day
            import calendar
            last_day = calendar.monthrange(now.year, now.month)[1]
            service_start = now.replace(day=last_day, hour=0, minute=0, second=0, microsecond=0)
        service_end = service_start + timedelta(days=service_days)
        due_date = service_start + timedelta(days=5)  # 5 days from billing date to pay
        
        # Calculate amounts
        base_amount = plan.get("price", 0)
        discount = subscriber.get("discount", 0)
        
        tax_amount = 0
        if operator.get("charge_gst") and plan.get("tax_percentage", 0) > 0:
            taxable = base_amount - discount
            if plan.get("tax_type") == "exclusive":
                tax_amount = taxable * (plan["tax_percentage"] / 100)
            elif plan.get("tax_type") == "inclusive":
                tax_amount = taxable - (taxable / (1 + plan["tax_percentage"] / 100))
        
        if plan.get("tax_type") == "exclusive":
            final_amount = base_amount - discount + tax_amount
        else:
            final_amount = base_amount - discount
        
        # Use operator's configured invoice prefix from invoice_settings
        inv_settings = await self.db.invoice_settings.find_one(
            {"operator_id": operator["id"]}, {"_id": 0}
        )
        # Generate globally unique invoice number using atomic counter
        from utils import generate_invoice_number_atomic
        invoice_number = await generate_invoice_number_atomic(self.db)
        
        # Create invoice
        invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": invoice_number,
            "subscriber_id": subscriber["id"],
            "subscriber_name": subscriber["name"],
            "plan_id": plan["id"],
            "plan_name": plan["name"],
            "base_amount": base_amount,
            "discount": discount,
            "tax_amount": round(tax_amount, 2),
            "final_amount": round(final_amount, 2),
            "service_start_date": service_start.isoformat(),
            "service_end_date": service_end.isoformat(),
            "due_date": due_date.isoformat(),
            "status": "pending",
            "payment_id": None,
            "payment_link": None,
            "payment_link_id": None,
            "operator_id": operator["id"],
            "auto_generated": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None
        }
        
        # Create payment link if Razorpay is configured
        if self.razorpay:
            try:
                gateway = await self.db.payment_gateways.find_one(
                    {"operator_id": operator["id"]},
                    {"_id": 0}
                )
                
                if gateway and gateway.get("is_active"):
                    # Use operator's Razorpay credentials
                    from services.razorpay_service import RazorpayService
                    op_razorpay = RazorpayService(gateway["api_key"], gateway["api_secret"])
                    
                    payment_link = op_razorpay.create_payment_link(
                        amount=final_amount,
                        description=f"Invoice {invoice_number} - {plan['name']}",
                        customer_name=subscriber["name"],
                        customer_email=subscriber.get("email", ""),
                        customer_phone=subscriber.get("whatsapp_number", ""),
                        invoice_number=invoice_number
                    )
                    
                    invoice["payment_link"] = payment_link.get("short_url")
                    invoice["payment_link_id"] = payment_link.get("id")
                    
            except Exception as e:
                logger.error(f"Failed to create payment link: {str(e)}")
        
        await self.db.invoices.insert_one(invoice)
        
        # Send notification if WhatsApp is available
        if self.whatsapp:
            try:
                await self.whatsapp.send_invoice_notification(
                    recipient_phone=subscriber["whatsapp_number"],
                    customer_name=subscriber["name"],
                    invoice_number=invoice_number,
                    amount=f"₹{final_amount:,.2f}",
                    due_date=due_date.strftime("%d %b %Y"),
                    payment_link=invoice.get("payment_link")
                )
            except Exception as e:
                logger.error(f"Failed to send invoice notification: {str(e)}")
        
        return invoice


    async def process_scheduled_reminders(self) -> Dict[str, Any]:
        """
        Process all operator reminder schedules.
        For each operator with whatsapp_notifications addon + WhatsApp configured + reminders enabled:
          - Check pending/overdue invoices
          - Send reminders based on schedule (before due, on due, after due)
          - Track reminders sent per invoice
        """
        results = {
            "operators_processed": 0,
            "reminders_sent": 0,
            "skipped": 0,
            "errors": [],
        }
        now = datetime.now(timezone.utc)
        today = now.date()

        # Get all reminder settings that are enabled
        settings_list = await self.db.reminder_settings.find(
            {"enabled": True}, {"_id": 0}
        ).to_list(1000)

        for settings in settings_list:
            operator_id = settings["operator_id"]
            try:
                # Verify operator is active
                operator = await self.db.operators.find_one(
                    {"id": operator_id, "status": {"$in": ["active", "trial"]}, "deleted_at": None},
                    {"_id": 0},
                )
                if not operator:
                    continue

                # Check addon is active
                has_addon = False
                if "whatsapp_notifications" in operator.get("active_addons", []):
                    has_addon = True
                else:
                    plan = await self.db.saas_plans.find_one(
                        {"id": operator.get("saas_plan_id"), "deleted_at": None}, {"_id": 0}
                    )
                    if plan and "whatsapp_notifications" in plan.get("included_addons", []):
                        has_addon = True
                if not has_addon:
                    continue

                # Check WhatsApp config - use platform global config
                wa_config = await self.db.global_settings.find_one(
                    {"type": "platform_whatsapp"}, {"_id": 0}
                )
                if not wa_config or not wa_config.get("access_token"):
                    continue

                # Get template settings
                template_settings = await self.db.global_settings.find_one(
                    {"type": "whatsapp_template_settings"}, {"_id": 0}
                ) or {}

                results["operators_processed"] += 1

                # Get pending and overdue invoices
                invoices = await self.db.invoices.find(
                    {
                        "operator_id": operator_id,
                        "status": {"$in": ["pending", "overdue"]},
                        "deleted_at": None,
                    },
                    {"_id": 0},
                ).to_list(5000)

                max_reminders = settings.get("max_reminders_per_invoice", 5)

                for invoice in invoices:
                    try:
                        due_str = invoice.get("due_date", "")
                        if not due_str:
                            continue
                        due_date = datetime.fromisoformat(due_str.replace("Z", "+00:00")).date()

                        days_diff = (due_date - today).days  # positive = before due, negative = after due

                        should_send = False
                        reason = ""

                        # Before due date
                        if days_diff > 0 and days_diff in settings.get("remind_before_due", []):
                            should_send = True
                            reason = f"{days_diff}d_before_due"
                        # On due date
                        elif days_diff == 0 and settings.get("remind_on_due", False):
                            should_send = True
                            reason = "on_due_date"
                        # After due date
                        elif days_diff < 0 and abs(days_diff) in settings.get("remind_after_due", []):
                            should_send = True
                            reason = f"{abs(days_diff)}d_after_due"

                        if not should_send:
                            continue

                        # Check how many reminders already sent for this invoice
                        sent_count = len(invoice.get("reminders_sent", []))
                        if sent_count >= max_reminders:
                            results["skipped"] += 1
                            continue

                        # Check if we already sent a reminder for this exact reason today
                        already_sent_today = any(
                            r.get("reason") == reason and r.get("date") == today.isoformat()
                            for r in invoice.get("reminders_sent", [])
                        )
                        if already_sent_today:
                            results["skipped"] += 1
                            continue

                        # Get subscriber
                        subscriber = await self.db.subscribers.find_one(
                            {"id": invoice["subscriber_id"], "deleted_at": None},
                            {"_id": 0},
                        )
                        if not subscriber:
                            continue

                        # Send reminder
                        from services.whatsapp_service import WhatsAppService

                        wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])

                        if days_diff <= 0:
                            # After due or on due — payment reminder
                            reminder_tpl = template_settings.get("reminder_template") or "payment_reminder"
                            days_overdue = max(0, abs(days_diff))
                            await wa_service.send_payment_reminder(
                                recipient_phone=subscriber["whatsapp_number"],
                                customer_name=subscriber["name"],
                                invoice_number=invoice["invoice_number"],
                                amount_due=f"₹{invoice['final_amount']:,.2f}",
                                days_overdue=str(days_overdue),
                                payment_link=invoice.get("payment_link"),
                                template_name_override=reminder_tpl,
                            )
                        else:
                            # Before due — invoice notification / upcoming reminder
                            invoice_tpl = template_settings.get("invoice_template") or "invoice_notification"
                            await wa_service.send_invoice_notification(
                                recipient_phone=subscriber["whatsapp_number"],
                                customer_name=subscriber["name"],
                                invoice_number=invoice["invoice_number"],
                                amount=f"₹{invoice['final_amount']:,.2f}",
                                due_date=due_date.strftime("%d %b %Y"),
                                payment_link=invoice.get("payment_link"),
                                template_name_override=invoice_tpl,
                            )

                        # Record the reminder
                        reminder_record = {
                            "reason": reason,
                            "date": today.isoformat(),
                            "sent_at": now.isoformat(),
                        }
                        await self.db.invoices.update_one(
                            {"id": invoice["id"]},
                            {
                                "$push": {"reminders_sent": reminder_record},
                                "$set": {"updated_at": now.isoformat()},
                            },
                        )

                        results["reminders_sent"] += 1
                        logger.info(
                            f"Sent scheduled reminder for invoice {invoice['invoice_number']} "
                            f"({reason}) to {subscriber['name']}"
                        )

                    except Exception as e:
                        results["errors"].append(
                            f"Invoice {invoice.get('invoice_number', '?')}: {str(e)}"
                        )

            except Exception as e:
                results["errors"].append(f"Operator {operator_id}: {str(e)}")

        return results


async def run_daily_invoice_generation(db):
    """Daily cron job for invoice generation"""
    service = CronJobService(db)
    results = await service.generate_upcoming_invoices(days_before=3)
    logger.info(f"Daily invoice generation: {results}")
    return results


async def run_daily_reminder_processing(db):
    """Daily cron job for scheduled reminder processing"""
    service = CronJobService(db)
    results = await service.process_scheduled_reminders()
    logger.info(f"Daily scheduled reminders: {results}")
    return results


async def run_hourly_reminder_check(db):
    """Hourly cron job for overdue reminders (legacy — marks overdue invoices)"""
    service = CronJobService(db)
    results = await service.send_overdue_reminders(days_overdue=1)
    logger.info(f"Hourly reminder check: {results}")
    return results


async def run_daily_expiry_check(db):
    """Daily cron job for subscription expiry"""
    service = CronJobService(db)
    results = await service.check_subscription_expiry()
    logger.info(f"Daily expiry check: {results}")
    return results



async def run_daily_settlement_processing(db):
    """Daily cron job for processing operator settlements.
    
    Finds all paid invoices from the previous day that haven't been settled,
    groups them by operator, applies platform fee, and creates settlement records.
    """
    import uuid
    now = datetime.now(timezone.utc)
    # Settle for yesterday
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_yesterday = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

    settlement_date = yesterday.strftime("%Y-%m-%d")

    results = {
        "settlement_date": settlement_date,
        "operators_processed": 0,
        "settlements_created": 0,
        "total_collected": 0,
        "total_settled": 0,
        "errors": [],
    }

    try:
        # Get platform fee percentage from global settings
        global_settings = await db.global_settings.find_one({"type": "platform_settings"}, {"_id": 0})
        platform_fee_pct = float((global_settings or {}).get("platform_fee_percentage", 2))

        # Find all paid invoices from yesterday that are NOT already settled
        paid_invoices = await db.invoices.find({
            "status": "paid",
            "deleted_at": None,
            "settled": {"$ne": True},
            "paid_at": {
                "$gte": yesterday.isoformat(),
                "$lte": end_of_yesterday.isoformat(),
            },
        }, {"_id": 0}).to_list(10000)

        if not paid_invoices:
            logger.info(f"No unsettled paid invoices for {settlement_date}")
            return results

        # Group invoices by operator
        operator_groups = {}
        for inv in paid_invoices:
            op_id = inv["operator_id"]
            if op_id not in operator_groups:
                operator_groups[op_id] = []
            operator_groups[op_id].append(inv)

        # Process each operator
        for operator_id, invoices in operator_groups.items():
            try:
                operator = await db.operators.find_one(
                    {"id": operator_id, "deleted_at": None}, {"_id": 0}
                )
                if not operator:
                    results["errors"].append(f"Operator {operator_id} not found")
                    continue

                total_collected = sum(inv["final_amount"] for inv in invoices)
                platform_fee = round(total_collected * platform_fee_pct / 100, 2)
                tax_on_fee = round(platform_fee * 18 / 100, 2)  # 18% GST on platform fee
                net_settlement = round(total_collected - platform_fee - tax_on_fee, 2)
                invoice_ids = [inv["id"] for inv in invoices]

                settlement = {
                    "id": str(uuid.uuid4()),
                    "operator_id": operator_id,
                    "operator_name": operator.get("company_name", "Unknown"),
                    "settlement_date": settlement_date,
                    "total_collections": total_collected,
                    "platform_fee_percentage": platform_fee_pct,
                    "platform_fee": platform_fee,
                    "tax_on_platform_fee": tax_on_fee,
                    "net_settlement": net_settlement,
                    "payment_count": len(invoices),
                    "invoice_ids": invoice_ids,
                    "status": "pending",
                    "utr_number": None,
                    "paid_at": None,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
                await db.settlements.insert_one(settlement)

                # Mark invoices as settled
                await db.invoices.update_many(
                    {"id": {"$in": invoice_ids}},
                    {"$set": {"settled": True, "settlement_id": settlement["id"]}}
                )

                results["operators_processed"] += 1
                results["settlements_created"] += 1
                results["total_collected"] += total_collected
                results["total_settled"] += net_settlement

            except Exception as e:
                results["errors"].append(f"Operator {operator_id}: {str(e)}")

    except Exception as e:
        results["errors"].append(f"Settlement processing error: {str(e)}")

    logger.info(f"Daily settlement processing: {results}")
    return results
