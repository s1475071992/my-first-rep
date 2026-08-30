from pathlib import Path
import importlib.util
import json
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_reference_matrix", ROOT / "scripts/validate_reference_matrix.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_passing_evidence(root: Path, matrix: dict, expected_sha: str) -> None:
    region_ids = [item["region_id"] for item in matrix["holdout_regions"]]
    for case in matrix["cases"]:
        evidence = root / case["case_id"] / "evidence"
        evidence.mkdir(parents=True)
        regions = {rid: {"status": "PASS"} for rid in region_ids}
        (evidence / "pair_acceptance.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "season": case["season"],
                    "executable_sha256": expected_sha,
                    "regions": regions,
                },
                sort_keys=True,
            )
        )
        (evidence / "runtime_status.json").write_text(
            json.dumps({"status": "PASS", "executable_sha256": expected_sha})
        )


def test_matrix_validator_accepts_same_frozen_region_set_independent_of_json_key_order(tmp_path):
    validator = load_validator()
    matrix = json.loads((ROOT / "config/reference_matrix.json").read_text())
    expected_sha = "a" * 64
    write_passing_evidence(tmp_path, matrix, expected_sha)

    result = validator.validate(matrix, tmp_path, expected_sha)

    assert result["status"] == "PASS"
    assert result["regions"] == [item["region_id"] for item in matrix["holdout_regions"]]
    assert result["season_region_cell_count"] == 20


def test_matrix_validator_rejects_region_set_or_count_change(tmp_path):
    validator = load_validator()
    matrix = json.loads((ROOT / "config/reference_matrix.json").read_text())
    expected_sha = "a" * 64
    write_passing_evidence(tmp_path, matrix, expected_sha)
    first_case = matrix["cases"][0]["case_id"]
    pair_path = tmp_path / first_case / "evidence" / "pair_acceptance.json"
    payload = json.loads(pair_path.read_text())
    payload["regions"].pop("ARCTIC")
    payload["regions"]["EXTRA"] = {"status": "PASS"}
    pair_path.write_text(json.dumps(payload, sort_keys=True))

    with pytest.raises(ValueError, match="region set/count mismatch"):
        validator.validate(matrix, tmp_path, expected_sha)
