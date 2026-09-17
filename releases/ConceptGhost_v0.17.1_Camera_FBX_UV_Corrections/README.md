# ConceptGhost v0.17.1 — Camera / FBX / UV Corrections

Complete frozen snapshot of the v0.17.1 correction pass.

Corrections included:
- exact source-image camera aspect / film-back framing contract;
- explicit Maya filmFit, resolution gate and source image-plane framing;
- FBX camera round-trip verification with focal/aperture/offset/world-matrix checks;
- FBX success is no longer inferred from file existence;
- raw MoGe E2 preview keeps native UV orientation for ComfyUI;
- separate E2-DCC branch converts the mesh to Atlas world space and flips V only for Maya/DCC export.

The complete project tree is stored as a tar.xz encoded into ordered Base64 parts in `tar_xz_parts/`. Run `RESTORE_BUNDLE.bat` on Windows to reconstruct and extract it.

Automated verification before publication: 87 tests passed, compileall passed, snapshot manifest had 0 mismatches. Real Maya/ComfyUI runtime validation is still required on the target Windows workstation.
