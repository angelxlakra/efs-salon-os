"""SalonOS API - Main Application Module.

This module initializes the FastAPI application for SalonOS, a local-first
salon management system. It provides the core application setup and health
check endpoints.

The application is designed to run on a local network (LAN) with no cloud
dependencies, ensuring fast performance and data privacy for salon operations.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.auth.router import router as auth_router
from app.api.pos import router as pos_router
from app.api.catalog import router as catalog_router
from app.api.customers import router as customers_router

# Initialize FastAPI application
app = FastAPI(
    title="SalonOS API",
    version="0.1.0",
    description="Local-first salon management system for POS, scheduling, inventory, and accounting",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api", tags=["Authentication"])
app.include_router(pos_router, prefix="/api", tags=["POS"])
app.include_router(catalog_router, prefix="/api", tags=["Catalog"])
app.include_router(customers_router, prefix="/api", tags=["Customers"])


@app.get("/healthz")
def health_check():
    """Basic health check endpoint.

    This endpoint provides a simple liveness probe to verify that the API
    server is running and responding to requests. It does not check dependencies
    like database or Redis connectivity.

    Returns:
        dict: A JSON response with the health status.
            - status (str): Always returns "healthy" if the server is running.

    Example:
        >>> GET /healthz
        {"status": "healthy"}
    """
    return {"status": "healthy"}


@app.get("/readyz")
def readiness_check():
    """Readiness check endpoint.

    This endpoint provides a readiness probe to verify that the API server
    is ready to accept traffic. In future implementations, this will check
    connectivity to critical dependencies like PostgreSQL and Redis.

    Returns:
        dict: A JSON response with the readiness status.
            - status (str): Returns "ready" when the service can accept requests.
            - database (str): Database connectivity status (placeholder for now).

    Example:
        >>> GET /readyz
        {"status": "ready", "database": "not_checked"}

    Note:
        Database connection check will be implemented in spec-02.
    """
    # TODO: Add database connection check in spec-02
    return {"status": "ready", "database": "not_checked"}


@app.get("/")
def root():
    """Root endpoint providing API information.

    This endpoint returns basic information about the SalonOS API service,
    including the service name, version, and current operational status.

    Returns:
        dict: A JSON response with API metadata.
            - service (str): The name of the service.
            - version (str): The current API version.
            - status (str): Current operational status.

    Example:
        >>> GET /
        {
            "service": "SalonOS API",
            "version": "0.1.0",
            "status": "running"
        }
    """
    return {"service": "SalonOS API", "version": "0.1.0", "status": "running"}
