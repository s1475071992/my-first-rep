# GCClassic 14.7.1 External Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible GitHub Actions reference producer that remotely compiles pinned GCClassic 14.7.1, generates official dry-run input manifests and, when official inputs are downloadable, executes TransportTracers/PassiveTracer runs for realistic-corpus expansion, cross-weather/season/region generalization, and an independent GEOS-Chem holdout discrepancy audit.

**Architecture:** The user-owned execution-control repo contains only CI, scripts, tests, provenance and small manifests. GitHub-hosted runners clone the official pinned upstream source, install build dependencies, create global 4x5 MERRA-2 TransportTracers run directories, compile GCClassic, dry-run to enumerate official input files, optionally download those inputs, execute the model, validate outputs, and upload artifacts. GEOS-Chem remains external validation only; Paper-1 neural labels remain the internal same-family HF Torch reference.

**Tech Stack:** GitHub Actions, Bash, Python 3, pytest, GCClassic 14.7.1, GEOS-Chem 14.7.1, gfortran, netCDF-C/netCDF-Fortran.

**Spec:** `docs/GC14_7_1_REFERENCE_PRODUCER_V1_DESIGN.md`

## Global Constraints

- GCClassic wrapper ref is exactly `14.7.1`.
- Numerical upstream source is never edited.
- Allowed instrumentation is configuration/diagnostic-only and must be recorded.
- Primary first run is global 4x5 MERRA-2, 72 levels, TransportTracers, PassiveTracer available.
- GEOS-Chem is not a training label and does not change the frozen A-prime training route.
- All outputs carry source refs, submodule SHAs, config hashes, input manifest hashes, runner environment and checksums.
- Failures are classified as CONNECTOR_BLOCKED, REMOTE_BUILD_FAILURE, REFERENCE_INPUT_FAILURE or REFERENCE_RUNTIME_FAILURE.

---

### Task 1: CI contract and remote-runner proof

**Files:**
- Create: `.github/workflows/gc14-reference-producer.yml`
- Create: `tests/test_reference_producer_contract.py`

**Interfaces:**
- Consumes: branch `gc14-7-1-reference-producer-v1`.
- Produces: remote pytest job proving GitHub Actions execution and enforcing required control-plane files.

- [ ] Write contract tests requiring bootstrap, run-dir, manifest-validation and provenance scripts.
- [ ] Push the test before the scripts exist and verify the GitHub Actions job fails for the expected missing-file assertion.
- [ ] Add the required scripts in Task 2 and verify the same test becomes green.

### Task 2: Pinned GCClassic bootstrap and build

**Files:**
- Create: `scripts/bootstrap_gcclassic.sh`
- Create: `scripts/create_transporttracers_rundir.sh`
- Create: `scripts/validate_dryrun.py`
- Create: `scripts/write_provenance.py`

**Interfaces:**
- `bootstrap_gcclassic.sh <workdir>` clones GCClassic tag 14.7.1 recursively, records commits/submodules, installs/builds compile dependencies supplied by workflow.
- `create_transporttracers_rundir.sh <gcclassic-dir> <extdata-dir> <rundir-parent>` creates a deterministic global 4x5 MERRA-2/72L TransportTracers run directory and writes a one-hour configuration.
- `validate_dryrun.py <rundir>` validates dry-run file lists and writes JSON summary.
- `write_provenance.py` records environment, source SHAs and file hashes.

- [ ] Implement scripts minimally to satisfy contract tests.
- [ ] Run compile-only upstream integration test on GitHub Actions.
- [ ] Verify `nf-config` exists and submodule SHAs are recorded.

### Task 3: Official input-manifest dry run

**Files:**
- Modify: `.github/workflows/gc14-reference-producer.yml`
- Create: `scripts/run_gc_dryrun.sh`

**Interfaces:**
- Produces: `reference_dryrun_artifact/` with dry-run log, `download_data.yml`, generated data list, run configuration, build logs and provenance.

- [ ] Configure one-hour global 4x5 MERRA-2 TransportTracers.
- [ ] Run `gcclassic --dryrun` without silently substituting inputs.
- [ ] Validate requested files, URLs/paths and timestamps.
- [ ] Upload the dry-run artifact.

### Task 4: Official-input execution path

**Files:**
- Create: `scripts/download_official_inputs.sh`
- Create: `scripts/run_reference_case.sh`
- Create: `scripts/validate_reference_outputs.py`

**Interfaces:**
- Downloads only files enumerated by the frozen dry-run manifest.
- Produces validated NetCDF/reference outputs plus run logs/checksums.

- [ ] Download official inputs and verify nonzero files/checksums.
- [ ] Execute the one-hour TransportTracers case.
- [ ] Validate expected output variables/dimensions/timestamps/finite values.
- [ ] Upload reference artifact or classify a precise REFERENCE_INPUT_FAILURE/REFERENCE_RUNTIME_FAILURE.

### Task 5: Corpus/generalization matrix

**Files:**
- Create: `config/reference_matrix.json`
- Create: `scripts/build_reference_matrix.py`

**Interfaces:**
- Defines frozen holdout combinations by season/time and later regional domains without entering neural training labels.

- [ ] Freeze at least four seasonal windows for global 4x5 MERRA-2 if available.
- [ ] Add regional matrix entries only where official nested input/BC manifests are resolvable.
- [ ] Keep state-level splits grouped by meteorological time/domain.

### Task 6: GEOS-Chem holdout discrepancy audit packaging

**Files:**
- Create: `scripts/package_gc_holdout.py`
- Create: `docs/GC_DISCREPANCY_AUDIT_PROTOCOL_V1.md`

**Interfaces:**
- Packages GEOS-Chem outputs as external holdout evidence only.
- Never feeds them into the neural-training loss.

- [ ] Record q/state/met/dry-mass/timestamp/grid provenance available from outputs.
- [ ] Produce audit manifest and checksums.
- [ ] State L5 numerical equivalence NOT CLAIMED.

### Task 7: Verification and release

**Files:**
- Create: `docs/GC14_7_1_REFERENCE_PRODUCER_STATUS_V1.md`

- [ ] Run repository pytest in GitHub Actions.
- [ ] Verify build/dry-run/reference jobs and inspect logs.
- [ ] Download produced workflow artifacts through the connector.
- [ ] Record exact final status and any input/runtime blocker without conflating it with Torch Teacher status.
