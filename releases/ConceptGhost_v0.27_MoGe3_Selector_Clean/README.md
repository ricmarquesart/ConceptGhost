# ConceptGhost v0.27 — MoGe-3 Selector Clean

Release purpose:
- remove stale SAM/Semantic controls caused by duplicate ConceptGhost Stage68 backup packages;
- archive duplicate `ConceptGhost_Stage68*` packages outside ComfyUI rather than deleting them;
- add a real lazy `moge_version = MoGe-2 | MoGe-3` route to MASTER CONTROLS;
- run MoGe-3 out-of-process in `%LOCALAPPDATA%\ConceptGhost-MoGeRuntime-v1`;
- keep MoGe-2, Single View, Multi View/Trellis and the shared ComfyUI Python/Torch environment untouched;
- prevent harmless native stderr from appearing as PowerShell 5.1 `NativeCommandError` during the private runtime installer.

Validation:
- complete package: 13/13 pytest PASS;
- source package: 12/12 PASS, with only the intentionally absent pinned vendor ZIP test deselected;
- workflow: 33 nodes / 85 links, zero dangling/backlink mismatches;
- active Semantic/SAM tokens: zero;
- v0.25 winding and face-vertex-normal regression preserved.

Google Drive complete package:
https://drive.google.com/file/d/16lcFjST1n6SRN7a9rAv9kHlOhU3LpNui/view?usp=drivesdk

Google Drive release folder:
https://drive.google.com/drive/folders/1ek5BKYhtlQIZPror6deZbzEh9NgI7t4I

SHA256:
- COMPLETE: 86cae028cf14bb386a93e708de4af9c1fe3a0bd6d7005fb8b6f65dd57d677c99
- SOURCE: 05682b1e3229e4a56f085923343929aeea3148d607b58f82b65061ca0c86aaeb

The exact text-source delta from the v0.26 source snapshot is stored in this directory as a gzip+base64 patch. CI reconstructs v0.27 from the committed v0.26 source ZIP and applies that patch before testing.
