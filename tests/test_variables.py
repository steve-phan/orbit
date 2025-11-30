"""
Tests for variables and secrets functionality.
"""

import pytest

from orbit.core.encryption import EncryptionService, encryption_service


def test_encryption_service_initialization():
    """Test encryption service can be initialized."""
    service = EncryptionService()
    assert service.fernet is not None


def test_encrypt_decrypt():
    """Test basic encryption and decryption."""
    service = EncryptionService()

    plaintext = "my_secret_password"
    encrypted = service.encrypt(plaintext)

    # Encrypted should be different from plaintext
    assert encrypted != plaintext

    # Decryption should return original
    decrypted = service.decrypt(encrypted)
    assert decrypted == plaintext


def test_encrypt_decrypt_special_characters():
    """Test encryption with special characters."""
    service = EncryptionService()

    plaintext = "P@ssw0rd!#$%^&*()"
    encrypted = service.encrypt(plaintext)
    decrypted = service.decrypt(encrypted)

    assert decrypted == plaintext


def test_encrypt_decrypt_unicode():
    """Test encryption with unicode characters."""
    service = EncryptionService()

    plaintext = "Hello 世界 🌍"
    encrypted = service.encrypt(plaintext)
    decrypted = service.decrypt(encrypted)

    assert decrypted == plaintext


def test_generate_key():
    """Test key generation."""
    key1 = EncryptionService.generate_key()
    key2 = EncryptionService.generate_key()

    # Keys should be different
    assert key1 != key2

    # Keys should be valid
    service1 = EncryptionService(key1)
    service2 = EncryptionService(key2)

    assert service1.fernet is not None
    assert service2.fernet is not None


def test_different_keys_produce_different_ciphertexts():
    """Test that different keys produce different encrypted values."""
    plaintext = "secret"

    service1 = EncryptionService(EncryptionService.generate_key())
    service2 = EncryptionService(EncryptionService.generate_key())

    encrypted1 = service1.encrypt(plaintext)
    encrypted2 = service2.encrypt(plaintext)

    # Same plaintext, different keys = different ciphertexts
    assert encrypted1 != encrypted2


def test_wrong_key_fails_decryption():
    """Test that decryption fails with wrong key."""
    plaintext = "secret"

    service1 = EncryptionService(EncryptionService.generate_key())
    service2 = EncryptionService(EncryptionService.generate_key())

    encrypted = service1.encrypt(plaintext)

    # Decryption with wrong key should fail
    with pytest.raises(Exception):
        service2.decrypt(encrypted)


def test_global_encryption_service():
    """Test global encryption service instance."""
    plaintext = "test_secret"

    encrypted = encryption_service.encrypt(plaintext)
    decrypted = encryption_service.decrypt(encrypted)

    assert decrypted == plaintext


def test_variable_interpolation_pattern():
    """Test variable interpolation pattern matching."""
    import re

    pattern = r'\$\{([^:]+):([^}]+)\}'

    # Test various patterns
    text1 = "${var:api_url}"
    matches1 = re.findall(pattern, text1)
    assert matches1 == [("var", "api_url")]

    text2 = "${secret:api_key}"
    matches2 = re.findall(pattern, text2)
    assert matches2 == [("secret", "api_key")]

    text3 = "URL: ${var:base_url}/api, Key: ${secret:token}"
    matches3 = re.findall(pattern, text3)
    assert matches3 == [("var", "base_url"), ("secret", "token")]

    text4 = "${global:timeout}"
    matches4 = re.findall(pattern, text4)
    assert matches4 == [("global", "timeout")]
