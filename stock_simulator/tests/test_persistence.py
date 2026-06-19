"""Tests for encrypted persistence."""

from stock_simulator.models.user import User
from stock_simulator.storage.persistence import (
    create_user_file,
    load_user,
    save_user,
    user_file_exists,
)
from stock_simulator.services import trading


def test_create_and_save_user(temp_data_dirs, mock_market_data):
    user = User(username="alice", balance=5000.0)
    create_user_file(user)
    holding = user.get_holding("AAPL")
    holding.add_shares(10, 100.0)
    user.stocks["AAPL"] = holding.shares
    save_user(user)

    loaded = User(username="alice", balance=0.0)
    load_user(loaded)
    assert loaded.balance == 5000.0
    assert loaded.stocks["AAPL"] == 10
    assert loaded.holdings["AAPL"].average_cost == 100.0


def test_user_file_exists(temp_data_dirs):
    user = User(username="bob", balance=100.0)
    assert not user_file_exists(user)
    create_user_file(user)
    assert user_file_exists(user)


def test_round_trip_with_transactions(temp_data_dirs, mock_market_data):
    user = User(username="carol", balance=10_000.0)
    create_user_file(user)
    trading.buy_stocks(user, 5, 0, "AAPL")
    save_user(user)

    loaded = User(username="carol", balance=0.0)
    load_user(loaded)
    assert len(loaded.transactions) == 1
    assert loaded.stocks["AAPL"] == 5


def test_v1_format_backward_compat(temp_data_dirs):
    """Load a v1-format save without schema header."""
    from stock_simulator.storage import encryption

    user = User(username="dave", balance=0.0)
    create_user_file(user)
    key = encryption.load_key("dave")
    v1_plaintext = "1000.0\nAAPL;5,\n\n\n"
    encrypted = encryption.encrypt_data(v1_plaintext, key)
    from stock_simulator.utils.paths import get_save_path

    get_save_path("dave").write_text(encrypted, encoding="utf-8")

    loaded = User(username="dave", balance=0.0)
    load_user(loaded)
    assert loaded.balance == 1000.0
    assert loaded.stocks["AAPL"] == 5
