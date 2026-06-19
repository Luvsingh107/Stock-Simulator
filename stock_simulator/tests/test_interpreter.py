"""Tests for CLI command handling."""

from stock_simulator.cli.interpreter import handle_command
from stock_simulator.models.user import User


def test_unknown_command(user_with_balance):
    result = handle_command("foobar", user_with_balance)
    assert not result.should_exit


def test_help_command(user_with_balance):
    result = handle_command("help", user_with_balance)
    assert not result.should_exit


def test_quit_command(user_with_balance):
    result = handle_command("quit", user_with_balance)
    assert result.should_exit


def test_buy_missing_args(user_with_balance):
    result = handle_command("buy AAPL", user_with_balance)
    assert not result.should_exit


def test_cancel_missing_args(user_with_balance):
    result = handle_command("cancel buy", user_with_balance)
    assert not result.should_exit


def test_price_command(mock_market_data, user_with_balance, capsys):
    handle_command("price AAPL", user_with_balance)
    captured = capsys.readouterr()
    assert "105.00" in captured.out


def test_portfolio_command(mock_market_data, user_with_balance, capsys):
    user_with_balance.stocks["AAPL"] = 5
    user_with_balance.get_holding("AAPL").add_shares(5, 100.0)
    handle_command("portfolio", user_with_balance)
    captured = capsys.readouterr()
    assert "PORTFOLIO" in captured.out


def test_history_command(user_with_balance, capsys):
    handle_command("history", user_with_balance)
    captured = capsys.readouterr()
    assert "No transactions" in captured.out
