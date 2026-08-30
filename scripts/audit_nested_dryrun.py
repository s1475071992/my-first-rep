#!/usr/bin/env python3
"""Audit a GCClassic nested dry-run without downloading scientific inputs.

Required verdict families are MET, RESTART, BC, and DRYRUN. Remote object
existence is probed against the official public gcgrid S3 HTTP endpoint.
Every source path and derived official URL is retained in the JSON/TSV output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SHA256 = "SHA256"
RESOLVABLE = "RESOLVABLE"
FAMILIES = ("MET", "RESTART", "BC")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def classify(line: str) -> str:
    u = line.upper()
    if "GEOSCHEM.RESTART" in u or "GEOSCHEM_RESTARTS" in u:
        return "RESTART"
    if "BOUNDARYCONDITIONS" in u or "BOUNDARY_CONDITIONS" in u or "BOUNDARY CONDITION" in u:
        return "BC"
    if "MERRA2" in u and ("GEOS_0.5X0.625" in u or "MERRA2." in u):
        return "MET"
    return "OTHER"


def remote_key(line: str) -> str | None:
    source = line.split("-->", 1)[1].strip() if "-->" in line else line.strip()
    normalized = source.replace("\\", "/")
    marker = "/ExtData/"
    if marker in normalized:
        return normalized.split(marker, 1)[1]
    if normalized.startswith("ExtData/"):
        return normalized[len("ExtData/"):]
    return None


def probe(url: str, timeout: float) -> dict:
    headers = {"User-Agent": "gc14-nested-input-probe/1"}
    attempts = []
    for method, extra in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        req = urllib.request.Request(url, method=method, headers={**headers, **extra})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                code = int(getattr(r, "status", r.getcode()))
                attempts.append({"method": method, "status": code})
                if 200 <= code < 400:
                    return {"resolvable": True, "http_status": code, "attempts": attempts}
        except urllib.error.HTTPError as e:
            attempts.append({"method": method, "status": int(e.code), "error": str(e)})
        except Exception as e:  # network evidence is preserved verbatim
            attempts.append({"method": method, "status": None, "error": repr(e)})
    last = attempts[-1] if attempts else {"status": None}
    return {"resolvable": False, "http_status": last.get("status"), "attempts": attempts}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rundir", required=True)
    ap.add_argument("--case", required=True)
    ap.add_argument("--unique-log", required=True)
    ap.add_argument("--portal-base", default="https://gcgrid.s3.amazonaws.com")
    ap.add_argument("--output", required=True)
    ap.add_argument("--urls-output", required=True)
    ap.add_argument("--timeout", type=float, default=20.0)
    args = ap.parse_args()

    rundir = Path(args.rundir).resolve()
    case_path = Path(args.case).resolve()
    unique_path = Path(args.unique_log).resolve()
    dryrun_path = rundir / "log.dryrun"

    dryrun_pass = dryrun_path.is_file() and dryrun_path.stat().st_size > 0 and unique_path.is_file()
    lines = []
    if unique_path.is_file():
        for raw in unique_path.read_text(errors="replace").splitlines():
            line = raw.strip()
            if line and not line.startswith("!"):
                lines.append(line)

    records = []
    base = args.portal_base.rstrip("/")
    for line in lines:
        family = classify(line)
        key = remote_key(line)
        rec = {"family": family, "source_path": line, "remote_key": key, "remote_url": None}
        if key is not None:
            rec["remote_url"] = base + "/" + urllib.parse.quote(key, safe="/")
        if family in FAMILIES and rec["remote_url"]:
            rec.update(probe(rec["remote_url"], args.timeout))
        else:
            rec["resolvable"] = None
            rec["http_status"] = None
            rec["attempts"] = []
        records.append(rec)

    family_results = {}
    for family in FAMILIES:
        subset = [r for r in records if r["family"] == family]
        if not subset:
            status = "FAIL_NO_REFERENCES"
        elif all(r.get("resolvable") is True for r in subset):
            status = RESOLVABLE
        else:
            status = "UNRESOLVABLE"
        family_results[family] = {
            "status": status,
            "reference_count": len(subset),
            "resolvable_count": sum(r.get("resolvable") is True for r in subset),
            "unresolvable_count": sum(r.get("resolvable") is False for r in subset),
        }

    dryrun_status = "PASS" if dryrun_pass else "FAIL"
    overall = dryrun_status == "PASS" and all(family_results[f]["status"] == RESOLVABLE for f in FAMILIES)

    hashes = {}
    for name in [
        "log.dryrun", "log.dryrun.unique", "download_data.yml", "geoschem_config.yml",
        "HEMCO_Config.rc", "HISTORY.rc", "species_database.yml", "REFERENCE_CASE.json",
    ]:
        p = rundir / name
        if p.is_file():
            hashes[name] = sha256(p)
    if case_path.is_file():
        hashes[str(case_path)] = sha256(case_path)

    result = {
        "schema_id": "GC14_7_1_NESTED_INPUT_MANIFEST_PROBE_V1",
        "status": "PASS" if overall else "FAIL",
        "case": json.loads(case_path.read_text()),
        "DRYRUN": {"status": dryrun_status},
        "MET": family_results["MET"],
        "RESTART": family_results["RESTART"],
        "BC": family_results["BC"],
        "portal_base": base,
        "path_record_count": len(records),
        "paths_and_urls": records,
        "SHA256": hashes,
        "scientific_data_downloaded": False,
        "scientific_thresholds_modified": False,
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    with Path(args.urls_output).open("w") as f:
        f.write("family\tresolvable\thttp_status\tsource_path\tremote_url\n")
        for r in records:
            f.write(
                f"{r['family']}\t{r['resolvable']}\t{r['http_status']}\t"
                f"{r['source_path']}\t{r['remote_url'] or ''}\n"
            )

    print(json.dumps({
        "status": result["status"],
        "DRYRUN": result["DRYRUN"]["status"],
        "MET": result["MET"]["status"],
        "RESTART": result["RESTART"]["status"],
        "BC": result["BC"]["status"],
    }, indent=2, sort_keys=True))
    return 0 if overall else 40


if __name__ == "__main__":
    raise SystemExit(main())
