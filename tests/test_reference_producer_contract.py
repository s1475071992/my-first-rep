from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_reference_producer_files_exist():
    required = [
        "scripts/bootstrap_gcclassic.sh",
        "scripts/create_transporttracers_rundir.sh",
        "scripts/validate_dryrun.py",
        "scripts/write_provenance.py",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, f"missing reference-producer files: {missing}"


def test_reference_strategy_remains_external_only():
    design = (ROOT / "docs/GC14_7_1_REFERENCE_PRODUCER_V1_DESIGN.md").read_text()
    assert "GEOS-Chem is **not** a neural training label" in design
    assert "L5 forward numerical equivalence is not claimed" in design
