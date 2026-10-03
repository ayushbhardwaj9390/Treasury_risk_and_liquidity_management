"""Independent numerical references. Synthetic benchmarks do not certify pricing."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from math import exp, log, sqrt
from types import SimpleNamespace

import pytest
from scipy.stats import norm

from app.services import institutional_risk as pricing


@pytest.fixture
def market(monkeypatch):
    monkeypatch.setattr(pricing, "latest_rate", lambda db, base, quote: Decimal("1.1"))
    monkeypatch.setattr(pricing, "_curve_rate", lambda db, currency, days:
                        (.04 if currency == "USD" else .02, datetime(2026, 10, 3), "SYNTHETIC"))
    monkeypatch.setattr(pricing, "convert", lambda db, amount, source, target: amount)


@pytest.mark.parametrize("days", [30, 365])
@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_forward_discounted_cashflow_reference(market, days, direction):
    trade = SimpleNamespace(maturity_date=date.today() + timedelta(days=days), notional=Decimal("1000000"), hedge_direction=direction)
    terms = SimpleNamespace(currency_pair="EUR/USD", contracted_rate=Decimal("1.12"))
    actual, _, _ = pricing._price_fx_forward(None, trade, terms)
    t = days / 365
    expected = 1000000 * (1.1 * exp(-.02 * t) - 1.12 * exp(-.04 * t))
    if direction == "SELL":
        expected = -expected
    assert float(actual) == pytest.approx(expected, abs=1e-7)


@pytest.mark.parametrize("days", [30, 365])
@pytest.mark.parametrize("volatility", [.01, .2, 1.0])
@pytest.mark.parametrize("option_type", ["CALL", "PUT"])
def test_fx_option_scipy_reference(market, monkeypatch, days, volatility, option_type):
    monkeypatch.setattr(pricing, "_volatility", lambda db, pair, days: (volatility, datetime(2026, 10, 3), "SYNTHETIC"))
    trade = SimpleNamespace(maturity_date=date.today() + timedelta(days=days), notional=Decimal("1000000"))
    terms = SimpleNamespace(currency_pair="EUR/USD", strike=Decimal("1.12"), option_type=option_type)
    actual, _, _ = pricing._price_fx_option(None, trade, terms)
    t = days / 365
    forward = 1.1 * exp(.02 * t)
    std = volatility * sqrt(t)
    d1 = log(forward / 1.12) / std + std / 2
    d2 = d1 - std
    call = exp(-.04 * t) * (forward * norm.cdf(d1) - 1.12 * norm.cdf(d2))
    unit = call if option_type == "CALL" else call - exp(-.04 * t) * (forward - 1.12)
    assert float(actual) == pytest.approx(1000000 * unit, abs=1e-7)
