"""
Cron Job Services for Auto Invoice Generation and Reminders
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

from services.global_settings_store import get_global_settings_doc
from services.env_service import get_env_setting

async def get_maintenance_state(db) -> Dict[str, Any]:
    settings = await get_global_settings_doc({"type": "platform"}, {"_id": 0}) or {}
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
        
        operators = await self.db.operators.find({
            "status": {"$in": ["active", "trial"]},
            "wallet_suspended": {"$ne": True},
            "deleted_at": None
        }, {"_id": 0}).to_list(1000)
        
        for operator in operators:
            try:
                # Skip if operator wallet balance is below Rs.50
                op_wallet = await self.db.operator_wallets.find_one({"operator_id": operator["id"]}, {"_id": 0})
                if (op_wallet or {}).get("balance", 0) < 50:
                    logger.info(f"Skipping auto-invoice for {operator.get('company_name', operator['id'])}: wallet balance below ₹50")
                    continue

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
                        plans_to_bill = [
                            p for p in subscriber.get("plans", [])
                            if p.get("billing_date") == target_day and p.get("status") == "active"
                        ]
                        
                        if not plans_to_bill:
                            continue

                        existing = await self._check_existing_invoice(
                            operator["id"],
                            subscriber["id"],
                            now,
                            validity="monthly",
                        )
                        
                        if existing:
                            continue
                        
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
        
        overdue_invoices = await self.db.invoices.find({
            "status": "pending",
            "due_date": {"$lt": cutoff_date},
            "deleted_at": None
        }, {"_id": 0}).to_list(1000)
        
        results["total_overdue"] = len(overdue_invoices)
        
        from services.whatsapp_service import get_whatsapp_service_async, log_whatsapp_message
        wa_service = await get_whatsapp_service_async()

        for invoice in overdue_invoices:
            try:
                await self.db.invoices.update_one(
                    {"id": invoice["id"]},
                    {"$set": {"status": "overdue", "updated_at": now.isoformat()}}
                )
                
                subscriber = await self.db.subscribers.find_one(
                    {"id": invoice["subscriber_id"], "deleted_at": None},
                    {"_id": 0}
                )
                
                if subscriber and wa_service:
                    due_date = datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00'))
                    days = (now - due_date).days
                    
                    wa_result = await wa_service.send_payment_reminder(
                        recipient_phone=subscriber["whatsapp_number"],
                        customer_name=subscriber["name"],
                        invoice_number=invoice["invoice_number"],
                        amount_due=f"INR {invoice['final_amount']:,.2f}",
                        days_overdue=str(days),
                        payment_link=invoice.get("payment_link")
                    )
                    
                    results["reminders_sent"] += 1

                    # Log the sent message
                    try:
                        wa_msg_id = (wa_result.get("messages") or [{}])[0].get("id", "") if wa_result else ""
                        wa_wa_id = (wa_result.get("contacts") or [{}])[0].get("wa_id", "") if wa_result else ""
                        await log_whatsapp_message(
                            self.db,
                            operator_id=invoice.get("operator_id"),
                            template_name="payment_reminder",
                            template_category="payment_due_reminder",
                            recipient_phone=subscriber["whatsapp_number"],
                            status="sent",
                            message_id=wa_msg_id,
                            wa_id=wa_wa_id,
                            invoice_id=invoice["id"],
                            invoice_number=invoice["invoice_number"],
                            trigger="cron",
                        )
                    except Exception as log_e:
                        logger.warning(f"WhatsApp message log failed: {log_e}")
                    
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
        import uuid
        now = datetime.now(timezone.utc)
        can_charge_gst = operator.get("charge_gst") and operator.get("gst_number")
        
        line_items = []
        total_base = 0
        total_discount = 0
        total_tax = 0
        total_final = 0

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

        first_service_start = datetime.fromisoformat(line_items[0]["service_start_date"])
        due_date = first_service_start + timedelta(days=5)

        from utils import generate_invoice_number_atomic
        invoice_number = await generate_invoice_number_atomic(self.db)
        
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
        try:
            gateway = await self.db.payment_gateways.find_one(
                {"operator_id": operator["id"], "is_active": True},
                {"_id": 0}
            )
            
            if gateway:
                from services.razorpay_service import get_razorpay_service_async
                op_razorpay = await get_razorpay_service_async(operator_id=operator["id"])
                
                if op_razorpay:
                    desc = f"Invoice {invoice_number} - {subscriber['name']}"
                    payment_link = await op_razorpay.create_payment_link_async(
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
        
        try:
            from routers.wallet import deduct_wallet_for_invoice
            await deduct_wallet_for_invoice(operator["id"], invoice["id"])
        except Exception as e:
            logger.warning(f"Wallet deduction failed for auto-invoice {invoice['id']}: {e}")

        # Send notification if WhatsApp is available
        from services.whatsapp_service import get_whatsapp_service_async, build_wa_send_params, log_whatsapp_message
        from services.invoice_view_service import build_public_invoice_url_from_env
        wa_service = await get_whatsapp_service_async()
        if wa_service:
            try:
                cron_template_settings = await self.db.global_settings.find_one(
                    {"type": "whatsapp_template_settings"}, {"_id": 0}
                ) or {}
                invoice_tpl_name = cron_template_settings.get("invoice_template") or "invoice_notification"
                tmpl_doc = await self.db.whatsapp_templates.find_one(
                    {"template_name": invoice_tpl_name, "deleted_at": None}, {"_id": 0}
                )

                inv_public_url = await build_public_invoice_url_from_env(invoice)
                params = await build_wa_send_params(self.db, tmpl_doc, invoice, subscriber, invoice_public_url=inv_public_url)

                wa_result = None
                if params["body_vars"]:
                    wa_result = await wa_service.send_template_message(
                        recipient_phone=subscriber["whatsapp_number"],
                        template_name=invoice_tpl_name,
                        language_code=params["language_code"],
                        variables=params["variables"],
                        header_params=params["header_params"],
                        header_type=params["header_type"],
                        button_params=params["btn_params"],
                    )
                else:
                    wa_result = await wa_service.send_invoice_notification(
                        recipient_phone=subscriber["whatsapp_number"],
                        customer_name=subscriber["name"],
                        invoice_number=invoice_number,
                        amount=f"INR {invoice['final_amount']:,.2f}",
                        due_date=due_date.strftime("%d %b %Y"),
                        payment_link=inv_public_url or invoice.get("payment_link"),
                        header_params=params["header_params"],
                        header_type=params["header_type"],
                    )

                # Log the sent message
                try:
                    wa_msg_id = (wa_result.get("messages") or [{}])[0].get("id", "") if wa_result else ""
                    wa_wa_id = (wa_result.get("contacts") or [{}])[0].get("wa_id", "") if wa_result else ""
                    await log_whatsapp_message(
                        self.db,
                        operator_id=operator["id"],
                        template_name=invoice_tpl_name,
                        template_category="invoice_notification",
                        recipient_phone=subscriber["whatsapp_number"],
                        status="sent",
                        message_id=wa_msg_id,
                        wa_id=wa_wa_id,
                        invoice_id=invoice["id"],
                        invoice_number=invoice_number,
                        trigger="auto_invoice",
                    )
                except Exception as log_e:
                    logger.warning(f"WhatsApp message log failed: {log_e}")
            except Exception as e:
                logger.error(f"Failed to send invoice notification: {str(e)}")
        
        return invoice


    async def process_scheduled_reminders(self) -> Dict[str, Any]:
        """
        Process all operator reminder schedules using the platform-wide global reminder settings.
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

        global_reminder = await self.db.global_settings.find_one(
            {"type": "reminder_settings"}, {"_id": 0}
        ) or {}
        if not global_reminder.get("enabled", True):
            return {**results, "skipped": 1, "reason": "Global reminders are disabled"}

        remind_before = global_reminder.get("remind_before_due", [7, 5, 3, 2, 1])
        remind_on_due = global_reminder.get("remind_on_due", True)
        remind_after  = global_reminder.get("remind_after_due", list(range(1, 11)))
        max_reminders = global_reminder.get("max_reminders_per_invoice", 20)

        operators = await self.db.operators.find(
            {"status": {"$in": ["active", "trial"]}, "deleted_at": None},
            {"_id": 0},
        ).to_list(1000)

        from services.whatsapp_service import get_whatsapp_service_async
        wa_service = await get_whatsapp_service_async()
        if not wa_service:
            return {**results, "skipped": 1, "reason": "WhatsApp not configured"}

        template_settings = await self.db.global_settings.find_one(
            {"type": "whatsapp_template_settings"}, {"_id": 0}
        ) or {}

        for operator in operators:
            operator_id = operator["id"]
            try:
                has_addon = "whatsapp_notifications" in operator.get("active_addons", [])
                if not has_addon:
                    plan = await self.db.saas_plans.find_one(
                        {"id": operator.get("saas_plan_id"), "deleted_at": None}, {"_id": 0}
                    )
                    if plan and "whatsapp_notifications" in plan.get("included_addons", []):
                        has_addon = True
                if not has_addon:
                    continue

                results["operators_processed"] += 1

                invoices = await self.db.invoices.find(
                    {
                        "operator_id": operator_id,
                        "status": {"$in": ["pending", "overdue"]},
                        "deleted_at": None,
                    },
                    {"_id": 0},
                ).to_list(5000)

                for invoice in invoices:
                    try:
                        due_str = invoice.get("due_date", "")
                        if not due_str:
                            continue
                        due_date = datetime.fromisoformat(due_str.replace("Z", "+00:00")).date()
                        days_diff = (due_date - today).days

                        should_send = False
                        reason = ""

                        if days_diff > 0 and days_diff in remind_before:
                            should_send = True
                            reason = f"{days_diff}d_before_due"
                        elif days_diff == 0 and remind_on_due:
                            should_send = True
                            reason = "on_due_date"
                        elif days_diff < 0 and abs(days_diff) in remind_after:
                            should_send = True
                            reason = f"{abs(days_diff)}d_after_due"

                        if not should_send:
                            continue

                        sent_count = len(invoice.get("reminders_sent", []))
                        if sent_count >= max_reminders:
                            results["skipped"] += 1
                            continue

                        already_sent_today = any(
                            r.get("reason") == reason and r.get("date") == today.isoformat()
                            for r in invoice.get("reminders_sent", [])
                        )
                        if already_sent_today:
                            results["skipped"] += 1
                            continue

                        subscriber = await self.db.subscribers.find_one(
                            {"id": invoice["subscriber_id"], "deleted_at": None},
                            {"_id": 0},
                        )
                        if not subscriber:
                            continue

                        from services.whatsapp_service import resolve_template_variables, build_wa_send_params, log_whatsapp_message
                        from services.invoice_view_service import build_public_invoice_url_from_env
                        inv_public_url = await build_public_invoice_url_from_env(invoice)
                        wa_send_result = None
                        wa_template_used = ""
                        wa_category_used = ""

                        if days_diff < 0:
                            # Overdue — use payment_due_reminder template if configured, else fall back to reminder_template
                            reminder_tpl = (
                                template_settings.get("payment_due_reminder_template") or
                                template_settings.get("reminder_template") or
                                "payment_reminder"
                            )
                            wa_template_used = reminder_tpl
                            wa_category_used = "payment_due_reminder"
                            tmpl_doc = await self.db.whatsapp_templates.find_one(
                                {"template_name": reminder_tpl, "deleted_at": None}, {"_id": 0}
                            )
                            params = await build_wa_send_params(self.db, tmpl_doc, invoice, subscriber, invoice_public_url=inv_public_url)

                            if params["body_vars"]:
                                wa_send_result = await wa_service.send_template_message(
                                    recipient_phone=subscriber["whatsapp_number"],
                                    template_name=reminder_tpl,
                                    language_code=params["language_code"],
                                    variables=params["variables"],
                                    header_params=params["header_params"],
                                    header_type=params["header_type"],
                                    button_params=params["btn_params"],
                                )
                            else:
                                wa_send_result = await wa_service.send_payment_reminder(
                                    recipient_phone=subscriber["whatsapp_number"],
                                    customer_name=subscriber["name"],
                                    invoice_number=invoice["invoice_number"],
                                    amount_due=f"INR {invoice['final_amount']:,.2f}",
                                    days_overdue=str(max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00'))).days)),
                                    payment_link=inv_public_url or invoice.get("payment_link"),
                                    header_params=params["header_params"],
                                    header_type=params["header_type"],
                                )
                        elif days_diff == 0:
                            # On due date — use regular reminder template
                            reminder_tpl = template_settings.get("reminder_template") or "payment_reminder"
                            wa_template_used = reminder_tpl
                            wa_category_used = "payment_reminder"
                            tmpl_doc = await self.db.whatsapp_templates.find_one(
                                {"template_name": reminder_tpl, "deleted_at": None}, {"_id": 0}
                            )
                            params = await build_wa_send_params(self.db, tmpl_doc, invoice, subscriber, invoice_public_url=inv_public_url)

                            if params["body_vars"]:
                                wa_send_result = await wa_service.send_template_message(
                                    recipient_phone=subscriber["whatsapp_number"],
                                    template_name=reminder_tpl,
                                    language_code=params["language_code"],
                                    variables=params["variables"],
                                    header_params=params["header_params"],
                                    header_type=params["header_type"],
                                    button_params=params["btn_params"],
                                )
                            else:
                                wa_send_result = await wa_service.send_payment_reminder(
                                    recipient_phone=subscriber["whatsapp_number"],
                                    customer_name=subscriber["name"],
                                    invoice_number=invoice["invoice_number"],
                                    amount_due=f"INR {invoice['final_amount']:,.2f}",
                                    days_overdue="0",
                                    payment_link=inv_public_url or invoice.get("payment_link"),
                                    header_params=params["header_params"],
                                    header_type=params["header_type"],
                                )
                        else:
                            # Before due date — use invoice template
                            invoice_tpl = template_settings.get("invoice_template") or "invoice_notification"
                            wa_template_used = invoice_tpl
                            wa_category_used = "invoice_notification"
                            tmpl_doc = await self.db.whatsapp_templates.find_one(
                                {"template_name": invoice_tpl, "deleted_at": None}, {"_id": 0}
                            )
                            params = await build_wa_send_params(self.db, tmpl_doc, invoice, subscriber, invoice_public_url=inv_public_url)

                            if params["body_vars"]:
                                wa_send_result = await wa_service.send_template_message(
                                    recipient_phone=subscriber["whatsapp_number"],
                                    template_name=invoice_tpl,
                                    language_code=params["language_code"],
                                    variables=params["variables"],
                                    header_params=params["header_params"],
                                    header_type=params["header_type"],
                                    button_params=params["btn_params"],
                                )
                            else:
                                wa_send_result = await wa_service.send_invoice_notification(
                                    recipient_phone=subscriber["whatsapp_number"],
                                    customer_name=subscriber["name"],
                                    invoice_number=invoice["invoice_number"],
                                    amount=f"INR {invoice['final_amount']:,.2f}",
                                    due_date=datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00')).strftime("%d %b %Y"),
                                    payment_link=inv_public_url or invoice.get("payment_link"),
                                    header_params=params["header_params"],
                                    header_type=params["header_type"],
                                )

                        # ── Log successful send ──────────────────────────────────────
                        try:
                            wa_msg_id = (wa_send_result.get("messages") or [{}])[0].get("id", "") if wa_send_result else ""
                            wa_wa_id = (wa_send_result.get("contacts") or [{}])[0].get("wa_id", "") if wa_send_result else ""
                            await log_whatsapp_message(
                                self.db,
                                operator_id=operator_id,
                                template_name=wa_template_used,
                                template_category=wa_category_used,
                                recipient_phone=subscriber["whatsapp_number"],
                                status="sent",
                                message_id=wa_msg_id,
                                wa_id=wa_wa_id,
                                invoice_id=invoice["id"],
                                invoice_number=invoice["invoice_number"],
                                trigger="cron",
                            )
                        except Exception as log_e:
                            logger.warning(f"WhatsApp message log failed: {log_e}")

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
                            f"Sent reminder for invoice {invoice['invoice_number']} ({reason}) to {subscriber['name']}"
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
    platform_settings = await get_global_settings_doc({"type": "platform"}, {"_id": 0}) or {}
    days_before = int(platform_settings.get("auto_invoice_days_before", 3) or 3)
    service = CronJobService(db)
    results = await service.generate_upcoming_invoices(days_before=days_before)
    logger.info(f"Daily invoice generation: {results}")
    return results


async def run_daily_reminder_processing(db):
    """Daily cron job for scheduled reminder processing"""
    service = CronJobService(db)
    results = await service.process_scheduled_reminders()
    logger.info(f"Daily scheduled reminders: {results}")
    return results


async def run_hourly_reminder_check(db):
    """Hourly cron job for overdue reminders (legacy)"""
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

    from services.whatsapp_service import get_whatsapp_service_async
    wa_service = await get_whatsapp_service_async()

    for op in operators:
        try:
            wallet = await db.operator_wallets.find_one({"operator_id": op["id"]}, {"_id": 0})
            balance = (wallet or {}).get("balance", 0)
            results["checked"] += 1

            if balance < 100 and not op.get("wallet_suspended"):
                await db.operators.update_one(
                    {"id": op["id"]},
                    {"$set": {"wallet_suspended": True, "is_read_only": True, "updated_at": now.isoformat()}}
                )
                results["suspended"] += 1
                logger.warning(f"Operator {op['company_name']} suspended due to low wallet balance: Rs.{balance}")

            elif balance < 500 and not op.get("wallet_suspended"):
                results["reminders_sent"] += 1
                if wa_service:
                    try:
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
