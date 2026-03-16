"""
Razorpay Payment Gateway Service
Handles payment link creation, QR codes, and webhooks
"""
import razorpay
import qrcode
import io
import base64
import hmac
import hashlib
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class RazorpayService:
    def __init__(self, api_key: str, api_secret: str):
        self.client = razorpay.Client(auth=(api_key, api_secret))
        self.api_key = api_key
        self.api_secret = api_secret
    
    def create_payment_link(
        self,
        amount: float,
        currency: str = "INR",
        description: str = "",
        customer_name: str = "",
        customer_email: str = "",
        customer_phone: str = "",
        invoice_number: str = "",
        callback_url: str = "",
        expire_by: int = None
    ) -> Dict[str, Any]:
        """
        Create a Razorpay payment link
        
        Args:
            amount: Amount in rupees (will be converted to paise)
            currency: Currency code (default INR)
            description: Payment description
            customer_name: Customer's name
            customer_email: Customer's email
            customer_phone: Customer's phone
            invoice_number: Reference invoice number
            callback_url: URL to redirect after payment
            expire_by: Unix timestamp for link expiry
        
        Returns:
            Payment link details including short_url
        """
        try:
            amount_paise = int(amount * 100)  # Convert to paise
            
            payload = {
                "amount": amount_paise,
                "currency": currency,
                "description": description,
                "customer": {
                    "name": customer_name,
                    "email": customer_email,
                    "contact": customer_phone
                },
                "notify": {
                    "sms": True,
                    "email": True
                },
                "reminder_enable": True,
                "notes": {
                    "invoice_number": invoice_number
                },
                "callback_url": callback_url,
                "callback_method": "get"
            }
            
            if expire_by:
                payload["expire_by"] = expire_by
            
            payment_link = self.client.payment_link.create(payload)
            
            logger.info(f"Payment link created: {payment_link.get('id')}")
            return payment_link
            
        except Exception as e:
            logger.error(f"Failed to create payment link: {str(e)}")
            raise
    
    def get_payment_link(self, payment_link_id: str) -> Dict[str, Any]:
        """Get payment link details"""
        return self.client.payment_link.fetch(payment_link_id)
    
    def cancel_payment_link(self, payment_link_id: str) -> Dict[str, Any]:
        """Cancel a payment link"""
        return self.client.payment_link.cancel(payment_link_id)
    
    def verify_webhook_signature(
        self,
        payload: str,
        signature: str,
        webhook_secret: str
    ) -> bool:
        """
        Verify Razorpay webhook signature
        
        Args:
            payload: Raw request body
            signature: X-Razorpay-Signature header
            webhook_secret: Webhook secret from Razorpay dashboard
        
        Returns:
            True if signature is valid
        """
        try:
            expected_signature = hmac.new(
                webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Signature verification failed: {str(e)}")
            return False
    
    def verify_payment_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str
    ) -> bool:
        """Verify payment signature for checkout flow"""
        try:
            self.client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            return True
        except Exception:
            return False
    
    def generate_qr_code(self, payment_url: str) -> str:
        """
        Generate QR code for payment link
        
        Args:
            payment_url: Payment link URL
        
        Returns:
            Base64 encoded PNG image
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(payment_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def get_payment_details(self, payment_id: str) -> Dict[str, Any]:
        """Get details of a payment"""
        return self.client.payment.fetch(payment_id)
    
    def create_order(
        self,
        amount: float,
        currency: str = "INR",
        receipt: str = "",
        notes: Dict = None
    ) -> Dict[str, Any]:
        """Create a Razorpay order for checkout flow"""
        amount_paise = int(amount * 100)
        
        payload = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt[:40] if receipt else "",
            "notes": notes or {}
        }
        
        return self.client.order.create(payload)


def get_razorpay_service(api_key: str, api_secret: str) -> Optional[RazorpayService]:
    """Factory function to create RazorpayService"""
    if not api_key or not api_secret:
        return None
    return RazorpayService(api_key, api_secret)
