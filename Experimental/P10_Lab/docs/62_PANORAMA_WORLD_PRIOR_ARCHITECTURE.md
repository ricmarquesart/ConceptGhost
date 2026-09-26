# P10 Panorama World-Prior Architecture

**Status:** MANDATORY PRODUCTION ARCHITECTURE  
**Effective:** 2026-09-25

## Private source boundary

The implementation-reference material for this lane is private and remains outside GitHub:

`G:\My Drive\ConceptGhost\360\00_ORIGINAL_READ_ONLY`

Do not copy the purchased source content into this repository or release bundles.

## Engineering decision

The panorama path is mandatory, but it is **not** a replacement for the accepted P9 solve.

P9 remains the high-authority reconstruction for the original concept camera and visible source region.

A generated 360 panorama is a mandatory lower-authority **shared world prior** for directions not visible in the concept. Its purpose is to give every later camera path the same hallucinated environment instead of asking independent routes to invent unrelated unseen worlds.

## Projection rule

A 2:1 equirectangular panorama is spherical data, not a normal perspective image.

The existing perspective MoGe path must not consume the flat ERP and interpret its pixels as one pinhole camera.

If panorama-derived depth/proxy geometry is needed:

1. generate/seam-correct the ERP;
2. sample it into ordinary perspective views with known yaw, pitch and FOV around the exact P9 camera center;
3. run perspective geometry/depth only on those rectilinear views;
4. align panorama-derived geometry to P9 where overlap exists;
5. keep panorama-derived geometry lower-confidence until independent multiview evidence supports it.

## Reference-aligned ConceptGhost path

Concept image  
→ exact P9 camera + P9 geometry  
→ generated 360 world prior  
→ seam correction / high-resolution ERP  
→ perspective projections around P9 camera center  
→ optional P9-anchored proxy depth/geometry  
→ persistent camera rails  
→ source/geometry-first control frames  
→ WAN only for unknown/disoccluded pixels  
→ source-preserving composite  
→ extendable multiview dataset  
→ explorable-world proof  
→ useful P9-aligned polygonal reconstruction  
→ protected fusion  
→ Maya.

## Acceptance

Panorama is not optional. Validate the mandatory path on the short-scene high-overlap five-route benchmark:

P9 → 360 world prior → panorama-informed route/control → WAN → source-preserving composite → dataset.

The stage passes only when it preserves the exact original concept-camera result, produces a seamless spherical prior, and gives downstream routes one shared unseen-world context. If quality is insufficient, fix the panorama/source-lock implementation rather than bypassing it.

Gate 8 remains blocked until the explorable-world and useful-surface hard proofs pass.


## Source-lock requirement

The generated panorama must not gain authority over the original concept patch.

1. project the original concept into ERP using the accepted P9 camera/FOV;
2. place the panorama wrap seam behind the original camera when possible;
3. generate/outpaint unknown ERP regions;
4. run seam repair/upscale;
5. composite the exact source concept pixels back into the source ERP patch;
6. verify that re-projecting the ERP through the exact concept camera reproduces the accepted source/P9 view.

Failure of this source-camera regression blocks the panorama lane.
