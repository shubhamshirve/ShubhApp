#!/usr/bin/env python3
"""
Seed test users for testing operator endpoints.
Creates:
1. Admin user: admin@saas.com / admin123
2. Operator user: operator@test.com / test123
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add backend to path
sys.path.insert(0, '/app/backend')

from database import db
from utils import generate_id, hash_password


async def seed_test_users():
    """Seed test users into the database."""
    print("Starting test user seeding...")
    
    # Check if admin already exists
    existing_admin = await db.users.find_one({"email": "admin@saas.com"})
    if existing_admin:
        print("✓ Admin user already exists")
    else:
        # Create admin user
        admin_id = generate_id()
        admin_user = {
            "id": admin_id,
            "email": "admin@saas.com",
            "password": hash_password("admin123"),
            "name": "Admin User",
            "role": "admin",
            "operator_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "deleted_at": None,
            "active_session_id": None,
            "last_login_at": None,
        }
        await db.users.insert_one(admin_user)
        print(f"✓ Created admin user: admin@saas.com / admin123 (ID: {admin_id})")
    
    # Check if operator already exists
    existing_operator_user = await db.users.find_one({"email": "operator@test.com"})
    if existing_operator_user:
        print("✓ Operator user already exists")
        operator_id = existing_operator_user.get("operator_id")
    else:
        # Create operator record first
        operator_id = generate_id()
        now = datetime.now(timezone.utc)
        trial_ends = now + timedelta(days=30)
        
        operator = {
            "id": operator_id,
            "email": "operator@test.com",
            "company_name": "Test Operator Company",
            "owner_name": "Test Operator",
            "phone": "9876543210",
            "address": "Test Address",
            "status": "active",
            "saas_plan_id": None,
            "saas_plan_name": None,
            "trial_ends_at": trial_ends.isoformat(),
            "subscription_ends_at": trial_ends.isoformat(),
            "is_read_only": False,
            "active_addons": ["audit_log"],  # Enable audit log addon for testing
            "addon_expiry": {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None,
        }
        await db.operators.insert_one(operator)
        print(f"✓ Created operator record (ID: {operator_id})")
        
        # Create operator user
        operator_user_id = generate_id()
        operator_user = {
            "id": operator_user_id,
            "email": "operator@test.com",
            "password": hash_password("test123"),
            "name": "Test Operator",
            "role": "operator",
            "operator_id": operator_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "deleted_at": None,
            "active_session_id": None,
            "last_login_at": None,
        }
        await db.users.insert_one(operator_user)
        print(f"✓ Created operator user: operator@test.com / test123 (ID: {operator_user_id})")
    
    # Create some test data for the operator (invoices, subscribers)
    print("\nCreating test data...")
    
    # Check if test subscriber exists
    existing_subscriber = await db.subscribers.find_one({"operator_id": operator_id, "email": "subscriber1@test.com"})
    if not existing_subscriber:
        subscriber_id = generate_id()
        subscriber = {
            "id": subscriber_id,
            "operator_id": operator_id,
            "name": "Test Subscriber 1",
            "email": "subscriber1@test.com",
            "phone": "9876543211",
            "whatsapp_number": "9876543211",
            "address": "Test Subscriber Address",
            "status": "active",
            "plans": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "deleted_at": None,
        }
        await db.subscribers.insert_one(subscriber)
        print(f"✓ Created test subscriber (ID: {subscriber_id})")
        
        # Create a paid invoice for testing payments endpoint
        invoice_id = generate_id()
        paid_at = datetime.now(timezone.utc).isoformat()
        invoice = {
            "id": invoice_id,
            "operator_id": operator_id,
            "subscriber_id": subscriber_id,
            "subscriber_name": "Test Subscriber 1",
            "invoice_number": "INV-001",
            "status": "paid",
            "final_amount": 1000.0,
            "amount_paid": 1000.0,
            "payment_mode": "cash",
            "payment_id": "TEST-PAY-001",
            "paid_at": paid_at,
            "line_items": [
                {
                    "description": "Test Service",
                    "amount": 1000.0,
                    "is_custom": True,
                }
            ],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "deleted_at": None,
        }
        await db.invoices.insert_one(invoice)
        print(f"✓ Created test paid invoice (ID: {invoice_id})")
        
        # Create a pending invoice for testing dashboard stats
        pending_invoice_id = generate_id()
        pending_invoice = {
            "id": pending_invoice_id,
            "operator_id": operator_id,
            "subscriber_id": subscriber_id,
            "subscriber_name": "Test Subscriber 1",
            "invoice_number": "INV-002",
            "status": "pending",
            "final_amount": 500.0,
            "amount_paid": 0.0,
            "line_items": [
                {
                    "description": "Test Service 2",
                    "amount": 500.0,
                    "is_custom": True,
                }
            ],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "deleted_at": None,
        }
        await db.invoices.insert_one(pending_invoice)
        print(f"✓ Created test pending invoice (ID: {pending_invoice_id})")
    else:
        print("✓ Test data already exists")
    
    print("\n✅ Test user seeding completed successfully!")
    print("\nTest credentials:")
    print("  Admin: admin@saas.com / admin123")
    print("  Operator: operator@test.com / test123")


if __name__ == "__main__":
    asyncio.run(seed_test_users())
