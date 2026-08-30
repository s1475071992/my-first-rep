# GC14 Paper 1 Unified Checkpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish one immutable reusable checkpoint image from a single workflow run that produces complete GLOBAL transport diagnostics, GLOBAL BoundaryConditions, complete Europe NESTED transport diagnostics, qualification evidence, and the exact reusable completed working state.

**Architecture:** Bootstrap exact GCClassic 14.7.1 source, apply a deterministic diagnostic-only source patch, build a distinct instrumented executable, qualify it against the canonical executable with A/B/C exact output comparisons, then run GLOBAL→BC→NESTED in one ordered workflow. The Fortran hook captures source-native arrays into lossless stream files only after transport-stage buffering; Python packs those files into formal NetCDF without unit conversion. The final checkpoint image is built from an immutable diagnostic-producer parent and `/checkpoint`, then pushed only after all scientific, lineage, schema, and provenance gates pass.

**Tech Stack:** Fortran 2008/GFortran, GCClassic 14.7.1, GEOS-Chem SHA `b9f570e2c7a98b308004cd07e2985a12a47b6f5c`, Python 3.11, NumPy, netCDF4, pytest, Docker/OCI, GitHub Actions, GHCR.

**Specs:** `GC14_7_1_TRANSPORT_DIAGNOSTIC_HOOK_SPEC_V1`, `GC14_7_1_TRANSPORTTRACERS_BC_NESTED_QUALIFICATION_V1.md`, `GC14_7_1_PAPER1_CHECKPOINT_IMAGE_SPEC_V1`.

## Global Constraints

- GCClassic source SHA: `c36ecd760c6663a62769f05a7449c927b8faf54b`.
- GEOS-Chem source SHA: `b9f570e2c7a98b308004cd07e2985a12a47b6f5c`.
- HEMCO SHA: `07da3c29fd85abc3824cb6288578b0b68c2395a3`.
- Canonical executable SHA256: `0ca0d46b3fc2809285f270ca817adfbb7d02ff97099a7546bf08649736e22696`.
- GLOBAL grid/cadence: MERRA2 4x5, 72L, 600 s transport timestep.
- NESTED grid/cadence: Europe MERRA2 0.5x0.625, 72L, 300 s transport timestep.
- PassiveTracer internal transport q unit: kg species / kg dry air.
- XMASS/YMASS native unit: hPa per dynamic timestep.
- GLOBAL vertical forcing: native WZ hPa per dynamic timestep.
- NESTED vertical forcing: pressure-remap `pe/ps/Ap/Bp`; no fabricated WZ.
- No TPCORE/PJC arithmetic, timestep, fill/negative treatment, scientific threshold, or algorithm changes.
- All GitHub writes/triggers require `in_progress=0` and `queued=0` first.
- Publication is fail-closed; no GHCR push before every qualification gate passes.

---

### Task 1: Diagnostic Patch Contract and Source Patcher

**Files:**
- Create: `scripts/apply_transport_audit_patch.py`
- Create: `tests/test_transport_audit_patch_contract.py`

**Interfaces:**
- Consumes: exact pinned GEOS-Chem source tree.
- Produces: `GeosCore/transport_audit_mod.F90` plus exact-anchor edits in `transport_mod.F90`, `tpcore_fvdas_mod.F90`, `tpcore_window_mod.F90`, and `GeosCore/CMakeLists.txt`.

- [ ] Write failing tests that require all four hook stages, exact source anchors, source-unit checks, PassiveTracer lookup by name, audit-disabled no-op path, and no numerical-expression edits.
- [ ] Run pytest and verify RED.
- [ ] Implement deterministic patcher and generated Fortran module.
- [ ] Run pytest and verify GREEN.

### Task 2: Raw-to-NetCDF Packer and Schema Validator

**Files:**
- Create: `scripts/pack_transport_audit.py`
- Create: `scripts/validate_transport_audit.py`
- Create: `tests/test_transport_audit_packer.py`

**Interfaces:**
- Consumes: per-step source-native stream files and metadata.
- Produces: `transport_audit.nc4`, `transport_audit_manifest.json`, SHA256 evidence.

- [ ] Write synthetic failing tests for host/TPCORE vertical orientation, GLOBAL WZ schema, NESTED `pe/ps` schema, step completeness, dtype preservation, dt sequences, and no hidden unit conversion.
- [ ] Verify RED.
- [ ] Implement packer/validator.
- [ ] Verify GREEN.

### Task 3: Instrumented Build and A/B/C No-Op Qualification

**Files:**
- Create: `.github/workflows/gc14-transport-audit-build.yml`
- Create: `config/transport_audit_qualification.json`
- Create: `scripts/compare_gc_scientific_outputs.py`
- Create: `tests/test_transport_audit_workflow_contract.py`

**Interfaces:**
- A: canonical frozen executable.
- B: instrumented executable with audit disabled.
- C: same instrumented executable with audit enabled.
- Produces: distinct instrumented build artifact, executable SHA, patch SHA, global and nested no-op qualification manifests.

- [ ] Write workflow contract tests first.
- [ ] Build exact pinned source + diagnostic patch with same Release/OMP=n lineage.
- [ ] Run GLOBAL A/B/C and require exact equality of common scientific arrays.
- [ ] Run NESTED A/B/C using qualified BC chain and require exact equality of common scientific arrays.
- [ ] Require B vs C exact equality and validate diagnostic NetCDF schemas.
- [ ] Freeze instrumented executable/build manifest only after both domain paths PASS.

### Task 4: Unified GLOBAL→BC→NESTED Producer

**Files:**
- Create: `config/paper1_checkpoint_case.json`
- Create: `scripts/run_paper1_checkpoint.py`
- Create: `scripts/assemble_checkpoint.py`
- Create: `tests/test_checkpoint_contract.py`

**Interfaces:**
- Consumes: qualified instrumented build.
- Produces: GLOBAL audit dataset, 3-hour BoundaryConditions, NESTED audit dataset, unified qualification and provenance.

- [ ] Write failing contract tests for 6 GLOBAL steps, 12 NESTED steps, runtime dt assertions, same-run BC SHA lineage, and required manifests.
- [ ] Implement ordered producer.
- [ ] Require `SHA256(global-produced-BC) == SHA256(nested-consumed-BC)`.
- [ ] Validate both datasets and manifests.

### Task 5: Reusable Checkpoint OCI Image

**Files:**
- Create: `docker/gc14-checkpoint/Dockerfile`
- Create: `.github/workflows/gc14-paper1-checkpoint.yml`
- Create: `scripts/validate_checkpoint.py`

**Interfaces:**
- Consumes: complete `/checkpoint` tree and immutable diagnostic producer image/build identity.
- Produces: `ghcr.io/s1475071992/gcclassic-paper1-checkpoint:14.7.1-global-nested-v1-run-<RUN_ID>` and immutable digest.

- [ ] Write failing publication-contract tests.
- [ ] Build checkpoint image locally only after all scientific gates pass.
- [ ] Verify executable/data/provenance hashes inside the candidate image.
- [ ] Login to GHCR only after validation.
- [ ] Push exact validated candidate without rebuild.
- [ ] Resolve immutable digest and write publication manifest.

### Task 6: Final Verification and Freeze Record

**Files:**
- Create: `GC14_7_1_PAPER1_CHECKPOINT_IMAGE_V1.md`

- [ ] Run complete contract test suite.
- [ ] Verify latest workflow conclusion is success.
- [ ] Verify no queued/in-progress branch runs remain.
- [ ] Verify publication manifest, checkpoint digest, parent lineage, BC lineage, GLOBAL/NESTED step counts, and scientific-threshold flag.
- [ ] Record final immutable image reference and evidence artifact IDs.
