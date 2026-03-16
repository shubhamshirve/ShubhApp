"""All Pydantic models for the application."""
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime


def _empty_to_none(v):
    """Convert empty strings to None for optional fields."""
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


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

    @field_validator("gst_number", "bank_account_name", "bank_account_number", "bank_ifsc", "bank_name", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)


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

    @field_validator("gst_number", "bank_account_name", "bank_account_number", "bank_ifsc", "bank_name", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)


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
    active_addons: Optional[List[str]] = None
    addon_expiry: Optional[Dict[str, str]] = None
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

    @field_validator("gst_number", "bank_account_name", "bank_account_number", "bank_ifsc", "bank_name", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)


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
    platform_fee_percentage: float = 3.0


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
    platform_fee_percentage: Optional[float] = 3.0
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

    @field_validator("email", "address", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)


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

    @field_validator("phone", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)


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
    invoice_template: str = "classic"  # "classic" or "modern"


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


class WhatsAppTemplateSettings(BaseModel):
    invoice_template: Optional[str] = None
    reminder_template: Optional[str] = None
    payment_confirmation_template: Optional[str] = None
    announcement_template: Optional[str] = None


class WhatsAppTestMessage(BaseModel):
    phone_number: str


class SendNotificationRequest(BaseModel):
    invoice_id: str
    notification_type: str = "invoice"  # invoice, reminder


class BulkNotificationRequest(BaseModel):
    subscriber_ids: List[str]
    message_template: str = "invoice"


# ============== REMINDER SETTINGS MODELS ==============

class ReminderSettingsUpdate(BaseModel):
    enabled: bool = False
    remind_before_due: List[int] = []      # e.g. [3, 1] = 3 days and 1 day before
    remind_on_due: bool = False
    remind_after_due: List[int] = []       # e.g. [1, 3, 7] = 1, 3, 7 days after
    max_reminders_per_invoice: int = 5


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


# ============== WHATSAPP TEMPLATE MODELS ==============

class WhatsAppTemplateCreate(BaseModel):
    template_name: str          # API name used in send_template_message calls
    display_name: str           # Human readable name shown in UI
    template_type: str          # invoice_notification, payment_reminder, payment_confirmation, announcement, custom
    language_code: str = "en"
    description: Optional[str] = None
    body_variables: Optional[List[str]] = []  # list of variable descriptions e.g. ["customer_name", "invoice_no"]
    has_payment_button: bool = False
    is_active: bool = True


class WhatsAppTemplateUpdate(BaseModel):
    display_name: Optional[str] = None
    template_name: Optional[str] = None
    language_code: Optional[str] = None
    description: Optional[str] = None
    body_variables: Optional[List[str]] = None
    has_payment_button: Optional[bool] = None
    is_active: Optional[bool] = None
