# ConceptGhost v0.35 — Frozen Baseline

Status: **FROZEN BUILD / FINAL WINDOWS + COMFYUI + MAYA ACCEPTANCE PENDING**

## Exact authorities
- Complete bundle: `ConceptGhost_v0.35_COMPLETE.zip`
- Complete ZIP SHA-256: `910f0f8c3cfe13fb66a6c2257510c17fb178aed46c5bb70e21fe1f1f78265e4e`
- Source snapshot: `ConceptGhost_v0.35_SOURCE.zip`
- Source ZIP SHA-256: `c0cc0d78c454650baf00522d84879eff9ae744ac94045a00809134054411d2eb`
- Drive frozen folder: https://drive.google.com/drive/folders/1gVLw5iWMMhL-hSIxAKCPuPQ1QEWifSYk
- Workflow: `ConceptGhost_Master_v0.35.json`
- Workflow structure: 42 nodes / 70 links / 9 groups / 7 embedded guide notes
- Functional regression: **129 PASS**
- Release/layout assertions: **36 PASS**
- Bundle inventory verification: **46/46 PASS**

## v0.35 freeze decisions
- MoGe-3 is the only geometry engine in the canonical workflow.
- Historical MoGe-2 routing and Atlas Relief / provider-native MoGe preview branches are removed from the canonical graph.
- PrimaryMesh remains authoritative.
- P1-P6 remain report-only.
- P7 creates geometric-region metadata/overlay only.
- P8 only creates a derived cleanup candidate after explicit artist approval; it never auto-replaces PrimaryMesh.
- Remesh Light/Medium/Strong remain derived-only and default OFF.
- Master/Light/Medium/Strong/P8 candidate terminate in native Save 3D Model preview/download outputs.
- DA3 is retired and absent from the bundle.
- `INSTALL_ALL.bat` installs core + private MoGe-3 + private Depth Pro runtimes.
- Depth Pro runtime/node contract uses the same private embedded Python path.
