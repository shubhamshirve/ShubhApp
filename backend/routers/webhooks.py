"""Webhook handlers (Razorpay, etc.)."""
from fastapi import APIRouter, Request, Query, Response
from datetime import datetime, timezone
import json
import logging

from database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ─── WhatsApp Cloud API status webhook ────────────────────────────────────────

# Order in which delivery_status can move forward. We never downgrade.
_STATUS_RANK = {"sent": 1, "delivered": 2, "read": 3, "failed": 4}


@router.get("/whatsapp")
async def whatsapp_webhook_verify(
    request: Request,
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
):
    """Meta webhook verification handshake. Returns the challenge string when token matches."""
    config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0}) or {}
    expected = config.get("webhook_verify_token") or ""
    if hub_mode == "subscribe" and hub_verify_token and hub_verify_token == expected:
        # Meta requires raw text/plain echo of the challenge
        return Response(content=hub_challenge or "", media_type="text/plain")
    logger.warning("WhatsApp webhook verify failed: mode=%s token_match=%s", hub_mode, hub_verify_token == expected)
    return Response(content="forbidden", status_code=403, media_type="text/plain")


@router.post("/whatsapp")
async def whatsapp_webhook_event(request: Request):
    """
    Receive WhatsApp Cloud API status callbacks (sent / delivered / read / failed)
    and update the matching whatsapp_message_logs document by message_id.
    Always returns 200 so Meta does not retry indefinitely.
    """
    try:
        body = await request.body()
        payload = json.loads(body or b"{}")
    except Exception as e:
        logger.warning(f"WhatsApp webhook: invalid JSON ({e})")
        return {"status": "ignored"}

    try:
        for entry in payload.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                statuses = value.get("statuses") or []
                for st in statuses:
                    await _apply_whatsapp_status_event(st)
    except Exception as e:
        logger.error(f"WhatsApp webhook processing error: {e}", exc_info=True)
    return {"status": "ok"}


async def _apply_whatsapp_status_event(st: dict) -> None:
    """Update one whatsapp_message_logs row for a single status event."""
    msg_id = st.get("id") or ""
    new_status = (st.get("status") or "").lower()
    if not msg_id or new_status not in _STATUS_RANK:
        return

    ts_raw = st.get("timestamp")
    try:
        event_dt = datetime.fromtimestamp(int(ts_raw), tz=timezone.utc) if ts_raw else datetime.now(timezone.utc)
    except (TypeError, ValueError):
        event_dt = datetime.now(timezone.utc)
    event_iso = event_dt.isoformat()

    err_obj = (st.get("errors") or [{}])[0] if st.get("errors") else {}
    err_code = err_obj.get("code")
    err_title = err_obj.get("title") or err_obj.get("message")
    err_detail = (err_obj.get("error_data") or {}).get("details") or ""

    existing = await db.whatsapp_message_logs.find_one({"message_id": msg_id}, {"_id": 0})
    event_record = {
        "status": new_status,
        "timestamp": event_iso,
        "source": "webhook",
        **({"error_code": err_code} if err_code is not None else {}),
        **({"error_title": err_title} if err_title else {}),
        **({"error_detail": err_detail} if err_detail else {}),
    }

    if not existing:
        # Orphan event — create a placeholder row so the admin still sees it.
        from utils import generate_id
        orphan = {
            "id": generate_id(),
            "operator_id": None,
            "template_name": "",
            "template_category": "",
            "recipient_phone": st.get("recipient_id") or "",
            "status": "sent" if new_status != "failed" else "failed",
            "delivery_status": new_status,
            "message_id": msg_id,
            "wa_id": st.get("recipient_id") or "",
            "error_message": err_title or "",
            "error_code": err_code,
            "error_title": err_title,
            "delivered_at": event_iso if new_status == "delivered" else None,
            "read_at": event_iso if new_status == "read" else None,
            "failed_at": event_iso if new_status == "failed" else None,
            "events": [event_record],
            "invoice_id": None,
            "invoice_number": "",
            "trigger": "webhook_orphan",
            "created_at": event_iso,
        }
        await db.whatsapp_message_logs.insert_one(orphan)
        return

    # Only move delivery_status forward (sent → delivered → read; failed always wins).
    current_rank = _STATUS_RANK.get(existing.get("delivery_status") or "sent", 1)
    incoming_rank = _STATUS_RANK[new_status]
    set_doc: dict = {}
    if new_status == "failed" or incoming_rank > current_rank:
        set_doc["delivery_status"] = new_status
    if new_status == "delivered" and not existing.get("delivered_at"):
        set_doc["delivered_at"] = event_iso
    if new_status == "read":
        if not existing.get("delivered_at"):
            # Some carriers skip 'delivered'; mark it implicitly.
            set_doc["delivered_at"] = event_iso
        set_doc["read_at"] = event_iso
    if new_status == "failed":
        set_doc["failed_at"] = event_iso
        if err_code is not None:
            set_doc["error_code"] = err_code
        if err_title:
            set_doc["error_title"] = err_title
            # Keep error_message readable — combine title + detail if present.
            set_doc["error_message"] = (
                f"{err_title}: {err_detail}" if err_detail else err_title
            )

    update_ops = {"$push": {"events": event_record}}
    if set_doc:
        update_ops["$set"] = set_doc
    await db.whatsapp_message_logs.update_one({"message_id": msg_id}, update_ops)


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
