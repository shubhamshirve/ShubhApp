from typing import Any, Dict, Optional
from urllib.parse import urlparse

from fastapi import HTTPException, Request

from database import db


DEFAULT_VISIBLE_FIELDS = {
    "show_logo": True,
    "show_company_address": True,
    "show_company_phone": True,
    "show_company_email": True,
    "show_bank_details": True,
    "show_subscriber_phone": True,
    "show_subscriber_email": True,
    "show_subscriber_address": True,
    "show_gst_number": True,
}


def normalize_invoice_settings(settings: Optional[Dict[str, Any]], operator: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    operator = operator or {}
    settings = settings or {}
    visible_fields = {**DEFAULT_VISIBLE_FIELDS, **(settings.get("visible_fields") or {})}
    operator_address = (
        operator.get("company_address")
        or operator.get("address")
        or ""
    )
    return {
        "company_name": settings.get("company_name") or operator.get("company_name", ""),
        "company_address": settings.get("company_address") or operator_address,
        "company_phone": settings.get("company_phone") or operator.get("phone", ""),
        "company_email": settings.get("company_email") or operator.get("email", ""),
        "logo_url": settings.get("logo_url"),
        "invoice_prefix": settings.get("invoice_prefix", "INV"),
        "show_gst": settings.get("show_gst", True),
        "accept_payment_gateway": settings.get("accept_payment_gateway", True),
        "accept_upi": settings.get("accept_upi", False),
        "allow_partial_payments": settings.get("allow_partial_payments", True),
        "invoice_footer": settings.get("invoice_footer"),
        "terms_conditions": settings.get("terms_conditions"),
        "invoice_template": settings.get("invoice_template", "classic"),
        "visible_fields": visible_fields,
    }


def build_public_invoice_path(invoice: Dict[str, Any]) -> str:
    return f"/invoice/{invoice.get('invoice_number') or invoice['id']}"


def build_public_invoice_url(request: Optional[Request], invoice: Dict[str, Any]) -> Optional[str]:
    if not request:
        return None
    origin = request.headers.get("origin") or request.headers.get("referer", "")
    if origin:
        parsed = urlparse(origin)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
    else:
        base_url = str(request.base_url).rstrip("/")
    if not base_url:
        return None
    return f"{base_url}{build_public_invoice_path(invoice)}"


async def build_public_invoice_url_from_env(invoice: Dict[str, Any]) -> Optional[str]:
    """Build public invoice URL using api_base_url from env settings (for use in background jobs/cron)."""
    try:
        from services.env_service import get_env_setting
        base_url = await get_env_setting("api_base_url")
        if not base_url:
            return None
        base_url = base_url.rstrip("/")
        return f"{base_url}{build_public_invoice_path(invoice)}"
    except Exception:
        return None


async def resolve_invoice_reference(invoice_ref: str, operator_id: Optional[str] = None) -> Dict[str, Any]:
    query = {"deleted_at": None}
    if operator_id:
        query["operator_id"] = operator_id

    invoice = await db.invoices.find_one({**query, "invoice_number": invoice_ref}, {"_id": 0})
    if not invoice:
        invoice = await db.invoices.find_one({**query, "id": invoice_ref}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


async def get_invoice_view_context(invoice_ref: str, operator_id: Optional[str] = None) -> Dict[str, Any]:
    invoice = await resolve_invoice_reference(invoice_ref, operator_id=operator_id)
    operator = await db.operators.find_one({"id": invoice["operator_id"], "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Business not found")

    subscriber = await db.subscribers.find_one(
        {"id": invoice["subscriber_id"], "deleted_at": None}, {"_id": 0}
    )
    plan_id = invoice.get("plan_id")
    if not plan_id and invoice.get("line_items"):
        plan_id = invoice["line_items"][0].get("plan_id")
    
    plan = None
    if plan_id:
        plan = await db.operator_plans.find_one({"id": plan_id, "deleted_at": None}, {"_id": 0})
    raw_settings = await db.invoice_settings.find_one({"operator_id": invoice["operator_id"]}, {"_id": 0}) or {}
    invoice_settings = normalize_invoice_settings(raw_settings, operator)
    return {
        "invoice": invoice,
        "operator": operator,
        "subscriber": subscriber or {},
        "plan": plan or {},
        "invoice_settings": invoice_settings,
    }
