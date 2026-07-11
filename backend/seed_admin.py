"""Quick script to seed admin user."""
import asyncio
import sys
sys.path.insert(0, '/app/backend')

async def main():
    from database import db
    from server import seed_data
    
    print("Seeding admin user and initial data...")
    result = await seed_data()
    print(result)
    
    # Verify admin user exists
    admin = await db.users.find_one({"email": "admin@saas.com"})
    if admin:
        print(f"\n✓ Admin user verified: {admin['email']} (role: {admin['role']})")
    else:
        print("\n✗ Admin user not found!")

if __name__ == "__main__":
    asyncio.run(main())
