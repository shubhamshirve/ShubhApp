#!/usr/bin/env python3
"""
V9.10 Bulk Upload Updates Test Suite
Tests the new bulk upload features for plans, subscribers, and invoices.
"""

import requests
import json
import time
import io
import csv
from datetime import datetime, timedelta

# Backend URL from frontend/.env
BACKEND_URL = "https://changelog-review-13.preview.emergentagent.com/api"

# Test credentials
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

class BulkUploadTester:
    def __init__(self):
        self.operator_token = None
        self.test_results = []
        
    def log_result(self, test_name, success, details=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append(f"{status} {test_name}: {details}")
        print(f"{status} {test_name}: {details}")
        
    def authenticate_operator(self):
        """Authenticate as operator and get token"""
        try:
            response = requests.post(f"{BACKEND_URL}/auth/login", json={
                "email": OPERATOR_EMAIL,
                "password": OPERATOR_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                self.log_result("Operator Authentication", True, f"Token obtained")
                return True
            else:
                self.log_result("Operator Authentication", False, f"Status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Operator Authentication", False, f"Exception: {str(e)}")
            return False
    
    def get_headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.operator_token}"}
    
    def test_seed_data(self):
        """Ensure seed data is available"""
        try:
            response = requests.post(f"{BACKEND_URL}/seed")
            if response.status_code == 200:
                self.log_result("Seed Data", True, "Data seeded successfully")
                return True
            else:
                self.log_result("Seed Data", False, f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Seed Data", False, f"Exception: {str(e)}")
            return False
    
    def test_sample_csv_downloads(self):
        """Test 1: Download and verify sample CSVs"""
        
        # Test plans sample CSV
        try:
            response = requests.get(f"{BACKEND_URL}/operator/plans/sample-csv", headers=self.get_headers())
            if response.status_code == 200:
                csv_content = response.text
                reader = csv.reader(io.StringIO(csv_content))
                headers = next(reader)
                
                if "available_validities" in headers:
                    self.log_result("Plans Sample CSV", True, "available_validities column present")
                else:
                    self.log_result("Plans Sample CSV", False, f"available_validities column missing. Headers: {headers}")
            else:
                self.log_result("Plans Sample CSV", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_result("Plans Sample CSV", False, f"Exception: {str(e)}")
        
        # Test subscribers sample CSV
        try:
            response = requests.get(f"{BACKEND_URL}/operator/subscribers/sample-csv", headers=self.get_headers())
            if response.status_code == 200:
                csv_content = response.text
                reader = csv.reader(io.StringIO(csv_content))
                headers = next(reader)
                
                if "tenure_1" in headers:
                    self.log_result("Subscribers Sample CSV", True, "tenure_1 column present")
                else:
                    self.log_result("Subscribers Sample CSV", False, f"tenure_1 column missing. Headers: {headers}")
            else:
                self.log_result("Subscribers Sample CSV", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_result("Subscribers Sample CSV", False, f"Exception: {str(e)}")
        
        # Test invoices sample CSV
        try:
            response = requests.get(f"{BACKEND_URL}/operator/invoices/sample-csv", headers=self.get_headers())
            if response.status_code == 200:
                csv_content = response.text
                reader = csv.reader(io.StringIO(csv_content))
                headers = next(reader)
                
                if "selected_validity" in headers:
                    self.log_result("Invoices Sample CSV", True, "selected_validity column present")
                else:
                    self.log_result("Invoices Sample CSV", False, f"selected_validity column missing. Headers: {headers}")
            else:
                self.log_result("Invoices Sample CSV", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_result("Invoices Sample CSV", False, f"Exception: {str(e)}")
    
    def test_plans_bulk_upload_with_available_validities(self):
        """Test 2: Plans bulk upload with available_validities"""
        
        # First ensure at least one plan exists
        try:
            response = requests.get(f"{BACKEND_URL}/operator/plans", headers=self.get_headers())
            if response.status_code == 200:
                plans = response.json()
                self.log_result("Existing Plans Check", True, f"Found {len(plans)} existing plans")
            else:
                self.log_result("Existing Plans Check", False, f"Status {response.status_code}")
                return
        except Exception as e:
            self.log_result("Existing Plans Check", False, f"Exception: {str(e)}")
            return
        
        # Create CSV content for bulk upload
        csv_content = '''name,price,validity,available_validities,tax_percentage,tax_type,description
Bulk Test Monthly,600,monthly,"monthly,quarterly,yearly",18,exclusive,Bulk test plan'''
        
        try:
            files = {'file': ('test_plans.csv', csv_content, 'text/csv')}
            response = requests.post(f"{BACKEND_URL}/operator/plans/bulk-upload", 
                                   files=files, headers=self.get_headers())
            
            if response.status_code == 200:
                data = response.json()
                job_id = data.get("job_id")
                self.log_result("Plans Bulk Upload Submit", True, f"Job ID: {job_id}")
                
                # Poll job status
                if self.wait_for_job_completion(job_id):
                    # Verify the plan was created correctly
                    self.verify_bulk_test_plan()
                else:
                    self.log_result("Plans Bulk Upload Job", False, "Job did not complete successfully")
            else:
                self.log_result("Plans Bulk Upload Submit", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("Plans Bulk Upload Submit", False, f"Exception: {str(e)}")
    
    def verify_bulk_test_plan(self):
        """Verify the bulk test plan was created correctly"""
        try:
            response = requests.get(f"{BACKEND_URL}/operator/plans", headers=self.get_headers())
            if response.status_code == 200:
                plans = response.json()
                bulk_plan = None
                for plan in plans:
                    if plan.get("name") == "Bulk Test Monthly":
                        bulk_plan = plan
                        break
                
                if bulk_plan:
                    expected_validities = ["monthly", "quarterly", "yearly"]
                    actual_validities = bulk_plan.get("available_validities", [])
                    
                    if set(expected_validities) == set(actual_validities) and bulk_plan.get("validity") == "monthly":
                        self.log_result("Bulk Test Plan Verification", True, 
                                      f"Plan created with correct available_validities: {actual_validities}")
                        return bulk_plan
                    else:
                        self.log_result("Bulk Test Plan Verification", False, 
                                      f"Expected {expected_validities}, got {actual_validities}")
                else:
                    self.log_result("Bulk Test Plan Verification", False, "Bulk Test Monthly plan not found")
            else:
                self.log_result("Bulk Test Plan Verification", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_result("Bulk Test Plan Verification", False, f"Exception: {str(e)}")
        return None
    
    def test_plans_bulk_upload_invalid_validity(self):
        """Test 3: Plans bulk upload with invalid available_validity"""
        
        # Create CSV with invalid validity
        csv_content = '''name,price,validity,available_validities,tax_percentage,tax_type
Bad Plan,500,monthly,"monthly,weekly",0,none'''
        
        try:
            files = {'file': ('test_bad_plans.csv', csv_content, 'text/csv')}
            response = requests.post(f"{BACKEND_URL}/operator/plans/bulk-upload", 
                                   files=files, headers=self.get_headers())
            
            if response.status_code == 200:
                data = response.json()
                job_id = data.get("job_id")
                self.log_result("Invalid Plans Upload Submit", True, f"Job ID: {job_id}")
                
                # Poll job status and check for errors
                if self.wait_for_job_completion(job_id, expect_errors=True):
                    self.log_result("Invalid Plans Upload Job", True, "Job completed with expected errors")
                else:
                    self.log_result("Invalid Plans Upload Job", False, "Job did not handle invalid validity correctly")
            else:
                self.log_result("Invalid Plans Upload Submit", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("Invalid Plans Upload Submit", False, f"Exception: {str(e)}")
    
    def test_subscribers_bulk_upload_with_tenure(self):
        """Test 4: Subscribers bulk upload with tenure"""
        
        # Create CSV content for subscriber with yearly tenure
        csv_content = '''name,whatsapp_number,email,address,plan_name_1,plan_start_date_1,tenure_1,discount_1
Bulk Tenure Sub,9100001111,bulk@test.com,Test Address,Bulk Test Monthly,2026-04-21,yearly,0'''
        
        try:
            files = {'file': ('test_subscribers.csv', csv_content, 'text/csv')}
            response = requests.post(f"{BACKEND_URL}/operator/subscribers/bulk-upload", 
                                   files=files, headers=self.get_headers())
            
            if response.status_code == 200:
                data = response.json()
                job_id = data.get("job_id")
                self.log_result("Subscribers Bulk Upload Submit", True, f"Job ID: {job_id}")
                
                # Poll job status
                if self.wait_for_job_completion(job_id):
                    # Verify the subscriber was created correctly
                    self.verify_bulk_subscriber()
                else:
                    self.log_result("Subscribers Bulk Upload Job", False, "Job did not complete successfully")
            else:
                self.log_result("Subscribers Bulk Upload Submit", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("Subscribers Bulk Upload Submit", False, f"Exception: {str(e)}")
    
    def verify_bulk_subscriber(self):
        """Verify the bulk subscriber was created correctly"""
        try:
            response = requests.get(f"{BACKEND_URL}/operator/subscribers", headers=self.get_headers())
            if response.status_code == 200:
                subscribers = response.json()
                bulk_subscriber = None
                for sub in subscribers:
                    if sub.get("whatsapp_number") == "9100001111":
                        bulk_subscriber = sub
                        break
                
                if bulk_subscriber:
                    plans = bulk_subscriber.get("plans", [])
                    if plans and len(plans) > 0:
                        plan = plans[0]
                        selected_validity = plan.get("selected_validity")
                        plan_expiry = plan.get("plan_expiry_date")
                        
                        # Check if expiry is calculated correctly (Apr 21 + 12 months - 1 day = Apr 20 next year)
                        expected_expiry = "2027-04-20"
                        
                        if selected_validity == "yearly" and plan_expiry == expected_expiry:
                            self.log_result("Bulk Subscriber Verification", True, 
                                          f"Subscriber created with yearly tenure, expiry: {plan_expiry}")
                            return bulk_subscriber
                        else:
                            self.log_result("Bulk Subscriber Verification", False, 
                                          f"Expected yearly tenure with expiry {expected_expiry}, got {selected_validity} with {plan_expiry}")
                    else:
                        self.log_result("Bulk Subscriber Verification", False, "No plans found for subscriber")
                else:
                    self.log_result("Bulk Subscriber Verification", False, "Bulk subscriber not found")
            else:
                self.log_result("Bulk Subscriber Verification", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_result("Bulk Subscriber Verification", False, f"Exception: {str(e)}")
        return None
    
    def test_invoices_bulk_upload_auto_price(self):
        """Test 5: Invoices bulk upload with auto-price calculation"""
        
        # Create CSV content for invoice with auto-calculated price
        csv_content = '''subscriber_whatsapp_number,plan_name,selected_validity,base_amount,discount,service_start_date,service_end_date,due_date
9100001111,Bulk Test Monthly,yearly,,0,2026-04-21,2027-04-20,2026-05-01'''
        
        try:
            files = {'file': ('test_invoices.csv', csv_content, 'text/csv')}
            response = requests.post(f"{BACKEND_URL}/operator/invoices/bulk-upload", 
                                   files=files, headers=self.get_headers())
            
            if response.status_code == 200:
                data = response.json()
                job_id = data.get("job_id")
                self.log_result("Invoices Bulk Upload Submit", True, f"Job ID: {job_id}")
                
                # Poll job status
                if self.wait_for_job_completion(job_id):
                    # Verify the invoice was created with correct auto-calculated price
                    self.verify_bulk_invoice()
                else:
                    self.log_result("Invoices Bulk Upload Job", False, "Job did not complete successfully")
            else:
                self.log_result("Invoices Bulk Upload Submit", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("Invoices Bulk Upload Submit", False, f"Exception: {str(e)}")
    
    def verify_bulk_invoice(self):
        """Verify the bulk invoice was created with correct auto-calculated price"""
        try:
            response = requests.get(f"{BACKEND_URL}/operator/invoices", headers=self.get_headers())
            if response.status_code == 200:
                invoices = response.json()
                # Find the most recent invoice for our test subscriber
                bulk_invoice = None
                for inv in invoices:
                    if inv.get("subscriber_name") == "Bulk Tenure Sub":
                        bulk_invoice = inv
                        break
                
                if bulk_invoice:
                    base_amount = bulk_invoice.get("base_amount")
                    line_items = bulk_invoice.get("line_items", [])
                    
                    # Expected: 600 (monthly) × 12 months / 1 month = 7200
                    expected_amount = 7200.0
                    
                    if abs(base_amount - expected_amount) < 0.01:
                        self.log_result("Bulk Invoice Auto-Price", True, 
                                      f"Invoice created with correct auto-calculated amount: ₹{base_amount}")
                        
                        # Also check line item details
                        if line_items and len(line_items) > 0:
                            item = line_items[0]
                            if item.get("selected_validity") == "yearly":
                                self.log_result("Bulk Invoice Line Item", True, 
                                              f"Line item has correct selected_validity: yearly")
                            else:
                                self.log_result("Bulk Invoice Line Item", False, 
                                              f"Expected yearly validity, got {item.get('selected_validity')}")
                    else:
                        self.log_result("Bulk Invoice Auto-Price", False, 
                                      f"Expected ₹{expected_amount}, got ₹{base_amount}")
                else:
                    self.log_result("Bulk Invoice Auto-Price", False, "Bulk invoice not found")
            else:
                self.log_result("Bulk Invoice Auto-Price", False, f"Status {response.status_code}")
        except Exception as e:
            self.log_result("Bulk Invoice Auto-Price", False, f"Exception: {str(e)}")
    
    def wait_for_job_completion(self, job_id, timeout=60, expect_errors=False):
        """Wait for a background job to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{BACKEND_URL}/operator/jobs/{job_id}", headers=self.get_headers())
                if response.status_code == 200:
                    job_data = response.json()
                    status = job_data.get("status")
                    
                    if status == "completed":
                        result = job_data.get("result", {})
                        errors = result.get("errors", [])
                        
                        if expect_errors and len(errors) > 0:
                            self.log_result(f"Job {job_id} Status", True, 
                                          f"Completed with expected errors: {len(errors)} errors")
                            return True
                        elif not expect_errors and len(errors) == 0:
                            created = result.get("created", 0)
                            self.log_result(f"Job {job_id} Status", True, 
                                          f"Completed successfully: {created} items created")
                            return True
                        else:
                            self.log_result(f"Job {job_id} Status", False, 
                                          f"Unexpected error state: {len(errors)} errors")
                            return False
                    
                    elif status == "failed":
                        error = job_data.get("error", "Unknown error")
                        self.log_result(f"Job {job_id} Status", False, f"Job failed: {error}")
                        return False
                    
                    # Still processing, wait a bit more
                    time.sleep(2)
                else:
                    self.log_result(f"Job {job_id} Status Check", False, f"Status {response.status_code}")
                    return False
                    
            except Exception as e:
                self.log_result(f"Job {job_id} Status Check", False, f"Exception: {str(e)}")
                return False
        
        self.log_result(f"Job {job_id} Status", False, f"Timeout after {timeout} seconds")
        return False
    
    def run_all_tests(self):
        """Run all V9.10 bulk upload tests"""
        print("=" * 60)
        print("V9.10 Bulk Upload Updates Test Suite")
        print("=" * 60)
        
        # Seed data first
        if not self.test_seed_data():
            print("❌ Cannot proceed without seed data")
            return
        
        # Authenticate
        if not self.authenticate_operator():
            print("❌ Cannot proceed without authentication")
            return
        
        # Run all tests
        self.test_sample_csv_downloads()
        self.test_plans_bulk_upload_with_available_validities()
        self.test_plans_bulk_upload_invalid_validity()
        self.test_subscribers_bulk_upload_with_tenure()
        self.test_invoices_bulk_upload_auto_price()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if "✅ PASS" in result)
        failed = sum(1 for result in self.test_results if "❌ FAIL" in result)
        
        for result in self.test_results:
            print(result)
        
        print(f"\nTotal: {len(self.test_results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        return failed == 0

if __name__ == "__main__":
    tester = BulkUploadTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)