#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 RUNDIR [PORTAL]" >&2
  exit 2
fi

RUNDIR=$(realpath "$1")
PORTAL=${2:-geoschem+aws}
cd "$RUNDIR"

test -f log.dryrun || { echo "REFERENCE_INPUT_FAILURE: missing log.dryrun" >&2; exit 20; }
test -x ./download_data.py || chmod +x ./download_data.py

case "$PORTAL" in
  geoschem+aws|geoschem+http|nested+aws|nested+http|rochester) ;;
  *) echo "REFERENCE_INPUT_FAILURE: unsupported portal $PORTAL" >&2; exit 21 ;;
esac

if [[ "$PORTAL" == *+aws ]]; then
  command -v aws >/dev/null || { echo "REFERENCE_INPUT_FAILURE: aws CLI missing" >&2; exit 22; }
fi

# Authoritative downloader from the pinned run directory.  It reads the dry-run
# manifest and only fetches files declared by GCClassic itself.
set +e
./download_data.py log.dryrun "$PORTAL" 2>&1 | tee download_official_inputs.log
rc=${PIPESTATUS[0]}
set -e
if [[ $rc -ne 0 ]]; then
  echo "REFERENCE_INPUT_FAILURE: download_data.py exited $rc" >&2
  exit $rc
fi

# Re-run dryrun after the download. Any remaining FILE NOT FOUND entry means the
# scientific input set is incomplete and must not proceed to runtime.
./gcclassic --dryrun 2>&1 | tee log.dryrun.after_download
if grep -qi "FILE NOT FOUND" log.dryrun.after_download; then
  echo "REFERENCE_INPUT_FAILURE: dry-run still reports missing files" >&2
  grep -i "FILE NOT FOUND" log.dryrun.after_download >&2 || true
  exit 23
fi

# A/B/C no-op qualification downloads official inputs only once in sibling A.
# ExtData is shared globally, but the initial GEOS-Chem Restart is local to each
# run directory.  When this helper is invoked for an A directory with sibling
# B and C directories already present, copy only the local initial Restart set
# to both siblings and require byte-identical SHA256 values.  OutputDir is never
# copied, so each executable still produces an independent scientific result.
PARENT=$(dirname "$RUNDIR")
if [[ "$(basename "$RUNDIR")" == "A" && -d "$PARENT/B" && -d "$PARENT/C" ]]; then
  mapfile -t restarts < <(find "$RUNDIR/Restarts" -maxdepth 1 -type f -name 'GEOSChem.Restart.*.nc4' | sort)
  if [[ ${#restarts[@]} -lt 1 ]]; then
    echo "REFERENCE_INPUT_FAILURE: no local GEOSChem.Restart.*.nc4 found for sibling sync" >&2
    exit 24
  fi

  for peer in B C; do
    rm -rf "$PARENT/$peer/Restarts"
    mkdir -p "$PARENT/$peer/Restarts"
    cp -a "$RUNDIR/Restarts/." "$PARENT/$peer/Restarts/"
  done

  for src in "${restarts[@]}"; do
    name=$(basename "$src")
    source_sha=$(sha256sum "$src" | awk '{print $1}')
    for peer in B C; do
      dst="$PARENT/$peer/Restarts/$name"
      test -f "$dst" || { echo "REFERENCE_INPUT_FAILURE: missing sibling restart $dst" >&2; exit 25; }
      peer_sha=$(sha256sum "$dst" | awk '{print $1}')
      if [[ "$peer_sha" != "$source_sha" ]]; then
        echo "REFERENCE_INPUT_FAILURE: sibling restart SHA256 mismatch for $peer/$name" >&2
        exit 26
      fi
    done
  done
  echo "REFERENCE_INPUT_SIBLING_RESTART_SYNC=PASS"
fi

echo "REFERENCE_INPUT_DOWNLOAD=PASS"
