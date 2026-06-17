"""Create PackageSale rows from PackageDefinition at bill finalization."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.package import (
    EntitlementType,
    PackageDefinition,
    PackageSale,
    PackageSaleItem,
    PackageSaleStatus,
)


def _block_sale_lines(
    blocks: list, locked_choices: list[str] | None
) -> tuple[int, list[dict], list[dict]]:
    """Map a v2 block stack onto the PackageSale model.

    Returns (total_sessions, lines, block_counters):
      - lines are PackageSaleItem kwargs; a line may carry `block_index`
        linking it to an independent per-block counter.
      - block_counters are {block_index, kind, name, remaining} rows; each is a
        budget shared across that block's options, independent of everything else.

    Block kinds:
      - items: one capped line per row (max = qty); adds Σqty to the GLOBAL pool.
      - choice@purchase: a single-use line per LOCKED service; adds picks to the
        global pool (the locked set already bounds total use).
      - choice@visit: an INDEPENDENT counter of `picks` shared across all options
        (use any option, `picks` times total, any day). Not in the global pool.
      - pool: an INDEPENDENT counter of `sessions` shared across listed services.
      - unlimited: pool-exempt, free, uncapped lines.
      - credit: skipped (wallet redemption not yet modelled).
    """
    locked = set(locked_choices or [])
    total = 0
    lines: list[dict] = []
    counters: list[dict] = []
    order = 0

    def add(service_id, price, cap, *, pool_exempt=False, block_index=None):
        nonlocal order
        lines.append({
            "service_id": service_id,
            "quantity": 1,
            "snapshot_unit_price_paise": price,
            "max_redemptions": cap,
            "remaining": cap,
            "pool_exempt": pool_exempt,
            "block_index": block_index,
            "display_order": order,
        })
        order += 1

    for idx, b in enumerate(blocks):
        kind = b.get("kind")
        rows = b.get("rows", [])
        if kind == "items":
            for r in rows:
                qty = int(r.get("quantity") or 1)
                total += qty
                add(r["service_id"], int(r.get("unit_price_paise") or 0), qty)
        elif kind == "choice":
            picks = int(b.get("picks") or 0)
            if b.get("choose_at") == "purchase":
                total += picks
                for r in rows:
                    if r["service_id"] in locked:
                        add(r["service_id"], int(r.get("unit_price_paise") or 0), 1)
            else:  # chosen each visit — independent shared counter of `picks`
                counters.append({
                    "block_index": idx, "kind": "choice",
                    "name": b.get("name") or "Choice", "remaining": picks,
                })
                for r in rows:
                    add(r["service_id"], int(r.get("unit_price_paise") or 0),
                        None, block_index=idx)
        elif kind == "pool":
            sessions = int(b.get("sessions") or 0)
            counters.append({
                "block_index": idx, "kind": "pool",
                "name": b.get("name") or "Session pool", "remaining": sessions,
            })
            for r in rows:
                add(r["service_id"], int(r.get("unit_price_paise") or 0),
                    None, block_index=idx)
        elif kind == "unlimited":
            for r in rows:
                add(r["service_id"], 0, None, pool_exempt=True)
        # credit: no service redemption yet

    return total, lines, counters


def create_sale(
    db: Session,
    package_definition_id: str,
    bill_id: str,
    customer_id: str,
    selling_staff_id: str | None,
    locked_choices: list[str] | None = None,
) -> PackageSale:
    """Atomically snapshot a PackageDefinition into a PackageSale + PackageSaleItems.

    Called from billing_service.finalize_bill() for each package_sale_line BillItem.
    Uses db.flush() only — transaction ownership belongs to the caller. v2 (block)
    definitions are projected onto the session-pool model via _block_sale_lines;
    v1 (items) definitions snapshot their items directly.

    Raises:
        ValueError: if the PackageDefinition does not exist.
    """
    pkg = db.get(PackageDefinition, package_definition_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {package_definition_id} not found")

    sold_at = datetime.now(timezone.utc)
    expires_at = sold_at + timedelta(days=pkg.validity_days)

    is_v2 = pkg.blocks is not None
    if is_v2:
        total_sessions, block_lines, block_counters = _block_sale_lines(
            pkg.blocks, locked_choices
        )
    else:
        total_sessions = pkg.total_sessions
        block_lines = None
        block_counters = []

    counted = is_v2 or pkg.entitlement_type == EntitlementType.COUNTED
    sale = PackageSale(
        bill_id=bill_id,
        package_definition_id=pkg.id,
        customer_id=customer_id,
        selling_staff_id=selling_staff_id,
        sold_at=sold_at,
        expires_at=expires_at,
        entitlement_type_snapshot=(
            EntitlementType.COUNTED if is_v2 else pkg.entitlement_type
        ),
        shareability_snapshot=pkg.shareability,
        cancellation_fee_pct_snapshot=pkg.cancellation_fee_pct,
        total_sessions_snapshot=total_sessions,
        sessions_remaining=total_sessions if counted else None,
        blocks_snapshot=pkg.blocks if is_v2 else None,
        status=PackageSaleStatus.ACTIVE,
    )
    db.add(sale)
    db.flush()  # get sale.id before inserting items

    if is_v2:
        from app.models.package import PackageSaleBlock
        # Create independent per-block counters first, then link lines to them.
        block_id_by_index: dict[int, str] = {}
        for c in block_counters:
            counter = PackageSaleBlock(
                package_sale_id=sale.id,
                block_index=c["block_index"],
                kind=c["kind"],
                name=c["name"],
                remaining=c["remaining"],
            )
            db.add(counter)
            db.flush()
            block_id_by_index[c["block_index"]] = counter.id

        for line in block_lines:
            db.add(PackageSaleItem(
                package_sale_id=sale.id,
                package_definition_item_id=None,
                service_id=line["service_id"],
                quantity=line["quantity"],
                snapshot_unit_price_paise=line["snapshot_unit_price_paise"],
                snapshot_gst_rate_pct=Decimal("0"),
                locked=False,
                display_order=line["display_order"],
                max_redemptions=line["max_redemptions"],
                remaining=line["remaining"],
                pool_exempt=line["pool_exempt"],
                sale_block_id=block_id_by_index.get(line.get("block_index")),
            ))
    else:
        # Definition items hold GROSS prices; apply the discount here so the
        # sale snapshots what the customer actually paid per unit.
        effective_prices = pkg.effective_item_prices()
        for def_item, effective_price in zip(pkg.items, effective_prices, strict=True):
            db.add(PackageSaleItem(
                package_sale_id=sale.id,
                package_definition_item_id=def_item.id,
                service_id=def_item.service_id,
                quantity=def_item.quantity,
                snapshot_unit_price_paise=effective_price,
                snapshot_gst_rate_pct=Decimal("0"),
                locked=def_item.locked,
                display_order=def_item.display_order,
                max_redemptions=def_item.max_redemptions,
                remaining=def_item.max_redemptions,
            ))

    db.flush()
    return sale
