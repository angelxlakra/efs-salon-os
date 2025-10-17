"""
Utility functions for ID generation, invoice numbers, etc.
"""
from datetime import datetime

from ulid import ULID
import pytz

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

def generate_ulid() -> str:
    """Generate a new ULID string"""
    return str(ULID())

def generate_invoice_number() -> str:
    """
    Generate invoice number in format: SAL-YY-NNNN
    Example: SAL-25-0001
    
    Note: This is a placeholder. Actual implementation will use
    PostgreSQL sequence in the migration.
    """
    now = datetime.now(IST)
    year = now.strftime("%y")
    # This will be replaced by PostgreSQL function
    return f"SAL-{year}-0001"

def generate_ticket_number() -> str:
    """
    Generate ticket number in format: TKT-YYMMDD-###
    Example: TKT-251015-001
    
    Note: This is a placeholder. Actual implementation will use
    PostgreSQL sequence in the migration.
    """
    now = datetime.now(IST)
    date_str = now.strftime("%y%m%d")
    # This will be replaced by PostgreSQL function
    return f"TKT-{date_str}-001"

def paise_to_rupees(paise: int) -> float:
    """Convert paise (integer) to rupees (float)"""
    return paise / 100.0

def rupees_to_paise(rupees: float) -> int:
    """Convert rupees (float) to paise (integer)"""
    return int(round(rupees * 100))

def calculate_gst(
    inclusive_amount: int,
    gst_rate: float = 18.0
) -> tuple[int, int, int]:
    """
    Calculate GST components from tax-inclusive amount.

    All catalog prices in SalonOS are tax-inclusive.
    This extracts the tax amount from the inclusive price.

    Formula: tax = (price * rate) / (100 + rate)

    Args:
        inclusive_amount: Tax-inclusive amount in paise
        gst_rate: GST rate percentage (default: 18%)

    Returns:
        tuple: (cgst_amount, sgst_amount, total_tax) all in paise

    Example:
        >>> calculate_gst(11800)  # ₹118 inclusive
        (900, 900, 1800)  # ₹9 CGST + ₹9 SGST = ₹18 total tax
    """
    total_tax = int(round((inclusive_amount * gst_rate) / (100 + gst_rate)))

    # Split equally between CGST and SGST
    cgst = total_tax // 2
    sgst = total_tax - cgst  # Handle odd amounts

    return cgst, sgst, total_tax

def round_to_nearest_rupee(paise: int) -> tuple[int, int]:
    """
    Round amount to nearest rupee and calculate adjustment.

    Args:
        paise: Amount in paise

    Returns:
        tuple: (rounded_paise, adjustment)
            - rounded_paise: Amount rounded to nearest ₹1
            - adjustment: Difference (positive if rounded up, negative if rounded down)

    Example:
        >>> round_to_nearest_rupee(34965)  # ₹349.65
        (35000, 35)  # Rounded to ₹350, adjustment +₹0.35

        >>> round_to_nearest_rupee(34925)  # ₹349.25
        (34900, -25)  # Rounded to ₹349, adjustment -₹0.25
    """
    rounded = round(paise / 100) * 100
    adjustment = rounded - paise
    return int(rounded), int(adjustment)