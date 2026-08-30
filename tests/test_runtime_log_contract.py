from pathlib import Path
import importlib.util

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_matrix_runner():
    path = ROOT / "scripts/run_reference_matrix.py"
    spec = importlib.util.spec_from_file_location("run_reference_matrix", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runtime_log_accepts_gcclassic_14_spaced_end_banner(tmp_path):
    module = load_matrix_runner()
    log = tmp_path / "GC.log"
    log.write_text("E N D   O F   G E O S -- C H E M\n")
    module.assert_runtime_log(log)


def test_runtime_log_rejects_fatal_marker_even_with_valid_end_banner(tmp_path):
    module = load_matrix_runner()
    log = tmp_path / "GC.log"
    log.write_text("HEMCO ERROR\nE N D   O F   G E O S -- C H E M\n")
    with pytest.raises(RuntimeError, match="fatal markers"):
        module.assert_runtime_log(log)


def test_runtime_log_rejects_missing_end_banner(tmp_path):
    module = load_matrix_runner()
    log = tmp_path / "GC.log"
    log.write_text("normal model output without final banner\n")
    with pytest.raises(RuntimeError, match="did not reach END OF GEOS--CHEM"):
        module.assert_runtime_log(log)
