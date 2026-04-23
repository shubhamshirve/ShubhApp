"""Seed script to create test operator and subscribers for testing searchable dropdown."""
import asyncio
import os
import sys
sys.path.insert(0, '/app/backend')
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from uuid import uuid4
from utils import hash_password

async def seed_data():
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db_name = os.getenv('DB_NAME', 'saas_db')
    db = client[db_name]
    
    print(f"Using database: {db_name}")
    
    # Check if operator already exists
    existing = await db.operators.find_one({"email": "operator@test.com"})
    if existing:
        print("✓ Operator already exists")
        operator_id = existing["id"]
    else:
        # Create test operator
        operator_id = str(uuid4())
        password_hash = hash_password("test123")
        operator = {
            "id": operator_id,
            "email": "operator@test.com",
            "password": password_hash,
            "company_name": "Test Company",
            "phone": "9999999999",
            "address": "Test Address",
            "wallet_balance": 1000.0,
            "saas_plan_id": None,
            "status": "active",
            "active_addons": [],
            "features": {
                "payment_gateway": False,
                "whatsapp_notifications": True,
                "email_notifications": True,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "deleted_at": None,
        }
        await db.operators.insert_one(operator)
        print(f"✓ Created operator: operator@test.com (ID: {operator_id})")
    
    # Create user account for operator (for login)
    existing_user = await db.users.find_one({"email": "operator@test.com"})
    if not existing_user:
        user_id = str(uuid4())
        password_hash = hash_password("test123")
        user = {
            "id": user_id,
            "operator_id": operator_id,
            "email": "operator@test.com",
            "password": password_hash,
            "name": "Test Operator",
            "role": "operator",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "deleted_at": None,
        }
        await db.users.insert_one(user)
        print(f"✓ Created user account: operator@test.com (User ID: {user_id})")
    
    # Check existing subscriber count
    existing_count = await db.subscribers.count_documents({"operator_id": operator_id, "deleted_at": None})
    print(f"✓ Existing subscribers: {existing_count}")
    
    # Create sample subscribers if less than 10
    if existing_count < 10:
        subscribers_to_create = [
            {"name": "Rajesh Kumar", "whatsapp_number": "9876543210", "email": "rajesh@example.com"},
            {"name": "Priya Sharma", "whatsapp_number": "9123456789", "email": "priya@example.com"},
            {"name": "Amit Patel", "whatsapp_number": "9988776655", "email": "amit@example.com"},
            {"name": "Sunita Verma", "whatsapp_number": "9871234567", "email": "sunita@example.com"},
            {"name": "Vikram Singh", "whatsapp_number": "9765432109", "email": "vikram@example.com"},
            {"name": "Ananya Das", "whatsapp_number": "9654321098", "email": "ananya@example.com"},
            {"name": "Rohan Gupta", "whatsapp_number": "9543210987", "email": "rohan@example.com"},
            {"name": "Meera Reddy", "whatsapp_number": "9432109876", "email": "meera@example.com"},
            {"name": "Karthik Iyer", "whatsapp_number": "9321098765", "email": "karthik@example.com"},
            {"name": "Lakshmi Naidu", "whatsapp_number": "9210987654", "email": "lakshmi@example.com"},
        ]
        
        for sub_data in subscribers_to_create:
            # Check if already exists
            exists = await db.subscribers.find_one({
                "operator_id": operator_id,
                "whatsapp_number": sub_data["whatsapp_number"],
                "deleted_at": None
            })
            if not exists:
                subscriber = {
                    "id": str(uuid4()),
                    "operator_id": operator_id,
                    "name": sub_data["name"],
                    "whatsapp_number": sub_data["whatsapp_number"],
                    "email": sub_data["email"],
                    "address": "Test Address",
                    "plans": [],
                    "status": "active",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "deleted_at": None,
                }
                await db.subscribers.insert_one(subscriber)
                print(f"  + Created subscriber: {sub_data['name']}")
    
    # Final count
    final_count = await db.subscribers.count_documents({"operator_id": operator_id, "deleted_at": None})
    print(f"\n✓ Total subscribers for operator: {final_count}")
    print("\n=== Test Credentials ===")
    print("Email: operator@test.com")
    print("Password: test123")

if __name__ == "__main__":
    asyncio.run(seed_data())
