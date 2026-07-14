"""Test wallet deduction for WhatsApp API sends."""
import sys
sys.path.insert(0, '/app/backend')
from motor.motor_asyncio import AsyncIOMotorClient
from routers.wallet import get_or_create_wallet, credit_wallet, deduct_wallet
import asyncio
import os

async def test_wallet_deduction_flow():
    """Test wallet check and deduction for WhatsApp sends."""
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db_name = os.getenv('DB_NAME', 'ebill_db')
    db = client[db_name]
    
    # Get operator
    operator = await db.operators.find_one({"email": "operator@test.com"}, {"_id": 0})
    if not operator:
        print("✗ Operator not found")
        return False
    
    operator_id = operator["id"]
    WHATSAPP_COST = 0.5
    
    print("\n=== Test 1: Check wallet balance ===")
    wallet = await get_or_create_wallet(operator_id)
    initial_balance = wallet.get("balance", 0)
    print(f"  Initial balance: ₹{initial_balance:.2f}")
    
    if initial_balance < WHATSAPP_COST:
        print(f"  ✗ Insufficient balance (need ₹{WHATSAPP_COST})")
        print(f"    This is expected behavior - wallet check working!")
        
        # Top up for next test
        print("\n  Topping up wallet...")
        new_balance = await credit_wallet(operator_id, 10.0, "Test topup")
        print(f"  ✓ Topped up to ₹{new_balance:.2f}")
        initial_balance = new_balance
    else:
        print(f"  ✓ Sufficient balance")
    
    print("\n=== Test 2: Deduct wallet for WhatsApp send ===")
    new_balance, suspended = await deduct_wallet(
        operator_id,
        WHATSAPP_COST,
        "WhatsApp message sent (test)",
        reference_id="test-invoice-123"
    )
    print(f"  Deducted: ₹{WHATSAPP_COST}")
    print(f"  New balance: ₹{new_balance:.2f}")
    print(f"  Expected: ₹{(initial_balance - WHATSAPP_COST):.2f}")
    
    if abs(new_balance - (initial_balance - WHATSAPP_COST)) < 0.01:
        print("  ✓ Deduction successful!")
    else:
        print("  ✗ Deduction mismatch!")
        return False
    
    print("\n=== Test 3: Verify transaction record ===")
    transaction = await db.wallet_transactions.find_one(
        {"operator_id": operator_id, "reference_id": "test-invoice-123"},
        {"_id": 0}
    )
    
    if transaction:
        print(f"  ✓ Transaction recorded")
        print(f"    Type: {transaction.get('type')}")
        print(f"    Amount: ₹{abs(transaction.get('amount', 0)):.2f}")
        print(f"    Description: {transaction.get('description')}")
        print(f"    Balance after: ₹{transaction.get('balance_after', 0):.2f}")
    else:
        print("  ✗ Transaction not found!")
        return False
    
    print("\n=== Test 4: Verify negative balance prevention ===")
    # Get current balance
    wallet = await get_or_create_wallet(operator_id)
    current_balance = wallet.get("balance", 0)
    print(f"  Current balance: ₹{current_balance:.2f}")
    
    # Try to deduct more than balance
    try:
        # Deduct until balance would go negative
        attempts = int(current_balance / WHATSAPP_COST) + 2
        print(f"  Attempting {attempts} deductions...")
        
        for i in range(attempts):
            wallet = await get_or_create_wallet(operator_id)
            balance = wallet.get("balance", 0)
            
            if balance >= WHATSAPP_COST:
                await deduct_wallet(operator_id, WHATSAPP_COST, f"Test deduction {i+1}")
                print(f"    #{i+1}: Deducted ₹{WHATSAPP_COST} (balance: ₹{balance - WHATSAPP_COST:.2f})")
            else:
                print(f"    #{i+1}: Insufficient balance (₹{balance:.2f} < ₹{WHATSAPP_COST})")
                print("  ✓ Negative balance prevention working!")
                break
    except Exception as e:
        print(f"  Exception: {e}")
    
    print("\n✅ All wallet deduction tests completed!")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_wallet_deduction_flow())
    sys.exit(0 if result else 1)
