"""Input validation utilities."""

from __future__ import annotations

import re

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")

WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate a username for safe filesystem use.

    Returns (is_valid, error_message).
    """
    if not username:
        return False, "Username cannot be empty."
    if not USERNAME_PATTERN.match(username):
        return False, "Username must be 3-32 characters and contain only letters, numbers, underscores, or hyphens."
    if username.upper() in WINDOWS_RESERVED_NAMES:
        return False, f"'{username}' is a reserved name and cannot be used."
    if ".." in username or "/" in username or "\\" in username:
        return False, "Username cannot contain path separators."
    return True, ""


def parse_positive_int(value: str, field_name: str = "amount") -> tuple[int | None, str]:
    """Parse a positive integer from user input."""
    try:
        parsed = int(value)
    except ValueError:
        return None, f"Invalid {field_name}: '{value}' is not a whole number."
    if parsed < 1:
        return None, f"{field_name.capitalize()} must be at least 1."
    return parsed, ""


def parse_non_negative_float(value: str, field_name: str = "price") -> tuple[float | None, str]:
    """Parse a non-negative float from user input."""
    try:
        parsed = float(value)
    except ValueError:
        return None, f"Invalid {field_name}: '{value}' is not a number."
    if parsed < 0:
        return None, f"{field_name.capitalize()} cannot be negative."
    return parsed, ""
