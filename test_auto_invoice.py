"""
Test script for auto-invoice bug fixes:
1. Auto-generated invoices include plan_description in line items
2. Auto-generated invoice due date = 1 day BEFORE service start date
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

# Add backend to path
sys.path.insert(0, '/app/backend')

async def test_auto_invoice_fixes():
    """Test both auto-invoice bug fixes"""
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL"))
    db = client["saas_db"]
    
    print("=" * 80)
    print("AUTO-INVOICE BUG FIX TESTING")
    print("=" * 80)
    
    # Get operator
    operator = await db.operators.find_one({"deleted_at": None}, {"_id": 0})
    if not operator:
        print("❌ No operator found in database")
        return
    
    print(f"\n✓ Operator: {operator.get('company_name', operator['id'])}")
    
    # Get a subscriber with plans
    subscriber = await db.subscribers.find_one({
        "operator_id": operator["id"],
        "deleted_at": None,
        "plans": {"$exists": True, "$ne": []}
    }, {"_id": 0})
    
    if not subscriber:
        print("❌ No subscriber with plans found")
        return
    
    print(f"✓ Subscriber: {subscriber['name']} (ID: {subscriber['id']})")
    
    # Get a plan with description
    plan = await db.operator_plans.find_one({
        "operator_id": operator["id"],
        "deleted_at": None
    }, {"_id": 0})
    
    if not plan:
        print("❌ No plan found")
        return
    
    print(f"✓ Plan: {plan['name']} (ID: {plan['id']})")
    print(f"  Current description: {plan.get('description', 'None')}")
    
    # Add description if missing
    if not plan.get("description"):
        test_description = "High-speed fiber broadband plan with unlimited data"
        await db.operator_plans.update_one(
            {"id": plan["id"]},
            {"$set": {"description": test_description}}
        )
        plan["description"] = test_description
        print(f"  ✓ Added test description: {test_description}")
    
    # Simulate plans_to_bill for auto-invoice generation
    # Use a future date for service start
    service_start_date = "2026-05-15"  # Future date
    plans_to_bill = [{
        "plan_id": plan["id"],
        "plan_expiry_date": service_start_date,  # This becomes service_start_date
        "selected_validity": plan.get("validity", "monthly"),
        "discount": 0,
        "billing_date": 15
    }]
    
    print(f"\n{'=' * 80}")
    print("TESTING AUTO-INVOICE GENERATION")
    print(f"{'=' * 80}")
    print(f"Service Start Date: {service_start_date}")
    
    # Import and call the cron service
    from services.cron_service import CronJobService
    
    svc = CronJobService(db)
    invoice = await svc._create_auto_invoice(operator, subscriber, plans_to_bill)
    
    if not invoice:
        print("\n❌ No invoice created")
        return
    
    print(f"\n✅ AUTO-INVOICE CREATED")
    print(f"{'=' * 80}")
    print(f"Invoice Number: {invoice.get('invoice_number')}")
    print(f"Subscriber: {invoice.get('subscriber_name')}")
    print(f"Due Date: {invoice.get('due_date')}")
    print(f"Final Amount: ₹{invoice.get('final_amount', 0):.2f}")
    print(f"Auto Generated: {invoice.get('auto_generated', False)}")
    
    print(f"\n{'=' * 80}")
    print("LINE ITEMS DETAILS")
    print(f"{'=' * 80}")
    
    for idx, item in enumerate(invoice.get("line_items", []), 1):
        print(f"\nLine Item #{idx}:")
        print(f"  Plan Name: {item.get('plan_name')}")
        print(f"  Plan Description: {item.get('plan_description')}")
        print(f"  Is Custom: {item.get('is_custom')}")
        print(f"  Selected Validity: {item.get('selected_validity')}")
        print(f"  Service Start Date: {item.get('service_start_date')}")
        print(f"  Service End Date: {item.get('service_end_date')}")
        print(f"  Base Amount: ₹{item.get('base_amount', 0):.2f}")
        print(f"  Discount: ₹{item.get('discount', 0):.2f}")
        print(f"  Tax Amount: ₹{item.get('tax_amount', 0):.2f}")
        print(f"  Final Amount: ₹{item.get('final_amount', 0):.2f}")
    
    # Validate Fix 1: plan_description present
    print(f"\n{'=' * 80}")
    print("VALIDATION RESULTS")
    print(f"{'=' * 80}")
    
    item = invoice["line_items"][0]
    
    # Fix 1: plan_description
    plan_desc = item.get('plan_description')
    fix1_pass = plan_desc is not None and plan_desc != ""
    print(f"\n✓ FIX 1: plan_description in line items")
    print(f"  Expected: Present (not None/empty)")
    print(f"  Actual: {repr(plan_desc)}")
    print(f"  Status: {'✅ PASS' if fix1_pass else '❌ FAIL'}")
    
    # Fix 2: due_date = service_start - 1 day
    service_start = datetime.fromisoformat(item["service_start_date"].replace('Z', '+00:00'))
    actual_due = datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00'))
    expected_due = service_start - timedelta(days=1)
    
    # Calculate difference in days (should be 0)
    date_diff = abs((actual_due.date() - expected_due.date()).days)
    fix2_pass = date_diff == 0
    
    print(f"\n✓ FIX 2: due_date = service_start - 1 day")
    print(f"  Service Start: {service_start.strftime('%Y-%m-%d')}")
    print(f"  Expected Due (start - 1): {expected_due.strftime('%Y-%m-%d')}")
    print(f"  Actual Due: {actual_due.strftime('%Y-%m-%d')}")
    print(f"  Date Difference: {date_diff} days")
    print(f"  Status: {'✅ PASS' if fix2_pass else '❌ FAIL'}")
    
    # Overall result
    print(f"\n{'=' * 80}")
    print("OVERALL TEST RESULT")
    print(f"{'=' * 80}")
    
    if fix1_pass and fix2_pass:
        print("✅ ALL TESTS PASSED - Both bug fixes verified successfully!")
    else:
        print("❌ SOME TESTS FAILED")
        if not fix1_pass:
            print("  - Fix 1 (plan_description) FAILED")
        if not fix2_pass:
            print("  - Fix 2 (due_date calculation) FAILED")
    
    print(f"\n{'=' * 80}")
    
    # Clean up - delete the test invoice
    await db.invoices.delete_one({"id": invoice["id"]})
    print(f"\n✓ Test invoice {invoice['invoice_number']} cleaned up")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(test_auto_invoice_fixes())
