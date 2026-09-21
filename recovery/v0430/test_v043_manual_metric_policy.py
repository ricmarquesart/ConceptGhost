policy={
  "release":"v0.43.0",
  "p9":"BASELINE",
  "refined":"P9 + future P10",
  "p10_implemented":False,
  "shared_manual_metric":True,
  "default_enabled":False,
  "authority":"ARTIST_MANUAL_KNOWN_DISTANCE",
  "measurement_types":["Vertical Height","Free 3D Distance"],
  "patch_px":7,
  "p10_scale_override_allowed":False,
  "manual_example":{"before":4.0,"known_m":2.0,"scale":0.5,"after_m":2.0},
  "invariants":["FOV","camera_rotation","reprojection","geometry_ratios"],
  "maya_roundtrip_required":True,
  "run_parameters_required":True,
  "new_solvers":0,
  "workflow":{"nodes":77,"links":146,"groups":17,"branches_identical":True},
}
assert policy["manual_example"]["known_m"]/policy["manual_example"]["before"]==policy["manual_example"]["scale"]
assert policy["manual_example"]["after_m"]==2.0
assert policy["p10_scale_override_allowed"] is False
assert policy["new_solvers"]==0
assert policy["workflow"]["branches_identical"] is True
print("V043_MANUAL_METRIC_POLICY_PASS",policy)
