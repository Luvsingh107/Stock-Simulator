"""Transaction and order history models."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum


class TransactionType(str, Enum):
    """Types of recorded account activity."""

    BUY = "buy"
    SELL = "sell"
    ORDER_EXEC = "order_exec"
    ORDER_CANCEL = "order_cancel"


class OrderStatus(str, Enum):
    """Lifecycle status for orders."""

    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class Transaction:
    """A single recorded transaction in the user's history."""

    transaction_type: TransactionType
    symbol: str
    quantity: int
    price: float
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    total: float = 0.0
    note: str = ""

    def __post_init__(self) -> None:
        if self.total == 0.0:
            self.total = self.price * self.quantity
