"""
Seed comprehensive sample data for testing the settlement flow.
Run this script to populate the database with operators, subscribers, invoices (paid & pending),
and then trigger settlement processing.
"""
import asyncio
import uuid
import bcrypt
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']


def generate_id():
    return str(uuid.uuid4())


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


async def seed_settlement_data():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    now = datetime.now(timezone.utc)

    print("=== Seeding Settlement Sample Data ===\n")

    # 1. Seed admin user (idempotent)
    if not await db.users.find_one({"role": "admin", "deleted_at": None}):
        admin_user = {
            "id": generate_id(), "email": "admin@saas.com", "name": "Super Admin",
            "phone": "9999999999", "password": hash_password("admin123"),
            "role": "admin", "operator_id": None, "status": "active",
            "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None
        }
        await db.users.insert_one(admin_user)
        print("✅ Admin user created (admin@saas.com / admin123)")
    else:
        print("⏭️  Admin user already exists")

    # 2. Seed addons
    required_addons = [
        {"code": "audit_log",              "name": "Audit Logs",               "price": 100},
        {"code": "payment_gateway",        "name": "Payment Gateway",          "price": 100},
        {"code": "custom_payment_gateway", "name": "Custom Payment Gateway",   "price": 100},
        {"code": "announcement",           "name": "Announcements",            "price": 100},
        {"code": "whatsapp_notifications", "name": "WhatsApp Notifications",   "price": 100},
        {"code": "staff_management",       "name": "Staff Management",         "price": 100},
    ]
    for addon_data in required_addons:
        existing = await db.addons.find_one({"code": addon_data["code"], "deleted_at": None})
        if not existing:
            await db.addons.insert_one({
                "id": generate_id(), **addon_data,
                "description": f"{addon_data['name']} addon",
                "status": "active", "created_at": now.isoformat(), "deleted_at": None
            })
    print("✅ Addons seeded")

    # 3. Seed SaaS Plans
    basic_plan_id = generate_id()
    pro_plan_id = generate_id()
    if not await db.saas_plans.find_one({"deleted_at": None}):
        plans = [
            {"id": basic_plan_id, "name": "Basic", "monthly_price": 500,
             "max_subscribers": 200, "max_staff": 0, "trial_enabled": False, "trial_days": 0,
             "gst_applicable": True, "included_addons": ["payment_gateway"],
             "platform_fee_percentage": 3.5,
             "status": "active", "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None},
            {"id": pro_plan_id, "name": "Pro", "monthly_price": 2500,
             "max_subscribers": 1000, "max_staff": 5, "trial_enabled": False, "trial_days": 0,
             "gst_applicable": True, "included_addons": ["payment_gateway", "audit_log", "announcement", "whatsapp_notifications"],
             "platform_fee_percentage": 3.0,
             "status": "active", "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None},
        ]
        await db.saas_plans.insert_many(plans)
        print(f"✅ SaaS Plans created (Basic: {basic_plan_id}, Pro: {pro_plan_id})")
    else:
        # Get existing plan IDs
        existing_plans = await db.saas_plans.find({"deleted_at": None}, {"_id": 0}).to_list(10)
        if existing_plans:
            basic_plan_id = existing_plans[0]["id"]
            if len(existing_plans) > 1:
                pro_plan_id = existing_plans[1]["id"]
        print(f"⏭️  SaaS Plans already exist (Basic: {basic_plan_id}, Pro: {pro_plan_id})")

    # 4. Set global platform settings
    await db.global_settings.update_one(
        {"type": "platform_settings"},
        {"$set": {"type": "platform_settings", "platform_fee_percentage": 2}},
        upsert=True
    )
    print("✅ Global platform fee set to 2%")

    # 5. Create platform payment gateway
    platform_gw = await db.payment_gateways.find_one({"is_platform_gateway": True, "deleted_at": None})
    if not platform_gw:
        await db.payment_gateways.insert_one({
            "id": generate_id(),
            "gateway_type": "razorpay",
            "api_key": os.environ.get("RAZORPAY_KEY_ID", "rzp_test_sFaXdx3kATIGiw"),
            "api_secret": os.environ.get("RAZORPAY_KEY_SECRET", "dOvQqMbfE2sPkYulgTeU2SpW"),
            "is_active": True,
            "is_platform_gateway": True,
            "for_operator_id": None,
            "created_at": now.isoformat(),
            "deleted_at": None,
        })
        print("✅ Platform payment gateway created")
    else:
        print("⏭️  Platform payment gateway already exists")

    # ---------- OPERATOR 1: Krishna Cable Network (Pro plan) ----------
    op1_id = generate_id()
    op1_user_id = generate_id()
    op1_exists = await db.operators.find_one({"company_name": "Krishna Cable Network", "deleted_at": None})
    if not op1_exists:
        op1_data = {
            "id": op1_id,
            "company_name": "Krishna Cable Network",
            "owner_name": "Venkat Rao",
            "email": "venkat@krishnacable.in",
            "phone": "9876543210",
            "address": "Plot 45, Industrial Area, Hyderabad 500032",
            "gstin": "36AABCK1234H1ZM",
            "charge_gst": True,
            "saas_plan_id": pro_plan_id,
            "saas_plan_name": "Pro",
            "status": "active",
            "subscription_start": (now - timedelta(days=60)).isoformat(),
            "subscription_end": (now + timedelta(days=300)).isoformat(),
            "active_addons": ["payment_gateway", "audit_log", "announcement", "whatsapp_notifications"],
            "addon_expiry": {},
            "bank_details": {
                "account_name": "Krishna Cable Network Pvt Ltd",
                "account_number": "50200045678901",
                "ifsc_code": "HDFC0001234",
                "bank_name": "HDFC Bank",
                "branch": "Banjara Hills, Hyderabad"
            },
            "created_at": (now - timedelta(days=60)).isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None,
        }
        await db.operators.insert_one(op1_data)

        op1_user = {
            "id": op1_user_id, "email": "venkat@krishnacable.in", "name": "Venkat Rao",
            "phone": "9876543210", "password": hash_password("operator123"),
            "role": "operator", "operator_id": op1_id, "status": "active",
            "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None
        }
        await db.users.insert_one(op1_user)
        print(f"✅ Operator 1 created: Krishna Cable Network (ID: {op1_id})")
    else:
        op1_id = op1_exists["id"]
        print(f"⏭️  Operator 1 already exists: Krishna Cable Network (ID: {op1_id})")

    # ---------- OPERATOR 2: Sagar Broadband (Basic plan) ----------
    op2_id = generate_id()
    op2_user_id = generate_id()
    op2_exists = await db.operators.find_one({"company_name": "Sagar Broadband", "deleted_at": None})
    if not op2_exists:
        op2_data = {
            "id": op2_id,
            "company_name": "Sagar Broadband",
            "owner_name": "Sagar Patil",
            "email": "sagar@sagarbroadband.com",
            "phone": "8765432109",
            "address": "Shop 12, MG Road, Pune 411001",
            "gstin": "27AABCS5678E1ZP",
            "charge_gst": True,
            "saas_plan_id": basic_plan_id,
            "saas_plan_name": "Basic",
            "status": "active",
            "subscription_start": (now - timedelta(days=45)).isoformat(),
            "subscription_end": (now + timedelta(days=315)).isoformat(),
            "active_addons": ["payment_gateway"],
            "addon_expiry": {},
            "bank_details": {
                "account_name": "Sagar Broadband Services",
                "account_number": "912020045612345",
                "ifsc_code": "UTIB0001567",
                "bank_name": "Axis Bank",
                "branch": "MG Road, Pune"
            },
            "created_at": (now - timedelta(days=45)).isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None,
        }
        await db.operators.insert_one(op2_data)

        op2_user = {
            "id": op2_user_id, "email": "sagar@sagarbroadband.com", "name": "Sagar Patil",
            "phone": "8765432109", "password": hash_password("operator123"),
            "role": "operator", "operator_id": op2_id, "status": "active",
            "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None
        }
        await db.users.insert_one(op2_user)
        print(f"✅ Operator 2 created: Sagar Broadband (ID: {op2_id})")
    else:
        op2_id = op2_exists["id"]
        print(f"⏭️  Operator 2 already exists: Sagar Broadband (ID: {op2_id})")

    # ---------- Create Invoice Customization for operators ----------
    for op_id, co_name, prefix in [(op1_id, "Krishna Cable Network", "KCN"), (op2_id, "Sagar Broadband", "SB")]:
        if not await db.invoice_customization.find_one({"operator_id": op_id}):
            await db.invoice_customization.insert_one({
                "operator_id": op_id,
                "company_name": co_name,
                "invoice_prefix": prefix,
                "show_gst": True,
                "footer_text": f"Thank you for choosing {co_name}",
                "invoice_template": "classic",
                "created_at": now.isoformat(),
            })
    print("✅ Invoice customization settings created")

    # ---------- SERVICE PLANS for each operator ----------
    plans_data = {
        op1_id: [
            {"name": "Basic 50 Mbps", "speed": "50 Mbps", "price": 399, "validity_days": 30,
             "tax_percentage": 18, "tax_type": "exclusive"},
            {"name": "Standard 100 Mbps", "speed": "100 Mbps", "price": 599, "validity_days": 30,
             "tax_percentage": 18, "tax_type": "exclusive"},
            {"name": "Premium 200 Mbps", "speed": "200 Mbps", "price": 999, "validity_days": 30,
             "tax_percentage": 18, "tax_type": "exclusive"},
            {"name": "Ultra 300 Mbps", "speed": "300 Mbps", "price": 1499, "validity_days": 30,
             "tax_percentage": 18, "tax_type": "exclusive"},
        ],
        op2_id: [
            {"name": "Economy 30 Mbps", "speed": "30 Mbps", "price": 299, "validity_days": 30,
             "tax_percentage": 18, "tax_type": "inclusive"},
            {"name": "Standard 100 Mbps", "speed": "100 Mbps", "price": 549, "validity_days": 30,
             "tax_percentage": 18, "tax_type": "inclusive"},
            {"name": "Premium 200 Mbps", "speed": "200 Mbps", "price": 849, "validity_days": 30,
             "tax_percentage": 18, "tax_type": "inclusive"},
        ],
    }

    plan_ids = {}  # {operator_id: [plan_id, ...]}
    for op_id, op_plans in plans_data.items():
        plan_ids[op_id] = []
        for plan in op_plans:
            existing = await db.operator_plans.find_one({
                "name": plan["name"], "operator_id": op_id, "deleted_at": None
            })
            if existing:
                plan_ids[op_id].append(existing["id"])
                continue
            pid = generate_id()
            await db.operator_plans.insert_one({
                "id": pid, "operator_id": op_id,
                "name": plan["name"], "speed": plan["speed"],
                "price": plan["price"], "validity_days": plan["validity_days"],
                "tax_percentage": plan["tax_percentage"], "tax_type": plan["tax_type"],
                "status": "active",
                "created_at": now.isoformat(), "updated_at": now.isoformat(), "deleted_at": None,
            })
            plan_ids[op_id].append(pid)
    print("✅ Service plans created for both operators")

    # ---------- SUBSCRIBERS for operator 1 (Krishna Cable Network) ----------
    op1_subscribers_data = [
        {"name": "Ramesh Kumar",    "phone": "919876543001", "email": "ramesh@gmail.com",   "address": "Flat 101, Green Park, Hyderabad"},
        {"name": "Priya Sharma",    "phone": "919876543002", "email": "priya@gmail.com",    "address": "House 22, Banjara Hills, Hyderabad"},
        {"name": "Suresh Reddy",    "phone": "919876543003", "email": "suresh@gmail.com",   "address": "Plot 8, Jubilee Hills, Hyderabad"},
        {"name": "Lakshmi Devi",    "phone": "919876543004", "email": "lakshmi@gmail.com",  "address": "Flat 305, Kukatpally, Hyderabad"},
        {"name": "Anil Prasad",     "phone": "919876543005", "email": "anil@gmail.com",     "address": "House 15, Secunderabad"},
        {"name": "Deepika Menon",   "phone": "919876543006", "email": "deepika@gmail.com",  "address": "Flat 412, Gachibowli, Hyderabad"},
        {"name": "Mohan Rao",       "phone": "919876543007", "email": "mohan@gmail.com",    "address": "Plot 33, Madhapur, Hyderabad"},
        {"name": "Kavitha Reddy",   "phone": "919876543008", "email": "kavitha@gmail.com",  "address": "House 7, Ameerpet, Hyderabad"},
        {"name": "Ravi Teja",       "phone": "919876543009", "email": "ravi.teja@gmail.com","address": "Flat 201, Dilsukhnagar, Hyderabad"},
        {"name": "Sridhar Babu",    "phone": "919876543010", "email": "sridhar@gmail.com",  "address": "House 44, LB Nagar, Hyderabad"},
    ]
    op1_sub_ids = []
    for sub in op1_subscribers_data:
        existing = await db.subscribers.find_one({
            "phone": sub["phone"], "operator_id": op1_id, "deleted_at": None
        })
        if existing:
            op1_sub_ids.append(existing["id"])
            continue
        sid = generate_id()
        plan_idx = len(op1_sub_ids) % len(plan_ids[op1_id])
        await db.subscribers.insert_one({
            "id": sid, "operator_id": op1_id,
            "name": sub["name"], "phone": sub["phone"],
            "email": sub.get("email"), "address": sub.get("address"),
            "plan_id": plan_ids[op1_id][plan_idx],
            "plan_name": plans_data[op1_id][plan_idx]["name"],
            "billing_date": 15,
            "status": "active",
            "created_at": (now - timedelta(days=30)).isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None,
        })
        op1_sub_ids.append(sid)
    print(f"✅ {len(op1_sub_ids)} subscribers created for Krishna Cable Network")

    # ---------- SUBSCRIBERS for operator 2 (Sagar Broadband) ----------
    op2_subscribers_data = [
        {"name": "Amit Patil",      "phone": "918765432001", "email": "amit@gmail.com",     "address": "Flat 201, Kothrud, Pune"},
        {"name": "Neha Joshi",      "phone": "918765432002", "email": "neha@gmail.com",     "address": "House 5, Deccan, Pune"},
        {"name": "Vikram Singh",    "phone": "918765432003", "email": "vikram@gmail.com",   "address": "Flat 102, Viman Nagar, Pune"},
        {"name": "Pooja Kulkarni",  "phone": "918765432004", "email": "pooja@gmail.com",    "address": "House 18, Aundh, Pune"},
        {"name": "Rajesh Deshmukh", "phone": "918765432005", "email": "rajesh.d@gmail.com", "address": "Plot 7, Hinjewadi, Pune"},
        {"name": "Sunita Bhosale",  "phone": "918765432006", "email": "sunita@gmail.com",   "address": "Flat 501, Baner, Pune"},
    ]
    op2_sub_ids = []
    for sub in op2_subscribers_data:
        existing = await db.subscribers.find_one({
            "phone": sub["phone"], "operator_id": op2_id, "deleted_at": None
        })
        if existing:
            op2_sub_ids.append(existing["id"])
            continue
        sid = generate_id()
        plan_idx = len(op2_sub_ids) % len(plan_ids[op2_id])
        await db.subscribers.insert_one({
            "id": sid, "operator_id": op2_id,
            "name": sub["name"], "phone": sub["phone"],
            "email": sub.get("email"), "address": sub.get("address"),
            "plan_id": plan_ids[op2_id][plan_idx],
            "plan_name": plans_data[op2_id][plan_idx]["name"],
            "billing_date": 1,
            "status": "active",
            "created_at": (now - timedelta(days=30)).isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None,
        })
        op2_sub_ids.append(sid)
    print(f"✅ {len(op2_sub_ids)} subscribers created for Sagar Broadband")

    # ---------- Create INVOICES for Operator 1 ----------
    # We'll create invoices across several dates, some paid and some pending
    # Settlement processing groups paid invoices by paid_at date

    invoice_counter = 1

    # -- Invoices paid 3 days ago (for settlement processing) --
    paid_date_3d = (now - timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)
    for i, sub_id in enumerate(op1_sub_ids[:6]):
        plan_idx = i % len(plan_ids[op1_id])
        plan = plans_data[op1_id][plan_idx]
        base = plan["price"]
        tax_amt = round(base * plan["tax_percentage"] / 100, 2) if plan["tax_type"] == "exclusive" else 0
        final_amt = round(base + tax_amt, 2)
        inv_id = generate_id()
        inv_number = f"KCN-{invoice_counter:04d}"
        invoice_counter += 1
        service_start = (paid_date_3d - timedelta(days=30)).isoformat()
        service_end = paid_date_3d.isoformat()
        due_date = (paid_date_3d + timedelta(days=15)).isoformat()

        await db.invoices.insert_one({
            "id": inv_id,
            "invoice_number": inv_number,
            "subscriber_id": sub_id,
            "subscriber_name": op1_subscribers_data[i]["name"],
            "plan_id": plan_ids[op1_id][plan_idx],
            "plan_name": plan["name"],
            "base_amount": base,
            "discount": 0,
            "tax_amount": tax_amt,
            "final_amount": final_amt,
            "service_start_date": service_start,
            "service_end_date": service_end,
            "due_date": due_date,
            "status": "paid",
            "paid_at": paid_date_3d.isoformat(),
            "payment_id": f"pay_{generate_id()[:12]}",
            "operator_id": op1_id,
            "settled": False,
            "created_at": (paid_date_3d - timedelta(days=5)).isoformat(),
            "updated_at": paid_date_3d.isoformat(),
            "deleted_at": None,
        })
    print(f"✅ 6 paid invoices created for OP1 (paid 3 days ago)")

    # -- Invoices paid 7 days ago --
    paid_date_7d = (now - timedelta(days=7)).replace(hour=14, minute=0, second=0, microsecond=0)
    for i, sub_id in enumerate(op1_sub_ids[4:8]):
        idx = i + 4
        plan_idx = idx % len(plan_ids[op1_id])
        plan = plans_data[op1_id][plan_idx]
        base = plan["price"]
        tax_amt = round(base * plan["tax_percentage"] / 100, 2) if plan["tax_type"] == "exclusive" else 0
        final_amt = round(base + tax_amt, 2)
        inv_id = generate_id()
        inv_number = f"KCN-{invoice_counter:04d}"
        invoice_counter += 1

        await db.invoices.insert_one({
            "id": inv_id,
            "invoice_number": inv_number,
            "subscriber_id": sub_id,
            "subscriber_name": op1_subscribers_data[idx]["name"],
            "plan_id": plan_ids[op1_id][plan_idx],
            "plan_name": plan["name"],
            "base_amount": base,
            "discount": 0,
            "tax_amount": tax_amt,
            "final_amount": final_amt,
            "service_start_date": (paid_date_7d - timedelta(days=30)).isoformat(),
            "service_end_date": paid_date_7d.isoformat(),
            "due_date": (paid_date_7d + timedelta(days=15)).isoformat(),
            "status": "paid",
            "paid_at": paid_date_7d.isoformat(),
            "payment_id": f"pay_{generate_id()[:12]}",
            "operator_id": op1_id,
            "settled": False,
            "created_at": (paid_date_7d - timedelta(days=5)).isoformat(),
            "updated_at": paid_date_7d.isoformat(),
            "deleted_at": None,
        })
    print(f"✅ 4 paid invoices created for OP1 (paid 7 days ago)")

    # -- Pending invoices (not paid yet) --
    for i, sub_id in enumerate(op1_sub_ids[8:]):
        idx = i + 8
        plan_idx = idx % len(plan_ids[op1_id])
        plan = plans_data[op1_id][plan_idx]
        base = plan["price"]
        tax_amt = round(base * plan["tax_percentage"] / 100, 2) if plan["tax_type"] == "exclusive" else 0
        final_amt = round(base + tax_amt, 2)
        inv_id = generate_id()
        inv_number = f"KCN-{invoice_counter:04d}"
        invoice_counter += 1

        await db.invoices.insert_one({
            "id": inv_id,
            "invoice_number": inv_number,
            "subscriber_id": sub_id,
            "subscriber_name": op1_subscribers_data[idx]["name"],
            "plan_id": plan_ids[op1_id][plan_idx],
            "plan_name": plan["name"],
            "base_amount": base,
            "discount": 0,
            "tax_amount": tax_amt,
            "final_amount": final_amt,
            "service_start_date": now.isoformat(),
            "service_end_date": (now + timedelta(days=30)).isoformat(),
            "due_date": (now + timedelta(days=15)).isoformat(),
            "status": "pending",
            "paid_at": None,
            "payment_id": None,
            "operator_id": op1_id,
            "settled": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None,
        })
    print(f"✅ 2 pending invoices created for OP1")

    # ---------- Create INVOICES for Operator 2 ----------
    invoice_counter_op2 = 1

    # -- Invoices paid 3 days ago --
    for i, sub_id in enumerate(op2_sub_ids[:4]):
        plan_idx = i % len(plan_ids[op2_id])
        plan = plans_data[op2_id][plan_idx]
        base = plan["price"]
        # Inclusive tax - tax is included in price
        if plan["tax_type"] == "inclusive":
            tax_amt = round(base - (base / (1 + plan["tax_percentage"] / 100)), 2)
            final_amt = base  # tax is included
        else:
            tax_amt = round(base * plan["tax_percentage"] / 100, 2)
            final_amt = round(base + tax_amt, 2)
        inv_id = generate_id()
        inv_number = f"SB-{invoice_counter_op2:04d}"
        invoice_counter_op2 += 1

        await db.invoices.insert_one({
            "id": inv_id,
            "invoice_number": inv_number,
            "subscriber_id": sub_id,
            "subscriber_name": op2_subscribers_data[i]["name"],
            "plan_id": plan_ids[op2_id][plan_idx],
            "plan_name": plan["name"],
            "base_amount": base,
            "discount": 0,
            "tax_amount": tax_amt,
            "final_amount": final_amt,
            "service_start_date": (paid_date_3d - timedelta(days=30)).isoformat(),
            "service_end_date": paid_date_3d.isoformat(),
            "due_date": (paid_date_3d + timedelta(days=15)).isoformat(),
            "status": "paid",
            "paid_at": paid_date_3d.isoformat(),
            "payment_id": f"pay_{generate_id()[:12]}",
            "operator_id": op2_id,
            "settled": False,
            "created_at": (paid_date_3d - timedelta(days=5)).isoformat(),
            "updated_at": paid_date_3d.isoformat(),
            "deleted_at": None,
        })
    print(f"✅ 4 paid invoices created for OP2 (paid 3 days ago)")

    # -- Invoices paid today (for testing "process today" flow) --
    for i, sub_id in enumerate(op2_sub_ids[4:]):
        idx = i + 4
        plan_idx = idx % len(plan_ids[op2_id])
        plan = plans_data[op2_id][plan_idx]
        base = plan["price"]
        if plan["tax_type"] == "inclusive":
            tax_amt = round(base - (base / (1 + plan["tax_percentage"] / 100)), 2)
            final_amt = base
        else:
            tax_amt = round(base * plan["tax_percentage"] / 100, 2)
            final_amt = round(base + tax_amt, 2)
        inv_id = generate_id()
        inv_number = f"SB-{invoice_counter_op2:04d}"
        invoice_counter_op2 += 1

        await db.invoices.insert_one({
            "id": inv_id,
            "invoice_number": inv_number,
            "subscriber_id": sub_id,
            "subscriber_name": op2_subscribers_data[idx]["name"],
            "plan_id": plan_ids[op2_id][plan_idx],
            "plan_name": plan["name"],
            "base_amount": base,
            "discount": 0,
            "tax_amount": tax_amt,
            "final_amount": final_amt,
            "service_start_date": now.isoformat(),
            "service_end_date": (now + timedelta(days=30)).isoformat(),
            "due_date": (now + timedelta(days=15)).isoformat(),
            "status": "paid",
            "paid_at": now.isoformat(),
            "payment_id": f"pay_{generate_id()[:12]}",
            "operator_id": op2_id,
            "settled": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None,
        })
    print(f"✅ 2 paid invoices created for OP2 (paid today)")

    # ---------- SETTLEMENT PROCESSING ----------
    print("\n=== Processing Settlements ===\n")

    global_settings = await db.global_settings.find_one({"type": "platform_settings"}, {"_id": 0})
    global_fee_pct = float((global_settings or {}).get("platform_fee_percentage", 2))

    # Process settlements for 3 days ago
    settlement_date_3d = paid_date_3d.strftime("%Y-%m-%d")
    start_3d = paid_date_3d.replace(hour=0, minute=0, second=0, microsecond=0)
    end_3d = paid_date_3d.replace(hour=23, minute=59, second=59, microsecond=999999)

    paid_invoices_3d = await db.invoices.find({
        "status": "paid", "deleted_at": None, "settled": {"$ne": True},
        "paid_at": {"$gte": start_3d.isoformat(), "$lte": end_3d.isoformat()},
    }, {"_id": 0}).to_list(10000)

    # Group by operator
    op_groups = {}
    for inv in paid_invoices_3d:
        op = inv["operator_id"]
        if op not in op_groups:
            op_groups[op] = []
        op_groups[op].append(inv)

    for operator_id, invoices in op_groups.items():
        operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
        if not operator:
            continue

        # Get plan-specific fee
        plan_fee_pct = global_fee_pct
        if operator.get("saas_plan_id"):
            plan = await db.saas_plans.find_one(
                {"id": operator["saas_plan_id"], "deleted_at": None},
                {"_id": 0, "platform_fee_percentage": 1, "name": 1}
            )
            if plan and plan.get("platform_fee_percentage") is not None:
                plan_fee_pct = float(plan["platform_fee_percentage"])

        total_collected = sum(inv["final_amount"] for inv in invoices)
        platform_fee = round(total_collected * plan_fee_pct / 100, 2)
        tax_on_fee = round(platform_fee * 18 / 100, 2)
        net_settlement = round(total_collected - platform_fee - tax_on_fee, 2)
        invoice_ids = [inv["id"] for inv in invoices]

        settlement = {
            "id": str(uuid.uuid4()),
            "operator_id": operator_id,
            "operator_name": operator.get("company_name", "Unknown"),
            "plan_name": operator.get("saas_plan_name", "N/A"),
            "settlement_date": settlement_date_3d,
            "total_collections": total_collected,
            "platform_fee_percentage": plan_fee_pct,
            "platform_fee": platform_fee,
            "tax_on_platform_fee": tax_on_fee,
            "net_settlement": net_settlement,
            "payment_count": len(invoices),
            "invoice_ids": invoice_ids,
            "status": "pending",
            "utr_number": None,
            "paid_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        await db.settlements.insert_one(settlement)
        await db.invoices.update_many(
            {"id": {"$in": invoice_ids}},
            {"$set": {"settled": True, "settlement_id": settlement["id"]}}
        )
        print(f"✅ Settlement created for {operator['company_name']} ({settlement_date_3d}): "
              f"₹{total_collected} collected, ₹{platform_fee} platform fee, ₹{net_settlement} net | "
              f"{len(invoices)} invoices | Status: pending")

    # Process settlements for 7 days ago (OP1 only)
    settlement_date_7d = paid_date_7d.strftime("%Y-%m-%d")
    start_7d = paid_date_7d.replace(hour=0, minute=0, second=0, microsecond=0)
    end_7d = paid_date_7d.replace(hour=23, minute=59, second=59, microsecond=999999)

    paid_invoices_7d = await db.invoices.find({
        "status": "paid", "deleted_at": None, "settled": {"$ne": True},
        "paid_at": {"$gte": start_7d.isoformat(), "$lte": end_7d.isoformat()},
    }, {"_id": 0}).to_list(10000)

    for inv in paid_invoices_7d:
        op_id = inv["operator_id"]
        if op_id not in op_groups:
            op_groups[op_id] = []

    # Group again for 7-day invoices
    op_groups_7d = {}
    for inv in paid_invoices_7d:
        op = inv["operator_id"]
        if op not in op_groups_7d:
            op_groups_7d[op] = []
        op_groups_7d[op].append(inv)

    for operator_id, invoices in op_groups_7d.items():
        operator = await db.operators.find_one({"id": operator_id, "deleted_at": None}, {"_id": 0})
        if not operator:
            continue

        plan_fee_pct = global_fee_pct
        if operator.get("saas_plan_id"):
            plan = await db.saas_plans.find_one(
                {"id": operator["saas_plan_id"], "deleted_at": None},
                {"_id": 0, "platform_fee_percentage": 1, "name": 1}
            )
            if plan and plan.get("platform_fee_percentage") is not None:
                plan_fee_pct = float(plan["platform_fee_percentage"])

        total_collected = sum(inv["final_amount"] for inv in invoices)
        platform_fee = round(total_collected * plan_fee_pct / 100, 2)
        tax_on_fee = round(platform_fee * 18 / 100, 2)
        net_settlement = round(total_collected - platform_fee - tax_on_fee, 2)
        invoice_ids = [inv["id"] for inv in invoices]

        # This one is marked as "completed" with UTR to show variety
        settlement = {
            "id": str(uuid.uuid4()),
            "operator_id": operator_id,
            "operator_name": operator.get("company_name", "Unknown"),
            "plan_name": operator.get("saas_plan_name", "N/A"),
            "settlement_date": settlement_date_7d,
            "total_collections": total_collected,
            "platform_fee_percentage": plan_fee_pct,
            "platform_fee": platform_fee,
            "tax_on_platform_fee": tax_on_fee,
            "net_settlement": net_settlement,
            "payment_count": len(invoices),
            "invoice_ids": invoice_ids,
            "status": "completed",
            "utr_number": f"NEFT{settlement_date_7d.replace('-', '')}001",
            "paid_at": (paid_date_7d + timedelta(days=2)).isoformat(),
            "created_at": (paid_date_7d + timedelta(days=1)).isoformat(),
            "updated_at": (paid_date_7d + timedelta(days=2)).isoformat(),
        }
        await db.settlements.insert_one(settlement)
        await db.invoices.update_many(
            {"id": {"$in": invoice_ids}},
            {"$set": {"settled": True, "settlement_id": settlement["id"]}}
        )
        print(f"✅ Settlement created for {operator['company_name']} ({settlement_date_7d}): "
              f"₹{total_collected} collected, ₹{platform_fee} platform fee, ₹{net_settlement} net | "
              f"{len(invoices)} invoices | Status: completed | UTR: {settlement['utr_number']}")

    # ---------- Summary ----------
    total_settlements = await db.settlements.count_documents({})
    total_invoices = await db.invoices.count_documents({})
    paid_invoices = await db.invoices.count_documents({"status": "paid"})
    pending_invoices = await db.invoices.count_documents({"status": "pending"})
    unsettled_paid = await db.invoices.count_documents({"status": "paid", "settled": {"$ne": True}})
    total_operators = await db.operators.count_documents({"deleted_at": None})
    total_subscribers = await db.subscribers.count_documents({"deleted_at": None})

    print(f"\n{'='*60}")
    print(f"✅ SETTLEMENT SAMPLE DATA SEEDING COMPLETE")
    print(f"{'='*60}")
    print(f"  Operators:           {total_operators}")
    print(f"  Subscribers:         {total_subscribers}")
    print(f"  Total Invoices:      {total_invoices}")
    print(f"  - Paid:              {paid_invoices}")
    print(f"  - Pending:           {pending_invoices}")
    print(f"  - Paid & Unsettled:  {unsettled_paid} (available for today's processing)")
    print(f"  Settlements:         {total_settlements}")
    print(f"{'='*60}")
    print(f"\n📋 Login Credentials:")
    print(f"  Admin:     admin@saas.com / admin123")
    print(f"  Operator1: venkat@krishnacable.in / operator123  (Pro Plan)")
    print(f"  Operator2: sagar@sagarbroadband.com / operator123  (Basic Plan)")
    print(f"\n💡 To process today's settlements, go to Admin > Settlements > 'Process Settlements'")
    print(f"   Or use: POST /api/admin/settlements/process?settlement_date={now.strftime('%Y-%m-%d')}")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed_settlement_data())
