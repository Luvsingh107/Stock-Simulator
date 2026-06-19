"""Tests for buy/sell trading logic."""

from stock_simulator.models.user import User
from stock_simulator.services import trading


def test_market_buy(mock_market_data, user_with_balance):
    user = user_with_balance
    assert trading.buy_stocks(user, 10, 0, "AAPL")
    assert user.stocks["AAPL"] == 10
    assert user.balance == 10_000 - 10 * 105.0
    assert len(user.transactions) == 1


def test_buy_insufficient_funds(mock_market_data):
    user = User(username="poor", balance=100.0)
    assert not trading.buy_stocks(user, 10, 0, "AAPL")
    assert "AAPL" not in user.stocks


def test_limit_buy_order_placed(mock_market_data, user_with_balance):
    user = user_with_balance
    assert trading.buy_stocks(user, 5, 50.0, "AAPL")
    assert len(user.buy_orders) == 1
    assert user.buy_orders[0].price == 50.0


def test_market_sell(mock_market_data, user_with_balance):
    user = user_with_balance
    trading.buy_stocks(user, 10, 0, "AAPL")
    starting_balance = user.balance
    assert trading.sell_stocks(user, 5, 0, "AAPL")
    assert user.stocks["AAPL"] == 5
    assert user.balance == starting_balance + 5 * 105.0


def test_sell_insufficient_shares(mock_market_data, user_with_balance):
    user = user_with_balance
    assert not trading.sell_stocks(user, 5, 0, "AAPL")


def test_cost_basis_tracking(mock_market_data, user_with_balance):
    user = user_with_balance
    trading.buy_stocks(user, 10, 0, "AAPL")
    holding = user.get_holding("AAPL")
    assert holding.average_cost == 105.0
    assert holding.shares == 10


def test_realized_pnl_on_sell(mock_market_data, user_with_balance):
    user = user_with_balance
    trading.buy_stocks(user, 10, 0, "AAPL")
    trading.sell_stocks(user, 5, 0, "AAPL")
    assert user.realized_pnl == 0.0  # same buy/sell price


def test_market_buy_respects_pending_orders(mock_market_data, user_with_balance):
    user = user_with_balance
    trading.buy_stocks(user, 50, 50.0, "AAPL")  # reserves 2500
    user.balance = 3000.0
    assert not trading.buy_stocks(user, 10, 0, "AAPL")  # needs 1050, only 500 available
