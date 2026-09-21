policy={
 "baseline":"Baseline v0.42 Frozen",
 "refined":"Refined Solver — Baseline Clone",
 "branches_identical":True,
 "remesh":["Light","Medium","Strong"],
 "artist_output":"Primary Master only",
 "fov_modes":["AUTO","MANUAL"],
 "manual_fov_default_deg":50.0,
 "run_parameters":True,
 "active_p9_solver_fusion_nodes":0,
 "registered_retired_p9_nodes":0,
 "nodes":76,
 "links":145,
 "groups":17,
 "node_overlap_60px":0,
 "group_overlap":0,
 "bundle_sha256":"c76d6b667b0402acc99b0a5f2af446c4573af73be9f6b9c005daafb6aaf0f68a",
 "workflow_sha256":"76bfb11a86ac37f0403bf216f16084422be60e2f3a6a10fc31749d62227f834e",
}
assert policy["branches_identical"] is True
assert policy["artist_output"]=="Primary Master only"
assert policy["fov_modes"]==["AUTO","MANUAL"]
assert policy["manual_fov_default_deg"]==50.0
assert policy["run_parameters"] is True
assert policy["active_p9_solver_fusion_nodes"]==0
assert policy["registered_retired_p9_nodes"]==0
assert policy["node_overlap_60px"]==0
assert policy["group_overlap"]==0
print("V042_FROZEN_BASELINE_RESET_POLICY_PASS",policy)
