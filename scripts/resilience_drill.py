"""Local SQLite backup/restore drill. Never certifies managed production DR."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from time import perf_counter


def drill(database: Path):
    if not database.is_file():
        raise ValueError("Source database does not exist")
    started = perf_counter()
    with tempfile.TemporaryDirectory() as directory:
        backup = Path(directory) / "backup.db"
        restored = Path(directory) / "restored.db"
        with closing(sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True)) as source:
            before = source.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            with closing(sqlite3.connect(backup)) as target:
                source.backup(target)
        with closing(sqlite3.connect(backup)) as source, closing(sqlite3.connect(restored)) as target:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
            after = target.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        digest = hashlib.sha256(backup.read_bytes()).hexdigest()
        identical = backup.read_bytes() == restored.read_bytes()
    return {"kind": "SYNTHETIC", "certification": "UNVALIDATED", "scope": "LOCAL_SQLITE_ONLY",
            "status": "PASS" if integrity == "ok" and before == after and identical else "FAIL",
            "backup_sha256": digest, "tables": len(after), "integrity": integrity,
            "restored_bytes_equal": identical, "local_elapsed_seconds": round(perf_counter() - started, 6),
            "production_rto_rpo": "NOT_MEASURED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = drill(args.database)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
