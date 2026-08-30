#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 WORKROOT OUTPUT_DIR" >&2
  exit 2
fi

WORKROOT=$(realpath "$1")
OUTPUT_DIR=$(realpath -m "$2")
RUNDIR="$WORKROOT/rundirs/gc_4x5_merra2_TransportTracers"
GC_DIR="$WORKROOT/GCClassic"
PROV_DIR="$WORKROOT/provenance"
STAGE="$OUTPUT_DIR/stage"
BUNDLE_NAME="gc14-7-1-frozen-build.tar.gz"
BUNDLE="$OUTPUT_DIR/$BUNDLE_NAME"
MANIFEST="$OUTPUT_DIR/frozen_build_manifest.json"

for path in "$GC_DIR" "$PROV_DIR" "$RUNDIR"; do
  [[ -e "$path" ]] || { echo "missing frozen-build input: $path" >&2; exit 20; }
done
[[ -x "$RUNDIR/gcclassic" ]] || { echo "missing installed gcclassic executable" >&2; exit 21; }

rm -rf "$OUTPUT_DIR"
mkdir -p "$STAGE/rundirs"

# Keep the exact pinned source checkout so later provenance can verify the
# original Git identities without rebuilding.  Keep the installed run-directory
# template, but remove build/runtime products that do not define the executable.
cp -a "$GC_DIR" "$STAGE/GCClassic"
cp -a "$PROV_DIR" "$STAGE/provenance"
cp -a "$RUNDIR" "$STAGE/rundirs/"
rm -rf \
  "$STAGE/rundirs/gc_4x5_merra2_TransportTracers/build" \
  "$STAGE/rundirs/gc_4x5_merra2_TransportTracers/OutputDir" \
  "$STAGE/rundirs/gc_4x5_merra2_TransportTracers/Restarts"
rm -f \
  "$STAGE/rundirs/gc_4x5_merra2_TransportTracers/GC.log" \
  "$STAGE/rundirs/gc_4x5_merra2_TransportTracers/log.dryrun" \
  "$STAGE/rundirs/gc_4x5_merra2_TransportTracers/download_data_skip.log" \
  "$STAGE/rundirs/gc_4x5_merra2_TransportTracers/download_official_inputs.log" \
  "$STAGE/rundirs/gc_4x5_merra2_TransportTracers/log.dryrun.after_download"

GC_SHA=$(git -C "$GC_DIR" rev-parse HEAD)
GEOSCHEM_SHA=$(git -C "$GC_DIR/src/GEOS-Chem" rev-parse HEAD)
HEMCO_SHA=$(git -C "$GC_DIR/src/HEMCO" rev-parse HEAD)
EXE_SHA=$(sha256sum "$RUNDIR/gcclassic" | awk '{print $1}')
EXE_SIZE=$(stat -c '%s' "$RUNDIR/gcclassic")

GC_SHA="$GC_SHA" \
GEOSCHEM_SHA="$GEOSCHEM_SHA" \
HEMCO_SHA="$HEMCO_SHA" \
EXE_SHA="$EXE_SHA" \
EXE_SIZE="$EXE_SIZE" \
BUNDLE_NAME="$BUNDLE_NAME" \
python3 - "$MANIFEST" <<'PY'
import json
import os
import sys
from pathlib import Path

out = Path(sys.argv[1])
record = {
    "schema_version": 1,
    "build_run_id": int(os.environ.get("GITHUB_RUN_ID", "0")),
    "build_run_attempt": int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
    "control_repo_sha": os.environ.get("GITHUB_SHA"),
    "gcclassic_version": "14.7.1",
    "gcclassic_sha": os.environ["GC_SHA"],
    "geoschem_sha": os.environ["GEOSCHEM_SHA"],
    "hemco_sha": os.environ["HEMCO_SHA"],
    "bundle_filename": os.environ["BUNDLE_NAME"],
    "executable_relpath": "rundirs/gc_4x5_merra2_TransportTracers/gcclassic",
    "executable_sha256": os.environ["EXE_SHA"],
    "executable_size_bytes": int(os.environ["EXE_SIZE"]),
    "layout_root": "/tmp/gc14-reference",
}
out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
PY

cp "$MANIFEST" "$STAGE/frozen_build_manifest.json"
tar -C "$STAGE" -czf "$BUNDLE" .
sha256sum "$BUNDLE" | tee "$BUNDLE.sha256"

# The outer artifact contains only immutable build evidence and the bundle.
rm -rf "$STAGE"
cat "$MANIFEST"
