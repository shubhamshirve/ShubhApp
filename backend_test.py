"""
Backend API Testing for Backup and Restore Endpoints
Tests the specific requirements from the review request.
"""
import requests
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8001"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"
BACKUP_PASSWORD = "ebill_default_bk_pw_2024"  # Actual backup password from env_service.py

# Expected collections in backup (25 total, excluding "backups" and without "whatsapp_configs")
EXPECTED_COLLECTIONS = [
    "users",
    "operators",
    "operator_wallets",
    "wallet_transactions",
    "saas_plans",
    "operator_plans",
    "addons",
    "subscribers",
    "invoices",
    "invoice_settings",
    "operator_theme",
    "payment_gateways",
    "saas_payments",
    "checkout_orders",
    "discount_codes",
    "global_settings",
    "whatsapp_templates",
    "whatsapp_message_logs",
    "announcements",
    "notification_queue",
    "audit_logs",
    "error_logs",
    "webhook_events",
    "support_tickets",
    "support_replies",
]

class BackupRestoreTest:
    def __init__(self):
        self.token = None
        self.backup_id = None
        self.test_results = []
        
    def log_result(self, test_name: str, passed: bool, message: str, details: Any = None):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        print(f"\n{status}: {test_name}")
        print(f"   {message}")
        if details and not passed:
            print(f"   Details: {json.dumps(details, indent=2)}")
    
    def login(self) -> bool:
        """Authenticate and get JWT token"""
        print("\n" + "="*80)
        print("TEST 0: Admin Login")
        print("="*80)
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token") or data.get("token")
                if self.token:
                    self.log_result("Admin Login", True, f"Successfully logged in as {ADMIN_EMAIL}")
                    return True
                else:
                    self.log_result("Admin Login", False, "No token in response", data)
                    return False
            else:
                self.log_result("Admin Login", False, f"Login failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_result("Admin Login", False, f"Exception during login: {str(e)}")
            return False
    
    def test_create_backup(self) -> bool:
        """Test POST /api/admin/backup/create"""
        print("\n" + "="*80)
        print("TEST 1: POST /api/admin/backup/create")
        print("="*80)
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{BASE_URL}/api/admin/backup/create",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                self.log_result(
                    "Create Backup - Status Code",
                    False,
                    f"Expected 200, got {response.status_code}",
                    response.text
                )
                return False
            
            data = response.json()
            backup = data.get("backup", {})
            
            # Store backup_id for later tests
            self.backup_id = backup.get("id")
            
            # Test 1.1: Check if collections key exists
            collections = backup.get("collections", [])
            if not collections:
                self.log_result(
                    "Create Backup - Collections Key",
                    False,
                    "No 'collections' key in backup response",
                    backup
                )
                return False
            
            self.log_result(
                "Create Backup - Collections Key",
                True,
                f"Found {len(collections)} collections in backup"
            )
            
            # Test 1.2: Check if collection_counts key exists
            collection_counts = backup.get("collection_counts", {})
            if not collection_counts:
                self.log_result(
                    "Create Backup - Collection Counts Key",
                    False,
                    "No 'collection_counts' key in backup response",
                    backup
                )
                return False
            
            self.log_result(
                "Create Backup - Collection Counts Key",
                True,
                f"Found collection_counts with {len(collection_counts)} entries"
            )
            
            # Test 1.3: Verify all 25 expected collections are present
            missing_collections = [col for col in EXPECTED_COLLECTIONS if col not in collections]
            extra_collections = [col for col in collections if col not in EXPECTED_COLLECTIONS]
            
            if missing_collections:
                self.log_result(
                    "Create Backup - Expected Collections",
                    False,
                    f"Missing {len(missing_collections)} expected collections",
                    {"missing": missing_collections, "found": collections}
                )
            elif extra_collections:
                self.log_result(
                    "Create Backup - Expected Collections",
                    False,
                    f"Found {len(extra_collections)} unexpected collections",
                    {"unexpected": extra_collections, "found": collections}
                )
            else:
                self.log_result(
                    "Create Backup - Expected Collections",
                    True,
                    f"All 25 expected collections present: {', '.join(collections)}"
                )
            
            # Test 1.4: Verify "backups" collection is NOT in the list
            if "backups" in collections:
                self.log_result(
                    "Create Backup - Backups Exclusion",
                    False,
                    "'backups' collection should be excluded from backup",
                    collections
                )
            else:
                self.log_result(
                    "Create Backup - Backups Exclusion",
                    True,
                    "'backups' collection correctly excluded from backup"
                )
            
            # Test 1.5: Verify "whatsapp_configs" is NOT in the list (legacy collection)
            if "whatsapp_configs" in collections:
                self.log_result(
                    "Create Backup - WhatsApp Configs Exclusion",
                    False,
                    "'whatsapp_configs' (legacy) should not be in backup",
                    collections
                )
            else:
                self.log_result(
                    "Create Backup - WhatsApp Configs Exclusion",
                    True,
                    "'whatsapp_configs' correctly not in backup (legacy collection removed)"
                )
            
            # Test 1.6: Verify collection_counts has counts for each collection
            counts_match = all(col in collection_counts for col in collections)
            if not counts_match:
                missing_counts = [col for col in collections if col not in collection_counts]
                self.log_result(
                    "Create Backup - Collection Counts Match",
                    False,
                    f"collection_counts missing entries for: {missing_counts}",
                    collection_counts
                )
            else:
                total_records = sum(collection_counts.values())
                self.log_result(
                    "Create Backup - Collection Counts Match",
                    True,
                    f"All collections have counts. Total records: {total_records}"
                )
            
            print(f"\n📊 Backup Summary:")
            print(f"   Backup ID: {self.backup_id}")
            print(f"   Collections: {len(collections)}")
            print(f"   Total Records: {backup.get('total_records', 0)}")
            print(f"   Size: {backup.get('size_kb', 0)} KB")
            
            return True
            
        except Exception as e:
            self.log_result(
                "Create Backup - Exception",
                False,
                f"Exception during backup creation: {str(e)}"
            )
            return False
    
    def test_list_backups(self) -> bool:
        """Test GET /api/admin/backup/list"""
        print("\n" + "="*80)
        print("TEST 2: GET /api/admin/backup/list")
        print("="*80)
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(
                f"{BASE_URL}/api/admin/backup/list",
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                self.log_result(
                    "List Backups - Status Code",
                    False,
                    f"Expected 200, got {response.status_code}",
                    response.text
                )
                return False
            
            data = response.json()
            backups = data.get("backups", [])
            
            if not backups:
                self.log_result(
                    "List Backups - Backups Found",
                    False,
                    "No backups found in list",
                    data
                )
                return False
            
            self.log_result(
                "List Backups - Backups Found",
                True,
                f"Found {len(backups)} backup(s)"
            )
            
            # Test 2.1: Find the backup we just created
            our_backup = None
            for backup in backups:
                if backup.get("id") == self.backup_id:
                    our_backup = backup
                    break
            
            if not our_backup:
                self.log_result(
                    "List Backups - Find Created Backup",
                    False,
                    f"Could not find backup with ID {self.backup_id}",
                    {"backups": [b.get("id") for b in backups]}
                )
                return False
            
            self.log_result(
                "List Backups - Find Created Backup",
                True,
                f"Found backup {self.backup_id} in list"
            )
            
            # Test 2.2: Verify collection_counts exists in the listed backup
            collection_counts = our_backup.get("collection_counts")
            if not collection_counts:
                self.log_result(
                    "List Backups - Collection Counts",
                    False,
                    "collection_counts not present in listed backup",
                    our_backup
                )
                return False
            
            self.log_result(
                "List Backups - Collection Counts",
                True,
                f"collection_counts present with {len(collection_counts)} collections"
            )
            
            print(f"\n📋 Listed Backup Details:")
            print(f"   ID: {our_backup.get('id')}")
            print(f"   Filename: {our_backup.get('filename')}")
            print(f"   Type: {our_backup.get('type')}")
            print(f"   Collections: {len(our_backup.get('collections', []))}")
            print(f"   Total Records: {our_backup.get('total_records', 0)}")
            
            return True
            
        except Exception as e:
            self.log_result(
                "List Backups - Exception",
                False,
                f"Exception during backup list: {str(e)}"
            )
            return False
    
    def test_restore_backup(self) -> bool:
        """Test POST /api/admin/backup/restore/{backup_id}"""
        print("\n" + "="*80)
        print("TEST 3: POST /api/admin/backup/restore/{backup_id}")
        print("="*80)
        
        if not self.backup_id:
            self.log_result(
                "Restore Backup - Backup ID",
                False,
                "No backup_id available for restore test"
            )
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{BASE_URL}/api/admin/backup/restore/{self.backup_id}",
                headers=headers,
                json={"password": BACKUP_PASSWORD},
                timeout=30
            )
            
            if response.status_code != 200:
                self.log_result(
                    "Restore Backup - Status Code",
                    False,
                    f"Expected 200, got {response.status_code}",
                    response.text
                )
                return False
            
            data = response.json()
            
            # Test 3.1: Verify collections_restored key exists
            collections_restored = data.get("collections_restored")
            if collections_restored is None:
                self.log_result(
                    "Restore Backup - Collections Restored Key",
                    False,
                    "No 'collections_restored' key in response",
                    data
                )
                return False
            
            self.log_result(
                "Restore Backup - Collections Restored Key",
                True,
                f"Found {len(collections_restored)} collections restored"
            )
            
            # Test 3.2: Verify collections_skipped key exists
            collections_skipped = data.get("collections_skipped")
            if collections_skipped is None:
                self.log_result(
                    "Restore Backup - Collections Skipped Key",
                    False,
                    "No 'collections_skipped' key in response",
                    data
                )
                return False
            
            self.log_result(
                "Restore Backup - Collections Skipped Key",
                True,
                f"Found {len(collections_skipped)} collections skipped: {collections_skipped}"
            )
            
            # Test 3.3: Verify records_restored key exists
            records_restored = data.get("records_restored")
            if records_restored is None:
                self.log_result(
                    "Restore Backup - Records Restored Key",
                    False,
                    "No 'records_restored' key in response",
                    data
                )
                return False
            
            self.log_result(
                "Restore Backup - Records Restored Key",
                True,
                f"Restored {records_restored} records"
            )
            
            # Test 3.4: Verify "note" field exists about re-login
            note = data.get("note")
            if not note:
                self.log_result(
                    "Restore Backup - Note Field",
                    False,
                    "No 'note' field in response about re-login",
                    data
                )
                return False
            
            if "log in again" not in note.lower():
                self.log_result(
                    "Restore Backup - Note Content",
                    False,
                    "Note field doesn't mention re-login requirement",
                    {"note": note}
                )
            else:
                self.log_result(
                    "Restore Backup - Note Field",
                    True,
                    f"Note field present: '{note}'"
                )
            
            print(f"\n🔄 Restore Summary:")
            print(f"   Collections Restored: {len(collections_restored)}")
            print(f"   Collections Skipped: {len(collections_skipped)}")
            print(f"   Records Restored: {records_restored}")
            print(f"   Note: {note}")
            
            return True
            
        except Exception as e:
            self.log_result(
                "Restore Backup - Exception",
                False,
                f"Exception during backup restore: {str(e)}"
            )
            return False
    
    def print_summary(self):
        """Print final test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for r in self.test_results if "✅ PASS" in r["status"])
        failed = sum(1 for r in self.test_results if "❌ FAIL" in r["status"])
        total = len(self.test_results)
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%\n")
        
        if failed > 0:
            print("Failed Tests:")
            for result in self.test_results:
                if "❌ FAIL" in result["status"]:
                    print(f"  • {result['test']}: {result['message']}")
        
        print("\n" + "="*80)
        
        return failed == 0

def main():
    """Run all backup and restore tests"""
    print("\n" + "="*80)
    print("BACKUP AND RESTORE API TESTING")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print(f"Expected Collections: {len(EXPECTED_COLLECTIONS)}")
    
    tester = BackupRestoreTest()
    
    # Run tests in sequence
    if not tester.login():
        print("\n❌ Login failed. Cannot proceed with tests.")
        return False
    
    tester.test_create_backup()
    tester.test_list_backups()
    tester.test_restore_backup()
    
    # Print summary
    success = tester.print_summary()
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
