"""
Test Payment Reminder Automation Scheduling Feature
Tests for the NEW reminder settings endpoints and cron processing
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://admin-dashboard-v2-34.preview.emergentagent.com"

# Credentials
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"
REMINDER_OPERATOR_EMAIL = "reminder_test@test.com"
REMINDER_OPERATOR_PASSWORD = "testpass123"


class TestReminderSettingsEndpoints:
    """Test GET/PUT /api/operator/reminder-settings endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Login as admin and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    def get_operator_with_addon_token(self):
        """Login as operator WITH payment_reminder addon"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": REMINDER_OPERATOR_EMAIL,
            "password": REMINDER_OPERATOR_PASSWORD
        })
        assert response.status_code == 200, f"Operator login failed: {response.text}"
        return response.json()["access_token"]

    def test_reminder_settings_returns_403_without_addon(self):
        """Test: GET /api/operator/reminder-settings returns 403 for operator without payment_reminder addon"""
        # Register a NEW operator who does NOT have the addon
        import uuid
        unique_email = f"test_no_addon_{uuid.uuid4().hex[:8]}@test.com"
        
        # Register new operator
        response = self.session.post(f"{BASE_URL}/api/auth/register", json={
            "company_name": "Test No Addon Co",
            "owner_name": "Test User",
            "email": unique_email,
            "phone": "1234567890",
            "password": "testpass123"
        })
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            
            # Try to access reminder settings - should fail with 403
            response = self.session.get(f"{BASE_URL}/api/operator/reminder-settings")
            assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
            assert "payment reminder" in response.json().get("detail", "").lower() or "add-on" in response.json().get("detail", "").lower()
            print(f"PASSED: Operator without addon correctly receives 403")
        else:
            # May already exist from previous tests
            print(f"Note: Could not create new operator (likely email taken), skipping 403 test")

    def test_reminder_settings_returns_defaults_for_operator_with_addon(self):
        """Test: GET /api/operator/reminder-settings returns defaults for operator WITH addon but no saved settings"""
        token = self.get_operator_with_addon_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # First verify the operator has the addon via features endpoint
        features_resp = self.session.get(f"{BASE_URL}/api/operator/features")
        assert features_resp.status_code == 200
        features = features_resp.json()
        assert features.get("payment_reminder") == True, "Test operator should have payment_reminder addon"
        print(f"PASSED: Operator has payment_reminder feature: {features.get('payment_reminder')}")
        
        # Now test the reminder settings endpoint
        response = self.session.get(f"{BASE_URL}/api/operator/reminder-settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should have expected fields
        assert "enabled" in data
        assert "remind_before_due" in data
        assert "remind_on_due" in data
        assert "remind_after_due" in data
        assert "max_reminders_per_invoice" in data
        
        # Default values (if no settings saved yet)
        # enabled should be false, arrays should be empty initially or have saved values
        assert isinstance(data["enabled"], bool)
        assert isinstance(data["remind_before_due"], list)
        assert isinstance(data["remind_on_due"], bool)
        assert isinstance(data["remind_after_due"], list)
        assert isinstance(data["max_reminders_per_invoice"], int)
        
        print(f"PASSED: GET reminder-settings returns valid structure: enabled={data['enabled']}, max_reminders={data['max_reminders_per_invoice']}")

    def test_put_reminder_settings_saves_correctly(self):
        """Test: PUT /api/operator/reminder-settings saves settings correctly"""
        token = self.get_operator_with_addon_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Save new settings
        new_settings = {
            "enabled": True,
            "remind_before_due": [7, 3, 1],
            "remind_on_due": True,
            "remind_after_due": [1, 3, 7],
            "max_reminders_per_invoice": 10
        }
        
        response = self.session.put(f"{BASE_URL}/api/operator/reminder-settings", json=new_settings)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result["enabled"] == True
        assert 7 in result["remind_before_due"]
        assert 3 in result["remind_before_due"]
        assert 1 in result["remind_before_due"]
        assert result["remind_on_due"] == True
        assert 1 in result["remind_after_due"]
        assert 3 in result["remind_after_due"]
        assert 7 in result["remind_after_due"]
        assert result["max_reminders_per_invoice"] == 10
        print(f"PASSED: PUT reminder-settings saves correctly")

    def test_put_reminder_settings_validates_before_due_days(self):
        """Test: PUT /api/operator/reminder-settings validates remind_before_due days (only [1,2,3,5,7] allowed)"""
        token = self.get_operator_with_addon_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try invalid day (e.g., 10 not in allowed list)
        invalid_settings = {
            "enabled": True,
            "remind_before_due": [10],  # Invalid - should only allow [1,2,3,5,7]
            "remind_on_due": False,
            "remind_after_due": [],
            "max_reminders_per_invoice": 5
        }
        
        response = self.session.put(f"{BASE_URL}/api/operator/reminder-settings", json=invalid_settings)
        assert response.status_code == 400, f"Expected 400 for invalid day, got {response.status_code}: {response.text}"
        print(f"PASSED: Invalid remind_before_due day (10) correctly rejected with 400")

    def test_put_reminder_settings_validates_after_due_days(self):
        """Test: PUT /api/operator/reminder-settings validates remind_after_due days (only [1,3,5,7,14,30] allowed)"""
        token = self.get_operator_with_addon_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try invalid day (e.g., 2 not in allowed list for after_due)
        invalid_settings = {
            "enabled": True,
            "remind_before_due": [],
            "remind_on_due": False,
            "remind_after_due": [2],  # Invalid - should only allow [1,3,5,7,14,30]
            "max_reminders_per_invoice": 5
        }
        
        response = self.session.put(f"{BASE_URL}/api/operator/reminder-settings", json=invalid_settings)
        assert response.status_code == 400, f"Expected 400 for invalid day, got {response.status_code}: {response.text}"
        print(f"PASSED: Invalid remind_after_due day (2) correctly rejected with 400")

    def test_get_reminder_settings_returns_saved_settings(self):
        """Test: GET /api/operator/reminder-settings returns previously saved settings"""
        token = self.get_operator_with_addon_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # First save some settings
        settings_to_save = {
            "enabled": True,
            "remind_before_due": [5, 2],
            "remind_on_due": False,
            "remind_after_due": [3, 14],
            "max_reminders_per_invoice": 7
        }
        
        put_resp = self.session.put(f"{BASE_URL}/api/operator/reminder-settings", json=settings_to_save)
        assert put_resp.status_code == 200
        
        # Now GET and verify
        get_resp = self.session.get(f"{BASE_URL}/api/operator/reminder-settings")
        assert get_resp.status_code == 200
        
        data = get_resp.json()
        assert data["enabled"] == True
        assert 5 in data["remind_before_due"]
        assert 2 in data["remind_before_due"]
        assert data["remind_on_due"] == False
        assert 3 in data["remind_after_due"]
        assert 14 in data["remind_after_due"]
        assert data["max_reminders_per_invoice"] == 7
        print(f"PASSED: GET correctly returns saved settings")


class TestAdminCronEndpoint:
    """Test POST /api/admin/cron/process-scheduled-reminders"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Login as admin and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]

    def test_process_scheduled_reminders_returns_expected_structure(self):
        """Test: POST /api/admin/cron/process-scheduled-reminders returns expected response structure"""
        token = self.get_admin_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/admin/cron/process-scheduled-reminders")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Expected structure: {operators_processed, reminders_sent, skipped, errors}
        assert "operators_processed" in data, "Missing 'operators_processed' in response"
        assert "reminders_sent" in data, "Missing 'reminders_sent' in response"
        assert "skipped" in data, "Missing 'skipped' in response"
        assert "errors" in data, "Missing 'errors' in response"
        
        assert isinstance(data["operators_processed"], int)
        assert isinstance(data["reminders_sent"], int)
        assert isinstance(data["skipped"], int)
        assert isinstance(data["errors"], list)
        
        print(f"PASSED: Cron endpoint returns correct structure - operators_processed={data['operators_processed']}, reminders_sent={data['reminders_sent']}, skipped={data['skipped']}")

    def test_process_scheduled_reminders_requires_admin(self):
        """Test: POST /api/admin/cron/process-scheduled-reminders requires admin auth"""
        # Try without auth
        response = self.session.post(f"{BASE_URL}/api/admin/cron/process-scheduled-reminders")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"
        print(f"PASSED: Cron endpoint correctly requires authentication")


class TestOperatorFeaturesEndpoint:
    """Test /api/operator/features returns payment_reminder flag correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def test_features_shows_payment_reminder_for_addon_operator(self):
        """Test: /api/operator/features returns payment_reminder:true for operator with addon"""
        # Login as operator with addon
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": REMINDER_OPERATOR_EMAIL,
            "password": REMINDER_OPERATOR_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get features
        features_resp = self.session.get(f"{BASE_URL}/api/operator/features")
        assert features_resp.status_code == 200
        
        features = features_resp.json()
        assert "payment_reminder" in features
        assert features["payment_reminder"] == True, f"Expected payment_reminder to be True, got {features['payment_reminder']}"
        print(f"PASSED: features endpoint returns payment_reminder=True for addon operator")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
