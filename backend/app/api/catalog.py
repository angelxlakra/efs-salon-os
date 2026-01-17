"""Catalog API endpoints for services and categories.

This module provides REST API endpoints for:
- Managing service categories
- Managing services
- Managing service addons
- Listing the full service catalog
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.user import User
from app.models.service import ServiceCategory, Service, ServiceAddon
from app.auth.dependencies import get_current_user, require_owner
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
