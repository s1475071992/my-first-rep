#!/usr/bin/env python3
"""Validate GCClassic external-holdout NetCDF outputs before packaging."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from netCDF4 import Dataset


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_passive(ds: Dataset) -> str:
    exact = ["SpeciesRst_PassiveTracer", "SpeciesConcVV_PassiveTracer", "PassiveTracer"]
    for name in exact:
        if name in ds.variables:
            return name
    candidates = [name for name in ds.variables if "passivetracer" in name.lower()]
    if not candidates:
        raise ValueError("PassiveTracer variable not found")
    return sorted(candidates)[0]


def inspect(path: Path) -> dict:
    if path.stat().st_size <= 0:
        raise ValueError(f"empty NetCDF file: {path}")
    with Dataset(path, "r") as ds:
        tracer_name = find_passive(ds)
        tracer = np.asarray(ds.variables[tracer_name][:], dtype=np.float64)
        if tracer.size == 0 or not np.isfinite(tracer).all():
            raise ValueError(f"non-finite/empty PassiveTracer in {path}")
        time_values = None
        if "time" in ds.variables:
            time_values = np.asarray(ds.variables["time"][:], dtype=np.float64)
            if time_values.size and (not np.isfinite(time_values).all() or np.any(np.diff(time_values) < 0)):
                raise ValueError(f"invalid/non-monotonic time coordinate in {path}")
        return {
            "path": str(path),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
            "passive_variable": tracer_name,
            "passive_shape": list(tracer.shape),
            "passive_min": float(tracer.min()),
            "passive_max": float(tracer.max()),
            "passive_mean": float(tracer.mean()),
            "time_count": int(0 if time_values is None else time_values.size),
            "has_met_delpdry": "Met_DELPDRY" in ds.variables,
        }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("paths", nargs="+")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    records = [inspect(Path(x).resolve()) for x in args.paths]
    payload = {"status": "PASS", "files": records}
    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
