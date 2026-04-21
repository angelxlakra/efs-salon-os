"""Inventory transfer service for SalonOS store side.

Handles three operations:
1. initiate_transfer   — called from API when manager clicks "Transfer"
2. poll_and_apply_incoming — called from scheduled job every 15 minutes
3. cancel_transfer     — called from API when manager cancels a pending OUT transfer

Design:
- All DB writes use explicit db.flush() + db.commit() patterns (sync SQLAlchemy).
- Central API calls use a synchronous httpx.Client.
- If the central API call fails during initiation, the DB transaction is rolled back
  so inventory and expense entries are never created without a central record.
- CENTRAL_SYNC_ENABLED is checked by the *caller* (job/endpoint), not here.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.expense import Expense, ExpenseCategory, ExpenseStatus
from app.models.inventory import SKU, InventoryCategory
from app.models.inventory_transfer import InventoryTransfer
from app.utils import IST, generate_ulid

logger = logging.getLogger(__name__)


class InventoryTransferService:
    def __init__(self, db: Session):
        self.db = db
        self._client: Optional[httpx.Client] = None

    # ------------------------------------------------------------------
    # HTTP client
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=settings.central_api_url,
                headers={"X-Store-API-Key": settings.central_api_key},
                timeout=30.0,
            )
        return self._client

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_system_user_id(self) -> str:
        """Return the ID of the first active user, for system-created expense records."""
        from app.models.user import User
        user = self.db.query(User).filter(User.is_active == True).first()
        if user:
            return user.id
        raise RuntimeError("No active users found — cannot create expense record")

    def _get_or_create_default_category_id(self) -> str:
        """Return the ID of the first inventory category, creating one if none exist."""
        cat = self.db.query(InventoryCategory).first()
        if cat:
            return cat.id
        new_cat = InventoryCategory(id=generate_ulid(), name="General")
        self.db.add(new_cat)
        self.db.flush()
        return new_cat.id

    # ------------------------------------------------------------------
    # Initiate (OUT)
    # ------------------------------------------------------------------

    def initiate_transfer(
        self,
        sku_id: str,
        destination_store_id: str,
        destination_store_name: str,
        quantity: int,
        user_id: str,
        notes: Optional[str] = None,
    ) -> InventoryTransfer:
        """Initiate an outgoing transfer.

        Atomic: decrements stock + creates expense + creates local record + posts to central.
        If the central API call fails, the entire DB transaction is rolled back.
        """
        # Validate SKU and stock
        sku = (
            self.db.query(SKU)
            .filter(SKU.id == sku_id, SKU.is_active == True)
            .with_for_update()
            .first()
        )
        if not sku:
            raise ValueError(f"SKU {sku_id} not found or inactive")

        if float(sku.current_stock) < quantity:
            raise ValueError(
                f"Insufficient stock: have {sku.current_stock}, need {quantity}"
            )

        unit_cost_paise = sku.avg_cost_per_unit
        total_cost_paise = unit_cost_paise * quantity

        try:
            # 1. Decrement stock
            sku.current_stock = float(sku.current_stock) - quantity

            # 2. Create TRANSFER_OUT expense
            now = datetime.now(IST)
            expense = Expense(
                id=generate_ulid(),
                category=ExpenseCategory.TRANSFER_OUT,
                amount=total_cost_paise,
                expense_date=now.date(),
                description=f"Transfer OUT: {sku.name} ×{quantity} → {destination_store_name}",
                notes=notes,
                is_recurring=False,
                status=ExpenseStatus.APPROVED,
                requires_approval=False,
                recorded_by=user_id,
                recorded_at=now,
                approved_by=user_id,
                approved_at=now,
            )
            self.db.add(expense)

            # 3. Create local transfer record
            local_transfer = InventoryTransfer(
                id=generate_ulid(),
                direction="OUT",
                other_store_name=destination_store_name,
                sku_id=sku_id,
                product_name=sku.name,
                product_sku=sku.sku_code,
                quantity=quantity,
                unit_cost_paise=unit_cost_paise,
                total_cost_paise=total_cost_paise,
                status="PENDING",
                initiated_at=now,
                notes=notes,
            )
            self.db.add(local_transfer)
            self.db.flush()  # Get IDs without committing

            # Link expense
            local_transfer.expense_id = expense.id
            self.db.flush()

            # 4. POST to central API
            idempotency_key = local_transfer.id  # Use local ULID as idempotency key
            client = self._get_client()
            response = client.post(
                "/v1/transfers",
                json={
                    "idempotency_key": idempotency_key,
                    "destination_store_id": destination_store_id,
                    "product_id": sku_id,
                    "product_name": sku.name,
                    "product_sku": sku.sku_code,
                    "quantity": quantity,
                    "unit_cost_paise": unit_cost_paise,
                    "initiated_by_user_id": user_id,
                    "notes": notes,
                },
            )
            response.raise_for_status()
            central_data = response.json()

            # 5. Store central transfer ID
            local_transfer.central_transfer_id = central_data["transfer_id"]
            self.db.commit()

            logger.info(
                "Transfer initiated: local=%s central=%s sku=%s qty=%d → %s",
                local_transfer.id,
                local_transfer.central_transfer_id,
                sku.sku_code,
                quantity,
                destination_store_name,
            )
            return local_transfer

        except Exception:
            self.db.rollback()
            raise

    # ------------------------------------------------------------------
    # Poll and apply incoming (IN)
    # ------------------------------------------------------------------

    def poll_and_apply_incoming(self) -> list[dict]:
        """Poll central for pending incoming transfers and apply them.

        Returns a list of dicts with applied transfer info.
        Idempotent: skips transfers already present in local inventory_transfers.
        """
        client = self._get_client()
        response = client.get("/v1/transfers/incoming", params={"status": "PENDING"})
        response.raise_for_status()
        data = response.json()
        incoming = data.get("transfers", [])

        if not incoming:
            logger.debug("No pending incoming transfers from central.")
            return []

        applied = []
        system_user_id = self._get_system_user_id()

        for transfer in incoming:
            central_id = transfer["transfer_id"]

            # Idempotency: skip if already applied
            existing = (
                self.db.query(InventoryTransfer)
                .filter(InventoryTransfer.central_transfer_id == central_id)
                .first()
            )
            if existing:
                logger.debug("Transfer %s already applied locally, skipping.", central_id)
                continue

            try:
                self._apply_one_incoming(transfer, system_user_id)
                # Notify central
                patch_resp = client.patch(f"/v1/transfers/{central_id}/apply")
                patch_resp.raise_for_status()
                applied.append({"central_transfer_id": central_id, "status": "applied"})
                logger.info("Applied incoming transfer %s", central_id)
            except Exception as exc:
                self.db.rollback()
                logger.error(
                    "Failed to apply transfer %s: %s", central_id, exc, exc_info=True
                )

        return applied

    def _apply_one_incoming(self, transfer: dict, user_id: str) -> InventoryTransfer:
        """Apply one incoming transfer inside a transaction.

        Upserts the SKU (by sku_code), increments stock, creates expense + local record.
        """
        product_sku_code = transfer.get("product_sku") or transfer["product_id"]
        product_name = transfer["product_name"]
        quantity = transfer["quantity"]
        unit_cost_paise = transfer["unit_cost_paise"]
        total_cost_paise = transfer["total_cost_paise"]
        central_id = transfer["transfer_id"]
        notes = transfer.get("notes")

        # Upsert SKU by sku_code
        sku = (
            self.db.query(SKU)
            .filter(SKU.sku_code == product_sku_code)
            .with_for_update()
            .first()
        )
        if sku is None:
            # Create minimal SKU for new-to-this-store product
            from app.models.inventory import UOMEnum
            sku = SKU(
                id=generate_ulid(),
                sku_code=product_sku_code,
                name=product_name,
                category_id=self._get_or_create_default_category_id(),
                uom=UOMEnum.PIECE,
                current_stock=0,
                avg_cost_per_unit=unit_cost_paise,
                is_active=True,
                reorder_point=0,
            )
            self.db.add(sku)
            self.db.flush()
            logger.info("Created new SKU %s for incoming transfer", product_sku_code)
        else:
            # Update weighted average cost
            existing_value = float(sku.current_stock) * sku.avg_cost_per_unit
            new_total_qty = float(sku.current_stock) + quantity
            if new_total_qty > 0:
                sku.avg_cost_per_unit = int(
                    (existing_value + unit_cost_paise * quantity) / new_total_qty
                )

        # Increment stock
        sku.current_stock = float(sku.current_stock) + quantity

        # Create TRANSFER_IN expense
        now = datetime.now(IST)
        source_store_id = transfer.get("source_store_id", "")
        expense = Expense(
            id=generate_ulid(),
            category=ExpenseCategory.TRANSFER_IN,
            amount=total_cost_paise,
            expense_date=now.date(),
            description=f"Transfer IN: {product_name} ×{quantity} from store {source_store_id}",
            notes=notes,
            is_recurring=False,
            status=ExpenseStatus.APPROVED,
            requires_approval=False,
            recorded_by=user_id,
            recorded_at=now,
            approved_by=user_id,
            approved_at=now,
        )
        self.db.add(expense)
        self.db.flush()

        # Create local transfer record
        local_transfer = InventoryTransfer(
            id=generate_ulid(),
            central_transfer_id=central_id,
            direction="IN",
            other_store_name=source_store_id,
            sku_id=sku.id,
            product_name=product_name,
            product_sku=product_sku_code,
            quantity=quantity,
            unit_cost_paise=unit_cost_paise,
            total_cost_paise=total_cost_paise,
            expense_id=expense.id,
            status="APPLIED",
            initiated_at=datetime.fromisoformat(transfer["initiated_at"])
            if transfer.get("initiated_at")
            else now,
            applied_at=now,
            notes=notes,
        )
        self.db.add(local_transfer)
        self.db.commit()
        return local_transfer

    # ------------------------------------------------------------------
    # Cancel (OUT)
    # ------------------------------------------------------------------

    def cancel_transfer(self, local_transfer_id: str, user_id: str) -> InventoryTransfer:
        """Cancel a pending outgoing transfer.

        1. Validates the transfer is PENDING + direction=OUT.
        2. Cancels on central API.
        3. Restores stock.
        4. Voids the expense (sets amount=0, description updated).
        5. Updates local status to CANCELLED.
        """
        local_transfer = (
            self.db.query(InventoryTransfer)
            .filter(InventoryTransfer.id == local_transfer_id)
            .first()
        )
        if not local_transfer:
            raise ValueError(f"Transfer {local_transfer_id} not found")

        if local_transfer.direction != "OUT":
            raise ValueError("Only outgoing (OUT) transfers can be cancelled from this store")

        if local_transfer.status != "PENDING":
            raise ValueError(
                f"Cannot cancel transfer in status {local_transfer.status}"
            )

        if not local_transfer.central_transfer_id:
            raise ValueError("Transfer has no central_transfer_id — cannot cancel")

        try:
            # Cancel on central
            client = self._get_client()
            response = client.patch(
                f"/v1/transfers/{local_transfer.central_transfer_id}/cancel"
            )
            response.raise_for_status()

            now = datetime.now(IST)

            # Restore stock
            sku = (
                self.db.query(SKU)
                .filter(SKU.id == local_transfer.sku_id)
                .with_for_update()
                .first()
            )
            if sku:
                sku.current_stock = float(sku.current_stock) + local_transfer.quantity

            # Void the expense (set amount to 0)
            if local_transfer.expense_id:
                expense = (
                    self.db.query(Expense)
                    .filter(Expense.id == local_transfer.expense_id)
                    .first()
                )
                if expense:
                    expense.amount = 0
                    expense.description = (
                        f"[CANCELLED] {expense.description}"
                    )

            # Update local transfer status
            local_transfer.status = "CANCELLED"
            local_transfer.cancelled_at = now
            self.db.commit()

            logger.info("Cancelled transfer %s", local_transfer_id)
            return local_transfer

        except Exception:
            self.db.rollback()
            raise
