"""
Database configuration and session management for the salon service app.

This module sets up the SQLAlchemy engine, session factory, and declarative base
used throughout the application for ORM models.

Exports:
    - engine: The SQLAlchemy engine connected to the configured database.
    - SessionLocal: The session factory for creating new database sessions.
    - Base: The declarative base class for ORM models.
    - get_db: Dependency function for acquiring and releasing DB sessions in FastAPI endpoints.
"""


import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://salon_user:change_me_123@postgres:5432/salon_db"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10,
    echo=False,  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    """
    Database session dependency for FastAPI endpoints.
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()