"""Portfolio analytics and display."""

from __future__ import annotations

from dataclasses import dataclass

from stock_simulator.models.user import User
from stock_simulator.services import market_data


@dataclass
class PortfolioSummary:
    """Aggregated portfolio metrics."""

    cash: float
    available_cash: float
    holdings_value: float
    total_value: float
    unrealized_pnl: float
    realized_pnl: float


def _reserved_balance(user: User) -> float:
    return sum(float(order.price) * order.amount for order in user.buy_orders)


def compute_portfolio_summary(user: User) -> PortfolioSummary:
    """Calculate portfolio value and profit/loss metrics."""
    reserved = _reserved_balance(user)
    available_cash = user.balance - reserved
    holdings_value = 0.0
    unrealized_pnl = 0.0

    for symbol, shares in user.stocks.items():
        quote = market_data.get_stock_quote(symbol)
        market_value = quote.current_price * shares
        holdings_value += market_value
        holding = user.get_holding(symbol)
        if holding.shares > 0:
            unrealized_pnl += (quote.current_price - holding.average_cost) * shares

    return PortfolioSummary(
        cash=user.balance,
        available_cash=available_cash,
        holdings_value=holdings_value,
        total_value=user.balance + holdings_value,
        unrealized_pnl=unrealized_pnl,
        realized_pnl=user.realized_pnl,
    )


def display_portfolio(user: User) -> None:
    """Print the user's portfolio, orders, and analytics."""
    summary = compute_portfolio_summary(user)

    print("PORTFOLIO\n")
    print(f"BALANCE: ${summary.cash:.2f} (available: ${summary.available_cash:.2f})")
    print(f"HOLDINGS VALUE: ${summary.holdings_value:.2f}")
    print(f"TOTAL VALUE: ${summary.total_value:.2f}")
    print(f"UNREALIZED P/L: ${summary.unrealized_pnl:.2f}")
    print(f"REALIZED P/L: ${summary.realized_pnl:.2f}\n")

    print("STOCKS")
    if not user.stocks:
        print("  (none)")
    for symbol, shares in user.stocks.items():
        quote = market_data.get_stock_quote(symbol)
        holding = user.get_holding(symbol)
        market_value = quote.current_price * shares
        position_pnl = (quote.current_price - holding.average_cost) * shares
        print(
            f"  {shares} {symbol} @ avg ${holding.average_cost:.2f} "
            f"(market: ${quote.current_price:.2f}, value: ${market_value:.2f}, P/L: ${position_pnl:.2f})"
        )

    print("\nBUY ORDERS")
    if not user.buy_orders:
        print("  (none)")
    for index, order in enumerate(user.buy_orders, start=1):
        total = order.amount * order.price
        print(
            f"  #{index}: {order.amount} {order.stock_symbol} at ${order.price:.2f}/share "
            f"(total: ${total:.2f}) ordered at [{order.date}]"
        )

    print("\nSELL ORDERS")
    if not user.sell_orders:
        print("  (none)")
    for index, order in enumerate(user.sell_orders, start=1):
        total = order.amount * order.price
        print(
            f"  #{index}: {order.amount} {order.stock_symbol} at ${order.price:.2f}/share "
            f"(total: ${total:.2f}) ordered at [{order.date}]"
        )


def display_cash(user: User) -> None:
    """Print the user's cash balance."""
    summary = compute_portfolio_summary(user)
    print(f"BALANCE: ${summary.cash:.2f} (available: ${summary.available_cash:.2f})")


def display_history(user: User, limit: int = 10) -> None:
    """Print recent transaction history."""
    if not user.transactions:
        print("No transactions recorded yet.")
        return

    print(f"TRANSACTION HISTORY (last {limit})\n")
    for txn in user.transactions[-limit:]:
        print(
            f"  [{txn.timestamp}] {txn.transaction_type.value.upper()} "
            f"{txn.quantity} {txn.symbol} @ ${txn.price:.2f} (total: ${txn.total:.2f})"
            + (f" — {txn.note}" if txn.note else "")
        )


def display_order_history(user: User, limit: int = 10) -> None:
    """Print completed and cancelled order history."""
    if not user.order_history:
        print("No order history yet.")
        return

    print(f"ORDER HISTORY (last {limit})\n")
    for order in user.order_history[-limit:]:
        print(
            f"  [{order.date}] {order.status.upper()} — "
            f"{order.amount} {order.stock_symbol} @ ${order.price:.2f}/share"
        )
