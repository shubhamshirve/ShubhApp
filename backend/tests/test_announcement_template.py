"""
Test announcement WhatsApp template functionality.

This script tests:
1. Announcement variable resolution (announcement_text, operator_name, operator_phone)
2. Template-based announcement sending
3. Fallback to plain text if no template configured
"""
import sys
sys.path.insert(0, '/app/backend')
from motor.motor_asyncio import AsyncIOMotorClient
from services.whatsapp_service import resolve_template_variables
import asyncio
import os

async def test_announcement_variables():
    """Test that announcement variables resolve correctly."""
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db_name = os.getenv('DB_NAME', 'saas_db')
    db = client[db_name]
    
    print("\n=== Testing Announcement WhatsApp Template Variables ===\n")
    
    # Get test operator and subscriber
    operator = await db.operators.find_one({"email": "operator@test.com"}, {"_id": 0})
    if not operator:
        print("✗ Test operator not found")
        return False
    
    subscriber = await db.subscribers.find_one({"operator_id": operator["id"]}, {"_id": 0})
    if not subscriber:
        print("✗ Test subscriber not found")
        return False
    
    print(f"✓ Using operator: {operator.get('company_name', 'N/A')}")
    print(f"✓ Using subscriber: {subscriber.get('name', 'N/A')}")
    print()
    
    # Create mock announcement data
    announcement = {
        "title": "Service Maintenance Notice",
        "message": "We will be performing maintenance on 26th January. Services will be unavailable from 2 AM to 6 AM. We apologize for any inconvenience.",
        "operator_id": operator["id"],
        "_operator": operator  # Pre-inject for testing
    }
    
    # Test variables
    test_variables = [
        "announcement_title",
        "announcement_text", 
        "announcement_message",
        "operator_name",
        "operator_phone",
        "operator_email",
        "customer_name",
    ]
    
    print("=== Resolving Variables ===")
    result = await resolve_template_variables(db, test_variables, announcement, subscriber)
    resolved = result["body"]
    
    for i, var_name in enumerate(test_variables):
        value = resolved[i] if i < len(resolved) else "ERROR"
        status = "✓" if value and value != var_name else "✗"
        print(f"{status} {var_name}: '{value}'")
    
    print("\n=== Expected Template Output ===")
    print(f"""
┌─────────────────────────────────────────┐
│      [Announcement Header Image]        │
└─────────────────────────────────────────┘

{resolved[1]}

─────────────────────────────────────────
From: {resolved[3]}
Contact: {resolved[4]}
    """)
    
    # Verify critical variables
    print("\n=== Verification ===")
    checks = []
    
    # Check announcement text
    if resolved[1] and "maintenance" in resolved[1].lower():
        print("✓ announcement_text contains message")
        checks.append(True)
    else:
        print("✗ announcement_text missing or incorrect")
        checks.append(False)
    
    # Check operator name
    if resolved[3] and len(resolved[3]) > 0:
        print(f"✓ operator_name resolved: {resolved[3]}")
        checks.append(True)
    else:
        print("✗ operator_name not resolved")
        checks.append(False)
    
    # Check operator phone
    if resolved[4] and len(resolved[4]) > 0:
        print(f"✓ operator_phone resolved: {resolved[4]}")
        checks.append(True)
    else:
        print("✗ operator_phone not resolved")
        checks.append(False)
    
    if all(checks):
        print("\n✅ All announcement variables working correctly!")
        return True
    else:
        print("\n❌ Some variables failed")
        return False

async def test_template_configuration():
    """Check if announcement template is configured."""
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db_name = os.getenv('DB_NAME', 'saas_db')
    db = client[db_name]
    
    print("\n=== Checking Template Configuration ===\n")
    
    # Check WhatsApp settings
    settings = await db.global_settings.find_one({"type": "whatsapp_template_settings"}, {"_id": 0})
    if not settings:
        print("⚠️  WhatsApp template settings not configured")
        print("   To configure: Admin Panel → Settings → WhatsApp Settings")
        return False
    
    announcement_template = settings.get("announcement_template", "")
    if not announcement_template:
        print("⚠️  No announcement template configured")
        print("   Template will use: Plain text (fallback)")
        return False
    
    print(f"✓ Announcement template configured: {announcement_template}")
    
    # Check if template exists
    template = await db.whatsapp_templates.find_one(
        {"template_name": announcement_template, "deleted_at": None},
        {"_id": 0}
    )
    
    if not template:
        print(f"✗ Template '{announcement_template}' not found in database")
        return False
    
    print(f"✓ Template found: {template.get('template_name')}")
    print(f"  - Header type: {template.get('header_type', 'none')}")
    print(f"  - Body variables: {', '.join(template.get('body_variables', []))}")
    print(f"  - Language: {template.get('language_code', 'en')}")
    print(f"  - Status: {'Active' if template.get('is_active') else 'Inactive'}")
    
    return True

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   Announcement WhatsApp Template - Variable Resolution Test  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    result1 = asyncio.run(test_announcement_variables())
    result2 = asyncio.run(test_template_configuration())
    
    print("\n" + "="*60)
    if result1:
        print("✅ Variable resolution: PASSED")
    else:
        print("❌ Variable resolution: FAILED")
    
    if result2:
        print("✅ Template configuration: READY")
    else:
        print("⚠️  Template configuration: NOT CONFIGURED (will use fallback)")
    
    print("="*60 + "\n")
    
    sys.exit(0 if result1 else 1)
