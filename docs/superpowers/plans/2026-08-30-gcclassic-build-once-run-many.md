# GCClassic Build-Once / Run-Many Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile pinned GCClassic 14.7.1 once, freeze the executable/source provenance as an immutable artifact, and make all later reference runs reuse that exact build without CMake or Make.

**Architecture:** A dedicated build workflow produces a tarred frozen runtime/source bundle. The reference workflow reads a committed build pin, downloads the exact cross-run artifact, verifies SHA256, extracts it to the deterministic workroot, and performs runtime-only configuration and validation.

**Tech Stack:** GitHub Actions, Bash, Python 3.11, GCClassic 14.7.1, CMake/Make only in the build workflow, SHA256 provenance.

**Spec:** `docs/superpowers/specs/2026-08-30-gcclassic-build-once-run-many-design.md`

## Global Constraints

- GCClassic tag `14.7.1`; wrapper SHA `c36ecd760c6663a62769f05a7449c927b8faf54b`.
- GEOS-Chem SHA `b9f570e2c7a98b308004cd07e2985a12a47b6f5c`.
- Reference runs must not invoke `cmake`, `make`, `bootstrap_gcclassic.sh`, or `create_transporttracers_rundir.sh`.
- Runtime HEMCO/HISTORY/time/season/region configuration remains mutable without rebuilding.
- TPCORE and transport numerical source remain untouched.
- Reference runs verify a committed build run id and bundle SHA256 before execution.

---

### Task 1: Frozen build packaging

**Files:**
- Create: `scripts/package_frozen_gcclassic_build.sh`
- Create: `.github/workflows/gc14-build.yml`
- Modify: `tests/test_reference_producer_contract.py`

**Interfaces:**
- Consumes: `/tmp/gc14-reference/GCClassic`, `/tmp/gc14-reference/provenance`, and compiled `/tmp/gc14-reference/rundirs/gc_4x5_merra2_TransportTracers`.
- Produces: `frozen-build/gc14-7-1-frozen-build.tar.gz`, its `.sha256`, and `frozen_build_manifest.json`.

- [ ] **Step 1: Add a contract test for build/run separation**

Assert that `gc14-build.yml` contains bootstrap/CMake/Make/upload-artifact, while `gc14-reference-producer.yml` will ultimately contain none of bootstrap/CMake/Make.

- [ ] **Step 2: Verify the new contract fails before the workflow split**

Run `python -m pytest -q tests/test_reference_producer_contract.py`; expected failure is that the reference workflow still contains build commands or the build workflow does not yet exist.

- [ ] **Step 3: Add the frozen-build packaging script**

The script must check the installed executable exists, copy the pinned source tree/provenance/run-directory template into a staging directory, remove runtime/build outputs, compute the executable SHA256, create a manifest, create the tarball, and emit the tarball SHA256.

- [ ] **Step 4: Add `gc14-build.yml`**

The workflow installs build dependencies, runs the existing pinned bootstrap and run-directory creation scripts, compiles/installs once, packages the frozen bundle, and uploads artifact `gc14-7-1-frozen-build-${{ github.run_id }}` with 90-day retention.

- [ ] **Step 5: Run the build workflow and inspect the artifact**

Acceptance: build job success, artifact exists, tarball SHA256 file verifies, manifest reports the pinned source SHAs and executable digest.

### Task 2: Explicit frozen-build pin

**Files:**
- Create: `config/frozen_gcclassic_build.json`
- Modify: `tests/test_reference_producer_contract.py`

**Interfaces:**
- Consumes: successful build run id, artifact name, tarball digest, executable digest.
- Produces: one committed immutable pointer used by all run-many jobs.

- [ ] **Step 1: Add tests for the pin schema**

Require positive integer `build_run_id`, artifact name `gc14-7-1-frozen-build-<run_id>`, `bundle_filename`, 64-hex bundle/executable SHA256, GCClassic version `14.7.1`, and the frozen wrapper/science SHAs.

- [ ] **Step 2: Verify the pin test fails while no pin exists**

Run the contract test; expected failure is missing `config/frozen_gcclassic_build.json`.

- [ ] **Step 3: Download the successful build artifact and verify its manifest/digests**

Use the artifact contents, not guessed values, to populate the pin.

- [ ] **Step 4: Commit the exact pin**

No `latest` lookup or branch-based artifact selection is allowed.

### Task 3: Convert reference producer to run-only

**Files:**
- Modify: `.github/workflows/gc14-reference-producer.yml`
- Modify: `tests/test_reference_producer_contract.py`

**Interfaces:**
- Consumes: `config/frozen_gcclassic_build.json` and the exact build artifact.
- Produces: the existing JJA reference evidence using the frozen executable.

- [ ] **Step 1: Add a failing contract for run-only workflow behavior**

Assert the reference workflow uses `actions/download-artifact@v4`, a `run-id` from the pin, SHA256 verification, and has no bootstrap/CMake/Make/run-directory-creation commands.

- [ ] **Step 2: Replace build steps with frozen artifact restore**

Read the JSON pin into GitHub step outputs, download artifact from that `build_run_id`, run `sha256sum -c`, extract into `/tmp/gc14-reference`, recreate the `.geoschem` runtime data-root config, and verify the executable SHA256 against the pin.

- [ ] **Step 3: Keep runtime-only configuration and validation unchanged**

Continue applying `configure_reference_case.py`, `patch_history_for_window.py`, dry-run/input download, 1-hour GCClassic execution, PassiveTracer validation, provenance, and holdout packaging.

- [ ] **Step 4: Record frozen-build identity in success/failure evidence**

Copy the committed pin and frozen build manifest into evidence; include `HEMCO_Config.rc` in failure diagnostics.

- [ ] **Step 5: Run contract tests**

Expected: all contract tests pass.

### Task 4: End-to-end run-many verification

**Files:**
- No scientific-source changes.

**Interfaces:**
- Consumes: frozen build pin and runtime-only JJA configuration.
- Produces: a successful JJA 2019-07-01 1-hour reference artifact generated without recompilation.

- [ ] **Step 1: Confirm no other workflow run is active before triggering**

Check for `queued`, `in_progress`, `waiting`, or `requested` states on the branch.

- [ ] **Step 2: Trigger the reference workflow by its workflow-file/pin commit**

The job list must not contain bootstrap, configure-CMake, compile, or install steps.

- [ ] **Step 3: Verify runtime success**

Require the one-hour GCClassic step, PassiveTracer validation, provenance/package, and success artifact upload all succeed.

- [ ] **Step 4: Verify frozen executable identity**

The runtime evidence executable SHA256 must equal `config/frozen_gcclassic_build.json` and the frozen build manifest.

- [ ] **Step 5: Verify no numerical-source changes**

Compare the implementation range against the pre-split commit and confirm changes are limited to workflows, control scripts/tests/docs/config pin.
