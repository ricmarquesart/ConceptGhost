# ConceptGhost v0.34 — Final Candidate Authority

Status: **FINAL CANDIDATE — consolidated Windows/ComfyUI/Maya acceptance pending**

## Executable bundle authority
- File: `ConceptGhost_v0.34_COMPLETE.zip`
- Size: `11,727,642` bytes
- SHA-256: `744ec8b8b19f7d8a301c2310a80b36f9c344489853c6ea06d893ef6d999e58a5`
- Google Drive folder: https://drive.google.com/drive/folders/1bCw7Vu4yJGkYQBTuN8mpD1dngCmZjhOA
- Google Drive file: https://drive.google.com/file/d/1D25OtK6KaL0sxC-CG_62vBpBjTy0Tlkh/view?usp=drivesdk

The Drive folder intentionally contains one complete bundle only.

## Bundle validation
- ZIP CRC: PASS
- Bundle manifest/hash verification: PASS
- Local regression suite: **129 PASS**
- Python compileall: PASS
- Workflow: `ConceptGhost_Master_v0.34.json`
- Workflow graph: **45 nodes / 92 links**
- Legacy v0.30/v0.31/v0.32/v0.33 filenames in release: none
- DA3 files/tools in release: none
- MoGe pinned vendor archive: included for clean-machine core installation
- Depth Pro: optional isolated runtime/bootstrap; core workflow does not require it

## Improvements status
- P1/A1 MoGe Metric Evidence: COMPLETE LOCAL
- P2/A2+A3+A4 Atlas Metrology: COMPLETE LOCAL
- P3/A5 MoGe × Atlas Agreement: COMPLETE LOCAL
- P4/A6 Maya Metric Diagnostics: IMPLEMENTED; Maya runtime acceptance pending
- P5/B1 Depth Pro witness: COMPLETE LOCAL; target runtime test pending
- P6/B3 Metric Consensus: COMPLETE LOCAL
- P7/B4 Geometric Regions: COMPLETE LOCAL + frozen real-PrimaryMesh benchmark
- P8/A7 Local Geometry Cleanup: COMPLETE LOCAL + frozen real-PrimaryMesh benchmark
- DA3 machine cleanup: completed separately by user; not part of v0.34

## Real frozen PrimaryMesh improvement proof
- PrimaryMesh: 1,426,735 vertices / 2,823,599 faces
- P7 retained regions: 96
- P7 face coverage: 96.65%
- exact connected components: 48
- principal shell: 98.2238% of faces
- P8 severe face removal candidate: 1 face only
- planar relaxation: CG_REGION_008 only
- moved interior vertices: 14,705
- max displacement: 0.0200000016 m
- RMS planarity: 0.0750368 m -> 0.0624955 m (~16.7% improvement)
- vertices moved outside approved region: 0
- protected boundary vertices moved: 0
- cross-region vertices moved: 0
- automatic PrimaryMesh replacement: false

## Artist-facing output correction
The final workflow terminates Master, Remesh Light, Remesh Medium, Remesh Strong and Local Cleanup Candidate in native ComfyUI `SaveGLB` nodes so the frontend can provide the normal 3D preview/download experience.

## Final acceptance still required
Run v0.34 on the target Windows/ComfyUI/Maya machine and collect validation evidence. Maya LIVE, Maya REOPEN, FBX ROUNDTRIP, optional Depth Pro runtime, and native frontend preview/download behavior must be confirmed on the target machine before promotion from FINAL CANDIDATE to RUNTIME VALIDATED.
