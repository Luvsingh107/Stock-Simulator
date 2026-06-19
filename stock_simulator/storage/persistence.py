"""Persistence layer for user save files."""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from cryptography.fernet import InvalidToken

from stock_simulator.models.transaction import Transaction, TransactionType
from stock_simulator.models.user import Holding, Order, User
from stock_simulator.storage import encryption
from stock_simulator.utils.paths import get_legacy_save_path, get_save_path, get_saves_dir

logger = logging.getLogger(__name__)

SCHEMA_V1 = "v1"
SCHEMA_V2 = "v2"


def user_file_exists(user: User) -> bool:
    """Check whether a save file exists for the user."""
    return get_save_path(user.username).exists() or get_legacy_save_path(user.username).exists()


def create_user_file(user: User) -> None:
    """Create a new encrypted save file and encryption key."""
    save_path = get_save_path(user.username)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if save_path.exists():
        raise FileExistsError(f"Save file already exists for user '{user.username}'.")

    key = encryption.generate_key()
    encryption.save_key(user.username, key)
    save_path.touch()


def _format_orders(orders: list[Order]) -> str:
    parts = []
    for order in orders:
        date_str = order.date if isinstance(order.date, str) else str(order.date)
        parts.append(f"{order.stock_symbol};{order.amount};{order.price};{date_str}")
    return ",".join(parts) + ("," if parts else "")


def _format_stocks(user: User) -> str:
    parts = [f"{symbol};{amount}" for symbol, amount in user.stocks.items()]
    return ",".join(parts) + ("," if parts else "")


def _serialize_v2_payload(user: User) -> str:
    """Serialize user state to the v2 plaintext format before encryption."""
    lines = [
        SCHEMA_V2,
        str(user.balance),
        _format_stocks(user),
        _format_orders(user.sell_orders),
        _format_orders(user.buy_orders),
        str(user.realized_pnl),
        json.dumps(
            {
                symbol: {"shares": h.shares, "average_cost": h.average_cost}
                for symbol, h in user.holdings.items()
            }
        ),
        json.dumps(
            [
                {
                    "type": t.transaction_type.value,
                    "symbol": t.symbol,
                    "quantity": t.quantity,
                    "price": t.price,
                    "timestamp": t.timestamp,
                    "total": t.total,
                    "note": t.note,
                }
                for t in user.transactions
            ]
        ),
        json.dumps(
            [
                {
                    "amount": o.amount,
                    "price": o.price,
                    "stock_symbol": o.stock_symbol,
                    "date": o.date if isinstance(o.date, str) else str(o.date),
                    "status": o.status,
                }
                for o in user.order_history
            ]
        ),
    ]
    return "\n".join(lines) + "\n"


def _parse_orders(order_string: str) -> list[Order]:
    orders: list[Order] = []
    if not order_string.strip():
        return orders
    for entry in order_string.split(","):
        if not entry.strip():
            continue
        parts = entry.split(";")
        if len(parts) < 4:
            continue
        symbol, amount, price, date = parts[0], parts[1], parts[2], parts[3]
        orders.append(Order(amount=int(amount), price=float(price), stock_symbol=symbol, date=date))
    return orders


def _deserialize_payload(data: str, user: User) -> None:
    """Load plaintext save data into a User object."""
    lines = data.split("\n")
    if not lines:
        raise ValueError("Save file is empty.")

    if lines[0] in (SCHEMA_V1, SCHEMA_V2):
        schema = lines[0]
        offset = 1
    else:
        schema = SCHEMA_V1
        offset = 0

    user.balance = float(lines[offset])
    user.stocks = {}
    stock_string = lines[offset + 1] if len(lines) > offset + 1 else ""
    for entry in stock_string.split(","):
        if not entry.strip():
            continue
        symbol, amount = entry.split(";")
        user.stocks[symbol] = int(amount)

    user.sell_orders = _parse_orders(lines[offset + 2] if len(lines) > offset + 2 else "")
    user.buy_orders = _parse_orders(lines[offset + 3] if len(lines) > offset + 3 else "")

    user.realized_pnl = 0.0
    user.holdings = {}
    user.transactions = []
    user.order_history = []

    if schema == SCHEMA_V2 and len(lines) > offset + 4:
        user.realized_pnl = float(lines[offset + 4] or 0)
        if len(lines) > offset + 5 and lines[offset + 5].strip():
            holdings_data = json.loads(lines[offset + 5])
            for symbol, info in holdings_data.items():
                user.holdings[symbol] = Holding(
                    symbol=symbol,
                    shares=int(info["shares"]),
                    average_cost=float(info["average_cost"]),
                )
        if len(lines) > offset + 6 and lines[offset + 6].strip():
            for item in json.loads(lines[offset + 6]):
                user.transactions.append(
                    Transaction(
                        transaction_type=TransactionType(item["type"]),
                        symbol=item["symbol"],
                        quantity=int(item["quantity"]),
                        price=float(item["price"]),
                        timestamp=item["timestamp"],
                        total=float(item.get("total", 0)),
                        note=item.get("note", ""),
                    )
                )
        if len(lines) > offset + 7 and lines[offset + 7].strip():
            for item in json.loads(lines[offset + 7]):
                user.order_history.append(
                    Order(
                        amount=int(item["amount"]),
                        price=float(item["price"]),
                        stock_symbol=item["stock_symbol"],
                        date=item["date"],
                        status=item.get("status", "filled"),
                    )
                )

    user.sync_holdings_from_stocks()


def _resolve_save_path(username: str) -> Path:
    """Return the path to an existing save file, checking legacy location."""
    new_path = get_save_path(username)
    if new_path.exists():
        return new_path
    legacy_path = get_legacy_save_path(username)
    if legacy_path.exists():
        return legacy_path
    return new_path


def load_user(user: User) -> None:
    """Load encrypted user data from disk."""
    save_path = _resolve_save_path(user.username)
    if not save_path.exists():
        raise FileNotFoundError(f"No save file found for user '{user.username}'.")

    encrypted_data = save_path.read_text(encoding="utf-8")
    key = encryption.load_key(user.username)

    try:
        plaintext = encryption.decrypt_data(encrypted_data, key)
    except InvalidToken as exc:
        raise ValueError("Save file could not be decrypted. The file may be corrupted.") from exc

    _deserialize_payload(plaintext, user)
    logger.info("Loaded save file for user '%s'", user.username)


def save_user(user: User) -> None:
    """Atomically write encrypted user data to disk."""
    save_path = get_save_path(user.username)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    plaintext = _serialize_v2_payload(user)
    key = encryption.load_key(user.username)
    encrypted_data = encryption.encrypt_data(plaintext, key)

    tmp_path = save_path.with_suffix(".tmp")
    tmp_path.write_text(encrypted_data, encoding="utf-8")

    # Validate round-trip before replacing the original file
    decrypted = encryption.decrypt_data(tmp_path.read_text(encoding="utf-8"), key)
    if decrypted != plaintext:
        tmp_path.unlink(missing_ok=True)
        raise IOError("Save validation failed: decrypted data does not match.")

    if hasattr(os, "replace"):
        os.replace(tmp_path, save_path)
    else:
        shutil.move(str(tmp_path), str(save_path))

    logger.info("Saved user data for '%s'", user.username)


def migrate_legacy_save(user: User) -> None:
    """Migrate a legacy-format save to the new location and schema."""
    legacy_path = get_legacy_save_path(user.username)
    if legacy_path.exists() and not get_save_path(user.username).exists():
        get_saves_dir().mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_path, get_save_path(user.username))
        logger.info("Migrated legacy save file for '%s'", user.username)
