"""All Pydantic models for the application."""
import re

from pydantic import Field, EmailStr, ConfigDict, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from sanitization import SanitizedModel


def _empty_to_none(v):
    """Convert empty strings to None for optional fields."""
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


GST_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]$")
IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

# Valid business types
BUSINESS_TYPES = [
    "Sole Proprietorship",
    "Partnership",
    "LLP",
    "Private Limited",
    "Public Limited",
    "Others"
]


def _normalize_phone(value: Optional[str], *, required: bool = False) -> Optional[str]:
    if value is None:
        if required:
            raise ValueError("Phone number is required")
        return None

    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) == 10:
        return digits
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    raise ValueError("Phone number must be a valid 10-digit Indian mobile or 12-digit number with country code")


def _normalize_gst(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    gst = value.upper()
    if not GST_PATTERN.fullmatch(gst):
        raise ValueError("GST number must be a valid 15-character GSTIN")
    return gst


def _normalize_ifsc(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    ifsc = value.upper()
    if not IFSC_PATTERN.fullmatch(ifsc):
        raise ValueError("IFSC code must be a valid 11-character IFSC")
    return ifsc


def _normalize_pan(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    pan = value.upper()
    if not PAN_PATTERN.fullmatch(pan):
        raise ValueError("PAN must be a valid 10-character PAN (e.g., ABCDE1234F)")
    return pan


def _validate_business_type(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if value not in BUSINESS_TYPES:
        raise ValueError(f"Business type must be one of: {', '.join(BUSINESS_TYPES)}")
    return value


# ============== USER MODELS ==============

class UserBase(SanitizedModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value):
        return _normalize_phone(value)


class UserCreate(UserBase):
    password: str
    role: str = "operator"


class UserLogin(SanitizedModel):
    _unsanitized_fields = {"password"}
    email: EmailStr
    password: str


class UserResponse(SanitizedModel):
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


class TokenResponse(SanitizedModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============== OPERATOR MODELS ==============

class OperatorCreate(SanitizedModel):
    _unsanitized_fields = {"password"}
    company_name: str
    owner_name: str
    email: EmailStr
    phone: str
    password: str
    business_type: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    address: Optional[str] = None
    charge_gst: bool = False
    bank_account_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_name: Optional[str] = None
    referral_code: Optional[str] = None  # code used during registration

    @field_validator("gst_number", "pan_number", "address", "bank_account_name", "bank_account_number", "bank_ifsc", "bank_name", "business_type", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value):
        return _normalize_phone(value, required=True)

    @field_validator("gst_number")
    @classmethod
    def normalize_gst(cls, value):
        return _normalize_gst(value)

    @field_validator("pan_number")
    @classmethod
    def normalize_pan(cls, value):
        return _normalize_pan(value)

    @field_validator("bank_ifsc")
    @classmethod
    def normalize_ifsc(cls, value):
        return _normalize_ifsc(value)

    @field_validator("business_type")
    @classmethod
    def validate_business_type(cls, value):
        return _validate_business_type(value)


class OperatorUpdate(SanitizedModel):
    company_name: Optional[str] = None
    owner_name: Optional[str] = None
    phone: Optional[str] = None
    business_type: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    address: Optional[str] = None
    charge_gst: Optional[bool] = None
    bank_account_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_name: Optional[str] = None
    status: Optional[str] = None

    @field_validator("gst_number", "pan_number", "address", "bank_account_name", "bank_account_number", "bank_ifsc", "bank_name", "business_type", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value):
        return _normalize_phone(value)

    @field_validator("gst_number")
    @classmethod
    def normalize_gst(cls, value):
        return _normalize_gst(value)

    @field_validator("pan_number")
    @classmethod
    def normalize_pan(cls, value):
        return _normalize_pan(value)

    @field_validator("bank_ifsc")
    @classmethod
    def normalize_ifsc(cls, value):
        return _normalize_ifsc(value)

    @field_validator("business_type")
    @classmethod
    def validate_business_type(cls, value):
        return _validate_business_type(value)


class OperatorResponse(SanitizedModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    company_name: str
    owner_name: str
    email: str
    phone: str
    business_type: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    address: Optional[str] = None
    charge_gst: bool = False
    bank_account_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_name: Optional[str] = None
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
    referral_code: Optional[str] = None
    referred_by_code: Optional[str] = None
    wallet_suspended: bool = False
    created_at: datetime


class AdminOperatorCreate(SanitizedModel):
    _unsanitized_fields = {"password"}
    company_name: str
    owner_name: str
    email: EmailStr
    phone: str
    password: str
    business_type: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    address: Optional[str] = None
    charge_gst: bool = False
    bank_account_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_name: Optional[str] = None
    saas_plan_id: str
    status: str = "active"  # active, trial, suspended
    subscription_months: int = 1

    @field_validator("gst_number", "pan_number", "address", "bank_account_name", "bank_account_number", "bank_ifsc", "bank_name", "business_type", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value):
        return _normalize_phone(value, required=True)

    @field_validator("gst_number")
    @classmethod
    def normalize_gst(cls, value):
        return _normalize_gst(value)

    @field_validator("pan_number")
    @classmethod
    def normalize_pan(cls, value):
        return _normalize_pan(value)

    @field_validator("bank_ifsc")
    @classmethod
    def normalize_ifsc(cls, value):
        return _normalize_ifsc(value)

    @field_validator("business_type")
    @classmethod
    def validate_business_type(cls, value):
        return _validate_business_type(value)


class ExtendSubscriptionRequest(SanitizedModel):
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


class SaaSPlanCreate(SanitizedModel):
    name: str
    monthly_price: float = 0.0  # Legacy/custom; auto-calculated for basic/pro
    max_subscribers: int = 99999
    max_staff: int = 999  # default high; staff access managed via addon
    trial_enabled: bool = False
    trial_days: int = 0
    gst_applicable: bool = True
    included_addons: List[str] = []
    platform_fee_percentage: float = 0.0
    plan_type: Optional[str] = None  # "basic", "pro", or None (custom/legacy)
    per_customer_rate: Optional[float] = None  # Rs.12 for basic, Rs.22 for pro
    monthly_base_fee: Optional[float] = 0.0  # Rs.0 for basic, Rs.1000 for pro


class SaaSPlanResponse(SanitizedModel):
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
    platform_fee_percentage: Optional[float] = 0.0
    plan_type: Optional[str] = None
    per_customer_rate: Optional[float] = None
    monthly_base_fee: Optional[float] = 0.0
    status: str
    created_at: datetime


# ============== SUBSCRIBER MODELS ==============

class SubscriberCreate(SanitizedModel):
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

    @field_validator("whatsapp_number")
    @classmethod
    def normalize_whatsapp(cls, value):
        return _normalize_phone(value, required=True)


class SubscriberResponse(SanitizedModel):
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

class OperatorPlanCreate(SanitizedModel):
    name: str
    price: float
    validity: str  # monthly, quarterly, half_yearly, yearly
    tax_percentage: float = 0
    tax_type: str = "none"  # inclusive, exclusive, none
    description: Optional[str] = None


class OperatorPlanResponse(SanitizedModel):
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

class InvoiceCreate(SanitizedModel):
    subscriber_id: str
    plan_id: str
    base_amount: float
    discount: float = 0
    service_start_date: datetime
    service_end_date: datetime
    due_date: datetime


class InvoiceResponse(SanitizedModel):
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


class PaymentLinkCreate(SanitizedModel):
    invoice_id: str


class PaymentLinkResponse(SanitizedModel):
    payment_link: str
    payment_link_id: str
    qr_code: str
    amount: float


# ============== STAFF MODELS ==============

class StaffCreate(SanitizedModel):
    _unsanitized_fields = {"password"}
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    permissions: List[str] = []

    @field_validator("phone", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value):
        return _normalize_phone(value)


class StaffResponse(SanitizedModel):
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

class AuditLogResponse(SanitizedModel):
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

class GlobalSettingsUpdate(SanitizedModel):
    active_payment_gateway: Optional[str] = None  # razorpay, cashfree, phonepe
    notification_enabled: bool = True
    auto_invoice_days_before: int = 3
    late_fee_percentage: float = 0
    gst_rate: float = 18


class AdminPaymentGatewayConfig(SanitizedModel):
    _unsanitized_fields = {"api_secret", "webhook_secret"}
    gateway_type: str  # razorpay, cashfree, phonepe
    api_key: str
    api_secret: str
    webhook_secret: Optional[str] = None
    is_active: bool = True
    for_operator_id: Optional[str] = None


# ============== INVOICE CUSTOMIZATION MODELS ==============

class InvoiceCustomization(SanitizedModel):
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

    @field_validator("company_phone")
    @classmethod
    def normalize_company_phone(cls, value):
        return _normalize_phone(value)

    @field_validator("invoice_prefix")
    @classmethod
    def normalize_invoice_prefix(cls, value):
        prefix = value.upper()
        if not re.fullmatch(r"[A-Z0-9_-]{2,10}", prefix):
            raise ValueError("Invoice prefix must be 2-10 characters using letters, numbers, underscore, or hyphen")
        return prefix


# ============== ANNOUNCEMENT MODELS ==============

class AnnouncementCreate(SanitizedModel):
    title: str
    message: str
    send_whatsapp: bool = True
    send_to_all: bool = True
    subscriber_ids: Optional[List[str]] = None


# ============== PAYMENT GATEWAY MODELS ==============

class PaymentGatewayConfig(SanitizedModel):
    _unsanitized_fields = {"api_secret", "webhook_secret"}
    gateway_type: str  # razorpay, cashfree, phonepe
    api_key: str
    api_secret: str
    webhook_secret: Optional[str] = None


# ============== WHATSAPP MODELS ==============

class WhatsAppConfig(SanitizedModel):
    _unsanitized_fields = {"access_token"}
    phone_number_id: str
    access_token: str
    business_account_id: Optional[str] = None

    @field_validator("phone_number_id")
    @classmethod
    def validate_phone_number_id(cls, value):
        if not value.isdigit():
            raise ValueError("Phone number ID must contain only digits")
        return value


class WhatsAppTemplateSettings(SanitizedModel):
    invoice_template: Optional[str] = None
    reminder_template: Optional[str] = None
    payment_confirmation_template: Optional[str] = None
    announcement_template: Optional[str] = None


class WhatsAppTestMessage(SanitizedModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value):
        return _normalize_phone(value, required=True)


class SendNotificationRequest(SanitizedModel):
    invoice_id: str
    notification_type: str = "invoice"  # invoice, reminder


class BulkNotificationRequest(SanitizedModel):
    subscriber_ids: List[str]
    message_template: str = "invoice"


# ============== REMINDER SETTINGS MODELS ==============

class ReminderSettingsUpdate(SanitizedModel):
    enabled: bool = False
    remind_before_due: List[int] = []      # e.g. [3, 1] = 3 days and 1 day before
    remind_on_due: bool = False
    remind_after_due: List[int] = []       # e.g. [1, 3, 7] = 1, 3, 7 days after
    max_reminders_per_invoice: int = 5


# ============== ADDON MODELS ==============

class AddonCreate(SanitizedModel):
    description: Optional[str] = None
    name: str
    code: str
    price: float


# ============== DISCOUNT CODE MODELS ==============

class DiscountCodeCreate(SanitizedModel):
    code: str
    description: Optional[str] = None
    discount_type: str  # "percentage" or "flat"
    discount_value: float  # e.g. 20 for 20% or 100 for ₹100 flat
    expiry_date: Optional[str] = None  # ISO date string YYYY-MM-DD
    max_redemptions: int = 0  # 0 = unlimited
    is_active: bool = True


class DiscountCodeResponse(SanitizedModel):
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

class WhatsAppTemplateCreate(SanitizedModel):
    template_name: str          # API name used in send_template_message calls
    display_name: str           # Human readable name shown in UI
    template_type: str          # invoice_notification, payment_reminder, payment_confirmation, announcement, custom
    language_code: str = "en"
    description: Optional[str] = None
    body_variables: Optional[List[str]] = []  # list of variable descriptions e.g. ["customer_name", "invoice_no"]
    has_payment_button: bool = False
    is_active: bool = True


class WhatsAppTemplateUpdate(SanitizedModel):
    display_name: Optional[str] = None
    template_name: Optional[str] = None
    language_code: Optional[str] = None
    description: Optional[str] = None
    body_variables: Optional[List[str]] = None
    has_payment_button: Optional[bool] = None
    is_active: Optional[bool] = None
