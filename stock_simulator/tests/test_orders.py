"""Tests for order execution and cancellation."""

from stock_simulator.models.user import Order, User
from stock_simulator.services import trading


def test_execute_buy_orders(mock_market_data, user_with_balance):
    user = user_with_balance
    order = Order(amount=5, price=110.0, stock_symbol="AAPL")
    user.buy_orders.append(order)
    filled = trading.execute_buy_orders(user, "AAPL", 105.0)
    assert len(filled) == 1
    assert user.stocks.get("AAPL") == 5


def test_failed_buy_order_not_removed(mock_market_data):
    user = User(username="poor", balance=100.0)
    order = Order(amount=10, price=110.0, stock_symbol="AAPL")
    user.buy_orders.append(order)
    filled = trading.execute_buy_orders(user, "AAPL", 105.0)
    assert len(filled) == 0
    assert len(user.buy_orders) == 1


def test_execute_sell_orders(mock_market_data, user_with_balance):
    user = user_with_balance
    trading.buy_stocks(user, 10, 0, "AAPL")
    order = Order(amount=5, price=100.0, stock_symbol="AAPL")
    user.sell_orders.append(order)
    filled = trading.execute_sell_orders(user, "AAPL", 105.0)
    assert len(filled) == 1
    assert user.stocks["AAPL"] == 5


def test_cancel_order(mock_market_data, user_with_balance):
    user = user_with_balance
    trading.buy_stocks(user, 5, 50.0, "AAPL")
    trading.cancel_order(user, "buy", 1)
    assert len(user.buy_orders) == 0
    assert len(user.order_history) == 1


def test_check_orders_retroactive_no_mutation_skip(mock_market_data, user_with_balance):
    user = user_with_balance
    user.buy_orders = [
        Order(amount=5, price=95.0, stock_symbol="AAPL"),
        Order(amount=3, price=95.0, stock_symbol="AAPL"),
    ]
    trading.check_orders_retroactive(user)
    assert len(user.buy_orders) == 0
    assert user.stocks["AAPL"] == 8


def test_retroactive_buy_skipped_insufficient_balance(mock_market_data):
    user = User(username="poor", balance=100.0)
    user.buy_orders = [Order(amount=10, price=95.0, stock_symbol="AAPL")]
    trading.check_orders_retroactive(user)
    assert len(user.buy_orders) == 1
