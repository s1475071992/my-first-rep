#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

DATA_SUFFIXES = (".nc", ".nc4", ".rc", ".yml", ".yaml")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def summarize(log_path: Path) -> dict:
    if not log_path.is_file() or log_path.stat().st_size == 0:
        raise ValueError(f"dry-run log missing or empty: {log_path}")
    text = log_path.read_text(errors="replace")
    if "GEOS-Chem" not in text and "GEOS-CHEM" not in text:
        raise ValueError("dry-run log does not look like GEOS-Chem output")

    candidates: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if any(suffix in line for suffix in DATA_SUFFIXES):
            candidates.append(line)

    # Dry-run format may decorate paths with FOUND/MISSING text.  Keep the
    # original lines as evidence and additionally extract path-like tokens.
    path_tokens: set[str] = set()
    pattern = re.compile(r"(?:/|\$ROOT/|\./)[^\s,;]+?(?:\.nc4?|\.rc|\.ya?ml)(?=\s|$|[,;])")
    for line in candidates:
        path_tokens.update(pattern.findall(line))

    return {
        "status": "PASS" if candidates else "FAIL_NO_DATA_REFERENCES",
        "log_file": str(log_path),
        "log_sha256": sha256(log_path),
        "data_reference_line_count": len(candidates),
        "unique_path_token_count": len(path_tokens),
        "unique_path_tokens": sorted(path_tokens),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("log")
    p.add_argument("--output", default="dryrun_summary.json")
    args = p.parse_args()
    result = summarize(Path(args.log))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if result["status"] != "PASS":
        raise SystemExit(30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
