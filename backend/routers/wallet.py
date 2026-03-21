"""Wallet router: operator wallet management, topup, referral system."""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
import math
import os
import logging

from database import db
from utils import generate_id
from dependencies import require_operator, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wallet"])


# ─── Wallet Helpers (also used by operator.py, cron) ─────────────────────────

async def get_or_create_wallet(operator_id: str) -> dict:
    """Get or create wallet for operator."""
    wallet = await db.operator_wallets.find_one({"operator_id": operator_id}, {"_id": 0})
    if not wallet:
        now = datetime.now(timezone.utc)
        wallet = {
            "operator_id": operator_id,
            "balance": 0.0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        await db.operator_wallets.insert_one(wallet)
        wallet = await db.operator_wallets.find_one({"operator_id": operator_id}, {"_id": 0})
    return wallet


async def credit_wallet(
    operator_id: str, amount: float, description: str,
    reference_id: str = None, tx_type: str = "credit"
) -> float:
    """Credit wallet and return new balance."""
    wallet = await get_or_create_wallet(operator_id)
    new_balance = round(wallet.get("balance", 0) + amount, 2)
    now = datetime.now(timezone.utc)
    await db.operator_wallets.update_one(
        {"operator_id": operator_id},
        {"$set": {"balance": new_balance, "updated_at": now.isoformat()}},
    )
    await db.wallet_transactions.insert_one({
        "id": generate_id(),
        "operator_id": operator_id,
        "type": tx_type,
        "amount": amount,
        "balance_after": new_balance,
        "description": description,
        "reference_id": reference_id,
        "created_at": now.isoformat(),
    })
    return new_balance


async def deduct_wallet(
    operator_id: str, amount: float, description: str, reference_id: str = None
) -> tuple:
    """Deduct from wallet. Returns (new_balance, became_suspended)."""
    wallet = await get_or_create_wallet(operator_id)
    new_balance = round(wallet.get("balance", 0) - amount, 2)
    now = datetime.now(timezone.utc)
    await db.operator_wallets.update_one(
        {"operator_id": operator_id},
        {"$set": {"balance": new_balance, "updated_at": now.isoformat()}},
    )
    await db.wallet_transactions.insert_one({
        "id": generate_id(),
        "operator_id": operator_id,
        "type": "deduction",
        "amount": -amount,
        "balance_after": new_balance,
        "description": description,
        "reference_id": reference_id,
        "created_at": now.isoformat(),
    })

    # Suspend operator if balance drops below 100
    became_suspended = False
    if new_balance < 100:
        operator = await db.operators.find_one(
            {"id": operator_id, "deleted_at": None}, {"_id": 0}
        )
        if operator and not operator.get("wallet_suspended"):
            await db.operators.update_one(
                {"id": operator_id},
                {"$set": {"wallet_suspended": True, "is_read_only": True, "updated_at": now.isoformat()}},
            )
            became_suspended = True

    return new_balance, became_suspended


async def deduct_wallet_for_invoice(operator_id: str, invoice_id: str) -> float:
    """Deduct per_invoice_price from operator wallet for invoice generation."""
    # Get operator's current plan to find per_invoice_price
    per_invoice_price = 10.0  # default fallback
    try:
        operator = await db.operators.find_one({"id": operator_id}, {"_id": 0, "saas_plan_id": 1})
        if operator and operator.get("saas_plan_id"):
            plan = await db.saas_plans.find_one(
                {"id": operator["saas_plan_id"]}, {"_id": 0, "per_invoice_price": 1}
            )
            if plan and plan.get("per_invoice_price") is not None:
                per_invoice_price = float(plan["per_invoice_price"])
    except Exception:
        pass

    new_balance, _ = await deduct_wallet(
        operator_id, per_invoice_price,
        f"Invoice generation charge (₹{per_invoice_price})",
        reference_id=invoice_id,
    )
    return new_balance


def is_referral_reward_active(operator: dict) -> bool:
    """Check if referral reward period is still active (3 months from registration)."""
    if not operator.get("referred_by_code"):
        return False
    created_at = operator.get("created_at")
    if not created_at:
        return False
    reg_date = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
    if reg_date.tzinfo is None:
        reg_date = reg_date.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < (reg_date + timedelta(days=90))


async def apply_referral_reward(operator_id: str, payment_amount: float, payment_ref: str):
    """Give 5% referral reward to referrer if within 3-month window."""
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator or not is_referral_reward_active(operator):
        return
    referrer = await db.operators.find_one(
        {"referral_code": operator["referred_by_code"], "deleted_at": None}, {"_id": 0}
    )
    if referrer:
        reward = round(payment_amount * 0.05, 2)
        await credit_wallet(
            referrer["id"], reward,
            f"Referral reward 5% from {operator.get('company_name', 'operator')}",
            reference_id=payment_ref,
            tx_type="referral_reward",
        )


async def get_platform_gst_rate() -> float:
    """Read platform GST rate from admin settings with a safe fallback."""
    settings = await db.global_settings.find_one({"type": "platform"}, {"_id": 0, "gst_rate": 1})
    try:
        return float((settings or {}).get("gst_rate", 18))
    except (TypeError, ValueError):
        return 18.0


# ─── Operator Wallet Endpoints ─────────────────────────────────────────────────

@router.get("/operator/wallet")
async def get_wallet(current_user: dict = Depends(require_operator)):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin doesn't have a wallet")
    operator_id = current_user["operator_id"]
    wallet = await get_or_create_wallet(operator_id)
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    return {
        "balance": wallet.get("balance", 0),
        "operator_id": operator_id,
        "referral_code": operator.get("referral_code", ""),
        "referred_by_code": operator.get("referred_by_code", ""),
        "referral_discount_used": operator.get("referral_discount_used", False),
        "referral_reward_active": is_referral_reward_active(operator) if operator else False,
        "wallet_suspended": operator.get("wallet_suspended", False) if operator else False,
        "updated_at": wallet.get("updated_at"),
    }


@router.get("/operator/wallet/transactions")
async def get_wallet_transactions(
    skip: int = 0, limit: int = 50,
    current_user: dict = Depends(require_operator),
):
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin doesn't have a wallet")
    txs = await db.wallet_transactions.find(
        {"operator_id": current_user["operator_id"]}, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.wallet_transactions.count_documents({"operator_id": current_user["operator_id"]})
    return {"transactions": txs, "total": total}


@router.post("/operator/wallet/topup/create-order")
async def create_topup_order(
    amount: float,
    current_user: dict = Depends(require_operator),
):
    """Create Razorpay order for wallet topup."""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin doesn't have a wallet")
    if amount < 100:
        raise HTTPException(status_code=400, detail="Minimum topup amount is Rs.100")
    if amount > 50000:
        raise HTTPException(status_code=400, detail="Maximum topup amount is Rs.50,000")

    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    platform_gw = await db.payment_gateways.find_one({"is_platform_gateway": True, "is_active": True}, {"_id": 0})
    razorpay_key = platform_gw["api_key"] if platform_gw else os.environ.get("RAZORPAY_KEY_ID")
    razorpay_secret = platform_gw["api_secret"] if platform_gw else os.environ.get("RAZORPAY_KEY_SECRET")
    if not razorpay_key or not razorpay_secret:
        raise HTTPException(status_code=500, detail="Payment gateway not configured. Contact admin.")

    from services.razorpay_service import RazorpayService
    rz = RazorpayService(razorpay_key, razorpay_secret)
    order_id = generate_id()
    gst_rate = await get_platform_gst_rate()
    base_amount = round(amount, 2)
    gst_amount = round(base_amount * gst_rate / 100, 2)
    exact_total = round(base_amount + gst_amount, 2)
    rounded_amount = math.floor(exact_total + 0.5)
    rounding_diff = round(rounded_amount - exact_total, 2)

    order = rz.create_order(
        amount=rounded_amount,
        receipt=f"WALLET-{order_id[:8]}",
        notes={"type": "wallet_topup", "operator_id": operator["id"], "internal_order_id": order_id},
    )

    now = datetime.now(timezone.utc)
    await db.checkout_orders.insert_one({
        "id": order_id,
        "razorpay_order_id": order["id"],
        "operator_id": operator["id"],
        "item_type": "wallet_topup",
        "base_amount": base_amount,
        "gst_rate": gst_rate,
        "gst_amount": gst_amount,
        "exact_total": exact_total,
        "rounding_diff": rounding_diff,
        "total_amount": rounded_amount,
        "status": "created",
        "created_at": now.isoformat(),
        "deleted_at": None,
    })

    settings = await db.global_settings.find_one({"type": "platform"}, {"_id": 0})
    platform_name = (settings or {}).get("platform_name", "E-Bill")
    return {
        "razorpay_order_id": order["id"],
        "razorpay_key": razorpay_key,
        "amount": rounded_amount * 100,
        "currency": "INR",
        "name": platform_name,
        "description": f"Wallet Topup - Rs.{base_amount}",
        "wallet_credit_amount": base_amount,
        "gst_rate": gst_rate,
        "gst_amount": gst_amount,
        "exact_total": exact_total,
        "rounding_diff": rounding_diff,
        "total_amount": rounded_amount,
        "prefill": {
            "name": operator.get("owner_name", ""),
            "email": operator.get("email", ""),
            "contact": operator.get("phone", ""),
        },
    }


@router.post("/operator/wallet/topup/verify")
async def verify_topup_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    current_user: dict = Depends(require_operator),
):
    """Verify wallet topup and credit wallet."""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin doesn't have a wallet")

    platform_gw = await db.payment_gateways.find_one({"is_platform_gateway": True, "is_active": True}, {"_id": 0})
    razorpay_key = platform_gw["api_key"] if platform_gw else os.environ.get("RAZORPAY_KEY_ID")
    razorpay_secret = platform_gw["api_secret"] if platform_gw else os.environ.get("RAZORPAY_KEY_SECRET")

    from services.razorpay_service import RazorpayService
    rz = RazorpayService(razorpay_key, razorpay_secret)
    if not rz.verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment verification failed")

    order = await db.checkout_orders.find_one(
        {"razorpay_order_id": razorpay_order_id, "operator_id": current_user["operator_id"]}, {"_id": 0}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] == "paid":
        raise HTTPException(status_code=400, detail="Payment already processed")

    credited_amount = round(float(order.get("base_amount", order["total_amount"])), 2)
    gst_amount = round(float(order.get("gst_amount", 0)), 2)
    paid_amount = round(float(order.get("total_amount", 0)), 2)
    gst_rate = round(float(order.get("gst_rate", 18)), 2)
    operator_id = current_user["operator_id"]
    now = datetime.now(timezone.utc)

    # Credit wallet
    new_balance = await credit_wallet(
        operator_id, credited_amount,
        f"Wallet Topup (Ref: {razorpay_payment_id[-8:]})",
        reference_id=razorpay_payment_id,
        tx_type="topup",
    )

    # Resume if wallet was suspended
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if operator and operator.get("wallet_suspended") and new_balance >= 100:
        await db.operators.update_one(
            {"id": operator_id},
            {"$set": {"wallet_suspended": False, "is_read_only": False, "updated_at": now.isoformat()}},
        )

    # Referral reward to referrer
    await apply_referral_reward(operator_id, credited_amount, razorpay_payment_id)

    await db.checkout_orders.update_one(
        {"razorpay_order_id": razorpay_order_id},
        {"$set": {"status": "paid", "razorpay_payment_id": razorpay_payment_id, "paid_at": now.isoformat()}},
    )

    return {
        "status": "success",
        "message": f"Wallet credited with Rs.{credited_amount:.2f}",
        "credited_amount": credited_amount,
        "gst_rate": gst_rate,
        "gst_amount": gst_amount,
        "paid_amount": paid_amount,
        "new_balance": new_balance,
    }


# ─── Admin Wallet Endpoints ────────────────────────────────────────────────────

@router.get("/admin/wallets")
async def admin_get_all_wallets(
    skip: int = 0, limit: int = 50,
    current_user: dict = Depends(require_admin),
):
    """Admin: view all operator wallets sorted by lowest balance."""
    wallets = await db.operator_wallets.find({}, {"_id": 0}).sort("balance", 1).skip(skip).limit(limit).to_list(limit)
    total = await db.operator_wallets.count_documents({})
    enriched = []
    for w in wallets:
        op = await db.operators.find_one(
            {"id": w["operator_id"]}, {"_id": 0, "company_name": 1, "status": 1, "wallet_suspended": 1}
        )
        enriched.append({
            **w,
            "company_name": (op or {}).get("company_name", "Unknown"),
            "operator_status": (op or {}).get("status", "unknown"),
            "wallet_suspended": (op or {}).get("wallet_suspended", False),
        })
    return {"wallets": enriched, "total": total}


@router.get("/admin/wallets/{operator_id}/transactions")
async def admin_get_wallet_transactions(
    operator_id: str,
    skip: int = 0, limit: int = 100,
    current_user: dict = Depends(require_admin),
):
    txs = await db.wallet_transactions.find(
        {"operator_id": operator_id}, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return txs
