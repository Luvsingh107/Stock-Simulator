"""Encryption key management."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from cryptography.fernet import Fernet

from stock_simulator.utils.paths import get_keys_dir, get_legacy_saves_dir


def _key_path(username: str) -> Path:
    return get_keys_dir() / f"{username}.key"


def _legacy_key_path(username: str) -> Path:
    return get_legacy_saves_dir() / f"{username}_key"


def save_key(username: str, key: bytes) -> None:
    """Persist an encryption key in the dedicated keys directory."""
    path = _key_path(username)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_key(username: str) -> bytes:
    """Load an encryption key, migrating from legacy location if needed."""
    path = _key_path(username)
    if path.exists():
        return path.read_bytes()

    legacy_path = _legacy_key_path(username)
    if legacy_path.exists():
        key = legacy_path.read_bytes()
        save_key(username, key)
        try:
            legacy_path.unlink()
        except OSError:
            pass
        return key

    raise FileNotFoundError(f"Encryption key not found for user '{username}'.")


def generate_key() -> bytes:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key()


def encrypt_data(data: str, key: bytes) -> str:
    """Encrypt a string payload."""
    return Fernet(key).encrypt(data.encode()).decode()


def decrypt_data(data: str, key: bytes) -> str:
    """Decrypt an encrypted string payload."""
    return Fernet(key).decrypt(data.encode()).decode()
