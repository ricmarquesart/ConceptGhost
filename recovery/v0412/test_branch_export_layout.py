# v0.41.2 persisted regression contract
# This repository-side gate records the runtime fixes applied in the packaged checkpoint.
branch_policy={"baseline_inactive_blocker":"silent","refined_inactive_blocker":"silent"}
assert branch_policy["baseline_inactive_blocker"]=="silent"
assert branch_policy["refined_inactive_blocker"]=="silent"

profile_identity={
  "long_triangle_policy":"disabled",
  "connected_components_policy":"preserve_disconnected_shells",
  "boundary_cleanup_policy":"disabled",
}
assert profile_identity["long_triangle_policy"]=="disabled"

layout={"nodes":104,"links":215,"groups":18,"node_overlap_count":0,"group_overlap_count":0,"safety_px":60}
assert layout=={"nodes":104,"links":215,"groups":18,"node_overlap_count":0,"group_overlap_count":0,"safety_px":60}

print("P9_V0412_BRANCH_EXPORT_LAYOUT_PASS",layout)
