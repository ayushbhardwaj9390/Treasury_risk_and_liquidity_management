"""Validate all dummy positions against unchanged treasury engines in isolated DBs."""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.db import Base
from app.core.config import settings
from app.models import BankAccount, CashFlow, FXRate, LegalEntity, DerivativePosition
from app.services.liquidity import calculate_global_liquidity
from app.services.forecast import calculate_liquidity_forecast
from app.services.derivative_risk import calculate_hedge_coverage


def money(value):
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def add_entity(db, definition, state):
    entity = LegalEntity(name=definition["name"], country_code=definition["country"], functional_currency=definition["functionalCurrency"], minimum_cash=Decimal(definition["buffer"]))
    db.add(entity); db.flush()
    for currency in definition["bankCurrencies"]:
        db.add(BankAccount(entity_id=entity.id, bank_name="FICTIONAL_TEST", country_code=definition["country"], currency=currency,
            book_balance=Decimal(state["balances"][currency]), restricted_balance=Decimal(definition["restricted"]) if currency == definition["functionalCurrency"] else 0,
            committed_outflows=Decimal(definition["committed"]) if currency == definition["functionalCurrency"] else 0))
    for flow in state["flows"]:
        if flow["entity"] == definition["id"]:
            db.add(CashFlow(entity_id=entity.id, flow_type="RECEIVABLE" if flow["direction"] == "INFLOW" else "PAYABLE",
                counterparty="FICTIONAL_TEST", currency=flow["currency"], amount=Decimal(flow["amount"]),
                probability=Decimal(flow["probability"]), due_date=date.fromisoformat(flow["date"])))
    return entity


def add_rates(db, state):
    for currency, rate in state["rates"].items():
        db.add(FXRate(base_currency=currency, quote_currency="USD", rate=Decimal(rate), source="SYNTHETIC", as_of=datetime(2026, 10, 8)))


def verify_entity_forecasts(source, case, definitions):
    for definition in definitions:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        try:
            with Session(engine) as db:
                # Independently derive opening cash and buffer from source balances
                # and entity assumptions, rather than expected TS position totals.
                add_entity(db, definition, case["state"])
                add_rates(db, case["state"])
                db.commit()
                forecast = calculate_liquidity_forecast(db, "BASE", 13, date.fromisoformat(source["start"]))
                expected = next(row for row in case["positions"]["entities"] if row["id"] == definition["id"])
                context = (case["scope"], case["cycle"], definition["id"])
                assert expected["maximumShortfall"] == money(forecast.maximum_shortfall), context
                assert expected["firstBreach"] == forecast.first_buffer_breach_week, context
        finally:
            engine.dispose()


def run():
    assert settings.group_reporting_currency == "USD", "Parity fixture requires USD reporting"
    source = json.loads((ROOT / "frontend/lib/dummy-feed.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "frontend/tests/fixtures/automatic-engine.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        state, expected = case["state"], case["positions"]
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        try:
            with Session(engine) as db:
                definitions = source["multinational"]["entities"] if case["scope"] == "mnc" else [{"id": "DEMO", "name": "Harbor Manufacturing US", "country": "US", "functionalCurrency": "USD", "bankCurrencies": ["USD", "EUR", "GBP"], "buffer": source["buffer"], "restricted": source["restricted"], "committed": source["committed"]}]
                entities = {}
                for definition in definitions:
                    entities[definition["id"]] = add_entity(db, definition, state)
                add_rates(db, state)
                for hedge in state["hedges"]:
                    db.add(DerivativePosition(entity_id=next(iter(entities.values())).id, instrument_type="FX_FORWARD", counterparty="FICTIONAL_TEST",
                        exposure_currency=hedge["currency"], notional=Decimal(hedge["amount"]), hedge_direction=hedge["direction"], maturity_date=date(2027, 3, 1)))
                db.commit()
                liquidity = calculate_global_liquidity(db)
                assert expected["gross"] == money(liquidity.gross_cash), case["cycle"]
                assert expected["deployable"] == money(liquidity.deployable_cash), case["cycle"]
                assert expected["headroom"] == money(liquidity.liquidity_headroom), case["cycle"]
                for position in expected["entities"]:
                    component = next(row for row in liquidity.entities if row.entity_id == entities[position["id"]].id)
                    assert position["deployableLocal"] == money(component.deployable_cash_local), (case["scope"], case["cycle"], position["id"])
                    assert position["deployable"] == money(component.deployable_cash_reporting)
                    assert position["buffer"] == money(component.minimum_cash_reporting)
                    assert position["headroom"] == money(component.liquidity_headroom_reporting)
                forecast = calculate_liquidity_forecast(db, "BASE", 13, date.fromisoformat(source["start"]))
                assert expected["forecast"]["ending"] == money(forecast.ending_cash), case["cycle"]
                assert expected["forecast"]["maximumShortfall"] == money(forecast.maximum_shortfall), case["cycle"]
                assert expected["forecast"]["firstBreach"] == forecast.first_buffer_breach_week, case["cycle"]
                for actual, point in zip(forecast.points, expected["forecast"]["points"], strict=True):
                    assert point["closing"] == money(actual.closing_cash), case["cycle"]
                    assert point["shortfall"] == money(actual.shortfall), case["cycle"]
                coverage = {row.currency: row for row in calculate_hedge_coverage(db)}
                residual_usd = Decimal(0)
                for hedge in expected["hedges"]:
                    actual = coverage[hedge["currency"]]
                    assert hedge["underlying"] == money(actual.underlying_exposure), case["cycle"]
                    assert hedge["hedge"] == money(actual.hedge_notional), case["cycle"]
                    assert hedge["residual"] == money(actual.residual_exposure), case["cycle"]
                    assert hedge["ratio"] == (None if actual.hedge_ratio is None else money(actual.hedge_ratio * 100)), case["cycle"]
                    assert hedge["status"] == actual.status, case["cycle"]
                    residual_usd += abs(actual.residual_exposure) * Decimal(state["rates"][actual.currency])
                assert expected["residualUsd"] == money(residual_usd), case["cycle"]
        finally:
            engine.dispose()
        verify_entity_forecasts(source, case, definitions)
    print(json.dumps({"cycles": len(cases), "entity_forecasts": sum(len(case["positions"]["entities"]) for case in cases), "result": "PASS", "persistent_company_writes": False, "live_ai_calls": 0}))


if __name__ == "__main__":
    run()
