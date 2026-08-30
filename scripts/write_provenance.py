#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(args: list[str], cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gcclassic", required=True)
    p.add_argument("--rundir")
    p.add_argument("--output", required=True)
    args = p.parse_args()

    gc = Path(args.gcclassic).resolve()
    out = Path(args.output)
    record = {
        "evidence_class": "GC_DISCREPANCY_AUDIT_EXTERNAL_REFERENCE",
        "geoschem_as_training_truth": False,
        "l5_forward_numerical_equivalence_claimed": False,
        "runner": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "github_sha": os.environ.get("GITHUB_SHA"),
        },
        "source": {
            "gcclassic_ref": "14.7.1",
            "gcclassic_sha": git(["rev-parse", "HEAD"], gc),
            "geoschem_sha": git(["rev-parse", "HEAD"], gc / "src/GEOS-Chem"),
            "hemco_sha": git(["rev-parse", "HEAD"], gc / "src/HEMCO"),
            "submodule_status": git(["submodule", "status", "--recursive"], gc).splitlines(),
        },
        "rundir": None,
    }

    if args.rundir:
        rd = Path(args.rundir).resolve()
        key_files = [
            "geoschem_config.yml",
            "HEMCO_Config.rc",
            "HISTORY.rc",
            "download_data.yml",
        ]
        files = {}
        for name in key_files:
            path = rd / name
            if path.is_file():
                files[name] = {"size": path.stat().st_size, "sha256": sha256(path)}
        record["rundir"] = {"path": str(rd), "files": files}

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
