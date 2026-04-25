"""
Shared invoice and WhatsApp helper functions.
"""
from datetime import datetime, timezone
from fastapi import HTTPException

from database import db
from models import InvoiceCreate, InvoiceUpdate

_VALIDITY_MONTHS = {"monthly": 1, "quarterly": 3, "half_yearly": 6, "yearly": 12}


def _price_for_tenure(base_price: float, base_validity: str, selected_validity: str) -> float:
    """Scale plan base_price to the selected tenure."""
    base_m = _VALIDITY_MONTHS.get(base_validity, 1)
    sel_m = _VALIDITY_MONTHS.get(selected_validity, base_m)
    if base_m == 0:
        return round(base_price, 2)
    return round(base_price / base_m * sel_m, 2)


# ─── WhatsApp config helpers ──────────────────────────────────────────────────

async def get_platform_whatsapp_config():
    """Return the global platform WhatsApp Cloud API config, or None if not set."""
    config = await db.global_settings.find_one({"type": "platform_whatsapp"}, {"_id": 0})
    if not config or not config.get("access_token"):
        return None
    return config


async def get_whatsapp_template_settings():
    """Return template assignment settings from admin config."""
    settings = await db.global_settings.find_one(
        {"type": "whatsapp_template_settings"}, {"_id": 0}
    )
    return settings or {}


# ─── Invoice payload builder ──────────────────────────────────────────────────

async def build_invoice_payload(operator_id: str, data: InvoiceCreate | InvoiceUpdate):
    """Build and validate the common invoice payload dict for create / update flows."""
    subscriber = await db.subscribers.find_one(
        {"id": data.subscriber_id, "operator_id": operator_id, "deleted_at": None}, {"_id": 0}
    )
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    can_charge_gst = operator.get("charge_gst") and operator.get("gst_number")

    total_base = 0.0
    total_discount = 0.0
    total_tax = 0.0
    total_final = 0.0
    line_items = []

    for item in data.line_items:
        # Handle custom items (no plan linked)
        if item.is_custom:
            if not item.description:
                raise HTTPException(status_code=400, detail="Custom items require a description")

            final_amount = item.base_amount - item.discount
            enriched_item = item.model_dump()
            enriched_item["plan_name"] = item.description  # Use description as plan_name for display
            enriched_item["plan_description"] = None
            enriched_item["tax_amount"] = 0.0
            enriched_item["final_amount"] = round(final_amount, 2)
            enriched_item["service_start_date"] = item.service_start_date.isoformat()
            enriched_item["service_end_date"] = item.service_end_date.isoformat()
            line_items.append(enriched_item)

            total_base += item.base_amount
            total_discount += item.discount
            total_final += final_amount
            continue

        # Standard plan-based item
        if not item.plan_id:
            raise HTTPException(status_code=400, detail="Plan-based items require a plan_id")

        plan = await db.operator_plans.find_one({"id": item.plan_id, "deleted_at": None}, {"_id": 0})
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {item.plan_id} not found")

        # Auto-calculate base_amount when selected_validity is provided
        effective_validity = item.selected_validity or plan.get("validity", "monthly")
        if item.selected_validity and item.selected_validity != plan.get("validity"):
            computed_price = _price_for_tenure(plan["price"], plan.get("validity", "monthly"), item.selected_validity)
        else:
            computed_price = item.base_amount  # use what the client sent (may already be correct)

        tax_amount = 0.0
        if can_charge_gst and plan.get("tax_percentage", 0) > 0:
            taxable = computed_price - item.discount
            if plan.get("tax_type") == "exclusive":
                tax_amount = taxable * (plan["tax_percentage"] / 100)
            elif plan.get("tax_type") == "inclusive":
                tax_amount = taxable - (taxable / (1 + plan["tax_percentage"] / 100))

        final_amount = computed_price - item.discount + (
            tax_amount if plan.get("tax_type") == "exclusive" else 0
        )

        enriched_item = item.model_dump()
        enriched_item["base_amount"] = round(computed_price, 2)
        enriched_item["plan_name"] = plan["name"]
        enriched_item["plan_description"] = plan.get("description")
        enriched_item["selected_validity"] = effective_validity
        enriched_item["tax_amount"] = round(tax_amount, 2)
        enriched_item["final_amount"] = round(final_amount, 2)
        enriched_item["service_start_date"] = item.service_start_date.isoformat()
        enriched_item["service_end_date"] = item.service_end_date.isoformat()
        line_items.append(enriched_item)

        total_base += computed_price
        total_discount += item.discount
        total_tax += tax_amount
        total_final += final_amount

    return {
        "subscriber": subscriber,
        "line_items": line_items,
        "base_amount": round(total_base, 2),
        "discount": round(total_discount, 2),
        "tax_amount": round(total_tax, 2),
        "final_amount": round(total_final, 2),
        "due_date": data.due_date.isoformat(),
    }


# ─── Date parsing helper ──────────────────────────────────────────────────────

def parse_bulk_invoice_date(value: str, field_name: str) -> datetime:
    """
    Parse a date string in various common formats used in bulk CSV uploads.
    Raises ValueError with a descriptive message on failure.
    """
    raw = (value or "").strip()
    if not raw:
        raise ValueError(f"{field_name} is required")

    normalized = raw.replace("T", " ")
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(
        f"Invalid date format for {field_name}: '{value}'. "
        "Expected formats: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY"
    )
