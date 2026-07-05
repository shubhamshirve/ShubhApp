"""
Invoice PDF Generation Service
Generates professional PDF invoices with GST compliance.
Supports two designs: Classic (dark header) and Modern (teal accent).
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas as rl_canvas
import io
import base64
import os
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from urllib.request import urlopen

logger = logging.getLogger(__name__)

# ─── Colour constants ──────────────────────────────────────────────────────────
CLASSIC_DARK   = colors.HexColor("#1e293b")
CLASSIC_MID    = colors.HexColor("#475569")
CLASSIC_LIGHT  = colors.HexColor("#f1f5f9")
CLASSIC_BORDER = colors.HexColor("#e2e8f0")
CLASSIC_TEXT   = colors.HexColor("#334155")

MODERN_PRIMARY  = colors.HexColor("#0f766e")   # teal-700
MODERN_ACCENT   = colors.HexColor("#14b8a6")   # teal-400
MODERN_BG_LIGHT = colors.HexColor("#f0fdfa")   # teal-50
MODERN_DARK     = colors.HexColor("#134e4a")   # teal-900
MODERN_TEXT     = colors.HexColor("#1e293b")
MODERN_SUBTLE   = colors.HexColor("#64748b")


class InvoicePDFService:
    """Service for generating professional invoice PDFs (Classic & Modern)."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    # ── Style setup ────────────────────────────────────────────────────────────

    def _setup_custom_styles(self):
        """Register reusable paragraph styles."""
        defs = [
            ("InvoiceTitle",   24, "Helvetica-Bold",  CLASSIC_DARK,  TA_CENTER, 20, 0),
            ("CompanyName",    16, "Helvetica-Bold",  CLASSIC_DARK,  TA_LEFT,    0, 0),
            ("SectionHeader",  11, "Helvetica-Bold",  CLASSIC_MID,   TA_LEFT,   15, 8),
            ("InvoiceBodyText",10, "Helvetica",        CLASSIC_TEXT,  TA_LEFT,    0, 0),
            ("InvoiceSmallText", 8,"Helvetica",        CLASSIC_MID,   TA_LEFT,    0, 0),
            # Modern variants
            ("ModernTitle",    22, "Helvetica-Bold",  colors.white,  TA_LEFT,    0, 0),
            ("ModernSubtitle",  9, "Helvetica",        colors.HexColor("#99f6e4"), TA_LEFT, 0, 0),
            ("ModernLabel",     8, "Helvetica-Bold",  MODERN_SUBTLE, TA_LEFT,    0, 4),
            ("ModernValue",    10, "Helvetica",        MODERN_TEXT,   TA_LEFT,    0, 2),
            ("ModernSection",  10, "Helvetica-Bold",  MODERN_PRIMARY,TA_LEFT,    12,4),
            ("ModernSmall",     8, "Helvetica",        MODERN_SUBTLE, TA_LEFT,    0, 0),
            ("ModernTotal",    13, "Helvetica-Bold",  MODERN_DARK,   TA_RIGHT,   0, 0),
        ]
        for (name, size, font, color, align, before, after) in defs:
            if name not in self.styles:
                self.styles.add(ParagraphStyle(
                    name=name, fontSize=size, fontName=font,
                    textColor=color, alignment=align,
                    spaceBefore=before, spaceAfter=after, leading=size * 1.35
                ))

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate_invoice_pdf(
        self,
        invoice_data: Dict[str, Any],
        operator_data: Dict[str, Any],
        subscriber_data: Dict[str, Any],
        plan_data: Dict[str, Any],
        qr_code_base64: Optional[str] = None,
        template: str = "classic",
    ) -> bytes:
        """Route to Classic or Modern renderer based on *template*."""
        if template == "modern":
            return self._generate_modern_invoice(
                invoice_data, operator_data, subscriber_data, plan_data, qr_code_base64
            )
        return self._generate_classic_invoice(
            invoice_data, operator_data, subscriber_data, plan_data, qr_code_base64
        )

    def generate_invoice_base64(self, *args, **kwargs) -> str:
        """Generate PDF and return as base64 string."""
        pdf_bytes = self.generate_invoice_pdf(*args, **kwargs)
        return base64.b64encode(pdf_bytes).decode("utf-8")

    # ── Classic Template ───────────────────────────────────────────────────────

    def _generate_classic_invoice(self, invoice, operator, subscriber, plan, qr_b64) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=20*mm, leftMargin=20*mm,
            topMargin=20*mm, bottomMargin=20*mm
        )
        elems = []
        elems.extend(self._classic_header(operator, invoice))
        elems.extend(self._classic_bill_to(subscriber, operator))
        elems.extend(self._classic_items(invoice, plan))
        elems.extend(self._classic_summary(invoice))
        if qr_b64:
            elems.extend(self._build_qr_section(qr_b64))
        if self._is_visible(operator, "show_bank_details") and operator.get("bank_account_number"):
            elems.extend(self._build_bank_details(operator))
        elems.extend(self._classic_footer(operator))
        doc.build(elems)
        buffer.seek(0)
        return buffer.getvalue()

    def _classic_header(self, operator, invoice):
        elems = []
        company_cell = [Paragraph(operator.get("company_name", "Company"), self.styles["CompanyName"])]
        logo = self._build_logo(operator.get("logo_url"), max_width=42*mm, max_height=16*mm)
        if logo:
            company_cell.insert(0, logo)
            company_cell.insert(1, Spacer(1, 4))
        header_data = [[
            company_cell,
            Paragraph("TAX INVOICE", self.styles["InvoiceTitle"])
        ]]
        t = Table(header_data, colWidths=[250, 250])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN",  (1, 0), (1,  0), "RIGHT"),
        ]))
        elems.append(t)
        elems.append(Spacer(1, 6))

        co_lines = []
        if operator.get("owner_name"):
            co_lines.append(operator["owner_name"])
        if operator.get("phone"):
            co_lines.append(f"Phone: {operator['phone']}")
        if operator.get("email"):
            co_lines.append(f"Email: {operator['email']}")
        if operator.get("gst_number"):
            co_lines.append(f"GSTIN: {operator['gst_number']}")
        if operator.get("company_address"):
            co_lines.append(f"Address: {operator['company_address']}")
        co_info = "<br/>".join(co_lines) or operator.get("company_name", "Company")

        inv_info = (
            f"<b>Invoice #:</b> {invoice.get('invoice_number', '')}<br/>"
            f"<b>Date:</b> {self._fmt(invoice.get('created_at'))}<br/>"
            f"<b>Due Date:</b> {self._fmt(invoice.get('due_date'))}<br/>"
            f"<b>Status:</b> {invoice.get('status', '').upper()}"
        )
        info_t = Table([[
            Paragraph(co_info, self.styles["InvoiceBodyText"]),
            Paragraph(inv_info, self.styles["InvoiceBodyText"])
        ]], colWidths=[250, 250])
        info_t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN",  (1, 0), (1,  0), "RIGHT"),
        ]))
        elems.append(info_t)
        elems.append(Spacer(1, 16))
        return elems

    def _classic_bill_to(self, subscriber, operator):
        elems = []
        elems.append(Paragraph("BILL TO", self.styles["SectionHeader"]))
        lines = [f"<b>{subscriber.get('name', '')}</b>"]
        if subscriber.get("whatsapp_number") and self._is_visible(operator, "show_subscriber_phone"):
            lines.append(f"Phone: {subscriber['whatsapp_number']}")
        if subscriber.get("email") and self._is_visible(operator, "show_subscriber_email"):
            lines.append(f"Email: {subscriber['email']}")
        if subscriber.get("address") and self._is_visible(operator, "show_subscriber_address"):
            lines.append(f"Address: {subscriber['address']}")
        bill = "<br/>".join(lines)
        elems.append(Paragraph(bill, self.styles["InvoiceBodyText"]))
        elems.append(Spacer(1, 16))
        return elems

    def _classic_items(self, invoice, plan):
        elems = []
        elems.append(Paragraph("INVOICE DETAILS", self.styles["SectionHeader"]))
        
        rows = [["Description", "Service Period", "Amount"]]
        
        line_items = invoice.get("line_items", [])
        if not line_items:
            # Fallback for old invoices
            period = f"{self._fmt(invoice.get('service_start_date'))} – {self._fmt(invoice.get('service_end_date'))}"
            rows.append([
                invoice.get("plan_name", plan.get("name", "Service")),
                period,
                f"₹{invoice.get('base_amount', 0):,.2f}"
            ])
        else:
            for item in line_items:
                if item.get("plan_name") == "Previous Pending":
                    # Show "Till <date>" instead of a meaningless same-day range
                    till_date = self._fmt(item.get("service_start_date"))
                    period = f"Till {till_date}" if till_date else "Carried forward"
                else:
                    period = f"{self._fmt(item.get('service_start_date'))} – {self._fmt(item.get('service_end_date'))}"
                rows.append([
                    item.get("plan_name", "Service"),
                    period,
                    f"₹{item.get('base_amount', 0):,.2f}"
                ])

        disc = invoice.get("discount", 0)
        if disc > 0:
            rows.append(["Discount", "", f"-₹{disc:,.2f}"])
        
        tax = invoice.get("tax_amount", 0)
        if tax > 0:
            rows.append([
                "GST / Taxes",
                "", f"₹{tax:,.2f}"
            ])

        t = Table(rows, colWidths=[250, 150, 100])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), CLASSIC_DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 10),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING",    (0, 0), (-1, 0), 10),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 10),
            ("TEXTCOLOR",     (0, 1), (-1, -1), CLASSIC_TEXT),
            ("ALIGN",         (2, 1), (2, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ("TOPPADDING",    (0, 1), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.5, CLASSIC_BORDER),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, CLASSIC_LIGHT]),
        ]))
        elems.append(t)
        elems.append(Spacer(1, 12))
        return elems

    def _classic_summary(self, invoice):
        elems = []
        final = invoice.get("final_amount", 0)
        t = Table([["", "Total Amount Due:", f"₹{final:,.2f}"]], colWidths=[250, 150, 100])
        t.setStyle(TableStyle([
            ("FONTNAME",      (1, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (1, 0), (-1, -1), 12),
            ("TEXTCOLOR",     (1, 0), (-1, -1), CLASSIC_DARK),
            ("ALIGN",         (1, 0), (1, -1), "RIGHT"),
            ("ALIGN",         (2, 0), (2, -1), "RIGHT"),
            ("BACKGROUND",    (1, 0), (-1, -1), CLASSIC_LIGHT),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ]))
        elems.append(t)
        elems.append(Spacer(1, 16))
        return elems

    def _classic_footer(self, operator):
        elems = []
        elems.append(Spacer(1, 16))
        footer_text = operator.get("invoice_footer", "")
        terms = operator.get("terms_conditions", "")
        combined = ""
        if footer_text:
            combined += f"{footer_text}<br/><br/>"
        if terms:
            combined += terms
        else:
            combined += (
                "<b>Terms &amp; Conditions:</b><br/>"
                "1. Payment is due by the due date mentioned above.<br/>"
                "2. Late payments may attract additional charges.<br/>"
                "3. This is a computer-generated invoice and does not require signature."
            )
        elems.append(Paragraph(combined, self.styles["InvoiceSmallText"]))
        return elems

    def _build_logo(self, logo_url: Optional[str], max_width: float, max_height: float):
        if not logo_url:
            return None
        try:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            root_dir = os.path.dirname(backend_dir)
            backend_upload_dir = os.path.join(root_dir, "uploads")
            
            if logo_url.startswith(("http://", "https://")):
                with urlopen(logo_url, timeout=5) as resp:
                    content = resp.read()
                img = Image(io.BytesIO(content))
            elif logo_url.startswith("/api/uploads/") or logo_url.startswith("/uploads/"):
                filename = logo_url.rsplit("/", 1)[-1]
                # Search for the file in multiple locations
                candidate_paths = [
                    os.path.join(backend_upload_dir, filename),  # Primary: root /uploads
                    os.path.join(root_dir, "backend", "uploads", filename),  # Alternate: backend/uploads
                    os.path.join(root_dir, "frontend", "public", "uploads", filename),  # Legacy: frontend/public/uploads
                    f"/app/uploads/{filename}",  # Docker primary
                    f"/app/frontend/public/uploads/{filename}",  # Docker legacy
                ]
                
                local_path = None
                for path in candidate_paths:
                    if os.path.exists(path):
                        local_path = path
                        logger.info(f"Found logo at: {local_path}")
                        break
                
                if not local_path:
                    logger.warning(f"Logo file not found for {logo_url}. Searched paths: {candidate_paths}")
                    return None
                    
                img = Image(local_path)
            elif logo_url.startswith("/"):
                root = os.path.join(root_dir, "frontend", "public")
                img = Image(os.path.join(root, logo_url.lstrip("/").replace("/", os.sep)))
            else:
                img = Image(logo_url)
            img._restrictSize(max_width, max_height)
            return img
        except Exception as exc:
            logger.warning(f"Failed to load invoice logo: {exc}")
            return None

    # ── Modern Template ────────────────────────────────────────────────────────

    def _generate_modern_invoice(self, invoice, operator, subscriber, plan, qr_b64) -> bytes:
        buffer = io.BytesIO()
        page_w, page_h = A4

        def draw_background(c, doc):
            """Draw full-width teal header band on every page."""
            c.saveState()
            c.setFillColor(MODERN_PRIMARY)
            c.rect(0, page_h - 100, page_w, 100, fill=1, stroke=0)
            # Subtle accent bar at bottom
            c.setFillColor(MODERN_ACCENT)
            c.rect(0, 0, page_w, 4, fill=1, stroke=0)
            c.restoreState()

        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=22*mm, leftMargin=22*mm,
            topMargin=108,  # below header band
            bottomMargin=22*mm,
            onFirstPage=draw_background,
            onLaterPages=draw_background,
        )

        elems = []
        elems.extend(self._modern_title_block(operator, invoice))
        elems.extend(self._modern_party_row(operator, subscriber, invoice))
        elems.extend(self._modern_items(invoice, plan))
        elems.extend(self._modern_summary(invoice))
        if qr_b64:
            elems.extend(self._build_qr_section(qr_b64))
        if self._is_visible(operator, "show_bank_details") and operator.get("bank_account_number"):
            elems.extend(self._build_bank_details_modern(operator))
        elems.extend(self._modern_footer(operator))

        doc.build(elems)
        buffer.seek(0)
        return buffer.getvalue()

    def _modern_title_block(self, operator, invoice):
        """The content that sits inside the teal header band (drawn via onFirstPage)."""
        elems = []
        # Company name + "TAX INVOICE" on the same row (already inside margin)
        row = [[
            Paragraph(f"<b>{operator.get('company_name', 'Company')}</b>",
                      self.styles["ModernTitle"]),
            Paragraph(
                f"<b>TAX INVOICE</b><br/>"
                f"<font size='9' color='#99f6e4'>#{invoice.get('invoice_number', '')}</font>",
                ParagraphStyle("_mt_inv", parent=self.styles["ModernTitle"],
                               alignment=TA_RIGHT, fontSize=18)
            )
        ]]
        t = Table(row, colWidths=[260, 215])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        # Push block UP into the header band using negative space trick
        elems.append(Spacer(1, -80))
        elems.append(t)
        elems.append(Spacer(1, 10))
        return elems

    def _modern_party_row(self, operator, subscriber, invoice):
        """Two info boxes side-by-side: Bill From | Bill To + Invoice Meta."""
        elems = []

        from_lines = [
            Paragraph("FROM", self.styles["ModernLabel"]),
            Paragraph(operator.get("owner_name", ""), self.styles["ModernValue"]),
        ]
        if self._is_visible(operator, "show_company_phone"):
            from_lines.append(Paragraph(operator.get("phone", ""), self.styles["ModernSmall"]))
        if self._is_visible(operator, "show_company_email"):
            from_lines.append(Paragraph(operator.get("email", ""), self.styles["ModernSmall"]))
        if operator.get("gst_number"):
            from_lines.append(Paragraph(f"GSTIN: {operator['gst_number']}", self.styles["ModernSmall"]))
        if operator.get("company_address") and self._is_visible(operator, "show_company_address"):
            from_lines.append(Paragraph(operator["company_address"], self.styles["ModernSmall"]))

        to_lines = [
            Paragraph("BILL TO", self.styles["ModernLabel"]),
            Paragraph(f"<b>{subscriber.get('name', '')}</b>", self.styles["ModernValue"]),
        ]
        if subscriber.get("whatsapp_number") and self._is_visible(operator, "show_subscriber_phone"):
            to_lines.append(Paragraph(subscriber["whatsapp_number"], self.styles["ModernSmall"]))
        if subscriber.get("email") and self._is_visible(operator, "show_subscriber_email"):
            to_lines.append(Paragraph(subscriber["email"], self.styles["ModernSmall"]))
        if subscriber.get("address") and self._is_visible(operator, "show_subscriber_address"):
            to_lines.append(Paragraph(subscriber["address"], self.styles["ModernSmall"]))

        meta_lines = [
            Paragraph("INVOICE DETAILS", self.styles["ModernLabel"]),
            Paragraph(f"Date: {self._fmt(invoice.get('created_at'))}", self.styles["ModernSmall"]),
            Paragraph(f"Due: {self._fmt(invoice.get('due_date'))}", self.styles["ModernSmall"]),
            Paragraph(
                f"Status: <b>{invoice.get('status', '').upper()}</b>",
                self.styles["ModernSmall"]
            ),
        ]

        def _stack(items):
            """Build mini inner table from a list of paragraphs."""
            return Table([[p] for p in items],
                         colWidths=[145],
                         style=[("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("TOPPADDING",    (0, 0), (-1, -1), 2),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 2)])

        row = [[_stack(from_lines), _stack(to_lines), _stack(meta_lines)]]
        outer = Table(row, colWidths=[155, 155, 155])
        outer.setStyle(TableStyle([
            ("VALIGN",         (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND",     (0, 0), (-1, -1), MODERN_BG_LIGHT),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
            ("BOX",            (0, 0), (-1, -1), 0.8, MODERN_ACCENT),
            ("INNERGRID",      (0, 0), (-1, -1), 0.4, colors.HexColor("#ccfbf1")),
            ("TOPPADDING",     (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 8),
            ("LEFTPADDING",    (0, 0), (-1, -1), 10),
        ]))
        elems.append(outer)
        elems.append(Spacer(1, 16))
        return elems

    def _modern_items(self, invoice, plan):
        elems = []
        elems.append(Paragraph("SERVICES", self.styles["ModernSection"]))
        elems.append(HRFlowable(width="100%", thickness=1.5,
                                color=MODERN_PRIMARY, spaceAfter=6))
        
        rows = [["#", "Description", "Period", "Amount"]]
        
        line_items = invoice.get("line_items", [])
        if not line_items:
            # Fallback for old invoices
            period = f"{self._fmt(invoice.get('service_start_date'))} – {self._fmt(invoice.get('service_end_date'))}"
            rows.append([
                "1",
                invoice.get("plan_name", plan.get("name", "Service")),
                period,
                f"₹{invoice.get('base_amount', 0):,.2f}"
            ])
        else:
            for idx, item in enumerate(line_items):
                if item.get("plan_name") == "Previous Pending":
                    till_date = self._fmt(item.get("service_start_date"))
                    period = f"Till {till_date}" if till_date else "Carried forward"
                else:
                    period = f"{self._fmt(item.get('service_start_date'))} – {self._fmt(item.get('service_end_date'))}"
                rows.append([
                    str(idx + 1),
                    item.get("plan_name", "Service"),
                    period,
                    f"₹{item.get('base_amount', 0):,.2f}"
                ])

        disc = invoice.get("discount", 0)
        if disc > 0:
            rows.append(["", "Discount", "", f"-₹{disc:,.2f}"])
        
        tax = invoice.get("tax_amount", 0)
        if tax > 0:
            rows.append([
                "", "GST / Taxes",
                "", f"₹{tax:,.2f}"
            ])

        col_w = [25, 205, 120, 115]
        t = Table(rows, colWidths=col_w)
        t.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",    (0, 0), (-1, 0), MODERN_PRIMARY),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 9),
            ("ALIGN",         (3, 0), (3, 0), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
            ("TOPPADDING",    (0, 0), (-1, 0), 9),
            # Body rows
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 9),
            ("TEXTCOLOR",     (0, 1), (-1, -1), MODERN_TEXT),
            ("ALIGN",         (3, 1), (3, -1), "RIGHT"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, MODERN_BG_LIGHT]),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
            ("TOPPADDING",    (0, 1), (-1, -1), 7),
            ("LINEBELOW",     (0, 0), (-1, -1), 0.4, CLASSIC_BORDER),
        ]))
        elems.append(t)
        elems.append(Spacer(1, 10))
        return elems

    def _modern_summary(self, invoice):
        elems = []
        final = invoice.get("final_amount", 0)
        t = Table(
            [["", Paragraph("<b>TOTAL AMOUNT DUE</b>", self.styles["ModernTotal"]),
              Paragraph(f"<b>₹{final:,.2f}</b>", self.styles["ModernTotal"])]],
            colWidths=[205, 150, 110]
        )
        t.setStyle(TableStyle([
            ("BACKGROUND",    (1, 0), (-1, -1), MODERN_BG_LIGHT),
            ("LINEABOVE",     (1, 0), (-1, 0), 1.5, MODERN_PRIMARY),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING",    (0, 0), (-1, -1), 12),
            ("ALIGN",         (2, 0), (2, 0), "RIGHT"),
        ]))
        elems.append(t)
        elems.append(Spacer(1, 16))
        return elems

    def _build_bank_details_modern(self, operator):
        elems = []
        elems.append(Paragraph("BANK DETAILS", self.styles["ModernSection"]))
        elems.append(HRFlowable(width="100%", thickness=1, color=MODERN_ACCENT, spaceAfter=4))
        bank_info = (
            f"Account Name: {operator.get('bank_account_name', '')} | "
            f"Account No: {operator.get('bank_account_number', '')} | "
            f"IFSC: {operator.get('bank_ifsc', '')} | "
            f"Bank: {operator.get('bank_name', '')}"
        )
        elems.append(Paragraph(bank_info, self.styles["ModernSmall"]))
        elems.append(Spacer(1, 12))
        return elems

    def _modern_footer(self, operator):
        elems = []
        elems.append(Spacer(1, 10))
        elems.append(HRFlowable(width="100%", thickness=0.5,
                                color=CLASSIC_BORDER, spaceAfter=6))
        footer_text = operator.get("invoice_footer", "")
        terms = operator.get("terms_conditions", "")
        combined = ""
        if footer_text:
            combined += f"{footer_text}  •  "
        if terms:
            combined += terms
        else:
            combined += (
                "Payment due by due date.  •  "
                "Late payments may attract charges.  •  "
                "Computer-generated invoice — no signature required."
            )
        elems.append(Paragraph(combined, self.styles["ModernSmall"]))
        return elems

    # ── Shared helpers ─────────────────────────────────────────────────────────

    def _build_qr_section(self, qr_base64: str) -> list:
        elems = []
        elems.append(Paragraph("SCAN TO PAY", self.styles["SectionHeader"]))
        try:
            qr_data = base64.b64decode(qr_base64)
            qr_image = Image(io.BytesIO(qr_data), width=100, height=100)
            elems.append(qr_image)
        except Exception as e:
            logger.error(f"Failed to add QR code: {e}")
        elems.append(Spacer(1, 6))
        elems.append(Paragraph("Scan QR code to pay instantly", self.styles["InvoiceSmallText"]))
        elems.append(Spacer(1, 12))
        return elems

    def _build_bank_details(self, operator: Dict) -> list:
        elems = []
        elems.append(Paragraph("BANK DETAILS", self.styles["SectionHeader"]))
        bank_info = (
            f"Account Name: {operator.get('bank_account_name', '')}<br/>"
            f"Account Number: {operator.get('bank_account_number', '')}<br/>"
            f"IFSC Code: {operator.get('bank_ifsc', '')}<br/>"
            f"Bank: {operator.get('bank_name', '')}"
        )
        elems.append(Paragraph(bank_info, self.styles["InvoiceBodyText"]))
        elems.append(Spacer(1, 12))
        return elems

    def _is_visible(self, operator: Dict[str, Any], field_key: str) -> bool:
        visible_fields = operator.get("visible_fields") or {}
        return visible_fields.get(field_key, True)

    def _fmt(self, val) -> str:
        if not val:
            return ""
        if isinstance(val, str):
            try:
                val = datetime.fromisoformat(val.replace("Z", "+00:00"))
            except Exception:
                return val
        if isinstance(val, datetime):
            return val.strftime("%d %b %Y")
        return str(val)
