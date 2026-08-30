from pathlib import Path
import importlib.util
import json
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_required_reference_producer_files_exist():
    required = [
        "scripts/bootstrap_gcclassic.sh",
        "scripts/create_transporttracers_rundir.sh",
        "scripts/package_frozen_gcclassic_build.sh",
        "scripts/validate_dryrun.py",
        "scripts/write_provenance.py",
        "scripts/configure_reference_case.py",
        "scripts/patch_history_for_window.py",
        "scripts/download_official_inputs.sh",
        "scripts/validate_reference_outputs.py",
        "scripts/validate_reference_pair.py",
        "scripts/validate_reference_matrix.py",
        "scripts/run_reference_matrix.py",
        "scripts/package_gc_holdout.py",
        "config/reference_matrix.json",
        "config/frozen_gcclassic_build.json",
        ".github/workflows/gc14-build.yml",
        ".github/workflows/gc14-reference-producer.yml",
        "docker/gc14-reference/Dockerfile",
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


def test_one_hour_case_reduces_history_to_transport_audit_collections(tmp_path):
    module = load_script(ROOT / "scripts/patch_history_for_window.py", "patch_history_for_window")
    history = tmp_path / "HISTORY.rc"
    history.write_text(
        "COLLECTIONS: 'Restart',\n"
        "             'RadioNuclide',\n"
        "             'SpeciesConc',\n"
        "             'CloudConvFlux',\n"
        "             'StateMet',\n"
        "::\n"
        "SpeciesConc.frequency: 00000001 000000\n"
        "SpeciesConc.duration:  00000001 000000\n"
        "StateMet.frequency:    00000001 000000\n"
    )
    module.patch_for_transport_audit(history, 3600)
    text = history.read_text()
    assert "COLLECTIONS: 'Restart',\n             'SpeciesConc',\n::" in text
    assert "SpeciesConc.frequency: 00000000 010000" in text
    assert "SpeciesConc.duration:  00000000 010000" in text
    assert "StateMet.frequency:    00000001 000000" in text


def test_reference_case_allows_missing_restart_species_with_background_default(tmp_path):
    module = load_script(ROOT / "scripts/configure_reference_case.py", "configure_reference_case")
    hemco = tmp_path / "HEMCO_Config.rc"
    hemco.write_text(
        "(((GC_RESTART\n"
        "* SPC_ ./Restarts/GEOSChem.Restart.$YYYY$MM$DD_$HH$MNz.nc4 "
        "SpeciesRst_?ALL? $YYYY/$MM/$DD/$HH EFYO xyz 1 * - 1 1\n"
        "* DELPDRY ./Restarts/GEOSChem.Restart.$YYYY$MM$DD_$HH$MNz.nc4 "
        "Met_DELPDRY $YYYY/$MM/$DD/$HH EY xyz 1 * - 1 1\n"
        ")))GC_RESTART\n"
    )
    module.patch_hemco_restart_policy(hemco)
    text = hemco.read_text()
    assert "SpeciesRst_?ALL? $YYYY/$MM/$DD/$HH CYS xyz 1 * - 1 1" in text
    assert "Met_DELPDRY $YYYY/$MM/$DD/$HH EY xyz 1 * - 1 1" in text


def test_frozen_build_workflow_owns_compilation():
    text = (ROOT / ".github/workflows/gc14-build.yml").read_text()
    assert "name: gc14-frozen-build" in text
    assert "bash scripts/bootstrap_gcclassic.sh" in text
    assert "cmake ../CodeDir" in text
    assert "make -j2" in text
    assert "gc14-7-1-frozen-build-${{ github.run_id }}" in text
    assert "actions/upload-artifact@v4" in text


def test_frozen_build_pin_is_explicit_and_immutable():
    pin = json.loads((ROOT / "config/frozen_gcclassic_build.json").read_text())
    assert pin["schema_version"] == 1
    assert isinstance(pin["build_run_id"], int) and pin["build_run_id"] > 0
    assert pin["artifact_name"] == f"gc14-7-1-frozen-build-{pin['build_run_id']}"
    assert pin["bundle_filename"] == "gc14-7-1-frozen-build.tar.gz"
    assert re.fullmatch(r"[0-9a-f]{64}", pin["bundle_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", pin["executable_sha256"])
    assert pin["gcclassic_version"] == "14.7.1"
    assert pin["gcclassic_sha"] == "c36ecd760c6663a62769f05a7449c927b8faf54b"
    assert pin["geoschem_sha"] == "b9f570e2c7a98b308004cd07e2985a12a47b6f5c"


def test_reference_workflow_reuses_frozen_build_without_compiling():
    text = (ROOT / ".github/workflows/gc14-reference-producer.yml").read_text()
    assert "actions/download-artifact@v4" in text
    assert "config/frozen_gcclassic_build.json" in text
    assert "run-id: ${{ steps.frozen.outputs.run_id }}" in text
    assert "sha256sum -c" in text
    assert "Verify candidate executable identity" in text
    forbidden = [
        "bash scripts/bootstrap_gcclassic.sh",
        "bash scripts/create_transporttracers_rundir.sh",
        "cmake ../CodeDir",
        "make -j2",
        "make install",
        "build-essential",
        "gfortran",
    ]
    for marker in forbidden:
        assert marker not in text, f"reference workflow must not compile GCClassic; found {marker!r}"


def test_reference_workflow_publishes_only_after_full_matrix_gate():
    text = (ROOT / ".github/workflows/gc14-reference-producer.yml").read_text()
    markers = [
        "Build candidate image locally - DO NOT PUSH",
        "Run full DJF/MAM/JJA/SON validation matrix",
        "Validate release gate - 4 seasons x 5 regions",
        "Upload complete pre-publication validation evidence",
        "Login to GHCR after full matrix PASS",
        "Publish exact validated candidate image without rebuild",
    ]
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions)
    assert "packages: write" in text
    assert "season_region_cell_count'] == 20" in text
    publish_pos = text.index("Publish exact validated candidate image without rebuild")
    assert "docker push" not in text[:publish_pos]
    assert "docker push" in text[publish_pos:]
    assert "docker build" not in text[publish_pos:]


def test_matrix_validator_requires_four_seasons_and_twenty_region_cells(tmp_path):
    module = load_script(ROOT / "scripts/validate_reference_matrix.py", "validate_reference_matrix")
    matrix = json.loads((ROOT / "config/reference_matrix.json").read_text())
    expected_sha = "a" * 64
    root = tmp_path / "cases"
    for case in matrix["cases"]:
        evidence = root / case["case_id"] / "evidence"
        evidence.mkdir(parents=True)
        regions = {
            item["region_id"]: {"status": "PASS"}
            for item in matrix["holdout_regions"]
        }
        (evidence / "pair_acceptance.json").write_text(json.dumps({
            "status": "PASS",
            "season": case["season"],
            "executable_sha256": expected_sha,
            "regions": regions,
        }))
        (evidence / "runtime_status.json").write_text(json.dumps({
            "status": "PASS",
            "executable_sha256": expected_sha,
        }))
    result = module.validate(matrix, root, expected_sha)
    assert result["status"] == "PASS"
    assert result["case_count"] == 4
    assert result["region_count"] == 5
    assert result["season_region_cell_count"] == 20

    broken = root / matrix["cases"][0]["case_id"] / "evidence" / "pair_acceptance.json"
    payload = json.loads(broken.read_text())
    payload["regions"].pop("ARCTIC")
    broken.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="region order/set mismatch"):
        module.validate(matrix, root, expected_sha)
