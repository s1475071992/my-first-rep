# GC14_7_1_TRANSPORTTRACERS_BC_NESTED_QUALIFICATION_V1

## 1. Qualification status

**Status: PASS**

This document freezes the successful input-chain qualification for the GEOS-Chem Classic 14.7.1 TransportTracers Europe nested-grid no-op qualification case.

The qualification establishes all of the following for the pinned case:

- the canonical global TransportTracers boundary-condition producer runs successfully with the frozen GCClassic executable;
- the produced BoundaryConditions file contains `SpeciesBC_PassiveTracer`;
- the produced BoundaryConditions file has the required 3-hourly instantaneous time semantics;
- the Europe nested case can resolve the required MERRA2 meteorology references;
- the Europe nested case can resolve the required restart reference;
- the Europe nested case can resolve and open the locally generated boundary-condition file;
- `gcclassic --dryrun` completes successfully for the nested case;
- no numerical-source modification, TPCORE modification, transport-timestep relaxation, or scientific-threshold modification was used to obtain PASS.

This is an **input-chain and dry-run qualification**. It is **not** a claim of full nested forward-run numerical equivalence, TorchCTM-vs-GEOS-Chem equivalence, or Paper 1 L5 equivalence.

---

## 2. Frozen qualification identifiers

| Item | Value |
|---|---|
| Qualification schema | `GC14_7_1_NESTED_BC_INPUT_QUALIFICATION_V1` |
| BC producer ID | `GC14_7_1_TRANSPORTTRACERS_BC_PRODUCER_V1` |
| Nested case ID | `GCNOOP_NESTED_EU_JJA_20190701_V1` |
| GCClassic version | `14.7.1` |
| GCClassic SHA | `c36ecd760c6663a62769f05a7449c927b8faf54b` |
| GEOS-Chem SHA | `b9f570e2c7a98b308004cd07e2985a12a47b6f5c` |
| Successful control-repo SHA | `9b422c6b0d8acad736a02440987149895e7398d3` |
| Successful workflow run | `33310761854` |
| Workflow | `gc14-input-probe` |
| Successful evidence artifact ID | `9731913805` |
| Evidence artifact name | `gc14-transporttracers-bc-nested-eu-33310761854` |
| Evidence artifact SHA-256 | `0778460f08410ce83f4f05749ac6bdc3a63c36c83114396de3b2a1b4f274b2e8` |

---

## 3. Frozen nested qualification case

The qualified nested case is:

| Property | Frozen value |
|---|---|
| Domain kind | `GEOSCHEM_NESTED_REGIONAL` |
| Domain | Europe (`EU`) |
| Grid | `0.5x0.625` |
| Longitude range | `[-30.0, 50.0]` |
| Latitude range | `[30.0, 70.0]` |
| Buffer zone NSEW | `[3, 3, 3, 3]` |
| Vertical levels | `72` |
| Meteorology | `MERRA2` |
| Simulation | `TransportTracers` |
| Primary tracer | `PassiveTracer` |
| Start | `2019-07-01T00:00:00Z` |
| Duration | `3600 s` |
| Transport timestep | `300 s` |
| Expected transport steps | `12` |
| Chemistry timestep | `600 s` |
| Boundary conditions required | `true` |
| Scientific thresholds modified | `false` |

The purpose of this case remains `DIAGNOSTIC_INSTRUMENTATION_NOOP_QUALIFICATION`.

---

## 4. Canonical global BoundaryConditions producer

The nested qualification uses a dedicated global GEOS-Chem TransportTracers producer to generate the boundary conditions required by the Europe nested case.

Frozen producer properties:

| Property | Value |
|---|---|
| Source domain | `GLOBAL_LATLON` |
| Grid | global `4x5` |
| Meteorology | `MERRA2` |
| Simulation | `TransportTracers` |
| Primary tracer | `PassiveTracer` |
| Start | `2019-07-01T00:00:00Z` |
| Producer duration | `10800 s` (`00:00 -> 03:00 UTC`) |
| Transport timestep | `600 s` |
| BoundaryConditions frequency | `10800 s` / 3 h |
| BoundaryConditions mode | `instantaneous` |
| BoundaryConditions fields | `SpeciesBC_?ADV?` |
| Numerical-source modification | none |
| Scientific thresholds modified | `false` |

The producer reused the frozen executable with SHA-256:

```text
0ca0d46b3fc2809285f270ca817adfbb7d02ff97099a7546bf08649736e22696
```

No GCClassic or GEOS-Chem recompilation was used in this qualification workflow.

---

## 5. Generated BoundaryConditions evidence

The successful producer generated:

```text
GEOSChem.BoundaryConditions.20190701_0000z.nc4
```

Frozen file evidence:

| Property | Value |
|---|---|
| Status | `PASS` |
| File size | `23,952,569 bytes` |
| File SHA-256 | `5345eb22b09c512c24e58861f7dcc1ccc13e2a6bffdbee10667b44919163d6e9` |
| Contains `SpeciesBC_PassiveTracer` | `true` |
| Time record count | `2` |
| Time units | `minutes since 2019-07-01 00:00:00` |
| Time values | `0, 180` |
| Boundary frequency | `3 h` |
| Averaging mode | `instantaneous` |

The file dimensions are:

```text
time = 2
lev  = 72
ilev = 73
lat  = 46
lon  = 72
nb   = 2
```

The required tracer variable is present as:

```text
float SpeciesBC_PassiveTracer(time, lev, lat, lon)
SpeciesBC_PassiveTracer:units = "mol mol-1 dry"
SpeciesBC_PassiveTracer:averaging_method = "instantaneous"
```

The global producer log reaches the canonical GCClassic completion banner:

```text
**************   E N D   O F   G E O S -- C H E M   **************
```

Thus the BoundaryConditions file is not a synthetic placeholder: it was produced by the frozen GCClassic 14.7.1 executable in the qualification run.

---

## 6. Boundary-condition time semantics

The qualified container has two records at 00:00 and 03:00 UTC:

```text
time = 0, 180 minutes since 2019-07-01 00:00:00
```

This preserves the standard GEOS-Chem 3-hourly BoundaryConditions container semantics.

For the nested qualification interval `2019-07-01 00:00 -> 01:00 UTC`, the generated file therefore provides the canonical 00 UTC 3-hour bin while retaining the following 03 UTC record in the same container.

The producer cadence was not shortened to match the one-hour nested qualification. The nested test therefore validates the intended 3-hourly BC interface rather than a special one-hour test-only BC format.

---

## 7. Nested input qualification result

The final `qualification_result.json` reports:

```text
status = PASS
```

The four required nested gates are:

| Gate | Result | Evidence |
|---|---|---|
| MET | `RESOLVABLE` | 8 / 8 required meteorology references resolvable |
| RESTART | `RESOLVABLE` | 1 / 1 restart reference resolvable |
| BC | `RESOLVABLE` | 1 / 1 BC reference resolvable as the locally generated file |
| DRYRUN | `PASS` | nested `gcclassic --dryrun` completed successfully |

Therefore the final qualification vector is:

```text
BC_PRODUCER  PASS
MET          RESOLVABLE
RESTART      RESOLVABLE
BC           RESOLVABLE
DRYRUN       PASS
OVERALL      PASS
```

---

## 8. MET evidence

The audit found eight required MERRA2 references and resolved all eight against the official GCGrid HTTP portal.

Examples include:

```text
GEOS_0.5x0.625_EU/MERRA2/2019/07/MERRA2.20190701.A1.05x0625.EU.nc4
GEOS_0.5x0.625_EU/MERRA2/2019/07/MERRA2.20190701.A3cld.05x0625.EU.nc4
GEOS_0.5x0.625_EU/MERRA2/2019/07/MERRA2.20190701.A3dyn.05x0625.EU.nc4
GEOS_0.5x0.625_EU/MERRA2/2019/07/MERRA2.20190701.A3mstC.05x0625.EU.nc4
GEOS_0.5x0.625_EU/MERRA2/2019/07/MERRA2.20190701.A3mstE.05x0625.EU.nc4
GEOS_0.5x0.625_EU/MERRA2/2019/07/MERRA2.20190701.I3.05x0625.EU.nc4
GEOS_0.5x0.625_EU/MERRA2/2019/07/MERRA2.20190702.I3.05x0625.EU.nc4
```

The regional constants/ocean-mask path is also qualified using the Europe-specific MERRA2 0.5x0.625 constants file.

The qualification intentionally does not download the complete nested scientific input payload. `nested_scientific_data_downloaded` remains `false`; the MET gate is a resolvability qualification, not a full nested forward integration.

---

## 9. Restart evidence

The required nested restart reference resolves successfully to the official benchmark restart source:

```text
GEOSCHEM_RESTARTS/GC_14.7.0/GEOSChem.Restart.TransportTracers.20190101_0000z.nc4
```

Qualification result:

```text
reference_count     = 1
resolvable_count    = 1
unresolvable_count  = 0
status              = RESOLVABLE
```

This preserves the existing benchmark-restart mapping used by the frozen external-reference architecture.

---

## 10. Nested BC injection evidence

The nested HEMCO configuration was modified only to point its `GC_BCs` input to the locally generated global BoundaryConditions file.

The nested dry-run log explicitly opens:

```text
/tmp/gc14-nested-input-probe/global-bc-rundir/OutputDir/GEOSChem.BoundaryConditions.20190701_0000z.nc4
```

The BC audit records:

```text
family             = BC
resolution_mode    = LOCAL_GENERATED_FILE
resolvable         = true
local_sha256       = 5345eb22b09c512c24e58861f7dcc1ccc13e2a6bffdbee10667b44919163d6e9
local_size_bytes   = 23952569
```

No remote substitute was used for the BC gate.

---

## 11. Meaning of dry-run `REQUIRED FILE NOT FOUND` lines

The nested `gcclassic --dryrun` log contains `REQUIRED FILE NOT FOUND` lines for meteorology and restart paths. In this workflow those messages are expected dry-run declarations of required input paths; they are not interpreted by themselves as qualification failures.

The control-plane audit separately resolves the relevant MET and RESTART paths against the official GCGrid portal and requires all frozen members of those families to be resolvable.

The BC path is stronger: it is a real local file generated earlier in the same workflow and is actually opened by HEMCO during the nested dry-run.

Accordingly, the qualification logic is:

```text
dry-run declares required path
        +
control-plane proves MET/RESTART remote resolvability
        +
control-plane proves BC local existence/hash
        +
nested gcclassic --dryrun exits successfully
        =
input-chain qualification PASS
```

This distinction prevents a dry-run diagnostic string from being misclassified as a scientific/runtime model failure.

---

## 12. Root cause closed during qualification

### 12.1 Failing run used for diagnosis

Before the final PASS, workflow run `33309499938` failed in the global BC producer. Its evidence artifact was:

```text
artifact ID: 9731541392
artifact:    gc14-transporttracers-bc-nested-eu-33309499938
```

The producer log reported:

```text
Collection        BoundaryConditions
  -> FileName     not found
  -> Frequency    not found
  -> Mode         not found

GEOS-Chem ERROR: Collection: BoundaryConditions is undefined!
```

### 12.2 Actual root cause

The generated `HISTORY.rc` had an empty line between the previous inactive collection terminator and the appended active BoundaryConditions definition:

```text
::

#==============================================================================
# %%%%% THE BoundaryConditions COLLECTION %%%%%
```

In GCClassic 14.7.1 `History_ReadCollectionData`, the state used while skipping an inactive collection can remain `UNDEFINED_INT`. Encountering the blank line immediately after the skipped collection causes the parser to re-enter the inactive-collection skip path and consume input until the next `::`. The complete BoundaryConditions block was therefore skipped even though it was correctly listed under `COLLECTIONS`.

The failure was a HISTORY parser/control-plane formatting interaction, not a failure of BoundaryConditions science, PassiveTracer, TPCORE, HEMCO time interpolation, or the frozen executable.

### 12.3 TDD closure

A regression test was added first to require the BoundaryConditions header to be immediately adjacent to the previous `::\n` terminator.

RED evidence:

```text
workflow run: 33310725778
commit:       68495d02e68b0737b5390920bc3fb1000ba8606f
result:       1 failed, 8 passed
failed test:  test_bc_history_patch_keeps_active_bc_block_adjacent_to_previous_terminator
```

The production fix then removed only the leading newline from the appended `BC_BLOCK`.

GREEN/final implementation commit:

```text
9b422c6b0d8acad736a02440987149895e7398d3
```

The resulting successful workflow run was `33310761854`.

No numerical or scientific configuration was changed as part of this fix.

---

## 13. Frozen control-plane hashes from the successful run

Selected successful-run SHA-256 values:

```text
config/nested_noop_case.json
861b50008a3fd416bef8fd895651d51e34f4f451432452b7fc91ef096cac7372

config/transporttracers_bc_producer.json
e6145d1e8a992528e01ace013653cdb81e35cb4dca542bfd22d5fa5f7682ac30

scripts/create_nested_noop_rundir.sh
01df65c2b1e0eee31fae4a3c7b279a757151b10f2d8692cb07d78e205ca382a4

scripts/audit_nested_dryrun.py
b12b40ec65449a5d9e73f0108bfce13252ce8e18a04465f9a8811877505af3e9

scripts/patch_boundary_conditions_history.py
4aff64bd49e1ce5807014625f9dd3cddec2704febe22b14d56305da0145f109d

scripts/configure_nested_boundary_conditions.py
e60fc3fa5ddb1c6e297300c71f385c5374bb09e212f402988d008ee75668f8c0

.github/workflows/gc14-input-probe.yml
2f3ee77ef256f911916b597c51ea6cd47aaaef45e025c6b7b717832f55d57437
```

Successful nested configuration hashes include:

```text
geoschem_config.yml
af08d2d704ca641ef28b8985edf185f279ee8c72e45f1c81989a3c90ecc2f77a

HEMCO_Config.rc
38600d2fdec831410e80fd01710255b9b498e00aa81c15317bc0fe241d483672

HISTORY.rc
7666cc825d3b6c49b83f3b275810ef58f9565da1e087982fc33c2c6bddd9cd80

species_database.yml
4ad82d86b1ebc40f82c2654563921e6ade07cf99f3f1083918538a59a48d16e6

nested log.dryrun
dc106a4037ddf81dc9d3b05bb343dd495a9b30c9cf2c546617ea28ed25daf4c8

nested_input_probe.json
b4d4950a1f9238713918f4982cf2723c1be3c038d4216243321f9b76a5d57d64

qualification_result.json
24720590bed30dd3568762d2fac905af3c36346087cb936f20a1a4f79e91744f
```

---

## 14. Scientific invariants preserved

The successful qualification does **not** change any of the following:

- GCClassic 14.7.1 source identity;
- frozen GEOS-Chem source identity;
- frozen GCClassic executable identity;
- TPCORE numerical source;
- horizontal or vertical transport algorithm;
- global producer transport timestep (`600 s`);
- nested qualification transport timestep (`300 s`);
- chemistry timestep (`600 s` nested qualification);
- BoundaryConditions cadence (`3 h`);
- BoundaryConditions mode (`instantaneous`);
- PassiveTracer definition;
- negative-value handling;
- mass flux formulation;
- frozen scientific thresholds.

`scientific_thresholds_modified` remains `false` in both producer and nested qualification outputs.

---

## 15. What this qualification proves

This qualification proves that a reproducible, source-authentic input path now exists from the frozen global TransportTracers producer into the pinned Europe nested TransportTracers configuration:

```text
frozen GCClassic executable
        |
        v
global 4x5 MERRA2 TransportTracers
        |
        |  canonical 3-hour instantaneous SpeciesBC_?ADV?
        v
GEOSChem.BoundaryConditions.20190701_0000z.nc4
        |
        v
Europe 0.5x0.625 MERRA2 TransportTracers HEMCO GC_BCs
        |
        v
nested gcclassic --dryrun
        |
        v
MET / RESTART / BC resolvability audit
        |
        v
OVERALL PASS
```

The previous nested input-chain blocker is therefore closed at the qualification level.

---

## 16. What this qualification does not prove

This document must not be cited as evidence for any of the following stronger claims:

- successful one-hour **full nested forward integration** with every scientific input downloaded locally;
- numerical equivalence between global and nested runs;
- numerical equivalence between GEOS-Chem and TorchCTM;
- trajectory-level Paper 1 acceptance;
- operator-substep equivalence;
- L5 forward numerical equivalence;
- validation of any future Fortran instrumentation hook.

Those require separate, explicitly frozen gates.

---

## 17. Governance conclusion

The nested input-chain qualification gate is closed:

```text
GC14_7_1_TRANSPORTTRACERS_BC_NESTED_QUALIFICATION_V1 = PASS
```

The frozen evidence anchor is workflow run:

```text
33310761854
```

with successful evidence artifact:

```text
9731913805
sha256:0778460f08410ce83f4f05749ac6bdc3a63c36c83114396de3b2a1b4f274b2e8
```

and generated BoundaryConditions payload:

```text
GEOSChem.BoundaryConditions.20190701_0000z.nc4
sha256:5345eb22b09c512c24e58861f7dcc1ccc13e2a6bffdbee10667b44919163d6e9
```

This closes the required BC/MET/RESTART/dry-run prerequisite for the pinned Europe nested no-op qualification case while preserving the Paper 1 frozen scientific configuration and the rule against unqualified numerical-source changes.
