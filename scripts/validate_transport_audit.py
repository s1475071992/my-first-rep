#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from netCDF4 import Dataset


def validate(path: Path, domain: str, expected_steps: int, expected_dt: float) -> dict:
    with Dataset(path) as ds:
        assert ds.schema_id == 'GC14_7_1_MINIMAL_TRANSPORT_AUDIT_V1'
        assert ds.domain_kind == domain
        step = np.asarray(ds.variables['step_id'][:])
        runtime_dt = np.asarray(ds.variables['runtime_dt_s'][:], dtype=np.float64)
        assert len(step) == expected_steps
        assert np.array_equal(step, np.arange(expected_steps, dtype=step.dtype))
        assert np.array_equal(runtime_dt, np.full(expected_steps, expected_dt, dtype=np.float64))
        for name in ('xmass_pjc_tpcore_hpa_step','ymass_pjc_tpcore_hpa_step','hybrid_a_tpcore_hpa','hybrid_b_tpcore_1'):
            a = np.asarray(ds.variables[name][:])
            assert np.isfinite(a).all(), name
        if domain == 'GLOBAL_LATLON':
            assert ds.vertical_operator_kind == 'WZ_PRESSURE_MASS_FLUX'
            w = np.asarray(ds.variables['wz_gc_native_hpa_step'][:])
            assert np.isfinite(w).all()
            # TPCORE lev order is top->surface and WZ(:,:,KM) is exactly zero.
            assert np.array_equal(w[:, -1, :, :], np.zeros_like(w[:, -1, :, :]))
        elif domain == 'GEOSCHEM_NESTED_REGIONAL':
            assert ds.vertical_operator_kind == 'PRESSURE_REMAP_MAP1_PPM'
            pe = np.asarray(ds.variables['pe_src_tpcore_hpa'][:])
            ps = np.asarray(ds.variables['ps_target_tpcore_hpa'][:])
            assert np.isfinite(pe).all() and np.isfinite(ps).all()
            assert pe.shape[1] == ds.dimensions['ilev_tpcore'].size
        else:
            raise AssertionError(domain)
    return {
        'status': 'PASS',
        'domain_kind': domain,
        'global_step_count': expected_steps if domain == 'GLOBAL_LATLON' else None,
        'nested_step_count': expected_steps if domain == 'GEOSCHEM_NESTED_REGIONAL' else None,
        'runtime_dt': expected_dt,
        'file': str(path),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('--domain', required=True, choices=['GLOBAL_LATLON','GEOSCHEM_NESTED_REGIONAL'])
    p.add_argument('--expected-steps', type=int, required=True)
    p.add_argument('--expected-dt', type=float, required=True)
    p.add_argument('--json-out')
    args = p.parse_args()
    result = validate(Path(args.file), args.domain, args.expected_steps, args.expected_dt)
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.json_out:
        Path(args.json_out).write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
