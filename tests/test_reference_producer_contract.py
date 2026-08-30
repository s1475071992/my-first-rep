from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_required_reference_producer_files_exist():
    required = [
        "scripts/bootstrap_gcclassic.sh",
        "scripts/create_transporttracers_rundir.sh",
        "scripts/validate_dryrun.py",
        "scripts/write_provenance.py",
        "scripts/configure_reference_case.py",
        "scripts/download_official_inputs.sh",
        "scripts/validate_reference_outputs.py",
        "scripts/package_gc_holdout.py",
        "config/reference_matrix.json",
        "docs/GC_DISCREPANCY_AUDIT_PROTOCOL_V1.md",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, f"missing reference-producer files: {missing}"


def test_reference_strategy_remains_external_only():
    design = (ROOT / "docs/GC14_7_1_REFERENCE_PRODUCER_V1_DESIGN.md").read_text()
    assert "GEOS-Chem is **not** a neural training label" in design
    assert "L5 forward numerical equivalence is not claimed" in design


def test_reference_matrix_freezes_four_seasons_before_scoring():
    matrix = json.loads((ROOT / "config/reference_matrix.json").read_text())
    assert matrix["matrix_id"] == "GC14_7_1_GLOBAL_SEASONAL_HOLDOUT_MATRIX_V1"
    assert matrix["geoschem_as_training_truth"] is False
    cases = matrix["cases"]
    assert [case["season"] for case in cases] == ["DJF", "MAM", "JJA", "SON"]
    assert len({case["start_date"] for case in cases}) == 4
    assert all(case["duration_seconds"] == 3600 for case in cases)
    assert all(case["met"] == "MERRA2" and case["grid"] == "4x5" for case in cases)


def test_holdout_regions_are_frozen_and_nonempty():
    matrix = json.loads((ROOT / "config/reference_matrix.json").read_text())
    region_ids = [item["region_id"] for item in matrix["holdout_regions"]]
    assert region_ids == [
        "TROPICS",
        "NH_MIDLAT",
        "SH_MIDLAT",
        "ARCTIC",
        "ANTARCTIC",
    ]
