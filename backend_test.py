#!/usr/bin/env python3
"""
Backend Test Suite for WhatsApp Template Fixes
Tests the new fields and functionality for WhatsApp Business API integration
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime, timezone

# Backend URL from environment
BACKEND_URL = "https://invoice-notify-wa.preview.emergentagent.com/api"

class WhatsAppTemplateTestSuite:
    def __init__(self):
        self.admin_token = None
        self.operator_token = None
        self.test_template_id = None
        self.test_results = {
            "template_crud": False,
            "build_wa_send_params": False,
            "known_invoice_variables": False,
            "send_notification_signature": False
        }
        
    async def run_all_tests(self):
        """Run all WhatsApp template tests"""
        print("🚀 Starting WhatsApp Template Fixes Test Suite")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        try:
            # 1. Login as admin
            await self.login_admin()
            
            # 2. Test Template CRUD with new fields
            await self.test_template_crud_with_new_fields()
            
            # 3. Test build_wa_send_params function
            await self.test_build_wa_send_params()
            
            # 4. Test KNOWN_INVOICE_VARIABLES
            await self.test_known_invoice_variables()
            
            # 5. Test send_notification endpoint signature
            await self.test_send_notification_signature()
            
            # Summary
            self.print_test_summary()
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            return False
            
        return all(self.test_results.values())
    
    async def login_admin(self):
        """Login as admin to get JWT token"""
        print("🔐 Logging in as admin...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/auth/login",
                json={
                    "email": "admin@saas.com",
                    "password": "admin123"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Admin login failed: {response.status_code} - {response.text}")
            
            data = response.json()
            self.admin_token = data["access_token"]
            print("✅ Admin login successful")
    
    async def test_template_crud_with_new_fields(self):
        """Test WhatsApp template CRUD operations with new fields"""
        print("\n📝 Testing WhatsApp Template CRUD with new fields...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        async with httpx.AsyncClient() as client:
            # 1. Create template with new fields
            print("  Creating template with new fields...")
            template_data = {
                "template_name": "test_invoice",
                "display_name": "Test Invoice",
                "template_type": "invoice_notification",
                "body_variables": ["customer_name", "plan_name", "tenure", "due_date", "amount"],
                "header_type": "image",
                "header_image_static": True,  # NEW field
                "has_payment_button": True,
                "button_url_variable": "invoice_public_url",  # NEW field
                "language_code": "en",
                "is_active": True,
                "description": "test"
            }
            
            response = await client.post(
                f"{BACKEND_URL}/admin/whatsapp-templates",
                headers=headers,
                json=template_data
            )
            
            if response.status_code != 200:
                print(f"    ❌ Template creation failed: {response.status_code} - {response.text}")
                return
            
            created_template = response.json()
            self.test_template_id = created_template["id"]
            
            # Verify new fields are present
            if not created_template.get("header_image_static"):
                print("    ❌ header_image_static field missing or False")
                return
            
            if created_template.get("button_url_variable") != "invoice_public_url":
                print(f"    ❌ button_url_variable incorrect: {created_template.get('button_url_variable')}")
                return
            
            print("    ✅ Template created with new fields")
            
            # 2. Update template to test header_image_static=false
            print("  Updating template header_image_static to false...")
            update_data = {"header_image_static": False}
            
            response = await client.put(
                f"{BACKEND_URL}/admin/whatsapp-templates/{self.test_template_id}",
                headers=headers,
                json=update_data
            )
            
            if response.status_code != 200:
                print(f"    ❌ Template update failed: {response.status_code} - {response.text}")
                return
            
            updated_template = response.json()
            if updated_template.get("header_image_static") is not False:
                print(f"    ❌ header_image_static not updated: {updated_template.get('header_image_static')}")
                return
            
            print("    ✅ Template updated successfully")
            
            # 3. List templates and verify both appear
            print("  Listing templates...")
            response = await client.get(
                f"{BACKEND_URL}/admin/whatsapp-templates",
                headers=headers
            )
            
            if response.status_code != 200:
                print(f"    ❌ Template listing failed: {response.status_code} - {response.text}")
                return
            
            templates = response.json()
            test_template_found = any(t["id"] == self.test_template_id for t in templates)
            
            if not test_template_found:
                print("    ❌ Created template not found in list")
                return
            
            print("    ✅ Template found in list")
            print("✅ Template CRUD with new fields test passed")
            self.test_results["template_crud"] = True
    
    async def test_build_wa_send_params(self):
        """Test build_wa_send_params helper function"""
        print("\n🔧 Testing build_wa_send_params helper function...")
        
        # This test requires importing the function and testing it directly
        # Since we can't import directly in this test environment, we'll test the behavior
        # through the API endpoints that use this function
        
        try:
            # Import the function for testing
            sys.path.append('/app/backend')
            from services.whatsapp_service import build_wa_send_params, KNOWN_INVOICE_VARIABLES
            
            # Mock database (we'll use a simple dict)
            class MockDB:
                async def find_one(self, *args, **kwargs):
                    return None
            
            db = MockDB()
            
            # Create mock template with header_image_static=True
            tmpl_doc = {
                "header_image_static": True,
                "has_payment_button": True,
                "button_url_variable": "invoice_public_url",
                "body_variables": ["customer_name", "amount"],
                "header_type": "image",
                "language_code": "en",
                "template_name": "test_template"
            }
            
            # Mock invoice and subscriber
            invoice = {
                "invoice_number": "INV-001",
                "final_amount": 1000.0,
                "due_date": "2024-01-15T00:00:00Z",
                "operator_id": "test_op"
            }
            
            subscriber = {
                "name": "Test Customer"
            }
            
            invoice_public_url = "https://example.com/invoice/INV-001"
            
            # Test the function
            result = await build_wa_send_params(db, tmpl_doc, invoice, subscriber, invoice_public_url)
            
            # Verify header_params is None for static image
            if result.get("header_params") is not None:
                print(f"    ❌ header_params should be None for static image, got: {result.get('header_params')}")
                return
            
            # Verify btn_params contains the invoice_public_url
            btn_params = result.get("btn_params")
            if not btn_params:
                print("    ❌ btn_params is missing")
                return
            
            if len(btn_params) == 0:
                print("    ❌ btn_params is empty")
                return
            
            btn_url = btn_params[0].get("parameters", [{}])[0].get("text", "")
            if btn_url != invoice_public_url:
                print(f"    ❌ Button URL incorrect. Expected: {invoice_public_url}, Got: {btn_url}")
                return
            
            print("    ✅ header_params is None for static image")
            print("    ✅ btn_params contains correct invoice_public_url")
            print("✅ build_wa_send_params function test passed")
            self.test_results["build_wa_send_params"] = True
            
        except ImportError as e:
            print(f"    ❌ Could not import build_wa_send_params: {e}")
        except Exception as e:
            print(f"    ❌ build_wa_send_params test failed: {e}")
    
    async def test_known_invoice_variables(self):
        """Test KNOWN_INVOICE_VARIABLES contains invoice_public_url"""
        print("\n📋 Testing KNOWN_INVOICE_VARIABLES...")
        
        try:
            sys.path.append('/app/backend')
            from services.whatsapp_service import KNOWN_INVOICE_VARIABLES
            
            # Check if invoice_public_url is in KNOWN_INVOICE_VARIABLES
            if "invoice_public_url" not in KNOWN_INVOICE_VARIABLES:
                print("    ❌ invoice_public_url not found in KNOWN_INVOICE_VARIABLES")
                return
            
            # Test that it resolves to the invoice's invoice_public_url field
            mock_invoice = {"invoice_public_url": "https://test.com/invoice/123"}
            mock_subscriber = {}
            
            resolver = KNOWN_INVOICE_VARIABLES["invoice_public_url"]
            result = resolver(mock_invoice, mock_subscriber)
            
            if result != "https://test.com/invoice/123":
                print(f"    ❌ invoice_public_url resolver returned wrong value: {result}")
                return
            
            print("    ✅ invoice_public_url found in KNOWN_INVOICE_VARIABLES")
            print("    ✅ invoice_public_url resolves correctly")
            print("✅ KNOWN_INVOICE_VARIABLES test passed")
            self.test_results["known_invoice_variables"] = True
            
        except ImportError as e:
            print(f"    ❌ Could not import KNOWN_INVOICE_VARIABLES: {e}")
        except Exception as e:
            print(f"    ❌ KNOWN_INVOICE_VARIABLES test failed: {e}")
    
    async def test_send_notification_signature(self):
        """Test send_notification endpoint accepts request parameter"""
        print("\n🔍 Testing send_notification endpoint signature...")
        
        try:
            # Read the operator.py file to check the function signature
            with open('/app/backend/routers/operator.py', 'r') as f:
                content = f.read()
            
            # Look for the send_notification function definition
            import re
            pattern = r'async def send_whatsapp_notification\([^)]*request:\s*Request[^)]*\)'
            match = re.search(pattern, content)
            
            if not match:
                print("    ❌ send_notification endpoint does not accept 'request: Request' parameter")
                return
            
            print("    ✅ send_notification endpoint accepts 'request: Request' parameter")
            print("✅ send_notification endpoint signature test passed")
            self.test_results["send_notification_signature"] = True
            
        except Exception as e:
            print(f"    ❌ send_notification signature test failed: {e}")
    
    def print_test_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())
        
        for test_name, passed in self.test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name:40} {status}")
        
        print("-" * 60)
        print(f"Total: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed!")
    
    async def cleanup(self):
        """Clean up test data"""
        if self.test_template_id and self.admin_token:
            try:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                async with httpx.AsyncClient() as client:
                    await client.delete(
                        f"{BACKEND_URL}/admin/whatsapp-templates/{self.test_template_id}",
                        headers=headers
                    )
                print("🧹 Test template cleaned up")
            except:
                pass

async def main():
    """Main test runner"""
    test_suite = WhatsAppTemplateTestSuite()
    
    try:
        success = await test_suite.run_all_tests()
        return success
    finally:
        await test_suite.cleanup()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)