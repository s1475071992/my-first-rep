#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 GCCLASSIC_DIR EXTDATA_DIR RUNDIR_PARENT" >&2
  exit 2
fi

GC_DIR=$(realpath "$1")
EXTDATA_DIR=$(realpath -m "$2")
RUNDIR_PARENT=$(realpath -m "$3")
SCI_DIR="$GC_DIR/src/GEOS-Chem"
CREATE_DIR="$SCI_DIR/run/GCClassic"
RUNDIR="$RUNDIR_PARENT/gc_4x5_merra2_TransportTracers"

mkdir -p "$EXTDATA_DIR" "$RUNDIR_PARENT" "$HOME/.geoschem"
cat > "$HOME/.geoschem/config" <<EOF
export GC_DATA_ROOT=$EXTDATA_DIR
export GC_USER_REGISTERED=true
EOF
export GC_DATA_ROOT="$EXTDATA_DIR"
export GC_USER_REGISTERED=true

if [[ ! -x "$CREATE_DIR/createRunDir.sh" ]]; then
  echo "missing createRunDir.sh at $CREATE_DIR" >&2
  exit 20
fi

rm -rf "$RUNDIR"
cd "$CREATE_DIR"

# Exact prompt sequence used by the upstream 14.7.1 integration test for
# 4x5 MERRA-2 / 72L / TransportTracers.  The final 'n' declines optional
# post-creation data download; official inputs are obtained only after dry-run.
printf '7\n1\n1\n1\n%s\n\nn\n' "$RUNDIR_PARENT" | ./createRunDir.sh

if [[ ! -d "$RUNDIR" ]]; then
  echo "expected run directory was not created: $RUNDIR" >&2
  exit 21
fi

for f in geoschem_config.yml HEMCO_Config.rc HISTORY.rc download_data.py download_data.yml; do
  [[ -f "$RUNDIR/$f" ]] || { echo "missing run-directory file: $f" >&2; exit 22; }
done

# Enforce the intended external-audit configuration.  The upstream template
# already has TransportTracers/TPCORE active; these checks guard against prompt
# drift without editing numerical source.
grep -q 'name: TransportTracers' "$RUNDIR/geoschem_config.yml"
grep -q 'resolution: 4.0x5.0' "$RUNDIR/geoschem_config.yml"
grep -q 'number_of_levels: 72' "$RUNDIR/geoschem_config.yml"
grep -q 'PassiveTracer' "$RUNDIR/geoschem_config.yml"

# createRunDir defaults to a one-hour integration-test-style interval in this
# release. Preserve the generated values and record them rather than silently
# rewriting them.
grep -E 'start_date:|end_date:|transport_timestep_in_s:' "$RUNDIR/geoschem_config.yml" > "$RUNDIR/REFERENCE_TIME_WINDOW.txt"

echo "$RUNDIR"
