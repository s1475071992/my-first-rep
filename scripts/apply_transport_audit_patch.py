#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

SCIENCE_SHA = "b9f570e2c7a98b308004cd07e2985a12a47b6f5c"
ALLOWLIST = {
    "GeosCore/CMakeLists.txt",
    "GeosCore/transport_mod.F90",
    "GeosCore/tpcore_fvdas_mod.F90",
    "GeosCore/tpcore_window_mod.F90",
    "GeosCore/transport_audit_mod.F90",
}

MODULE = r'''! Diagnostic-only transport forcing capture for TorchCTM Paper 1.
! Source-native values only.  No scientific arithmetic is changed here.
MODULE Transport_Audit_Mod
  USE Precision_Mod, ONLY : fp
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: Audit_Capture_Horiz
  PUBLIC :: Audit_Capture_Global_WZ
  PUBLIC :: Audit_Capture_Nested_Vert
  PUBLIC :: Audit_Flush

  LOGICAL, SAVE :: checked = .FALSE.
  LOGICAL, SAVE :: enabled = .FALSE.
  LOGICAL, SAVE :: have_horiz = .FALSE.
  LOGICAL, SAVE :: have_global_wz = .FALSE.
  LOGICAL, SAVE :: have_nested_vert = .FALSE.
  LOGICAL, SAVE :: nested = .FALSE.
  INTEGER, SAVE :: step_id = 0
  INTEGER, SAVE :: i_start=0, i_end=0, j_start=0, j_end=0
  INTEGER, SAVE :: west_buffer=0, east_buffer=0, south_buffer=0, north_buffer=0
  REAL(fp), SAVE :: runtime_dt_s = 0.0_fp
  CHARACTER(LEN=1024), SAVE :: audit_path = ''
  REAL(fp), ALLOCATABLE, SAVE :: xmass_save(:,:,:), ymass_save(:,:,:)
  REAL(fp), ALLOCATABLE, SAVE :: wz_save(:,:,:)
  REAL(fp), ALLOCATABLE, SAVE :: pe_save(:,:,:), ps_save(:,:)
  REAL(fp), ALLOCATABLE, SAVE :: ak_save(:), bk_save(:)

CONTAINS

  SUBROUTINE Audit_Check_Enabled()
    CHARACTER(LEN=64) :: flag
    INTEGER :: stat
    IF ( checked ) RETURN
    checked = .TRUE.
    flag = ''
    CALL GET_ENVIRONMENT_VARIABLE('GC_TRANSPORT_AUDIT', flag, STATUS=stat)
    enabled = ( stat == 0 .AND. TRIM(flag) == '1' )
    IF ( .NOT. enabled ) RETURN
    audit_path = ''
    CALL GET_ENVIRONMENT_VARIABLE('GC_TRANSPORT_AUDIT_PATH', audit_path, STATUS=stat)
    IF ( stat /= 0 .OR. LEN_TRIM(audit_path) == 0 ) THEN
       ERROR STOP 'GC_TRANSPORT_AUDIT_PATH is required when GC_TRANSPORT_AUDIT=1'
    ENDIF
  END SUBROUTINE Audit_Check_Enabled

  SUBROUTINE Audit_Capture_Horiz(dt, xmass, ymass, ak, bk, is_nested, &
                                 i0, i1, j0, j1, wb, eb, sb, nb)
    REAL(fp), INTENT(IN) :: dt
    REAL(fp), INTENT(IN) :: xmass(:,:,:), ymass(:,:,:)
    REAL(fp), INTENT(IN) :: ak(:), bk(:)
    LOGICAL, INTENT(IN) :: is_nested
    INTEGER, INTENT(IN) :: i0, i1, j0, j1, wb, eb, sb, nb
    CALL Audit_Check_Enabled()
    IF ( .NOT. enabled ) RETURN
    IF ( ALLOCATED(xmass_save) ) DEALLOCATE(xmass_save)
    IF ( ALLOCATED(ymass_save) ) DEALLOCATE(ymass_save)
    IF ( ALLOCATED(ak_save) ) DEALLOCATE(ak_save)
    IF ( ALLOCATED(bk_save) ) DEALLOCATE(bk_save)
    ALLOCATE(xmass_save(SIZE(xmass,1),SIZE(xmass,2),SIZE(xmass,3)))
    ALLOCATE(ymass_save(SIZE(ymass,1),SIZE(ymass,2),SIZE(ymass,3)))
    ALLOCATE(ak_save(SIZE(ak)), bk_save(SIZE(bk)))
    xmass_save = xmass
    ymass_save = ymass
    ak_save = ak
    bk_save = bk
    runtime_dt_s = dt
    nested = is_nested
    i_start=i0; i_end=i1; j_start=j0; j_end=j1
    west_buffer=wb; east_buffer=eb; south_buffer=sb; north_buffer=nb
    have_horiz = .TRUE.
  END SUBROUTINE Audit_Capture_Horiz

  SUBROUTINE Audit_Capture_Global_WZ(wz)
    REAL(fp), INTENT(IN) :: wz(:,:,:)
    CALL Audit_Check_Enabled()
    IF ( .NOT. enabled ) RETURN
    IF ( ALLOCATED(wz_save) ) DEALLOCATE(wz_save)
    ALLOCATE(wz_save(SIZE(wz,1),SIZE(wz,2),SIZE(wz,3)))
    wz_save = wz
    have_global_wz = .TRUE.
  END SUBROUTINE Audit_Capture_Global_WZ

  SUBROUTINE Audit_Capture_Nested_Vert(pe, ps)
    REAL(fp), INTENT(IN) :: pe(:,:,:), ps(:,:)
    CALL Audit_Check_Enabled()
    IF ( .NOT. enabled ) RETURN
    IF ( ALLOCATED(pe_save) ) DEALLOCATE(pe_save)
    IF ( ALLOCATED(ps_save) ) DEALLOCATE(ps_save)
    ALLOCATE(pe_save(SIZE(pe,1),SIZE(pe,2),SIZE(pe,3)))
    ALLOCATE(ps_save(SIZE(ps,1),SIZE(ps,2)))
    pe_save = pe
    ps_save = ps
    have_nested_vert = .TRUE.
  END SUBROUTINE Audit_Capture_Nested_Vert

  SUBROUTINE Audit_Write_3D(suffix, a)
    CHARACTER(LEN=*), INTENT(IN) :: suffix
    REAL(fp), INTENT(IN) :: a(:,:,:)
    CHARACTER(LEN=1400) :: fname
    CHARACTER(LEN=6) :: s
    INTEGER :: u, ios
    WRITE(s,'(I6.6)') step_id
    fname = TRIM(audit_path)//'/step_'//s//'_'//TRIM(suffix)
    OPEN(NEWUNIT=u, FILE=TRIM(fname), STATUS='REPLACE', ACCESS='STREAM', &
         FORM='UNFORMATTED', ACTION='WRITE', IOSTAT=ios)
    IF ( ios /= 0 ) ERROR STOP 'transport audit binary open failed'
    WRITE(u) a
    CLOSE(u)
  END SUBROUTINE Audit_Write_3D

  SUBROUTINE Audit_Write_2D(suffix, a)
    CHARACTER(LEN=*), INTENT(IN) :: suffix
    REAL(fp), INTENT(IN) :: a(:,:)
    CHARACTER(LEN=1400) :: fname
    CHARACTER(LEN=6) :: s
    INTEGER :: u, ios
    WRITE(s,'(I6.6)') step_id
    fname = TRIM(audit_path)//'/step_'//s//'_'//TRIM(suffix)
    OPEN(NEWUNIT=u, FILE=TRIM(fname), STATUS='REPLACE', ACCESS='STREAM', &
         FORM='UNFORMATTED', ACTION='WRITE', IOSTAT=ios)
    IF ( ios /= 0 ) ERROR STOP 'transport audit binary open failed'
    WRITE(u) a
    CLOSE(u)
  END SUBROUTINE Audit_Write_2D

  SUBROUTINE Audit_Write_1D(suffix, a)
    CHARACTER(LEN=*), INTENT(IN) :: suffix
    REAL(fp), INTENT(IN) :: a(:)
    CHARACTER(LEN=1400) :: fname
    CHARACTER(LEN=6) :: s
    INTEGER :: u, ios
    WRITE(s,'(I6.6)') step_id
    fname = TRIM(audit_path)//'/step_'//s//'_'//TRIM(suffix)
    OPEN(NEWUNIT=u, FILE=TRIM(fname), STATUS='REPLACE', ACCESS='STREAM', &
         FORM='UNFORMATTED', ACTION='WRITE', IOSTAT=ios)
    IF ( ios /= 0 ) ERROR STOP 'transport audit binary open failed'
    WRITE(u) a
    CLOSE(u)
  END SUBROUTINE Audit_Write_1D

  SUBROUTINE Audit_Flush()
    CHARACTER(LEN=1400) :: fname
    CHARACTER(LEN=6) :: s
    INTEGER :: u, ios
    CALL Audit_Check_Enabled()
    IF ( .NOT. enabled ) RETURN
    IF ( .NOT. have_horiz ) ERROR STOP 'transport audit missing horizontal capture'
    IF ( nested .AND. .NOT. have_nested_vert ) ERROR STOP 'transport audit missing nested vertical capture'
    IF ( (.NOT. nested) .AND. .NOT. have_global_wz ) ERROR STOP 'transport audit missing global WZ capture'

    CALL Audit_Write_3D('xmass.bin', xmass_save)
    CALL Audit_Write_3D('ymass.bin', ymass_save)
    CALL Audit_Write_1D('ak.bin', ak_save)
    CALL Audit_Write_1D('bk.bin', bk_save)
    IF ( nested ) THEN
       CALL Audit_Write_3D('pe_src.bin', pe_save)
       CALL Audit_Write_2D('ps_target.bin', ps_save)
    ELSE
       CALL Audit_Write_3D('wz.bin', wz_save)
    ENDIF

    WRITE(s,'(I6.6)') step_id
    fname = TRIM(audit_path)//'/step_'//s//'_window_meta.txt'
    OPEN(NEWUNIT=u, FILE=TRIM(fname), STATUS='REPLACE', ACTION='WRITE', IOSTAT=ios)
    IF ( ios /= 0 ) ERROR STOP 'transport audit metadata open failed'
    WRITE(u,'(A,I0)') 'step_id=', step_id
    WRITE(u,'(A,ES24.16)') 'runtime_dt_s=', runtime_dt_s
    WRITE(u,'(A,I0)') 'source_fp_bytes=', STORAGE_SIZE(runtime_dt_s)/8
    WRITE(u,'(A)') 'lev_tpcore=top_to_surface'
    IF ( nested ) THEN
       WRITE(u,'(A)') 'domain_kind=GEOSCHEM_NESTED_REGIONAL'
    ELSE
       WRITE(u,'(A)') 'domain_kind=GLOBAL_LATLON'
    ENDIF
    WRITE(u,'(A,I0)') 'nx=', SIZE(xmass_save,1)
    WRITE(u,'(A,I0)') 'ny=', SIZE(xmass_save,2)
    WRITE(u,'(A,I0)') 'nz=', SIZE(xmass_save,3)
    WRITE(u,'(A,I0)') 'nedge=', SIZE(ak_save)
    WRITE(u,'(A,I0)') 'i_start_gc=', i_start
    WRITE(u,'(A,I0)') 'i_end_gc=', i_end
    WRITE(u,'(A,I0)') 'j_start_gc=', j_start
    WRITE(u,'(A,I0)') 'j_end_gc=', j_end
    WRITE(u,'(A,I0)') 'west_buffer=', west_buffer
    WRITE(u,'(A,I0)') 'east_buffer=', east_buffer
    WRITE(u,'(A,I0)') 'south_buffer=', south_buffer
    WRITE(u,'(A,I0)') 'north_buffer=', north_buffer
    CLOSE(u)

    have_horiz = .FALSE.; have_global_wz = .FALSE.; have_nested_vert = .FALSE.
    IF ( ALLOCATED(xmass_save) ) DEALLOCATE(xmass_save)
    IF ( ALLOCATED(ymass_save) ) DEALLOCATE(ymass_save)
    IF ( ALLOCATED(wz_save) ) DEALLOCATE(wz_save)
    IF ( ALLOCATED(pe_save) ) DEALLOCATE(pe_save)
    IF ( ALLOCATED(ps_save) ) DEALLOCATE(ps_save)
    IF ( ALLOCATED(ak_save) ) DEALLOCATE(ak_save)
    IF ( ALLOCATED(bk_save) ) DEALLOCATE(bk_save)
    step_id = step_id + 1
  END SUBROUTINE Audit_Flush
END MODULE Transport_Audit_Mod
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_subroutine(text: str, name: str, old: str, new: str, label: str) -> str:
    upper = text.upper()
    start = upper.index(f"SUBROUTINE {name.upper()}")
    end = upper.index(f"END SUBROUTINE {name.upper()}", start)
    part = text[start:end]
    part2 = replace_once(part, old, new, label)
    return text[:start] + part2 + text[end:]


def patch(science: Path) -> None:
    sha = subprocess.check_output(["git", "-C", str(science), "rev-parse", "HEAD"], text=True).strip()
    if sha != SCIENCE_SHA:
        raise RuntimeError(f"GEOS-Chem SHA mismatch: {sha}")

    geos = science / "GeosCore"
    (geos / "transport_audit_mod.F90").write_text(MODULE)

    cm = geos / "CMakeLists.txt"
    text = cm.read_text()
    text = replace_once(text, "  transport_mod.F90\n", "  transport_audit_mod.F90\n  transport_mod.F90\n", "CMake registration")
    cm.write_text(text)

    tm = geos / "transport_mod.F90"
    text = tm.read_text()
    text = patch_subroutine(text, "DO_TRANSPORT",
        "    USE TIME_MOD,        ONLY : GET_TS_DYN\n",
        "    USE TIME_MOD,        ONLY : GET_TS_DYN\n    USE Transport_Audit_Mod, ONLY : Audit_Flush\n",
        "DO_TRANSPORT use")
    text = patch_subroutine(text, "DO_TRANSPORT",
        "    ENDIF\n\n    !------------------------------------------------------------------------\n    ! Transport (advection) budget diagnostics - Part 2 of 2",
        "    ENDIF\n\n    CALL Audit_Flush()\n\n    !------------------------------------------------------------------------\n    ! Transport (advection) budget diagnostics - Part 2 of 2",
        "DO_TRANSPORT flush")

    text = patch_subroutine(text, "DO_GLOBAL_ADV",
        "    USE TPCORE_FVDAS_MOD,   ONLY : TPCORE_FVDAS\n",
        "    USE TPCORE_FVDAS_MOD,   ONLY : TPCORE_FVDAS\n    USE Transport_Audit_Mod, ONLY : Audit_Capture_Horiz\n",
        "DO_GLOBAL_ADV use")
    anchor = "    p_XMASS   => XMASS            (:,:,State_Grid%NZ:1:-1)\n    p_YMASS   => YMASS            (:,:,State_Grid%NZ:1:-1)\n"
    call = anchor + "\n    CALL Audit_Capture_Horiz( D_DYN, p_XMASS, p_YMASS, Ap, Bp, .FALSE., &\n         1, State_Grid%NX, 1, State_Grid%NY, 0, 0, 0, 0 )\n"
    text = patch_subroutine(text, "DO_GLOBAL_ADV", anchor, call, "GLOBAL H1")

    text = patch_subroutine(text, "DO_WINDOW_TRANSPORT",
        "    USE TPCORE_WINDOW_MOD,    ONLY : TPCORE_WINDOW\n",
        "    USE TPCORE_WINDOW_MOD,    ONLY : TPCORE_WINDOW\n    USE Transport_Audit_Mod, ONLY : Audit_Capture_Horiz\n",
        "DO_WINDOW_TRANSPORT use")
    anchor = "    p_XMASS  => XMASS      ( IA:IB, JA:JB, State_Grid%NZ:1:-1    )\n    p_YMASS  => YMASS      ( IA:IB, JA:JB, State_Grid%NZ:1:-1    )\n    p_Spc    => Q_Spc      ( :,     :,     State_Grid%NZ:1:-1, : )\n"
    call = anchor + "\n    CALL Audit_Capture_Horiz( D_DYN, p_XMASS, p_YMASS, Ap, Bp, .TRUE., &\n         IA, IB, JA, JB, State_Grid%WestBuffer, State_Grid%EastBuffer, &\n         State_Grid%SouthBuffer, State_Grid%NorthBuffer )\n"
    text = patch_subroutine(text, "DO_WINDOW_TRANSPORT", anchor, call, "NESTED H1")
    tm.write_text(text)

    gf = geos / "tpcore_fvdas_mod.F90"
    text = gf.read_text()
    text = patch_subroutine(text, "Tpcore_FvDas",
        "    USE State_Diag_Mod, ONLY : DgnState\n",
        "    USE State_Diag_Mod, ONLY : DgnState\n    USE Transport_Audit_Mod, ONLY : Audit_Capture_Global_WZ\n",
        "TPCORE global use")
    anchor = "         (dbk, dps_ctm, dpi, wz, &\n         1, im, 1, jm, 1, km)\n"
    text = patch_subroutine(text, "Tpcore_FvDas", anchor,
        anchor + "\n    CALL Audit_Capture_Global_WZ( wz )\n", "GLOBAL H2")
    gf.write_text(text)

    nw = geos / "tpcore_window_mod.F90"
    text = nw.read_text()
    text = patch_subroutine(text, "TPCORE_WINDOW",
        "    USE State_Diag_Mod, ONLY : DgnState\n",
        "    USE State_Diag_Mod, ONLY : DgnState\n    USE Transport_Audit_Mod, ONLY : Audit_Capture_Nested_Vert\n",
        "TPCORE nested use")
    anchor = " call qmap(pe, q, im, jm, km, nx, jfirst, jlast, ng, nq,         &\n           ps, ak, bk, kord, iv)\n"
    text = patch_subroutine(text, "TPCORE_WINDOW", anchor,
        " call Audit_Capture_Nested_Vert( pe, ps )\n\n" + anchor, "NESTED H2")
    nw.write_text(text)

    changed = set(subprocess.check_output(
        ["git", "-C", str(science), "status", "--short"], text=True
    ).splitlines())
    names = {line[3:] for line in changed if len(line) >= 4}
    if names != ALLOWLIST:
        raise RuntimeError(f"diagnostic patch allowlist mismatch: {sorted(names)}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("science_dir")
    args = p.parse_args()
    patch(Path(args.science_dir).resolve())
    print("transport audit patch applied")


if __name__ == "__main__":
    main()
