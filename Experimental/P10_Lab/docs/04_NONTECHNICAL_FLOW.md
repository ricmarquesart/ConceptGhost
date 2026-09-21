# P10-Lab — Nontechnical Flow

There are now two branches.

The normal **Baseline** branch continues exactly as it is.

The **Refined Solver Fusion** branch first runs P9. P9 is intentionally the same as Baseline, so up to that point both branches should produce the same scene. Only after that does the refined branch continue into P10.

P10 creates a virtual camera that automatically moves a little left, right and forward. The user does not fly it. When the camera moves, it exposes places the original image could never see: the back of a tree, a missing wall behind it, or distorted stairs hidden by a railing.

The system marks which pixels are already known and which ones are missing. A generation model watches the camera movement and imagines only the missing areas. Good original pixels remain protected.

These newly generated views are then treated like extra photographs of the same scene. The system compares them, rebuilds new 3D points and creates additional mesh geometry.

The new geometry is returned to the P9 coordinate system, which should be the same coordinate system as Baseline. Reliable P9/Baseline geometry remains untouched; new geometry fills unseen areas; the seam is locally cleaned.

The program also repairs nearby defects such as stretched triangles, floating pieces and noisy geometry.

Finally, the original ConceptGhost camera is restored and used as a regression check. If the completion damages the concept-art view, the P10 result is rejected and the untouched P9 result remains available. The separate Baseline branch also remains unchanged.

The successful refined result is still a normal editable Maya scene. The temporary panoramic frames, virtual-camera videos and reconstruction files are internal steps rather than manual user operations.

In simple form:

`Baseline branch: image → Baseline → Maya`

`Refined Solver Fusion: image → P9 (= Baseline) → P10 → refined Maya`
