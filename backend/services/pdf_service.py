"""
Invoice PDF Generation Service
Generates professional PDF invoices with GST compliance
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import io
import base64
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class InvoicePDFService:
    """Service for generating professional invoice PDFs"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            fontSize=24,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1e293b'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            fontSize=16,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1e293b'),
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontSize=11,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#475569'),
            spaceBefore=15,
            spaceAfter=8
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceBodyText',
            fontSize=10,
            fontName='Helvetica',
            textColor=colors.HexColor('#334155'),
            leading=14
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceSmallText',
            fontSize=8,
            fontName='Helvetica',
            textColor=colors.HexColor('#64748b')
        ))
    
    def generate_invoice_pdf(
        self,
        invoice_data: Dict[str, Any],
        operator_data: Dict[str, Any],
        subscriber_data: Dict[str, Any],
        plan_data: Dict[str, Any],
        qr_code_base64: Optional[str] = None
    ) -> bytes:
        """
        Generate a professional invoice PDF
        
        Args:
            invoice_data: Invoice details
            operator_data: Operator/company details
            subscriber_data: Customer details
            plan_data: Service plan details
            qr_code_base64: Optional QR code for payment
        
        Returns:
            PDF as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        elements = []
        
        # Header with company info
        elements.extend(self._build_header(operator_data, invoice_data))
        
        # Bill To section
        elements.extend(self._build_bill_to(subscriber_data))
        
        # Invoice details table
        elements.extend(self._build_invoice_table(invoice_data, plan_data))
        
        # Amount summary
        elements.extend(self._build_amount_summary(invoice_data))
        
        # Payment QR code if available
        if qr_code_base64:
            elements.extend(self._build_qr_section(qr_code_base64))
        
        # Bank details if available
        if operator_data.get('bank_account_number'):
            elements.extend(self._build_bank_details(operator_data))
        
        # Footer with terms
        elements.extend(self._build_footer())
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_header(self, operator: Dict, invoice: Dict) -> list:
        """Build invoice header section"""
        elements = []
        
        # Company name and invoice title
        header_data = [
            [
                Paragraph(operator.get('company_name', 'Company'), self.styles['CompanyName']),
                Paragraph('TAX INVOICE', self.styles['InvoiceTitle'])
            ]
        ]
        
        header_table = Table(header_data, colWidths=[250, 250])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10))
        
        # Company details and invoice info
        company_info = f"""
        {operator.get('owner_name', '')}<br/>
        Phone: {operator.get('phone', '')}<br/>
        Email: {operator.get('email', '')}
        """
        if operator.get('gst_number'):
            company_info += f"<br/>GSTIN: {operator.get('gst_number')}"
        
        invoice_info = f"""
        <b>Invoice #:</b> {invoice.get('invoice_number', '')}<br/>
        <b>Date:</b> {self._format_date(invoice.get('created_at'))}<br/>
        <b>Due Date:</b> {self._format_date(invoice.get('due_date'))}<br/>
        <b>Status:</b> {invoice.get('status', '').upper()}
        """
        
        info_data = [
            [
                Paragraph(company_info, self.styles['InvoiceBodyText']),
                Paragraph(invoice_info, self.styles['InvoiceBodyText'])
            ]
        ]
        
        info_table = Table(info_data, colWidths=[250, 250])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_bill_to(self, subscriber: Dict) -> list:
        """Build Bill To section"""
        elements = []
        
        elements.append(Paragraph('BILL TO', self.styles['SectionHeader']))
        
        bill_to_info = f"""
        <b>{subscriber.get('name', '')}</b><br/>
        Phone: {subscriber.get('whatsapp_number', '')}
        """
        if subscriber.get('email'):
            bill_to_info += f"<br/>Email: {subscriber.get('email')}"
        if subscriber.get('address'):
            bill_to_info += f"<br/>Address: {subscriber.get('address')}"
        
        elements.append(Paragraph(bill_to_info, self.styles['InvoiceBodyText']))
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_invoice_table(self, invoice: Dict, plan: Dict) -> list:
        """Build invoice items table"""
        elements = []
        
        elements.append(Paragraph('INVOICE DETAILS', self.styles['SectionHeader']))
        
        # Service period
        service_period = f"{self._format_date(invoice.get('service_start_date'))} - {self._format_date(invoice.get('service_end_date'))}"
        
        # Table data
        table_data = [
            ['Description', 'Service Period', 'Amount'],
            [
                invoice.get('plan_name', plan.get('name', 'Service')),
                service_period,
                f"₹{invoice.get('base_amount', 0):,.2f}"
            ]
        ]
        
        # Add discount row if applicable
        discount = invoice.get('discount', 0)
        if discount > 0:
            table_data.append(['Discount', '', f"-₹{discount:,.2f}"])
        
        # Add tax row if applicable
        tax = invoice.get('tax_amount', 0)
        if tax > 0:
            tax_type = plan.get('tax_type', 'GST')
            tax_pct = plan.get('tax_percentage', 18)
            table_data.append([f'{tax_type.upper()} ({tax_pct}%)', '', f"₹{tax:,.2f}"])
        
        invoice_table = Table(table_data, colWidths=[250, 150, 100])
        invoice_table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            # Body style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#334155')),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        
        elements.append(invoice_table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_amount_summary(self, invoice: Dict) -> list:
        """Build amount summary section"""
        elements = []
        
        final_amount = invoice.get('final_amount', 0)
        
        summary_data = [
            ['', 'Total Amount Due:', f"₹{final_amount:,.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[250, 150, 100])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (1, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 0), (-1, -1), 12),
            ('TEXTCOLOR', (1, 0), (-1, -1), colors.HexColor('#1e293b')),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BACKGROUND', (1, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_qr_section(self, qr_base64: str) -> list:
        """Build payment QR code section"""
        elements = []
        
        elements.append(Paragraph('SCAN TO PAY', self.styles['SectionHeader']))
        
        try:
            qr_data = base64.b64decode(qr_base64)
            qr_buffer = io.BytesIO(qr_data)
            qr_image = Image(qr_buffer, width=100, height=100)
            elements.append(qr_image)
        except Exception as e:
            logger.error(f"Failed to add QR code: {e}")
        
        elements.append(Spacer(1, 10))
        elements.append(Paragraph('Scan QR code to pay instantly', self.styles['InvoiceSmallText']))
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_bank_details(self, operator: Dict) -> list:
        """Build bank details section"""
        elements = []
        
        elements.append(Paragraph('BANK DETAILS', self.styles['SectionHeader']))
        
        bank_info = f"""
        Account Name: {operator.get('bank_account_name', '')}<br/>
        Account Number: {operator.get('bank_account_number', '')}<br/>
        IFSC Code: {operator.get('bank_ifsc', '')}<br/>
        Bank: {operator.get('bank_name', '')}
        """
        
        elements.append(Paragraph(bank_info, self.styles['InvoiceBodyText']))
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_footer(self) -> list:
        """Build footer with terms"""
        elements = []
        
        elements.append(Spacer(1, 20))
        
        terms = """
        <b>Terms & Conditions:</b><br/>
        1. Payment is due by the due date mentioned above.<br/>
        2. Late payments may attract additional charges.<br/>
        3. This is a computer generated invoice and does not require signature.
        """
        
        elements.append(Paragraph(terms, self.styles['InvoiceSmallText']))
        
        return elements
    
    def _format_date(self, date_value) -> str:
        """Format date for display"""
        if not date_value:
            return ""
        
        if isinstance(date_value, str):
            try:
                date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except:
                return date_value
        
        if isinstance(date_value, datetime):
            return date_value.strftime('%d %b %Y')
        
        return str(date_value)
    
    def generate_invoice_base64(self, *args, **kwargs) -> str:
        """Generate PDF and return as base64 string"""
        pdf_bytes = self.generate_invoice_pdf(*args, **kwargs)
        return base64.b64encode(pdf_bytes).decode('utf-8')
