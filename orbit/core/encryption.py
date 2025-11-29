"""
Encryption utilities for secrets management.
Uses Fernet symmetric encryption for secure secret storage.
"""

import os
from cryptography.fernet import Fernet
from typing import Optional

from orbit.core.logging import get_logger

logger = get_logger("core.encryption")


class EncryptionService:
    """
    Service for encrypting and decrypting secrets.
    Uses Fernet symmetric encryption with a key from environment.
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service.

        Args:
            encryption_key: Base64-encoded Fernet key. If None, reads from env.
        """
        if encryption_key is None:
            encryption_key = os.getenv("ORBIT_ENCRYPTION_KEY")

        if not encryption_key:
            logger.warning(
                "No encryption key found. Generating a new key. "
                "Set ORBIT_ENCRYPTION_KEY environment variable for production."
            )
            encryption_key = Fernet.generate_key().decode()
            logger.info(f"Generated encryption key: {encryption_key}")

        try:
            self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise ValueError(f"Invalid encryption key: {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64-encoded)
        """
        try:
            encrypted = self.fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: Encrypted string (base64-encoded)

        Returns:
            Decrypted plaintext string
        """
        try:
            decrypted = self.fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded encryption key
        """
        return Fernet.generate_key().decode()


# Global encryption service instance
encryption_service = EncryptionService()
