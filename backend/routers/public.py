"""Public router: unauthenticated access to invoices for customers."""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from datetime import datetime, timezone
from typing import Optional
import os
import logging

from database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public", tags=["Public"])


# ── Addon helper (copied since we can't import with circular deps) ──────────
async def _has_addon(operator_id: str, addon_code: str) -> bool:
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        return False
    if addon_code in operator.get("active_addons", []):
        return True
    plan_id = operator.get("saas_plan_id")
    if plan_id:
        plan = await db.saas_plans.find_one({"id": plan_id, "deleted_at": None}, {"_id": 0})
        if plan and addon_code in plan.get("included_addons", []):
            return True
    return False


async def _get_payment_gateway_for_operator(operator_id: str):
    """Determine which payment gateway keys to use for an operator's subscriber payments."""
    has_custom_pg = await _has_addon(operator_id, "custom_payment_gateway")
    has_platform_pg = await _has_addon(operator_id, "payment_gateway")

    if has_custom_pg:
        gateway = await db.payment_gateways.find_one({"operator_id": operator_id}, {"_id": 0})
        if gateway and gateway.get("is_active"):
            return gateway
    elif has_platform_pg:
        gateway = await db.payment_gateways.find_one({"is_platform_gateway": True, "is_active": True}, {"_id": 0})
        if gateway:
            return gateway

    return None


# ── GET /public/invoice/{invoice_id} ─────────────────────────────────────────
@router.get("/invoice/{invoice_id}")
async def get_public_invoice(invoice_id: str):
    """Get invoice details for public viewing (no auth required)."""
    invoice = await db.invoices.find_one({"id": invoice_id, "deleted_at": None}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    operator_id = invoice["operator_id"]

    # Fetch operator info
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Business not found")

    # Fetch subscriber info
    subscriber = await db.subscribers.find_one(
        {"id": invoice["subscriber_id"], "deleted_at": None}, {"_id": 0}
    )

    # Fetch plan info
    plan = await db.operator_plans.find_one({"id": invoice["plan_id"], "deleted_at": None}, {"_id": 0})

    # Fetch invoice settings for operator
    inv_settings = await db.invoice_settings.find_one(
        {"operator_id": operator_id}, {"_id": 0}
    ) or {}

    # Check if payment gateway is available
    gateway = await _get_payment_gateway_for_operator(operator_id)
    has_payment = gateway is not None
    razorpay_key = gateway["api_key"] if gateway else None

    return {
        "invoice": {
            "id": invoice["id"],
            "invoice_number": invoice.get("invoice_number", ""),
            "subscriber_id": invoice["subscriber_id"],
            "subscriber_name": invoice.get("subscriber_name", ""),
            "plan_id": invoice["plan_id"],
            "plan_name": invoice.get("plan_name", ""),
            "base_amount": invoice["base_amount"],
            "discount": invoice.get("discount", 0),
            "tax_amount": invoice.get("tax_amount", 0),
            "final_amount": invoice["final_amount"],
            "service_start_date": invoice["service_start_date"],
            "service_end_date": invoice["service_end_date"],
            "due_date": invoice["due_date"],
            "status": invoice["status"],
            "payment_link": invoice.get("payment_link"),
            "created_at": invoice["created_at"],
        },
        "operator": {
            "company_name": operator.get("company_name", ""),
            "owner_name": operator.get("owner_name", ""),
            "gst_number": operator.get("gst_number"),
            "charge_gst": operator.get("charge_gst", False),
            "phone": operator.get("phone", ""),
            "email": operator.get("email", ""),
            "bank_account_name": operator.get("bank_account_name"),
            "bank_account_number": operator.get("bank_account_number"),
            "bank_ifsc": operator.get("bank_ifsc"),
            "bank_name": operator.get("bank_name"),
        },
        "subscriber": {
            "name": subscriber.get("name", "") if subscriber else "",
            "email": subscriber.get("email", "") if subscriber else "",
            "phone": subscriber.get("whatsapp_number", "") if subscriber else "",
            "address": subscriber.get("address", "") if subscriber else "",
        } if subscriber else None,
        "plan": {
            "name": plan.get("name", "") if plan else "",
            "tax_percentage": plan.get("tax_percentage", 0) if plan else 0,
            "tax_type": plan.get("tax_type", "none") if plan else "none",
            "validity": plan.get("validity", "") if plan else "",
        } if plan else None,
        "invoice_settings": {
            "company_name": inv_settings.get("company_name", operator.get("company_name", "")),
            "invoice_prefix": inv_settings.get("invoice_prefix", "INV"),
            "show_gst": inv_settings.get("show_gst", True),
            "invoice_footer": inv_settings.get("invoice_footer"),
            "terms_conditions": inv_settings.get("terms_conditions"),
            "invoice_template": inv_settings.get("invoice_template", "classic"),
        },
        "payment": {
            "enabled": has_payment,
            "razorpay_key": razorpay_key,
        },
    }


# ── POST /public/invoice/{invoice_id}/create-payment-order ───────────────────
@router.post("/invoice/{invoice_id}/create-payment-order")
async def create_public_payment_order(invoice_id: str):
    """Create a Razorpay order for a public invoice payment (no auth)."""
    from services.razorpay_service import RazorpayService

    invoice = await db.invoices.find_one({"id": invoice_id, "deleted_at": None}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice["status"] == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already paid")

    if invoice["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Invoice is cancelled")

    operator_id = invoice["operator_id"]
    gateway = await _get_payment_gateway_for_operator(operator_id)
    if not gateway:
        raise HTTPException(status_code=400, detail="Payment gateway not available for this invoice")

    subscriber = await db.subscribers.find_one(
        {"id": invoice["subscriber_id"], "deleted_at": None}, {"_id": 0}
    )
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})

    try:
        rz = RazorpayService(gateway["api_key"], gateway["api_secret"])
        order = rz.create_order(
            amount=invoice["final_amount"],
            currency="INR",
            receipt=f"inv_{invoice['invoice_number']}",
            notes={
                "invoice_id": invoice["id"],
                "invoice_number": invoice["invoice_number"],
                "subscriber_name": invoice.get("subscriber_name", ""),
                "type": "public_invoice_payment",
            },
        )
        return {
            "razorpay_order_id": order["id"],
            "razorpay_key": gateway["api_key"],
            "amount": invoice["final_amount"],
            "currency": "INR",
            "invoice_number": invoice["invoice_number"],
            "operator_name": operator.get("company_name", "") if operator else "",
            "subscriber_name": subscriber.get("name", "") if subscriber else "",
            "subscriber_email": subscriber.get("email", "") if subscriber else "",
            "subscriber_phone": subscriber.get("whatsapp_number", "") if subscriber else "",
        }
    except Exception as e:
        logger.error(f"Public payment order creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create payment order: {e}")


# ── POST /public/invoice/{invoice_id}/verify-payment ─────────────────────────
@router.post("/invoice/{invoice_id}/verify-payment")
async def verify_public_payment(
    invoice_id: str,
    razorpay_order_id: str = Query(...),
    razorpay_payment_id: str = Query(...),
    razorpay_signature: str = Query(...),
):
    """Verify Razorpay payment and mark invoice as paid (no auth)."""
    from services.razorpay_service import RazorpayService

    invoice = await db.invoices.find_one({"id": invoice_id, "deleted_at": None}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice["status"] == "paid":
        return {"message": "Invoice already paid", "status": "paid"}

    operator_id = invoice["operator_id"]
    gateway = await _get_payment_gateway_for_operator(operator_id)
    if not gateway:
        raise HTTPException(status_code=400, detail="Payment gateway not available")

    rz = RazorpayService(gateway["api_key"], gateway["api_secret"])
    if not rz.verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment verification failed")

    now = datetime.now(timezone.utc)
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "status": "paid",
            "payment_id": razorpay_payment_id,
            "razorpay_order_id": razorpay_order_id,
            "paid_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }}
    )

    return {"message": "Payment successful", "status": "paid"}


# ── GET /public/invoice/{invoice_id}/pdf ─────────────────────────────────────
@router.get("/invoice/{invoice_id}/pdf")
async def get_public_invoice_pdf(invoice_id: str):
    """Download invoice PDF without authentication."""
    from services.pdf_service import InvoicePDFService
    from services.razorpay_service import RazorpayService

    invoice = await db.invoices.find_one({"id": invoice_id, "deleted_at": None}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    operator_id = invoice["operator_id"]
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    subscriber = await db.subscribers.find_one(
        {"id": invoice["subscriber_id"], "deleted_at": None}, {"_id": 0}
    )
    plan = await db.operator_plans.find_one({"id": invoice["plan_id"], "deleted_at": None}, {"_id": 0})

    qr_code = None
    if invoice.get("payment_link"):
        gateway = await _get_payment_gateway_for_operator(operator_id)
        if gateway:
            try:
                rz = RazorpayService(gateway["api_key"], gateway["api_secret"])
                qr_code = rz.generate_qr_code(invoice["payment_link"])
            except Exception:
                pass

    inv_settings = await db.invoice_settings.find_one(
        {"operator_id": operator_id}, {"_id": 0}
    ) or {}
    template = inv_settings.get("invoice_template", "classic")

    pdf_service = InvoicePDFService()
    pdf_bytes = pdf_service.generate_invoice_pdf(
        invoice_data=invoice,
        operator_data={**(operator or {}), **(inv_settings or {})},
        subscriber_data=subscriber or {},
        plan_data=plan or {},
        qr_code_base64=qr_code,
        template=template,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Invoice_{invoice.get('invoice_number', invoice_id)}.pdf"},
    )
