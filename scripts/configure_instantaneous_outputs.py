#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def interval(seconds: int) -> str:
    if seconds <= 0:
        raise ValueError('seconds must be positive')
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{days:08d} {hours:02d}{minutes:02d}{secs:02d}"


def replace_one(text: str, pattern: str, repl: str, label: str) -> str:
    text2, n = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE | re.DOTALL)
    if n != 1:
        raise RuntimeError(f'{label}: expected one match, got {n}')
    return text2


def configure_history(path: Path, seconds: int, boundary_conditions: bool) -> None:
    freq = interval(seconds)
    text = path.read_text()
    collections = ["'Restart'", "'SpeciesConc'", "'StateMet'", "'StateMetLevEdge'"]
    if boundary_conditions:
        collections.append("'BoundaryConditions'")
    block = 'COLLECTIONS: ' + ',\n             '.join(collections) + ',\n::'
    text = replace_one(text, r'^COLLECTIONS:.*?^::\s*$', block, 'COLLECTIONS')

    species = f"""  SpeciesConc.template:       '%y4%m2%d2_%h2%n2z.nc4',
  SpeciesConc.frequency:      {freq}
  SpeciesConc.duration:       {freq}
  SpeciesConc.mode:           'instantaneous'
  SpeciesConc.fields:         'SpeciesConcVV_?ALL?           ',
::"""
    text = replace_one(text, r'^  SpeciesConc\.template:.*?^::\s*$', species, 'SpeciesConc')

    statemet = f"""  StateMet.template:          '%y4%m2%d2_%h2%n2z.nc4',
  StateMet.frequency:         {freq}
  StateMet.duration:          {freq}
  StateMet.mode:              'instantaneous'
  StateMet.fields:            'Met_AD                        ',
                              'Met_DELPDRY                   ',
::"""
    text = replace_one(text, r'^  StateMet\.template:.*?^::\s*$', statemet, 'StateMet')

    edges = f"""  StateMetLevEdge.template:    '%y4%m2%d2_%h2%n2z.nc4',
  StateMetLevEdge.frequency:   {freq}
  StateMetLevEdge.duration:    {freq}
  StateMetLevEdge.mode:        'instantaneous'
  StateMetLevEdge.fields:      'Met_PEDGEDRY                  ',
::"""
    text = replace_one(text, r'^  StateMetLevEdge\.template:.*?^::\s*$', edges, 'StateMetLevEdge')

    if boundary_conditions:
        bc = """#==============================================================================
# %%%%% THE BoundaryConditions COLLECTION %%%%%
#==============================================================================
  BoundaryConditions.template:    '%y4%m2%d2_%h2%n2z.nc4',
  BoundaryConditions.frequency:   00000000 030000
  BoundaryConditions.duration:    00000000 030000
  BoundaryConditions.mode:        'instantaneous'
  BoundaryConditions.fields:      'SpeciesBC_?ADV?              ',
::
"""
        if 'BoundaryConditions.template:' not in text:
            text = text.rstrip() + '\n' + bc
        else:
            text = replace_one(text, r'^  BoundaryConditions\.template:.*?^::\s*$', bc.strip(), 'BoundaryConditions')

    forbidden = ["SpeciesConc.mode:           'time-averaged'",
                 "StateMet.mode:              'time-averaged'",
                 "StateMetLevEdge.mode:       'time-averaged'"]
    for item in forbidden:
        if item in text:
            raise RuntimeError(f'time averaging survived for retained state collection: {item}')
    path.write_text(text)


def configure_hemco(hemco_diagn: Path | None) -> None:
    # TransportTracers does not require a HEMCO diagnostic collection for the
    # transport-state contract.  If a HEMCO_Diagn.rc is retained, do not add
    # accumulated or averaged diagnostics here: formal HEMCO outputs must be
    # instantaneous by construction.  BoundaryConditions are emitted by
    # HISTORY as an instantaneous collection, not by HEMCO diagnostics.
    if hemco_diagn is None or not hemco_diagn.exists():
        return
    text = hemco_diagn.read_text()
    lowered = text.lower()
    for forbidden in ('time-averaged', 'monthly mean', 'daily mean'):
        if forbidden in lowered:
            raise RuntimeError(f'non-instantaneous retained HEMCO diagnostic policy found: {forbidden}')


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('history')
    p.add_argument('--seconds', type=int, required=True)
    p.add_argument('--boundary-conditions', action='store_true')
    p.add_argument('--hemco-diagn')
    args = p.parse_args()
    configure_history(Path(args.history), args.seconds, args.boundary_conditions)
    configure_hemco(Path(args.hemco_diagn) if args.hemco_diagn else None)
    print('instantaneous HISTORY/HEMCO output policy configured')


if __name__ == '__main__':
    main()
