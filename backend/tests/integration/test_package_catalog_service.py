"""Integration tests for package_catalog_service.py."""

import pytest
from decimal import Decimal
from app.services.package_catalog_service import (
    create_definition, publish, archive, soft_delete, update_definition,
)
from app.schemas.package import (
    PackageDefinitionCreate, PackageDefinitionItemCreate, DiscountInput,
    PackageDefinitionUpdate,
)
from app.models.package import PackageDefinitionStatus, EntitlementType, Shareability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(db_session, name_suffix=""):
    from app.models.service import Service, ServiceCategory
    cat = ServiceCategory(
        name=f"Cat{name_suffix}", display_order=1, is_active=True
    )
    db_session.add(cat)
    db_session.flush()
    svc = Service(
        category_id=cat.id,
        name=f"Service{name_suffix}",
        base_price=100000,
        duration_minutes=30,
        is_active=True,
        display_order=1,
    )
    db_session.add(svc)
    db_session.flush()
    return svc


def _counted_payload(items, discount=None):
    return PackageDefinitionCreate(
        name="Test Pack",
        entitlement_type=EntitlementType.COUNTED,
        total_sessions=5,
        validity_days=90,
        shareability=Shareability.OWNER_ONLY,
        items=items,
        discount=discount,
    )


def test_block_sale_lines_independent_choice_and_pool_counters():
    """choice@visit and pool blocks get their OWN counter, separate from the
    global session pool; only fixed items feed the global pool."""
    from app.services.package_sales_service import _block_sale_lines

    blocks = [
        {"kind": "choice", "choose_at": "visit", "picks": "3", "name": "Facial choice",
         "rows": [{"service_id": "a", "unit_price_paise": 220000},
                  {"service_id": "b", "unit_price_paise": 250000},
                  {"service_id": "c", "unit_price_paise": 120000}]},
        {"kind": "pool", "sessions": "2",
         "rows": [{"service_id": "p1", "unit_price_paise": 50000},
                  {"service_id": "p2", "unit_price_paise": 40000}]},
        {"kind": "items",
         "rows": [{"service_id": "h", "quantity": "2", "unit_price_paise": 250000}]},
    ]
    total, lines, counters = _block_sale_lines(blocks, None)

    # Only the fixed-items block feeds the global pool.
    assert total == 2
    # One independent counter for the choice block, one for the pool block.
    by_idx = {c["block_index"]: c for c in counters}
    assert by_idx[0]["remaining"] == 3
    assert by_idx[1]["remaining"] == 2

    line_by_svc = {l["service_id"]: l for l in lines}
    # Choice options share counter 0; pool options share counter 1.
    assert all(line_by_svc[s]["block_index"] == 0 for s in ("a", "b", "c"))
    assert all(line_by_svc[s]["block_index"] == 1 for s in ("p1", "p2"))
    # Items line is global-pool governed (no block counter, per-line cap = qty).
    assert line_by_svc["h"]["block_index"] is None
    assert line_by_svc["h"]["max_redemptions"] == 2


def test_block_sale_lines_mapping():
    """v2 block stack maps onto session-pool lines correctly."""
    from app.services.package_sales_service import _block_sale_lines

    blocks = [
        {"kind": "items", "rows": [{"service_id": "h", "quantity": "2", "unit_price_paise": 250000}]},
        {"kind": "choice", "choose_at": "purchase", "picks": "2",
         "rows": [{"service_id": "a", "unit_price_paise": 220000},
                  {"service_id": "b", "unit_price_paise": 250000},
                  {"service_id": "c", "unit_price_paise": 120000}]},
        {"kind": "unlimited", "rows": [{"service_id": "wash"}]},
        {"kind": "credit", "amount_paise": 500000, "scope": "any"},
    ]
    total, lines, _counters = _block_sale_lines(blocks, locked_choices=["a", "c"])

    # pool = 2 (items) + 2 (choice picks) + 0 (unlimited) + 0 (credit)
    assert total == 4
    by_svc = {l["service_id"]: l for l in lines}
    # items line capped at qty
    assert by_svc["h"]["max_redemptions"] == 2 and by_svc["h"]["remaining"] == 2
    # only the LOCKED choice services become single-use lines
    assert set(by_svc) == {"h", "a", "c", "wash"}
    assert by_svc["a"]["max_redemptions"] == 1
    assert "b" not in by_svc
    # unlimited line is pool-exempt and free
    assert by_svc["wash"]["pool_exempt"] is True
    assert by_svc["wash"]["snapshot_unit_price_paise"] == 0


def test_choice_visit_block_enforces_independent_total_cap(
    db_session, user_factory, customer_factory, bill_factory, test_user
):
    """A choice@visit group of `picks` allows that many TOTAL redemptions across
    its options (any mix), independent of the global pool."""
    from app.services.package_sales_service import create_sale
    from app.services.package_redemption_service import apply_redemption
    from app.models.billing import Bill, BillItem, BillItemType, BillStatus, BillType

    svc_a = _make_service(db_session, "CA")
    svc_b = _make_service(db_session, "CB")
    user = user_factory()
    customer = customer_factory()
    blocks = [{
        "id": "b1", "kind": "choice", "bonus": False, "choose_at": "visit",
        "picks": "2", "name": "Facial choice",
        "rows": [
            {"service_id": svc_a.id, "unit_price_paise": 220000},
            {"service_id": svc_b.id, "unit_price_paise": 250000},
        ],
    }]
    pkg = create_definition(db_session, PackageDefinitionCreate(
        name="Choice Cap", validity_days=90, shareability=Shareability.OWNER_ONLY,
        blocks=blocks, final_price_paise=400000,
    ), user.id)
    publish(db_session, pkg.id)

    bill = bill_factory(customer_id=customer.id)
    sale = create_sale(db_session, pkg.id, bill.id, customer.id, None)

    # Independent counter of 2; global pool not fed by the choice block.
    assert len(sale.block_counters) == 1
    assert sale.block_counters[0].remaining == 2
    assert sale.total_sessions_snapshot == 0

    def redeem(service_id):
        bi = BillItem(
            id=__import__("ulid").ULID().__str__(), bill_id=bill.id,
            service_id=service_id, item_name="x", base_price=220000, quantity=1,
            line_total=220000, item_type=BillItemType.SERVICE,
        )
        db_session.add(bi)
        db_session.flush()
        return apply_redemption(db_session, sale.id, bi.id, customer.id, user.id)

    # Use the SAME option twice + the other once = 3 attempts; only 2 allowed.
    redeem(svc_a.id)
    redeem(svc_a.id)
    db_session.refresh(sale.block_counters[0])
    assert sale.block_counters[0].remaining == 0
    with pytest.raises(ValueError, match="budget exhausted"):
        redeem(svc_b.id)


def test_redemption_consumes_quantity_units_of_budget(
    db_session, user_factory, customer_factory, bill_factory, test_user
):
    """A redeemed line of quantity N consumes N budget units (not 1), and a line
    needing more than the remaining budget is rejected — no free over-redemption."""
    from app.services.package_sales_service import create_sale
    from app.services.package_redemption_service import apply_redemption
    from app.models.billing import BillItem, BillItemType

    svc = _make_service(db_session, "QA")
    user = user_factory()
    customer = customer_factory()
    blocks = [{
        "id": "b1", "kind": "choice", "bonus": False, "choose_at": "visit",
        "picks": "2", "name": "Facial choice",
        "rows": [{"service_id": svc.id, "unit_price_paise": 220000}],
    }]
    pkg = create_definition(db_session, PackageDefinitionCreate(
        name="Qty Cap", validity_days=90, shareability=Shareability.OWNER_ONLY,
        blocks=blocks, final_price_paise=400000,
    ), user.id)
    publish(db_session, pkg.id)
    bill = bill_factory(customer_id=customer.id)
    sale = create_sale(db_session, pkg.id, bill.id, customer.id, None)
    assert sale.block_counters[0].remaining == 2

    def bill_item(qty):
        bi = BillItem(
            id=__import__("ulid").ULID().__str__(), bill_id=bill.id,
            service_id=svc.id, item_name="x", base_price=220000, quantity=qty,
            line_total=220000 * qty, item_type=BillItemType.SERVICE,
        )
        db_session.add(bi)
        db_session.flush()
        return bi

    # A quantity-3 line needs 3 budget units but only 2 remain → rejected.
    with pytest.raises(ValueError, match="budget"):
        apply_redemption(db_session, sale.id, bill_item(3).id, customer.id, user.id)

    # A quantity-2 line consumes both remaining units.
    apply_redemption(db_session, sale.id, bill_item(2).id, customer.id, user.id)
    db_session.refresh(sale.block_counters[0])
    assert sale.block_counters[0].remaining == 0


def test_create_sale_from_v2_definition(
    db_session, user_factory, customer_factory, bill_factory
):
    """create_sale snapshots a v2 block definition onto the sale."""
    from app.services.package_sales_service import create_sale

    svc_h = _make_service(db_session, "VH")
    svc_w = _make_service(db_session, "VW")
    user = user_factory()
    customer = customer_factory()
    blocks = [
        {"id": "b1", "kind": "items", "bonus": False,
         "rows": [{"service_id": svc_h.id, "quantity": "2", "unit_price_paise": 250000}]},
        {"id": "b2", "kind": "unlimited", "bonus": False,
         "rows": [{"service_id": svc_w.id}]},
    ]
    pkg = create_definition(db_session, PackageDefinitionCreate(
        name="V2 Sale", validity_days=90, shareability=Shareability.OWNER_ONLY,
        blocks=blocks, final_price_paise=500000,
    ), user.id)
    publish(db_session, pkg.id)

    bill = bill_factory(customer_id=customer.id)
    sale = create_sale(db_session, pkg.id, bill.id, customer.id, None)

    assert sale.total_sessions_snapshot == 2
    assert sale.sessions_remaining == 2
    wash = next(i for i in sale.items if i.service_id == svc_w.id)
    assert wash.pool_exempt is True
    assert wash.package_definition_item_id is None


def test_create_v2_block_package_persists_blocks_and_price(db_session, user_factory):
    """v2 builder packages store the block stack + builder price, no items."""
    user = user_factory()
    blocks = [
        {"id": "b1", "kind": "items", "bonus": False,
         "rows": [{"service_id": "x", "quantity": "2", "unit_price_paise": 250000}]},
        {"id": "b2", "kind": "credit", "bonus": False,
         "amount_paise": 500000, "scope": "any"},
    ]
    payload = PackageDefinitionCreate(
        name="Freedom Pack v2",
        validity_days=90,
        shareability=Shareability.OWNER_ONLY,
        blocks=blocks,
        final_price_paise=799900,
    )
    pkg = create_definition(db_session, payload, user.id)
    assert pkg.items == []
    assert pkg.blocks == blocks
    assert pkg.stored_price_paise == 799900
    # final_price_paise property trusts the stored v2 price
    assert pkg.final_price_paise == 799900


# ---------------------------------------------------------------------------
# create_definition
# ---------------------------------------------------------------------------

def test_create_with_discount_persists_gross_prices(db_session, user_factory):
    """create_definition stores GROSS item prices and the discount itself.

    The discount is no longer baked into item prices at save time — it is
    applied at sale time so editing always round-trips the entered values.
    """
    svc1 = _make_service(db_session, "A")
    svc2 = _make_service(db_session, "B")
    user = user_factory()
    payload = _counted_payload(
        items=[
            PackageDefinitionItemCreate(service_id=svc1.id, quantity=1, unit_price_paise=200000),
            PackageDefinitionItemCreate(service_id=svc2.id, quantity=1, unit_price_paise=200000),
        ],
        discount=DiscountInput(mode="pct", value=Decimal("20")),
    )
    pkg = create_definition(db_session, payload, user.id)
    assert pkg.status == PackageDefinitionStatus.DRAFT
    # Gross prices preserved exactly as entered
    assert all(i.unit_price_paise == 200000 for i in pkg.items)
    # Discount persisted on the definition
    assert pkg.discount_mode == "pct"
    assert pkg.discount_value == Decimal("20")
    # Effective selling price computed on demand: 20% off 400000
    assert pkg.final_price_paise == 320000


def test_create_without_discount(db_session, user_factory):
    """create_definition without discount preserves original prices."""
    svc = _make_service(db_session, "C")
    user = user_factory()
    payload = _counted_payload(
        items=[
            PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=150000),
        ],
    )
    pkg = create_definition(db_session, payload, user.id)
    assert pkg.status == PackageDefinitionStatus.DRAFT
    assert pkg.items[0].unit_price_paise == 150000


def test_create_flat_discount(db_session, user_factory):
    """Flat discount: gross price kept, final price reflects the discount."""
    svc = _make_service(db_session, "D")
    user = user_factory()
    payload = _counted_payload(
        items=[
            PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=300000),
        ],
        discount=DiscountInput(mode="flat", value=Decimal("50000")),
    )
    pkg = create_definition(db_session, payload, user.id)
    assert pkg.items[0].unit_price_paise == 300000
    assert pkg.discount_mode == "flat"
    assert pkg.final_price_paise == 250000


def test_final_discount_round_trips(db_session, user_factory):
    """Regression: 2×2200 + 2×2500 with final ₹7999 must round-trip intact."""
    svc1 = _make_service(db_session, "F1")
    svc2 = _make_service(db_session, "F2")
    user = user_factory()
    payload = _counted_payload(
        items=[
            PackageDefinitionItemCreate(service_id=svc1.id, quantity=2, unit_price_paise=220000),
            PackageDefinitionItemCreate(service_id=svc2.id, quantity=2, unit_price_paise=250000),
        ],
        discount=DiscountInput(mode="final", value=Decimal("799900")),
    )
    pkg = create_definition(db_session, payload, user.id)
    assert [i.unit_price_paise for i in pkg.items] == [220000, 250000]
    assert pkg.discount_mode == "final"
    assert pkg.discount_value == Decimal("799900")
    assert pkg.final_price_paise == 799900


def test_create_sale_snapshots_discounted_prices(
    db_session, user_factory, customer_factory, bill_factory
):
    """Sale snapshots use the EFFECTIVE (discounted) prices, not gross."""
    from app.services.package_sales_service import create_sale

    svc1 = _make_service(db_session, "S1")
    svc2 = _make_service(db_session, "S2")
    user = user_factory()
    customer = customer_factory()
    pkg = create_definition(db_session, _counted_payload(
        items=[
            PackageDefinitionItemCreate(service_id=svc1.id, quantity=1, unit_price_paise=200000),
            PackageDefinitionItemCreate(service_id=svc2.id, quantity=1, unit_price_paise=200000),
        ],
        discount=DiscountInput(mode="pct", value=Decimal("20")),
    ), user.id)
    publish(db_session, pkg.id)

    bill = bill_factory(customer_id=customer.id)
    sale = create_sale(db_session, pkg.id, bill.id, customer.id, None)
    # 20% off each 200000 line
    assert sorted(i.snapshot_unit_price_paise for i in sale.items) == [160000, 160000]


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------

def test_publish_from_draft(db_session, user_factory):
    """publish() transitions DRAFT -> PUBLISHED."""
    svc = _make_service(db_session, "E")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)
    assert pkg.status == PackageDefinitionStatus.DRAFT

    result = publish(db_session, pkg.id)
    assert result.status == PackageDefinitionStatus.PUBLISHED


def test_publish_only_from_draft_raises(db_session, user_factory):
    """publish() on a non-DRAFT package raises ValueError."""
    svc = _make_service(db_session, "F")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)
    publish(db_session, pkg.id)  # now PUBLISHED
    with pytest.raises(ValueError, match="draft"):
        publish(db_session, pkg.id)  # second publish should fail


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------

def test_archive_published(db_session, user_factory):
    """archive() sets status to ARCHIVED on a published package."""
    svc = _make_service(db_session, "G")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)
    publish(db_session, pkg.id)

    result = archive(db_session, pkg.id)
    assert result.status == PackageDefinitionStatus.ARCHIVED


# ---------------------------------------------------------------------------
# soft_delete
# ---------------------------------------------------------------------------

def test_soft_delete_allowed_when_no_active_sales(db_session, user_factory):
    """soft_delete() succeeds when no active PackageSales exist."""
    svc = _make_service(db_session, "H")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)

    soft_delete(db_session, pkg.id)
    db_session.refresh(pkg)
    assert pkg.deleted_at is not None


def test_soft_delete_blocked_when_active_sales(
    db_session, user_factory,
):
    """soft_delete() raises ValueError when active PackageSales exist."""
    svc = _make_service(db_session, "I")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)
    publish(db_session, pkg.id)

    from app.models.customer import Customer
    customer = Customer(
        first_name="Block", last_name="Test", phone="9000000001",
        total_visits=0, total_spent=0,
    )
    db_session.add(customer)
    db_session.flush()

    # Create an active sale referencing this definition's id directly
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal as D
    from app.models.billing import Bill, BillStatus, BillType
    from app.models.package import PackageSale, PackageSaleStatus, EntitlementType, Shareability
    bill = Bill(
        customer_id=customer.id,
        subtotal=100000,
        discount_amount=0,
        tax_amount=18000,
        cgst_amount=9000,
        sgst_amount=9000,
        total_amount=118000,
        rounded_total=118000,
        rounding_adjustment=0,
        status=BillStatus.POSTED,
        bill_type=BillType.NORMAL,
        created_by=user.id,
    )
    db_session.add(bill)
    db_session.flush()

    sale = PackageSale(
        bill_id=bill.id,
        package_definition_id=pkg.id,
        customer_id=customer.id,
        sold_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
        entitlement_type_snapshot=EntitlementType.COUNTED,
        shareability_snapshot=Shareability.OWNER_ONLY,
        cancellation_fee_pct_snapshot=D("20.00"),
        total_sessions_snapshot=5,
        sessions_remaining=5,
        status=PackageSaleStatus.ACTIVE,
    )
    db_session.add(sale)
    db_session.flush()

    with pytest.raises(ValueError, match="active sales"):
        soft_delete(db_session, pkg.id)


# ---------------------------------------------------------------------------
# update_definition
# ---------------------------------------------------------------------------

def test_update_definition_replaces_items(db_session, user_factory):
    """update_definition clears old items and re-inserts new ones."""
    svc1 = _make_service(db_session, "J")
    svc2 = _make_service(db_session, "K")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc1.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)
    original_id = pkg.items[0].id

    update_payload = PackageDefinitionUpdate(
        name="Updated Pack",
        entitlement_type=EntitlementType.COUNTED,
        total_sessions=5,
        validity_days=90,
        shareability=Shareability.OWNER_ONLY,
        items=[
            PackageDefinitionItemCreate(service_id=svc2.id, quantity=2, unit_price_paise=200000),
        ],
    )
    updated = update_definition(db_session, pkg.id, update_payload)
    assert updated.name == "Updated Pack"
    assert len(updated.items) == 1
    assert updated.items[0].service_id == svc2.id
    assert updated.items[0].quantity == 2
    # Old item must be gone
    assert updated.items[0].id != original_id


def test_update_definition_not_found_raises(db_session, user_factory):
    """update_definition raises ValueError for unknown id."""
    user = user_factory()
    svc = _make_service(db_session, "L")
    update_payload = PackageDefinitionUpdate(
        name="Ghost",
        entitlement_type=EntitlementType.COUNTED,
        total_sessions=5,
        validity_days=90,
        shareability=Shareability.OWNER_ONLY,
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    with pytest.raises(ValueError, match="not found"):
        update_definition(db_session, "00000000000000000000000000", update_payload)


def test_archive_already_archived_raises(db_session, user_factory):
    """archive() on an already-ARCHIVED package raises ValueError."""
    svc = _make_service(db_session, "M")
    user = user_factory()
    pkg = create_definition(db_session, _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    ), user.id)
    publish(db_session, pkg.id)
    archive(db_session, pkg.id)
    with pytest.raises(ValueError, match="already archived"):
        archive(db_session, pkg.id)


def test_soft_delete_already_deleted_raises(db_session, user_factory):
    """soft_delete() on an already-deleted package raises ValueError."""
    svc = _make_service(db_session, "N")
    user = user_factory()
    pkg = create_definition(db_session, _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    ), user.id)
    soft_delete(db_session, pkg.id)
    with pytest.raises(ValueError, match="already deleted"):
        soft_delete(db_session, pkg.id)


def test_update_definition_with_discount(db_session, user_factory):
    """update_definition applies discount distribution on update."""
    svc = _make_service(db_session, "O")
    user = user_factory()
    pkg = create_definition(db_session, _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    ), user.id)
    update_payload = PackageDefinitionUpdate(
        name="Updated Pack",
        entitlement_type=EntitlementType.COUNTED,
        total_sessions=5,
        validity_days=60,
        shareability=Shareability.OWNER_ONLY,
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
        discount=DiscountInput(mode="pct", value=Decimal("10")),
    )
    updated = update_definition(db_session, pkg.id, update_payload)
    # Gross price kept; discount persisted; final price reflects 10% off
    assert updated.items[0].unit_price_paise == 100000
    assert updated.discount_mode == "pct"
    assert updated.final_price_paise == 90000


# ---------------------------------------------------------------------------
# max_redemptions (per-line cap)
# ---------------------------------------------------------------------------

def test_create_definition_persists_per_line_max_redemptions(
    db_session, service_factory, test_user,
):
    """create_definition stores max_redemptions on each PackageDefinitionItem."""
    svc_a = service_factory(base_price=100000)
    svc_b = service_factory(base_price=50000)
    payload = PackageDefinitionCreate(
        name="Salon Royal Pass",
        entitlement_type="counted",
        total_sessions=12,
        validity_days=180,
        shareability="owner_only",
        cancellation_fee_pct="20.00",
        items=[
            PackageDefinitionItemCreate(
                service_id=svc_a.id, quantity=1, unit_price_paise=100000,
                max_redemptions=3,
            ),
            PackageDefinitionItemCreate(
                service_id=svc_b.id, quantity=1, unit_price_paise=50000,
                max_redemptions=None,
            ),
        ],
    )
    pkg = create_definition(db_session, payload, user_id=test_user.id)
    db_session.flush()
    by_svc = {it.service_id: it for it in pkg.items}
    assert by_svc[svc_a.id].max_redemptions == 3
    assert by_svc[svc_b.id].max_redemptions is None
