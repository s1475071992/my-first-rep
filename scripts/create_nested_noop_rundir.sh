#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 GCCLASSIC_DIR EXTDATA_DIR RUNDIR_PARENT" >&2
  exit 2
fi

CONTROL_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
GC_DIR=$(realpath "$1")
EXTDATA_DIR=$(realpath -m "$2")
RUNDIR_PARENT=$(realpath -m "$3")
SCI_DIR="$GC_DIR/src/GEOS-Chem"
CREATE_DIR="$SCI_DIR/run/GCClassic"
RUNDIR="$RUNDIR_PARENT/gc_05x0625_EU_merra2_TransportTracers"
CREATE_LOG="$RUNDIR_PARENT/createRunDir.log"

mkdir -p "$EXTDATA_DIR" "$RUNDIR_PARENT" "$HOME/.geoschem"
cat > "$HOME/.geoschem/config" <<EOF
export GC_DATA_ROOT=$EXTDATA_DIR
export GC_USER_REGISTERED=true
EOF
export GC_DATA_ROOT="$EXTDATA_DIR"
export GC_USER_REGISTERED=true

if [[ ! -x "$CREATE_DIR/createRunDir.sh" ]]; then
  echo "missing official createRunDir.sh at $CREATE_DIR" >&2
  exit 20
fi

rm -rf "$RUNDIR"
cd "$CREATE_DIR"

# Official GCClassic 14.7.1 prompt sequence:
#   7 = TransportTracers
#   1 = MERRA-2
#   3 = 0.5x0.625
#   3 = Europe
#   1 = 72 levels
#   RUNDIR_PARENT = creation path
#   blank = official default run-directory name
#   n = do not download scientific input data during creation
printf '7\n1\n3\n3\n1\n%s\n\nn\n' "$RUNDIR_PARENT" | ./createRunDir.sh > "$CREATE_LOG" 2>&1

if [[ ! -d "$RUNDIR" ]]; then
  echo "expected official Europe nested run directory was not created: $RUNDIR" >&2
  cat "$CREATE_LOG" >&2 || true
  exit 21
fi
cp "$CREATE_LOG" "$RUNDIR/createRunDir.log"

for f in geoschem_config.yml HEMCO_Config.rc HISTORY.rc species_database.yml download_data.py download_data.yml; do
  [[ -f "$RUNDIR/$f" ]] || { echo "missing run-directory file: $f" >&2; exit 22; }
done

python3 "$CONTROL_ROOT/scripts/configure_reference_case.py" \
  --rundir "$RUNDIR" \
  --case-id GCNOOP_NESTED_EU_JJA_20190701_V1 \
  --start 20190701T000000 \
  --end 20190701T010000

python3 "$CONTROL_ROOT/scripts/patch_history_for_window.py" \
  "$RUNDIR/HISTORY.rc" \
  --seconds 3600

python3 - "$RUNDIR/geoschem_config.yml" <<'PY'
import sys, yaml
p = sys.argv[1]
x = yaml.safe_load(open(p))
assert x['simulation']['name'] == 'TransportTracers'
assert str(x['simulation']['met_field']).upper() == 'MERRA2'
assert str(x['grid']['resolution']) == '0.5x0.625'
assert x['grid']['number_of_levels'] == 72
assert x['grid']['longitude']['range'] == [-30.0, 50.0]
assert x['grid']['latitude']['range'] == [30.0, 70.0]
assert x['grid']['nested_grid_simulation']['activate'] is True
assert x['grid']['nested_grid_simulation']['buffer_zone_NSEW'] == [3, 3, 3, 3]
assert x['timesteps']['transport_timestep_in_s'] == 300
assert x['timesteps']['chemistry_timestep_in_s'] == 600
assert 'PassiveTracer' in x['operations']['transport']['transported_species']
PY

grep -q 'transport_timestep_in_s: 300' "$RUNDIR/geoschem_config.yml"
grep -q ' CYS ' "$RUNDIR/HEMCO_Config.rc"
grep -q "COLLECTIONS: 'Restart'" "$RUNDIR/HISTORY.rc"
grep -q "'SpeciesConc'" "$RUNDIR/HISTORY.rc"

cat > "$RUNDIR/NESTED_NOOP_CASE.txt" <<'EOF'
case_id=GCNOOP_NESTED_EU_JJA_20190701_V1
domain=Europe
domain_code=EU
grid=0.5x0.625
met=MERRA2
transport_timestep_in_s=300
expected_transport_steps=12
boundary_conditions_required=true
missing_restart_species_policy=CYS
EOF

echo "$RUNDIR"
