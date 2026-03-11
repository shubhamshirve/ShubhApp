"""All Pydantic models for the application."""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============== USER MODELS ==============

class UserBase(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    role: str = "operator"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    phone: Optional[str] = None
    role: str
    operator_id: Optional[str] = None
    status: str = "active"
    impersonated_by: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============== OPERATOR MODELS ==============

class OperatorCreate(BaseModel):
    company_name: str
    owner_name: str
    email: EmailStr
    phone: str
    password: str
    gst_number: Optional[str] = None
    charge_gst: bool = False
    bank_account_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_name: Optional[str] = None


class OperatorUpdate(BaseModel):
    company_name: Optional[str] = None
    owner_name: Optional[str] = None
    phone: Optional[str] = None
    gst_number: Optional[str] = None
    charge_gst: Optional[bool] = None
    bank_account_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_name: Optional[str] = None
    status: Optional[str] = None


class OperatorResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    company_name: str
    owner_name: str
    email: str
    phone: str
    gst_number: Optional[str] = None
    charge_gst: bool = False
    status: str
    saas_plan_id: Optional[str] = None
    saas_plan_name: Optional[str] = None
    trial_ends_at: Optional[datetime] = None
    subscription_ends_at: Optional[datetime] = None
    is_read_only: bool = False
    max_staff: Optional[int] = None
    subscriber_count: Optional[int] = 0
    created_at: datetime


class AdminOperatorCreate(BaseModel):
    company_name: str
    owner_name: str
    email: EmailStr
    phone: str
    password: str
    gst_number: Optional[str] = None
    charge_gst: bool = False
    bank_account_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_name: Optional[str] = None
    saas_plan_id: str
    status: str = "active"  # active, trial, suspended
    subscription_months: int = 1


class ExtendSubscriptionRequest(BaseModel):
    months: Optional[int] = None
    custom_date: Optional[str] = None


# ============== SAAS PLAN MODELS ==============

# Subscriber tier: count → base monthly price
SUBSCRIBER_TIERS = {250: 500, 500: 1000, 750: 1500, 1000: 2000, 1500: 3000, 2000: 4000, 3000: 5500}
# Staff tier: count → additional monthly price
STAFF_TIERS = {0: 0, 5: 100, 10: 200, 20: 300}

VALID_SUBSCRIBER_COUNTS = sorted(SUBSCRIBER_TIERS.keys())
VALID_STAFF_COUNTS = sorted(STAFF_TIERS.keys())


def calc_plan_price(max_subscribers: int, max_staff: int, addon_prices: List[float]) -> float:
    base = SUBSCRIBER_TIERS.get(max_subscribers, 0)
    staff = STAFF_TIERS.get(max_staff, 0)
    return base + staff + sum(addon_prices)


class SaaSPlanCreate(BaseModel):
    name: str
    monthly_price: float
    max_subscribers: int
    max_staff: int = 999  # default high; staff access managed via addon
    trial_enabled: bool = False
    trial_days: int = 0
    gst_applicable: bool = True
    included_addons: List[str] = []


class SaaSPlanResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    monthly_price: float
    max_subscribers: int
    max_staff: int
    trial_enabled: bool
    trial_days: int
    gst_applicable: bool
    included_addons: List[str] = []
    status: str
    created_at: datetime


# ============== SUBSCRIBER MODELS ==============

class SubscriberCreate(BaseModel):
    name: str
    whatsapp_number: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    plan_id: str
    billing_date: int  # Day of month (1-28)
    discount: float = 0


class SubscriberResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    whatsapp_number: str
    email: Optional[str] = None
    address: Optional[str] = None
    plan_id: str
    plan_name: Optional[str] = None
    billing_date: int
    discount: float
    status: str
    operator_id: str
    created_at: datetime


# ============== OPERATOR PLAN MODELS ==============

class OperatorPlanCreate(BaseModel):
    name: str
    price: float
    validity: str  # monthly, quarterly, half_yearly, yearly
    tax_percentage: float = 0
    tax_type: str = "none"  # inclusive, exclusive, none
    description: Optional[str] = None


class OperatorPlanResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    price: float
    validity: str
    tax_percentage: float
    tax_type: str
    description: Optional[str] = None
    status: str
    operator_id: str
    created_at: datetime


# ============== INVOICE MODELS ==============

class InvoiceCreate(BaseModel):
    subscriber_id: str
    plan_id: str
    base_amount: float
    discount: float = 0
    service_start_date: datetime
    service_end_date: datetime
    due_date: datetime


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    invoice_number: str
    subscriber_id: str
    subscriber_name: Optional[str] = None
    plan_id: str
    plan_name: Optional[str] = None
    base_amount: float
    discount: float
    tax_amount: float
    final_amount: float
    service_start_date: datetime
    service_end_date: datetime
    due_date: datetime
    status: str  # pending, paid, overdue, cancelled
    payment_id: Optional[str] = None
    operator_id: str
    created_at: datetime


class PaymentLinkCreate(BaseModel):
    invoice_id: str


class PaymentLinkResponse(BaseModel):
    payment_link: str
    payment_link_id: str
    qr_code: str
    amount: float


# ============== STAFF MODELS ==============

class StaffCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    permissions: List[str] = []


class StaffResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str = "staff"
    permissions: List[str]
    operator_id: str
    status: str
    created_at: datetime


# ============== AUDIT LOG MODELS ==============

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    user_name: str
    role: str
    action: str
    module: str
    old_value: Optional[Dict] = None
    new_value: Optional[Dict] = None
    ip_address: Optional[str] = None
    operator_id: Optional[str] = None
    created_at: datetime


# ============== ADMIN / SETTINGS MODELS ==============

class GlobalSettingsUpdate(BaseModel):
    active_payment_gateway: Optional[str] = None  # razorpay, cashfree, phonepe
    notification_enabled: bool = True
    auto_invoice_days_before: int = 3
    late_fee_percentage: float = 0
    gst_rate: float = 18


class AdminPaymentGatewayConfig(BaseModel):
    gateway_type: str  # razorpay, cashfree, phonepe
    api_key: str
    api_secret: str
    webhook_secret: Optional[str] = None
    is_active: bool = True
    for_operator_id: Optional[str] = None


# ============== INVOICE CUSTOMIZATION MODELS ==============

class InvoiceCustomization(BaseModel):
    company_name: str
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    logo_url: Optional[str] = None
    invoice_prefix: str = "INV"
    invoice_footer: Optional[str] = None
    show_gst: bool = True
    terms_conditions: Optional[str] = None


# ============== ANNOUNCEMENT MODELS ==============

class AnnouncementCreate(BaseModel):
    title: str
    message: str
    send_whatsapp: bool = True
    send_to_all: bool = True
    subscriber_ids: Optional[List[str]] = None


# ============== PAYMENT GATEWAY MODELS ==============

class PaymentGatewayConfig(BaseModel):
    gateway_type: str  # razorpay, cashfree, phonepe
    api_key: str
    api_secret: str
    webhook_secret: Optional[str] = None


# ============== WHATSAPP MODELS ==============

class WhatsAppConfig(BaseModel):
    phone_number_id: str
    access_token: str
    business_account_id: Optional[str] = None


class SendNotificationRequest(BaseModel):
    invoice_id: str
    notification_type: str = "invoice"  # invoice, reminder


class BulkNotificationRequest(BaseModel):
    subscriber_ids: List[str]
    message_template: str = "invoice"


# ============== ADDON MODELS ==============

class AddonCreate(BaseModel):
    name: str
    code: str
    price: float


# ============== DISCOUNT CODE MODELS ==============

class DiscountCodeCreate(BaseModel):
    code: str
    description: Optional[str] = None
    discount_type: str  # "percentage" or "flat"
    discount_value: float  # e.g. 20 for 20% or 100 for ₹100 flat
    expiry_date: Optional[str] = None  # ISO date string YYYY-MM-DD
    max_redemptions: int = 0  # 0 = unlimited
    is_active: bool = True


class DiscountCodeResponse(BaseModel):
    id: str
    code: str
    description: Optional[str] = None
    discount_type: str
    discount_value: float
    expiry_date: Optional[str] = None
    max_redemptions: int = 0
    used_count: int = 0
    is_active: bool = True
    created_at: datetime
    description: Optional[str] = None
