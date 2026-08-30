# GC_DISCREPANCY_AUDIT_PROTOCOL_V1

## Status

`FROZEN_BEFORE_FORMAL_EXTERNAL_SCORING`

## Scientific role

GEOS-Chem Classic is an **independent external behavior reference** for Paper 1. It is not a neural training label and it is not used in the loss. The primary training reference remains the independently-qualified same-family Torch high-fidelity reference.

No claim of GEOS-Chem/TPCORE L5 forward numerical equivalence is made.

## Pinned software

- GCClassic wrapper tag: `14.7.1`
- GCClassic release commit: `c36ecd760c6663a62769f05a7449c927b8faf54b`
- GEOS-Chem science commit: `b9f570e2c7a98b308004cd07e2985a12a47b6f5c`
- Simulation: `TransportTracers`
- Primary tracer: `PassiveTracer`
- Global grid: `4x5`, 72 levels
- Meteorology: MERRA-2

## Process isolation

The external reference cases disable chemistry, convection, dry deposition, wet deposition, and PBL mixing. GCClassic TPCORE transport remains enabled. This prevents the external discrepancy score from silently mixing unrelated process differences into an advection-only comparison.

The official numerical source is not patched. Control-repository changes are limited to run configuration, evidence collection, validation, and provenance.

## Frozen seasonal matrix

The four one-hour cases are frozen in `config/reference_matrix.json` before formal scoring:

- DJF: 2019-01-01 00:00 UTC
- MAM: 2019-04-01 00:00 UTC
- JJA: 2019-07-01 00:00 UTC
- SON: 2019-10-01 00:00 UTC

## Frozen regional scoring masks

External results are reported separately for:

1. TROPICS: 23.5S–23.5N
2. NH_MIDLAT: 30–60N
3. SH_MIDLAT: 60–30S
4. ARCTIC: 66.5–90N
5. ANTARCTIC: 90–66.5S

No region may be deleted after seeing discrepancy values.

## Inputs

Each case must obtain required files only from the paths emitted by the pinned GCClassic dry-run and its copied `download_data.py` / `download_data.yml` configuration. The preferred portal is `geoschem+aws`; `geoschem+http` is an allowed documented fallback if the AWS CLI route is unavailable. Any substitution of meteorology collection or restart family requires a prospective protocol amendment.

## Required evidence

Each run must preserve:

- exact wrapper/science/submodule SHAs;
- compiler, CMake, netCDF-C, netCDF-Fortran versions;
- final `geoschem_config.yml`, `HEMCO_Config.rc`, `HISTORY.rc` hashes;
- dry-run log and unique-input manifest;
- input download log;
- runtime log;
- output NetCDF validation report;
- per-file SHA256 manifest;
- workflow commit SHA and Actions run ID.

## Failure classes

- `CONNECTOR_BLOCKED`
- `REMOTE_BUILD_FAILURE`
- `REFERENCE_INPUT_FAILURE`
- `REFERENCE_RUNTIME_FAILURE`
- `REFERENCE_OUTPUT_VALIDATION_FAILURE`

A failure is preserved and must not be converted to PASS by changing season, region, resolution, tracer, timestep, or input collection after scoring begins.

## External metrics

For aligned endpoint fields define external discrepancies for production Teacher `T`, internal high-fidelity reference `HF`, and optional trained correction `N`:

`D_T = ||q_GC - q_T||`

`D_HF = ||q_GC - q_HF||`

`D_N = ||q_GC - q_N||`

Primary audit questions are directional, not equivalence claims:

1. Is `D_HF < D_T` on held-out seasons/regions?
2. Is `D_N < D_T` on held-out seasons/regions?
3. Are improvements consistent across the frozen regional masks rather than driven by one latitude band?

Failure of either inequality is an external-validation result; it does not retroactively invalidate the already-frozen same-family training truth unless it exposes a separate implementation defect.

## Leakage rule

GEOS-Chem states, discrepancies, diagnostics, and scores are prohibited from model fitting, hyperparameter selection, normalization fitting, early stopping, architecture selection, or training-set filtering for the Paper-1 primary experiment.
