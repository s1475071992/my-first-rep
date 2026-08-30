#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from netCDF4 import Dataset


def eq_array(a, b) -> bool:
    aa = np.asanyarray(a)
    bb = np.asanyarray(b)
    if aa.shape != bb.shape or aa.dtype != bb.dtype:
        return False
    if np.ma.isMaskedArray(aa) or np.ma.isMaskedArray(bb):
        am = np.ma.getmaskarray(aa)
        bm = np.ma.getmaskarray(bb)
        if not np.array_equal(am, bm):
            return False
        aa = np.ma.getdata(aa)
        bb = np.ma.getdata(bb)
    if np.issubdtype(aa.dtype, np.floating):
        return np.array_equal(aa, bb, equal_nan=True)
    return np.array_equal(aa, bb)


def compare_nc(a: Path, b: Path) -> dict:
    failures = []
    with Dataset(a) as da, Dataset(b) as db:
        va = set(da.variables)
        vb = set(db.variables)
        if va != vb:
            failures.append({'kind': 'variable_set', 'a_only': sorted(va-vb), 'b_only': sorted(vb-va)})
        for name in sorted(va & vb):
            xa = da.variables[name]
            xb = db.variables[name]
            if xa.dimensions != xb.dimensions:
                failures.append({'kind': 'dimensions', 'variable': name,
                                 'a': xa.dimensions, 'b': xb.dimensions})
                continue
            aa = xa[:]
            bb = xb[:]
            if not eq_array(aa, bb):
                ad = np.asanyarray(np.ma.getdata(aa))
                bd = np.asanyarray(np.ma.getdata(bb))
                item = {'kind': 'values', 'variable': name,
                        'shape_a': list(ad.shape), 'shape_b': list(bd.shape),
                        'dtype_a': str(ad.dtype), 'dtype_b': str(bd.dtype)}
                if ad.shape == bd.shape and np.issubdtype(ad.dtype, np.number) and np.issubdtype(bd.dtype, np.number):
                    diff = np.abs(ad.astype(np.float64) - bd.astype(np.float64))
                    finite = np.isfinite(diff)
                    item['max_abs_diff'] = float(diff[finite].max()) if finite.any() else None
                failures.append(item)
    return {'file_a': str(a), 'file_b': str(b), 'failures': failures}


def collect(root: Path) -> dict[str, Path]:
    out = {}
    for sub in ('OutputDir', 'Restarts'):
        p = root / sub
        if not p.exists():
            continue
        for f in sorted(p.glob('*.nc4')):
            # BoundaryConditions are an input-lineage product, not the state no-op surface.
            if 'BoundaryConditions' in f.name:
                continue
            out[f'{sub}/{f.name}'] = f
    return out


def compare_roots(a: Path, b: Path) -> dict:
    fa, fb = collect(a), collect(b)
    failures = []
    if set(fa) != set(fb):
        failures.append({'kind': 'file_set', 'a_only': sorted(set(fa)-set(fb)), 'b_only': sorted(set(fb)-set(fa))})
    files = []
    for rel in sorted(set(fa) & set(fb)):
        r = compare_nc(fa[rel], fb[rel])
        r['relative_path'] = rel
        files.append(r)
        failures.extend([{'relative_path': rel, **x} for x in r['failures']])
    return {
        'status': 'PASS' if not failures else 'FAIL',
        'comparison_rule': 'EXACT_ELEMENTWISE_SCIENTIFIC_ARRAY_EQUALITY',
        'root_a': str(a), 'root_b': str(b),
        'file_count': len(files),
        'failures': failures,
        'files': files,
        'scientific_thresholds_modified': False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('root_a')
    p.add_argument('root_b')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    result = compare_roots(Path(args.root_a), Path(args.root_b))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k: result[k] for k in ('status','file_count','comparison_rule')}, sort_keys=True))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
