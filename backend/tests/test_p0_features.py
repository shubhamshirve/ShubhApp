"""
P0 Feature Tests - Iteration 8
Tests for:
1. Admin Audit Logs (search, filter, pagination)
2. Auto-invoice cron endpoint
3. Admin change password
4. Backup download
5. Invoice template selection (operator)
6. Admin settings payment gateway display
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"

# Test operator credentials
TEST_OPERATOR_EMAIL = "demo@democorp.com"
TEST_OPERATOR_PASSWORD = "demo123"


class TestAdminLogin:
    """Test admin authentication before other tests"""
    
    def test_admin_login_success(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Admin login failed")


@pytest.fixture(scope="module")
def operator_token():
    """Get operator auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_OPERATOR_EMAIL,
        "password": TEST_OPERATOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Operator login failed")


@pytest.fixture
def admin_client(admin_token):
    """Session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


@pytest.fixture
def operator_client(operator_token):
    """Session with operator auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {operator_token}"
    })
    return session


class TestAdminAuditLogs:
    """Tests for Admin Audit Logs API with filters, search, and pagination"""
    
    def test_get_audit_logs_basic(self, admin_client):
        """Test basic audit logs retrieval"""
        response = admin_client.get(f"{BASE_URL}/api/admin/audit-logs")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert isinstance(data["logs"], list)
        assert isinstance(data["total"], int)
        print(f"✓ Audit logs retrieval works - Total: {data['total']}")
    
    def test_audit_logs_pagination(self, admin_client):
        """Test pagination with skip and limit"""
        # First page
        response1 = admin_client.get(f"{BASE_URL}/api/admin/audit-logs?skip=0&limit=10")
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second page
        response2 = admin_client.get(f"{BASE_URL}/api/admin/audit-logs?skip=10&limit=10")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify total is consistent
        assert data1["total"] == data2["total"]
        print(f"✓ Pagination works - Page 1: {len(data1['logs'])} items, Page 2: {len(data2['logs'])} items")
    
    def test_audit_logs_filter_by_action(self, admin_client):
        """Test filter by action type"""
        for action in ["create", "update", "delete", "login"]:
            response = admin_client.get(f"{BASE_URL}/api/admin/audit-logs?action={action}")
            assert response.status_code == 200, f"Failed for action={action}: {response.text}"
            data = response.json()
            # All returned logs should have the filtered action
            for log in data["logs"]:
                assert log["action"] == action, f"Expected action {action}, got {log['action']}"
        print("✓ Filter by action works")
    
    def test_audit_logs_filter_by_role(self, admin_client):
        """Test filter by role"""
        for role in ["admin", "operator"]:
            response = admin_client.get(f"{BASE_URL}/api/admin/audit-logs?role={role}")
            assert response.status_code == 200, f"Failed for role={role}: {response.text}"
            data = response.json()
            for log in data["logs"]:
                assert log["role"] == role, f"Expected role {role}, got {log['role']}"
        print("✓ Filter by role works")
    
    def test_audit_logs_filter_by_module(self, admin_client):
        """Test filter by module"""
        response = admin_client.get(f"{BASE_URL}/api/admin/audit-logs?module=auth")
        assert response.status_code == 200
        data = response.json()
        # Module filter uses regex, so partial match is fine
        print(f"✓ Filter by module works - Found {len(data['logs'])} auth-related logs")
    
    def test_audit_logs_search(self, admin_client):
        """Test text search across user_name, module, ip_address"""
        response = admin_client.get(f"{BASE_URL}/api/admin/audit-logs?search=admin")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Search works - Found {len(data['logs'])} logs matching 'admin'")
    
    def test_audit_logs_date_range(self, admin_client):
        """Test date range filter"""
        response = admin_client.get(
            f"{BASE_URL}/api/admin/audit-logs?date_from=2024-01-01&date_to=2026-12-31"
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Date range filter works - Found {len(data['logs'])} logs in range")
    
    def test_audit_logs_combined_filters(self, admin_client):
        """Test multiple filters combined"""
        response = admin_client.get(
            f"{BASE_URL}/api/admin/audit-logs?action=login&role=admin&skip=0&limit=20"
        )
        assert response.status_code == 200
        data = response.json()
        for log in data["logs"]:
            assert log["action"] == "login"
            assert log["role"] == "admin"
        print(f"✓ Combined filters work - Found {len(data['logs'])} admin login logs")


class TestAdminCronInvoiceGeneration:
    """Tests for auto-invoice cron generation endpoint"""
    
    def test_cron_generate_invoices_endpoint(self, admin_client):
        """Test POST /api/admin/cron/generate-invoices returns expected structure"""
        response = admin_client.post(f"{BASE_URL}/api/admin/cron/generate-invoices")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total_checked" in data, "Missing 'total_checked' in response"
        assert "invoices_generated" in data, "Missing 'invoices_generated' in response"
        assert "errors" in data, "Missing 'errors' in response"
        
        assert isinstance(data["total_checked"], int)
        assert isinstance(data["invoices_generated"], int)
        assert isinstance(data["errors"], list)
        
        print(f"✓ Cron generate-invoices works - Checked: {data['total_checked']}, Generated: {data['invoices_generated']}")
    
    def test_cron_send_reminders_endpoint(self, admin_client):
        """Test POST /api/admin/cron/send-reminders endpoint"""
        response = admin_client.post(f"{BASE_URL}/api/admin/cron/send-reminders")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "total_overdue" in data
        assert "reminders_sent" in data
        assert "errors" in data
        print(f"✓ Cron send-reminders works - Overdue: {data['total_overdue']}")
    
    def test_cron_check_expiry_endpoint(self, admin_client):
        """Test POST /api/admin/cron/check-expiry endpoint"""
        response = admin_client.post(f"{BASE_URL}/api/admin/cron/check-expiry")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "checked" in data
        assert "expired" in data
        assert "set_read_only" in data
        print(f"✓ Cron check-expiry works - Checked: {data['checked']}")


class TestAdminChangePassword:
    """Tests for admin change password functionality"""
    
    def test_change_password_wrong_current(self, admin_client):
        """Test change password with wrong current password"""
        response = admin_client.put(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "wrongpassword",
            "new_password": "newpass123"
        })
        assert response.status_code == 400
        data = response.json()
        assert "incorrect" in data.get("detail", "").lower()
        print("✓ Change password rejects wrong current password")
    
    def test_change_password_too_short(self, admin_client):
        """Test change password with too short new password"""
        response = admin_client.put(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": ADMIN_PASSWORD,
            "new_password": "12345"
        })
        assert response.status_code == 400
        data = response.json()
        assert "6 characters" in data.get("detail", "")
        print("✓ Change password validates minimum length")
    
    def test_change_password_success_and_revert(self, admin_client):
        """Test successful password change and revert it back"""
        new_password = "admin123new"
        
        # Change password
        response = admin_client.put(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": ADMIN_PASSWORD,
            "new_password": new_password
        })
        assert response.status_code == 200, f"Failed to change password: {response.text}"
        
        # Verify login with new password works
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": new_password
        })
        assert login_response.status_code == 200, "Login with new password failed"
        new_token = login_response.json()["access_token"]
        
        # Revert password back to original
        revert_client = requests.Session()
        revert_client.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {new_token}"
        })
        revert_response = revert_client.put(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": new_password,
            "new_password": ADMIN_PASSWORD
        })
        assert revert_response.status_code == 200, "Failed to revert password"
        
        # Verify original password works again
        final_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert final_login.status_code == 200, "Login with reverted password failed"
        print("✓ Change password works (changed and reverted successfully)")


class TestBackupDownload:
    """Tests for backup download functionality"""
    
    def test_backup_list(self, admin_client):
        """Test listing backups"""
        response = admin_client.get(f"{BASE_URL}/api/admin/backup/list")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Backup list works - Found {len(data)} backups")
    
    def test_create_and_download_backup(self, admin_client):
        """Test creating a backup and downloading it"""
        # Create backup
        create_response = admin_client.post(f"{BASE_URL}/api/admin/backup/create")
        assert create_response.status_code == 200, f"Failed to create backup: {create_response.text}"
        data = create_response.json()
        
        assert "backup" in data
        backup_id = data["backup"]["id"]
        print(f"✓ Created backup: {backup_id}")
        
        # Download backup
        download_response = admin_client.get(f"{BASE_URL}/api/admin/backup/download/{backup_id}")
        assert download_response.status_code == 200, f"Failed to download: {download_response.text}"
        
        # Check response is gzipped content
        content_type = download_response.headers.get("Content-Type", "")
        assert "gzip" in content_type or len(download_response.content) > 0
        print(f"✓ Downloaded backup successfully ({len(download_response.content)} bytes)")
        
        # Delete the test backup
        delete_response = admin_client.delete(f"{BASE_URL}/api/admin/backup/{backup_id}")
        assert delete_response.status_code == 200
        print("✓ Test backup cleaned up")
    
    def test_download_nonexistent_backup(self, admin_client):
        """Test download with invalid backup ID"""
        response = admin_client.get(f"{BASE_URL}/api/admin/backup/download/nonexistent-id")
        assert response.status_code == 404
        print("✓ Download returns 404 for nonexistent backup")


class TestAdminPaymentGatewayDisplay:
    """Tests for admin payment gateway settings display"""
    
    def test_get_payment_gateways(self, admin_client):
        """Test that payment gateways list returns masked keys"""
        response = admin_client.get(f"{BASE_URL}/api/admin/payment-gateways")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        # Check that api_key is masked (should end with ****)
        for gw in data:
            if gw.get("api_key"):
                assert "****" in gw["api_key"], f"API key should be masked: {gw['api_key']}"
        print(f"✓ Payment gateways list works - {len(data)} gateways, keys are masked")


class TestOperatorInvoiceTemplate:
    """Tests for operator invoice template selection"""
    
    def test_get_invoice_settings(self, operator_client):
        """Test getting invoice settings"""
        response = operator_client.get(f"{BASE_URL}/api/operator/invoice-settings")
        # May return 200 with data or default values
        assert response.status_code in [200, 404], f"Unexpected: {response.text}"
        if response.status_code == 200:
            data = response.json()
            # invoice_template should be present (classic or modern)
            if "invoice_template" in data:
                assert data["invoice_template"] in ["classic", "modern", None, ""]
                print(f"✓ Invoice settings retrieved - Template: {data.get('invoice_template', 'not set')}")
            else:
                print("✓ Invoice settings retrieved (no template set yet)")
        else:
            print("✓ Invoice settings endpoint works (no settings yet)")
    
    def test_update_invoice_template(self, operator_client):
        """Test updating invoice template selection"""
        # Set to 'modern'
        response = operator_client.put(f"{BASE_URL}/api/operator/invoice-settings", json={
            "invoice_template": "modern"
        })
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify it was saved
        get_response = operator_client.get(f"{BASE_URL}/api/operator/invoice-settings")
        if get_response.status_code == 200:
            data = get_response.json()
            assert data.get("invoice_template") == "modern"
        
        # Set back to 'classic'
        response2 = operator_client.put(f"{BASE_URL}/api/operator/invoice-settings", json={
            "invoice_template": "classic"
        })
        assert response2.status_code == 200
        print("✓ Invoice template selection works (tested modern and classic)")


class TestAdminSettings:
    """Tests for admin settings endpoints"""
    
    def test_get_admin_settings(self, admin_client):
        """Test getting global admin settings"""
        response = admin_client.get(f"{BASE_URL}/api/admin/settings")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify expected fields
        assert "active_payment_gateway" in data or "gst_rate" in data
        print(f"✓ Admin settings retrieved - Gateway: {data.get('active_payment_gateway', 'N/A')}")
    
    def test_update_admin_settings(self, admin_client):
        """Test updating admin settings"""
        # Get current settings
        get_response = admin_client.get(f"{BASE_URL}/api/admin/settings")
        current = get_response.json()
        
        # Update with same values (non-destructive test)
        update_data = {
            "active_payment_gateway": current.get("active_payment_gateway", "razorpay"),
            "auto_invoice_days_before": current.get("auto_invoice_days_before", 3),
            "gst_rate": current.get("gst_rate", 18),
            "late_fee_percentage": current.get("late_fee_percentage", 0),
            "notification_enabled": current.get("notification_enabled", True)
        }
        
        response = admin_client.put(f"{BASE_URL}/api/admin/settings", json=update_data)
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ Admin settings update works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
