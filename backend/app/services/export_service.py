"""Service for exporting bills to CSV and PDF formats."""

import csv
import io
from typing import List
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas

from app.models.billing import Bill


class ExportService:
    """Handle bill exports in various formats."""

    @staticmethod
    def export_bills_to_csv(bills: List[Bill]) -> str:
        """Export bills to CSV format.

        Args:
            bills: List of Bill objects to export

        Returns:
            str: CSV content as string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'Invoice Number',
            'Date',
            'Customer Name',
            'Customer Phone',
            'Status',
            'Subtotal (₹)',
            'Discount (₹)',
            'Tax (₹)',
            'Total (₹)',
            'Payment Method',
            'Created By'
        ])

        # Write data rows
        for bill in bills:
            # Get payment method (first payment if exists)
            payment_method = ''
            if bill.payments and len(bill.payments) > 0:
                payment_method = bill.payments[0].payment_method.value

            writer.writerow([
                bill.invoice_number or 'DRAFT',
                bill.created_at.strftime('%Y-%m-%d %H:%M'),
                bill.customer_name or '',
                bill.customer_phone or '',
                bill.status.value,
                f'{bill.subtotal / 100:.2f}',
                f'{bill.discount_amount / 100:.2f}',
                f'{bill.tax_amount / 100:.2f}',
                f'{bill.rounded_total / 100:.2f}',
                payment_method,
                bill.created_by
            ])

        return output.getvalue()

    @staticmethod
    def export_bills_to_pdf(
        bills: List[Bill],
        salon_name: str = "SalonOS",
        date_range: str = None
    ) -> bytes:
        """Export bills to PDF format.

        Args:
            bills: List of Bill objects to export
            salon_name: Name of salon for header
            date_range: Optional date range string for title

        Returns:
            bytes: PDF content as bytes
        """
        buffer = io.BytesIO()

        # Create PDF with landscape orientation for better table fit
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.5*inch
        )

        # Container for PDF elements
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_text = f"{salon_name} - Bills Report"
        if date_range:
            title_text += f"\n{date_range}"
        title = Paragraph(title_text, styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.25*inch))

        # Summary stats
        total_bills = len(bills)
        total_revenue = sum(bill.rounded_total for bill in bills if bill.status.value == 'posted')
        summary = Paragraph(
            f"<b>Total Transactions:</b> {total_bills} | "
            f"<b>Total Revenue:</b> ₹{total_revenue / 100:,.2f}",
            styles['Normal']
        )
        elements.append(summary)
        elements.append(Spacer(1, 0.25*inch))

        # Table data
        data = [[
            'Invoice #',
            'Date',
            'Customer',
            'Status',
            'Subtotal',
            'Discount',
            'Tax',
            'Total',
        ]]

        for bill in bills:
            data.append([
                bill.invoice_number or 'DRAFT',
                bill.created_at.strftime('%Y-%m-%d\n%H:%M'),
                (bill.customer_name or 'Walk-in')[:20],  # Truncate long names
                bill.status.value.title(),
                f'₹{bill.subtotal / 100:.2f}',
                f'₹{bill.discount_amount / 100:.2f}',
                f'₹{bill.tax_amount / 100:.2f}',
                f'₹{bill.rounded_total / 100:.2f}',
            ])

        # Create table
        table = Table(data, colWidths=[
            1.2*inch,  # Invoice
            1*inch,    # Date
            1.5*inch,  # Customer
            0.8*inch,  # Status
            0.9*inch,  # Subtotal
            0.9*inch,  # Discount
            0.9*inch,  # Tax
            1*inch,    # Total
        ])

        # Style the table
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),  # Right-align amounts
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))

        elements.append(table)

        # Add footer with generation timestamp
        elements.append(Spacer(1, 0.25*inch))
        footer = Paragraph(
            f"<i>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>",
            styles['Normal']
        )
        elements.append(footer)

        # Build PDF
        doc.build(elements)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes
