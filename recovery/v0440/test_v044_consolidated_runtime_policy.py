policy={
 "release":"v0.44.0",
 "consolidated_runtime":True,
 "manual_metric_authority":True,
 "maya_units_per_meter":100.0,
 "lowres_projection_support_fixed":True,
 "legacy_workflows_packaged":False,
 "retired_p9_runtimes_packaged":False,
 "moge_quality_reduced":False,
 "workflow":{"nodes":77,"links":146,"groups":17},
}
assert policy["maya_units_per_meter"]==100.0
assert policy["lowres_projection_support_fixed"] is True
assert policy["legacy_workflows_packaged"] is False
assert policy["retired_p9_runtimes_packaged"] is False
assert policy["moge_quality_reduced"] is False
assert policy["workflow"]=={"nodes":77,"links":146,"groups":17}
print("V044_CONSOLIDATED_RUNTIME_POLICY_PASS",policy)
