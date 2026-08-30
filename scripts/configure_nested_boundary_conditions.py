#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def configure(hemco: Path, boundary_file: Path) -> None:
    boundary_file = boundary_file.resolve()
    if not boundary_file.is_file():
        raise SystemExit(f"boundary file does not exist: {boundary_file}")

    text = hemco.read_text()

    switch = re.compile(r"^(\s*-->\s+GC_BCs\s*:\s*).*$", re.MULTILINE)
    if switch.search(text):
        text = switch.sub(r"\g<1>true", text, count=1)
    else:
        anchor = re.compile(r"^(\s*-->\s+GC_RESTART\s*:\s*true.*)$", re.MULTILINE)
        text, count = anchor.subn(r"\1\n    --> GC_BCs                 :       true", text, count=1)
        if count != 1:
            raise RuntimeError("could not insert GC_BCs extension switch")

    bc_block = f"""
#==============================================================================
# --- GEOS-Chem boundary condition file for pinned Europe nested qualification
#==============================================================================
(((GC_BCs
* BC_  {boundary_file} SpeciesBC_?ADV? 2019/7/1/0-23 RFY xyz 1 * - 1 1
)))GC_BCs
"""

    block_re = re.compile(r"^\(\(\(GC_BCs\s*$.*?^\)\)\)GC_BCs\s*$", re.MULTILINE | re.DOTALL)
    if block_re.search(text):
        text = block_re.sub(bc_block.strip(), text, count=1)
    else:
        restart_end = ")))GC_RESTART"
        pos = text.find(restart_end)
        if pos < 0:
            raise RuntimeError("could not find GC_RESTART block for BC insertion")
        pos += len(restart_end)
        text = text[:pos] + "\n\n" + bc_block.strip() + text[pos:]

    hemco.write_text(text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hemco", required=True)
    ap.add_argument("--boundary-file", required=True)
    args = ap.parse_args()
    configure(Path(args.hemco), Path(args.boundary_file))


if __name__ == "__main__":
    main()
