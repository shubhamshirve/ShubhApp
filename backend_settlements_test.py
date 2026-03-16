#!/usr/bin/env python3
"""
Settlements API Testing Suite for Multi-Tenant SaaS Billing Platform
Testing all settlements-related endpoints as specified in review request:
1. GET /api/admin/settlements/summary
2. GET /api/admin/settlements (with pagination and filters) 
3. GET /api/admin/settlements/{settlement_id}
4. PUT /api/admin/settlements/{settlement_id}/status
5. POST /api/admin/settlements/process
6. PUT /api/admin/settlements/platform-fee
7. Daily settlement cron job (referenced)
"""

import requests
import json
import uuid
from datetime import datetime
import os
from typing import Dict, Any, Optional, List

# Backend URL from frontend/.env
BACKEND_URL = "https://settlement-analyzer-2.preview.emergentagent.com/api"

class SettlementsTester:
    def __init__(self):
        self.admin_token = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.settlement_ids = []  # Store settlement IDs for testing
        
    def log(self, message: str):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def make_request(self, method: str, endpoint: str, token: str = None, **kwargs) -> requests.Response:
        """Make authenticated request to backend"""
        url = f"{BACKEND_URL}{endpoint}"
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            return response
        except Exception as e:
            self.log(f"❌ Request failed: {e}")
            raise
            
    def test_admin_login(self) -> bool:
        """Test admin authentication"""
        self.log("🔐 Testing admin login...")
        try:
            login_data = {
                "email": "admin@saas.com",
                "password": "admin123"
            }
            response = self.make_request('POST', '/auth/login', json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get('access_token')
                self.log("✅ Admin login successful")
                return True
            else:
                self.log(f"❌ Admin login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Admin login error: {e}")
            return False

    def test_settlements_summary(self) -> bool:
        """Test 1: GET /api/admin/settlements/summary"""
        self.log("\n🧪 TEST 1: GET /api/admin/settlements/summary")
        try:
            response = self.make_request('GET', '/admin/settlements/summary', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Summary response received")
                
                # Check required fields
                required_fields = [
                    'total_settled', 'total_pending', 'platform_fee_percentage', 
                    'pending_count', 'completed_count', 'processing_count'
                ]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log(f"❌ Missing required fields: {missing_fields}")
                    return False
                    
                # Verify data types and expected values
                platform_fee_pct = data.get('platform_fee_percentage', 0)
                completed_count = data.get('completed_count', 0)
                pending_count = data.get('pending_count', 0)
                
                self.log(f"  Platform fee percentage: {platform_fee_pct}%")
                self.log(f"  Completed settlements: {completed_count}")
                self.log(f"  Pending settlements: {pending_count}")
                
                # According to review request, should have >= 2 completed, >= 1 pending
                if completed_count >= 2 and pending_count >= 1:
                    self.log("✅ Expected settlement counts verified (>=2 completed, >=1 pending)")
                    return True
                else:
                    self.log(f"❌ Unexpected settlement counts - completed: {completed_count}, pending: {pending_count}")
                    return False
                    
            else:
                self.log(f"❌ Summary failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Summary test error: {e}")
            return False

    def test_settlements_list(self) -> bool:
        """Test 2: GET /api/admin/settlements with pagination and filters"""
        self.log("\n🧪 TEST 2: GET /api/admin/settlements (pagination & filters)")
        
        try:
            # Test 2a: Basic pagination
            self.log("  Testing basic pagination...")
            response = self.make_request('GET', '/admin/settlements?page=1&limit=10', token=self.admin_token)
            
            if response.status_code != 200:
                self.log(f"❌ List settlements failed: {response.status_code} - {response.text}")
                return False
                
            data = response.json()
            required_fields = ['settlements', 'total', 'page', 'pages']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                self.log(f"❌ Missing pagination fields: {missing_fields}")
                return False
                
            settlements = data.get('settlements', [])
            total_count = data.get('total', 0)
            
            self.log(f"  ✅ Found {len(settlements)} settlements (total: {total_count})")
            
            # Store settlement IDs for detail testing
            if settlements:
                self.settlement_ids = [s.get('id') for s in settlements if s.get('id')]
                
            # Test 2b: Status filter - completed
            self.log("  Testing status filter: completed...")
            response = self.make_request('GET', '/admin/settlements?status=completed', token=self.admin_token)
            
            if response.status_code == 200:
                completed_data = response.json()
                completed_settlements = completed_data.get('settlements', [])
                
                # Verify all returned settlements have "completed" status
                all_completed = all(s.get('status') == 'completed' for s in completed_settlements)
                if all_completed:
                    self.log(f"  ✅ Completed filter working: {len(completed_settlements)} settlements")
                else:
                    self.log("  ❌ Completed filter not working - mixed statuses returned")
                    return False
            else:
                self.log(f"  ❌ Completed filter failed: {response.status_code}")
                return False
                
            # Test 2c: Status filter - pending
            self.log("  Testing status filter: pending...")
            response = self.make_request('GET', '/admin/settlements?status=pending', token=self.admin_token)
            
            if response.status_code == 200:
                pending_data = response.json()
                pending_settlements = pending_data.get('settlements', [])
                
                # Verify all returned settlements have "pending" status
                all_pending = all(s.get('status') == 'pending' for s in pending_settlements)
                if all_pending:
                    self.log(f"  ✅ Pending filter working: {len(pending_settlements)} settlements")
                    return True
                else:
                    self.log("  ❌ Pending filter not working - mixed statuses returned")
                    return False
            else:
                self.log(f"  ❌ Pending filter failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ List settlements test error: {e}")
            return False

    def test_settlement_detail(self) -> bool:
        """Test 3: GET /api/admin/settlements/{settlement_id}"""
        self.log("\n🧪 TEST 3: GET /api/admin/settlements/{settlement_id}")
        
        if not self.settlement_ids:
            self.log("❌ No settlement IDs available for detail testing")
            return False
            
        try:
            settlement_id = self.settlement_ids[0]
            self.log(f"  Testing detail for settlement: {settlement_id}")
            
            response = self.make_request('GET', f'/admin/settlements/{settlement_id}', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for required fields in settlement detail
                required_fields = ['id', 'operator_id', 'settlement_date', 'status', 'net_settlement']
                settlement_fields = [field for field in required_fields if field not in data]
                
                if settlement_fields:
                    self.log(f"❌ Missing settlement fields: {settlement_fields}")
                    return False
                    
                # Check for invoices array
                if 'invoices' not in data:
                    self.log("❌ Missing 'invoices' array in settlement detail")
                    return False
                    
                # Check for operator_details
                if 'operator_details' not in data:
                    self.log("❌ Missing 'operator_details' in settlement detail")
                    return False
                    
                invoices_count = len(data.get('invoices', []))
                operator_name = data.get('operator_details', {}).get('company_name', 'Unknown')
                
                self.log(f"  ✅ Settlement detail retrieved: {invoices_count} invoices, operator: {operator_name}")
                return True
                
            else:
                self.log(f"❌ Settlement detail failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Settlement detail test error: {e}")
            return False

    def test_settlement_status_updates(self) -> Dict[str, bool]:
        """Test 4 & 5: PUT /api/admin/settlements/{settlement_id}/status"""
        self.log("\n🧪 TEST 4-5: PUT /api/admin/settlements/{settlement_id}/status")
        results = {}
        
        if not self.settlement_ids:
            self.log("❌ No settlement IDs available for status update testing")
            return {"processing_status": False, "completed_status": False}
            
        try:
            # Find a settlement that we can update
            settlement_id = None
            for sid in self.settlement_ids:
                response = self.make_request('GET', f'/admin/settlements/{sid}', token=self.admin_token)
                if response.status_code == 200:
                    settlement = response.json()
                    if settlement.get('status') == 'pending':
                        settlement_id = sid
                        break
                        
            if not settlement_id:
                self.log("❌ No pending settlements found for status update testing")
                return {"processing_status": False, "completed_status": False}
                
            # Test 4a: Update to processing
            self.log(f"  Testing status update to 'processing' for: {settlement_id}")
            response = self.make_request('PUT', f'/admin/settlements/{settlement_id}/status?status=processing', 
                                       token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'processing':
                    self.log("  ✅ Status updated to 'processing'")
                    results["processing_status"] = True
                else:
                    self.log(f"  ❌ Status not updated correctly: {data.get('status')}")
                    results["processing_status"] = False
            else:
                self.log(f"  ❌ Processing status update failed: {response.status_code}")
                results["processing_status"] = False
                
            # Test 4b: Update to completed with UTR
            self.log(f"  Testing status update to 'completed' with UTR...")
            response = self.make_request('PUT', f'/admin/settlements/{settlement_id}/status?status=completed&utr_number=UTR123TEST', 
                                       token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                if (data.get('status') == 'completed' and 
                    data.get('utr_number') == 'UTR123TEST' and 
                    data.get('paid_at')):
                    self.log("  ✅ Status updated to 'completed' with UTR and paid_at")
                    results["completed_status"] = True
                else:
                    self.log(f"  ❌ Completed status update incomplete: status={data.get('status')}, utr={data.get('utr_number')}, paid_at={data.get('paid_at')}")
                    results["completed_status"] = False
            else:
                self.log(f"  ❌ Completed status update failed: {response.status_code}")
                results["completed_status"] = False
                
        except Exception as e:
            self.log(f"❌ Status update test error: {e}")
            results["processing_status"] = False
            results["completed_status"] = False
            
        return results

    def test_manual_settlement_processing(self) -> bool:
        """Test 6: POST /api/admin/settlements/process"""
        self.log("\n🧪 TEST 6: POST /api/admin/settlements/process")
        
        try:
            response = self.make_request('POST', '/admin/settlements/process', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for expected response fields
                if 'message' not in data or 'settlements_created' not in data:
                    self.log(f"❌ Missing required fields in process response: {data}")
                    return False
                    
                settlements_created = data.get('settlements_created', 0)
                message = data.get('message', '')
                
                self.log(f"  ✅ Manual processing response: {settlements_created} settlements created")
                self.log(f"  Message: {message}")
                return True
                
            else:
                self.log(f"❌ Manual processing failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Manual processing test error: {e}")
            return False

    def test_platform_fee_update(self) -> bool:
        """Test 7: PUT /api/admin/settlements/platform-fee"""
        self.log("\n🧪 TEST 7: PUT /api/admin/settlements/platform-fee")
        
        try:
            # Test 7a: Update platform fee to 3%
            self.log("  Testing platform fee update to 3%...")
            response = self.make_request('PUT', '/admin/settlements/platform-fee?percentage=3', 
                                       token=self.admin_token)
            
            if response.status_code != 200:
                self.log(f"❌ Platform fee update to 3% failed: {response.status_code}")
                return False
                
            data = response.json()
            if data.get('platform_fee_percentage') != 3:
                self.log(f"❌ Platform fee not updated to 3%: {data}")
                return False
                
            # Test 7b: Verify summary shows 3%
            self.log("  Verifying summary shows updated 3% fee...")
            response = self.make_request('GET', '/admin/settlements/summary', token=self.admin_token)
            
            if response.status_code != 200:
                self.log(f"❌ Could not verify fee in summary: {response.status_code}")
                return False
                
            summary_data = response.json()
            if summary_data.get('platform_fee_percentage') != 3:
                self.log(f"❌ Summary does not show 3% fee: {summary_data.get('platform_fee_percentage')}")
                return False
                
            # Test 7c: Reset back to 2%
            self.log("  Resetting platform fee back to 2%...")
            response = self.make_request('PUT', '/admin/settlements/platform-fee?percentage=2', 
                                       token=self.admin_token)
            
            if response.status_code == 200:
                reset_data = response.json()
                if reset_data.get('platform_fee_percentage') == 2:
                    self.log("  ✅ Platform fee updated and reset successfully")
                    return True
                else:
                    self.log(f"❌ Platform fee not reset to 2%: {reset_data}")
                    return False
            else:
                self.log(f"❌ Platform fee reset failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Platform fee update test error: {e}")
            return False

    def run_all_tests(self):
        """Run all settlements tests"""
        self.log("🚀 Starting Settlements API Testing Suite")
        self.log(f"Backend URL: {BACKEND_URL}")
        self.log("Testing settlements endpoints as per review request")
        
        # Initialize authentication
        if not self.test_admin_login():
            self.log("❌ Admin authentication failed - aborting tests")
            return
        
        # Run all settlements tests
        results = {}
        
        # Test 1: Summary API
        results["summary"] = self.test_settlements_summary()
        
        # Test 2: List API with filters
        results["list_and_filters"] = self.test_settlements_list()
        
        # Test 3: Detail API
        results["detail"] = self.test_settlement_detail()
        
        # Test 4-5: Status updates
        status_results = self.test_settlement_status_updates()
        results.update(status_results)
        
        # Test 6: Manual processing
        results["manual_processing"] = self.test_manual_settlement_processing()
        
        # Test 7: Platform fee update
        results["platform_fee_update"] = self.test_platform_fee_update()
        
        # Summary
        self.log("\n📊 SETTLEMENTS API TEST SUMMARY")
        self.log("=" * 60)
        
        test_names = [
            ("1. Settlements Summary API", "summary"),
            ("2. Settlements List & Filters", "list_and_filters"), 
            ("3. Settlement Detail API", "detail"),
            ("4. Status Update (Processing)", "processing_status"),
            ("5. Status Update (Completed+UTR)", "completed_status"),
            ("6. Manual Settlement Processing", "manual_processing"),
            ("7. Platform Fee Update", "platform_fee_update")
        ]
        
        passed_count = 0
        total_count = len(test_names)
        
        for name, key in test_names:
            passed = results.get(key, False)
            status = "✅ PASSED" if passed else "❌ FAILED"
            self.log(f"{name}: {status}")
            if passed:
                passed_count += 1
                
        # Overall results
        success_rate = (passed_count / total_count) * 100
        self.log(f"\nOVERALL: {passed_count}/{total_count} tests passed ({success_rate:.1f}%)")
        
        if passed_count == total_count:
            self.log("🎉 ALL SETTLEMENTS API TESTS PASSED!")
        else:
            self.log("⚠️  Some settlements tests failed - please review the results above")
            
        # Additional info
        if self.settlement_ids:
            self.log(f"\n📋 Test Data: Found {len(self.settlement_ids)} settlements for testing")
        else:
            self.log("\n⚠️  No settlement data found - some tests may be limited")

if __name__ == "__main__":
    tester = SettlementsTester()
    tester.run_all_tests()