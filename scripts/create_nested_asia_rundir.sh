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
RUNDIR="$RUNDIR_PARENT/gc_05x0625_AS_merra2_TransportTracers"
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
#   3 = 0.5 x 0.625
#   2 = Asia
#   1 = 72 levels
#   RUNDIR_PARENT = creation path
#   blank = official default run-directory name
#   n = do not download scientific inputs during creation
printf '7\n1\n3\n2\n1\n%s\n\nn\n' "$RUNDIR_PARENT" | ./createRunDir.sh > "$CREATE_LOG" 2>&1

if [[ ! -d "$RUNDIR" ]]; then
  echo "expected official Asia nested run directory was not created: $RUNDIR" >&2
  cat "$CREATE_LOG" >&2 || true
  exit 21
fi
cp "$CREATE_LOG" "$RUNDIR/createRunDir.log"

for f in geoschem_config.yml HEMCO_Config.rc HISTORY.rc species_database.yml download_data.py download_data.yml; do
  [[ -f "$RUNDIR/$f" ]] || { echo "missing run-directory file: $f" >&2; exit 22; }
done

# GCClassic 14.7.1 regionalizes the dedicated met-field include but the
# separate OCEAN_MASK constant in the main HEMCO config retains CN.$RES.$NC.
# Correct only that generated file path to the official Asia regional file.
python3 - "$RUNDIR/HEMCO_Config.rc" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text()
old = "1000 OCEAN_MASK  $METDIR/$CNYR/01/$MET.$CNYR0101.CN.$RES.$NC"
new = "1000 OCEAN_MASK  $METDIR/$CNYR/01/$MET.$CNYR0101.CN.$RES.AS.$NC"
count = text.count(old)
if count != 1:
    raise SystemExit(f"expected exactly one generated OCEAN_MASK path to patch, found {count}")
p.write_text(text.replace(old, new, 1))
PY

grep -q 'OCEAN_MASK.*CN\.\$RES\.AS\.\$NC' "$RUNDIR/HEMCO_Config.rc"

python3 "$CONTROL_ROOT/scripts/configure_reference_case.py" \
  --rundir "$RUNDIR" \
  --case-id GCNOOP_NESTED_AS_JJA_20190701_V1 \
  --start 20190701T000000 \
  --end 20190701T010000

# GCClassic 14.7.1 explicitly requires all nested restart reads to go through
# HEMCO.  configure_reference_case.py enables local REAL8 reads for GLOBAL
# bitwise qualification, so override that setting only for this nested case.
python3 - "$RUNDIR/geoschem_config.yml" <<'PY'
from pathlib import Path
import sys, yaml
p = Path(sys.argv[1])
x = yaml.safe_load(p.read_text())
x['simulation']['read_restart_as_real8'] = False
p.write_text(yaml.safe_dump(x, sort_keys=False))
PY

python3 "$CONTROL_ROOT/scripts/patch_history_for_window.py" \
  "$RUNDIR/HISTORY.rc" \
  --seconds 3600

python3 - "$RUNDIR/geoschem_config.yml" <<'PY'
import sys, yaml
x = yaml.safe_load(open(sys.argv[1]))
assert x['simulation']['name'] == 'TransportTracers'
assert str(x['simulation']['met_field']).upper() == 'MERRA2'
assert x['simulation']['read_restart_as_real8'] is False
assert str(x['grid']['resolution']) == '0.5x0.625'
assert x['grid']['number_of_levels'] == 72
assert x['grid']['longitude']['range'] == [60.0, 150.0]
assert x['grid']['latitude']['range'] == [-11.0, 55.0]
assert x['grid']['nested_grid_simulation']['activate'] is True
assert x['grid']['nested_grid_simulation']['buffer_zone_NSEW'] == [3, 3, 3, 3]
assert x['timesteps']['transport_timestep_in_s'] == 300
assert x['timesteps']['chemistry_timestep_in_s'] == 600
assert 'PassiveTracer' in x['operations']['transport']['transported_species']
PY

grep -q 'transport_timestep_in_s: 300' "$RUNDIR/geoschem_config.yml"
grep -q ' CYS ' "$RUNDIR/HEMCO_Config.rc"

cat > "$RUNDIR/NESTED_ASIA_CASE.txt" <<'EOF'
case_id=GCNOOP_NESTED_AS_JJA_20190701_V1
domain=Asia
domain_code=AS
grid=0.5x0.625
longitude_range=[60.0, 150.0]
latitude_range=[-11.0, 55.0]
met=MERRA2
transport_timestep_in_s=300
expected_transport_steps=12
boundary_conditions_required=true
restart_reader=HEMCO
missing_restart_species_policy=CYS
generated_config_ocean_mask_fix=CN.$RES.AS.$NC
EOF

echo "$RUNDIR"
