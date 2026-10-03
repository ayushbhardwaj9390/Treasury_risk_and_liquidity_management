"""Run fictional energy cash flows through unchanged engines, without persistent writes."""
import copy
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import Base
from app.models import BankAccount, CashFlow, FXRate, LegalEntity
from app.services.forecast import calculate_liquidity_forecast
from app.services.liquidity import calculate_global_liquidity
from app.services.production import require_live_release, snapshot
from app.schemas.production import ReleaseCreate
from app.services.production import create_release
from app.models import UserAccount


def run():
    source = ROOT / "pilot/ENERGY_DEMO_SCENARIO.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    assert data["kind"] == "SYNTHETIC" and settings.group_reporting_currency == "USD"
    assumptions = data["calculation_assumptions"]
    rates = {k: Decimal(v) for k, v in assumptions["fx_usd_per_unit"].items()}
    start = date.fromisoformat(data["as_of"])
    opening = sum(Decimal(b["amount"]) * rates[b["currency"]] for b in data["opening_cash"])
    buffer = sum(Decimal(v) for v in assumptions["minimum_cash_usd"].values())
    report = {"kind": "SYNTHETIC", "production_status": "BLOCKED_EXTERNAL_EVIDENCE",
              "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "as_of": data["as_of"], "assumptions": assumptions, "scenarios": []}
    for code in ("BASE", "RECEIPT_DELAY", "CARGO_COST_UP", "USD_FUNDING_PRESSURE", "COMBINED"):
        flows = copy.deepcopy(data["cashflows"])
        for f in flows:
            if code in {"RECEIPT_DELAY", "COMBINED"} and f["id"] == "DEMO_DIESEL_SALE":
                f["date"] = (date.fromisoformat(f["date"]) + timedelta(days=10)).isoformat()
            if code in {"CARGO_COST_UP", "COMBINED"} and f["id"] == "DEMO_CRUDE_PURCHASE":
                f["amount"] = str(Decimal(f["amount"]) * Decimal("1.20"))
            if code in {"USD_FUNDING_PRESSURE", "COMBINED"} and f["direction"] == "OUTFLOW" and f["currency"] != "USD":
                # Cost uplift only; opening balances and FX quotes remain fixed.
                f["amount"] = str(Decimal(f["amount"]) * Decimal("1.10"))
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        try:
            with Session(engine) as db:
                entities = []
                for name, country in (("DEMO_UK_ENERGY", "GB"), ("DEMO_SINGAPORE_TRADING", "SG")):
                    entity = LegalEntity(name=name, country_code=country, functional_currency="USD",
                                         minimum_cash=Decimal(assumptions["minimum_cash_usd"][name]))
                    db.add(entity)
                    entities.append(entity)
                db.flush()
                for b in data["opening_cash"]:
                    entity = entities[1] if b["currency"] == "SGD" else entities[0]
                    db.add(BankAccount(entity_id=entity.id, bank_name="SIMULATED_BANK", country_code=entity.country_code,
                                       currency=b["currency"], book_balance=Decimal(b["amount"])))
                for currency, rate in rates.items():
                    if currency != "USD":
                        db.add(FXRate(base_currency=currency, quote_currency="USD", rate=rate,
                                      source="SYNTHETIC", as_of=datetime.combine(start, datetime.min.time())))
                for f in flows:
                    db.add(CashFlow(entity_id=entities[1 if f["currency"] == "SGD" else 0].id,
                        flow_type="RECEIVABLE" if f["direction"] == "INFLOW" else "PAYABLE",
                        counterparty="FICTIONAL_COUNTERPARTY", currency=f["currency"], amount=Decimal(f["amount"]),
                        due_date=date.fromisoformat(f["date"]), source_reference=f["id"], probability=1))
                db.commit()
                liquidity = calculate_global_liquidity(db)
                forecast = calculate_liquidity_forecast(db, "BASE", assumptions["forecast_weeks"], start)
                assert liquidity.deployable_cash == opening and liquidity.minimum_cash == buffer
                cash = opening
                for point in forecast.points:
                    incoming = outgoing = Decimal(0)
                    for f in flows:
                        if point.week_start <= date.fromisoformat(f["date"]) <= point.week_end:
                            amount = Decimal(f["amount"]) * rates[f["currency"]]
                            if f["direction"] == "INFLOW":
                                incoming += amount
                            else:
                                outgoing += amount
                    cash += incoming - outgoing
                    assert point.expected_inflows == incoming and point.expected_outflows == outgoing
                    assert point.closing_cash == cash and point.liquidity_headroom == cash - buffer
                assert not forecast.warnings
                report["scenarios"].append({"case": code, "arithmetic_check": "PASS",
                                            "opening_liquidity": liquidity.model_dump(mode="json"),
                                            "forecast": forecast.model_dump(mode="json")})
                if code == "BASE":
                    db.add(UserAccount(username="synthetic_pilot_maker", display_name="Synthetic pilot maker",
                                       role="GROUP_TREASURER", active=True))
                    db.commit()
                    rid = create_release(db, ReleaseCreate(name="SYNTHETIC energy pilot",
                        artifact_sha256=report["input_sha256"], previous_artifact_sha256="0" * 64), "synthetic_pilot_maker")["id"]
                    gate = snapshot(db, rid)
                    old_id = settings.production_release_id
                    try:
                        settings.production_release_id = rid
                        try:
                            require_live_release(db)
                        except PermissionError:
                            report["execution_control"] = "PASS: incomplete synthetic release denied execution"
                        else:
                            raise AssertionError("Synthetic release authorized execution")
                    finally:
                        settings.production_release_id = old_id
                    report["release_gate"] = gate
        finally:
            engine.dispose()
    output = ROOT / "pilot/ENERGY_PILOT_RESULTS.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # Keep the frontend image self-contained; its build context excludes pilot/.
    frontend_data = {key: report[key] for key in ("kind", "as_of", "input_sha256", "scenarios")}
    (ROOT / "frontend/lib/energy-pilot.json").write_text(json.dumps(frontend_data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "cases": len(report["scenarios"]),
                      "execution_control": report["execution_control"]}))


if __name__ == "__main__":
    run()
