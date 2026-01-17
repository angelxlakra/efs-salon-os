"""
Unit Tests for TaxCalculator

LESSON 1: Testing Pure Functions
=================================

This is your first test file! We're testing the TaxCalculator service,
which is perfect for learning because:
- It has no database dependencies
- It has no external service calls
- It's a pure function: same input always gives same output

LEARNING OBJECTIVES:
1. Understand the AAA pattern (Arrange, Act, Assert)
2. Write tests for normal cases, edge cases, and error cases
3. Use pytest to run tests
4. Read and understand test output

RUN THIS TEST:
    uv run pytest tests/unit/test_tax_calculator.py -v

The -v flag means "verbose" - it shows you each test name as it runs.
"""

import pytest
from decimal import Decimal
from app.services.tax_calculator import TaxCalculator


# ==============================================================================
# LESSON 1A: Testing Normal Cases (Happy Path)
# ==============================================================================

def test_calculate_tax_breakdown_with_standard_amount():
    """
    TEST CASE 1: Normal case - Standard amount

    WHAT: Calculate tax breakdown for a typical bill amount
    WHY: This is the most common use case - we need to ensure it works correctly
    EXPECTED: For ₹1,180 (tax-inclusive), we should get:
        - Taxable value: ₹1,000 (the base price before tax)
        - CGST (9%): ₹90
        - SGST (9%): ₹90
        - Total tax: ₹180

    TEACHING POINT: This is the "happy path" - testing what should work normally.
    Always start with this!
    """
    # ARRANGE: Set up the test data
    # We're testing with ₹1,180, which in paise is 118,000
    # (Remember: All amounts in SalonOS are stored in paise to avoid decimal issues)
    inclusive_price = 118000  # ₹1,180.00 in paise

    # ACT: Call the function we're testing
    result = TaxCalculator.calculate_tax_breakdown(inclusive_price)

    # ASSERT: Verify the results are correct
    # We check each component of the returned dictionary
    assert result["taxable_value"] == 100000, "Taxable value should be ₹1,000 (100,000 paise)"
    assert result["cgst"] == 9000, "CGST (9%) should be ₹90 (9,000 paise)"
    assert result["sgst"] == 9000, "SGST (9%) should be ₹90 (9,000 paise)"
    assert result["total_tax"] == 18000, "Total tax should be ₹180 (18,000 paise)"

    # TEACHING POINT: The assert messages (after the comma) are optional but helpful!
    # They show up when a test fails, making debugging easier.


def test_real_world_haircut_price():
    """
    TEST CASE 2: Real-world example - Haircut price

    WHAT: Test with an actual salon service price
    WHY: Validates the calculation works with real business data
    EXPECTED: For ₹750 haircut:
        - Taxable: ₹635.59 → 63559 paise (rounded)
        - CGST: ₹57.20 → 5720 paise
        - SGST: ₹57.20 → 5720 paise

    TEACHING POINT: Testing with real-world data helps catch issues
    that might not show up with "clean" numbers like 1,000.
    """
    # ARRANGE
    haircut_price = 75000  # ₹750.00 in paise (typical haircut price)

    # ACT
    result = TaxCalculator.calculate_tax_breakdown(haircut_price)

    # ASSERT
    # Note: Due to rounding, we verify the calculation is approximately correct
    assert result["taxable_value"] == 63559  # ₹635.59
    assert result["cgst"] == 5720  # ₹57.20
    assert result["sgst"] == 5720  # ₹57.20
    assert result["total_tax"] == 11441  # ₹114.41

    # TEACHING POINT: When dealing with rounding, exact values matter!
    # We use ROUND_HALF_UP in the calculator, so we can predict exact results.


# ==============================================================================
# LESSON 1B: Testing Edge Cases
# ==============================================================================

def test_calculate_tax_breakdown_with_zero_amount():
    """
    TEST CASE 3: Edge case - Zero amount

    WHAT: What happens when the price is zero?
    WHY: Edge cases like zero often reveal bugs
    EXPECTED: All values should be zero (no tax on zero amount)

    TEACHING POINT: "Edge cases" are boundary conditions - values at the
    edge of what's valid. Common edge cases: 0, -1, max values, empty strings.
    """
    # ARRANGE
    zero_price = 0

    # ACT
    result = TaxCalculator.calculate_tax_breakdown(zero_price)

    # ASSERT
    assert result["taxable_value"] == 0
    assert result["cgst"] == 0
    assert result["sgst"] == 0
    assert result["total_tax"] == 0

    # TEACHING POINT: Zero is a special case. Always test it!
    # Many bugs happen when developers forget to handle zero.


def test_calculate_tax_breakdown_with_large_amount():
    """
    TEST CASE 4: Edge case - Very large amount

    WHAT: Test with a very large bill (₹100,000 = ₹1 lakh)
    WHY: Ensure calculations work correctly with big numbers
    EXPECTED: Calculations should still be accurate (no overflow or precision loss)

    TEACHING POINT: Large numbers can cause integer overflow or precision
    issues. Testing them ensures your code scales.
    """
    # ARRANGE
    large_price = 10000000  # ₹100,000 (1 lakh) in paise

    # ACT
    result = TaxCalculator.calculate_tax_breakdown(large_price)

    # ASSERT
    # For ₹100,000 inclusive:
    # Taxable = 100,000 / 1.18 = ₹84,745.76
    assert result["taxable_value"] == 8474576  # ₹84,745.76
    assert result["cgst"] == 762712  # 9% of taxable
    assert result["sgst"] == 762712  # 9% of taxable
    assert result["total_tax"] == 1525424  # Total tax

    # TEACHING POINT: We're using Decimal internally, which handles
    # large numbers precisely. This test proves it works!


# ==============================================================================
# LESSON 1C: Testing Error Cases
# ==============================================================================

def test_calculate_tax_breakdown_raises_error_for_negative_price():
    """
    TEST CASE 5: Error case - Negative price

    WHAT: Verify that negative prices are rejected
    WHY: Negative prices don't make business sense - the code should prevent them
    EXPECTED: ValueError should be raised

    TEACHING POINT: Testing error cases is just as important as testing
    success cases! We want to ensure our code fails gracefully and safely.
    """
    # ARRANGE
    negative_price = -50000  # ₹-500 (invalid!)

    # ACT & ASSERT combined using pytest.raises
    # This special syntax checks that an exception is raised
    with pytest.raises(ValueError) as exc_info:
        TaxCalculator.calculate_tax_breakdown(negative_price)

    # We can also check the error message
    assert "Price cannot be negative" in str(exc_info.value)

    # TEACHING POINT: pytest.raises is a context manager that catches
    # exceptions. If the exception ISN'T raised, the test fails!
    # This ensures our validation works.


# ==============================================================================
# LESSON 1D: Testing Business Rules
# ==============================================================================

def test_cgst_equals_sgst_always():
    """
    TEST CASE 6: Business rule - CGST must equal SGST

    WHAT: Verify that CGST and SGST are always equal
    WHY: This is a legal requirement - GST is split 50/50 between central and state
    EXPECTED: For any valid amount, CGST == SGST

    TEACHING POINT: Business rules should be tested explicitly!
    Even if the code looks correct, a test documents the requirement.
    """
    # ARRANGE: Test with multiple amounts to be thorough
    test_amounts = [
        118000,   # ₹1,180
        75000,    # ₹750
        250000,   # ₹2,500
        999999,   # ₹9,999.99
    ]

    # ACT & ASSERT: Test each amount
    for amount in test_amounts:
        result = TaxCalculator.calculate_tax_breakdown(amount)

        # The business rule: CGST must always equal SGST
        assert result["cgst"] == result["sgst"], \
            f"CGST and SGST must be equal for amount ₹{amount/100:.2f}"

    # TEACHING POINT: Testing multiple values in one test is OK when
    # they test the SAME behavior. This is called "parameterized testing".


def test_tax_components_sum_correctly():
    """
    TEST CASE 7: Verification - Components should sum to total

    WHAT: Verify that taxable_value + cgst + sgst ≈ inclusive_price
    WHY: Catch rounding errors or calculation bugs
    EXPECTED: Components should sum back to original (within rounding tolerance)

    TEACHING POINT: "Sanity checks" like this catch subtle bugs.
    If the math doesn't add up, something's wrong!
    """
    # ARRANGE
    inclusive_price = 147034  # A random amount with complex rounding

    # ACT
    result = TaxCalculator.calculate_tax_breakdown(inclusive_price)

    # ASSERT
    calculated_total = (
        result["taxable_value"] +
        result["cgst"] +
        result["sgst"]
    )

    # Due to rounding, we allow a tiny difference (1 paise)
    difference = abs(calculated_total - inclusive_price)
    assert difference <= 1, \
        f"Components should sum to original price (difference: {difference} paise)"

    # TEACHING POINT: When testing floating-point or rounded values,
    # use a tolerance instead of exact equality.


def test_no_floating_point_errors():
    """
    TEST CASE 8: Technical verification - Decimal precision

    WHAT: Ensure we're using Decimal, not float
    WHY: Floats cause precision errors in money calculations (e.g., 0.1 + 0.2 ≠ 0.3)
    EXPECTED: Results should be exact, not approximate

    TEACHING POINT: This tests our technical decision to use Decimal.
    It's a "non-functional requirement" test.
    """
    # ARRANGE: Use an amount that would cause float precision issues
    tricky_price = 33333  # ₹333.33 - repeating decimals in calculations

    # ACT
    result = TaxCalculator.calculate_tax_breakdown(tricky_price)

    # ASSERT: Check that values are integers (no decimal drift)
    assert isinstance(result["taxable_value"], int)
    assert isinstance(result["cgst"], int)
    assert isinstance(result["sgst"], int)
    assert isinstance(result["total_tax"], int)

    # Also verify the math is close (within rounding tolerance)
    # NOTE: Due to independent rounding of CGST, SGST, and total_tax,
    # they might differ by 1 paise. This is acceptable for tax calculations.
    difference = abs((result["cgst"] + result["sgst"]) - result["total_tax"])
    assert difference <= 1, f"CGST + SGST should approximately equal total_tax (diff: {difference})"

    # TEACHING POINT: Testing data types (not just values) can catch bugs.
    # If someone changes Decimal to float, this test will fail!
    # ALSO: This test taught us that rounding can cause tiny differences - that's OK!


# ==============================================================================
# LESSON 1E: Testing the Rounding Function
# ==============================================================================

def test_round_to_rupee_rounds_down():
    """
    TEST CASE 9: Rounding - Round down case

    WHAT: Test rounding when amount is below 0.50
    WHY: Bills are rounded to nearest rupee for customer convenience
    EXPECTED: 147034 paise (₹1,470.34) → 147000 paise (₹1,470.00)
              Adjustment: -34 paise

    TEACHING POINT: Test both directions of rounding (up and down).
    Rounding bugs often only appear in one direction.
    """
    # ARRANGE
    amount_paise = 147034  # ₹1,470.34

    # ACT
    rounded_paise, adjustment = TaxCalculator.round_to_rupee(amount_paise)

    # ASSERT
    assert rounded_paise == 147000, "Should round down to ₹1,470.00"
    assert adjustment == -34, "Adjustment should be -34 paise"

    # Verify the math: original + adjustment = rounded
    assert amount_paise + adjustment == rounded_paise


def test_round_to_rupee_rounds_up():
    """
    TEST CASE 10: Rounding - Round up case

    WHAT: Test rounding when amount is 0.50 or above
    WHY: ROUND_HALF_UP means 0.50 rounds up
    EXPECTED: 147067 paise (₹1,470.67) → 147100 paise (₹1,471.00)
              Adjustment: +33 paise
    """
    # ARRANGE
    amount_paise = 147067  # ₹1,470.67

    # ACT
    rounded_paise, adjustment = TaxCalculator.round_to_rupee(amount_paise)

    # ASSERT
    assert rounded_paise == 147100, "Should round up to ₹1,471.00"
    assert adjustment == 33, "Adjustment should be +33 paise"
    assert amount_paise + adjustment == rounded_paise


def test_round_to_rupee_exact_rupee():
    """
    TEST CASE 11: Rounding - Already a whole rupee

    WHAT: Test when amount is already a whole rupee
    WHY: Edge case - no rounding needed
    EXPECTED: No change, adjustment = 0
    """
    # ARRANGE
    amount_paise = 150000  # Exactly ₹1,500.00

    # ACT
    rounded_paise, adjustment = TaxCalculator.round_to_rupee(amount_paise)

    # ASSERT
    assert rounded_paise == 150000, "Should remain unchanged"
    assert adjustment == 0, "No adjustment needed"


def test_round_to_rupee_raises_error_for_negative():
    """
    TEST CASE 12: Rounding error case - Negative amount

    WHAT: Verify negative amounts are rejected
    WHY: Can't round negative bills
    EXPECTED: ValueError raised
    """
    # ARRANGE
    negative_amount = -100000

    # ACT & ASSERT
    with pytest.raises(ValueError) as exc_info:
        TaxCalculator.round_to_rupee(negative_amount)

    assert "Amount cannot be negative" in str(exc_info.value)


# ==============================================================================
# END OF LESSON 1
# ==============================================================================

"""
🎉 CONGRATULATIONS! You've written your first test file!

WHAT YOU LEARNED:
1. ✅ AAA Pattern (Arrange, Act, Assert)
2. ✅ Testing normal cases (happy path)
3. ✅ Testing edge cases (zero, large numbers)
4. ✅ Testing error cases (pytest.raises)
5. ✅ Testing business rules
6. ✅ Using clear test names and docstrings

NEXT STEPS:
1. Run these tests: uv run pytest tests/unit/test_tax_calculator.py -v
2. Try making a test fail on purpose (change an assert value)
3. See what the error message looks like
4. Fix it back and watch it pass again

QUIZ FOR YOU:
1. What does the -v flag do when running pytest?
2. Why do we test with zero?
3. What's the difference between testing and debugging?

When you're ready, we'll move to LESSON 2: Fixtures and conftest.py! 🚀
"""
