#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

SCHEMA_ID = 'GC14_7_1_MINIMAL_TRANSPORT_AUDIT_V1'


def read_meta(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def dtype_for(meta: dict[str, str]):
    n = int(meta['source_fp_bytes'])
    if n == 8:
        return np.dtype('<f8')
    if n == 4:
        return np.dtype('<f4')
    raise ValueError(f'unsupported source_fp_bytes={n}')


def read_fortran(path: Path, dtype, shape: tuple[int, ...]) -> np.ndarray:
    a = np.fromfile(path, dtype=dtype)
    expected = int(np.prod(shape))
    if a.size != expected:
        raise ValueError(f'{path}: expected {expected} values, got {a.size}')
    return a.reshape(shape, order="F")


def find_steps(raw: Path):
    metas = sorted(raw.glob('step_*_window_meta.txt'))
    if not metas:
        raise RuntimeError('no transport audit metadata files')
    steps = []
    for p in metas:
        m = re.search(r'step_(\d{6})_window_meta\.txt$', p.name)
        if not m:
            continue
        step = int(m.group(1))
        meta = read_meta(p)
        if int(meta['step_id']) != step:
            raise RuntimeError(f'step id mismatch in {p}')
        steps.append((step, meta))
    return steps


def pack(raw: Path, output: Path) -> dict:
    steps = find_steps(raw)
    first = steps[0][1]
    domain = first['domain_kind']
    if domain not in ('GLOBAL_LATLON', 'GEOSCHEM_NESTED_REGIONAL'):
        raise ValueError(domain)
    nx, ny, nz, nedge = (int(first[k]) for k in ('nx','ny','nz','nedge'))
    source_fp_bytes = int(first['source_fp_bytes'])
    dt = dtype_for(first)

    for expected, (step, meta) in enumerate(steps):
        if step != expected:
            raise RuntimeError(f'non-contiguous step sequence at {step}, expected {expected}')
        for k in ('domain_kind','nx','ny','nz','nedge','source_fp_bytes'):
            if meta[k] != first[k]:
                raise RuntimeError(f'inconsistent {k} at step {step}')

    output.parent.mkdir(parents=True, exist_ok=True)
    with Dataset(output, 'w', format='NETCDF4') as ds:
        ds.schema_id = SCHEMA_ID
        ds.schema_version = 1
        ds.domain_kind = domain
        ds.source_fp_bytes = source_fp_bytes
        ds.lev_tpcore = 'top_to_surface'
        ds.native_capture_only = 'true'
        ds.createDimension('step', len(steps))
        ds.createDimension('transport_x', nx)
        ds.createDimension('transport_y', ny)
        ds.createDimension('lev_tpcore', nz)
        ds.createDimension('ilev_tpcore', nedge)

        vstep = ds.createVariable('step_id', 'i8', ('step',))
        vdt = ds.createVariable('runtime_dt_s', 'f8', ('step',))
        vx = ds.createVariable('xmass_pjc_tpcore_hpa_step', 'f8', ('step','lev_tpcore','transport_y','transport_x'))
        vy = ds.createVariable('ymass_pjc_tpcore_hpa_step', 'f8', ('step','lev_tpcore','transport_y','transport_x'))
        vak = ds.createVariable('hybrid_a_tpcore_hpa', 'f8', ('ilev_tpcore',))
        vbk = ds.createVariable('hybrid_b_tpcore_1', 'f8', ('ilev_tpcore',))
        if domain == 'GLOBAL_LATLON':
            vv = ds.createVariable('wz_gc_native_hpa_step', 'f8', ('step','lev_tpcore','transport_y','transport_x'))
            ds.vertical_operator_kind = 'WZ_PRESSURE_MASS_FLUX'
        else:
            vpe = ds.createVariable('pe_src_tpcore_hpa', 'f8', ('step','ilev_tpcore','transport_y','transport_x'))
            vps = ds.createVariable('ps_target_tpcore_hpa', 'f8', ('step','transport_y','transport_x'))
            ds.vertical_operator_kind = 'PRESSURE_REMAP_MAP1_PPM'
            for k in ('i_start_gc','i_end_gc','j_start_gc','j_end_gc','west_buffer','east_buffer','south_buffer','north_buffer'):
                setattr(ds, k, int(first[k]))

        for idx, (step, meta) in enumerate(steps):
            prefix = raw / f'step_{step:06d}_'
            vstep[idx] = step
            vdt[idx] = float(meta['runtime_dt_s'])
            x = read_fortran(Path(str(prefix)+'xmass.bin'), dt, (nx,ny,nz)).transpose(2,1,0)
            y = read_fortran(Path(str(prefix)+'ymass.bin'), dt, (nx,ny,nz)).transpose(2,1,0)
            vx[idx] = x.astype(np.float64, copy=False)
            vy[idx] = y.astype(np.float64, copy=False)
            ak = read_fortran(Path(str(prefix)+'ak.bin'), dt, (nedge,))
            bk = read_fortran(Path(str(prefix)+'bk.bin'), dt, (nedge,))
            if idx == 0:
                vak[:] = ak.astype(np.float64, copy=False)
                vbk[:] = bk.astype(np.float64, copy=False)
            else:
                if not (np.array_equal(ak, vak[:]) and np.array_equal(bk, vbk[:])):
                    raise RuntimeError('hybrid coordinates changed across transport steps')
            if domain == 'GLOBAL_LATLON':
                w = read_fortran(Path(str(prefix)+'wz.bin'), dt, (nx,ny,nz)).transpose(2,1,0)
                vv[idx] = w.astype(np.float64, copy=False)
            else:
                pe = read_fortran(Path(str(prefix)+'pe_src.bin'), dt, (nx,nedge,ny)).transpose(1,2,0)
                ps = read_fortran(Path(str(prefix)+'ps_target.bin'), dt, (nx,ny)).transpose(1,0)
                vpe[idx] = pe.astype(np.float64, copy=False)
                vps[idx] = ps.astype(np.float64, copy=False)

    manifest = {
        'schema_id': SCHEMA_ID,
        'domain_kind': domain,
        'step_count': len(steps),
        'runtime_dt_s': [float(m['runtime_dt_s']) for _, m in steps],
        'source_fp_bytes': source_fp_bytes,
        'output': str(output),
    }
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('raw_dir')
    p.add_argument('output', help='transport_audit.nc4')
    args = p.parse_args()
    result = pack(Path(args.raw_dir), Path(args.output))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
