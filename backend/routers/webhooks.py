"""Webhook handlers (Razorpay, etc.)."""
from fastapi import APIRouter, Request
from datetime import datetime, timezone
import json
import logging

from database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(request: Request):
    """Handle Razorpay payment webhooks."""
    try:
        body = await request.body()
        payload = json.loads(body)
        event = payload.get("event", "")
        logger.info(f"Razorpay webhook: {event}")

        if event == "payment_link.paid":
            payment_link = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
            payment_link_id = payment_link.get("id")
            invoice = await db.invoices.find_one({"payment_link_id": payment_link_id, "deleted_at": None}, {"_id": 0})
            if invoice:
                now = datetime.now(timezone.utc)
                payment_id = (
                    payment_link.get("payments", [{}])[0].get("payment_id")
                    if payment_link.get("payments") else None
                )
                await db.invoices.update_one(
                    {"id": invoice["id"]},
                    {"$set": {"status": "paid", "payment_id": payment_id, "updated_at": now.isoformat()}}
                )
                logger.info(f"Invoice {invoice['invoice_number']} marked as paid")

        elif event == "payment.captured":
            payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
            invoice_number = payment.get("notes", {}).get("invoice_number")
            if invoice_number:
                await db.invoices.update_one(
                    {"invoice_number": invoice_number, "deleted_at": None},
                    {"$set": {"status": "paid", "payment_id": payment.get("id"),
                              "updated_at": datetime.now(timezone.utc).isoformat()}}
                )

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}
