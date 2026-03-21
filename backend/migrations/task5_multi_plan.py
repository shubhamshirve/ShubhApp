"""
Migration script for Task 5: Multi-Plan Subscribers and Multi-Line Invoices.
Converts single-plan subscribers and invoices to the multi-plan/multi-line format.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

# Add parent directory to sys.path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db, client

async def migrate_subscribers():
    print("Migrating subscribers...")
    # Find subscribers that still have the old plan_id field
    subscribers = await db.subscribers.find({"plan_id": {"$exists": True}}).to_list(None)
    print(f"Found {len(subscribers)} subscribers to migrate.")
    
    for sub in subscribers:
        plan_id = sub.get("plan_id")
        plan_name = sub.get("plan_name")
        billing_date = sub.get("billing_date", 1)
        discount = sub.get("discount", 0)
        
        if plan_id:
            new_plans = [{
                "plan_id": plan_id,
                "plan_name": plan_name,
                "billing_date": billing_date,
                "discount": discount,
                "status": "active"
            }]
            await db.subscribers.update_one(
                {"_id": sub["_id"]},
                {
                    "$set": {"plans": new_plans}, 
                    "$unset": {"plan_id": "", "plan_name": "", "billing_date": "", "discount": ""}
                }
            )
    print("Subscribers migration completed.")

async def migrate_invoices():
    print("Migrating invoices...")
    # Find invoices that still have the old plan_id field
    invoices = await db.invoices.find({"plan_id": {"$exists": True}}).to_list(None)
    print(f"Found {len(invoices)} invoices to migrate.")
    
    for inv in invoices:
        plan_id = inv.get("plan_id")
        plan_name = inv.get("plan_name")
        base_amount = inv.get("base_amount", 0)
        discount = inv.get("discount", 0)
        tax_amount = inv.get("tax_amount", 0)
        final_amount = inv.get("final_amount", 0)
        service_start_date = inv.get("service_start_date")
        service_end_date = inv.get("service_end_date")
        
        if plan_id:
            line_items = [{
                "plan_id": plan_id,
                "plan_name": plan_name,
                "base_amount": base_amount,
                "discount": discount,
                "tax_amount": tax_amount,
                "final_amount": final_amount,
                "service_start_date": service_start_date,
                "service_end_date": service_end_date
            }]
            await db.invoices.update_one(
                {"_id": inv["_id"]},
                {
                    "$set": {"line_items": line_items}, 
                    "$unset": {
                        "plan_id": "", "plan_name": "", "base_amount": "", 
                        "discount": "", "tax_amount": "", "service_start_date": "", 
                        "service_end_date": ""
                    }
                }
            )
    print("Invoices migration completed.")

async def main():
    try:
        await migrate_subscribers()
        await migrate_invoices()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())
