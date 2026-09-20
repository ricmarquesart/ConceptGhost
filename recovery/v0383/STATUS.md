# ConceptGhost v0.38.3 — P9.10 CI checkpoint

Exact WIP bundle authority is stored in Google Drive as `ConceptGhost_v0.38.3_P9_SEMANTIC_GEOMETRY_WIP_CHECKPOINT.zip`.

Bundle SHA-256: `7360b142278b2d44e9d7a8ce1a3e7e0db43e4aef60c4a6d5f6bb6268dcc9b91c`.

Local static proof before packaging:
- P9 recovery: PASS
- P9.3–P9.8 contract recovery: PASS
- P9.10 semantic geometry: PASS
- Python compileall: PASS
- bundle manifest: 72/72 payload hashes PASS
- ZIP CRC: PASS

P9.10 geometry effects:
- confident sky invalidates canonical depth pixels before point-cloud reconstruction;
- semantic ground uses confidence/boundary-gated plane regularization;
- structure uses same-region/same-instance conservative smoothing;
- normal consistency gates refinement;
- semantic+dense boundaries suppress refinement;
- reliable normal+boundary discontinuities can reject PrimaryMesh bridge faces.

Windows/GPU Semantic Assist and Maya round-trip remain pending. This branch is WIP, not a release.
