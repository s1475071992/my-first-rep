#!/usr/bin/env python3
"""Freeze a transport-only GCClassic external-reference case in an existing run directory."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import yaml


def parse_stamp(text: str) -> dt.datetime:
    return dt.datetime.strptime(text, "%Y%m%dT%H%M%S").replace(tzinfo=dt.timezone.utc)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rundir", required=True)
    p.add_argument("--case-id", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    args = p.parse_args()

    rundir = Path(args.rundir).resolve()
    cfg_path = rundir / "geoschem_config.yml"
    cfg = yaml.safe_load(cfg_path.read_text())
    start = parse_stamp(args.start)
    end = parse_stamp(args.end)
    if end <= start:
        raise SystemExit("end must be later than start")

    cfg["simulation"]["start_date"] = [int(start.strftime("%Y%m%d")), int(start.strftime("%H%M%S"))]
    cfg["simulation"]["end_date"] = [int(end.strftime("%Y%m%d")), int(end.strftime("%H%M%S"))]
    cfg["simulation"]["read_restart_as_real8"] = True

    ops = cfg["operations"]
    # External audit isolates GCClassic's native advection map.  Disable other
    # processes so a Torch-vs-GC difference is not silently contaminated by
    # chemistry, PBL mixing, convection, or deposition.
    for key in ["chemistry", "convection", "dry_deposition", "pbl_mixing", "wet_deposition"]:
        if key in ops and isinstance(ops[key], dict):
            ops[key]["activate"] = False
    ops["transport"]["gcclassic_tpcore"]["activate"] = True
    transported = ops["transport"].get("transported_species", [])
    if "PassiveTracer" not in transported:
        raise SystemExit("PassiveTracer is not transported in this TransportTracers run directory")

    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))

    record = {
        "case_id": args.case_id,
        "start_utc": start.isoformat().replace("+00:00", "Z"),
        "end_utc": end.isoformat().replace("+00:00", "Z"),
        "duration_seconds": int((end - start).total_seconds()),
        "simulation": cfg["simulation"]["name"],
        "met_field": cfg["simulation"]["met_field"],
        "resolution": cfg["grid"]["resolution"],
        "levels": cfg["grid"]["number_of_levels"],
        "primary_tracer": "PassiveTracer",
        "process_scope": "TPCORE_ADVECTION_ONLY",
        "geoschem_as_training_truth": False,
        "geoschem_config_sha256": sha256(cfg_path),
    }
    (rundir / "REFERENCE_CASE.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
