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

echo "REFERENCE_INPUT_DOWNLOAD=PASS"
