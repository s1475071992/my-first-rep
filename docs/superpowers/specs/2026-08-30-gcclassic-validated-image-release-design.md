# GCClassic Validated Image Release Design

## Goal

Publish a permanent reusable GCClassic 14.7.1 OCI image only after the exact candidate image has passed the complete frozen Paper-1 external-reference acceptance matrix.

## Release invariant

No container image is pushed to GHCR before all of the following have passed on the same local candidate image:

1. Control-plane contract tests.
2. Frozen executable SHA256 identity check.
3. HISTORY transport-audit policy: only Restart and SpeciesConc enabled for the one-hour cases; the former CloudConvFlux abort path is absent.
4. HEMCO restart fallback policy: the `SPC_` restart container uses `CYS`, so missing restart species such as Rn222 do not abort initialization.
5. One-hour GCClassic runtime reaches `END OF GEOS--CHEM` without HEMCO/GEOS-Chem fatal markers.
6. PassiveTracer pre/post reference-pair integrity checks.
7. Dry-air mass fields are present, finite, positive, and used to report dry-air-weighted PassiveTracer diagnostics.
8. All frozen seasons DJF, MAM, JJA, SON pass.
9. For every seasonal result, all frozen holdout regions TROPICS, NH_MIDLAT, SH_MIDLAT, ARCTIC, ANTARCTIC pass producer-integrity acceptance, yielding 20 season-region cells.

Publication is a pure `docker tag` + `docker push` of the already-tested local image. There is no rebuild between validation and publication.

## Matrix execution model

The frozen matrix defines four global 4x5 MERRA2 TransportTracers integrations and five latitude-band holdout regions. Therefore the producer runs four GCClassic integrations, one per season, and evaluates five region slices from each pre/post pair. This yields 20 acceptance cells without redundantly rerunning the same global integration five times.

## Reference-pair acceptance boundary

This gate validates reference-production integrity, not Torch-vs-GC numerical equivalence. It verifies finite PassiveTracer, finite positive `Met_DELPDRY`, valid grid-cell area, matching pre/post grids, distinct pre/post files, and complete regional metrics. It records dry-air-mass and PassiveTracer inventory changes but introduces no new scoring threshold and changes no frozen scientific threshold.

## Image contents

The candidate image is built from the explicitly pinned frozen GCClassic build bundle. It contains:

- the exact previously compiled GCClassic 14.7.1 executable;
- the pinned GCClassic / GEOS-Chem / HEMCO source trees and provenance already stored in the frozen bundle;
- the TransportTracers run-directory template;
- runtime libraries and Python packages needed for dry-run, official input download, NetCDF validation, and matrix production;
- the control scripts and frozen matrix configuration from the control-repository commit being validated.

GCClassic is never recompiled in the reference-release workflow.

## Publication identity

The workflow publishes a unique GHCR tag containing the validation run ID and records the immutable OCI digest. The publication manifest also records the control-repository SHA, frozen build run/artifact identity, frozen executable SHA256, GCClassic/GEOS-Chem/HEMCO SHAs, matrix ID, and 4/5/20 acceptance counts.

Future Paper-1 runs should reference the image by OCI digest rather than relying on a mutable tag.
