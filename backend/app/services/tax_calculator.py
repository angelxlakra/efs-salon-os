"""Tax calculation utilities for GST computation.

  This module provides functionality to calculate GST (CGST/SGST) breakdown
  from tax-inclusive prices and handle rounding operations for billing.

  All catalog prices in SalonOS are tax-inclusive at 18% GST (9% CGST + 9% SGST).
  This calculator extracts the tax components from the inclusive price.

  Example:
      Tax-inclusive price: ₹1,180 (in paise: 118000)
      Taxable value: ₹1,000 (100000 paise)
      CGST (9%): ₹90 (9000 paise)
      SGST (9%): ₹90 (9000 paise)
  """


from decimal import Decimal, ROUND_HALF_UP
from app.config import settings


class TaxCalculator:
    """Calculate GST breakdown from tax-inclusive prices.

      All prices in the salon catalog are tax-inclusive. This class provides
      methods to extract the taxable value and calculate CGST/SGST components.

      GST Rate: 18% (9% CGST + 9% SGST)
      Formula: taxable_value = inclusive_price / 1.18

      All amounts are in paise (1 rupee = 100 paise) to avoid floating-point
      precision issues. Decimal arithmetic is used for accurate calculations.

      Attributes:
          GST_RATE: Total GST rate as Decimal (0.18)
          CGST_RATE: Central GST rate as Decimal (0.09)
          SGST_RATE: State GST rate as Decimal (0.09)
      """

    GST_RATE = settings.gst_rate
    CGST_RATE = GST_RATE / Decimal("2")
    SGST_RATE = GST_RATE / Decimal("2")

    @classmethod
    def calculate_tax_breakdown(cls, inclusive_price: int) -> dict:
        """Calculate tax breakdown from tax-inclusive price.

      Extracts the taxable value, CGST, and SGST from a tax-inclusive price.
      Uses Decimal arithmetic for precision and rounds to nearest paise.

      Args:
          inclusive_price: Price in paise including 18% GST (integer).
                          Example: ₹750.00 = 75000 paise

      Returns:
          dict: Tax breakdown with the following keys:
              - taxable_value (int): Base price before tax in paise
              - cgst (int): Central GST amount in paise (9%)
              - sgst (int): State GST amount in paise (9%)
              - total_tax (int): Combined CGST + SGST in paise

      Example:
          >>> TaxCalculator.calculate_tax_breakdown(118000)
          {
              'taxable_value': 100000,
              'cgst': 9000,
              'sgst': 9000,
              'total_tax': 18000
          }

      Note:
          All values are rounded to nearest paise using ROUND_HALF_UP.
      """

        if inclusive_price < 0:
            raise ValueError("Price cannot be negative")

        price = Decimal(inclusive_price)
        taxable_value = price / (Decimal("1") + cls.GST_RATE)
        total_tax = price - taxable_value
        cgst = cls.CGST_RATE * taxable_value
        sgst = cls.SGST_RATE * taxable_value

        return {
            "taxable_value": int(taxable_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
            "total_tax": int(total_tax.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
            "cgst": int(cgst.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
            "sgst": int(sgst.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        }

    @classmethod
    def round_to_rupee(cls, amount_paise: int) -> tuple[int, int]:
        """
            Round amount to nearest rupee.

            Bills are rounded to the nearest rupee for customer convenience.
            This method returns both the rounded amount and the adjustment made.

            Args:
                amount_paise: Amount in paise to be rounded (integer).
            
            Example: 147034 paise = ₹1470.34

            Returns:
                tuple[int, int]: A tuple containing:
                    - rounded_paise (int): Amount rounded to nearest rupee in paise
                    - adjustment (int): Rounding adjustment in paise (can be negative)

            Example:
                >>> TaxCalculator.round_to_rupee(147034)
                (147000, -34)

                >>> TaxCalculator.round_to_rupee(147067)
                (147100, 33)

      Note:
          Uses ROUND_HALF_UP: 0.50 and above rounds up, below 0.50 rounds down.
          Adjustment is stored in the bill for audit trail.
      """

        if amount_paise < 0:
            raise ValueError("Amount cannot be negative")

        amount_rupees = Decimal(amount_paise) / Decimal("100")
        rounded_rupees = amount_rupees.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        rounded_paise = int(rounded_rupees * 100)
        adjustment = rounded_paise - amount_paise

        return (rounded_paise, adjustment)
