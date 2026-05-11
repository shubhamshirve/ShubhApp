"""
Backend API Testing for E-Bill Platform
Tests the following new endpoints:
1. GET /api/operator/subscribers/{subscriber_id}/expiry-audit
2. GET /api/admin/backup/list (with pagination)
3. GET /api/operator/whatsapp-stats
4. GET /api/operator/whatsapp-message-logs
"""

import httpx
import asyncio
import os
from datetime import datetime

# Backend URL from environment
BACKEND_URL = os.getenv("REACT_APP_BACKEND_URL", "https://whatsapp-stats-view.preview.emergentagent.com")
BASE_URL = f"{BACKEND_URL}/api"

# Test credentials
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"


class TestResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test_name: str, details: str = ""):
        self.passed.append(f"✅ {test_name}: {details}")
    
    def add_fail(self, test_name: str, error: str):
        self.failed.append(f"❌ {test_name}: {error}")
    
    def add_warning(self, test_name: str, warning: str):
        self.warnings.append(f"⚠️  {test_name}: {warning}")
    
    def print_summary(self):
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        if self.passed:
            print("\n✅ PASSED TESTS:")
            for p in self.passed:
                print(f"  {p}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for w in self.warnings:
                print(f"  {w}")
        
        if self.failed:
            print("\n❌ FAILED TESTS:")
            for f in self.failed:
                print(f"  {f}")
        
        print("\n" + "="*80)
        print(f"Total: {len(self.passed)} passed, {len(self.failed)} failed, {len(self.warnings)} warnings")
        print("="*80 + "\n")


async def login(email: str, password: str) -> dict:
    """Login and return cookies for authentication"""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code != 200:
            raise Exception(f"Login failed: {response.status_code} - {response.text}")
        
        # Return cookies for subsequent requests
        return dict(response.cookies)


async def test_expiry_audit(result: TestResult):
    """Test GET /api/operator/subscribers/{subscriber_id}/expiry-audit"""
    print("\n" + "="*80)
    print("TEST 1: Subscriber Expiry Audit Endpoint")
    print("="*80)
    
    try:
        # Login as operator
        cookies = await login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
        print(f"✓ Logged in as operator: {OPERATOR_EMAIL}")
        
        async with httpx.AsyncClient(follow_redirects=True, cookies=cookies) as client:
            # Get list of subscribers first
            print("\n→ Fetching subscribers list...")
            subs_response = await client.get(f"{BASE_URL}/operator/subscribers")
            
            if subs_response.status_code != 200:
                result.add_fail("Expiry Audit - Get Subscribers", 
                              f"Failed to get subscribers: {subs_response.status_code}")
                return
            
            subscribers = subs_response.json()
            print(f"✓ Found {len(subscribers)} subscribers")
            
            if not subscribers:
                result.add_warning("Expiry Audit", 
                                 "No subscribers found to test expiry audit endpoint")
                return
            
            # Test with first subscriber
            subscriber_id = subscribers[0]["id"]
            subscriber_name = subscribers[0].get("name", "Unknown")
            print(f"\n→ Testing expiry audit for subscriber: {subscriber_name} (ID: {subscriber_id})")
            
            # Call expiry audit endpoint
            audit_response = await client.get(
                f"{BASE_URL}/operator/subscribers/{subscriber_id}/expiry-audit"
            )
            
            if audit_response.status_code != 200:
                result.add_fail("Expiry Audit", 
                              f"API returned {audit_response.status_code}: {audit_response.text}")
                return
            
            audit_data = audit_response.json()
            
            # Validate response structure
            required_fields = ["subscriber_id", "subscriber_name", "events"]
            missing_fields = [f for f in required_fields if f not in audit_data]
            
            if missing_fields:
                result.add_fail("Expiry Audit - Response Structure", 
                              f"Missing fields: {missing_fields}")
                return
            
            # Validate data
            if audit_data["subscriber_id"] != subscriber_id:
                result.add_fail("Expiry Audit - Data Validation", 
                              f"Subscriber ID mismatch: expected {subscriber_id}, got {audit_data['subscriber_id']}")
                return
            
            events = audit_data["events"]
            print(f"✓ Response structure valid")
            print(f"✓ Found {len(events)} expiry audit events")
            
            if events:
                print("\n  Sample event:")
                event = events[0]
                for key in ["invoice_number", "plan_name", "service_start_date", "service_end_date"]:
                    if key in event:
                        print(f"    - {key}: {event[key]}")
            
            result.add_pass("Expiry Audit Endpoint", 
                          f"Successfully retrieved {len(events)} events for subscriber {subscriber_name}")
            
    except Exception as e:
        result.add_fail("Expiry Audit", f"Exception: {str(e)}")


async def test_backup_list(result: TestResult):
    """Test GET /api/admin/backup/list with pagination"""
    print("\n" + "="*80)
    print("TEST 2: Admin Backup List Endpoint (with pagination)")
    print("="*80)
    
    try:
        # Login as admin
        cookies = await login(ADMIN_EMAIL, ADMIN_PASSWORD)
        print(f"✓ Logged in as admin: {ADMIN_EMAIL}")
        
        async with httpx.AsyncClient(follow_redirects=True, cookies=cookies) as client:
            # Test 1: Default pagination
            print("\n→ Testing default pagination...")
            response1 = await client.get(f"{BASE_URL}/admin/backup/list")
            
            if response1.status_code != 200:
                result.add_fail("Backup List - Default", 
                              f"API returned {response1.status_code}: {response1.text}")
                return
            
            data1 = response1.json()
            
            # Validate response structure
            required_fields = ["backups", "total", "page", "per_page", "total_pages"]
            missing_fields = [f for f in required_fields if f not in data1]
            
            if missing_fields:
                result.add_fail("Backup List - Response Structure", 
                              f"Missing fields: {missing_fields}")
                return
            
            print(f"✓ Response structure valid")
            print(f"  - Total backups: {data1['total']}")
            print(f"  - Page: {data1['page']}")
            print(f"  - Per page: {data1['per_page']}")
            print(f"  - Total pages: {data1['total_pages']}")
            print(f"  - Backups in response: {len(data1['backups'])}")
            
            # Test 2: Custom pagination
            print("\n→ Testing custom pagination (page=1, per_page=5)...")
            response2 = await client.get(f"{BASE_URL}/admin/backup/list?page=1&per_page=5")
            
            if response2.status_code != 200:
                result.add_fail("Backup List - Custom Pagination", 
                              f"API returned {response2.status_code}: {response2.text}")
                return
            
            data2 = response2.json()
            
            if data2["per_page"] != 5:
                result.add_fail("Backup List - Pagination", 
                              f"Expected per_page=5, got {data2['per_page']}")
                return
            
            if len(data2["backups"]) > 5:
                result.add_fail("Backup List - Pagination", 
                              f"Expected max 5 backups, got {len(data2['backups'])}")
                return
            
            print(f"✓ Custom pagination working correctly")
            print(f"  - Returned {len(data2['backups'])} backups (max 5)")
            
            # Validate backup structure if any exist
            if data1["backups"]:
                backup = data1["backups"][0]
                backup_fields = ["id", "filename", "created_at", "size_bytes", "type"]
                missing_backup_fields = [f for f in backup_fields if f not in backup]
                
                if missing_backup_fields:
                    result.add_warning("Backup List - Backup Structure", 
                                     f"Backup missing fields: {missing_backup_fields}")
                else:
                    print(f"\n  Sample backup:")
                    print(f"    - ID: {backup['id']}")
                    print(f"    - Filename: {backup['filename']}")
                    print(f"    - Type: {backup['type']}")
                    print(f"    - Size: {backup.get('size_kb', 0)} KB")
            
            result.add_pass("Backup List Endpoint", 
                          f"Successfully retrieved {data1['total']} backups with pagination support")
            
    except Exception as e:
        result.add_fail("Backup List", f"Exception: {str(e)}")


async def test_whatsapp_stats(result: TestResult):
    """Test GET /api/operator/whatsapp-stats"""
    print("\n" + "="*80)
    print("TEST 3: WhatsApp Stats Endpoint")
    print("="*80)
    
    try:
        # Login as operator
        cookies = await login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
        print(f"✓ Logged in as operator: {OPERATOR_EMAIL}")
        
        async with httpx.AsyncClient(follow_redirects=True, cookies=cookies) as client:
            print("\n→ Fetching WhatsApp statistics...")
            response = await client.get(f"{BASE_URL}/operator/whatsapp-stats")
            
            if response.status_code != 200:
                result.add_fail("WhatsApp Stats", 
                              f"API returned {response.status_code}: {response.text}")
                return
            
            stats = response.json()
            
            # Validate response structure
            required_fields = [
                "total", "today", "this_month", "sent", "failed", 
                "success_rate", "by_category", "by_trigger", "recent_7_days"
            ]
            missing_fields = [f for f in required_fields if f not in stats]
            
            if missing_fields:
                result.add_fail("WhatsApp Stats - Response Structure", 
                              f"Missing fields: {missing_fields}")
                return
            
            print(f"✓ Response structure valid")
            print(f"\n  Statistics:")
            print(f"    - Total messages: {stats['total']}")
            print(f"    - Today: {stats['today']}")
            print(f"    - This month: {stats['this_month']}")
            print(f"    - Sent: {stats['sent']}")
            print(f"    - Failed: {stats['failed']}")
            print(f"    - Success rate: {stats['success_rate']}%")
            
            # Validate data types
            if not isinstance(stats["by_category"], dict):
                result.add_fail("WhatsApp Stats - Data Type", 
                              f"by_category should be dict, got {type(stats['by_category'])}")
                return
            
            if not isinstance(stats["by_trigger"], dict):
                result.add_fail("WhatsApp Stats - Data Type", 
                              f"by_trigger should be dict, got {type(stats['by_trigger'])}")
                return
            
            if not isinstance(stats["recent_7_days"], list):
                result.add_fail("WhatsApp Stats - Data Type", 
                              f"recent_7_days should be list, got {type(stats['recent_7_days'])}")
                return
            
            if stats["by_category"]:
                print(f"\n  By Category:")
                for cat, count in stats["by_category"].items():
                    print(f"    - {cat}: {count}")
            
            if stats["by_trigger"]:
                print(f"\n  By Trigger:")
                for trigger, count in stats["by_trigger"].items():
                    print(f"    - {trigger}: {count}")
            
            if stats["recent_7_days"]:
                print(f"\n  Recent 7 days: {len(stats['recent_7_days'])} data points")
            
            result.add_pass("WhatsApp Stats Endpoint", 
                          f"Successfully retrieved stats: {stats['total']} total messages, {stats['success_rate']}% success rate")
            
    except Exception as e:
        result.add_fail("WhatsApp Stats", f"Exception: {str(e)}")


async def test_whatsapp_message_logs(result: TestResult):
    """Test GET /api/operator/whatsapp-message-logs"""
    print("\n" + "="*80)
    print("TEST 4: WhatsApp Message Logs Endpoint")
    print("="*80)
    
    try:
        # Login as operator
        cookies = await login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
        print(f"✓ Logged in as operator: {OPERATOR_EMAIL}")
        
        async with httpx.AsyncClient(follow_redirects=True, cookies=cookies) as client:
            # Test 1: Default pagination
            print("\n→ Testing default pagination...")
            response1 = await client.get(f"{BASE_URL}/operator/whatsapp-message-logs")
            
            if response1.status_code != 200:
                result.add_fail("WhatsApp Message Logs - Default", 
                              f"API returned {response1.status_code}: {response1.text}")
                return
            
            data1 = response1.json()
            
            # Validate response structure
            required_fields = ["logs", "total", "page", "per_page", "total_pages"]
            missing_fields = [f for f in required_fields if f not in data1]
            
            if missing_fields:
                result.add_fail("WhatsApp Message Logs - Response Structure", 
                              f"Missing fields: {missing_fields}")
                return
            
            print(f"✓ Response structure valid")
            print(f"  - Total logs: {data1['total']}")
            print(f"  - Page: {data1['page']}")
            print(f"  - Per page: {data1['per_page']}")
            print(f"  - Total pages: {data1['total_pages']}")
            print(f"  - Logs in response: {len(data1['logs'])}")
            
            # Test 2: Custom pagination
            print("\n→ Testing custom pagination (page=1, per_page=5)...")
            response2 = await client.get(
                f"{BASE_URL}/operator/whatsapp-message-logs?page=1&per_page=5"
            )
            
            if response2.status_code != 200:
                result.add_fail("WhatsApp Message Logs - Custom Pagination", 
                              f"API returned {response2.status_code}: {response2.text}")
                return
            
            data2 = response2.json()
            
            if data2["per_page"] != 5:
                result.add_fail("WhatsApp Message Logs - Pagination", 
                              f"Expected per_page=5, got {data2['per_page']}")
                return
            
            if len(data2["logs"]) > 5:
                result.add_fail("WhatsApp Message Logs - Pagination", 
                              f"Expected max 5 logs, got {len(data2['logs'])}")
                return
            
            print(f"✓ Custom pagination working correctly")
            print(f"  - Returned {len(data2['logs'])} logs (max 5)")
            
            # Validate log structure if any exist
            if data1["logs"]:
                log = data1["logs"][0]
                log_fields = ["operator_id", "template_name", "recipient_phone", "status", "created_at"]
                present_fields = [f for f in log_fields if f in log]
                
                print(f"\n  Sample log entry:")
                for field in present_fields:
                    print(f"    - {field}: {log[field]}")
            
            result.add_pass("WhatsApp Message Logs Endpoint", 
                          f"Successfully retrieved {data1['total']} logs with pagination support")
            
    except Exception as e:
        result.add_fail("WhatsApp Message Logs", f"Exception: {str(e)}")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("E-BILL BACKEND API TESTING")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    result = TestResult()
    
    # Run all tests
    await test_expiry_audit(result)
    await test_backup_list(result)
    await test_whatsapp_stats(result)
    await test_whatsapp_message_logs(result)
    
    # Print summary
    result.print_summary()
    
    # Return exit code
    return 0 if not result.failed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
