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


def patch_hemco_restart_policy(path: Path) -> None:
    """Allow absent restart species to use GCClassic's background defaults.

    GEOS-Chem Classic 14.7.1 documents CYS (or EY) on the SPC_ restart
    container as the supported way to proceed when the restart timestamp does
    not match the simulation start or when some transported species are absent.
    Keep every other HEMCO field unchanged.
    """
    lines = path.read_text().splitlines(keepends=True)
    matches = 0
    patched: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            tokens = stripped.split()
            if len(tokens) >= 7 and tokens[0] == "*" and tokens[1] == "SPC_" and tokens[3].startswith("SpeciesRst_"):
                matches += 1
                if tokens[5] not in {"EFYO", "CYS"}:
                    raise SystemExit(f"unexpected HEMCO SPC_ restart policy: {tokens[5]}")
                if tokens[5] == "EFYO":
                    start = line.find("EFYO")
                    if start < 0:
                        raise SystemExit("could not locate EFYO token in HEMCO SPC_ restart line")
                    line = line[:start] + "CYS " + line[start + 5 :]
        patched.append(line)
    if matches != 1:
        raise SystemExit(f"expected exactly one HEMCO SPC_ restart entry, found {matches}")
    path.write_text("".join(patched))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rundir", required=True)
    p.add_argument("--case-id", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    args = p.parse_args()

    rundir = Path(args.rundir).resolve()
    cfg_path = rundir / "geoschem_config.yml"
    hemco_path = rundir / "HEMCO_Config.rc"
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
    patch_hemco_restart_policy(hemco_path)

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
        "restart_missing_species_policy": "HEMCO_SPC_CYS_BACKGROUND_DEFAULT",
        "geoschem_config_sha256": sha256(cfg_path),
        "hemco_config_sha256": sha256(hemco_path),
    }
    (rundir / "REFERENCE_CASE.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
