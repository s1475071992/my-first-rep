# GC14_7_1_REFERENCE_PRODUCER_V1 Design

## Purpose

Create an isolated GitHub Actions control plane that builds pinned GEOS-Chem Classic 14.7.1 on a GitHub-hosted Ubuntu runner and produces external transport-reference evidence without changing the Paper-1 Torch training truth.

## Scientific role

- Evidence label: `GC_DISCREPANCY_AUDIT` / `EXTERNAL_BEHAVIOR_VALIDATION`.
- GEOS-Chem is **not** a neural training label.
- TPCORE distillation is out of scope.
- L5 forward numerical equivalence is not claimed.
- Numerical source must remain upstream-authentic; only diagnostic/configuration instrumentation is allowed.

## Frozen upstream

- Wrapper: `geoschem/GCClassic`, tag `14.7.1`.
- Science code: wrapper-pinned GEOS-Chem 14.7.1; expected science release commit includes `b9f570e` provenance already used by Paper 1.
- First remote experiment: global 4x5 MERRA-2 `TransportTracers`, 72 levels, `PassiveTracer` available in the transported-species list.

## Execution phases

1. Verify runner toolchain and install `libnetcdf-dev`, `libnetcdff-dev`, `netcdf-bin`.
2. Clone GCClassic at the exact tag with recursive submodules and record all submodule SHAs.
3. Create a noninteractive 4x5 MERRA-2 TransportTracers run directory.
4. Configure a one-hour interval and compile/install `gcclassic`.
5. Execute `gcclassic --dryrun` and capture the exact official input manifest.
6. Validate dry-run provenance and upload logs/configuration as an artifact.
7. A later production step may download only the manifest-listed official inputs and execute the external reference run; inability to obtain inputs is `REFERENCE_INPUT_FAILURE`, not a Teacher failure.

## Failure classes

- `CONNECTOR_BLOCKED`
- `LOCAL_CONTAINER_NETWORK_BLOCKED`
- `REMOTE_BUILD_FAILURE`
- `REFERENCE_INPUT_FAILURE`
- `REFERENCE_RUNTIME_FAILURE`

## Repository isolation

This branch contains only workflow control files, scripts, tests, provenance, logs/artifacts metadata. It does not vendor or modify GEOS-Chem numerical source and does not commit large scientific binaries.
