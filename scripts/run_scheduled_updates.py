"""Run one bounded readiness pass; unavailable external adapters remain BLOCKED."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.db import SessionLocal
from app.services.scheduled_updates import record_due_attempts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", required=True, help="Provisioned active GROUP_TREASURER operator username")
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps({"worker_status": "BLOCKED", "attempts": record_due_attempts(db, args.actor)}))


if __name__ == "__main__":
    main()
