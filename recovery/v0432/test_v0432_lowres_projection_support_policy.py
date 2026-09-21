policy={
 "release":"v0.43.2",
 "node":"ConceptGhostMoGeProjectionSupport",
 "helper_parameter":"discontinuity_threshold",
 "bad_free_name":"low_resolution_projection_threshold",
 "high_fidelity_threshold":0.0,
 "low_resolution_default_threshold":0.20,
 "solver_math_changed":False,
 "profile_policy_changed":False,
 "manual_metric_math_changed":False,
 "maya_metric_v0431_preserved":True,
}
assert policy["helper_parameter"]=="discontinuity_threshold"
assert policy["high_fidelity_threshold"]==0.0
assert policy["low_resolution_default_threshold"]>0.0
assert policy["solver_math_changed"] is False
assert policy["profile_policy_changed"] is False
assert policy["manual_metric_math_changed"] is False
assert policy["maya_metric_v0431_preserved"] is True
print("V0432_LOW_RES_PROJECTION_SUPPORT_POLICY_PASS",policy)
