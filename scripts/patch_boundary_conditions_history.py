#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

COLLECTION_BLOCK = """COLLECTIONS: 'Restart',
             'BoundaryConditions',
::"""

# Keep the metadata/field syntax byte-for-byte equivalent to the official
# GCClassic 14.7.1 fullchem BoundaryConditions collection, while activating
# only Restart + BoundaryConditions for this dedicated BC producer.
BC_BLOCK = """
#==============================================================================
# %%%%% THE BoundaryConditions COLLECTION %%%%%
#
# GEOS-Chem boundary conditions for use in nested grid simulations
#
# NOTE: Do not change the BoundaryConditions.frequency setting below,
# because GEOS-Chem nested-grid simulations expect to read boundary
# condition data at 3 hour intervals.
#==============================================================================
  BoundaryConditions.template:   '%y4%m2%d2_%h2%n2z.nc4',
  BoundaryConditions.frequency:  00000000 030000
  BoundaryConditions.duration:   00000001 000000
  BoundaryConditions.mode:       'instantaneous'
  BoundaryConditions.fields:     'SpeciesBC_?ADV?             ',
::
"""


def patch(path: Path) -> None:
    text = path.read_text()
    collections = re.compile(r"^COLLECTIONS:.*?^::\s*$", re.MULTILINE | re.DOTALL)
    text, count = collections.subn(COLLECTION_BLOCK, text, count=1)
    if count != 1:
        raise RuntimeError("expected exactly one HISTORY COLLECTIONS declaration")

    existing = re.compile(
        r"^#=+\n# %%%%% THE BoundaryConditions COLLECTION %%%%%.*?^::\s*$",
        re.MULTILINE | re.DOTALL,
    )
    if existing.search(text):
        text = existing.sub(BC_BLOCK.strip(), text, count=1)
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += BC_BLOCK

    path.write_text(text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("history")
    args = ap.parse_args()
    patch(Path(args.history))


if __name__ == "__main__":
    main()
