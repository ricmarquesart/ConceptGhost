# ConceptGhost v0.17.2 — Hero Mesh / Camera / FBX / UV snapshot

This directory archives the complete portable ConceptGhost v0.17.2 revision.

Key corrections:
- exact source-image aspect / Maya camera framing contract;
- verified FBX camera round-trip;
- separate ComfyUI preview UV vs Maya/DCC UV path;
- E2-DCC authored as `CG_HERO_MESH` inside the official `.ma` scene;
- official FBX includes both ConceptGhost cameras plus `CG_HERO_MESH`.

Portable ZIP is stored on Google Drive. The exact project tree is also stored here as an XZ-compressed tar encoded into ordered Base64 parts under `tar_xz_parts/`.

## Restore from GitHub
Run `RESTORE_BUNDLE.bat`. It concatenates the parts, decodes Base64, verifies SHA-256, and extracts the full package directory.

Verification before publication:
- pytest: 94 passed
- compileall: passed
- snapshot manifest: 92 entries, 0 mismatches

Portable ZIP SHA-256: `85afee8525bd23bb42acbb424ffbbbd626a11e8f4edc1a226671040fc9fc7f0f`
GitHub tar.xz SHA-256: `41c468d86bbf736ea73b634c03a31990512350f8398b0ef0f17890784c0c29c3`
