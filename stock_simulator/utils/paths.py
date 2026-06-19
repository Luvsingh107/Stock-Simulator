"""Path helpers for runtime data directories."""

from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PACKAGE_ROOT.parent


def get_data_dir() -> Path:
    return PROJECT_ROOT / "data"


def get_saves_dir() -> Path:
    return get_data_dir() / "saves"


def get_keys_dir() -> Path:
    return get_data_dir() / "keys"


def get_logs_dir() -> Path:
    return PROJECT_ROOT / "logs"


def get_legacy_saves_dir() -> Path:
    """Original save location for backward-compatible migration."""
    legacy = PROJECT_ROOT / "Stock-Market-Sim" / "src" / "saves"
    if legacy.exists():
        return legacy
    return PACKAGE_ROOT / "data" / "legacy_saves"


def get_legacy_save_path(username: str) -> Path:
    return get_legacy_saves_dir() / username


def get_save_path(username: str) -> Path:
    return get_saves_dir() / f"{username}.enc"


def ensure_runtime_dirs() -> None:
    """Create runtime directories if they do not exist."""
    get_saves_dir().mkdir(parents=True, exist_ok=True)
    get_keys_dir().mkdir(parents=True, exist_ok=True)
    get_logs_dir().mkdir(parents=True, exist_ok=True)
    (get_logs_dir() / "users").mkdir(parents=True, exist_ok=True)
