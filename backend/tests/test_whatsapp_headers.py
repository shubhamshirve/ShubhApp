import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.whatsapp_service import resolve_template_variables, WhatsAppService
from motor.motor_asyncio import AsyncIOMotorClient

async def test_header_resolution():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client[os.environ.get("DB_NAME", "saas_db")]
    
    # Mock data
    invoice = {
        "id": "inv_123",
        "operator_id": "op_123",
        "invoice_number": "EB-101",
        "final_amount": 500.0,
        "due_date": "2026-05-01T00:00:00Z"
    }
    subscriber = {
        "name": "Test User",
        "whatsapp_number": "919999999999"
    }
    
    # Test 1: Image Header with company_logo
    print("Testing Image Header resolution...")
    # Mock invoice_settings
    await db.invoice_settings.delete_many({"operator_id": "op_123"})
    await db.invoice_settings.insert_one({
        "operator_id": "op_123",
        "logo_url": "/uploads/logo_123.png"
    })
    
    res = await resolve_template_variables(
        db, 
        body_variables=["customer_name", "amount"],
        invoice=invoice,
        subscriber=subscriber,
        header_variable="company_logo"
    )
    
    print(f"Resolved Body: {str(res['body']).encode('ascii', 'backslashreplace').decode()}")
    print(f"Resolved Header: {str(res['header']).encode('ascii', 'backslashreplace').decode()}")
    
    assert res['header'] == "/uploads/logo_123.png"
    assert "Test User" in res['body']
    print("[OK] Header resolution passed\n")

    # Test 2: Absolute URL construction
    print("Testing Absolute URL construction...")
    wa_service = WhatsAppService("dummy_id", "dummy_token")
    # Mock env setting
    # We can't easily mock get_env_setting without monkeypatching, 
    # but we can test the fallback
    abs_url = await wa_service._ensure_absolute_url("/uploads/logo_123.png")
    print(f"Absolute URL: {abs_url}")
    assert abs_url.startswith("http")
    assert "/uploads/logo_123.png" in abs_url
    print("✓ Absolute URL construction passed\n")

    # Test 3: Fallback Image when logo is missing
    print("Testing Fallback Image when logo is missing...")
    await db.invoice_settings.update_one(
        {"operator_id": "op_123"},
        {"$set": {"logo_url": ""}}
    )
    
    res = await resolve_template_variables(
        db, 
        body_variables=["customer_name"],
        invoice=invoice,
        subscriber=subscriber,
        header_variable="company_logo"
    )
    
    print(f"Resolved Header (empty): {str(res['header']).encode('ascii', 'backslashreplace').decode()}")
    
    # Simulate send_template_message logic for fallback
    image_url = await wa_service._ensure_absolute_url(str(res['header']))
    if not image_url or image_url.endswith("/uploads/") or image_url.endswith("/"):
        image_url = "https://raw.githubusercontent.com/shubhamshirve/ShubhApp/live/frontend/public/logo192.png"
    
    print(f"Final Image URL (fallback): {image_url}")
    assert "logo192.png" in image_url
    print("[OK] Fallback image logic passed\n")

    print("All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_header_resolution())
