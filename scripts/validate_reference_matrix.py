#!/usr/bin/env python3
"""Aggregate the frozen four-season/five-region reference release gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(matrix: dict, results_root: Path, expected_executable_sha256: str) -> dict:
    expected_regions = [item["region_id"] for item in matrix["holdout_regions"]]
    case_records = []
    region_cell_count = 0

    for case in matrix["cases"]:
        case_id = case["case_id"]
        evidence = results_root / case_id / "evidence"
        pair_path = evidence / "pair_acceptance.json"
        runtime_path = evidence / "runtime_status.json"
        if not pair_path.is_file():
            raise ValueError(f"missing pair acceptance: {pair_path}")
        if not runtime_path.is_file():
            raise ValueError(f"missing runtime status: {runtime_path}")
        pair = json.loads(pair_path.read_text())
        runtime = json.loads(runtime_path.read_text())
        if pair.get("status") != "PASS":
            raise ValueError(f"reference pair did not pass: {case_id}")
        if runtime.get("status") != "PASS":
            raise ValueError(f"runtime did not pass: {case_id}")
        if pair.get("season") != case["season"]:
            raise ValueError(f"season mismatch for {case_id}")
        if pair.get("executable_sha256") != expected_executable_sha256:
            raise ValueError(f"executable identity mismatch for {case_id}")
        if runtime.get("executable_sha256") != expected_executable_sha256:
            raise ValueError(f"runtime executable identity mismatch for {case_id}")
        regions = pair.get("regions", {})
        if list(regions) != expected_regions:
            raise ValueError(f"region order/set mismatch for {case_id}: {list(regions)}")
        for rid in expected_regions:
            if regions[rid].get("status") != "PASS":
                raise ValueError(f"region {rid} did not pass for {case_id}")
            region_cell_count += 1
        case_records.append(
            {
                "case_id": case_id,
                "season": case["season"],
                "status": "PASS",
                "pair_acceptance": str(pair_path),
                "runtime_status": str(runtime_path),
            }
        )

    if len(case_records) != 4:
        raise ValueError(f"expected 4 seasonal cases, got {len(case_records)}")
    if region_cell_count != 20:
        raise ValueError(f"expected 20 season-region acceptance cells, got {region_cell_count}")

    return {
        "status": "PASS",
        "release_gate": "GC14_7_1_REFERENCE_IMAGE_FULL_MATRIX_V1",
        "matrix_id": matrix["matrix_id"],
        "case_count": len(case_records),
        "region_count": len(expected_regions),
        "season_region_cell_count": region_cell_count,
        "seasons": [case["season"] for case in matrix["cases"]],
        "regions": expected_regions,
        "executable_sha256": expected_executable_sha256,
        "scientific_thresholds_modified": False,
        "cases": case_records,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--matrix", required=True)
    p.add_argument("--results-root", required=True)
    p.add_argument("--expected-executable-sha256", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    matrix = json.loads(Path(args.matrix).read_text())
    payload = validate(matrix, Path(args.results_root).resolve(), args.expected_executable_sha256)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
