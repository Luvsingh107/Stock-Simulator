"""Pytest configuration and shared fixtures."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from stock_simulator.models.quote import StockQuote
from stock_simulator.models.user import User
from stock_simulator.services import market_data


@pytest.fixture
def sample_quote() -> StockQuote:
    """Return a deterministic quote for testing."""
    data = pd.DataFrame(
        {
            "Date": [pd.Timestamp("2024-01-01").date()],
            "Time": [pd.Timestamp("2024-01-01 09:30:00").time()],
            "Open": [100.0],
            "High": [110.0],
            "Low": [90.0],
            "Close": [105.0],
            "Volume": [1000],
        }
    )
    return StockQuote(
        dataframe=data,
        current_price=105.0,
        period_high=110.0,
        period_low=90.0,
    )


@pytest.fixture
def mock_market_data(sample_quote: StockQuote):
    """Patch market data calls to return a fixed quote."""
    with patch.object(market_data, "get_stock_quote", return_value=sample_quote):
        with patch.object(market_data, "get_max_stock_value", return_value=110.0):
            with patch.object(market_data, "get_min_stock_value", return_value=90.0):
                yield sample_quote


@pytest.fixture
def user_with_balance() -> User:
    """Return a user with cash and no holdings."""
    return User(username="testuser", balance=10_000.0)


@pytest.fixture
def temp_data_dirs(tmp_path, monkeypatch):
    """Redirect data and log directories to a temp folder."""
    data_dir = tmp_path / "data"
    saves_dir = data_dir / "saves"
    keys_dir = data_dir / "keys"
    logs_dir = tmp_path / "logs"
    saves_dir.mkdir(parents=True)
    keys_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)

    monkeypatch.setattr("stock_simulator.utils.paths.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("stock_simulator.utils.paths.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("stock_simulator.utils.paths.get_saves_dir", lambda: saves_dir)
    monkeypatch.setattr("stock_simulator.utils.paths.get_keys_dir", lambda: keys_dir)
    monkeypatch.setattr("stock_simulator.utils.paths.get_logs_dir", lambda: logs_dir)
    monkeypatch.setattr("stock_simulator.utils.paths.get_legacy_saves_dir", lambda: tmp_path / "legacy")

    return tmp_path
