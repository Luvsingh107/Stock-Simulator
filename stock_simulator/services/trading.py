"""Trading logic: buy, sell, and order execution."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from stock_simulator.models.transaction import OrderStatus, Transaction, TransactionType
from stock_simulator.models.user import Order, User
from stock_simulator.services import market_data

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _reserved_balance(user: User, exclude_order: Order | None = None) -> float:
    """Sum of balance reserved by pending buy orders."""
    total = 0.0
    for buy_order in user.buy_orders:
        if exclude_order is not None and buy_order is exclude_order:
            continue
        total += float(buy_order.price) * buy_order.amount
    return total


def _available_balance(user: User, exclude_order: Order | None = None) -> float:
    """Cash available after pending buy order reservations."""
    return user.balance - _reserved_balance(user, exclude_order)


def _record_transaction(
    user: User,
    transaction_type: TransactionType,
    symbol: str,
    quantity: int,
    price: float,
    note: str = "",
) -> None:
    """Append a transaction to the user's history."""
    user.transactions.append(
        Transaction(
            transaction_type=transaction_type,
            symbol=symbol,
            quantity=quantity,
            price=price,
            note=note,
        )
    )


def buy_stocks(user: User, amount: int, price: float, stock_symbol: str, *, executing_order: Order | None = None) -> bool:
    """
    Buy shares at market or place a limit buy order.

    Returns True if the buy executed or a new order was placed successfully.
    """
    symbol = stock_symbol.upper()
    quote = market_data.get_stock_quote(symbol)
    market_price = quote.current_price
    execution_price = market_price if price == 0 else min(price, market_price)
    total_cost = execution_price * amount

    if _available_balance(user, exclude_order=executing_order) < total_cost:
        print("Insufficient funds. Cancel a pending buy order to free up balance.")
        return False

    if price != 0 and price < market_price:
        new_order = Order(amount=amount, price=price, stock_symbol=symbol)
        user.buy_orders.append(new_order)
        print(f"{user.username} placed a buy order for {amount} shares of {symbol} at ${price:.2f} each.")
        logger.info("Buy order placed: %s x%d @ $%.2f", symbol, amount, price)
        return True

    user.balance -= total_cost
    holding = user.get_holding(symbol)
    holding.add_shares(amount, execution_price)
    user.stocks[symbol] = holding.shares

    _record_transaction(user, TransactionType.BUY, symbol, amount, execution_price)
    print(
        f"{user.username} bought {amount} shares of {symbol} at ${execution_price:.2f} each, "
        f"for a total of ${total_cost:.2f}."
    )
    logger.info("Buy executed: %s x%d @ $%.2f", symbol, amount, execution_price)
    return True


def sell_stocks(user: User, amount: int, price: float, stock_symbol: str, *, executing_order: Order | None = None) -> bool:
    """
    Sell shares at market or place a limit sell order.

    Returns True if the sell executed or a new order was placed successfully.
    """
    symbol = stock_symbol.upper()
    quote = market_data.get_stock_quote(symbol)
    market_price = quote.current_price
    execution_price = market_price

    if symbol not in user.stocks or user.stocks[symbol] < amount:
        print("Insufficient shares. Cancel pending sell orders or buy more shares.")
        return False

    amount_already_listed = sum(
        order.amount for order in user.sell_orders if order.stock_symbol == symbol and order is not executing_order
    )
    if amount_already_listed + amount > user.stocks[symbol]:
        print("Insufficient shares available. Cancel pending sell orders to free up shares.")
        return False

    if price != 0 and price > market_price:
        new_order = Order(amount=amount, price=price, stock_symbol=symbol)
        user.sell_orders.append(new_order)
        print(f"{user.username} placed a sell order for {amount} shares of {symbol} at ${price:.2f} each.")
        logger.info("Sell order placed: %s x%d @ $%.2f", symbol, amount, price)
        return True

    total_proceeds = execution_price * amount
    holding = user.get_holding(symbol)
    cost_basis = holding.remove_shares(amount)
    realized = total_proceeds - cost_basis
    user.realized_pnl += realized

    user.balance += total_proceeds
    if holding.shares == 0:
        del user.stocks[symbol]
        del user.holdings[symbol]
    else:
        user.stocks[symbol] = holding.shares

    _record_transaction(user, TransactionType.SELL, symbol, amount, execution_price)
    print(
        f"{user.username} sold {amount} shares of {symbol} at ${execution_price:.2f} each, "
        f"for a total of ${total_proceeds:.2f}."
    )
    logger.info("Sell executed: %s x%d @ $%.2f (realized P/L: $%.2f)", symbol, amount, execution_price, realized)
    return True


def execute_buy_orders(user: User, stock_symbol: str, stock_price: float) -> list[Order]:
    """Execute eligible buy orders for a symbol at the current price."""
    filled: list[Order] = []
    for buy_order in list(user.buy_orders):
        if buy_order.stock_symbol == stock_symbol and buy_order.price >= stock_price:
            if buy_stocks(user, buy_order.amount, buy_order.price, buy_order.stock_symbol, executing_order=buy_order):
                buy_order.status = OrderStatus.FILLED.value
                user.order_history.append(buy_order)
                filled.append(buy_order)
                _record_transaction(
                    user,
                    TransactionType.ORDER_EXEC,
                    stock_symbol,
                    buy_order.amount,
                    stock_price,
                    note="buy order filled",
                )
    return filled


def execute_sell_orders(user: User, stock_symbol: str, stock_price: float) -> list[Order]:
    """Execute eligible sell orders for a symbol at the current price."""
    filled: list[Order] = []
    for sell_order in list(user.sell_orders):
        if sell_order.stock_symbol == stock_symbol and sell_order.price <= stock_price:
            if sell_stocks(user, sell_order.amount, sell_order.price, sell_order.stock_symbol, executing_order=sell_order):
                sell_order.status = OrderStatus.FILLED.value
                user.order_history.append(sell_order)
                filled.append(sell_order)
                _record_transaction(
                    user,
                    TransactionType.ORDER_EXEC,
                    stock_symbol,
                    sell_order.amount,
                    stock_price,
                    note="sell order filled",
                )
    return filled


def remove_executed_orders(user: User, orders_to_remove: list[Order], order_type: str) -> None:
    """Remove filled orders from the pending order list."""
    order_list = user.buy_orders if order_type == "buy" else user.sell_orders
    for order in orders_to_remove:
        if order in order_list:
            order_list.remove(order)


def check_orders(user: User) -> None:
    """Check and execute pending buy and sell orders against live prices."""
    symbols = {order.stock_symbol for order in user.buy_orders + user.sell_orders}
    for symbol in symbols:
        quote = market_data.get_stock_quote(symbol)
        buy_filled = execute_buy_orders(user, symbol, quote.current_price)
        remove_executed_orders(user, buy_filled, "buy")
        sell_filled = execute_sell_orders(user, symbol, quote.current_price)
        remove_executed_orders(user, sell_filled, "sell")


def _try_fill_buy_retroactive(user: User, buy_order: Order, time_now: datetime.datetime) -> bool:
    """Attempt to fill a buy order based on historical minimum price."""
    min_price = market_data.get_min_stock_value(buy_order.stock_symbol, buy_order.date, time_now)
    if buy_order.price < min_price:
        return False

    total_cost = buy_order.price * buy_order.amount
    if user.balance < total_cost:
        logger.warning(
            "Retroactive buy skipped for %s: insufficient balance ($%.2f needed, $%.2f available)",
            buy_order.stock_symbol,
            total_cost,
            user.balance,
        )
        return False

    user.balance -= total_cost
    holding = user.get_holding(buy_order.stock_symbol)
    holding.add_shares(buy_order.amount, buy_order.price)
    user.stocks[buy_order.stock_symbol] = holding.shares
    buy_order.status = OrderStatus.FILLED.value
    user.order_history.append(buy_order)
    _record_transaction(
        user,
        TransactionType.ORDER_EXEC,
        buy_order.stock_symbol,
        buy_order.amount,
        buy_order.price,
        note="retroactive buy order filled",
    )
    logger.info("Retroactive buy filled: %s", buy_order.stock_symbol)
    return True


def _try_fill_sell_retroactive(user: User, sell_order: Order, time_now: datetime.datetime) -> bool:
    """Attempt to fill a sell order based on historical maximum price."""
    max_price = market_data.get_max_stock_value(sell_order.stock_symbol, sell_order.date, time_now)
    if sell_order.price > max_price:
        return False

    if user.stocks.get(sell_order.stock_symbol, 0) < sell_order.amount:
        logger.warning("Retroactive sell skipped for %s: insufficient shares", sell_order.stock_symbol)
        return False

    proceeds = sell_order.price * sell_order.amount
    holding = user.get_holding(sell_order.stock_symbol)
    cost_basis = holding.remove_shares(sell_order.amount)
    user.realized_pnl += proceeds - cost_basis
    user.balance += proceeds
    if holding.shares == 0:
        del user.stocks[sell_order.stock_symbol]
        del user.holdings[sell_order.stock_symbol]
    else:
        user.stocks[sell_order.stock_symbol] = holding.shares

    sell_order.status = OrderStatus.FILLED.value
    user.order_history.append(sell_order)
    _record_transaction(
        user,
        TransactionType.ORDER_EXEC,
        sell_order.stock_symbol,
        sell_order.amount,
        sell_order.price,
        note="retroactive sell order filled",
    )
    logger.info("Retroactive sell filled: %s", sell_order.stock_symbol)
    return True


def check_orders_retroactive(user: User) -> None:
    """Fill pending orders that would have executed while the user was offline."""
    time_now = datetime.datetime.now()

    filled_buys = [order for order in list(user.buy_orders) if _try_fill_buy_retroactive(user, order, time_now)]
    for order in filled_buys:
        user.buy_orders.remove(order)

    filled_sells = [order for order in list(user.sell_orders) if _try_fill_sell_retroactive(user, order, time_now)]
    for order in filled_sells:
        user.sell_orders.remove(order)


def cancel_order(user: User, order_type: str, order_number: int) -> None:
    """Cancel a pending buy or sell order by its display number."""
    order_list = user.buy_orders if order_type.lower() == "buy" else user.sell_orders
    if order_type.lower() not in ("buy", "sell"):
        print("Invalid order type. Use 'buy' or 'sell'.")
        return

    if order_number < 1 or order_number > len(order_list):
        print("Invalid order number. Use 'portfolio' to see order numbers.")
        return

    order = order_list.pop(order_number - 1)
    order.status = OrderStatus.CANCELLED.value
    user.order_history.append(order)
    _record_transaction(
        user,
        TransactionType.ORDER_CANCEL,
        order.stock_symbol,
        order.amount,
        order.price,
        note=f"{order_type} order cancelled",
    )
    print(f"Cancelled {order_type} order for {order.amount} {order.stock_symbol} shares.")
