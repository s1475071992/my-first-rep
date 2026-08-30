#!/usr/bin/env python3
"""Package validated GEOS-Chem external holdout evidence with immutable hashes."""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--case-id", required=True)
    p.add_argument("--source-dir", required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    source = Path(args.source_dir).resolve()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in source.rglob("*") if p.is_file())
    if not files:
        raise SystemExit("no evidence files to package")

    manifest = {
        "case_id": args.case_id,
        "evidence_role": "GEOSCHEM_EXTERNAL_HOLDOUT_AUDIT",
        "geoschem_as_training_truth": False,
        "l5_forward_numerical_equivalence": "NOT_CLAIMED",
        "files": [
            {
                "path": str(p.relative_to(source)),
                "size_bytes": p.stat().st_size,
                "sha256": sha256(p),
            }
            for p in files
        ],
    }
    manifest_path = out / f"{args.case_id}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    archive = out / f"{args.case_id}.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        for p in files:
            tf.add(p, arcname=p.relative_to(source))
        tf.add(manifest_path, arcname=manifest_path.name)

    checksum_path = out / f"{args.case_id}.sha256"
    checksum_path.write_text(f"{sha256(archive)}  {archive.name}\n")
    print(json.dumps({"archive": str(archive), "sha256": sha256(archive)}, indent=2))


if __name__ == "__main__":
    main()
