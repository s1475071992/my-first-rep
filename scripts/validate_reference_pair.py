#!/usr/bin/env python3
"""Validate one GCClassic pre/post reference pair and frozen holdout regions.

This is a producer-integrity gate, not a Torch-vs-GC scoring gate. It checks
that the reference pair is structurally valid, finite, uses dry-air mass data,
and covers every frozen holdout region. It records diagnostic changes without
inventing or relaxing scientific comparison thresholds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

GRAVITY_M_S2 = 9.80665


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


def _squeeze_time(arr: np.ndarray, name: str) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float64)
    if arr.ndim == 4:
        if arr.shape[0] != 1:
            raise ValueError(f"{name} expected one time record, got shape={arr.shape}")
        arr = arr[0]
    if arr.ndim != 3:
        raise ValueError(f"{name} expected (lev,lat,lon), got shape={arr.shape}")
    return arr


def load_state(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValueError(f"missing or empty NetCDF file: {path}")
    with Dataset(path, "r") as ds:
        tracer_name = find_passive(ds)
        required = ["lat", "AREA", "Met_DELPDRY"]
        missing = [name for name in required if name not in ds.variables]
        if missing:
            raise ValueError(f"missing required dry-air/grid fields in {path}: {missing}")
        q = _squeeze_time(ds.variables[tracer_name][:], tracer_name)
        delp = _squeeze_time(ds.variables["Met_DELPDRY"][:], "Met_DELPDRY")
        lat = np.asarray(ds.variables["lat"][:], dtype=np.float64)
        area = np.asarray(ds.variables["AREA"][:], dtype=np.float64).squeeze()
        if area.ndim != 2:
            raise ValueError(f"AREA expected (lat,lon), got shape={area.shape}")
        if q.shape != delp.shape:
            raise ValueError(f"PassiveTracer/DELPDRY shape mismatch: {q.shape} vs {delp.shape}")
        if q.shape[1:] != area.shape:
            raise ValueError(f"3-D/AREA grid mismatch: {q.shape[1:]} vs {area.shape}")
        if q.shape[1] != lat.size:
            raise ValueError(f"latitude size mismatch: q={q.shape[1]} lat={lat.size}")
        for name, arr in [(tracer_name, q), ("Met_DELPDRY", delp), ("lat", lat), ("AREA", area)]:
            if arr.size == 0 or not np.isfinite(arr).all():
                raise ValueError(f"non-finite or empty {name} in {path}")
        if np.any(delp <= 0.0):
            raise ValueError(f"Met_DELPDRY must be strictly positive in {path}")
        if np.any(area <= 0.0):
            raise ValueError(f"AREA must be strictly positive in {path}")
        dry_mass = delp * 100.0 * area[None, :, :] / GRAVITY_M_S2
        return {
            "path": str(path),
            "sha256": sha256(path),
            "tracer_name": tracer_name,
            "q": q,
            "delp": delp,
            "dry_mass": dry_mass,
            "lat": lat,
            "area": area,
            "rn222_present": "SpeciesRst_Rn222" in ds.variables,
        }


def summarize_region(state: dict, lat_min: float, lat_max: float) -> dict:
    mask = (state["lat"] >= lat_min) & (state["lat"] <= lat_max)
    if not np.any(mask):
        raise ValueError(f"empty latitude holdout [{lat_min}, {lat_max}]")
    q = state["q"][:, mask, :]
    dry_mass = state["dry_mass"][:, mask, :]
    dry_total = float(dry_mass.sum())
    if not np.isfinite(dry_total) or dry_total <= 0.0:
        raise ValueError("invalid regional dry-air mass")
    inventory = float((q * dry_mass).sum())
    weighted_mean = float(inventory / dry_total)
    return {
        "dry_air_mass_kg": dry_total,
        "passive_min": float(q.min()),
        "passive_max": float(q.max()),
        "passive_mean": float(q.mean()),
        "passive_dry_air_weighted_mean": weighted_mean,
        "passive_inventory_proxy_kg": inventory,
        "latitude_cell_count": int(mask.sum()),
    }


def relative_change(initial: float, final: float) -> float:
    if initial == 0.0:
        return float("nan")
    return float((final - initial) / initial)


def validate_pair(
    initial_path: Path,
    final_path: Path,
    matrix: dict,
    case_id: str,
    executable_sha256: str,
) -> dict:
    cases = {case["case_id"]: case for case in matrix["cases"]}
    if case_id not in cases:
        raise ValueError(f"case_id not found in frozen matrix: {case_id}")
    case = cases[case_id]
    initial = load_state(initial_path)
    final = load_state(final_path)
    if initial["q"].shape != final["q"].shape:
        raise ValueError("pre/post PassiveTracer shapes differ")
    if not np.array_equal(initial["lat"], final["lat"]):
        raise ValueError("pre/post latitude grids differ")
    if not np.array_equal(initial["area"], final["area"]):
        raise ValueError("pre/post grid-cell areas differ")
    if initial["sha256"] == final["sha256"]:
        raise ValueError("pre/post restart files are byte-identical")

    regions = {}
    for region in matrix["holdout_regions"]:
        rid = region["region_id"]
        pre = summarize_region(initial, float(region["lat_min"]), float(region["lat_max"]))
        post = summarize_region(final, float(region["lat_min"]), float(region["lat_max"]))
        regions[rid] = {
            "status": "PASS",
            "lat_min": float(region["lat_min"]),
            "lat_max": float(region["lat_max"]),
            "initial": pre,
            "final": post,
            "dry_air_mass_relative_change": relative_change(pre["dry_air_mass_kg"], post["dry_air_mass_kg"]),
            "passive_inventory_relative_change": relative_change(
                pre["passive_inventory_proxy_kg"], post["passive_inventory_proxy_kg"]
            ),
        }

    return {
        "status": "PASS",
        "acceptance_class": "REFERENCE_PAIR_INTEGRITY",
        "scientific_thresholds_applied": False,
        "scientific_threshold_note": "No Torch-vs-GC scoring threshold is introduced or changed by this producer gate.",
        "matrix_id": matrix["matrix_id"],
        "case_id": case_id,
        "season": case["season"],
        "duration_seconds": int(case["duration_seconds"]),
        "executable_sha256": executable_sha256,
        "initial": {
            "path": initial["path"],
            "sha256": initial["sha256"],
            "rn222_present": initial["rn222_present"],
        },
        "final": {
            "path": final["path"],
            "sha256": final["sha256"],
            "rn222_present": final["rn222_present"],
        },
        "regions": regions,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--initial", required=True)
    p.add_argument("--final", required=True)
    p.add_argument("--matrix", required=True)
    p.add_argument("--case-id", required=True)
    p.add_argument("--executable-sha256", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    matrix = json.loads(Path(args.matrix).read_text())
    payload = validate_pair(
        Path(args.initial).resolve(),
        Path(args.final).resolve(),
        matrix,
        args.case_id,
        args.executable_sha256,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
