"""Inventory service for retail product operations."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.inventory import SKU, StockLedger
from app.models.user import User


class InventoryService:
    """Service for handling retail product operations."""

    def __init__(self, db: Session):
        self.db = db

    def validate_sellable_product(
        self,
        sku_id: str,
        quantity: Decimal,
        raise_on_error: bool = True
    ) -> Optional[SKU]:
        """
        Validate that a product can be sold.

        Args:
            sku_id: SKU ID to validate
            quantity: Quantity requested
            raise_on_error: Whether to raise HTTPException or return None

        Returns:
            SKU if valid, None if invalid and raise_on_error=False

        Raises:
            HTTPException: If product is not sellable or out of stock
        """
        sku = self.db.query(SKU).filter(SKU.id == sku_id).first()

        if not sku:
            if raise_on_error:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product not found: {sku_id}"
                )
            return None

        if not sku.is_active:
            if raise_on_error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product is inactive: {sku.name}"
                )
            return None

        if not sku.is_sellable:
            if raise_on_error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product is not available for retail sale: {sku.name}"
                )
            return None

        if sku.retail_price is None or sku.retail_price <= 0:
            if raise_on_error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product does not have a valid retail price: {sku.name}"
                )
            return None

        if sku.current_stock < quantity:
            if raise_on_error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {sku.name}. Available: {sku.current_stock} {sku.uom}, Requested: {quantity} {sku.uom}"
                )
            return None

        return sku

    def reduce_stock_for_sale(
        self,
        sku_id: str,
        quantity: Decimal,
        bill_id: str,
        user_id: str
    ) -> StockLedger:
        """
        Reduce stock when a product is sold.

        Creates a StockLedger entry with transaction_type="sale".

        Args:
            sku_id: SKU ID to reduce
            quantity: Quantity sold
            bill_id: Bill ID for reference
            user_id: User making the sale

        Returns:
            Created StockLedger entry

        Raises:
            HTTPException: If validation fails
        """
        # Validate product
        sku = self.validate_sellable_product(sku_id, quantity, raise_on_error=True)

        # Calculate quantities
        quantity_change = -quantity  # Negative for reduction
        quantity_after = sku.current_stock + quantity_change

        # Calculate cost (for COGS tracking)
        unit_cost = sku.avg_cost_per_unit
        total_value = int(unit_cost * float(quantity))

        # Create ledger entry
        ledger_entry = StockLedger(
            sku_id=sku_id,
            transaction_type="sale",
            quantity_change=quantity_change,
            quantity_after=quantity_after,
            unit_cost=unit_cost,
            total_value=total_value,
            avg_cost_after=unit_cost,  # Doesn't change on sale
            reference_type="bill",
            reference_id=bill_id,
            notes=f"Retail sale of {quantity} {sku.uom}",
            created_by=user_id
        )
        self.db.add(ledger_entry)

        # Update SKU stock
        sku.current_stock = quantity_after

        # Commit changes
        self.db.commit()
        self.db.refresh(ledger_entry)

        return ledger_entry

    def calculate_product_cogs(self, sku_id: str, quantity: Decimal) -> int:
        """
        Calculate COGS for a retail product.

        Args:
            sku_id: SKU ID
            quantity: Quantity sold

        Returns:
            COGS amount in paise
        """
        sku = self.db.query(SKU).filter(SKU.id == sku_id).first()
        if not sku:
            return 0

        return int(sku.avg_cost_per_unit * float(quantity))

    def get_retail_products(
        self,
        category_id: Optional[str] = None,
        in_stock_only: bool = True,
        is_active_only: bool = True
    ) -> list[SKU]:
        """
        Get list of retail products.

        Args:
            category_id: Optional category filter
            in_stock_only: Only return products with stock
            is_active_only: Only return active products

        Returns:
            List of SKU objects
        """
        query = self.db.query(SKU).filter(SKU.is_sellable == True)

        if category_id:
            query = query.filter(SKU.category_id == category_id)

        if is_active_only:
            query = query.filter(SKU.is_active == True)

        if in_stock_only:
            query = query.filter(SKU.current_stock > 0)

        return query.order_by(SKU.name).all()
