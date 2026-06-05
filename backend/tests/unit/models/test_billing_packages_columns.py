"""Verify additive columns on Bill, BillItem; new PaymentMethod value."""

from app.models.billing import Bill, BillItem, BillType, BillItemType, PaymentMethod


def test_bill_has_bill_type_and_original_bill_id():
    assert hasattr(Bill, "bill_type")
    assert hasattr(Bill, "original_bill_id")


def test_bill_type_enum_has_normal_and_credit_note():
    assert BillType.NORMAL.value == "normal"
    assert BillType.CREDIT_NOTE.value == "credit_note"


def test_bill_item_has_item_type_and_package_refs():
    assert hasattr(BillItem, "item_type")
    assert hasattr(BillItem, "package_sale_id")
    assert hasattr(BillItem, "package_sale_item_id")


def test_bill_item_type_enum_values():
    assert BillItemType.SERVICE.value == "service"
    assert BillItemType.PRODUCT.value == "product"
    assert BillItemType.PACKAGE_SALE_LINE.value == "package_sale_line"
    assert BillItemType.PACKAGE_REDEMPTION.value == "package_redemption"


def test_payment_method_has_package_redemption():
    assert PaymentMethod.PACKAGE_REDEMPTION.value == "package_redemption"


def test_bill_credit_note_constraint_declared():
    """Verify the credit-note check constraint is in Bill.__table_args__."""
    constraint_names = {
        getattr(arg, "name", None) for arg in Bill.__table_args__
    }
    assert "ck_bill_credit_note_has_original" in constraint_names
