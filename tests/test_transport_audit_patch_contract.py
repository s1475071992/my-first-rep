from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / 'scripts' / 'apply_transport_audit_patch.py'
PACKER = ROOT / 'scripts' / 'pack_transport_audit.py'
VALIDATOR = ROOT / 'scripts' / 'validate_transport_audit.py'


def test_transport_audit_patcher_exists_and_is_pinned():
    assert PATCHER.exists(), 'missing scripts/apply_transport_audit_patch.py'
    text = PATCHER.read_text()
    for token in [
        'b9f570e2c7a98b308004cd07e2985a12a47b6f5c',
        'transport_audit_mod.F90',
        'KG_SPECIES_PER_KG_DRY_AIR',
        'PassiveTracer',
        'GC_TRANSPORT_AUDIT',
        'GC_TRANSPORT_AUDIT_PATH',
        'Audit_Capture_Pre',
        'Audit_Capture_Horiz',
        'Audit_Capture_Global_WZ',
        'Audit_Capture_Nested_Vert',
        'Audit_Capture_Post_And_Flush',
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


def test_hook_keeps_source_native_units_and_vertical_semantics():
    text = PATCHER.read_text()
    for token in [
        'q_pre.bin', 'q_post.bin',
        'ad_pre.bin', 'ad_post.bin',
        'delp_pre.bin', 'delp_post.bin',
        'pedge_pre.bin', 'pedge_post.bin',
        'xmass.bin', 'ymass.bin',
        'ps1.bin', 'ps2.bin', 'ak.bin', 'bk.bin', 'area.bin',
        'wz.bin', 'pe_src.bin', 'ps_target.bin',
        'source_fp_bytes', 'lev_tpcore=top_to_surface',
    ]:
        assert token in text
    assert '28.97' not in text
    assert '28.9644' not in text, 'hook must not perform molecular-weight conversion'


def test_packer_and_validator_are_part_of_formal_contract():
    assert PACKER.exists(), 'missing scripts/pack_transport_audit.py'
    assert VALIDATOR.exists(), 'missing scripts/validate_transport_audit.py'
    pack = PACKER.read_text()
    val = VALIDATOR.read_text()
    for token in ['transport_audit.nc4', 'order="F"', 'GLOBAL_LATLON', 'GEOSCHEM_NESTED_REGIONAL']:
        assert token in pack
    for token in ['global_step_count', 'nested_step_count', 'runtime_dt', 'PASS']:
        assert token in val
