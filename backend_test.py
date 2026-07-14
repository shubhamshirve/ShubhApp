#!/usr/bin/env python3
"""
Backend API tests for subscriber ID migration endpoints.

Test Requirements:
1. GET /api/admin/migrate-subscriber-ids/preview - requires admin auth, returns preview
2. POST /api/admin/migrate-subscriber-ids - requires admin auth, performs migration
3. Verify endpoints are protected (admin-only) - 401/403 without auth
4. Backend health check - GET /api/health
5. Static code verification - check imports and endpoint definitions
"""

import requests
import json
import sys

# Backend URL (internal container URL)
BASE_URL = "http://localhost:8001"

# Admin credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def print_result(test_name, passed, details=""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")


def get_admin_token():
    """Login as admin and get access token."""
    print_section("Admin Authentication")
    
    url = f"{BASE_URL}/api/auth/login"
    payload = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Login request: POST {url}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print_result("Admin login", True, f"Token obtained (length: {len(token)})")
                return token
            else:
                print_result("Admin login", False, "No access_token in response")
                print(f"Response: {json.dumps(data, indent=2)}")
                return None
        else:
            print_result("Admin login", False, f"Status {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print_result("Admin login", False, f"Exception: {e}")
        return None


def test_health_endpoint():
    """Test 4: Backend health check."""
    print_section("Test 4: Backend Health Check")
    
    url = f"{BASE_URL}/api/health"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Request: GET {url}")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        
        passed = response.status_code == 200
        print_result("Health endpoint", passed, 
                    f"Expected 200, got {response.status_code}")
        return passed
    except Exception as e:
        print_result("Health endpoint", False, f"Exception: {e}")
        return False


def test_preview_endpoint_with_auth(token):
    """Test 1: GET /api/admin/migrate-subscriber-ids/preview with admin auth."""
    print_section("Test 1: Preview Endpoint (With Auth)")
    
    url = f"{BASE_URL}/api/admin/migrate-subscriber-ids/preview"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Request: GET {url}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response body:")
            print(json.dumps(data, indent=2))
            
            # Verify response structure
            required_fields = ["total_subscribers", "need_migration", "already_eb_format", "preview"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                print_result("Preview endpoint structure", False, 
                           f"Missing fields: {missing_fields}")
                return False
            
            print_result("Preview endpoint", True, 
                        f"total_subscribers={data['total_subscribers']}, "
                        f"need_migration={data['need_migration']}, "
                        f"already_eb_format={data['already_eb_format']}")
            return True
        else:
            print(f"Response: {response.text}")
            print_result("Preview endpoint", False, 
                        f"Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print_result("Preview endpoint", False, f"Exception: {e}")
        return False


def test_migration_endpoint_with_auth(token):
    """Test 2: POST /api/admin/migrate-subscriber-ids with admin auth."""
    print_section("Test 2: Migration Endpoint (With Auth)")
    
    url = f"{BASE_URL}/api/admin/migrate-subscriber-ids"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        print(f"Request: POST {url}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response body:")
            print(json.dumps(data, indent=2))
            
            # Verify response structure
            required_fields = ["status", "migrated", "errors"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                print_result("Migration endpoint structure", False, 
                           f"Missing fields: {missing_fields}")
                return False
            
            # Check if it's a no-op (DB empty or already migrated)
            if data.get("status") == "no_op":
                print_result("Migration endpoint", True, 
                           f"No-op response (DB empty or already migrated): {data.get('message', '')}")
            else:
                print_result("Migration endpoint", True, 
                           f"status={data['status']}, migrated={data['migrated']}, "
                           f"errors={len(data['errors'])}")
            return True
        else:
            print(f"Response: {response.text}")
            print_result("Migration endpoint", False, 
                        f"Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print_result("Migration endpoint", False, f"Exception: {e}")
        return False


def test_preview_endpoint_without_auth():
    """Test 3: GET /api/admin/migrate-subscriber-ids/preview without auth (should fail)."""
    print_section("Test 3: Preview Endpoint (Without Auth - Should Fail)")
    
    url = f"{BASE_URL}/api/admin/migrate-subscriber-ids/preview"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Request: GET {url} (no Authorization header)")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Should return 401 or 403
        passed = response.status_code in [401, 403]
        print_result("Endpoint protection", passed, 
                    f"Expected 401 or 403, got {response.status_code}")
        return passed
    except Exception as e:
        print_result("Endpoint protection", False, f"Exception: {e}")
        return False


def test_static_code_verification():
    """Test 5: Static code verification."""
    print_section("Test 5: Static Code Verification")
    
    all_passed = True
    
    # Check 1: generate_subscriber_id import at line 22
    try:
        with open("/app/backend/routers/admin.py", "r") as f:
            lines = f.readlines()
            line_22 = lines[21] if len(lines) > 21 else ""  # 0-indexed
            
            if "generate_subscriber_id" in line_22:
                print_result("Import check (line 22)", True, 
                           f"generate_subscriber_id found in: {line_22.strip()}")
            else:
                print_result("Import check (line 22)", False, 
                           f"generate_subscriber_id NOT found at line 22. Line content: {line_22.strip()}")
                all_passed = False
    except Exception as e:
        print_result("Import check", False, f"Exception: {e}")
        all_passed = False
    
    # Check 2: _UUID_PATTERN regex defined
    try:
        with open("/app/backend/routers/admin.py", "r") as f:
            content = f.read()
            
            if "_UUID_PATTERN" in content and "re.compile" in content:
                print_result("_UUID_PATTERN regex", True, "_UUID_PATTERN regex is defined")
            else:
                print_result("_UUID_PATTERN regex", False, "_UUID_PATTERN not found")
                all_passed = False
    except Exception as e:
        print_result("_UUID_PATTERN check", False, f"Exception: {e}")
        all_passed = False
    
    # Check 3: Both endpoints exist (checking for correct path without duplicate /admin)
    try:
        with open("/app/backend/routers/admin.py", "r") as f:
            content = f.read()
            
            # The router has prefix="/admin", so endpoints should be defined without /admin prefix
            preview_exists = '@router.get("/migrate-subscriber-ids/preview")' in content
            migration_exists = '@router.post("/migrate-subscriber-ids")' in content
            
            if preview_exists:
                print_result("Preview endpoint definition", True, 
                           "GET /migrate-subscriber-ids/preview found (correct - no duplicate /admin)")
            else:
                print_result("Preview endpoint definition", False, 
                           "GET /migrate-subscriber-ids/preview NOT found")
                all_passed = False
            
            if migration_exists:
                print_result("Migration endpoint definition", True, 
                           "POST /migrate-subscriber-ids found (correct - no duplicate /admin)")
            else:
                print_result("Migration endpoint definition", False, 
                           "POST /migrate-subscriber-ids NOT found")
                all_passed = False
    except Exception as e:
        print_result("Endpoint definition check", False, f"Exception: {e}")
        all_passed = False
    
    # Check 4: Both use Depends(require_admin)
    try:
        with open("/app/backend/routers/admin.py", "r") as f:
            lines = f.readlines()
            
            # Find the preview endpoint (updated path without duplicate /admin)
            preview_has_auth = False
            migration_has_auth = False
            
            for i, line in enumerate(lines):
                if '@router.get("/migrate-subscriber-ids/preview")' in line:
                    # Check next few lines for require_admin
                    for j in range(i, min(i+5, len(lines))):
                        if "require_admin" in lines[j]:
                            preview_has_auth = True
                            break
                
                if '@router.post("/migrate-subscriber-ids")' in line:
                    # Check next few lines for require_admin
                    for j in range(i, min(i+5, len(lines))):
                        if "require_admin" in lines[j]:
                            migration_has_auth = True
                            break
            
            if preview_has_auth:
                print_result("Preview endpoint auth", True, 
                           "Uses Depends(require_admin)")
            else:
                print_result("Preview endpoint auth", False, 
                           "Does NOT use Depends(require_admin)")
                all_passed = False
            
            if migration_has_auth:
                print_result("Migration endpoint auth", True, 
                           "Uses Depends(require_admin)")
            else:
                print_result("Migration endpoint auth", False, 
                           "Does NOT use Depends(require_admin)")
                all_passed = False
    except Exception as e:
        print_result("Auth dependency check", False, f"Exception: {e}")
        all_passed = False
    
    # Check 5: migrate_subscriber_ids.py script exists
    try:
        import os
        script_path = "/app/backend/scripts/migrate_subscriber_ids.py"
        
        if os.path.exists(script_path):
            with open(script_path, "r") as f:
                content = f.read()
                
                if "run_migration" in content:
                    print_result("Migration script", True, 
                               f"{script_path} exists with run_migration function")
                else:
                    print_result("Migration script", False, 
                               "run_migration function NOT found in script")
                    all_passed = False
        else:
            print_result("Migration script", False, 
                       f"{script_path} does NOT exist")
            all_passed = False
    except Exception as e:
        print_result("Migration script check", False, f"Exception: {e}")
        all_passed = False
    
    return all_passed


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  SUBSCRIBER ID MIGRATION ENDPOINTS - BACKEND TEST SUITE")
    print("="*70)
    print(f"Backend URL: {BASE_URL}")
    print(f"Admin credentials: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    
    results = {}
    
    # Test 4: Health check (no auth required)
    results["health"] = test_health_endpoint()
    
    # Test 5: Static code verification
    results["static_code"] = test_static_code_verification()
    
    # Get admin token
    admin_token = get_admin_token()
    
    if not admin_token:
        print("\n❌ CRITICAL: Cannot proceed with API tests - admin login failed")
        print_section("FINAL SUMMARY")
        print("❌ Tests incomplete - admin authentication failed")
        sys.exit(1)
    
    # Test 3: Endpoint protection (without auth)
    results["protection"] = test_preview_endpoint_without_auth()
    
    # Test 1: Preview endpoint (with auth)
    results["preview"] = test_preview_endpoint_with_auth(admin_token)
    
    # Test 2: Migration endpoint (with auth)
    results["migration"] = test_migration_endpoint_with_auth(admin_token)
    
    # Final summary
    print_section("FINAL SUMMARY")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    print(f"\nTotal tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    print("\nDetailed results:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    if passed_tests == total_tests:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print(f"\n❌ {total_tests - passed_tests} TEST(S) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
