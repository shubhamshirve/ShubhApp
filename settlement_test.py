#!/usr/bin/env python3
"""
Settlement Flow Testing Suite
Testing comprehensive settlement flow with sample seeded data.

Test Scenarios:
1. Admin Settlement Summary
2. Admin Settlement List (with filters)
3. Admin Settlement Detail
4. Settlement Status Update (pending -> processing -> completed)
5. Process Settlements for Today
6. Operator Settlement Summary
7. Operator Settlement List
8. Operator Settlement Detail
9. Platform Fee Update

Credentials:
- Admin: admin@saas.com / admin123
- Operator: venkat@krishnacable.in / operator123
"""

import requests
import json
import uuid
from datetime import datetime, date
import os
from typing import Dict, Any, Optional, List

# Backend URL from frontend/.env
BACKEND_URL = "https://settlement-analyzer-2.preview.emergentagent.com/api"

class SettlementTester:
    def __init__(self):
        self.admin_token = None
        self.operator_token = None
        self.operator_id = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.settlement_ids = []
        
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

    def test_operator_login(self) -> bool:
        """Test operator authentication"""
        self.log("🔐 Testing operator login...")
        try:
            login_data = {
                "email": "venkat@krishnacable.in",
                "password": "operator123"
            }
            response = self.make_request('POST', '/auth/login', json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get('access_token')
                self.operator_id = data.get('user', {}).get('operator_id')
                self.log("✅ Operator login successful")
                return True
            else:
                self.log(f"❌ Operator login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Operator login error: {e}")
            return False

    def test_admin_settlement_summary(self) -> Dict[str, Any]:
        """Test 1: Admin Settlement Summary"""
        self.log("\n🧪 TEST 1: Admin Settlement Summary")
        try:
            response = self.make_request('GET', '/admin/settlements/summary', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"  Summary response: {json.dumps(data, indent=2)}")
                
                # Verify expected fields
                required_fields = ['total_settled', 'pending_count', 'completed_count', 'platform_fee_percentage']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log(f"  ❌ Missing required fields: {missing_fields}")
                    return {"success": False, "error": f"Missing fields: {missing_fields}"}
                
                # Verify data expectations
                total_settled = data.get('total_settled', 0)
                pending_count = data.get('pending_count', 0)
                completed_count = data.get('completed_count', 0)
                platform_fee_percentage = data.get('platform_fee_percentage', 0)
                
                checks = {
                    "total_settled_positive": total_settled > 0,
                    "pending_count_ge_2": pending_count >= 2,
                    "completed_count_ge_1": completed_count >= 1,
                    "platform_fee_is_2": platform_fee_percentage == 2
                }
                
                self.log(f"  Verification checks:")
                self.log(f"    - total_settled > 0: {total_settled} {'✅' if checks['total_settled_positive'] else '❌'}")
                self.log(f"    - pending_count >= 2: {pending_count} {'✅' if checks['pending_count_ge_2'] else '❌'}")
                self.log(f"    - completed_count >= 1: {completed_count} {'✅' if checks['completed_count_ge_1'] else '❌'}")
                self.log(f"    - platform_fee_percentage = 2: {platform_fee_percentage}% {'✅' if checks['platform_fee_is_2'] else '❌'}")
                
                success = all(checks.values())
                if success:
                    self.log("  ✅ Admin Settlement Summary - ALL CHECKS PASSED")
                else:
                    failed_checks = [k for k, v in checks.items() if not v]
                    self.log(f"  ❌ Admin Settlement Summary - FAILED CHECKS: {failed_checks}")
                
                return {"success": success, "data": data, "checks": checks}
            else:
                error_msg = f"HTTP {response.status_code} - {response.text}"
                self.log(f"  ❌ Admin Settlement Summary failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            self.log(f"  ❌ Admin Settlement Summary error: {e}")
            return {"success": False, "error": str(e)}

    def test_admin_settlement_list(self) -> Dict[str, Any]:
        """Test 2: Admin Settlement List"""
        self.log("\n🧪 TEST 2: Admin Settlement List")
        results = {}
        
        try:
            # Test 2a: Get all settlements
            self.log("  2a: Testing GET /admin/settlements (all settlements)...")
            response = self.make_request('GET', '/admin/settlements', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                settlements = data.get('settlements', [])
                total = data.get('total', 0)
                
                # Store settlement IDs for later tests
                self.settlement_ids = [s.get('id') for s in settlements if s.get('id')]
                
                self.log(f"    Found {len(settlements)} settlements, total={total}")
                if len(settlements) >= 4:
                    self.log("    ✅ At least 4 settlements exist")
                    results["all_settlements"] = {"success": True, "count": len(settlements)}
                else:
                    self.log(f"    ❌ Expected at least 4 settlements, got {len(settlements)}")
                    results["all_settlements"] = {"success": False, "count": len(settlements)}
            else:
                error_msg = f"HTTP {response.status_code} - {response.text}"
                self.log(f"    ❌ Failed to get all settlements: {error_msg}")
                results["all_settlements"] = {"success": False, "error": error_msg}
            
            # Test 2b: Filter by completed status
            self.log("  2b: Testing status filter ?status=completed...")
            response = self.make_request('GET', '/admin/settlements?status=completed', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                settlements = data.get('settlements', [])
                
                self.log(f"    Found {len(settlements)} completed settlements")
                if len(settlements) >= 1:
                    self.log("    ✅ At least 1 completed settlement exists")
                    results["completed_filter"] = {"success": True, "count": len(settlements)}
                else:
                    self.log(f"    ❌ Expected at least 1 completed settlement, got {len(settlements)}")
                    results["completed_filter"] = {"success": False, "count": len(settlements)}
            else:
                error_msg = f"HTTP {response.status_code} - {response.text}"
                self.log(f"    ❌ Failed to filter completed settlements: {error_msg}")
                results["completed_filter"] = {"success": False, "error": error_msg}
            
            # Test 2c: Filter by pending status
            self.log("  2c: Testing status filter ?status=pending...")
            response = self.make_request('GET', '/admin/settlements?status=pending', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                settlements = data.get('settlements', [])
                
                self.log(f"    Found {len(settlements)} pending settlements")
                if len(settlements) >= 2:
                    self.log("    ✅ At least 2 pending settlements exist")
                    results["pending_filter"] = {"success": True, "count": len(settlements)}
                else:
                    self.log(f"    ❌ Expected at least 2 pending settlements, got {len(settlements)}")
                    results["pending_filter"] = {"success": False, "count": len(settlements)}
            else:
                error_msg = f"HTTP {response.status_code} - {response.text}"
                self.log(f"    ❌ Failed to filter pending settlements: {error_msg}")
                results["pending_filter"] = {"success": False, "error": error_msg}
            
        except Exception as e:
            self.log(f"  ❌ Admin Settlement List error: {e}")
            results["error"] = str(e)
        
        # Overall success
        all_passed = all(result.get("success", False) for result in results.values() if "success" in result)
        if all_passed:
            self.log("  ✅ Admin Settlement List - ALL TESTS PASSED")
        else:
            self.log("  ❌ Admin Settlement List - SOME TESTS FAILED")
        
        return {"success": all_passed, "results": results}

    def test_admin_settlement_detail(self) -> Dict[str, Any]:
        """Test 3: Admin Settlement Detail"""
        self.log("\n🧪 TEST 3: Admin Settlement Detail")
        
        if not self.settlement_ids:
            self.log("  ❌ No settlement IDs available from previous tests")
            return {"success": False, "error": "No settlement IDs available"}
        
        try:
            settlement_id = self.settlement_ids[0]
            self.log(f"  Testing GET /admin/settlements/{settlement_id}...")
            
            response = self.make_request('GET', f'/admin/settlements/{settlement_id}', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"  Settlement detail keys: {list(data.keys())}")
                
                # Verify required fields
                invoices = data.get('invoices', [])
                operator_details = data.get('operator_details', {})
                
                checks = {
                    "has_invoices": len(invoices) > 0,
                    "has_operator_details": bool(operator_details),
                    "has_bank_name": bool(operator_details.get('bank_name')),
                    "has_bank_account": bool(operator_details.get('bank_account_number')),
                    "has_bank_ifsc": bool(operator_details.get('bank_ifsc'))
                }
                
                self.log(f"  Verification checks:")
                self.log(f"    - invoices array not empty: {len(invoices)} invoices {'✅' if checks['has_invoices'] else '❌'}")
                self.log(f"    - operator_details present: {'✅' if checks['has_operator_details'] else '❌'}")
                
                if operator_details:
                    self.log(f"    - bank_name: {operator_details.get('bank_name', 'MISSING')} {'✅' if checks['has_bank_name'] else '❌'}")
                    self.log(f"    - bank_account_number: {operator_details.get('bank_account_number', 'MISSING')} {'✅' if checks['has_bank_account'] else '❌'}")
                    self.log(f"    - bank_ifsc: {operator_details.get('bank_ifsc', 'MISSING')} {'✅' if checks['has_bank_ifsc'] else '❌'}")
                
                success = all(checks.values())
                if success:
                    self.log("  ✅ Admin Settlement Detail - ALL CHECKS PASSED")
                else:
                    failed_checks = [k for k, v in checks.items() if not v]
                    self.log(f"  ❌ Admin Settlement Detail - FAILED CHECKS: {failed_checks}")
                
                return {"success": success, "data": data, "checks": checks}
            else:
                error_msg = f"HTTP {response.status_code} - {response.text}"
                self.log(f"  ❌ Admin Settlement Detail failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            self.log(f"  ❌ Admin Settlement Detail error: {e}")
            return {"success": False, "error": str(e)}

    def test_settlement_status_update(self) -> Dict[str, Any]:
        """Test 4: Settlement Status Update"""
        self.log("\n🧪 TEST 4: Settlement Status Update")
        
        # Find a pending settlement
        try:
            response = self.make_request('GET', '/admin/settlements?status=pending', token=self.admin_token)
            if response.status_code != 200:
                self.log(f"  ❌ Could not fetch pending settlements: {response.status_code}")
                return {"success": False, "error": "Could not fetch pending settlements"}
            
            data = response.json()
            settlements = data.get('settlements', [])
            if not settlements:
                self.log("  ❌ No pending settlements found for status update test")
                return {"success": False, "error": "No pending settlements found"}
            
            settlement_id = settlements[0]['id']
            self.log(f"  Using pending settlement: {settlement_id}")
            
            # Step 1: Update to processing
            self.log("  4a: Updating status to 'processing'...")
            response = self.make_request('PUT', f'/admin/settlements/{settlement_id}/status?status=processing', 
                                      token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'processing':
                    self.log("    ✅ Status updated to processing")
                    processing_success = True
                else:
                    self.log(f"    ❌ Status not updated correctly: {data.get('status')}")
                    processing_success = False
            else:
                self.log(f"    ❌ Failed to update to processing: {response.status_code} - {response.text}")
                processing_success = False
            
            # Step 2: Update to completed with UTR
            self.log("  4b: Updating status to 'completed' with UTR...")
            response = self.make_request('PUT', f'/admin/settlements/{settlement_id}/status?status=completed&utr_number=NEFT20260313TEST', 
                                      token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                checks = {
                    "status_completed": data.get('status') == 'completed',
                    "utr_number_set": data.get('utr_number') == 'NEFT20260313TEST',
                    "paid_at_set": bool(data.get('paid_at'))
                }
                
                self.log(f"    Verification checks:")
                self.log(f"      - status = completed: {'✅' if checks['status_completed'] else '❌'}")
                self.log(f"      - utr_number = NEFT20260313TEST: {'✅' if checks['utr_number_set'] else '❌'}")
                self.log(f"      - paid_at is set: {'✅' if checks['paid_at_set'] else '❌'}")
                
                completed_success = all(checks.values())
                if completed_success:
                    self.log("    ✅ Status updated to completed with UTR and paid_at")
                else:
                    failed_checks = [k for k, v in checks.items() if not v]
                    self.log(f"    ❌ Failed checks: {failed_checks}")
            else:
                self.log(f"    ❌ Failed to update to completed: {response.status_code} - {response.text}")
                completed_success = False
                checks = {}
            
            overall_success = processing_success and completed_success
            if overall_success:
                self.log("  ✅ Settlement Status Update - ALL STEPS PASSED")
            else:
                self.log("  ❌ Settlement Status Update - SOME STEPS FAILED")
            
            return {
                "success": overall_success,
                "processing_success": processing_success,
                "completed_success": completed_success,
                "checks": checks if completed_success else {}
            }
            
        except Exception as e:
            self.log(f"  ❌ Settlement Status Update error: {e}")
            return {"success": False, "error": str(e)}

    def test_process_settlements_today(self) -> Dict[str, Any]:
        """Test 5: Process Settlements for Today"""
        self.log("\n🧪 TEST 5: Process Settlements for Today")
        
        try:
            # Use today's date in the expected format
            settlement_date = "2026-03-13"
            self.log(f"  Testing POST /admin/settlements/process?settlement_date={settlement_date}...")
            
            response = self.make_request('POST', f'/admin/settlements/process?settlement_date={settlement_date}', 
                                      token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"  Process settlements response: {json.dumps(data, indent=2)}")
                
                settlements_created = data.get('settlements_created', -1)
                message = data.get('message', '')
                
                # Check if it's the expected response (already processed or new settlements created)
                is_valid_response = (
                    settlements_created == 0 and "already processed" in message.lower() or
                    "no unsettled" in message.lower() or
                    settlements_created > 0
                )
                
                if is_valid_response:
                    self.log(f"  ✅ Process settlements working - settlements_created: {settlements_created}")
                    self.log(f"      Message: {message}")
                    return {"success": True, "settlements_created": settlements_created, "message": message}
                else:
                    self.log(f"  ❌ Unexpected response - settlements_created: {settlements_created}")
                    return {"success": False, "error": f"Unexpected response: {data}"}
            else:
                error_msg = f"HTTP {response.status_code} - {response.text}"
                self.log(f"  ❌ Process settlements failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            self.log(f"  ❌ Process settlements error: {e}")
            return {"success": False, "error": str(e)}

    def test_operator_settlement_summary(self) -> Dict[str, Any]:
        """Test 6: Operator Settlement Summary"""
        self.log("\n🧪 TEST 6: Operator Settlement Summary")
        
        try:
            response = self.make_request('GET', '/operator/settlements/summary', token=self.operator_token)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"  Operator summary response: {json.dumps(data, indent=2)}")
                
                total_settled = data.get('total_settled', 0)
                total_pending = data.get('total_pending', 0)
                
                checks = {
                    "total_settled_positive": total_settled > 0,
                    "total_pending_positive": total_pending > 0
                }
                
                self.log(f"  Verification checks:")
                self.log(f"    - total_settled > 0: {total_settled} {'✅' if checks['total_settled_positive'] else '❌'}")
                self.log(f"    - total_pending > 0: {total_pending} {'✅' if checks['total_pending_positive'] else '❌'}")
                
                success = all(checks.values())
                if success:
                    self.log("  ✅ Operator Settlement Summary - ALL CHECKS PASSED")
                else:
                    failed_checks = [k for k, v in checks.items() if not v]
                    self.log(f"  ❌ Operator Settlement Summary - FAILED CHECKS: {failed_checks}")
                
                return {"success": success, "data": data, "checks": checks}
            else:
                error_msg = f"HTTP {response.status_code} - {response.text}"
                self.log(f"  ❌ Operator Settlement Summary failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            self.log(f"  ❌ Operator Settlement Summary error: {e}")
            return {"success": False, "error": str(e)}

    def test_operator_settlement_list(self) -> Dict[str, Any]:
        """Test 7: Operator Settlement List"""
        self.log("\n🧪 TEST 7: Operator Settlement List")
        
        try:
            response = self.make_request('GET', '/operator/settlements', token=self.operator_token)
            
            if response.status_code == 200:
                data = response.json()
                settlements = data.get('settlements', [])
                total = data.get('total', 0)
                
                self.log(f"  Found {len(settlements)} settlements for operator, total={total}")
                
                if len(settlements) >= 2:
                    self.log("  ✅ At least 2 settlements for this operator")
                    return {"success": True, "count": len(settlements), "data": settlements}
                else:
                    self.log(f"  ❌ Expected at least 2 settlements, got {len(settlements)}")
                    return {"success": False, "count": len(settlements), "error": f"Expected >=2, got {len(settlements)}"}
            else:
                error_msg = f"HTTP {response.status_code} - {response.text}"
                self.log(f"  ❌ Operator Settlement List failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            self.log(f"  ❌ Operator Settlement List error: {e}")
            return {"success": False, "error": str(e)}

    def test_operator_settlement_detail(self) -> Dict[str, Any]:
        """Test 8: Operator Settlement Detail"""
        self.log("\n🧪 TEST 8: Operator Settlement Detail")
        
        try:
            # First get the operator's settlements to find an ID
            response = self.make_request('GET', '/operator/settlements', token=self.operator_token)
            
            if response.status_code != 200:
                self.log(f"  ❌ Could not fetch operator settlements: {response.status_code}")
                return {"success": False, "error": "Could not fetch operator settlements"}
            
            data = response.json()
            settlements = data.get('settlements', [])
            if not settlements:
                self.log("  ❌ No settlements found for operator")
                return {"success": False, "error": "No settlements found for operator"}
            
            settlement_id = settlements[0]['id']
            self.log(f"  Testing GET /operator/settlements/{settlement_id}...")
            
            response = self.make_request('GET', f'/operator/settlements/{settlement_id}', token=self.operator_token)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"  Operator settlement detail keys: {list(data.keys())}")
                
                invoices = data.get('invoices', [])
                has_invoices = len(invoices) > 0
                
                self.log(f"  Verification check:")
                self.log(f"    - has invoices array: {len(invoices)} invoices {'✅' if has_invoices else '❌'}")
                
                if has_invoices:
                    self.log("  ✅ Operator Settlement Detail - HAS INVOICES")
                    return {"success": True, "data": data, "invoice_count": len(invoices)}
                else:
                    self.log("  ❌ Operator Settlement Detail - NO INVOICES")
                    return {"success": False, "error": "No invoices in settlement"}
            else:
                error_msg = f"HTTP {response.status_code} - {response.text}"
                self.log(f"  ❌ Operator Settlement Detail failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            self.log(f"  ❌ Operator Settlement Detail error: {e}")
            return {"success": False, "error": str(e)}

    def test_platform_fee_update(self) -> Dict[str, Any]:
        """Test 9: Platform Fee Update"""
        self.log("\n🧪 TEST 9: Platform Fee Update")
        
        try:
            # Step 1: Update platform fee to 3%
            self.log("  9a: Updating platform fee to 3%...")
            response = self.make_request('PUT', '/admin/settlements/platform-fee?percentage=3', 
                                      token=self.admin_token)
            
            if response.status_code == 200:
                self.log("    ✅ Platform fee updated to 3%")
                update_to_3_success = True
            else:
                self.log(f"    ❌ Failed to update to 3%: {response.status_code} - {response.text}")
                update_to_3_success = False
            
            # Step 2: Verify summary shows 3%
            self.log("  9b: Verifying summary shows 3%...")
            response = self.make_request('GET', '/admin/settlements/summary', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                platform_fee_percentage = data.get('platform_fee_percentage', 0)
                
                if platform_fee_percentage == 3:
                    self.log("    ✅ Summary shows 3% platform fee")
                    verify_3_success = True
                else:
                    self.log(f"    ❌ Summary shows {platform_fee_percentage}%, expected 3%")
                    verify_3_success = False
            else:
                self.log(f"    ❌ Failed to get summary: {response.status_code}")
                verify_3_success = False
            
            # Step 3: Reset to 2%
            self.log("  9c: Resetting platform fee to 2%...")
            response = self.make_request('PUT', '/admin/settlements/platform-fee?percentage=2', 
                                      token=self.admin_token)
            
            if response.status_code == 200:
                self.log("    ✅ Platform fee reset to 2%")
                reset_to_2_success = True
            else:
                self.log(f"    ❌ Failed to reset to 2%: {response.status_code} - {response.text}")
                reset_to_2_success = False
            
            # Step 4: Verify summary shows 2%
            self.log("  9d: Verifying summary shows 2%...")
            response = self.make_request('GET', '/admin/settlements/summary', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                platform_fee_percentage = data.get('platform_fee_percentage', 0)
                
                if platform_fee_percentage == 2:
                    self.log("    ✅ Summary shows 2% platform fee")
                    verify_2_success = True
                else:
                    self.log(f"    ❌ Summary shows {platform_fee_percentage}%, expected 2%")
                    verify_2_success = False
            else:
                self.log(f"    ❌ Failed to get summary: {response.status_code}")
                verify_2_success = False
            
            overall_success = all([update_to_3_success, verify_3_success, reset_to_2_success, verify_2_success])
            
            if overall_success:
                self.log("  ✅ Platform Fee Update - ALL STEPS PASSED")
            else:
                self.log("  ❌ Platform Fee Update - SOME STEPS FAILED")
            
            return {
                "success": overall_success,
                "update_to_3": update_to_3_success,
                "verify_3": verify_3_success,
                "reset_to_2": reset_to_2_success,
                "verify_2": verify_2_success
            }
            
        except Exception as e:
            self.log(f"  ❌ Platform Fee Update error: {e}")
            return {"success": False, "error": str(e)}

    def run_all_settlement_tests(self):
        """Run all settlement flow tests"""
        self.log("🎯 Starting Settlement Flow Testing Suite")
        self.log(f"Backend URL: {BACKEND_URL}")
        self.log("Sample Data Expected: 2 operators, 16 subscribers, 18 invoices (16 paid, 2 pending), 4 settlements")
        
        # Authentication
        if not self.test_admin_login():
            self.log("❌ Admin authentication failed - aborting tests")
            return
        
        if not self.test_operator_login():
            self.log("❌ Operator authentication failed - aborting tests")
            return
        
        # Run all settlement tests
        results = {}
        
        # Admin tests
        results["admin_summary"] = self.test_admin_settlement_summary()
        results["admin_list"] = self.test_admin_settlement_list()
        results["admin_detail"] = self.test_admin_settlement_detail()
        results["status_update"] = self.test_settlement_status_update()
        results["process_settlements"] = self.test_process_settlements_today()
        
        # Operator tests
        results["operator_summary"] = self.test_operator_settlement_summary()
        results["operator_list"] = self.test_operator_settlement_list()
        results["operator_detail"] = self.test_operator_settlement_detail()
        
        # Platform fee test
        results["platform_fee"] = self.test_platform_fee_update()
        
        # Final Summary
        self.log("\n🏁 SETTLEMENT FLOW TEST SUMMARY")
        self.log("=" * 80)
        
        test_names = [
            "admin_summary", "admin_list", "admin_detail", "status_update", 
            "process_settlements", "operator_summary", "operator_list", 
            "operator_detail", "platform_fee"
        ]
        
        test_labels = [
            "1. Admin Settlement Summary",
            "2. Admin Settlement List", 
            "3. Admin Settlement Detail",
            "4. Settlement Status Update",
            "5. Process Settlements for Today",
            "6. Operator Settlement Summary",
            "7. Operator Settlement List",
            "8. Operator Settlement Detail",
            "9. Platform Fee Update"
        ]
        
        passed_tests = 0
        total_tests = len(test_names)
        
        for i, (test_name, label) in enumerate(zip(test_names, test_labels)):
            test_result = results.get(test_name, {})
            success = test_result.get("success", False)
            
            status = "✅ PASSED" if success else "❌ FAILED"
            self.log(f"{label}: {status}")
            
            if success:
                passed_tests += 1
            elif "error" in test_result:
                self.log(f"   Error: {test_result['error']}")
        
        self.log(f"\nOVERALL RESULT: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        
        if passed_tests == total_tests:
            self.log("🎉 ALL SETTLEMENT FLOW TESTS PASSED!")
            self.log("The settlement system is working correctly with seeded sample data.")
        else:
            self.log("⚠️  Some settlement tests failed - please review the results above")
        
        return results

if __name__ == "__main__":
    tester = SettlementTester()
    tester.run_all_settlement_tests()