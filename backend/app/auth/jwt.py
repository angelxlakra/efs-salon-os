"""JWT token handling for authentication.

This module provides utilities for creating and validating JWT access and refresh
tokens with role-based claims and optional device binding.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from jose import jwt
from ulid import ULID
from app.config import settings
from app.models.user import User


class JWTHandler:
    """Handle JWT token creation and validation.

    This class provides methods to create access and refresh tokens,
    decode and validate tokens, and extract user information from token payloads.
    """

    ALGORITHM = settings.algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
    REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

    @classmethod
    def create_access_token(
        cls,
        user: User,
        device_id: Optional[str] = None
    ) -> str:
        """Create JWT access token for user.

        Args:
            user: The User model instance.
            device_id: Optional device identifier for device binding.

        Returns:
            str: Encoded JWT access token.

        Example:
            >>> user = db.query(User).first()
            >>> token = JWTHandler.create_access_token(user)
            >>> isinstance(token, str)
            True
        """
        expire = datetime.utcnow() + timedelta(
            minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        payload = {
            "sub": user.id,  # Subject: user ID
            "username": user.username,
            "role": user.role.name.value,
            "type": "access",
            "iat": datetime.utcnow(),  # Issued at
            "exp": expire  # Expiration
        }

        if device_id:
            payload["device_id"] = device_id

        return jwt.encode(
            payload,
            settings.secret_key,
            algorithm=cls.ALGORITHM
        )

    @classmethod
    def create_refresh_token(
        cls,
        user: User,
        device_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """Create JWT refresh token for user.

        Args:
            user: The User model instance.
            device_id: Optional device identifier for device binding.

        Returns:
            tuple: (token, jti) - The encoded token and unique token ID.

        Example:
            >>> user = db.query(User).first()
            >>> token, jti = JWTHandler.create_refresh_token(user)
            >>> isinstance(token, str) and isinstance(jti, str)
            True
        """
        jti = str(ULID())  # Unique token identifier for revocation
        expire = datetime.utcnow() + timedelta(
            days=cls.REFRESH_TOKEN_EXPIRE_DAYS
        )

        payload = {
            "sub": user.id,
            "type": "refresh",
            "jti": jti,  # JWT ID for revocation tracking
            "iat": datetime.utcnow(),
            "exp": expire
        }

        if device_id:
            payload["device_id"] = device_id

        token = jwt.encode(
            payload,
            settings.secret_key,
            algorithm=cls.ALGORITHM
        )

        return token, jti

    @classmethod
    def decode_token(cls, token: str) -> Dict[str, Any]:
        """Decode and verify JWT token.

        Args:
            token: The JWT token string to decode.

        Returns:
            dict: Decoded token payload.

        Raises:
            ValueError: If token is expired or invalid.

        Example:
            >>> token = JWTHandler.create_access_token(user)
            >>> payload = JWTHandler.decode_token(token)
            >>> "sub" in payload
            True
        """
        try:
            return jwt.decode(
                token,
                settings.secret_key,
                algorithms=[cls.ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    @classmethod
    def get_token_type(cls, token: str) -> Optional[str]:
        """Get token type without full validation.

        Args:
            token: The JWT token string.

        Returns:
            str: Token type ("access" or "refresh"), or None if invalid.
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[cls.ALGORITHM],
                options={"verify_exp": False}  # Don't verify expiration
            )
            return payload.get("type")
        except Exception:
            return None

    @classmethod
    def extract_user_id(cls, token: str) -> Optional[str]:
        """Extract user ID from token without full validation.

        Useful for logging or tracking purposes where token might be expired.

        Args:
            token: The JWT token string.

        Returns:
            str: User ID from token subject, or None if invalid.
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[cls.ALGORITHM],
                options={"verify_exp": False}
            )
            return payload.get("sub")
        except Exception:
            return None

    @classmethod
    def get_token_expiry(cls, token: str) -> Optional[datetime]:
        """Get token expiration time.

        Args:
            token: The JWT token string.

        Returns:
            datetime: Token expiration timestamp, or None if invalid.
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[cls.ALGORITHM],
                options={"verify_exp": False}
            )
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp)
            return None
        except Exception:
            return None
