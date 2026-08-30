import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'gc14-global-asia-checkpoint.yml'
ASIA_CASE = ROOT / 'config' / 'global_asia_checkpoint_case.json'
CREATE_ASIA = ROOT / 'scripts' / 'create_nested_asia_rundir.sh'


def test_asia_case_is_pinned():
    assert ASIA_CASE.exists(), 'missing Asia checkpoint case config'
    case = json.loads(ASIA_CASE.read_text())
    assert case['schema_id'] == 'GC14_7_1_GLOBAL_ASIA_CHECKPOINT_CASE_V1'
    assert case['nested_case_id'] == 'GCNOOP_NESTED_AS_JJA_20190701_V1'
    assert case['nested_domain_kind'] == 'GEOSCHEM_NESTED_REGIONAL'
    assert case['nested_domain_name'] == 'Asia'
    assert case['nested_domain_code'] == 'AS'
    assert case['nested_grid'] == '0.5x0.625'
    assert case['nested_lon_range'] == [60.0, 150.0]
    assert case['nested_lat_range'] == [-11.0, 55.0]
    assert case['global_transport_timestep_seconds'] == 600
    assert case['nested_transport_timestep_seconds'] == 300
    assert case['global_expected_transport_steps'] == 6
    assert case['nested_expected_transport_steps'] == 12
    assert case['checkpoint_repository'] == 'ghcr.io/s1475071992/gcclassic-paper1-checkpoint'


def test_asia_rundir_uses_official_creator_and_nested_restart_path():
    assert CREATE_ASIA.exists(), 'missing Asia run-directory creator'
    text = CREATE_ASIA.read_text()
    for token in [
        'createRunDir.sh',
        "printf '7\\n1\\n3\\n2\\n1\\n%s\\n\\nn\\n'",
        'gc_05x0625_AS_merra2_TransportTracers',
        "[60.0, 150.0]",
        "[-11.0, 55.0]",
        "read_restart_as_real8'] = False",
        'CN.$RES.AS.$NC',
    ]:
        assert token in text


def test_unified_workflow_order_and_snapshot_contract():
    assert WORKFLOW.exists(), 'missing unified GLOBAL->Asia checkpoint workflow'
    text = WORKFLOW.read_text()
    required_steps = [
        'Run and validate GLOBAL A/B/C',
        'Produce GLOBAL BoundaryConditions',
        'Bootstrap exact source for Asia',
        'Compile Asia baseline executable',
        'Compile Asia instrumented executable',
        'Run and validate Asia NESTED A/B/C',
        'Assemble reusable checkpoint',
        'Build and push checkpoint image',
        'Verify published checkpoint image',
    ]
    positions = [text.index(step) for step in required_steps]
    assert positions == sorted(positions), 'GLOBAL -> BC -> Asia -> checkpoint order changed'
    for token in [
        'packages: write',
        'GCNOOP_NESTED_AS_JJA_20190701_V1',
        '--domain GLOBAL_LATLON --expected-steps 6 --expected-dt 600',
        '--domain GEOSCHEM_NESTED_REGIONAL --expected-steps 12 --expected-dt 300',
        'apply_transport_audit_patch.py',
        'cmake ../CodeDir -DRUNDIR=.. -DCMAKE_BUILD_TYPE=Release -DOMP=n',
        'SHA256(global produced BC)',
        'checkpoint/ExtData',
        'checkpoint/global',
        'checkpoint/nested',
        'checkpoint/bc-producer',
        'checkpoint/software',
        'ghcr.io/s1475071992/gcclassic-paper1-checkpoint',
        '14.7.1-global-asia-v1-run-${{ github.run_id }}',
        'sha256:209a95291bdcf009390eb2a57d298a1fe1c354546a7b55408c252b89a9574518',
    ]:
        assert token in text
    assert 'docker commit' not in text


def test_nested_is_compiled_after_global_validation_not_reused_from_global():
    text = WORKFLOW.read_text()
    global_done = text.index('Run and validate GLOBAL A/B/C')
    nested_bootstrap = text.index('Bootstrap exact source for Asia')
    nested_compile = text.index('Compile Asia baseline executable')
    nested_run = text.index('Run and validate Asia NESTED A/B/C')
    assert global_done < nested_bootstrap < nested_compile < nested_run
    assert 'asia-baseline/gcclassic' in text
    assert 'asia-instrumented/gcclassic' in text
