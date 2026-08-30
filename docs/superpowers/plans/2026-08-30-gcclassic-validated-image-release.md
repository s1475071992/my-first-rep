# GCClassic Validated Image Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a reusable GCClassic 14.7.1 OCI image only after the exact candidate image passes the complete four-season/five-region reference-producer gate.

**Architecture:** Reuse the pinned frozen build artifact without recompilation, assemble it into a local Ubuntu 24.04 candidate image, run all four global seasonal cases inside that image, validate five frozen latitude regions for each pre/post pair, aggregate 20 acceptance cells, and only then push the unchanged candidate image to GHCR. Publication records the immutable digest and frozen source/binary identities.

**Tech Stack:** GitHub Actions, Docker/OCI, GHCR, Python 3, NumPy, netCDF4, GCClassic 14.7.1, MERRA2 TransportTracers.

**Spec:** `docs/superpowers/specs/2026-08-30-gcclassic-validated-image-release-design.md`

## Global Constraints

- Do not modify GCClassic/TPCORE numerical source.
- Do not modify the frozen season matrix, holdout regions, transport timestep, or scientific thresholds.
- Reuse frozen executable SHA256 `0ca0d46b3fc2809285f270ca817adfbb7d02ff97099a7546bf08649736e22696` unless the explicit frozen-build pin is intentionally replaced.
- No GHCR push occurs before the 4-season / 5-region / 20-cell release gate passes.
- No image rebuild occurs between full-matrix validation and `docker push`.

---

### Task 1: Freeze publication-order contract

**Files:**
- Modify: `tests/test_reference_producer_contract.py`

**Interfaces:**
- Consumes: frozen matrix and current build pin.
- Produces: tests requiring candidate-build -> full-matrix -> release-gate -> GHCR login -> push ordering.

- [ ] Add required-file checks for the Dockerfile and full-matrix scripts.
- [ ] Add a workflow-order test proving `docker push` is absent before the full release gate.
- [ ] Add a pure-Python matrix-validator test requiring exactly four seasons and twenty region cells.
- [ ] Run `python -m pytest -q` and verify the new tests fail before implementation.

### Task 2: Add reference-pair and matrix acceptance

**Files:**
- Create: `scripts/validate_reference_pair.py`
- Create: `scripts/validate_reference_matrix.py`

**Interfaces:**
- `validate_reference_pair.py` consumes initial/final restart files, frozen matrix, case ID, and executable SHA256; produces `pair_acceptance.json`.
- `validate_reference_matrix.py` consumes all case acceptance records; produces `matrix_acceptance.json` with 4 cases and 20 region cells.

- [ ] Validate finite PassiveTracer and positive finite `Met_DELPDRY` / `AREA`.
- [ ] Compute dry-air mass from `DELPDRY * area / g` and record dry-air-weighted PassiveTracer metrics per frozen region.
- [ ] Do not introduce a numerical Torch-vs-GC threshold.
- [ ] Require all four seasons and five regions in the aggregate gate.

### Task 3: Add full-matrix runner

**Files:**
- Create: `scripts/run_reference_matrix.py`

**Interfaces:**
- Consumes: frozen TransportTracers template, matrix JSON, expected executable SHA256.
- Produces: four pre/post pair evidence directories plus aggregate matrix acceptance.

- [ ] Copy the frozen run template independently for each seasonal case.
- [ ] Apply existing HEMCO/HISTORY runtime-only patches.
- [ ] Dry-run and download only official inputs.
- [ ] Save the initial restart before runtime and final restart after one hour.
- [ ] Require clean GCClassic termination and invoke pair validation.
- [ ] Aggregate all four cases into the 20-cell release gate.

### Task 4: Build local candidate image and gate publication

**Files:**
- Create: `docker/gc14-reference/Dockerfile`
- Modify: `.github/workflows/gc14-reference-producer.yml`

**Interfaces:**
- Consumes: pinned frozen build artifact and current control scripts.
- Produces: validated GHCR image plus publication manifest.

- [ ] Download and SHA256-verify the exact frozen build artifact.
- [ ] Build a local candidate image without pushing it.
- [ ] Verify the executable SHA256 inside the image.
- [ ] Run the entire seasonal matrix inside that exact candidate image.
- [ ] Upload pre-publication matrix evidence.
- [ ] Only after PASS, authenticate to GHCR.
- [ ] Tag and push the already-tested local image without rebuilding.
- [ ] Record the immutable OCI digest and all provenance identities.

### Task 5: End-to-end verification

**Files:**
- Verify all files from Tasks 1-4.

**Interfaces:**
- Produces: one GitHub Actions run showing contract PASS, four seasonal runtime PASS records, 20 regional acceptance cells, and a publication manifest containing the GHCR digest.

- [ ] Confirm no other Actions run is active before triggering.
- [ ] Run the workflow from the feature branch.
- [ ] If any seasonal or regional case fails, preserve failure evidence and do not publish.
- [ ] If all gates pass, verify GHCR publication occurs after the matrix evidence upload and record the immutable digest.
