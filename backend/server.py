from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import json
from bson import ObjectId

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'saas-billing-secret-key-2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI(title="Multi-Tenant SaaS Billing Platform")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============== PYDANTIC MODELS ==============

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
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Operator Models
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
    created_at: datetime

# SaaS Plan Models
class SaaSPlanCreate(BaseModel):
    name: str
    monthly_price: float
    max_subscribers: int
    max_staff: int
    trial_enabled: bool = True
    trial_days: int = 3
    notification_module: bool = False
    auto_reminder: bool = False
    audit_logs: bool = False
    payment_gateway_setup: bool = False
    gst_applicable: bool = True

class SaaSPlanResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    monthly_price: float
    max_subscribers: int
    max_staff: int
    trial_enabled: bool
    trial_days: int
    notification_module: bool
    auto_reminder: bool
    audit_logs: bool
    payment_gateway_setup: bool
    gst_applicable: bool
    status: str
    created_at: datetime

# Subscriber Models
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

# Operator Plan Models
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

# Invoice Models
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

# Payment Gateway Models
class PaymentGatewayConfig(BaseModel):
    gateway_type: str  # razorpay, cashfree, phonepe
    api_key: str
    api_secret: str
    webhook_secret: Optional[str] = None

# Staff Models
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

# Audit Log Model
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

# ============== UTILITY FUNCTIONS ==============

def generate_id() -> str:
    return str(uuid.uuid4())

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_data: dict) -> str:
    payload = {
        "sub": user_data["id"],
        "email": user_data["email"],
        "role": user_data["role"],
        "operator_id": user_data.get("operator_id"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def generate_invoice_number(operator_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"INV-{operator_id[:8].upper()}-{timestamp}"

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    user = await db.users.find_one({"id": payload["sub"], "deleted_at": None}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def require_operator(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] not in ["operator", "admin", "staff"]:
        raise HTTPException(status_code=403, detail="Operator access required")
    return current_user

async def require_operator_no_staff(current_user: dict = Depends(get_current_user)) -> dict:
    """Only operators (not staff) can perform this action"""
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff users cannot perform delete operations")
    if current_user["role"] not in ["operator", "admin"]:
        raise HTTPException(status_code=403, detail="Operator access required")
    return current_user

async def check_operator_read_only(operator_id: str) -> bool:
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if operator and operator.get("is_read_only"):
        return True
    return False

async def log_audit(user_id: str, user_name: str, role: str, action: str, module: str,
                   old_value: dict = None, new_value: dict = None, 
                   ip_address: str = None, operator_id: str = None):
    audit_log = {
        "id": generate_id(),
        "user_id": user_id,
        "user_name": user_name,
        "role": role,
        "action": action,
        "module": module,
        "old_value": old_value,
        "new_value": new_value,
        "ip_address": ip_address,
        "operator_id": operator_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_logs.insert_one(audit_log)

# ============== AUTH ENDPOINTS ==============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register_operator(data: OperatorCreate):
    """Register a new operator with trial period"""
    # Check if email exists
    existing = await db.users.find_one({"email": data.email, "deleted_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Get default trial plan
    trial_plan = await db.saas_plans.find_one({"trial_enabled": True, "deleted_at": None}, {"_id": 0})
    
    now = datetime.now(timezone.utc)
    operator_id = generate_id()
    user_id = generate_id()
    
    # Create operator
    operator = {
        "id": operator_id,
        "company_name": data.company_name,
        "owner_name": data.owner_name,
        "email": data.email,
        "phone": data.phone,
        "gst_number": data.gst_number,
        "charge_gst": data.charge_gst,
        "bank_account_name": data.bank_account_name,
        "bank_account_number": data.bank_account_number,
        "bank_ifsc": data.bank_ifsc,
        "bank_name": data.bank_name,
        "status": "trial",
        "saas_plan_id": trial_plan["id"] if trial_plan else None,
        "saas_plan_name": trial_plan["name"] if trial_plan else None,
        "trial_ends_at": (now + timedelta(days=trial_plan["trial_days"] if trial_plan else 3)).isoformat(),
        "subscription_ends_at": None,
        "is_read_only": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.operators.insert_one(operator)
    
    # Create user account for operator
    user = {
        "id": user_id,
        "email": data.email,
        "name": data.owner_name,
        "phone": data.phone,
        "password": hash_password(data.password),
        "role": "operator",
        "operator_id": operator_id,
        "status": "active",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.users.insert_one(user)
    
    # Generate token
    token = create_token({"id": user_id, "email": data.email, "role": "operator", "operator_id": operator_id})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=data.email,
            name=data.owner_name,
            phone=data.phone,
            role="operator",
            operator_id=operator_id,
            status="active",
            created_at=now
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(data: UserLogin):
    """Login for all users"""
    user = await db.users.find_one({"email": data.email, "deleted_at": None}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user["status"] != "active":
        raise HTTPException(status_code=401, detail="Account is not active")
    
    token = create_token({
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "operator_id": user.get("operator_id")
    })
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            phone=user.get("phone"),
            role=user["role"],
            operator_id=user.get("operator_id"),
            status=user["status"],
            created_at=datetime.fromisoformat(user["created_at"])
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        phone=current_user.get("phone"),
        role=current_user["role"],
        operator_id=current_user.get("operator_id"),
        status=current_user["status"],
        created_at=datetime.fromisoformat(current_user["created_at"])
    )

# ============== ADMIN: SAAS PLANS ==============

@api_router.post("/admin/saas-plans", response_model=SaaSPlanResponse)
async def create_saas_plan(data: SaaSPlanCreate, current_user: dict = Depends(require_admin)):
    """Create a new SaaS plan (Admin only)"""
    now = datetime.now(timezone.utc)
    plan = {
        "id": generate_id(),
        "name": data.name,
        "monthly_price": data.monthly_price,
        "max_subscribers": data.max_subscribers,
        "max_staff": data.max_staff,
        "trial_enabled": data.trial_enabled,
        "trial_days": data.trial_days,
        "notification_module": data.notification_module,
        "auto_reminder": data.auto_reminder,
        "audit_logs": data.audit_logs,
        "payment_gateway_setup": data.payment_gateway_setup,
        "gst_applicable": data.gst_applicable,
        "status": "active",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.saas_plans.insert_one(plan)
    
    await log_audit(current_user["id"], current_user["name"], current_user["role"],
                   "create", "saas_plans", None, {"name": data.name})
    
    return SaaSPlanResponse(**{**plan, "created_at": now})

@api_router.get("/admin/saas-plans", response_model=List[SaaSPlanResponse])
async def get_saas_plans(current_user: dict = Depends(require_admin)):
    """Get all SaaS plans (Admin only)"""
    plans = await db.saas_plans.find({"deleted_at": None}, {"_id": 0}).to_list(100)
    return [SaaSPlanResponse(**{**p, "created_at": datetime.fromisoformat(p["created_at"])}) for p in plans]

@api_router.put("/admin/saas-plans/{plan_id}", response_model=SaaSPlanResponse)
async def update_saas_plan(plan_id: str, data: SaaSPlanCreate, current_user: dict = Depends(require_admin)):
    """Update a SaaS plan (Admin only)"""
    existing = await db.saas_plans.find_one({"id": plan_id, "deleted_at": None}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    now = datetime.now(timezone.utc)
    update_data = {
        "name": data.name,
        "monthly_price": data.monthly_price,
        "max_subscribers": data.max_subscribers,
        "max_staff": data.max_staff,
        "trial_enabled": data.trial_enabled,
        "trial_days": data.trial_days,
        "notification_module": data.notification_module,
        "auto_reminder": data.auto_reminder,
        "audit_logs": data.audit_logs,
        "payment_gateway_setup": data.payment_gateway_setup,
        "gst_applicable": data.gst_applicable,
        "updated_at": now.isoformat()
    }
    
    await db.saas_plans.update_one({"id": plan_id}, {"$set": update_data})
    
    updated = await db.saas_plans.find_one({"id": plan_id}, {"_id": 0})
    return SaaSPlanResponse(**{**updated, "created_at": datetime.fromisoformat(updated["created_at"])})

@api_router.delete("/admin/saas-plans/{plan_id}")
async def delete_saas_plan(plan_id: str, current_user: dict = Depends(require_admin)):
    """Soft delete a SaaS plan (Admin only)"""
    result = await db.saas_plans.update_one(
        {"id": plan_id, "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Plan deleted successfully"}

# ============== ADMIN: OPERATORS ==============

@api_router.get("/admin/operators", response_model=List[OperatorResponse])
async def get_operators(current_user: dict = Depends(require_admin)):
    """Get all operators (Admin only)"""
    operators = await db.operators.find({"deleted_at": None}, {"_id": 0}).to_list(1000)
    return [OperatorResponse(**{**o, "created_at": datetime.fromisoformat(o["created_at"]),
            "trial_ends_at": datetime.fromisoformat(o["trial_ends_at"]) if o.get("trial_ends_at") else None,
            "subscription_ends_at": datetime.fromisoformat(o["subscription_ends_at"]) if o.get("subscription_ends_at") else None}) 
            for o in operators]

@api_router.get("/admin/operators/{operator_id}", response_model=OperatorResponse)
async def get_operator(operator_id: str, current_user: dict = Depends(require_admin)):
    """Get operator details (Admin only)"""
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    return OperatorResponse(**{**operator, "created_at": datetime.fromisoformat(operator["created_at"]),
            "trial_ends_at": datetime.fromisoformat(operator["trial_ends_at"]) if operator.get("trial_ends_at") else None,
            "subscription_ends_at": datetime.fromisoformat(operator["subscription_ends_at"]) if operator.get("subscription_ends_at") else None})

@api_router.put("/admin/operators/{operator_id}", response_model=OperatorResponse)
async def update_operator(operator_id: str, data: OperatorUpdate, current_user: dict = Depends(require_admin)):
    """Update operator (Admin only)"""
    existing = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.operators.update_one({"id": operator_id}, {"$set": update_data})
    
    updated = await db.operators.find_one({"id": operator_id}, {"_id": 0})
    return OperatorResponse(**{**updated, "created_at": datetime.fromisoformat(updated["created_at"]),
            "trial_ends_at": datetime.fromisoformat(updated["trial_ends_at"]) if updated.get("trial_ends_at") else None,
            "subscription_ends_at": datetime.fromisoformat(updated["subscription_ends_at"]) if updated.get("subscription_ends_at") else None})

# ============== ADMIN: MANUAL OPERATOR CREATION ==============

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
    subscription_months: int = 1  # Number of months for subscription

@api_router.post("/admin/operators/create", response_model=OperatorResponse)
async def create_operator_manually(data: AdminOperatorCreate, current_user: dict = Depends(require_admin)):
    """Manually create operator (Admin only) - No trial, direct plan assignment"""
    # Check if email exists
    existing = await db.users.find_one({"email": data.email, "deleted_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Verify plan exists
    plan = await db.saas_plans.find_one({"id": data.saas_plan_id, "deleted_at": None}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="SaaS plan not found")
    
    now = datetime.now(timezone.utc)
    operator_id = generate_id()
    user_id = generate_id()
    
    # Calculate subscription end date
    subscription_ends_at = (now + timedelta(days=30 * data.subscription_months)).isoformat()
    
    # Create operator
    operator = {
        "id": operator_id,
        "company_name": data.company_name,
        "owner_name": data.owner_name,
        "email": data.email,
        "phone": data.phone,
        "gst_number": data.gst_number,
        "charge_gst": data.charge_gst,
        "bank_account_name": data.bank_account_name,
        "bank_account_number": data.bank_account_number,
        "bank_ifsc": data.bank_ifsc,
        "bank_name": data.bank_name,
        "status": data.status,
        "saas_plan_id": data.saas_plan_id,
        "saas_plan_name": plan["name"],
        "trial_ends_at": None,
        "subscription_ends_at": subscription_ends_at if data.status == "active" else None,
        "is_read_only": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.operators.insert_one(operator)
    
    # Create user account for operator
    user = {
        "id": user_id,
        "email": data.email,
        "name": data.owner_name,
        "phone": data.phone,
        "password": hash_password(data.password),
        "role": "operator",
        "operator_id": operator_id,
        "status": "active",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.users.insert_one(user)
    
    # Log audit
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "create", "operators", None, 
        {"company_name": data.company_name, "email": data.email, "plan": plan["name"]}
    )
    
    return OperatorResponse(**{
        **operator,
        "created_at": now,
        "trial_ends_at": None,
        "subscription_ends_at": datetime.fromisoformat(subscription_ends_at) if data.status == "active" else None
    })

# ============== ADMIN: EXTEND SUBSCRIPTION ==============

class ExtendSubscriptionRequest(BaseModel):
    months: Optional[int] = None  # Quick extend: 1, 3, 6, 12
    custom_date: Optional[str] = None  # Custom date in ISO format

@api_router.post("/admin/operators/{operator_id}/extend-subscription")
async def extend_operator_subscription(
    operator_id: str, 
    data: ExtendSubscriptionRequest, 
    current_user: dict = Depends(require_admin)
):
    """Extend operator subscription (Admin only)"""
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    now = datetime.now(timezone.utc)
    
    # Calculate new expiry date
    if data.custom_date:
        # Use custom date
        new_expiry = data.custom_date
    elif data.months:
        # Extend from current expiry or now
        current_expiry = operator.get("subscription_ends_at")
        if current_expiry:
            base_date = datetime.fromisoformat(current_expiry)
            # If already expired, extend from now
            if base_date < now:
                base_date = now
        else:
            base_date = now
        
        new_expiry = (base_date + timedelta(days=30 * data.months)).isoformat()
    else:
        raise HTTPException(status_code=400, detail="Either months or custom_date must be provided")
    
    # Update operator
    update_data = {
        "subscription_ends_at": new_expiry,
        "status": "active",
        "is_read_only": False,
        "updated_at": now.isoformat()
    }
    
    await db.operators.update_one({"id": operator_id}, {"$set": update_data})
    
    # Log audit
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "extend_subscription", "operators",
        {"old_expiry": operator.get("subscription_ends_at")},
        {"new_expiry": new_expiry, "months": data.months}
    )
    
    return {
        "message": "Subscription extended successfully",
        "new_expiry_date": new_expiry,
        "operator_id": operator_id
    }

# ============== ADMIN: DELETE OPERATOR ==============

@api_router.delete("/admin/operators/{operator_id}")
async def delete_operator(operator_id: str, current_user: dict = Depends(require_admin)):
    """Soft delete operator and all related data (Admin only)"""
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    now = datetime.now(timezone.utc)
    deleted_at = now.isoformat()
    
    # Soft delete operator
    await db.operators.update_one(
        {"id": operator_id},
        {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}}
    )
    
    # Soft delete all related users (operator and staff)
    await db.users.update_many(
        {"operator_id": operator_id, "deleted_at": None},
        {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}}
    )
    
    # Soft delete all subscribers
    await db.subscribers.update_many(
        {"operator_id": operator_id, "deleted_at": None},
        {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}}
    )
    
    # Soft delete all operator plans
    await db.operator_plans.update_many(
        {"operator_id": operator_id, "deleted_at": None},
        {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}}
    )
    
    # Soft delete all invoices
    await db.invoices.update_many(
        {"operator_id": operator_id, "deleted_at": None},
        {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}}
    )
    
    # Log audit
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "delete", "operators",
        {"company_name": operator["company_name"], "email": operator["email"]},
        {"deleted_at": deleted_at}
    )
    
    return {
        "message": "Operator and all related data deleted successfully",
        "operator_id": operator_id,
        "company_name": operator["company_name"]
    }

@api_router.post("/admin/operators/{operator_id}/assign-plan")
async def assign_plan_to_operator(operator_id: str, plan_id: str = Query(...), current_user: dict = Depends(require_admin)):
    """Assign SaaS plan to operator (Admin only)"""
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    plan = await db.saas_plans.find_one({"id": plan_id, "deleted_at": None}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    now = datetime.now(timezone.utc)
    update_data = {
        "saas_plan_id": plan_id,
        "saas_plan_name": plan["name"],
        "status": "active",
        "subscription_ends_at": (now + timedelta(days=30)).isoformat(),
        "is_read_only": False,
        "updated_at": now.isoformat()
    }
    
    await db.operators.update_one({"id": operator_id}, {"$set": update_data})
    return {"message": "Plan assigned successfully"}

@api_router.post("/admin/operators/{operator_id}/suspend")
async def suspend_operator(operator_id: str, current_user: dict = Depends(require_admin)):
    """Suspend an operator (Admin only)"""
    result = await db.operators.update_one(
        {"id": operator_id, "deleted_at": None},
        {"$set": {"status": "suspended", "is_read_only": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Operator not found")
    return {"message": "Operator suspended"}

@api_router.post("/admin/operators/{operator_id}/activate")
async def activate_operator(operator_id: str, current_user: dict = Depends(require_admin)):
    """Activate a suspended operator (Admin only)"""
    result = await db.operators.update_one(
        {"id": operator_id, "deleted_at": None},
        {"$set": {"status": "active", "is_read_only": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Operator not found")
    return {"message": "Operator activated"}

# ============== ADMIN: IMPERSONATE OPERATOR ==============

@api_router.post("/admin/operators/{operator_id}/impersonate")
async def impersonate_operator(operator_id: str, current_user: dict = Depends(require_admin)):
    """Admin login to operator panel (impersonate)"""
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    # Get operator's user account
    user = await db.users.find_one({"operator_id": operator_id, "role": "operator", "deleted_at": None}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Operator user not found")
    
    # Generate token for operator with admin_impersonating flag
    token = create_token({
        "id": user["id"],
        "email": user["email"],
        "role": "operator",
        "operator_id": operator_id,
        "impersonated_by": current_user["id"]
    })
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "operator": {
            "id": operator_id,
            "company_name": operator["company_name"],
            "owner_name": operator["owner_name"]
        }
    }

# ============== ADMIN: GLOBAL SETTINGS ==============

class GlobalSettingsUpdate(BaseModel):
    active_payment_gateway: Optional[str] = None  # razorpay, cashfree, phonepe
    notification_enabled: bool = True
    auto_invoice_days_before: int = 3
    late_fee_percentage: float = 0
    gst_rate: float = 18

@api_router.get("/admin/settings")
async def get_global_settings(current_user: dict = Depends(require_admin)):
    """Get global platform settings (Admin only)"""
    settings = await db.global_settings.find_one({"type": "platform"}, {"_id": 0})
    if not settings:
        # Return defaults
        return {
            "active_payment_gateway": "razorpay",
            "notification_enabled": True,
            "auto_invoice_days_before": 3,
            "late_fee_percentage": 0,
            "gst_rate": 18
        }
    return settings

@api_router.put("/admin/settings")
async def update_global_settings(data: GlobalSettingsUpdate, current_user: dict = Depends(require_admin)):
    """Update global platform settings (Admin only)"""
    now = datetime.now(timezone.utc)
    settings = {
        "type": "platform",
        **data.model_dump(),
        "updated_at": now.isoformat(),
        "updated_by": current_user["id"]
    }
    
    await db.global_settings.update_one(
        {"type": "platform"},
        {"$set": settings},
        upsert=True
    )
    
    await log_audit(current_user["id"], current_user["name"], current_user["role"],
                   "update", "global_settings", None, data.model_dump())
    
    return {"message": "Settings updated successfully"}

# ============== ADMIN: PAYMENT GATEWAY MANAGEMENT ==============

class AdminPaymentGatewayConfig(BaseModel):
    gateway_type: str  # razorpay, cashfree, phonepe
    api_key: str
    api_secret: str
    webhook_secret: Optional[str] = None
    is_active: bool = True
    for_operator_id: Optional[str] = None  # If None, it's the platform default

@api_router.post("/admin/payment-gateways")
async def create_admin_payment_gateway(data: AdminPaymentGatewayConfig, current_user: dict = Depends(require_admin)):
    """Create/configure payment gateway (Admin only) - can be for platform or specific operator"""
    now = datetime.now(timezone.utc)
    
    gateway = {
        "id": generate_id(),
        "gateway_type": data.gateway_type,
        "api_key": data.api_key,
        "api_secret": data.api_secret,
        "webhook_secret": data.webhook_secret,
        "is_active": data.is_active,
        "operator_id": data.for_operator_id,  # None means platform default
        "is_platform_gateway": data.for_operator_id is None,
        "created_by": current_user["id"],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Upsert based on operator_id (or None for platform)
    await db.payment_gateways.update_one(
        {"operator_id": data.for_operator_id, "gateway_type": data.gateway_type},
        {"$set": gateway},
        upsert=True
    )
    
    return {"message": "Payment gateway configured successfully", "id": gateway["id"]}

@api_router.get("/admin/payment-gateways")
async def get_admin_payment_gateways(current_user: dict = Depends(require_admin)):
    """Get all payment gateway configurations (Admin only)"""
    gateways = await db.payment_gateways.find({}, {"_id": 0, "api_secret": 0}).to_list(100)
    
    # Mask API keys
    for g in gateways:
        if g.get("api_key"):
            g["api_key"] = g["api_key"][:8] + "****"
    
    return gateways

@api_router.delete("/admin/payment-gateways/{gateway_id}")
async def delete_admin_payment_gateway(gateway_id: str, current_user: dict = Depends(require_admin)):
    """Delete a payment gateway configuration (Admin only)"""
    result = await db.payment_gateways.delete_one({"id": gateway_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Gateway not found")
    return {"message": "Gateway deleted"}

# ============== ADMIN: PAYMENT REPORTS ==============

@api_router.get("/admin/reports/payments")
async def get_admin_payment_reports(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Get platform-wide payment reports (Admin only)"""
    query = {"status": "paid", "deleted_at": None}
    
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    # Get all paid invoices grouped by operator
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(10000)
    
    # Group by operator
    operator_revenue = {}
    total_revenue = 0
    total_tax = 0
    
    for inv in invoices:
        op_id = inv.get("operator_id")
        if op_id not in operator_revenue:
            operator_revenue[op_id] = {"count": 0, "revenue": 0, "tax": 0}
        operator_revenue[op_id]["count"] += 1
        operator_revenue[op_id]["revenue"] += inv.get("final_amount", 0)
        operator_revenue[op_id]["tax"] += inv.get("tax_amount", 0)
        total_revenue += inv.get("final_amount", 0)
        total_tax += inv.get("tax_amount", 0)
    
    # Get operator names
    for op_id in operator_revenue:
        operator = await db.operators.find_one({"id": op_id}, {"_id": 0, "company_name": 1})
        operator_revenue[op_id]["company_name"] = operator.get("company_name", "Unknown") if operator else "Unknown"
    
    return {
        "total_invoices": len(invoices),
        "total_revenue": round(total_revenue, 2),
        "total_tax": round(total_tax, 2),
        "by_operator": list(operator_revenue.values())
    }

@api_router.get("/admin/reports/saas-revenue")
async def get_saas_revenue_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Get SaaS subscription revenue report (Admin only)"""
    query = {"deleted_at": None}
    
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    # Get SaaS payments
    payments = await db.saas_payments.find(query, {"_id": 0}).to_list(1000)
    
    total = sum(p.get("total_amount", 0) for p in payments)
    gst = sum(p.get("gst_amount", 0) for p in payments)
    
    # Count by plan
    plan_counts = {}
    for p in payments:
        plan_id = p.get("saas_plan_id")
        if plan_id not in plan_counts:
            plan_counts[plan_id] = {"count": 0, "revenue": 0}
        plan_counts[plan_id]["count"] += 1
        plan_counts[plan_id]["revenue"] += p.get("total_amount", 0)
    
    return {
        "total_payments": len(payments),
        "total_revenue": round(total, 2),
        "total_gst": round(gst, 2),
        "by_plan": plan_counts
    }

# ============== ADMIN: ADDONS MANAGEMENT ==============

class AddonCreate(BaseModel):
    name: str
    code: str  # notifications, custom_gateway, subscriber_upgrade_100, audit_logs
    price: float
    description: Optional[str] = None

@api_router.post("/admin/addons")
async def create_addon(data: AddonCreate, current_user: dict = Depends(require_admin)):
    """Create a SaaS addon (Admin only)"""
    now = datetime.now(timezone.utc)
    addon = {
        "id": generate_id(),
        "name": data.name,
        "code": data.code,
        "price": data.price,
        "description": data.description,
        "status": "active",
        "created_at": now.isoformat(),
        "deleted_at": None
    }
    await db.addons.insert_one(addon)
    return addon

@api_router.get("/admin/addons")
async def get_addons(current_user: dict = Depends(require_admin)):
    """Get all addons (Admin only)"""
    addons = await db.addons.find({"deleted_at": None}, {"_id": 0}).to_list(100)
    return addons

@api_router.post("/admin/operators/{operator_id}/addons/{addon_code}")
async def assign_addon_to_operator(operator_id: str, addon_code: str, current_user: dict = Depends(require_admin)):
    """Assign an addon to an operator (Admin only)"""
    addon = await db.addons.find_one({"code": addon_code, "deleted_at": None}, {"_id": 0})
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    now = datetime.now(timezone.utc)
    
    # Add addon to operator's active addons
    existing_addons = operator.get("active_addons", [])
    if addon_code not in existing_addons:
        existing_addons.append(addon_code)
    
    await db.operators.update_one(
        {"id": operator_id},
        {"$set": {"active_addons": existing_addons, "updated_at": now.isoformat()}}
    )
    
    return {"message": f"Addon '{addon['name']}' assigned to operator"}

# ============== ADMIN: DASHBOARD ==============

@api_router.get("/admin/dashboard")
async def get_admin_dashboard(current_user: dict = Depends(require_admin)):
    """Get admin dashboard KPIs"""
    total_operators = await db.operators.count_documents({"deleted_at": None})
    active_operators = await db.operators.count_documents({"status": "active", "deleted_at": None})
    trial_operators = await db.operators.count_documents({"status": "trial", "deleted_at": None})
    suspended_operators = await db.operators.count_documents({"status": "suspended", "deleted_at": None})
    read_only_operators = await db.operators.count_documents({"is_read_only": True, "deleted_at": None})
    
    # Calculate SaaS revenue this month
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get expiring operators (within 7 days)
    expiring_date = (now + timedelta(days=7)).isoformat()
    expiring_operators = await db.operators.count_documents({
        "subscription_ends_at": {"$lte": expiring_date, "$gte": now.isoformat()},
        "deleted_at": None
    })
    
    return {
        "total_operators": total_operators,
        "active_operators": active_operators,
        "trial_operators": trial_operators,
        "suspended_operators": suspended_operators,
        "read_only_operators": read_only_operators,
        "expiring_operators": expiring_operators,
        "saas_revenue_this_month": 0,  # Would calculate from payments
        "gst_collected": 0,
        "addon_revenue": 0
    }

# ============== ADMIN: AUDIT LOGS ==============

@api_router.get("/admin/audit-logs", response_model=List[AuditLogResponse])
async def get_all_audit_logs(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(require_admin)
):
    """Get all audit logs (Admin only)"""
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [AuditLogResponse(**{**l, "created_at": datetime.fromisoformat(l["created_at"])}) for l in logs]

# ============== OPERATOR: PROFILE ==============

@api_router.get("/operator/profile", response_model=OperatorResponse)
async def get_operator_profile(current_user: dict = Depends(require_operator)):
    """Get current operator's profile"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin users don't have operator profile")
    
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    return OperatorResponse(**{**operator, "created_at": datetime.fromisoformat(operator["created_at"]),
            "trial_ends_at": datetime.fromisoformat(operator["trial_ends_at"]) if operator.get("trial_ends_at") else None,
            "subscription_ends_at": datetime.fromisoformat(operator["subscription_ends_at"]) if operator.get("subscription_ends_at") else None})

@api_router.put("/operator/profile", response_model=OperatorResponse)
async def update_operator_profile(data: OperatorUpdate, current_user: dict = Depends(require_operator)):
    """Update current operator's profile"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin users don't have operator profile")
    
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode. Please renew subscription.")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    # Remove status from operator self-update
    update_data.pop("status", None)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.operators.update_one({"id": current_user["operator_id"]}, {"$set": update_data})
    
    updated = await db.operators.find_one({"id": current_user["operator_id"]}, {"_id": 0})
    return OperatorResponse(**{**updated, "created_at": datetime.fromisoformat(updated["created_at"]),
            "trial_ends_at": datetime.fromisoformat(updated["trial_ends_at"]) if updated.get("trial_ends_at") else None,
            "subscription_ends_at": datetime.fromisoformat(updated["subscription_ends_at"]) if updated.get("subscription_ends_at") else None})

# ============== OPERATOR: INVOICE CUSTOMIZATION ==============

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

@api_router.get("/operator/invoice-settings")
async def get_invoice_settings(current_user: dict = Depends(require_operator)):
    """Get invoice customization settings"""
    settings = await db.invoice_settings.find_one(
        {"operator_id": current_user["operator_id"]},
        {"_id": 0}
    )
    if not settings:
        # Get from operator profile
        operator = await db.operators.find_one({"id": current_user["operator_id"]}, {"_id": 0})
        return {
            "company_name": operator.get("company_name", ""),
            "company_address": "",
            "company_phone": operator.get("phone", ""),
            "company_email": operator.get("email", ""),
            "logo_url": None,
            "invoice_prefix": "INV",
            "invoice_footer": None,
            "show_gst": True,
            "terms_conditions": None
        }
    return settings

@api_router.put("/operator/invoice-settings")
async def update_invoice_settings(data: InvoiceCustomization, current_user: dict = Depends(require_operator)):
    """Update invoice customization settings"""
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    now = datetime.now(timezone.utc)
    settings = {
        "operator_id": current_user["operator_id"],
        **data.model_dump(),
        "updated_at": now.isoformat()
    }
    
    await db.invoice_settings.update_one(
        {"operator_id": current_user["operator_id"]},
        {"$set": settings},
        upsert=True
    )
    
    return {"message": "Invoice settings updated"}

# ============== OPERATOR: ANNOUNCEMENTS/NOTIFICATIONS ==============

class AnnouncementCreate(BaseModel):
    title: str
    message: str
    send_whatsapp: bool = True
    send_to_all: bool = True
    subscriber_ids: Optional[List[str]] = None

@api_router.post("/operator/announcements")
async def create_announcement(data: AnnouncementCreate, current_user: dict = Depends(require_operator)):
    """Create and send announcement to subscribers"""
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    # Check if operator has notification addon
    operator = await db.operators.find_one({"id": current_user["operator_id"]}, {"_id": 0})
    active_addons = operator.get("active_addons", [])
    saas_plan = await db.saas_plans.find_one({"id": operator.get("saas_plan_id")}, {"_id": 0})
    
    if not (saas_plan and saas_plan.get("notification_module")) and "notifications" not in active_addons:
        raise HTTPException(status_code=403, detail="Notification addon not enabled")
    
    now = datetime.now(timezone.utc)
    
    # Get subscribers
    if data.send_to_all:
        subscribers = await db.subscribers.find(
            {"operator_id": current_user["operator_id"], "status": "active", "deleted_at": None},
            {"_id": 0}
        ).to_list(10000)
    else:
        subscribers = await db.subscribers.find(
            {"id": {"$in": data.subscriber_ids or []}, "operator_id": current_user["operator_id"], "deleted_at": None},
            {"_id": 0}
        ).to_list(10000)
    
    # Create announcement record
    announcement = {
        "id": generate_id(),
        "operator_id": current_user["operator_id"],
        "title": data.title,
        "message": data.message,
        "recipient_count": len(subscribers),
        "sent_via_whatsapp": data.send_whatsapp,
        "created_by": current_user["id"],
        "created_at": now.isoformat()
    }
    await db.announcements.insert_one(announcement)
    
    # Queue WhatsApp messages if enabled
    sent_count = 0
    if data.send_whatsapp:
        for sub in subscribers:
            notification = {
                "id": generate_id(),
                "operator_id": current_user["operator_id"],
                "subscriber_id": sub["id"],
                "notification_type": "announcement",
                "whatsapp_number": sub["whatsapp_number"],
                "message": f"*{data.title}*\n\n{data.message}",
                "status": "pending",
                "created_at": now.isoformat()
            }
            await db.notification_queue.insert_one(notification)
            sent_count += 1
    
    return {
        "message": "Announcement created",
        "recipients": len(subscribers),
        "queued_notifications": sent_count
    }

@api_router.get("/operator/announcements")
async def get_announcements(current_user: dict = Depends(require_operator)):
    """Get all announcements"""
    announcements = await db.announcements.find(
        {"operator_id": current_user["operator_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return announcements

# ============== OPERATOR: DASHBOARD ==============

@api_router.get("/operator/dashboard")
async def get_operator_dashboard(current_user: dict = Depends(require_operator)):
    """Get operator dashboard data"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Use admin dashboard")
    
    operator_id = current_user["operator_id"]
    
    total_subscribers = await db.subscribers.count_documents({"operator_id": operator_id, "deleted_at": None})
    active_subscribers = await db.subscribers.count_documents({"operator_id": operator_id, "status": "active", "deleted_at": None})
    total_invoices = await db.invoices.count_documents({"operator_id": operator_id, "deleted_at": None})
    pending_invoices = await db.invoices.count_documents({"operator_id": operator_id, "status": "pending", "deleted_at": None})
    overdue_invoices = await db.invoices.count_documents({"operator_id": operator_id, "status": "overdue", "deleted_at": None})
    paid_invoices = await db.invoices.count_documents({"operator_id": operator_id, "status": "paid", "deleted_at": None})
    
    # Calculate revenue
    paid_invoice_list = await db.invoices.find(
        {"operator_id": operator_id, "status": "paid", "deleted_at": None},
        {"_id": 0, "final_amount": 1}
    ).to_list(1000)
    total_revenue = sum(inv.get("final_amount", 0) for inv in paid_invoice_list)
    
    # Get operator info
    operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
    
    return {
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers,
        "total_invoices": total_invoices,
        "pending_invoices": pending_invoices,
        "overdue_invoices": overdue_invoices,
        "paid_invoices": paid_invoices,
        "total_revenue": total_revenue,
        "is_read_only": operator.get("is_read_only", False) if operator else False,
        "subscription_ends_at": operator.get("subscription_ends_at") if operator else None,
        "trial_ends_at": operator.get("trial_ends_at") if operator else None,
        "status": operator.get("status") if operator else "unknown"
    }

# ============== OPERATOR: PLANS ==============

@api_router.post("/operator/plans", response_model=OperatorPlanResponse)
async def create_operator_plan(data: OperatorPlanCreate, current_user: dict = Depends(require_operator)):
    """Create a service plan (Operator only)"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot create operator plans")
    
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    now = datetime.now(timezone.utc)
    plan = {
        "id": generate_id(),
        "name": data.name,
        "price": data.price,
        "validity": data.validity,
        "tax_percentage": data.tax_percentage,
        "tax_type": data.tax_type,
        "description": data.description,
        "status": "active",
        "operator_id": current_user["operator_id"],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.operator_plans.insert_one(plan)
    
    return OperatorPlanResponse(**{**plan, "created_at": now})

@api_router.get("/operator/plans", response_model=List[OperatorPlanResponse])
async def get_operator_plans(current_user: dict = Depends(require_operator)):
    """Get all service plans for operator"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator plans")
    
    plans = await db.operator_plans.find(
        {"operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0}
    ).to_list(100)
    
    return [OperatorPlanResponse(**{**p, "created_at": datetime.fromisoformat(p["created_at"])}) for p in plans]

@api_router.put("/operator/plans/{plan_id}", response_model=OperatorPlanResponse)
async def update_operator_plan(plan_id: str, data: OperatorPlanCreate, current_user: dict = Depends(require_operator)):
    """Update a service plan"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot update operator plans")
    
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    existing = await db.operator_plans.find_one(
        {"id": plan_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    update_data = data.model_dump()
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.operator_plans.update_one({"id": plan_id}, {"$set": update_data})
    
    updated = await db.operator_plans.find_one({"id": plan_id}, {"_id": 0})
    return OperatorPlanResponse(**{**updated, "created_at": datetime.fromisoformat(updated["created_at"])})

@api_router.delete("/operator/plans/{plan_id}")
async def delete_operator_plan(plan_id: str, current_user: dict = Depends(require_operator_no_staff)):
    """Soft delete a service plan"""
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    result = await db.operator_plans.update_one(
        {"id": plan_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Plan deleted"}

# ============== OPERATOR: SUBSCRIBERS ==============

@api_router.post("/operator/subscribers", response_model=SubscriberResponse)
async def create_subscriber(data: SubscriberCreate, current_user: dict = Depends(require_operator)):
    """Create a subscriber"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot create subscribers")
    
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    # Check subscriber limit
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if operator:
        plan = await db.saas_plans.find_one({"id": operator.get("saas_plan_id"), "deleted_at": None}, {"_id": 0})
        if plan:
            current_count = await db.subscribers.count_documents({"operator_id": current_user["operator_id"], "deleted_at": None})
            if current_count >= plan["max_subscribers"]:
                raise HTTPException(status_code=403, detail=f"Subscriber limit ({plan['max_subscribers']}) reached")
    
    # Verify plan exists
    op_plan = await db.operator_plans.find_one(
        {"id": data.plan_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0}
    )
    if not op_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    now = datetime.now(timezone.utc)
    subscriber = {
        "id": generate_id(),
        "name": data.name,
        "whatsapp_number": data.whatsapp_number,
        "email": data.email,
        "address": data.address,
        "plan_id": data.plan_id,
        "plan_name": op_plan["name"],
        "billing_date": data.billing_date,
        "discount": data.discount,
        "status": "active",
        "operator_id": current_user["operator_id"],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.subscribers.insert_one(subscriber)
    
    return SubscriberResponse(**{**subscriber, "created_at": now})

@api_router.get("/operator/subscribers", response_model=List[SubscriberResponse])
async def get_subscribers(
    status: Optional[str] = None,
    plan_id: Optional[str] = None,
    current_user: dict = Depends(require_operator)
):
    """Get all subscribers"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator subscribers")
    
    query = {"operator_id": current_user["operator_id"], "deleted_at": None}
    if status:
        query["status"] = status
    if plan_id:
        query["plan_id"] = plan_id
    
    subscribers = await db.subscribers.find(query, {"_id": 0}).to_list(1000)
    return [SubscriberResponse(**{**s, "created_at": datetime.fromisoformat(s["created_at"])}) for s in subscribers]

@api_router.get("/operator/subscribers/{subscriber_id}", response_model=SubscriberResponse)
async def get_subscriber(subscriber_id: str, current_user: dict = Depends(require_operator)):
    """Get subscriber details"""
    subscriber = await db.subscribers.find_one(
        {"id": subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0}
    )
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return SubscriberResponse(**{**subscriber, "created_at": datetime.fromisoformat(subscriber["created_at"])})

@api_router.put("/operator/subscribers/{subscriber_id}", response_model=SubscriberResponse)
async def update_subscriber(subscriber_id: str, data: SubscriberCreate, current_user: dict = Depends(require_operator)):
    """Update subscriber"""
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    existing = await db.subscribers.find_one(
        {"id": subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    # Get plan name
    op_plan = await db.operator_plans.find_one({"id": data.plan_id, "deleted_at": None}, {"_id": 0})
    
    update_data = data.model_dump()
    update_data["plan_name"] = op_plan["name"] if op_plan else None
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.subscribers.update_one({"id": subscriber_id}, {"$set": update_data})
    
    updated = await db.subscribers.find_one({"id": subscriber_id}, {"_id": 0})
    return SubscriberResponse(**{**updated, "created_at": datetime.fromisoformat(updated["created_at"])})

@api_router.delete("/operator/subscribers/{subscriber_id}")
async def delete_subscriber(subscriber_id: str, current_user: dict = Depends(require_operator_no_staff)):
    """Soft delete subscriber"""
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    result = await db.subscribers.update_one(
        {"id": subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"message": "Subscriber deleted"}

# ============== OPERATOR: INVOICES ==============

@api_router.post("/operator/invoices", response_model=InvoiceResponse)
async def create_invoice(data: InvoiceCreate, current_user: dict = Depends(require_operator)):
    """Create an invoice manually"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot create invoices")
    
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    # Get subscriber
    subscriber = await db.subscribers.find_one(
        {"id": data.subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0}
    )
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    # Get plan
    plan = await db.operator_plans.find_one({"id": data.plan_id, "deleted_at": None}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Get operator for GST settings
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    
    # Calculate tax
    tax_amount = 0
    if operator.get("charge_gst") and plan.get("tax_percentage", 0) > 0:
        if plan.get("tax_type") == "exclusive":
            tax_amount = (data.base_amount - data.discount) * (plan["tax_percentage"] / 100)
        elif plan.get("tax_type") == "inclusive":
            tax_amount = (data.base_amount - data.discount) - ((data.base_amount - data.discount) / (1 + plan["tax_percentage"] / 100))
    
    final_amount = data.base_amount - data.discount + (tax_amount if plan.get("tax_type") == "exclusive" else 0)
    
    now = datetime.now(timezone.utc)
    invoice = {
        "id": generate_id(),
        "invoice_number": generate_invoice_number(current_user["operator_id"]),
        "subscriber_id": data.subscriber_id,
        "subscriber_name": subscriber["name"],
        "plan_id": data.plan_id,
        "plan_name": plan["name"],
        "base_amount": data.base_amount,
        "discount": data.discount,
        "tax_amount": round(tax_amount, 2),
        "final_amount": round(final_amount, 2),
        "service_start_date": data.service_start_date.isoformat(),
        "service_end_date": data.service_end_date.isoformat(),
        "due_date": data.due_date.isoformat(),
        "status": "pending",
        "payment_id": None,
        "operator_id": current_user["operator_id"],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.invoices.insert_one(invoice)
    
    return InvoiceResponse(**{
        **invoice,
        "created_at": now,
        "service_start_date": data.service_start_date,
        "service_end_date": data.service_end_date,
        "due_date": data.due_date
    })

@api_router.get("/operator/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    status: Optional[str] = None,
    subscriber_id: Optional[str] = None,
    current_user: dict = Depends(require_operator)
):
    """Get all invoices"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator invoices")
    
    query = {"operator_id": current_user["operator_id"], "deleted_at": None}
    if status:
        query["status"] = status
    if subscriber_id:
        query["subscriber_id"] = subscriber_id
    
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    result = []
    for inv in invoices:
        result.append(InvoiceResponse(**{
            **inv,
            "created_at": datetime.fromisoformat(inv["created_at"]),
            "service_start_date": datetime.fromisoformat(inv["service_start_date"]),
            "service_end_date": datetime.fromisoformat(inv["service_end_date"]),
            "due_date": datetime.fromisoformat(inv["due_date"])
        }))
    return result

@api_router.put("/operator/invoices/{invoice_id}/status")
async def update_invoice_status(invoice_id: str, status: str = Query(...), current_user: dict = Depends(require_operator)):
    """Update invoice status"""
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    if status not in ["pending", "paid", "overdue", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await db.invoices.update_one(
        {"id": invoice_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": f"Invoice marked as {status}"}

# ============== OPERATOR: STAFF ==============

@api_router.post("/operator/staff", response_model=StaffResponse)
async def create_staff(data: StaffCreate, current_user: dict = Depends(require_operator)):
    """Create staff member"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot create staff")
    
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    # Check staff limit
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if operator:
        plan = await db.saas_plans.find_one({"id": operator.get("saas_plan_id"), "deleted_at": None}, {"_id": 0})
        if plan:
            current_count = await db.users.count_documents({
                "operator_id": current_user["operator_id"],
                "role": "staff",
                "deleted_at": None
            })
            if current_count >= plan["max_staff"]:
                raise HTTPException(status_code=403, detail=f"Staff limit ({plan['max_staff']}) reached")
    
    # Check email uniqueness
    existing = await db.users.find_one({"email": data.email, "deleted_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    now = datetime.now(timezone.utc)
    user_id = generate_id()
    
    user = {
        "id": user_id,
        "email": data.email,
        "name": data.name,
        "phone": data.phone,
        "password": hash_password(data.password),
        "role": "staff",
        "permissions": data.permissions,
        "operator_id": current_user["operator_id"],
        "status": "active",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.users.insert_one(user)
    
    return StaffResponse(
        id=user_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
        role="staff",
        permissions=data.permissions,
        operator_id=current_user["operator_id"],
        status="active",
        created_at=now
    )

@api_router.get("/operator/staff", response_model=List[StaffResponse])
async def get_staff(current_user: dict = Depends(require_operator)):
    """Get all staff members"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator staff")
    
    staff = await db.users.find(
        {"operator_id": current_user["operator_id"], "role": "staff", "deleted_at": None},
        {"_id": 0, "password": 0}
    ).to_list(100)
    
    return [StaffResponse(**{**s, "permissions": s.get("permissions", []), "created_at": datetime.fromisoformat(s["created_at"])}) for s in staff]

@api_router.delete("/operator/staff/{staff_id}")
async def delete_staff(staff_id: str, current_user: dict = Depends(require_operator_no_staff)):
    """Soft delete staff member"""
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    result = await db.users.update_one(
        {"id": staff_id, "operator_id": current_user["operator_id"], "role": "staff", "deleted_at": None},
        {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"message": "Staff deleted"}

# ============== OPERATOR: PAYMENT GATEWAY ==============

@api_router.post("/operator/payment-gateway")
async def configure_payment_gateway(data: PaymentGatewayConfig, current_user: dict = Depends(require_operator)):
    """Configure payment gateway"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot configure operator payment gateway")
    
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    # Check if payment gateway setup add-on is enabled
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if operator:
        plan = await db.saas_plans.find_one({"id": operator.get("saas_plan_id"), "deleted_at": None}, {"_id": 0})
        if plan and not plan.get("payment_gateway_setup"):
            raise HTTPException(status_code=403, detail="Payment gateway setup add-on is not enabled")
    
    now = datetime.now(timezone.utc)
    gateway_config = {
        "id": generate_id(),
        "operator_id": current_user["operator_id"],
        "gateway_type": data.gateway_type,
        "api_key": data.api_key,  # In production, encrypt this
        "api_secret": data.api_secret,  # In production, encrypt this
        "webhook_secret": data.webhook_secret,
        "is_active": True,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Upsert - update if exists, create if not
    await db.payment_gateways.update_one(
        {"operator_id": current_user["operator_id"]},
        {"$set": gateway_config},
        upsert=True
    )
    
    return {"message": "Payment gateway configured successfully"}

@api_router.get("/operator/payment-gateway")
async def get_payment_gateway(current_user: dict = Depends(require_operator)):
    """Get payment gateway configuration"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator payment gateway")
    
    gateway = await db.payment_gateways.find_one(
        {"operator_id": current_user["operator_id"]},
        {"_id": 0, "api_secret": 0}  # Don't expose secret
    )
    if not gateway:
        return {"configured": False}
    
    return {
        "configured": True,
        "gateway_type": gateway["gateway_type"],
        "api_key": gateway["api_key"][:8] + "****",  # Mask the key
        "is_active": gateway.get("is_active", False)
    }

# ============== OPERATOR: REPORTS ==============

@api_router.get("/operator/reports/revenue")
async def get_revenue_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_operator)
):
    """Get revenue report"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator reports")
    
    query = {"operator_id": current_user["operator_id"], "status": "paid", "deleted_at": None}
    
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(10000)
    
    total_revenue = sum(inv.get("final_amount", 0) for inv in invoices)
    total_base = sum(inv.get("base_amount", 0) for inv in invoices)
    total_tax = sum(inv.get("tax_amount", 0) for inv in invoices)
    total_discount = sum(inv.get("discount", 0) for inv in invoices)
    
    return {
        "total_invoices": len(invoices),
        "total_revenue": round(total_revenue, 2),
        "total_base_amount": round(total_base, 2),
        "total_tax": round(total_tax, 2),
        "total_discount": round(total_discount, 2)
    }

@api_router.get("/operator/reports/gst-summary")
async def get_gst_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_operator)
):
    """Get GST summary report"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator reports")
    
    query = {"operator_id": current_user["operator_id"], "deleted_at": None}
    
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(10000)
    
    total_taxable = sum(inv.get("base_amount", 0) - inv.get("discount", 0) for inv in invoices)
    total_gst = sum(inv.get("tax_amount", 0) for inv in invoices)
    
    return {
        "total_taxable_amount": round(total_taxable, 2),
        "total_gst_collected": round(total_gst, 2),
        "cgst": round(total_gst / 2, 2),
        "sgst": round(total_gst / 2, 2)
    }

@api_router.get("/operator/reports/pending-overdue")
async def get_pending_overdue_report(current_user: dict = Depends(require_operator)):
    """Get pending and overdue invoices report"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Admin cannot access operator reports")
    
    pending = await db.invoices.find(
        {"operator_id": current_user["operator_id"], "status": "pending", "deleted_at": None},
        {"_id": 0}
    ).to_list(1000)
    
    overdue = await db.invoices.find(
        {"operator_id": current_user["operator_id"], "status": "overdue", "deleted_at": None},
        {"_id": 0}
    ).to_list(1000)
    
    return {
        "pending_count": len(pending),
        "pending_amount": round(sum(inv.get("final_amount", 0) for inv in pending), 2),
        "overdue_count": len(overdue),
        "overdue_amount": round(sum(inv.get("final_amount", 0) for inv in overdue), 2)
    }

# ============== OPERATOR: AUDIT LOGS ==============

@api_router.get("/operator/audit-logs", response_model=List[AuditLogResponse])
async def get_operator_audit_logs(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(require_operator)
):
    """Get audit logs for operator"""
    if current_user["role"] == "admin":
        raise HTTPException(status_code=400, detail="Use admin audit logs endpoint")
    
    # Check if audit logs add-on is enabled
    operator = await db.operators.find_one({"id": current_user["operator_id"], "deleted_at": None}, {"_id": 0})
    if operator:
        plan = await db.saas_plans.find_one({"id": operator.get("saas_plan_id"), "deleted_at": None}, {"_id": 0})
        if plan and not plan.get("audit_logs"):
            raise HTTPException(status_code=403, detail="Audit logs add-on is not enabled")
    
    logs = await db.audit_logs.find(
        {"operator_id": current_user["operator_id"]},
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return [AuditLogResponse(**{**l, "created_at": datetime.fromisoformat(l["created_at"])}) for l in logs]

# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Multi-Tenant SaaS Billing Platform"}

# ============== SEED DATA ==============

@api_router.post("/seed")
async def seed_data():
    """Seed initial data (Admin account and default SaaS plan)"""
    # Check if admin exists
    admin = await db.users.find_one({"role": "admin", "deleted_at": None})
    if admin:
        return {"message": "Data already seeded"}
    
    now = datetime.now(timezone.utc)
    
    # Create admin user
    admin_user = {
        "id": generate_id(),
        "email": "admin@saas.com",
        "name": "Super Admin",
        "phone": "9999999999",
        "password": hash_password("admin123"),
        "role": "admin",
        "operator_id": None,
        "status": "active",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None
    }
    await db.users.insert_one(admin_user)
    
    # Create default SaaS plans
    plans = [
        {
            "id": generate_id(),
            "name": "Starter (Trial)",
            "monthly_price": 0,
            "max_subscribers": 10,
            "max_staff": 1,
            "trial_enabled": True,
            "trial_days": 3,
            "notification_module": False,
            "auto_reminder": False,
            "audit_logs": False,
            "payment_gateway_setup": False,
            "gst_applicable": False,
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None
        },
        {
            "id": generate_id(),
            "name": "Basic",
            "monthly_price": 999,
            "max_subscribers": 100,
            "max_staff": 3,
            "trial_enabled": False,
            "trial_days": 0,
            "notification_module": True,
            "auto_reminder": True,
            "audit_logs": False,
            "payment_gateway_setup": True,
            "gst_applicable": True,
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None
        },
        {
            "id": generate_id(),
            "name": "Professional",
            "monthly_price": 2499,
            "max_subscribers": 500,
            "max_staff": 10,
            "trial_enabled": False,
            "trial_days": 0,
            "notification_module": True,
            "auto_reminder": True,
            "audit_logs": True,
            "payment_gateway_setup": True,
            "gst_applicable": True,
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None
        },
        {
            "id": generate_id(),
            "name": "Enterprise",
            "monthly_price": 4999,
            "max_subscribers": 2000,
            "max_staff": 25,
            "trial_enabled": False,
            "trial_days": 0,
            "notification_module": True,
            "auto_reminder": True,
            "audit_logs": True,
            "payment_gateway_setup": True,
            "gst_applicable": True,
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None
        }
    ]
    await db.saas_plans.insert_many(plans)
    
    return {"message": "Data seeded successfully", "admin_email": "admin@saas.com", "admin_password": "admin123"}

# ============== PAYMENT LINK & RAZORPAY ENDPOINTS ==============

class PaymentLinkCreate(BaseModel):
    invoice_id: str

class PaymentLinkResponse(BaseModel):
    payment_link: str
    payment_link_id: str
    qr_code: str
    amount: float

@api_router.post("/operator/invoices/{invoice_id}/payment-link", response_model=PaymentLinkResponse)
async def create_payment_link(invoice_id: str, current_user: dict = Depends(require_operator)):
    """Generate Razorpay payment link for an invoice"""
    from services.razorpay_service import RazorpayService
    
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    # Get invoice
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get payment gateway config
    gateway = await db.payment_gateways.find_one(
        {"operator_id": current_user["operator_id"]},
        {"_id": 0}
    )
    if not gateway or not gateway.get("is_active"):
        raise HTTPException(status_code=400, detail="Payment gateway not configured")
    
    # Get subscriber
    subscriber = await db.subscribers.find_one(
        {"id": invoice["subscriber_id"], "deleted_at": None},
        {"_id": 0}
    )
    
    try:
        razorpay_service = RazorpayService(gateway["api_key"], gateway["api_secret"])
        
        payment_link = razorpay_service.create_payment_link(
            amount=invoice["final_amount"],
            description=f"Invoice {invoice['invoice_number']}",
            customer_name=subscriber["name"] if subscriber else "",
            customer_email=subscriber.get("email", "") if subscriber else "",
            customer_phone=subscriber.get("whatsapp_number", "") if subscriber else "",
            invoice_number=invoice["invoice_number"]
        )
        
        # Generate QR code
        qr_code = razorpay_service.generate_qr_code(payment_link["short_url"])
        
        # Update invoice with payment link
        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {
                "payment_link": payment_link["short_url"],
                "payment_link_id": payment_link["id"],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return PaymentLinkResponse(
            payment_link=payment_link["short_url"],
            payment_link_id=payment_link["id"],
            qr_code=qr_code,
            amount=invoice["final_amount"]
        )
        
    except Exception as e:
        logger.error(f"Payment link creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create payment link: {str(e)}")

@api_router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    """Handle Razorpay payment webhooks"""
    try:
        body = await request.body()
        signature = request.headers.get("X-Razorpay-Signature", "")
        
        payload = json.loads(body)
        event = payload.get("event", "")
        
        logger.info(f"Razorpay webhook: {event}")
        
        if event == "payment_link.paid":
            payment_link = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
            payment_link_id = payment_link.get("id")
            
            # Find invoice by payment link ID
            invoice = await db.invoices.find_one(
                {"payment_link_id": payment_link_id, "deleted_at": None},
                {"_id": 0}
            )
            
            if invoice:
                now = datetime.now(timezone.utc)
                
                # Update invoice status
                await db.invoices.update_one(
                    {"id": invoice["id"]},
                    {"$set": {
                        "status": "paid",
                        "payment_id": payment_link.get("payments", [{}])[0].get("payment_id") if payment_link.get("payments") else None,
                        "updated_at": now.isoformat()
                    }}
                )
                
                logger.info(f"Invoice {invoice['invoice_number']} marked as paid")
        
        elif event == "payment.captured":
            payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
            notes = payment.get("notes", {})
            invoice_number = notes.get("invoice_number")
            
            if invoice_number:
                await db.invoices.update_one(
                    {"invoice_number": invoice_number, "deleted_at": None},
                    {"$set": {
                        "status": "paid",
                        "payment_id": payment.get("id"),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

# ============== PDF INVOICE GENERATION ==============

@api_router.get("/operator/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(invoice_id: str, current_user: dict = Depends(require_operator)):
    """Generate and download invoice PDF"""
    from services.pdf_service import InvoicePDFService
    from services.razorpay_service import RazorpayService
    from fastapi.responses import Response
    
    # Get invoice
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get operator
    operator = await db.operators.find_one(
        {"id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0}
    )
    
    # Get subscriber
    subscriber = await db.subscribers.find_one(
        {"id": invoice["subscriber_id"], "deleted_at": None},
        {"_id": 0}
    )
    
    # Get plan
    plan = await db.operator_plans.find_one(
        {"id": invoice["plan_id"], "deleted_at": None},
        {"_id": 0}
    )
    
    # Generate QR code if payment link exists
    qr_code = None
    if invoice.get("payment_link"):
        gateway = await db.payment_gateways.find_one(
            {"operator_id": current_user["operator_id"]},
            {"_id": 0}
        )
        if gateway:
            try:
                razorpay_service = RazorpayService(gateway["api_key"], gateway["api_secret"])
                qr_code = razorpay_service.generate_qr_code(invoice["payment_link"])
            except:
                pass
    
    # Generate PDF
    pdf_service = InvoicePDFService()
    pdf_bytes = pdf_service.generate_invoice_pdf(
        invoice_data=invoice,
        operator_data=operator or {},
        subscriber_data=subscriber or {},
        plan_data=plan or {},
        qr_code_base64=qr_code
    )
    
    filename = f"Invoice_{invoice['invoice_number']}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

# ============== WHATSAPP NOTIFICATIONS ==============

class WhatsAppConfig(BaseModel):
    phone_number_id: str
    access_token: str

@api_router.post("/operator/whatsapp-config")
async def configure_whatsapp(data: WhatsAppConfig, current_user: dict = Depends(require_operator)):
    """Configure WhatsApp Business API credentials"""
    if await check_operator_read_only(current_user["operator_id"]):
        raise HTTPException(status_code=403, detail="Account is in read-only mode")
    
    now = datetime.now(timezone.utc)
    config = {
        "id": generate_id(),
        "operator_id": current_user["operator_id"],
        "phone_number_id": data.phone_number_id,
        "access_token": data.access_token,
        "is_active": True,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.whatsapp_configs.update_one(
        {"operator_id": current_user["operator_id"]},
        {"$set": config},
        upsert=True
    )
    
    return {"message": "WhatsApp configured successfully"}

@api_router.get("/operator/whatsapp-config")
async def get_whatsapp_config(current_user: dict = Depends(require_operator)):
    """Get WhatsApp configuration status"""
    config = await db.whatsapp_configs.find_one(
        {"operator_id": current_user["operator_id"]},
        {"_id": 0, "access_token": 0}
    )
    if config:
        return {"configured": True, "phone_number_id": config.get("phone_number_id", "")[:10] + "***"}
    return {"configured": False}

class SendNotificationRequest(BaseModel):
    invoice_id: str
    notification_type: str = "invoice"  # invoice, reminder

@api_router.post("/operator/send-notification")
async def send_whatsapp_notification(data: SendNotificationRequest, current_user: dict = Depends(require_operator)):
    """Send WhatsApp notification for an invoice"""
    from services.whatsapp_service import WhatsAppService
    
    # Get WhatsApp config
    wa_config = await db.whatsapp_configs.find_one(
        {"operator_id": current_user["operator_id"], "is_active": True},
        {"_id": 0}
    )
    if not wa_config:
        raise HTTPException(status_code=400, detail="WhatsApp not configured")
    
    # Get invoice
    invoice = await db.invoices.find_one(
        {"id": data.invoice_id, "operator_id": current_user["operator_id"], "deleted_at": None},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get subscriber
    subscriber = await db.subscribers.find_one(
        {"id": invoice["subscriber_id"], "deleted_at": None},
        {"_id": 0}
    )
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    try:
        wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
        
        if data.notification_type == "reminder":
            # Calculate days overdue
            due_date = datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00'))
            days_overdue = max(0, (datetime.now(timezone.utc) - due_date).days)
            
            result = await wa_service.send_payment_reminder(
                recipient_phone=subscriber["whatsapp_number"],
                customer_name=subscriber["name"],
                invoice_number=invoice["invoice_number"],
                amount_due=f"₹{invoice['final_amount']:,.2f}",
                days_overdue=str(days_overdue),
                payment_link=invoice.get("payment_link")
            )
        else:
            result = await wa_service.send_invoice_notification(
                recipient_phone=subscriber["whatsapp_number"],
                customer_name=subscriber["name"],
                invoice_number=invoice["invoice_number"],
                amount=f"₹{invoice['final_amount']:,.2f}",
                due_date=datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00')).strftime("%d %b %Y"),
                payment_link=invoice.get("payment_link")
            )
        
        return {"success": True, "message_id": result.get("messages", [{}])[0].get("id")}
        
    except Exception as e:
        logger.error(f"WhatsApp notification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")

class BulkNotificationRequest(BaseModel):
    subscriber_ids: List[str]
    message_template: str = "invoice"

@api_router.post("/operator/bulk-notification")
async def send_bulk_notification(data: BulkNotificationRequest, current_user: dict = Depends(require_operator)):
    """Send bulk WhatsApp notifications"""
    from services.whatsapp_service import WhatsAppService
    
    wa_config = await db.whatsapp_configs.find_one(
        {"operator_id": current_user["operator_id"], "is_active": True},
        {"_id": 0}
    )
    if not wa_config:
        raise HTTPException(status_code=400, detail="WhatsApp not configured")
    
    results = {"sent": 0, "failed": 0, "errors": []}
    
    wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
    
    for subscriber_id in data.subscriber_ids:
        try:
            subscriber = await db.subscribers.find_one(
                {"id": subscriber_id, "operator_id": current_user["operator_id"], "deleted_at": None},
                {"_id": 0}
            )
            if not subscriber:
                continue
            
            # Get latest pending invoice
            invoice = await db.invoices.find_one(
                {"subscriber_id": subscriber_id, "status": {"$in": ["pending", "overdue"]}, "deleted_at": None},
                {"_id": 0}
            )
            
            if invoice:
                await wa_service.send_invoice_notification(
                    recipient_phone=subscriber["whatsapp_number"],
                    customer_name=subscriber["name"],
                    invoice_number=invoice["invoice_number"],
                    amount=f"₹{invoice['final_amount']:,.2f}",
                    due_date=datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00')).strftime("%d %b %Y"),
                    payment_link=invoice.get("payment_link")
                )
                results["sent"] += 1
                
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"subscriber_id": subscriber_id, "error": str(e)})
    
    return results

# ============== CRON JOB ENDPOINTS ==============

@api_router.post("/admin/cron/generate-invoices")
async def trigger_invoice_generation(current_user: dict = Depends(require_admin)):
    """Manually trigger invoice generation (Admin only)"""
    from services.cron_service import CronJobService
    
    service = CronJobService(db)
    results = await service.generate_upcoming_invoices(days_before=5)
    
    await log_audit(
        current_user["id"], current_user["name"], current_user["role"],
        "trigger", "cron_jobs", None, {"action": "generate_invoices", "results": results}
    )
    
    return results

@api_router.post("/admin/cron/send-reminders")
async def trigger_reminders(current_user: dict = Depends(require_admin)):
    """Manually trigger overdue reminders (Admin only)"""
    from services.cron_service import CronJobService
    
    service = CronJobService(db)
    results = await service.send_overdue_reminders(days_overdue=1)
    
    return results

@api_router.post("/admin/cron/check-expiry")
async def trigger_expiry_check(current_user: dict = Depends(require_admin)):
    """Manually trigger subscription expiry check (Admin only)"""
    from services.cron_service import CronJobService
    
    service = CronJobService(db)
    results = await service.check_subscription_expiry()
    
    return results

# Include the router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
