from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_reference_workflow_gates_control_plane_provenance_before_matrix():
    text = (ROOT / ".github/workflows/gc14-reference-producer.yml").read_text()
    gate_marker = "Verify candidate control-plane provenance"
    matrix_marker = "Run full DJF/MAM/JJA/SON validation matrix"
    assert gate_marker in text
    assert text.index(gate_marker) < text.index(matrix_marker)

    gate = text[text.index(gate_marker):text.index(matrix_marker)]
    for marker in [
        "org.opencontainers.image.revision",
        "scripts/run_reference_matrix.py",
        "/opt/control/scripts/run_reference_matrix.py",
        "scripts/validate_reference_pair.py",
        "/opt/control/scripts/validate_reference_pair.py",
        "control_plane_provenance.json",
        "control-plane provenance mismatch",
    ]:
        assert marker in gate

    assert text.count("/tmp/gc14-release-gate/matrix-work/control_plane_provenance.json") >= 2
