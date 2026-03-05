"""
Iteration 6 Test Suite - Announcements, CSV Export, Sidebar Links
Tests for:
1. Announcements page and API (GET/POST /api/operator/announcements)
2. Sidebar links for Announcements and Subscription
3. CSV export on operator reports
4. Invoice tab in operator settings
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

# Test credentials
OPERATOR_EMAIL = "demo@democorp.com"
OPERATOR_PASSWORD = "demo123"
STAFF_EMAIL = "staff@democorp.com"
STAFF_PASSWORD = "staff123"

class TestSetup:
    """Test setup and authentication"""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    @pytest.fixture(scope="class")
    def operator_token(self, api_client):
        """Get operator auth token"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": OPERATOR_EMAIL,
            "password": OPERATOR_PASSWORD
        })
        assert response.status_code == 200, f"Operator login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def staff_token(self, api_client):
        """Get staff auth token"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Staff login failed - skipping staff tests")

class TestAnnouncements(TestSetup):
    """Tests for Announcements API"""
    
    def test_get_announcements(self, api_client, operator_token):
        """GET /api/operator/announcements returns list of announcements"""
        response = api_client.get(
            f"{BASE_URL}/api/operator/announcements",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Failed to get announcements: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of announcements"
        print(f"Found {len(data)} existing announcements")
        
    def test_create_announcement_without_whatsapp(self, api_client, operator_token):
        """POST /api/operator/announcements with send_whatsapp=false creates announcement"""
        payload = {
            "title": f"TEST_Announcement_{datetime.now().strftime('%H%M%S')}",
            "message": "This is a test announcement message for testing purposes.",
            "send_whatsapp": False,
            "send_to_all": True
        }
        response = api_client.post(
            f"{BASE_URL}/api/operator/announcements",
            json=payload,
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Failed to create announcement: {response.text}"
        data = response.json()
        # Verify response contains recipients count
        assert "recipients" in data, "Response should contain recipients count"
        assert isinstance(data["recipients"], int), "Recipients should be integer"
        print(f"Announcement created successfully. Recipients: {data['recipients']}")
        
    def test_create_announcement_with_whatsapp_fails_without_addon(self, api_client, operator_token):
        """POST /api/operator/announcements with send_whatsapp=true fails if addon not enabled"""
        payload = {
            "title": "TEST_WhatsApp_Announcement",
            "message": "This should fail because WhatsApp addon is not enabled.",
            "send_whatsapp": True,
            "send_to_all": True
        }
        response = api_client.post(
            f"{BASE_URL}/api/operator/announcements",
            json=payload,
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        # Should return 403 since trial plan doesn't have notification_module
        assert response.status_code == 403, f"Expected 403 for WhatsApp without addon, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data, "Response should contain detail message"
        assert "WhatsApp" in data["detail"] or "notification" in data["detail"].lower(), \
            f"Error message should mention WhatsApp/notification: {data['detail']}"
        print(f"WhatsApp announcement correctly blocked: {data['detail']}")
        
    def test_verify_announcement_persisted(self, api_client, operator_token):
        """Verify the test announcement was persisted"""
        response = api_client.get(
            f"{BASE_URL}/api/operator/announcements",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Find our test announcement
        test_announcements = [a for a in data if a.get("title", "").startswith("TEST_")]
        assert len(test_announcements) > 0, "Test announcement should be persisted"
        
        # Verify announcement structure
        ann = test_announcements[0]
        assert "id" in ann, "Announcement should have id"
        assert "title" in ann, "Announcement should have title"
        assert "message" in ann, "Announcement should have message"
        assert "recipient_count" in ann, "Announcement should have recipient_count"
        assert "sent_via_whatsapp" in ann, "Announcement should have sent_via_whatsapp"
        assert "created_at" in ann, "Announcement should have created_at"
        print(f"Verified announcement structure: {ann['title']}")

class TestSubscription(TestSetup):
    """Tests for Subscription API"""
    
    def test_get_subscription(self, api_client, operator_token):
        """GET /api/operator/subscription returns subscription details"""
        response = api_client.get(
            f"{BASE_URL}/api/operator/subscription",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Failed to get subscription: {response.text}"
        data = response.json()
        
        # Verify subscription fields
        assert "operator_id" in data, "Should have operator_id"
        assert "status" in data, "Should have status"
        assert "company_name" in data, "Should have company_name"
        assert "available_plans" in data, "Should have available_plans list"
        
        print(f"Subscription status: {data['status']}, Plan: {data.get('saas_plan_name', 'None')}")

class TestReportsAPI(TestSetup):
    """Tests for Reports API that support CSV export"""
    
    def test_get_revenue_report(self, api_client, operator_token):
        """GET /api/operator/reports/revenue returns revenue data for CSV"""
        response = api_client.get(
            f"{BASE_URL}/api/operator/reports/revenue?start_date=2024-01-01&end_date=2026-12-31",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Failed to get revenue report: {response.text}"
        data = response.json()
        
        # Verify revenue report fields
        assert "total_revenue" in data, "Should have total_revenue"
        assert "total_invoices" in data, "Should have total_invoices"
        print(f"Revenue report: Total Revenue = {data['total_revenue']}, Total Invoices = {data['total_invoices']}")
        
    def test_get_gst_report(self, api_client, operator_token):
        """GET /api/operator/reports/gst-summary returns GST data for CSV"""
        response = api_client.get(
            f"{BASE_URL}/api/operator/reports/gst-summary?start_date=2024-01-01&end_date=2026-12-31",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Failed to get GST report: {response.text}"
        data = response.json()
        
        # Verify GST report fields used in CSV export
        assert "total_taxable_amount" in data, "Should have total_taxable_amount"
        assert "total_gst_collected" in data, "Should have total_gst_collected"
        print(f"GST report: Taxable Amount = {data['total_taxable_amount']}, GST = {data['total_gst_collected']}")
        
    def test_get_invoices_for_csv(self, api_client, operator_token):
        """GET /api/operator/invoices returns invoice data for CSV export"""
        response = api_client.get(
            f"{BASE_URL}/api/operator/invoices",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Failed to get invoices: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return list of invoices"
        print(f"Found {len(data)} invoices available for CSV export")

class TestInvoiceSettings(TestSetup):
    """Tests for Invoice Settings API (Invoice tab)"""
    
    def test_get_invoice_settings(self, api_client, operator_token):
        """GET /api/operator/invoice-settings returns invoice customization settings"""
        response = api_client.get(
            f"{BASE_URL}/api/operator/invoice-settings",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        # May return 200 with data or 404/empty if not configured
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"Invoice settings response: {response.status_code}")
        
    def test_update_invoice_settings(self, api_client, operator_token):
        """PUT /api/operator/invoice-settings updates invoice customization"""
        payload = {
            "company_name": "TEST Demo Corp",
            "invoice_prefix": "TINV",
            "show_gst": True,
            "invoice_footer": "Thank you for your business!"
        }
        response = api_client.put(
            f"{BASE_URL}/api/operator/invoice-settings",
            json=payload,
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Failed to update invoice settings: {response.text}"
        print("Invoice settings updated successfully")

class TestOperatorProfile(TestSetup):
    """Tests for Operator Profile (verifies Settings page access)"""
    
    def test_get_operator_profile(self, api_client, operator_token):
        """GET /api/operator/profile returns operator profile"""
        response = api_client.get(
            f"{BASE_URL}/api/operator/profile",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Failed to get profile: {response.text}"
        data = response.json()
        assert "company_name" in data, "Should have company_name"
        print(f"Profile loaded: {data.get('company_name')}")

class TestDashboard(TestSetup):
    """Tests for Dashboard (verify sidebar access points)"""
    
    def test_get_dashboard(self, api_client, operator_token):
        """GET /api/operator/dashboard verifies operator access"""
        response = api_client.get(
            f"{BASE_URL}/api/operator/dashboard",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200, f"Failed to get dashboard: {response.text}"
        data = response.json()
        assert "total_subscribers" in data or "subscriber_count" in data or "active_subscribers" in data, \
            "Dashboard should have subscriber stats"
        print("Dashboard loaded successfully")
