import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "config" / "nested_noop_case.json"
CREATE = ROOT / "scripts" / "create_nested_noop_rundir.sh"
AUDIT = ROOT / "scripts" / "audit_nested_dryrun.py"
WORKFLOW = ROOT / ".github" / "workflows" / "gc14-input-probe.yml"


def test_nested_case_contract_is_pinned():
    assert CASE.exists(), "missing config/nested_noop_case.json"
    case = json.loads(CASE.read_text())
    assert case["case_id"] == "GCNOOP_NESTED_EU_JJA_20190701_V1"
    assert case["purpose"] == "DIAGNOSTIC_INSTRUMENTATION_NOOP_QUALIFICATION"
    assert case["domain_kind"] == "GEOSCHEM_NESTED_REGIONAL"
    assert case["domain_code"] == "EU"
    assert case["grid"] == "0.5x0.625"
    assert case["lon_range"] == [-30.0, 50.0]
    assert case["lat_range"] == [30.0, 70.0]
    assert case["buffer_zone_NSEW"] == [3, 3, 3, 3]
    assert case["boundary_conditions_required"] is True
    assert case["met"] == "MERRA2"
    assert case["vertical_levels"] == 72
    assert case["simulation"] == "TransportTracers"
    assert case["primary_tracer"] == "PassiveTracer"
    assert case["start_date"] == "2019-07-01T00:00:00Z"
    assert case["duration_seconds"] == 3600
    assert case["transport_timestep_seconds"] == 300
    assert case["expected_transport_steps"] == 12
    assert case["chemistry_timestep_seconds"] == 600
    assert case["gcclassic_sha"] == "c36ecd760c6663a62769f05a7449c927b8faf54b"
    assert case["geoschem_sha"] == "b9f570e2c7a98b308004cd07e2985a12a47b6f5c"
    assert case["scientific_thresholds_modified"] is False


def test_rundir_script_uses_official_creator_and_dryrun_only_contract():
    assert CREATE.exists(), "missing scripts/create_nested_noop_rundir.sh"
    text = CREATE.read_text()
    assert "createRunDir.sh" in text
    assert "TransportTracers" in text
    assert "0.5x0.625" in text
    assert "Europe" in text or "_EU_" in text
    assert "transport_timestep_in_s: 300" in text
    assert "CYS" in text
    assert "gcclassic --dryrun" not in text, "creation script must not run the model"


def test_nested_eu_ocean_mask_uses_regional_constants_file():
    text = CREATE.read_text()
    assert "OCEAN_MASK" in text
    assert "CN.$RES.EU.$NC" in text
    assert "CN.$RES.$NC" in text


def test_audit_script_classifies_required_input_families():
    assert AUDIT.exists(), "missing scripts/audit_nested_dryrun.py"
    text = AUDIT.read_text()
    for token in ["MET", "RESTART", "BC", "DRYRUN", "RESOLVABLE", "SHA256"]:
        assert token in text


def test_workflow_is_probe_only_and_uploads_required_evidence():
    text = WORKFLOW.read_text()
    for token in [
        "gcclassic --dryrun",
        "download_data.yml",
        "log.dryrun",
        "geoschem_config.yml",
        "HEMCO_Config.rc",
        "HISTORY.rc",
        "species_database.yml",
        "nested_input_probe.json",
        "control_sha256.txt",
        "actions/upload-artifact@v4",
    ]:
        assert token in text
    forbidden = ["docker/login-action", "docker push", "ghcr.io", "./gcclassic >", "./gcclassic 2>"]
    for token in forbidden:
        assert token not in text
