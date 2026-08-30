#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 WORKDIR" >&2
  exit 2
fi

WORKDIR=$(realpath -m "$1")
GC_DIR="$WORKDIR/GCClassic"
PROV_DIR="$WORKDIR/provenance"
WRAPPER_SHA_EXPECTED="c36ecd760c6663a62769f05a7449c927b8faf54b"
SCIENCE_SHA_EXPECTED="b9f570e2c7a98b308004cd07e2985a12a47b6f5c"

mkdir -p "$WORKDIR" "$PROV_DIR"
rm -rf "$GC_DIR"

git clone \
  --branch 14.7.1 \
  --depth 1 \
  --recurse-submodules \
  --shallow-submodules \
  https://github.com/geoschem/GCClassic.git \
  "$GC_DIR"

git -C "$GC_DIR" submodule update --init --recursive

wrapper_sha=$(git -C "$GC_DIR" rev-parse HEAD)
science_sha=$(git -C "$GC_DIR/src/GEOS-Chem" rev-parse HEAD)

if [[ "$wrapper_sha" != "$WRAPPER_SHA_EXPECTED" ]]; then
  echo "GCClassic wrapper SHA mismatch: $wrapper_sha" >&2
  exit 10
fi
if [[ "$science_sha" != "$SCIENCE_SHA_EXPECTED" ]]; then
  echo "GEOS-Chem science SHA mismatch: $science_sha" >&2
  exit 11
fi

{
  echo "GCClassic_tag=14.7.1"
  echo "GCClassic_sha=$wrapper_sha"
  echo "GEOSChem_sha=$science_sha"
} > "$PROV_DIR/source_identity.txt"

git -C "$GC_DIR" submodule status --recursive > "$PROV_DIR/submodules.txt"
git --version > "$PROV_DIR/toolchain.txt"
gfortran --version | head -n 1 >> "$PROV_DIR/toolchain.txt"
cmake --version | head -n 1 >> "$PROV_DIR/toolchain.txt"
if command -v nc-config >/dev/null 2>&1; then nc-config --version >> "$PROV_DIR/toolchain.txt"; fi
if command -v nf-config >/dev/null 2>&1; then nf-config --version >> "$PROV_DIR/toolchain.txt"; fi

echo "$GC_DIR"
