"""
WhatsApp Business API Service
Handles sending templated messages for invoices, reminders, and notifications
"""
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class WhatsAppService:
    """Service for WhatsApp Business API Cloud interactions"""
    
    BASE_URL = "https://graph.facebook.com/v20.0"
    
    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def send_text_message(
        self,
        recipient_phone: str,
        message_text: str
    ) -> Dict[str, Any]:
        """
        Send a simple text message (only within 24-hour window)
        
        Args:
            recipient_phone: Phone number in E.164 format (without +)
            message_text: Message content (max 4096 chars)
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(recipient_phone),
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text
            }
        }
        
        return await self._send_request(payload)
    
    async def send_template_message(
        self,
        recipient_phone: str,
        template_name: str,
        language_code: str = "en",
        variables: Optional[List[str]] = None,
        header_params: Optional[List[str]] = None,
        button_params: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Send a pre-approved template message
        
        Args:
            recipient_phone: Phone in E.164 format
            template_name: Approved template name
            language_code: Language code (e.g., 'en', 'hi')
            variables: Body text variables
            header_params: Header variables
            button_params: Button variables
        """
        components = []
        
        # Header component
        if header_params:
            components.append({
                "type": "header",
                "parameters": [
                    {"type": "text", "text": str(p)} for p in header_params
                ]
            })
        
        # Body component
        if variables:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(v)} for v in variables
                ]
            })
        
        # Button component
        if button_params:
            for idx, btn in enumerate(button_params):
                components.append({
                    "type": "button",
                    "sub_type": btn.get("sub_type", "url"),
                    "index": str(idx),
                    "parameters": btn.get("parameters", [])
                })
        
        payload = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone(recipient_phone),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code}
            }
        }
        
        if components:
            payload["template"]["components"] = components
        
        return await self._send_request(payload)
    
    async def send_invoice_notification(
        self,
        recipient_phone: str,
        customer_name: str,
        invoice_number: str,
        amount: str,
        due_date: str,
        payment_link: str = None,
        template_name_override: str = None
    ) -> Dict[str, Any]:
        """
        Send invoice notification template
        
        Template should be pre-approved with variables:
        {{1}} - Customer name
        {{2}} - Invoice number
        {{3}} - Amount
        {{4}} - Due date
        """
        variables = [customer_name, invoice_number, amount, due_date]
        
        button_params = None
        if payment_link:
            # If template has a URL button, add payment link
            button_params = [{
                "sub_type": "url",
                "parameters": [{"type": "text", "text": payment_link}]
            }]
        
        return await self.send_template_message(
            recipient_phone=recipient_phone,
            template_name=template_name_override or "invoice_notification",
            variables=variables,
            button_params=button_params
        )
    
    async def send_payment_reminder(
        self,
        recipient_phone: str,
        customer_name: str,
        invoice_number: str,
        amount_due: str,
        days_overdue: str,
        payment_link: str = None,
        template_name_override: str = None
    ) -> Dict[str, Any]:
        """
        Send payment reminder template
        
        Template variables:
        {{1}} - Customer name
        {{2}} - Invoice number
        {{3}} - Amount due
        {{4}} - Days overdue
        """
        variables = [customer_name, invoice_number, amount_due, days_overdue]
        
        button_params = None
        if payment_link:
            button_params = [{
                "sub_type": "url",
                "parameters": [{"type": "text", "text": payment_link}]
            }]
        
        return await self.send_template_message(
            recipient_phone=recipient_phone,
            template_name=template_name_override or "payment_reminder",
            variables=variables,
            button_params=button_params
        )
    
    async def send_payment_confirmation(
        self,
        recipient_phone: str,
        customer_name: str,
        invoice_number: str,
        amount_paid: str,
        payment_date: str
    ) -> Dict[str, Any]:
        """Send payment confirmation template"""
        return await self.send_template_message(
            recipient_phone=recipient_phone,
            template_name="payment_confirmation",
            variables=[customer_name, invoice_number, amount_paid, payment_date]
        )
    
    async def send_bulk_messages(
        self,
        messages: List[Dict[str, Any]],
        template_name: str,
        rate_limit_delay: float = 0.1
    ) -> Dict[str, Any]:
        """
        Send multiple messages with rate limiting
        
        Args:
            messages: List of dicts with 'phone' and 'variables'
            template_name: Template to use
            rate_limit_delay: Seconds between messages
        
        Returns:
            Summary with success/failure counts
        """
        import asyncio
        
        results = {
            "total": len(messages),
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        for msg in messages:
            try:
                await self.send_template_message(
                    recipient_phone=msg["phone"],
                    template_name=template_name,
                    variables=msg.get("variables", [])
                )
                results["sent"] += 1
                await asyncio.sleep(rate_limit_delay)
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "phone": msg["phone"],
                    "error": str(e)
                })
        
        return results
    
    async def _send_request(self, payload: Dict) -> Dict[str, Any]:
        """Send request to WhatsApp API"""
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_body = response.text
                logger.error(f"WhatsApp API error: {error_body}")
                # Try to extract meaningful error message
                try:
                    error_json = response.json()
                    error_msg = error_json.get("error", {}).get("error_data", {}).get("details", "") or error_json.get("error", {}).get("message", "")
                    if error_msg:
                        raise Exception(f"WhatsApp API error ({response.status_code}): {error_msg}")
                except (ValueError, KeyError):
                    pass
                raise Exception(f"WhatsApp API error: {response.status_code} - {error_body}")
            
            return response.json()
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format without +"""
        # Remove common formatting
        cleaned = ''.join(c for c in phone if c.isdigit())
        # Add India country code if not present
        if len(cleaned) == 10:
            cleaned = "91" + cleaned
        return cleaned


def get_whatsapp_service(phone_number_id: str, access_token: str) -> Optional[WhatsAppService]:
    """Factory function to create WhatsAppService"""
    if not phone_number_id or not access_token:
        return None
    return WhatsAppService(phone_number_id, access_token)
