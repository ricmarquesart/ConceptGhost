# ConceptGhost v1.54 P10 — Gate 3 Preview r1

## Purpose

This preview proves the temporary panorama and authority boundary before any WAN
generation is introduced.

The workflow contains:

1. P10 P9 Completion Bundle Builder
2. P10 P9 Bundle Loader / Validator
3. P10 Temporary Panorama / Authority Preview

The Panorama node displays three previews directly in ComfyUI:

- **temporary panorama** — source pixels projected through the canonical P9
  camera into a 2:1 equirectangular canvas; unknown pixels remain black;
- **source-lock mask** — white means observed/authoritative and cannot be
  generated over;
- **generation-candidate mask** — white means unknown *and* inside the bounded
  local completion envelope.

No image generation happens in Gate 3.

## Expected real v1.53 reference behavior

For the real validation run 20260921T194812_539232Z_366c63df at 2048×1024:

- source camera HFOV ≈ 36.83175 degrees;
- source camera VFOV ≈ 28.04257 degrees;
- observed/source-lock fraction ≈ 1.57%;
- local generation-candidate fraction ≈ 20.67%;
- PrimaryMesh-derived characteristic radius ≈ 70.27 canonical units.

These values are diagnostics, not editable camera/scale overrides.

## Test rule

Do not use this Gate 3 preview to bypass an unresolved Gate 2 runtime failure.
Gate 3 can be prepared in parallel, but its runtime acceptance depends on the
Gate 2 boundary working in the user's real ComfyUI Desktop installation.

## Acceptance

Gate 3 visual runtime acceptance requires:

- Builder PASS;
- Loader PASS;
- Panorama node PASS;
- source image appears centered in the ERP without mirror/flip;
- source-lock covers exactly the observed source projection;
- candidate mask never overlaps source-lock;
- no source pixels are generated or altered;
- no rear-hemisphere/world-scale candidate region appears.
