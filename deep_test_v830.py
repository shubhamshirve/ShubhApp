#!/usr/bin/env python3
"""
V8.30 WhatsApp Logging Deep Test
Focused test to verify WhatsApp logging functionality and investigate issues.
"""

import asyncio
import httpx
import json
from datetime import datetime, timezone

BACKEND_URL = "https://changelog-review-13.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

async def make_request(method: str, endpoint: str, headers: dict = None, json_data: dict = None):
    """Make HTTP request with error handling"""
    url = f"{BACKEND_URL}{endpoint}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=json_data)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=json_data)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except Exception as e:
            print(f"Request failed: {method} {url} - {str(e)}")
            raise

async def authenticate(email: str, password: str) -> str:
    """Authenticate and return access token"""
    response = await make_request("POST", "/auth/login", json_data={
        "email": email,
        "password": password
    })
    
    if response.status_code != 200:
        raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
    
    data = response.json()
    return data["access_token"]

async def main():
    print("🔍 V8.30 WhatsApp Logging Deep Test")
    print("="*50)
    
    # Authenticate
    admin_token = await authenticate(ADMIN_EMAIL, ADMIN_PASSWORD)
    operator_token = await authenticate(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    operator_headers = {"Authorization": f"Bearer {operator_token}"}
    
    print("✅ Authentication successful")
    
    # Check WhatsApp message logs via admin endpoint
    print("\n📱 Checking WhatsApp Message Logs...")
    wa_logs_response = await make_request("GET", "/admin/whatsapp-message-logs", headers=admin_headers)
    
    if wa_logs_response.status_code == 200:
        logs_data = wa_logs_response.json()
        logs = logs_data.get("logs", [])
        total = logs_data.get("total", 0)
        
        print(f"✅ WhatsApp logs endpoint accessible")
        print(f"📊 Total logs: {total}")
        
        if logs:
            print(f"📝 Recent log entries:")
            for i, log in enumerate(logs[:3]):  # Show first 3 logs
                print(f"  {i+1}. Template: {log.get('template_name', 'N/A')}")
                print(f"     Trigger: {log.get('trigger', 'N/A')}")
                print(f"     Status: {log.get('status', 'N/A')}")
                print(f"     Phone: {log.get('recipient_phone', 'N/A')}")
                print(f"     Created: {log.get('created_at', 'N/A')}")
                print()
        else:
            print("📝 No WhatsApp logs found")
    else:
        print(f"❌ WhatsApp logs endpoint failed: {wa_logs_response.status_code}")
        print(f"Response: {wa_logs_response.text}")
    
    # Check WhatsApp stats
    print("\n📊 Checking WhatsApp Stats...")
    wa_stats_response = await make_request("GET", "/admin/whatsapp-stats", headers=admin_headers)
    
    if wa_stats_response.status_code == 200:
        stats = wa_stats_response.json()
        print(f"✅ WhatsApp stats endpoint accessible")
        print(f"📈 Stats: {json.dumps(stats, indent=2)}")
    else:
        print(f"❌ WhatsApp stats endpoint failed: {wa_stats_response.status_code}")
    
    # Get existing subscribers to test with
    print("\n👥 Getting existing subscribers...")
    subs_response = await make_request("GET", "/operator/subscribers", headers=operator_headers)
    
    if subs_response.status_code == 200:
        subscribers = subs_response.json()
        print(f"✅ Found {len(subscribers)} subscribers")
        
        if subscribers:
            # Test manual invoice creation with proper data
            subscriber = subscribers[0]
            subscriber_id = subscriber["id"]
            
            print(f"\n📄 Testing manual invoice creation for subscriber: {subscriber['name']}")
            
            # Get plans to use proper plan data
            plans_response = await make_request("GET", "/operator/plans", headers=operator_headers)
            if plans_response.status_code == 200:
                plans = plans_response.json()
                if plans:
                    plan = plans[0]
                    
                    # Create a proper invoice payload
                    invoice_data = {
                        "subscriber_id": subscriber_id,
                        "line_items": [{
                            "plan_id": plan["id"],
                            "plan_name": plan["name"],
                            "base_amount": float(plan["price"]),
                            "discount": 0.0,
                            "tax_amount": 0.0,
                            "final_amount": float(plan["price"]),
                            "service_start_date": "2026-04-24T00:00:00",
                            "service_end_date": "2026-05-23T00:00:00"
                        }],
                        "whatsapp_notifications": True
                    }
                    
                    print(f"📝 Invoice data: {json.dumps(invoice_data, indent=2)}")
                    
                    manual_invoice_response = await make_request("POST", "/operator/invoices", 
                                                               headers=operator_headers, json_data=invoice_data)
                    
                    if manual_invoice_response.status_code == 201:
                        invoice = manual_invoice_response.json()
                        print(f"✅ Manual invoice created: {invoice['invoice_number']}")
                        
                        # Check if WhatsApp logs increased
                        print("\n📱 Checking WhatsApp logs after manual invoice...")
                        wa_logs_after = await make_request("GET", "/admin/whatsapp-message-logs", headers=admin_headers)
                        
                        if wa_logs_after.status_code == 200:
                            logs_after_data = wa_logs_after.json()
                            total_after = logs_after_data.get("total", 0)
                            print(f"📊 Total logs after invoice: {total_after}")
                            
                            # Look for recent logs with auto_invoice_create trigger
                            recent_logs = logs_after_data.get("logs", [])[:5]
                            auto_invoice_logs = [log for log in recent_logs if log.get("trigger") == "auto_invoice_create"]
                            
                            if auto_invoice_logs:
                                print(f"✅ Found {len(auto_invoice_logs)} auto_invoice_create log(s)")
                                for log in auto_invoice_logs:
                                    print(f"  - Invoice: {log.get('invoice_number', 'N/A')}")
                                    print(f"  - Status: {log.get('status', 'N/A')}")
                                    print(f"  - Template: {log.get('template_name', 'N/A')}")
                            else:
                                print("⚠️  No auto_invoice_create logs found (WA may not be configured)")
                        
                    else:
                        print(f"❌ Manual invoice creation failed: {manual_invoice_response.status_code}")
                        print(f"Error: {manual_invoice_response.text}")
                else:
                    print("❌ No plans found")
            else:
                print(f"❌ Failed to get plans: {plans_response.status_code}")
        else:
            print("⚠️  No subscribers found")
    else:
        print(f"❌ Failed to get subscribers: {subs_response.status_code}")
    
    # Test subscriber creation with generate_first_invoice=true again to see logs
    print("\n🧪 Testing subscriber creation with first invoice...")
    
    plans_response = await make_request("GET", "/operator/plans", headers=operator_headers)
    if plans_response.status_code == 200:
        plans = plans_response.json()
        if plans:
            plan_id = plans[0]["id"]
            
            # Get current log count
            wa_logs_before = await make_request("GET", "/admin/whatsapp-message-logs", headers=admin_headers)
            logs_before_count = 0
            if wa_logs_before.status_code == 200:
                logs_before_count = wa_logs_before.json().get("total", 0)
            
            subscriber_data = {
                "name": "Deep Test Subscriber",
                "whatsapp_number": "9177777777",
                "email": "deeptest@test.com",
                "address": "Deep Test Address",
                "plans": [{
                    "plan_id": plan_id,
                    "plan_start_date": "2026-04-24",
                    "discount": 0
                }],
                "generate_first_invoice": True
            }
            
            create_response = await make_request("POST", "/operator/subscribers", 
                                               headers=operator_headers, json_data=subscriber_data)
            
            if create_response.status_code == 200:
                new_subscriber = create_response.json()
                print(f"✅ Created subscriber: {new_subscriber['name']}")
                
                # Check logs after creation
                wa_logs_after = await make_request("GET", "/admin/whatsapp-message-logs", headers=admin_headers)
                if wa_logs_after.status_code == 200:
                    logs_after_count = wa_logs_after.json().get("total", 0)
                    print(f"📊 Logs before: {logs_before_count}, after: {logs_after_count}")
                    
                    if logs_after_count > logs_before_count:
                        print("✅ WhatsApp log entry created for first invoice!")
                        
                        # Show the new log
                        recent_logs = wa_logs_after.json().get("logs", [])[:3]
                        first_invoice_logs = [log for log in recent_logs if log.get("trigger") == "first_invoice"]
                        
                        if first_invoice_logs:
                            print("📝 First invoice log details:")
                            log = first_invoice_logs[0]
                            print(f"  - Trigger: {log.get('trigger')}")
                            print(f"  - Template: {log.get('template_name')}")
                            print(f"  - Status: {log.get('status')}")
                            print(f"  - Phone: {log.get('recipient_phone')}")
                            print(f"  - Invoice: {log.get('invoice_number')}")
                    else:
                        print("⚠️  No new WhatsApp logs (WA may not be configured, but that's expected)")
            else:
                print(f"❌ Subscriber creation failed: {create_response.status_code}")
                print(f"Error: {create_response.text}")
    
    print("\n✅ Deep test completed!")

if __name__ == "__main__":
    asyncio.run(main())