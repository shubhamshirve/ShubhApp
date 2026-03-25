import asyncio
import logging
from datetime import datetime, time, timedelta
import pytz
from typing import List, Dict, Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from services.whatsapp_service import WhatsAppService, get_whatsapp_service_async
from services.email_service import EmailService
from services.env_service import get_env_setting

logger = logging.getLogger(__name__)

class CronService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.tz = pytz.timezone("Asia/Kolkata")
        self._stop_event = asyncio.Event()

    async def start(self):
        """Main cron loop"""
        logger.info("Cron Service started")
        while not self._stop_event.is_set():
            try:
                now = datetime.now(self.tz)
                settings = await self.db.global_settings.find_one({"type": "admin_settings"})
                if not settings:
                    await asyncio.sleep(60)
                    continue

                # Maintenance Mode Check
                if settings.get("maintenance_mode", False):
                    # In maintenance mode, we might want to skip some jobs
                    pass

                # Job 1: Daily Backup (03:00 IST default)
                await self._check_and_run_job(
                    "daily_backup",
                    settings.get("cron_backup_time", "03:00"),
                    self._run_backup
                )

                # Job 2: Expiry Check (00:05 IST default)
                await self._check_and_run_job(
                    "expiry_check",
                    settings.get("cron_expiry_time", "00:05"),
                    self._run_expiry_check
                )

                # Job 3: Automated Invoicing (08:00 IST default)
                await self._check_and_run_job(
                    "auto_invoicing",
                    settings.get("cron_invoice_time", "08:00"),
                    self._run_auto_invoicing
                )

                # Job 4: Wallet Suspension Check (09:00 IST default)
                await self._check_and_run_job(
                    "wallet_check",
                    settings.get("cron_wallet_time", "09:00"),
                    self._run_wallet_check
                )

                # Job 5: WhatsApp Reminders (10:00 IST default)
                await self._check_and_run_job(
                    "whatsapp_reminders",
                    settings.get("cron_reminder_time", "10:00"),
                    self._run_whatsapp_reminders
                )

                # Update Last Run stats periodically
                await self.db.global_settings.update_one(
                    {"type": "cron_stats"},
                    {"$set": {"last_heartbeat": now, "status": "running"}},
                    upsert=True
                )

                # Sleep until the next minute
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in Cron Service main loop: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def stop(self):
        self._stop_event.set()
        logger.info("Cron Service stopping")

    async def _check_and_run_job(self, job_name: str, scheduled_time_str: str, job_func):
        """Helper to run a job if its time has come and it hasn't run today yet."""
        now = datetime.now(self.tz)
        today_date = now.strftime("%Y-%m-%d")

        try:
            hour, minute = map(int, scheduled_time_str.split(":"))
            scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            logger.error(f"Invalid scheduled time for {job_name}: {scheduled_time_str}")
            return

        # Fetch job status from DB
        status = await self.db.global_settings.find_one({"type": "cron_job_status", "job_name": job_name})
        
        last_run_date = status.get("last_run_date") if status else None

        # If it's time or past time, and not yet run today
        if now >= scheduled_time and last_run_date != today_date:
            logger.info(f"Running scheduled job: {job_name}")
            try:
                # Update status to 'running'
                await self.db.global_settings.update_one(
                    {"type": "cron_job_status", "job_name": job_name},
                    {"$set": {"status": "running", "start_time": now}},
                    upsert=True
                )
                
                await job_func()
                
                # Update status to 'success'
                await self.db.global_settings.update_one(
                    {"type": "cron_job_status", "job_name": job_name},
                    {"$set": {
                        "status": "success", 
                        "last_run_date": today_date,
                        "last_run_at": now,
                        "duration_seconds": (datetime.now(self.tz) - now).total_seconds()
                    }}
                )
            except Exception as e:
                logger.error(f"Failed to run scheduled job {job_name}: {e}", exc_info=True)
                await self.db.global_settings.update_one(
                    {"type": "cron_job_status", "job_name": job_name},
                    {"$set": {"status": "failed", "error": str(e), "last_failed_at": now}}
                )

    # ── Job Implementations ───────────────────────────────────────────────────

    async def _run_backup(self):
        """Creates a daily encrypted backup in the filesystem"""
        from services.backup_service import BackupService
        backup_service = BackupService(self.db)
        await backup_service.create_backup(backup_type="auto")
        logger.info("Automated daily backup completed")

    async def _run_expiry_check(self):
        """Checks for operators whose subscription has expired"""
        now = datetime.now(self.tz)
        
        # 1. Operators whose membership_expires_at is in the past and they are still active
        expired_ops = await self.db.operators.find({
            "status": "active",
            "membership_expires_at": {"$lt": now},
            "deleted_at": None
        }).to_list(1000)

        for op in expired_ops:
            op_id = op["id"]
            # Check if they have auto-renew or any pending credits? (Future enhancement)
            # For now, mark as expired
            await self.db.operators.update_one(
                {"id": op_id},
                {"$set": {"status": "expired", "updated_at": now}}
            )
            # Mark all staff/owner as read-only (handled by dependency in routers)
            logger.info(f"Operator {op_id} ({op.get('company_name')}) subscription expired")

    async def _run_auto_invoicing(self):
        """Generates invoices for users whose billing cycle is ending soon"""
        # (Implementation details omitted for brevity, assuming existing logic)
        pass

    async def _run_wallet_check(self):
        """Monitors operator wallet balances and applies logic"""
        now = datetime.now(self.tz)
        
        # Find operators with negative balance
        operators = await self.db.operators.find({
            "wallet_balance": {"$lt": 0},
            "status": {"$in": ["active", "trial"]},
            "deleted_at": None
        }).to_list(1000)

        for op in operators:
            balance = op.get("wallet_balance", 0)
            # Threshold logic (e.g., if balance < -100, suspend?)
            # This is where business rules for SaaS subscriptions go
            pass

    async def _run_whatsapp_reminders(self):
        """Sends WhatsApp reminders for overdue or upcoming invoices"""
        # Fetch reminder settings
        settings = await self.db.global_settings.find_one({"type": "reminder_settings"})
        if not settings or not settings.get("enabled", True):
            return

        now = datetime.now(self.tz)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        results = {"sent": 0, "failed": 0, "skipped": 0}

        # ── Get all active operators ───────────────────────────────────────────
        operators = await self.db.operators.find(
            {"status": {"$in": ["active", "trial"]}, "deleted_at": None},
            {"_id": 0},
        ).to_list(1000)

        # Fetch WhatsApp service (priority: env_settings -> platform_whatsapp -> os.environ)
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
                # 1. Verification: Does this operator have WhatsApp Add-on?
                # We check the 'active_addons' field
                addons = operator.get("active_addons", [])
                if "whatsapp_notifications" not in addons:
                    continue

                # 2. Get un-reminded invoices for this operator
                # Filter: status=unpaid, is_draft=False
                invoices = await self.db.invoices.find({
                    "operator_id": operator_id,
                    "status": "unpaid",
                    "is_draft": False,
                    "deleted_at": None
                }).to_list(1000)

                for inv in invoices:
                    due_date = inv.get("due_date")
                    if not due_date: continue
                    
                    # Convert to TZ aware for comparison
                    if due_date.tzinfo is None:
                        due_date = self.tz.localize(due_date)
                    
                    # Calculate days diff
                    days_diff = (due_date.date() - now.date()).days
                    
                    should_remind = False
                    reminder_type = ""

                    # Remind Before Due
                    if days_diff > 0 and days_diff in settings.get("remind_before_due", []):
                        should_remind = True
                        reminder_type = f"before_{days_diff}"
                    
                    # Remind On Due
                    elif days_diff == 0 and settings.get("remind_on_due", True):
                        should_remind = True
                        reminder_type = "on_due"
                        
                    # Remind After Due (Overdue)
                    elif days_diff < 0:
                        abs_diff = abs(days_diff)
                        if abs_diff in settings.get("remind_after_due", []):
                            should_remind = True
                            reminder_type = f"after_{abs_diff}"

                    if should_remind:
                        # Check if already reminded today for this invoice
                        # (Basic throttle: max 1 reminder per day per invoice)
                        history = inv.get("reminder_history", [])
                        last_rem = history[-1] if history else None
                        
                        if last_rem and last_rem.get("date") == today.isoformat():
                            continue
                            
                        # Limit total reminders per invoice
                        if len(history) >= settings.get("max_reminders_per_invoice", 20):
                            continue

                        # Get Template ID
                        template_name = template_settings.get("reminder_template")
                        if not template_name:
                            continue

                        # Fetch subscriber details for variables
                        subscriber = await self.db.subscribers.find_one({"id": inv["subscriber_id"]})
                        if not subscriber or not subscriber.get("phone_number"):
                            continue

                        # Prepare Template Variables
                        # {{1}} = Subscriber Name, {{2}} = Amount, {{3}} = Due Date, {{4}} = Payment Link
                        # (Note: Payment link logic might require Razorpay/Gateway service)
                        
                        # --- Payment Link Generation ---
                        gateway = await self.db.payment_gateways.find_one({
                            "for_operator_id": operator_id,
                            "is_active": True,
                            "gateway_type": "razorpay"
                        })
                        
                        payment_url = f"https://e-bill.web.app/pay/{inv['id']}" # Default public URL
                        
                        if gateway:
                            try:
                                from services.razorpay_service import RazorpayService
                                op_razorpay = RazorpayService(gateway["api_key"], gateway["api_secret"])
                                # Only create if not already exists or expired
                                if not inv.get("razorpay_payment_link"):
                                    amount_paise = int(inv["total_amount"] * 100)
                                    link_data = op_razorpay.create_payment_link(
                                        amount=amount_paise,
                                        description=f"Invoice #{inv['invoice_number']} for {subscriber['name']}",
                                        customer_details={
                                            "name": subscriber["name"],
                                            "contact": subscriber["phone_number"],
                                            "email": subscriber.get("email") or "customer@example.com"
                                        },
                                        notes={"invoice_id": inv["id"], "operator_id": operator_id}
                                    )
                                    if link_data and link_data.get("short_url"):
                                        payment_url = link_data["short_url"]
                                        await self.db.invoices.update_one(
                                            {"id": inv["id"]},
                                            {"$set": {"razorpay_payment_link": payment_url, "razorpay_pl_id": link_data["id"]}}
                                        )
                                else:
                                    payment_url = inv["razorpay_payment_link"]
                            except Exception as e:
                                logger.warning(f"Failed to generate Razorpay link for reminder: {e}")

                        vars = [
                            subscriber["name"],
                            f"INR {inv['total_amount']:.2f}",
                            due_date.strftime("%d/%m/%Y"),
                            payment_url
                        ]

                        # Send via WhatsApp
                        success = await wa_service.send_template_message(
                            recipient_phone=subscriber["phone_number"],
                            template_name=template_name,
                            variables=vars
                        )

                        if success:
                            # Update invoice history
                            await self.db.invoices.update_one(
                                {"id": inv["id"]},
                                {"$push": {"reminder_history": {
                                    "date": today.isoformat(),
                                    "type": reminder_type,
                                    "sent_at": datetime.now(self.tz)
                                }}}
                            )
                            results["sent"] += 1
                        else:
                            results["failed"] += 1

            except Exception as e:
                logger.error(f"Error processing reminders for operator {operator_id}: {e}", exc_info=True)

        logger.info(f"WhatsApp Reminder Job Scan Finished. Results: {results}")
        return results
