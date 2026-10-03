"""Exercise dashboard read endpoints against a separate synthetic database."""
import json
import os
from pathlib import Path
import sys
import time
from datetime import UTC, datetime

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = "sqlite:///./application-smoke.db"
os.environ["ENVIRONMENT"] = "development"
os.environ["AUTH_MODE"] = "demo_header"
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")
from fastapi.testclient import TestClient
from app.main import app

catalog = json.loads((ROOT / "frontend/lib/endpoints.json").read_text())
results = []
snapshots = {}
with TestClient(app, raise_server_exceptions=False) as client:
    for name, item in catalog.items():
        started = time.perf_counter()
        response = client.get(item["path"])
        if response.status_code == 200:
            snapshots[name] = response.json()
        results.append({"name": name, "path": item["path"], "status": response.status_code,
                        "seconds": round(time.perf_counter() - started, 3)})
    for path, expected in (("/health", 200), ("/health/ready", 200),
                           ("/health/production", 503), ("/api/v1/production/releases/1", 401)):
        response = client.get(path)
        if path == "/health/production":
            snapshots["productionGate"] = response.json()
        results.append({"path": path, "status": response.status_code, "expected": expected})
failures = [r for r in results if r["status"] != r.get("expected", 200)]
report = {"kind": "SYNTHETIC", "checks": len(results), "failures": failures, "results": results}
(ROOT / "APPLICATION_SMOKE_EVIDENCE.json").write_text(json.dumps(report, indent=2) + "\n")
if not failures:
    (ROOT / "frontend/lib/demo-snapshot.json").write_text(json.dumps({
        "kind": "SYNTHETIC_RECORDED_DEMO", "captured_at": datetime.now(UTC).isoformat(),
        "results": snapshots,
    }, indent=2) + "\n")
print(json.dumps({"checks": len(results), "failures": failures}))
sys.exit(bool(failures))
