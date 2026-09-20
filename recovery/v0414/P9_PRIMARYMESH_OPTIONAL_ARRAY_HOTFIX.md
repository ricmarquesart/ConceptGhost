# ConceptGhost v0.41.4 — PrimaryMesh optional-array runtime hotfix

Observed on Baseline v0.36 export:

`TypeError: len() of unsized object`

Root cause:
optional canonical attributes may be scalar summary values or `None` on some branches. The PrimaryMesh exporter converted them with `np.asarray(...)` and then called `len(...)`; 0-D numpy arrays have no length.

v0.41.4 rule:
- optional canonical attributes are treated as per-point data only when `ndim >= 1` and `shape[0] == canonical_point_count`;
- scalar / 0-D / `None` values remain metadata and are skipped from per-vertex payloads;
- correctly aligned arrays continue to propagate unchanged;
- no broadcasting of scalar metadata into vertices.

Affected optional fields include:
`source_pixel_id`, `camera_depth`, `geometric_boundary_strength`, `confidence`, `normal_confidence`, `semantic_macro_class_id`, and `semantic_instance_id`.

v0.41.3 Maya camera-signature fix is retained.
New solvers: 0.
Bundle SHA-256: `d5547e02a936fffd42b1e0f7ec69e3cbc09887f36da472905c464b298f0598b9`.
