from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / 'scripts' / 'apply_transport_audit_patch.py'
OUTPUT_CFG = ROOT / 'scripts' / 'configure_instantaneous_outputs.py'
DOWNLOADER = ROOT / 'scripts' / 'download_official_inputs.sh'
PACKER = ROOT / 'scripts' / 'pack_transport_audit.py'
VALIDATOR = ROOT / 'scripts' / 'validate_transport_audit.py'


def test_transport_audit_patcher_exists_and_is_pinned():
    assert PATCHER.exists(), 'missing scripts/apply_transport_audit_patch.py'
    text = PATCHER.read_text()
    for token in [
        'b9f570e2c7a98b308004cd07e2985a12a47b6f5c',
        'transport_audit_mod.F90',
        'GC_TRANSPORT_AUDIT',
        'GC_TRANSPORT_AUDIT_PATH',
        'Audit_Capture_Horiz',
        'Audit_Capture_Global_WZ',
        'Audit_Capture_Nested_Vert',
        'runtime_dt_s',
    ]:
        assert token in text


def test_patcher_targets_only_diagnostic_allowlist():
    text = PATCHER.read_text()
    for path in [
        'GeosCore/CMakeLists.txt',
        'GeosCore/transport_mod.F90',
        'GeosCore/tpcore_fvdas_mod.F90',
        'GeosCore/tpcore_window_mod.F90',
    ]:
        assert path in text
    for forbidden in [
        'pjc_pfix_mod.F90',
        'pjc_pfix_window_mod.F90',
        'Calc_Vert_Mass_Flux arithmetic',
        'qmap arithmetic',
    ]:
        assert forbidden not in text


def test_hook_is_minimal_and_source_native():
    text = PATCHER.read_text()
    for token in [
        'xmass.bin', 'ymass.bin',
        'wz.bin',
        'pe_src.bin', 'ps_target.bin', 'ak.bin', 'bk.bin',
        'window_meta.txt',
        'source_fp_bytes', 'lev_tpcore=top_to_surface',
    ]:
        assert token in text
    for duplicated_state in [
        'q_pre.bin', 'q_post.bin',
        'ad_pre.bin', 'ad_post.bin',
        'delp_pre.bin', 'delp_post.bin',
        'pedge_pre.bin', 'pedge_post.bin',
    ]:
        assert duplicated_state not in text
    assert '28.97' not in text
    assert '28.9644' not in text, 'hook must not perform molecular-weight conversion'


def test_official_outputs_are_instantaneous():
    assert OUTPUT_CFG.exists(), 'missing scripts/configure_instantaneous_outputs.py'
    text = OUTPUT_CFG.read_text()
    for token in [
        'SpeciesConc', 'StateMet', 'StateMetLevEdge',
        'instantaneous', 'SpeciesConcVV', 'Met_AD', 'Met_DELPDRY', 'Met_PEDGEDRY',
        'BoundaryConditions', 'SpeciesBC_?ADV?',
    ]:
        assert token in text
    for forbidden in ['time-averaged', 'monthly mean', 'daily mean']:
        assert forbidden not in text.lower()


def test_instantaneous_state_file_duration_exceeds_sampling_frequency():
    """GC14.7.1 does not create the t=0 file when instantaneous frequency==duration."""
    text = OUTPUT_CFG.read_text()
    assert "p.add_argument('--file-duration-seconds', type=int, default=3600)" in text
    assert 'file_duration = interval(file_duration_seconds)' in text
    assert 'SpeciesConc.duration:       {file_duration}' in text
    assert 'StateMet.duration:          {file_duration}' in text
    assert 'StateMetLevEdge.duration:    {file_duration}' in text
    assert 'SpeciesConc.duration:       {freq}' not in text
    assert 'StateMet.duration:          {freq}' not in text
    assert 'StateMetLevEdge.duration:    {freq}' not in text


def test_downloaded_local_restart_is_shared_across_abc_runs():
    """A/B/C must start from byte-identical local restart files."""
    text = DOWNLOADER.read_text()
    for token in [
        'REFERENCE_INPUT_SIBLING_RESTART_SYNC=PASS',
        'basename "$RUNDIR"',
        '$PARENT/B',
        '$PARENT/C',
        'sha256sum',
        'GEOSChem.Restart.',
    ]:
        assert token in text
    assert '$PARENT/B/OutputDir' not in text
    assert '$PARENT/C/OutputDir' not in text


def test_packer_and_validator_are_part_of_formal_contract():
    assert PACKER.exists(), 'missing scripts/pack_transport_audit.py'
    assert VALIDATOR.exists(), 'missing scripts/validate_transport_audit.py'
    pack = PACKER.read_text()
    val = VALIDATOR.read_text()
    for token in ['transport_audit.nc4', 'order="F"', 'GLOBAL_LATLON', 'GEOSCHEM_NESTED_REGIONAL']:
        assert token in pack
    for token in ['global_step_count', 'nested_step_count', 'runtime_dt', 'PASS']:
        assert token in val
