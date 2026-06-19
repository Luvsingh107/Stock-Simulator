"""User account and order models."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stock_simulator.models.transaction import Transaction


@dataclass
class Order:
    """A pending buy or sell limit order."""

    amount: int
    price: float
    stock_symbol: str
    date: str = field(
        default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    status: str = "pending"


@dataclass
class Holding:
    """Cost-basis tracking for a single stock position."""

    symbol: str
    shares: int = 0
    average_cost: float = 0.0

    def add_shares(self, quantity: int, price: float) -> None:
        """Update average cost after a purchase."""
        if quantity <= 0:
            return
        total_cost = self.average_cost * self.shares + price * quantity
        self.shares += quantity
        self.average_cost = total_cost / self.shares if self.shares else 0.0

    def remove_shares(self, quantity: int) -> float:
        """Remove shares and return the cost basis of the sold portion."""
        if quantity <= 0 or quantity > self.shares:
            return 0.0
        cost_basis = self.average_cost * quantity
        self.shares -= quantity
        if self.shares == 0:
            self.average_cost = 0.0
        return cost_basis


@dataclass
class User:
    """A user account with balance, holdings, and orders."""

    username: str
    balance: float
    stocks: dict[str, int] = field(default_factory=dict)
    holdings: dict[str, Holding] = field(default_factory=dict)
    sell_orders: list[Order] = field(default_factory=list)
    buy_orders: list[Order] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)
    order_history: list[Order] = field(default_factory=list)
    realized_pnl: float = 0.0

    def get_holding(self, symbol: str) -> Holding:
        """Return or create a cost-basis holding for a symbol."""
        if symbol not in self.holdings:
            shares = self.stocks.get(symbol, 0)
            self.holdings[symbol] = Holding(symbol=symbol, shares=shares)
        return self.holdings[symbol]

    def sync_holdings_from_stocks(self) -> None:
        """Ensure holdings dict matches stocks dict (for v1 save migration)."""
        for symbol, shares in self.stocks.items():
            if symbol not in self.holdings:
                self.holdings[symbol] = Holding(symbol=symbol, shares=shares)
            elif self.holdings[symbol].shares != shares:
                self.holdings[symbol].shares = shares
