"""Package a source release with a verified per-file digest manifest."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".venv", "node_modules", ".next", ".pytest_cache", "__pycache__", ".audit-cache", ".git", "secrets", ".vercel"}


def include(path):
    relative = path.relative_to(ROOT)
    return (not any(part in EXCLUDED_DIRS for part in relative.parts)
            and (not path.name.startswith(".env") or path.name == ".env.example")
            and path.suffix not in {".db", ".pyc", ".tsbuildinfo", ".zip", ".pem", ".key"}
            and not path.name.endswith((".db-wal", ".db-shm", ".db-journal"))
            and not ("output" in path.name and path.suffix == ".txt")
            and path.name != "RELEASE_MANIFEST.json")


def package(output):
    files = []
    for directory, directories, names in os.walk(ROOT):
        directories[:] = [name for name in directories if name not in EXCLUDED_DIRS]
        files.extend(path for name in names if include(path := Path(directory) / name))
    files.sort()
    manifest = {"release": "Production Phases 2-4", "production_status": "BLOCKED_EXTERNAL_EVIDENCE",
                "baseline_sha256": "657e8d7d263bf6897825c56800e44e94242a5a0bf73976f25826b6cc853a9eb9",
                "files": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr("RELEASE_MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True))
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name, digest in manifest["files"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".sha256").write_text(digest + "  " + output.name + "\n", encoding="utf-8")
    print(json.dumps({"archive": str(output.resolve()), "files": len(files), "sha256": digest}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    package(parser.parse_args().output)
