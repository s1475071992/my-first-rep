#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def interval(seconds: int) -> str:
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if seconds <= 0:
        raise ValueError("seconds must be positive")
    return f"{days:08d} {hours:02d}{minutes:02d}{secs:02d}"


def patch_speciesconc(path: Path, seconds: int) -> None:
    value = interval(seconds)
    text = path.read_text()
    for key in ("frequency", "duration"):
        pattern = re.compile(rf"^(\s*SpeciesConc\.{key}:\s*).*$", re.MULTILINE)
        text, count = pattern.subn(rf"\g<1>{value}", text, count=1)
        if count != 1:
            raise RuntimeError(f"expected one SpeciesConc.{key} entry")
    path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("history")
    parser.add_argument("--seconds", type=int, required=True)
    args = parser.parse_args()
    patch_speciesconc(Path(args.history), args.seconds)


if __name__ == "__main__":
    main()
