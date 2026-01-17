"""Password handling utilities.

This module provides secure password hashing, verification, and strength
validation using bcrypt with configurable cost factors.
"""

from typing import List, Tuple
import bcrypt
from app.config import settings


class PasswordHandler:
    """Handle password hashing, verification, and validation."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using bcrypt.

        Args:
            password: The plaintext password to hash.

        Returns:
            str: The hashed password string.

        Example:
            >>> hashed = PasswordHandler.hash_password("MySecure123")
            >>> hashed.startswith("$2b$")
            True
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against its hash.

        Args:
            plain_password: The plaintext password to verify.
            hashed_password: The hashed password to compare against.

        Returns:
            bool: True if password matches, False otherwise.

        Example:
            >>> hashed = PasswordHandler.hash_password("MySecure123")
            >>> PasswordHandler.verify_password("MySecure123", hashed)
            True
            >>> PasswordHandler.verify_password("WrongPassword", hashed)
            False
        """
        try:
            password_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            # Handle invalid hash format or other errors
            return False

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
        """Validate password meets strength requirements.

        Password must:
        - Be at least 8 characters long (configurable)
        - Contain at least one uppercase letter
        - Contain at least one lowercase letter
        - Contain at least one number

        Args:
            password: The password to validate.

        Returns:
            tuple: (is_valid, error_messages)
                - is_valid: True if password meets all requirements
                - error_messages: List of validation error messages

        Example:
            >>> is_valid, errors = PasswordHandler.validate_password_strength("weak")
            >>> is_valid
            False
            >>> len(errors) > 0
            True
        """
        errors = []

        # Check minimum length
        if len(password) < settings.password_min_length:
            errors.append(
                f"Password must be at least {settings.password_min_length} characters long"
            )

        # Check for uppercase letter
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")

        # Check for lowercase letter
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")

        # Check for digit
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")

        return len(errors) == 0, errors

    @staticmethod
    def check_password_history(
        new_password_hash: str,
        previous_password_hashes: List[str]
    ) -> bool:
        """Check if new password was used recently.

        Args:
            new_password_hash: The hash of the new password.
            previous_password_hashes: List of previous password hashes to check.

        Returns:
            bool: True if password is reused, False if it's unique.

        Note:
            Compares up to last N passwords as configured in settings.password_history_count
        """
        if not previous_password_hashes:
            return False

        # Check against recent password hashes
        check_count = min(
            len(previous_password_hashes),
            settings.password_history_count
        )

        for old_hash in previous_password_hashes[-check_count:]:
            if new_password_hash == old_hash:
                return True

        return False

    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        """Check if password hash needs to be updated.

        This is useful when bcrypt cost factor changes or when
        the hashing algorithm is upgraded.

        Args:
            hashed_password: The hashed password to check.

        Returns:
            bool: True if hash should be regenerated.
        """
        try:
            # Extract cost factor from bcrypt hash
            # Format: $2b$rounds$salt$hash
            parts = hashed_password.split('$')
            if len(parts) >= 3:
                current_rounds = int(parts[2])
                return current_rounds < settings.bcrypt_rounds
            return False
        except Exception:
            return False
