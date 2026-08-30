#!/usr/bin/env python3
"""Run the frozen four-season GCClassic reference matrix inside one candidate image."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None, log: Path | None = None) -> None:
    print("+", " ".join(str(x) for x in cmd), flush=True)
    if log is None:
        subprocess.run(cmd, cwd=cwd, env=env, check=True)
        return
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as fh:
        proc = subprocess.run(cmd, cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        print(log.read_text(errors="replace"), flush=True)
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def iso_to_dt(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


def cli_stamp(value: dt.datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def restart_name(value: dt.datetime) -> str:
    return f"GEOSChem.Restart.{value.strftime('%Y%m%d_%H%M')}z.nc4"


def assert_runtime_log(path: Path) -> None:
    text = path.read_text(errors="replace")
    fatal = ["HEMCO ERROR", "GEOS-Chem ERROR", "REFERENCE_RUNTIME_FAILURE", "Segmentation fault", "SIGSEGV"]
    found = [marker for marker in fatal if marker.lower() in text.lower()]
    if found:
        raise RuntimeError(f"runtime log contains fatal markers {found}: {path}")
    if "END OF GEOS--CHEM" not in text:
        raise RuntimeError(f"runtime did not reach END OF GEOS--CHEM: {path}")


def assert_runtime_config(rundir: Path) -> None:
    history = (rundir / "HISTORY.rc").read_text()
    head = history.split("::", 1)[0]
    if "'Restart'" not in head or "'SpeciesConc'" not in head:
        raise RuntimeError("Restart/SpeciesConc are not enabled in HISTORY collection declaration")
    for forbidden in ["'CloudConvFlux'", "'StateMet'", "'RadioNuclide'"]:
        if forbidden in head:
            raise RuntimeError(f"unexpected enabled HISTORY collection: {forbidden}")
    hemco = (rundir / "HEMCO_Config.rc").read_text().splitlines()
    spc = [line for line in hemco if line.strip().startswith("* SPC_") and "SpeciesRst_" in line]
    if len(spc) != 1 or " CYS " not in spc[0]:
        raise RuntimeError(f"HEMCO restart fallback is not exactly one SPC_ CYS entry: {spc}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--template", required=True)
    p.add_argument("--matrix", required=True)
    p.add_argument("--work-root", required=True)
    p.add_argument("--expected-executable-sha256", required=True)
    args = p.parse_args()

    control_root = Path(__file__).resolve().parents[1]
    template = Path(args.template).resolve()
    matrix_path = Path(args.matrix).resolve()
    matrix = json.loads(matrix_path.read_text())
    work_root = Path(args.work_root).resolve()
    cases_root = work_root / "cases"
    extdata = work_root / "extdata"
    cases_root.mkdir(parents=True, exist_ok=True)
    extdata.mkdir(parents=True, exist_ok=True)

    home_cfg = Path.home() / ".geoschem" / "config"
    home_cfg.parent.mkdir(parents=True, exist_ok=True)
    home_cfg.write_text(f"export GC_DATA_ROOT={extdata}\nexport GC_USER_REGISTERED=true\n")

    env = os.environ.copy()
    env["GC_DATA_ROOT"] = str(extdata)
    env["GC_USER_REGISTERED"] = "true"
    env["GITHUB_WORKSPACE"] = str(control_root)

    template_exe = template / "gcclassic"
    if not template_exe.is_file():
        raise SystemExit(f"missing frozen executable: {template_exe}")
    actual_exe_sha = sha256(template_exe)
    if actual_exe_sha != args.expected_executable_sha256:
        raise SystemExit(
            f"frozen executable mismatch before matrix: {actual_exe_sha} != {args.expected_executable_sha256}"
        )

    for case in matrix["cases"]:
        case_id = case["case_id"]
        season = case["season"]
        print(f"\n=== {case_id} ({season}) ===", flush=True)
        start = iso_to_dt(case["start_date"])
        end = start + dt.timedelta(seconds=int(case["duration_seconds"]))
        case_root = cases_root / case_id
        rundir = case_root / "rundir"
        evidence = case_root / "evidence"
        if case_root.exists():
            shutil.rmtree(case_root)
        shutil.copytree(template, rundir, symlinks=True)
        evidence.mkdir(parents=True)
        for dirname in ["OutputDir", "Restarts"]:
            target = rundir / dirname
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True)

        run(
            [
                sys.executable,
                str(control_root / "scripts/configure_reference_case.py"),
                "--rundir",
                str(rundir),
                "--case-id",
                case_id,
                "--start",
                cli_stamp(start),
                "--end",
                cli_stamp(end),
            ],
            env=env,
        )
        run(
            [
                sys.executable,
                str(control_root / "scripts/patch_history_for_window.py"),
                str(rundir / "HISTORY.rc"),
                "--seconds",
                str(int(case["duration_seconds"])),
            ],
            env=env,
        )
        assert_runtime_config(rundir)

        run(["./gcclassic", "--dryrun"], cwd=rundir, env=env, log=rundir / "log.dryrun")
        run(
            [
                sys.executable,
                str(control_root / "scripts/validate_dryrun.py"),
                str(rundir / "log.dryrun"),
                "--output",
                str(rundir / "dryrun_summary.json"),
            ],
            env=env,
        )
        # Upstream GCClassic 14.7.1 still dereferences the selected portal while
        # generating the unique dry-run manifest, even with -skip-download.
        # Supply the same official portal used by the real download so the
        # manifest-only pass cannot fail with portal=None.
        run(
            ["./download_data.py", "log.dryrun", "geoschem+aws", "-skip-download"],
            cwd=rundir,
            env=env,
            log=rundir / "download_data_skip.log",
        )
        run(
            ["bash", str(control_root / "scripts/download_official_inputs.sh"), str(rundir), "geoschem+aws"],
            cwd=control_root,
            env=env,
        )

        initial_restart = rundir / "Restarts" / restart_name(start)
        if not initial_restart.is_file():
            raise RuntimeError(f"missing initial restart after official download: {initial_restart}")
        shutil.copy2(initial_restart, evidence / "initial_restart.nc4")

        run(["./gcclassic"], cwd=rundir, env=env, log=rundir / "GC.log")
        assert_runtime_log(rundir / "GC.log")

        final_restart = rundir / "Restarts" / restart_name(end)
        if not final_restart.is_file():
            raise RuntimeError(f"missing final restart: {final_restart}")
        shutil.copy2(final_restart, evidence / "final_restart.nc4")

        run(
            [
                sys.executable,
                str(control_root / "scripts/validate_reference_pair.py"),
                "--initial",
                str(evidence / "initial_restart.nc4"),
                "--final",
                str(evidence / "final_restart.nc4"),
                "--matrix",
                str(matrix_path),
                "--case-id",
                case_id,
                "--executable-sha256",
                actual_exe_sha,
                "--output",
                str(evidence / "pair_acceptance.json"),
            ],
            env=env,
        )

        runtime_status = {
            "status": "PASS",
            "case_id": case_id,
            "season": season,
            "start_utc": start.isoformat().replace("+00:00", "Z"),
            "end_utc": end.isoformat().replace("+00:00", "Z"),
            "duration_seconds": int(case["duration_seconds"]),
            "history_restart_speciesconc_only": True,
            "hemco_missing_species_policy": "CYS",
            "gcclassic_end_marker": "END OF GEOS--CHEM",
            "executable_sha256": actual_exe_sha,
        }
        (evidence / "runtime_status.json").write_text(json.dumps(runtime_status, indent=2, sort_keys=True) + "\n")

        for name in [
            "REFERENCE_CASE.json",
            "geoschem_config.yml",
            "HEMCO_Config.rc",
            "HISTORY.rc",
            "GC.log",
            "log.dryrun",
            "log.dryrun.after_download",
            "download_data_skip.log",
            "download_official_inputs.log",
        ]:
            src = rundir / name
            if src.is_file():
                shutil.copy2(src, evidence / name)

    matrix_output = work_root / "matrix_acceptance.json"
    run(
        [
            sys.executable,
            str(control_root / "scripts/validate_reference_matrix.py"),
            "--matrix",
            str(matrix_path),
            "--results-root",
            str(cases_root),
            "--expected-executable-sha256",
            actual_exe_sha,
            "--output",
            str(matrix_output),
        ],
        env=env,
    )
    print(f"FULL_MATRIX_ACCEPTANCE={matrix_output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
