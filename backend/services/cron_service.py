"""
Cron Job Services for Auto Invoice Generation and Reminders
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)


async def get_maintenance_state(db) -> Dict[str, Any]:
    settings = await db.global_settings.find_one({"type": "platform"}, {"_id": 0}) or {}
    return {
        "maintenance_mode": bool(settings.get("maintenance_mode", False)),
        "maintenance_message": settings.get("maintenance_message") or "The app is under maintenance.",
    }

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
        maintenance = await get_maintenance_state(self.db)
        if maintenance["maintenance_mode"]:
            return {**results, "skipped": True, "reason": maintenance["maintenance_message"]}
        
        now = datetime.now(timezone.utc)
        target_day = (now + timedelta(days=days_before)).day
        
        # Get all active operators (skip wallet-suspended ones for automation)
        operators = await self.db.operators.find({
            "status": {"$in": ["active", "trial"]},
            "wallet_suspended": {"$ne": True},
            "deleted_at": None
        }, {"_id": 0}).to_list(1000)
        
        for operator in operators:
            try:
                # Get subscribers with at least one plan matching the target billing date
                subscribers = await self.db.subscribers.find({
                    "operator_id": operator["id"],
                    "status": "active",
                    "plans": {
                        "$elemMatch": {
                            "billing_date": target_day,
                            "status": "active"
                        }
                    },
                    "deleted_at": None
                }, {"_id": 0}).to_list(1000)
                
                results["total_checked"] += len(subscribers)
                
                for subscriber in subscribers:
                    try:
                        # Identify which plans are due today
                        plans_to_bill = [
                            p for p in subscriber.get("plans", [])
                            if p.get("billing_date") == target_day and p.get("status") == "active"
                        ]
                        
                        if not plans_to_bill:
                            continue

                        # Check if invoice already exists for this period (for any of the plans)
                        # To keep it simple, we check if ANY invoice was generated for this subscriber 
                        # in the last 25 days (lookback window). 
                        # In a more advanced version, we'd check per plan_id.
                        existing = await self._check_existing_invoice(
                            operator["id"],
                            subscriber["id"],
                            now,
                            validity="monthly", # Default to monthly for check
                        )
                        
                        if existing:
                            continue
                        
                        # Generate new invoice with all plans due today
                        invoice = await self._create_auto_invoice(
                            operator,
                            subscriber,
                            plans_to_bill
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
        maintenance = await get_maintenance_state(self.db)
        if maintenance["maintenance_mode"]:
            return {**results, "skipped": True, "reason": maintenance["maintenance_message"]}
        
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
        maintenance = await get_maintenance_state(self.db)
        if maintenance["maintenance_mode"]:
            return {**results, "skipped": True, "reason": maintenance["maintenance_message"]}
        
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
        subscriber: Dict,
        plans_to_bill: List[Dict]
    ) -> Dict[str, Any]:
        """Create an auto-generated invoice with multiple line items"""
        import uuid
        
        now = datetime.now(timezone.utc)
        can_charge_gst = operator.get("charge_gst") and operator.get("gst_number")
        
        line_items = []
        total_base = 0
        total_discount = 0
        total_tax = 0
        total_final = 0

        # Calculate dates based on validity
        validity_days_map = {
            "monthly": 30,
            "quarterly": 90,
            "half_yearly": 180,
            "yearly": 365
        }

        for p_info in plans_to_bill:
            plan = await self.db.operator_plans.find_one(
                {"id": p_info["plan_id"], "deleted_at": None},
                {"_id": 0}
            )
            if not plan:
                continue

            service_days = validity_days_map.get(plan.get("validity", "monthly"), 30)
            billing_day = p_info.get("billing_date", now.day)
            try:
                service_start = now.replace(day=billing_day, hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                import calendar
                last_day = calendar.monthrange(now.year, now.month)[1]
                service_start = now.replace(day=last_day, hour=0, minute=0, second=0, microsecond=0)
            
            service_end = service_start + timedelta(days=service_days)
            
            # Calculate amounts
            base_amount = plan.get("price", 0)
            discount = p_info.get("discount", 0)
            
            tax_amount = 0
            if can_charge_gst and plan.get("tax_percentage", 0) > 0:
                taxable = base_amount - discount
                if plan.get("tax_type") == "exclusive":
                    tax_amount = taxable * (plan["tax_percentage"] / 100)
                elif plan.get("tax_type") == "inclusive":
                    tax_amount = taxable - (taxable / (1 + plan["tax_percentage"] / 100))
            
            final_amount = base_amount - discount + (tax_amount if plan.get("tax_type") == "exclusive" else 0)
            
            line_items.append({
                "plan_id": plan["id"],
                "plan_name": plan["name"],
                "base_amount": base_amount,
                "discount": discount,
                "tax_amount": round(tax_amount, 2),
                "final_amount": round(final_amount, 2),
                "service_start_date": service_start.isoformat(),
                "service_end_date": service_end.isoformat()
            })
            
            total_base += base_amount
            total_discount += discount
            total_tax += tax_amount
            total_final += final_amount

        if not line_items:
            return None

        # Due date is 5 days from the (first) service start date
        first_service_start = datetime.fromisoformat(line_items[0]["service_start_date"])
        due_date = first_service_start + timedelta(days=5)

        # Generate globally unique invoice number using atomic counter
        from utils import generate_invoice_number_atomic
        invoice_number = await generate_invoice_number_atomic(self.db)
        
        # Create invoice
        invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": invoice_number,
            "subscriber_id": subscriber["id"],
            "subscriber_name": subscriber["name"],
            "line_items": line_items,
            "base_amount": round(total_base, 2),
            "discount": round(total_discount, 2),
            "tax_amount": round(total_tax, 2),
            "final_amount": round(total_final, 2),
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
                    from services.razorpay_service import RazorpayService
                    op_razorpay = RazorpayService(gateway["api_key"], gateway["api_secret"])
                    
                    desc = f"Invoice {invoice_number} - {subscriber['name']}"
                    if len(line_items) == 1:
                        desc = f"Invoice {invoice_number} - {line_items[0]['plan_name']}"
                    
                    payment_link = op_razorpay.create_payment_link(
                        amount=invoice["final_amount"],
                        description=desc,
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
        
        # Deduct Rs.10 from operator wallet for invoice generation
        try:
            from routers.wallet import deduct_wallet_for_invoice
            await deduct_wallet_for_invoice(operator["id"], invoice["id"])
        except Exception as e:
            logger.warning(f"Wallet deduction failed for auto-invoice {invoice['id']}: {e}")

        # Send notification if WhatsApp is available
        if self.whatsapp:
            try:
                await self.whatsapp.send_invoice_notification(
                    recipient_phone=subscriber["whatsapp_number"],
                    customer_name=subscriber["name"],
                    invoice_number=invoice_number,
                    amount=f"₹{invoice['final_amount']:,.2f}",
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
        maintenance = await get_maintenance_state(self.db)
        if maintenance["maintenance_mode"]:
            return {**results, "skipped": 1, "reason": maintenance["maintenance_message"]}
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



async def run_daily_wallet_check(db):
    """Daily cron: check operator wallet balances, send reminders, suspend if < 100."""
    now = datetime.now(timezone.utc)
    results = {"checked": 0, "reminders_sent": 0, "suspended": 0, "errors": []}
    maintenance = await get_maintenance_state(db)
    if maintenance["maintenance_mode"]:
        return {**results, "skipped": True, "reason": maintenance["maintenance_message"]}

    operators = await db.operators.find(
        {"status": {"$in": ["active", "trial"]}, "deleted_at": None}, {"_id": 0}
    ).to_list(5000)

    for op in operators:
        try:
            wallet = await db.operator_wallets.find_one({"operator_id": op["id"]}, {"_id": 0})
            balance = (wallet or {}).get("balance", 0)
            results["checked"] += 1

            if balance < 100 and not op.get("wallet_suspended"):
                # Suspend operator
                await db.operators.update_one(
                    {"id": op["id"]},
                    {"$set": {"wallet_suspended": True, "is_read_only": True, "updated_at": now.isoformat()}}
                )
                results["suspended"] += 1
                logger.warning(f"Operator {op['company_name']} suspended due to low wallet balance: Rs.{balance}")

            elif balance < 500 and not op.get("wallet_suspended"):
                # Send reminder via WhatsApp if configured
                results["reminders_sent"] += 1
                try:
                    wa_config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
                    if wa_config and wa_config.get("access_token"):
                        from services.whatsapp_service import WhatsAppService
                        wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
                        await wa_service.send_text_message(
                            recipient_phone=op.get("phone", ""),
                            message=(
                                f"Dear {op.get('company_name', 'Operator')},\n\n"
                                f"Your E-Bill wallet balance is low (Rs.{balance:.2f}).\n"
                                f"Please topup your wallet to keep services active.\n"
                                f"Balance below Rs.100 will suspend your account.\n\nLogin to topup: E-Bill Dashboard"
                            )
                        )
                except Exception as wa_err:
                    logger.warning(f"Wallet reminder WhatsApp failed for {op['id']}: {wa_err}")

        except Exception as e:
            results["errors"].append(f"Operator {op.get('id', '?')}: {str(e)}")

    logger.info(f"Daily wallet check: {results}")
    return results
