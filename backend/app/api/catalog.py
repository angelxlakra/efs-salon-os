"""Catalog API endpoints for services and categories.

This module provides REST API endpoints for:
- Managing service categories
- Managing services
- Managing service addons
- Listing the full service catalog
- Bulk importing catalog data
"""

from typing import Optional, List
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.user import User
from app.models.service import ServiceCategory, Service, ServiceAddon
from app.models.inventory import SKU
from app.auth.dependencies import get_current_user, require_owner
from app.services.staff_availability_service import StaffAvailabilityService
from app.services.inventory_service import InventoryService
from app.schemas.expense import RetailProductResponse
from app.schemas.catalog import (
    # Category schemas
    ServiceCategoryCreate,
    ServiceCategoryUpdate,
    ServiceCategoryResponse,
    ServiceCategoryListResponse,
    ServiceCategoryWithServices,
    # Service schemas
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    ServiceListResponse,
    ServiceWithAddons,
    ServiceWithCategory,
    # Addon schemas
    ServiceAddonCreate,
    ServiceAddonUpdate,
    ServiceAddonResponse,
    # Full catalog
    CatalogResponse,
)


router = APIRouter(prefix="/catalog", tags=["Catalog"])


# ========== Service Categories ==========

@router.get(
    "/categories",
    response_model=ServiceCategoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all service categories"
)
def list_categories(
    include_inactive: bool = Query(False, description="Include inactive categories"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all service categories.

    **Permissions**: Any authenticated user

    Args:
        include_inactive: Whether to include inactive categories (default: False).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        ServiceCategoryListResponse: List of categories.
    """
    query = db.query(ServiceCategory)

    if not include_inactive:
        query = query.filter(ServiceCategory.is_active == True)

    categories = query.order_by(ServiceCategory.display_order).all()

    return ServiceCategoryListResponse(
        categories=[ServiceCategoryResponse.model_validate(c) for c in categories],
        total=len(categories)
    )


@router.post(
    "/categories",
    response_model=ServiceCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a service category"
)
def create_category(
    category_data: ServiceCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Create a new service category.

    **Permissions**: Owner only

    Args:
        category_data: Category details.
        db: Database session.
        current_user: Authenticated owner.

    Returns:
        ServiceCategoryResponse: Created category.

    Raises:
        400: Category with same name already exists.
    """
    # Check for duplicate name
    existing = db.query(ServiceCategory).filter(
        ServiceCategory.name == category_data.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with name '{category_data.name}' already exists"
        )

    category = ServiceCategory(
        name=category_data.name,
        description=category_data.description,
        display_order=category_data.display_order,
        is_active=True
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return ServiceCategoryResponse.model_validate(category)


@router.get(
    "/categories/{category_id}",
    response_model=ServiceCategoryWithServices,
    status_code=status.HTTP_200_OK,
    summary="Get category with services"
)
def get_category(
    category_id: str,
    include_inactive_services: bool = Query(False, description="Include inactive services"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a category with its services.

    **Permissions**: Any authenticated user

    Args:
        category_id: Category ID.
        include_inactive_services: Whether to include inactive services.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        ServiceCategoryWithServices: Category with services.

    Raises:
        404: Category not found.
    """
    category = db.query(ServiceCategory).options(
        joinedload(ServiceCategory.services)
    ).filter(
        ServiceCategory.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_id}"
        )

    # Filter services if needed
    services = category.services
    if not include_inactive_services:
        services = [s for s in services if s.is_active and s.deleted_at is None]

    # Sort by display_order
    services = sorted(services, key=lambda s: s.display_order)

    return ServiceCategoryWithServices(
        id=category.id,
        name=category.name,
        description=category.description,
        display_order=category.display_order,
        is_active=category.is_active,
        created_at=category.created_at,
        updated_at=category.updated_at,
        services=[ServiceResponse.model_validate(s) for s in services]
    )


@router.patch(
    "/categories/{category_id}",
    response_model=ServiceCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a service category"
)
def update_category(
    category_id: str,
    category_data: ServiceCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Update a service category.

    **Permissions**: Owner only

    Args:
        category_id: Category ID.
        category_data: Fields to update.
        db: Database session.
        current_user: Authenticated owner.

    Returns:
        ServiceCategoryResponse: Updated category.

    Raises:
        400: Duplicate name.
        404: Category not found.
    """
    category = db.query(ServiceCategory).filter(
        ServiceCategory.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_id}"
        )

    # Check for duplicate name if updating
    if category_data.name and category_data.name != category.name:
        existing = db.query(ServiceCategory).filter(
            ServiceCategory.name == category_data.name,
            ServiceCategory.id != category_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with name '{category_data.name}' already exists"
            )

    # Update fields
    update_data = category_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    return ServiceCategoryResponse.model_validate(category)


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a service category"
)
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Deactivate a service category.

    **Permissions**: Owner only

    Note: This will mark the category as inactive and soft-delete all services in it.
    The category and its services are preserved in the database for historical records.

    Args:
        category_id: Category ID.
        db: Database session.
        current_user: Authenticated owner.

    Raises:
        404: Category not found.
        400: Cannot delete if category has active services.
    """
    category = db.query(ServiceCategory).filter(
        ServiceCategory.id == category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_id}"
        )

    # Check for active services in this category
    active_services = db.query(Service).filter(
        Service.category_id == category_id,
        Service.deleted_at.is_(None),
        Service.is_active == True
    ).count()

    if active_services > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category with {active_services} active services. Please delete or deactivate services first."
        )

    # Soft delete all inactive services in this category
    services = db.query(Service).filter(
        Service.category_id == category_id,
        Service.deleted_at.is_(None)
    ).all()

    for service in services:
        service.soft_delete()

    # Mark category as inactive (soft delete)
    category.is_active = False
    db.commit()


# ========== Services ==========

@router.get(
    "/services",
    response_model=ServiceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all services"
)
def list_services(
    category_id: Optional[str] = Query(None, description="Filter by category"),
    include_inactive: bool = Query(False, description="Include inactive services"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all services with optional filtering.

    **Permissions**: Any authenticated user

    Args:
        category_id: Optional category filter.
        include_inactive: Whether to include inactive services.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        ServiceListResponse: List of services.
    """
    query = db.query(Service).options(
        joinedload(Service.category)
    ).filter(
        Service.deleted_at.is_(None)
    )

    if not include_inactive:
        query = query.filter(Service.is_active == True)

    if category_id:
        query = query.filter(Service.category_id == category_id)

    services = query.order_by(Service.display_order).all()

    service_list = []
    for s in services:
        service_data = ServiceWithCategory(
            id=s.id,
            category_id=s.category_id,
            name=s.name,
            description=s.description,
            base_price=s.base_price,
            duration_minutes=s.duration_minutes,
            display_order=s.display_order,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
            category=ServiceCategoryResponse.model_validate(s.category) if s.category else None
        )
        service_list.append(service_data)

    return ServiceListResponse(
        services=service_list,
        total=len(service_list)
    )


@router.post(
    "/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a service"
)
def create_service(
    service_data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Create a new service.

    **Permissions**: Owner only

    Args:
        service_data: Service details.
        db: Database session.
        current_user: Authenticated owner.

    Returns:
        ServiceResponse: Created service.

    Raises:
        400: Category not found.
    """
    # Verify category exists
    category = db.query(ServiceCategory).filter(
        ServiceCategory.id == service_data.category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category not found: {service_data.category_id}"
        )

    service = Service(
        category_id=service_data.category_id,
        name=service_data.name,
        description=service_data.description,
        base_price=service_data.base_price,
        duration_minutes=service_data.duration_minutes,
        display_order=service_data.display_order,
        is_active=True
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return ServiceResponse.model_validate(service)


@router.get(
    "/services/{service_id}",
    response_model=ServiceWithAddons,
    status_code=status.HTTP_200_OK,
    summary="Get service details"
)
def get_service(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get service details with addons.

    **Permissions**: Any authenticated user

    Args:
        service_id: Service ID.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        ServiceWithAddons: Service with addons.

    Raises:
        404: Service not found.
    """
    service = db.query(Service).options(
        joinedload(Service.category),
        joinedload(Service.addons)
    ).filter(
        Service.id == service_id,
        Service.deleted_at.is_(None)
    ).first()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service not found: {service_id}"
        )

    return ServiceWithAddons(
        id=service.id,
        category_id=service.category_id,
        name=service.name,
        description=service.description,
        base_price=service.base_price,
        duration_minutes=service.duration_minutes,
        display_order=service.display_order,
        is_active=service.is_active,
        created_at=service.created_at,
        updated_at=service.updated_at,
        category=ServiceCategoryResponse.model_validate(service.category) if service.category else None,
        addons=[ServiceAddonResponse.model_validate(a) for a in service.addons]
    )


@router.patch(
    "/services/{service_id}",
    response_model=ServiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a service"
)
def update_service(
    service_id: str,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Update a service.

    **Permissions**: Owner only

    Args:
        service_id: Service ID.
        service_data: Fields to update.
        db: Database session.
        current_user: Authenticated owner.

    Returns:
        ServiceResponse: Updated service.

    Raises:
        400: Invalid category.
        404: Service not found.
    """
    service = db.query(Service).filter(
        Service.id == service_id,
        Service.deleted_at.is_(None)
    ).first()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service not found: {service_id}"
        )

    # Verify new category if updating
    if service_data.category_id and service_data.category_id != service.category_id:
        category = db.query(ServiceCategory).filter(
            ServiceCategory.id == service_data.category_id
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category not found: {service_data.category_id}"
            )

    # Update fields
    update_data = service_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)

    db.commit()
    db.refresh(service)

    return ServiceResponse.model_validate(service)


@router.delete(
    "/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a service (soft delete)"
)
def delete_service(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Soft delete a service.

    **Permissions**: Owner only

    The service is not permanently deleted but marked as deleted.
    Historical bills will still reference the service.

    Args:
        service_id: Service ID.
        db: Database session.
        current_user: Authenticated owner.

    Raises:
        404: Service not found.
    """
    service = db.query(Service).filter(
        Service.id == service_id,
        Service.deleted_at.is_(None)
    ).first()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service not found: {service_id}"
        )

    # Soft delete
    service.soft_delete()
    db.commit()


# ========== Service Addons ==========

@router.post(
    "/services/{service_id}/addons",
    response_model=ServiceAddonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add addon to service"
)
def create_addon(
    service_id: str,
    addon_data: ServiceAddonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Add an addon to a service.

    **Permissions**: Owner only

    Args:
        service_id: Service ID.
        addon_data: Addon details.
        db: Database session.
        current_user: Authenticated owner.

    Returns:
        ServiceAddonResponse: Created addon.

    Raises:
        404: Service not found.
    """
    service = db.query(Service).filter(
        Service.id == service_id,
        Service.deleted_at.is_(None)
    ).first()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service not found: {service_id}"
        )

    addon = ServiceAddon(
        service_id=service_id,
        name=addon_data.name,
        price=addon_data.price
    )

    db.add(addon)
    db.commit()
    db.refresh(addon)

    return ServiceAddonResponse.model_validate(addon)


@router.patch(
    "/addons/{addon_id}",
    response_model=ServiceAddonResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a service addon"
)
def update_addon(
    addon_id: str,
    addon_data: ServiceAddonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Update a service addon.

    **Permissions**: Owner only

    Args:
        addon_id: Addon ID.
        addon_data: Fields to update.
        db: Database session.
        current_user: Authenticated owner.

    Returns:
        ServiceAddonResponse: Updated addon.

    Raises:
        404: Addon not found.
    """
    addon = db.query(ServiceAddon).filter(
        ServiceAddon.id == addon_id
    ).first()

    if not addon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Addon not found: {addon_id}"
        )

    # Update fields
    update_data = addon_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(addon, field, value)

    db.commit()
    db.refresh(addon)

    return ServiceAddonResponse.model_validate(addon)


@router.delete(
    "/addons/{addon_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a service addon"
)
def delete_addon(
    addon_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Delete a service addon.

    **Permissions**: Owner only

    Args:
        addon_id: Addon ID.
        db: Database session.
        current_user: Authenticated owner.

    Raises:
        404: Addon not found.
    """
    addon = db.query(ServiceAddon).filter(
        ServiceAddon.id == addon_id
    ).first()

    if not addon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Addon not found: {addon_id}"
        )

    db.delete(addon)
    db.commit()


# ========== Bulk Import ==========

@router.post(
    "/import",
    status_code=status.HTTP_200_OK,
    summary="Bulk import categories and services from CSV"
)
async def bulk_import_catalog(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Bulk import categories and services from CSV file.

    **Permissions**: Owner only

    CSV Format:
    - Headers: type,category_name,name,description,base_price,duration_minutes,display_order
    - type: "category" or "service"
    - category_name: Category name (for services, must match existing or new category)
    - name: Name of category or service
    - description: Description
    - base_price: Price in rupees (for services only, e.g., 500.00)
    - duration_minutes: Duration in minutes (for services only, e.g., 30)
    - display_order: Display order (integer)

    Example CSV:
    ```
    type,category_name,name,description,base_price,duration_minutes,display_order
    category,,Haircut & Styling,Hair cutting and styling services,,,1
    service,Haircut & Styling,Basic Haircut,Simple haircut for men,300,15,1
    service,Haircut & Styling,Premium Haircut,Premium styling with consultation,500,30,2
    category,,Hair Color & Treatment,Hair coloring and treatment services,,,2
    service,Hair Color & Treatment,Full Hair Color,Complete hair coloring,2500,120,1
    ```

    Returns:
        Summary of import results.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file"
        )

    try:
        # Read CSV file
        contents = await file.read()
        decoded = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded))

        categories_created = 0
        services_created = 0
        errors = []
        category_map = {}  # Maps category names to IDs

        # Load existing categories
        existing_categories = db.query(ServiceCategory).all()
        for cat in existing_categories:
            category_map[cat.name] = cat.id

        row_num = 1
        for row in csv_reader:
            row_num += 1
            try:
                row_type = row.get('type', '').strip().lower()

                if row_type == 'category':
                    # Create category
                    name = row.get('name', '').strip()
                    description = row.get('description', '').strip()
                    display_order = int(row.get('display_order', 0))

                    if not name:
                        errors.append(f"Row {row_num}: Category name is required")
                        continue

                    # Check if category already exists
                    if name in category_map:
                        errors.append(f"Row {row_num}: Category '{name}' already exists")
                        continue

                    category = ServiceCategory(
                        name=name,
                        description=description,
                        display_order=display_order,
                        is_active=True
                    )
                    db.add(category)
                    db.flush()  # Get ID without committing
                    category_map[name] = category.id
                    categories_created += 1

                elif row_type == 'service':
                    # Create service
                    category_name = row.get('category_name', '').strip()
                    name = row.get('name', '').strip()
                    description = row.get('description', '').strip()
                    base_price_str = row.get('base_price', '').strip()
                    duration_str = row.get('duration_minutes', '').strip()
                    display_order = int(row.get('display_order', 0))

                    if not name:
                        errors.append(f"Row {row_num}: Service name is required")
                        continue

                    if not category_name:
                        errors.append(f"Row {row_num}: category_name is required for services")
                        continue

                    if category_name not in category_map:
                        errors.append(f"Row {row_num}: Category '{category_name}' not found. Create category first.")
                        continue

                    # Parse price (convert rupees to paise)
                    try:
                        base_price_rupees = float(base_price_str) if base_price_str else 0
                        base_price = int(base_price_rupees * 100)  # Convert to paise
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid base_price '{base_price_str}'")
                        continue

                    # Parse duration
                    try:
                        duration_minutes = int(duration_str) if duration_str else 30
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid duration_minutes '{duration_str}'")
                        continue

                    service = Service(
                        category_id=category_map[category_name],
                        name=name,
                        description=description,
                        base_price=base_price,
                        duration_minutes=duration_minutes,
                        display_order=display_order,
                        is_active=True
                    )
                    db.add(service)
                    services_created += 1

                else:
                    if row_type:  # Only log error if type field is not empty
                        errors.append(f"Row {row_num}: Invalid type '{row_type}'. Must be 'category' or 'service'")

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue

        # Commit all changes
        db.commit()

        return {
            "success": True,
            "categories_created": categories_created,
            "services_created": services_created,
            "errors": errors,
            "total_rows_processed": row_num - 1
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV file: {str(e)}"
        )


# ========== Full Catalog ==========

@router.get(
    "",
    response_model=CatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full service catalog"
)
def get_catalog(
    include_inactive: bool = Query(False, description="Include inactive items"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the full service catalog organized by category.

    **Permissions**: Any authenticated user

    Returns categories with their services, ordered by display_order.
    This is optimized for displaying the full POS catalog.

    Args:
        include_inactive: Whether to include inactive categories and services.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        CatalogResponse: Full catalog with categories and services.
    """
    query = db.query(ServiceCategory).options(
        joinedload(ServiceCategory.services)
    )

    if not include_inactive:
        query = query.filter(ServiceCategory.is_active == True)

    categories = query.order_by(ServiceCategory.display_order).all()

    result_categories = []
    for category in categories:
        # Filter and sort services
        services = category.services
        if not include_inactive:
            services = [s for s in services if s.is_active and s.deleted_at is None]
        services = sorted(services, key=lambda s: s.display_order)

        result_categories.append(
            ServiceCategoryWithServices(
                id=category.id,
                name=category.name,
                description=category.description,
                display_order=category.display_order,
                is_active=category.is_active,
                created_at=category.created_at,
                updated_at=category.updated_at,
                services=[ServiceResponse.model_validate(s) for s in services]
            )
        )

    return CatalogResponse(categories=result_categories)


# ========== Retail Products ==========

@router.get(
    "/retail-products",
    response_model=List[RetailProductResponse],
    status_code=status.HTTP_200_OK,
    summary="List retail products available for sale"
)
def list_retail_products(
    category_id: Optional[str] = Query(None, description="Filter by inventory category"),
    in_stock_only: bool = Query(True, description="Only show products in stock"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List retail products (sellable inventory items).

    **Permissions**: Any authenticated user

    Returns SKUs marked as sellable with retail pricing.
    Useful for POS when selling retail products directly to customers.

    Args:
        category_id: Optional inventory category filter.
        in_stock_only: Whether to only return products with stock (default: True).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        List[RetailProductResponse]: List of sellable products.
    """
    inventory_service = InventoryService(db)
    products = inventory_service.get_retail_products(
        category_id=category_id,
        in_stock_only=in_stock_only,
        is_active_only=True
    )

    # Convert to response schema
    result = []
    for product in products:
        result.append(RetailProductResponse(
            id=product.id,
            sku_code=product.sku_code,
            name=product.name,
            description=product.description,
            retail_price=product.retail_price,
            current_stock=float(product.current_stock),
            uom=product.uom.value,
            category_name=product.category.name if product.category else "Unknown",
            category_id=product.category_id
        ))

    return result


# ========== Service Analytics ==========

@router.post(
    "/services/update-average-durations",
    status_code=status.HTTP_200_OK,
    summary="Update average service durations from historical data"
)
def update_service_average_durations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner)
):
    """Update average_duration_minutes for all services based on historical completion data.

    **Permission**: Owner only

    This endpoint calculates the average actual duration for each service based on
    completed walk-ins from the last 90 days. The average is stored in the
    `average_duration_minutes` field and is used to estimate wait times.

    **Use Cases**:
    - Run manually after significant service time changes
    - Schedule as a nightly background job
    - Initial setup to populate historical averages

    **How it works**:
    - Analyzes completed walk-ins from the last 90 days
    - Calculates average time between `started_at` and `completed_at`
    - Updates `average_duration_minutes` for each service
    - Services with no historical data keep their default `duration_minutes`

    Returns:
        Dict with:
        - updated_count: Number of services with updated averages
        - averages: Dict mapping service_id to calculated average
    """
    service = StaffAvailabilityService(db)
    averages = service.calculate_service_average_durations()
    updated_count = service.update_service_average_durations()

    return {
        "updated_count": updated_count,
        "averages": averages,
        "message": f"Successfully updated average durations for {updated_count} service(s)"
    }
