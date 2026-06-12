"""Receipt generation service for thermal printers (80mm).

This module generates PDF receipts optimized for 80mm thermal printers
like TVS RP3230, reading configuration from salon settings.
"""

from io import BytesIO
from typing import Optional
from datetime import datetime
import pytz

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.orm import Session

from app.models.billing import (
    Bill,
    BillClass,
    BillItemType,
    BillType,
    PaymentMethod as PaymentMethodEnum,
)
from app.models.settings import SalonSettings
from app.utils import IST

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
    def _format_rate(rate_percent: float) -> str:
        """Format a tax rate percentage, trimming trailing zeros (2.5% / 9%)."""
        return f"{rate_percent:g}%"

    @staticmethod
    def _split_payments(
        payments: list,
    ) -> tuple[list, int]:
        """Split payments into regular and package-redemption categories.

        Returns:
            (regular_payments, package_redemption_total_paise)
        """
        regular = [p for p in payments if p.payment_method != PaymentMethodEnum.PACKAGE_REDEMPTION]
        redemption_total = sum(p.amount for p in payments if p.payment_method == PaymentMethodEnum.PACKAGE_REDEMPTION)
        return regular, redemption_total

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

        # GST split-billing bills (service/product class) get a Rule 46 compliant
        # tax-invoice layout; mixed_legacy bills keep the original layout exactly.
        # Treat as a GST tax invoice only when the bill actually carries GST.
        # A service bill for an unregistered salon has no GST, so it prints as a
        # plain receipt (no TAX INVOICE title, GSTIN, tax lines or declarations).
        has_gst = ((bill.cgst_amount or 0) + (bill.sgst_amount or 0)) != 0
        is_gst_bill = bill.bill_class in (BillClass.SERVICE, BillClass.PRODUCT) and has_gst
        is_credit_note = bill.bill_type == BillType.CREDIT_NOTE

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
            textColor=colors.black
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
            textColor=colors.black
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

        # GSTIN — mandatory and prominent on tax invoices; opt-in on legacy bills
        if is_gst_bill and settings and settings.gstin:
            gstin_style = ParagraphStyle(
                'Gstin',
                parent=info_style,
                fontSize=9,
                fontName=UNICODE_FONT_BOLD,
            )
            elements.append(Paragraph(f"GSTIN: {settings.gstin}", gstin_style))
        elif settings and settings.receipt_show_gstin and settings.gstin:
            elements.append(Paragraph(f"GSTIN: {settings.gstin}", info_style))

        # Custom header message
        if settings and settings.receipt_header_text:
            elements.append(Spacer(1, 2 * mm))
            elements.append(Paragraph(settings.receipt_header_text, message_style))

        # Separator
        elements.append(Spacer(1, 3 * mm))
        sep_style = ParagraphStyle('Sep', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)

        # ==================== INVOICE INFO ====================

        # Always a clean customer-facing title — no internal "draft" wording.
        # A pre-payment bill is still titled TAX INVOICE; it simply has no
        # invoice number until the sale is posted (the number row is omitted
        # below until then).
        if is_gst_bill:
            invoice_label = "CREDIT NOTE" if is_credit_note else "TAX INVOICE"
            # Document title — centered and prominent (Rule 46)
            doc_title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Normal'],
                alignment=TA_CENTER,
                fontSize=11,
                fontName=UNICODE_FONT_BOLD,
                spaceAfter=2,
            )
            elements.append(Paragraph(invoice_label, doc_title_style))
            elements.append(Spacer(1, 1 * mm))
        else:
            invoice_label = "INVOICE"

        # Convert to IST for display (handle both timezone-aware and naive datetimes)
        if bill.created_at.tzinfo is None:
            # If naive, assume UTC and convert to IST
            bill_time_ist = pytz.utc.localize(bill.created_at).astimezone(IST)
        else:
            # If aware, convert to IST
            bill_time_ist = bill.created_at.astimezone(IST)

        invoice_date = bill_time_ist.strftime("%d/%m/%Y %I:%M %p")

        # Create clean invoice info table. The invoice-number row is shown only
        # once a number has been assigned (at posting) — a pre-payment bill
        # carries no number rather than an internal "#DRAFT" placeholder.
        invoice_data = []
        if bill.invoice_number:
            invoice_data.append([
                Paragraph("Invoice No:" if is_gst_bill else invoice_label, invoice_label_style),
                Paragraph(f"<b>#{bill.invoice_number}</b>", ParagraphStyle('InvNum', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT))
            ])
        if is_gst_bill and is_credit_note and bill.original_bill and bill.original_bill.invoice_number:
            invoice_data.append([
                Paragraph("Against Invoice:", ParagraphStyle('Label', parent=styles['Normal'], fontSize=8)),
                Paragraph(f"#{bill.original_bill.invoice_number}", ParagraphStyle('Value', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
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

            # Sub-note rows for package items
            note_style = ParagraphStyle('Note', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor('#555555'))

            if item.item_type == BillItemType.PACKAGE_SALE_LINE:
                # Note: this is a package sale — sub-services are included
                items_data.append([
                    Paragraph("  * Package sale", note_style),
                    Paragraph("", note_style),
                    Paragraph("", note_style),
                    Paragraph("", note_style),
                ])

            elif item.item_type == BillItemType.PACKAGE_REDEMPTION:
                # Note: this service is covered by a package
                items_data.append([
                    Paragraph("  * Paid via package", note_style),
                    Paragraph("", note_style),
                    Paragraph("", note_style),
                    Paragraph("", note_style),
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
                Paragraph(discount_label, ParagraphStyle('TL', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, textColor=colors.black)),
                Paragraph(f"- {ReceiptService.format_currency(bill.discount_amount)}", ParagraphStyle('TV', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, textColor=colors.black))
            ])

        # Tax breakdown — CGST and SGST shown as separate lines (Rule 46).
        if is_gst_bill:
            # Per-rate from the stored amounts; rate per half is 2.5% (service,
            # exclusive) or 9% (product, inclusive in MRP). Taxable value works
            # for both classes and credit notes: total minus tax.
            taxable_value = bill.total_amount - bill.tax_amount
            half_rate = 2.5 if bill.bill_class == BillClass.SERVICE else 9
            incl_note = " incl." if bill.bill_class == BillClass.PRODUCT else ""
            totals_data.append([
                Paragraph("Taxable Value:", ParagraphStyle('TL', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)),
                Paragraph(ReceiptService.format_currency(taxable_value), ParagraphStyle('TV', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
            ])
            totals_data.append([
                Paragraph(f"CGST @ {ReceiptService._format_rate(half_rate)}{incl_note}:", ParagraphStyle('TL', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)),
                Paragraph(ReceiptService.format_currency(bill.cgst_amount), ParagraphStyle('TV', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
            ])
            totals_data.append([
                Paragraph(f"SGST @ {ReceiptService._format_rate(half_rate)}{incl_note}:", ParagraphStyle('TL', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)),
                Paragraph(ReceiptService.format_currency(bill.sgst_amount), ParagraphStyle('TV', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
            ])
        elif settings and settings.receipt_show_gstin and bill.tax_amount:
            # Legacy inclusive-18% bills: keep the original CGST/SGST display.
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
            sign = "+" if round_off > 0 else "-"
            totals_data.append([
                Paragraph("Round Off:", ParagraphStyle('TL', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT, textColor=colors.black)),
                Paragraph(f"{sign} {ReceiptService.format_currency(abs(round_off))}", ParagraphStyle('TV', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT, textColor=colors.black))
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

        if bill.status.value == "posted":
            elements.append(Spacer(1, 2 * mm))
            elements.append(Paragraph("-" * 48, sep_style))
            elements.append(Spacer(1, 2 * mm))

            # Show payments if any
            if bill.payments:
                # Separate package redemption payments from regular payments.
                # PACKAGE_REDEMPTION rows are internal accounting entries; each redeemed
                # item already shows "Paid via package" in the items section.
                # We group them into a single summary line instead.
                regular_payments, package_redemption_total = ReceiptService._split_payments(bill.payments)

                payment_data = [[
                    Paragraph("<b>Payment Method</b>", ParagraphStyle('PH', parent=styles['Normal'], fontSize=8)),
                    Paragraph("<b>Amount</b>", ParagraphStyle('PH', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
                ]]

                for payment in regular_payments:
                    payment_data.append([
                        Paragraph(payment.payment_method.value.upper(), ParagraphStyle('PM', parent=styles['Normal'], fontSize=8)),
                        Paragraph(ReceiptService.format_currency(payment.amount, show_symbol=False), ParagraphStyle('PA', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
                    ])

                if package_redemption_total > 0:
                    payment_data.append([
                        Paragraph("PACKAGE REDEMPTION", ParagraphStyle('PM', parent=styles['Normal'], fontSize=8)),
                        Paragraph(ReceiptService.format_currency(package_redemption_total, show_symbol=False), ParagraphStyle('PA', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT))
                    ])

                payment_table = Table(payment_data, colWidths=[44 * mm, 30 * mm])
                payment_table.setStyle(TableStyle([
                    ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#CCCCCC')),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                elements.append(payment_table)

                # Include PACKAGE_REDEMPTION payments in total_paid — these are internal accounting
                # entries that offset the cost of redeemed services. The balance calculation is:
                #   pending = rounded_total - (cash/upi/card payments) - (package redemption payments)
                # This is correct: package-covered services are already "paid" by the package.
                total_paid = sum(payment.amount for payment in bill.payments)
                pending_balance = bill.rounded_total - total_paid

                if pending_balance > 0:
                    elements.append(Spacer(1, 2 * mm))
                    pending_data = [[
                        Paragraph("<b>PENDING BALANCE:</b>", ParagraphStyle('PendL', parent=styles['Normal'], fontSize=9, fontName=UNICODE_FONT_BOLD, alignment=TA_RIGHT, textColor=colors.black)),
                        Paragraph(f"<b>{ReceiptService.format_currency(pending_balance)}</b>", ParagraphStyle('PendV', parent=styles['Normal'], fontSize=9, fontName=UNICODE_FONT_BOLD, alignment=TA_RIGHT, textColor=colors.black))
                    ]]
                    pending_table = Table(pending_data, colWidths=[46 * mm, 28 * mm])
                    pending_table.setStyle(TableStyle([
                        ('TOPPADDING', (0, 0), (-1, 0), 2),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
                    ]))
                    elements.append(pending_table)
            else:
                # No payments - completely free or pending
                if bill.rounded_total > 0:
                    # Bill has amount but no payments - show pending
                    pending_style = ParagraphStyle(
                        'PendingFull',
                        parent=styles['Normal'],
                        fontSize=9,
                        fontName=UNICODE_FONT_BOLD,
                        alignment=TA_CENTER,
                        textColor=colors.black
                    )
                    elements.append(Paragraph(f"<b>FULL AMOUNT PENDING: {ReceiptService.format_currency(bill.rounded_total)}</b>", pending_style))
                else:
                    # Bill is zero or free
                    free_style = ParagraphStyle(
                        'Free',
                        parent=styles['Normal'],
                        fontSize=9,
                        fontName=UNICODE_FONT_BOLD,
                        alignment=TA_CENTER,
                        textColor=colors.black
                    )
                    elements.append(Paragraph("<b>COMPLIMENTARY SERVICE</b>", free_style))

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
                textColor=colors.black
            )
            elements.append(Paragraph(settings.invoice_terms, terms_style))

        # ==================== TAX-INVOICE DECLARATIONS (Rule 46) ====================

        if is_gst_bill:
            elements.append(Spacer(1, 3 * mm))
            declaration_style = ParagraphStyle(
                'Declaration',
                parent=styles['Normal'],
                fontSize=7,
                fontName=UNICODE_FONT,
                alignment=TA_LEFT,
                leading=9,
                textColor=colors.black,
            )
            elements.append(Paragraph(
                "Whether tax is payable under reverse charge: No",
                declaration_style,
            ))

            # Authorised signatory — leave vertical space for a signature
            elements.append(Spacer(1, 8 * mm))
            signatory_style = ParagraphStyle(
                'Signatory',
                parent=styles['Normal'],
                fontSize=8,
                fontName=UNICODE_FONT,
                alignment=TA_RIGHT,
                leading=9,
                textColor=colors.black,
            )
            elements.append(Paragraph("Authorised Signatory", signatory_style))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_group_receipt_pdf(bills: list, db: Optional[Session] = None) -> BytesIO:
        """Combine several bills into one multi-page PDF (one bill per page).

        For a GST split checkout the service bill and product bill print as
        separate pages of a single document — an 80mm thermal printer prints
        each page in turn on the continuous roll (feed/cut between pages), so
        the customer gets two distinct receipts from one print job. Reuses the
        single-bill renderer and concatenates the pages.
        """
        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()
        for bill in bills:
            single = ReceiptService.generate_receipt_pdf(bill, db)
            reader = PdfReader(single)
            for page in reader.pages:
                writer.add_page(page)

        out = BytesIO()
        writer.write(out)
        out.seek(0)
        return out
