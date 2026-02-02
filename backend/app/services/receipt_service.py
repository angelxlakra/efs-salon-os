"""Receipt generation service for thermal printers (80mm).

This module generates PDF receipts optimized for 80mm thermal printers
like TVS RP3230, reading configuration from salon settings.
"""

from io import BytesIO
from typing import Optional
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.orm import Session

from app.models.billing import Bill
from app.models.settings import SalonSettings

# Register DejaVu fonts for Unicode support (including ₹ symbol)
try:
    # Try Alpine Linux path first
    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/ttf-dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/ttf-dejavu/DejaVuSans-Bold.ttf'))
    UNICODE_FONT = 'DejaVuSans'
    UNICODE_FONT_BOLD = 'DejaVuSans-Bold'
except:
    try:
        # Try direct filename (for systems with fonts in PATH)
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
        UNICODE_FONT = 'DejaVuSans'
        UNICODE_FONT_BOLD = 'DejaVuSans-Bold'
    except:
        # Fallback to Helvetica if DejaVu not available
        UNICODE_FONT = 'Helvetica'
        UNICODE_FONT_BOLD = 'Helvetica-Bold'


class ReceiptService:
    """Service for generating thermal printer receipts."""

    # 80mm thermal printer page size (80mm width x variable height)
    THERMAL_WIDTH = 80 * mm  # 80mm
    THERMAL_HEIGHT = 297 * mm  # A4 height, can be trimmed

    @staticmethod
    def format_currency(amount_paise: int, show_symbol: bool = True) -> str:
        """Format currency for thermal printer compatibility.

        Args:
            amount_paise: Amount in paise (1 rupee = 100 paise)
            show_symbol: Whether to include the Rs. prefix (default: True)

        Returns:
            Formatted string like "Rs. 1234.00" or "1234.00" (no comma separator)
        """
        rupees = amount_paise / 100
        if show_symbol:
            # Use Rs. with non-breaking space for reliable rendering
            return f"Rs.\u00a0{rupees:.2f}"
        else:
            # Just the amount, no symbol
            return f"{rupees:.2f}"

    @staticmethod
    def generate_receipt_pdf(bill: Bill, db: Optional[Session] = None) -> BytesIO:
        """Generate PDF receipt for 80mm thermal printer.

        Optimized for TVS RP3230 and similar 80mm thermal printers.
        Uses salon settings for business information and customization.

        Args:
            bill: Bill model instance with loaded items and customer
            db: Optional database session for loading settings

        Returns:
            BytesIO: PDF file stream optimized for 80mm thermal printing
        """
        buffer = BytesIO()

        # Load salon settings if db session provided
        settings = None
        if db:
            settings = db.query(SalonSettings).first()

        # Create document with 80mm width (thermal printer)
        doc = SimpleDocTemplate(
            buffer,
            pagesize=(ReceiptService.THERMAL_WIDTH, ReceiptService.THERMAL_HEIGHT),
            rightMargin=3 * mm,
            leftMargin=3 * mm,
            topMargin=3 * mm,
            bottomMargin=5 * mm
        )

        elements = []
        styles = getSampleStyleSheet()

        # ==================== STYLES ====================

        # Salon name - large and bold
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=16,
            fontName=UNICODE_FONT_BOLD,
            spaceAfter=2,
            leading=18,
            textColor=colors.black
        )

        # Tagline (removed - not used in receipt)

        # Address and contact
        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=8,
            fontName=UNICODE_FONT,
            spaceAfter=1,
            leading=9,
            textColor=colors.HexColor('#333333')
        )

        # Custom header/footer messages
        message_style = ParagraphStyle(
            'Message',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=8,
            fontName=UNICODE_FONT,
            spaceAfter=1,
            leading=10,
            textColor=colors.HexColor('#555555')
        )

        # Invoice label
        invoice_label_style = ParagraphStyle(
            'InvoiceLabel',
            parent=styles['Normal'],
            fontSize=10,
            fontName=UNICODE_FONT_BOLD,
            alignment=TA_LEFT,
            textColor=colors.black
        )

        # ==================== HEADER ====================

        salon_name = settings.salon_name if settings else "SalonOS"
        elements.append(Paragraph(salon_name, title_style))

        # Address lines
        if settings:
            if settings.salon_address:
                elements.append(Paragraph(settings.salon_address, info_style))

            city_state = []
            if settings.salon_city:
                city_state.append(settings.salon_city)
            if settings.salon_state:
                city_state.append(settings.salon_state)
            if city_state:
                elements.append(Paragraph(", ".join(city_state), info_style))

            if settings.salon_pincode:
                elements.append(Paragraph(f"PIN: {settings.salon_pincode}", info_style))
        else:
            elements.append(Paragraph("123 Main Street, City, State", info_style))

        # Contact
        if settings and settings.contact_phone:
            elements.append(Paragraph(f"Ph: {settings.contact_phone}", info_style))
        else:
            elements.append(Paragraph("Ph: +91 98765 43210", info_style))

        # GSTIN (if enabled)
        if settings and settings.receipt_show_gstin and settings.gstin:
            elements.append(Paragraph(f"GSTIN: {settings.gstin}", info_style))

        # Custom header message
        if settings and settings.receipt_header_text:
            elements.append(Spacer(1, 2 * mm))
            elements.append(Paragraph(settings.receipt_header_text, message_style))

        # Separator
        elements.append(Spacer(1, 3 * mm))
        sep_style = ParagraphStyle('Sep', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)

        # ==================== INVOICE INFO ====================

        invoice_label = "TAX INVOICE" if bill.status.value == "posted" else "DRAFT BILL"
        invoice_number = bill.invoice_number or "DRAFT"
        invoice_date = bill.created_at.strftime("%d/%m/%Y %I:%M %p")

        # Create clean invoice info table
        invoice_data = []
        invoice_data.append([
            Paragraph(invoice_label, invoice_label_style),
            Paragraph(f"<b>#{invoice_number}</b>", ParagraphStyle('InvNum', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT))
        ])
        invoice_data.append([
            Paragraph("Date:", ParagraphStyle('Label', parent=styles['Normal'], fontSize=8)),
            Paragraph(invoice_date, ParagraphStyle('Value', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
        ])

        if bill.customer_name:
            invoice_data.append([
                Paragraph("Customer:", ParagraphStyle('Label', parent=styles['Normal'], fontSize=8)),
                Paragraph(bill.customer_name, ParagraphStyle('Value', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
            ])
        if bill.customer_phone:
            invoice_data.append([
                Paragraph("Phone:", ParagraphStyle('Label', parent=styles['Normal'], fontSize=8)),
                Paragraph(bill.customer_phone, ParagraphStyle('Value', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
            ])

        invoice_table = Table(invoice_data, colWidths=[37 * mm, 37 * mm])
        invoice_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(invoice_table)

        # Separator
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph("-" * 48, sep_style))
        elements.append(Spacer(1, 2 * mm))

        # ==================== ITEMS TABLE ====================

        # Header - short labels to prevent wrapping
        items_data = [[
            Paragraph("<b>Item</b>", ParagraphStyle('H', parent=styles['Normal'], fontSize=8)),
            Paragraph("<b>Qty</b>", ParagraphStyle('H', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)),
            Paragraph("<b>Price</b>", ParagraphStyle('H', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT)),
            Paragraph("<b>Amount</b>", ParagraphStyle('H', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT))
        ]]

        # Items
        for item in bill.items:
            item_name = item.item_name
            if len(item_name) > 26:
                item_name = item_name[:23] + "..."

            items_data.append([
                Paragraph(item_name, ParagraphStyle('Item', parent=styles['Normal'], fontSize=8)),
                Paragraph(str(item.quantity), ParagraphStyle('Qty', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)),
                Paragraph(ReceiptService.format_currency(item.base_price, show_symbol=False), ParagraphStyle('Price', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)),
                Paragraph(ReceiptService.format_currency(item.line_total, show_symbol=False), ParagraphStyle('Amt', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
            ])

        items_table = Table(items_data, colWidths=[26 * mm, 10 * mm, 19 * mm, 19 * mm])
        items_table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F5F5')),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ('TOPPADDING', (0, 0), (-1, 0), 3),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),

            # Body styling
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ]))
        elements.append(items_table)

        elements.append(Spacer(1, 2 * mm))

        # ==================== TOTALS ====================

        totals_data = []

        # Subtotal
        totals_data.append([
            Paragraph("Subtotal:", ParagraphStyle('TL', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)),
            Paragraph(ReceiptService.format_currency(bill.subtotal), ParagraphStyle('TV', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
        ])

        # Discount
        if bill.discount_amount > 0:
            # Calculate discount percentage
            discount_pct = 0.0
            if bill.subtotal > 0:
                discount_pct = (bill.discount_amount / bill.subtotal) * 100

            discount_label = f"Discount ({discount_pct:.1f}%):" if discount_pct > 0 else "Discount:"

            totals_data.append([
                Paragraph(discount_label, ParagraphStyle('TL', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, textColor=colors.HexColor('#E53935'))),
                Paragraph(f"- {ReceiptService.format_currency(bill.discount_amount)}", ParagraphStyle('TV', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, textColor=colors.HexColor('#E53935')))
            ])

        # Tax breakdown (only show if receipt_show_gstin is enabled)
        if settings and settings.receipt_show_gstin:
            cgst = bill.tax_amount / 2
            sgst = bill.tax_amount / 2
            totals_data.append([
                Paragraph("CGST (9%):", ParagraphStyle('TL', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)),
                Paragraph(ReceiptService.format_currency(int(cgst)), ParagraphStyle('TV', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
            ])
            totals_data.append([
                Paragraph("SGST (9%):", ParagraphStyle('TL', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)),
                Paragraph(ReceiptService.format_currency(int(sgst)), ParagraphStyle('TV', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
            ])

        # Round off
        round_off = bill.rounded_total - bill.total_amount
        if abs(round_off) >= 1:
            sign = "+" if round_off > 0 else ""
            totals_data.append([
                Paragraph("Round Off:", ParagraphStyle('TL', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT, textColor=colors.HexColor('#666666'))),
                Paragraph(f"{sign} {ReceiptService.format_currency(abs(round_off))}", ParagraphStyle('TV', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT, textColor=colors.HexColor('#666666')))
            ])

        totals_table = Table(totals_data, colWidths=[46 * mm, 28 * mm])
        totals_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
        ]))
        elements.append(totals_table)

        # Grand total - bold and larger
        elements.append(Spacer(1, 1 * mm))
        grand_total_data = [[
            Paragraph("<b>TOTAL:</b>", ParagraphStyle('GTL', parent=styles['Normal'], fontSize=10, fontName=UNICODE_FONT_BOLD, alignment=TA_RIGHT)),
            Paragraph(f"<b>{ReceiptService.format_currency(bill.rounded_total)}</b>", ParagraphStyle('GTV', parent=styles['Normal'], fontSize=10, fontName=UNICODE_FONT_BOLD, alignment=TA_RIGHT))
        ]]
        grand_total_table = Table(grand_total_data, colWidths=[46 * mm, 28 * mm])
        grand_total_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.black),
            ('TOPPADDING', (0, 0), (-1, 0), 3),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ]))
        elements.append(grand_total_table)

        # ==================== PAYMENT INFO ====================

        if bill.status.value == "posted" and bill.payments:
            elements.append(Spacer(1, 2 * mm))
            elements.append(Paragraph("-" * 48, sep_style))
            elements.append(Spacer(1, 2 * mm))

            payment_data = [[
                Paragraph("<b>Payment Method</b>", ParagraphStyle('PH', parent=styles['Normal'], fontSize=8)),
                Paragraph("<b>Amount</b>", ParagraphStyle('PH', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
            ]]

            for payment in bill.payments:
                payment_data.append([
                    Paragraph(payment.payment_method.value.upper(), ParagraphStyle('PM', parent=styles['Normal'], fontSize=8)),
                    Paragraph(ReceiptService.format_currency(payment.amount, show_symbol=False), ParagraphStyle('PA', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
                ])

            payment_table = Table(payment_data, colWidths=[44 * mm, 30 * mm])
            payment_table.setStyle(TableStyle([
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#CCCCCC')),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(payment_table)

        # ==================== FOOTER ====================

        elements.append(Spacer(1, 4 * mm))

        # Footer message
        footer_text = "Thank you for your visit!"
        if settings and settings.receipt_footer_text:
            footer_text = settings.receipt_footer_text

        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=9,
            fontName=UNICODE_FONT_BOLD,
            spaceAfter=2,
            leading=11
        )
        elements.append(Paragraph(footer_text, footer_style))

        # Terms and conditions
        if settings and settings.invoice_terms:
            elements.append(Spacer(1, 2 * mm))
            terms_style = ParagraphStyle(
                'Terms',
                parent=styles['Normal'],
                fontSize=6,
                fontName=UNICODE_FONT,
                alignment=TA_CENTER,
                leading=7,
                textColor=colors.HexColor('#666666')
            )
            elements.append(Paragraph(settings.invoice_terms, terms_style))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
