"""Compare the browser planning contract with the unchanged Python forecast engine."""
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.db import Base
from app.models import BankAccount, CashFlow, FXRate, LegalEntity
from app.services.forecast import calculate_liquidity_forecast


def run():
    source = json.loads((ROOT / "pilot/ENERGY_DEMO_SCENARIO.json").read_text(encoding="utf-8"))
    category = {"DEMO_CRUDE_PURCHASE": "CRUDE_PURCHASE", "DEMO_DIESEL_SALE": "PRODUCT_SALE",
                "DEMO_FREIGHT": "FREIGHT"}
    flows = [{"id": f["id"], "entity": "GROUP", "date": f["date"], "direction": f["direction"],
              "currency": f["currency"], "amount": f["amount"], "category": category.get(f["id"], "OPERATING"),
              "probability": "1"} for f in source["cashflows"]]
    cases = [("BASE", {}), ("DELAY", {"delay": 10}), ("OIL", {"oil": 20}),
             ("FX", {"fx": 10}), ("COMBINED", {"delay": 10, "costs": 10, "oil": 20, "fx": 10}),
             ("RECEIPTS", {"receipts": -25}), ("OUTSIDE_HORIZON", {"delay": 90})]
    records = []
    for label, changes in cases:
        assumptions = {"start": source["as_of"], "weeks": 13, "opening": "34800000", "buffer": "15000000",
                       "rates": {"GBP": "1.25", "SGD": "0.80"}, "delay": 0, "receipts": 0, "costs": 0, "oil": 0, "fx": 0, **changes}
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        try:
            with Session(engine) as db:
                entity = LegalEntity(name="PRIVATE_PLANNING_TEST", country_code="GB", functional_currency="USD", minimum_cash=Decimal(assumptions["buffer"]))
                db.add(entity); db.flush()
                db.add(BankAccount(entity_id=entity.id, bank_name="TEST", country_code="GB", currency="USD", book_balance=Decimal(assumptions["opening"])))
                for currency, rate in assumptions["rates"].items():
                    db.add(FXRate(base_currency=currency, quote_currency="USD", rate=Decimal(rate) * (1 + Decimal(assumptions["fx"]) / 100), source="SYNTHETIC", as_of=datetime.fromisoformat(assumptions["start"])))
                for flow in flows:
                    amount = Decimal(flow["amount"])
                    if flow["category"] in {"CRUDE_PURCHASE", "PRODUCT_SALE"}: amount *= 1 + Decimal(assumptions["oil"]) / 100
                    amount *= 1 + Decimal(assumptions["receipts"] if flow["direction"] == "INFLOW" else assumptions["costs"]) / 100
                    due = date.fromisoformat(flow["date"]) + timedelta(days=assumptions["delay"] if flow["direction"] == "INFLOW" else 0)
                    db.add(CashFlow(entity_id=entity.id, flow_type="RECEIVABLE" if flow["direction"] == "INFLOW" else "PAYABLE", counterparty="TEST", currency=flow["currency"], amount=amount, due_date=due, probability=Decimal(flow["probability"]), source_reference=flow["id"]))
                db.commit()
                result = calculate_liquidity_forecast(db, "BASE", assumptions["weeks"], date.fromisoformat(assumptions["start"]))
                money = lambda value: str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
                expected = {"ending": money(result.ending_cash), "headroom": money(result.ending_liquidity_headroom),
                            "maximumShortfall": money(result.maximum_shortfall), "firstBreach": result.first_buffer_breach_week,
                            "points": [{"week": p.week, "closing": money(p.closing_cash), "inflows": money(p.expected_inflows), "outflows": money(p.expected_outflows), "shortfall": money(p.shortfall)} for p in result.points]}
                records.append({"case": label, "flows": flows, "assumptions": assumptions, "expected": expected})
        finally:
            engine.dispose()
    target = ROOT / "frontend/tests/fixtures/planning-engine.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"source": "unchanged Python treasury forecast engine; synthetic isolated database", "cases": records}, indent=2), encoding="utf-8")
    print(json.dumps({"cases": len(records), "persistent_treasury_writes": False, "fixture": str(target)}))


if __name__ == "__main__":
    run()
