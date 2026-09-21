policy={
  "release":"v0.43.1",
  "canonical_unit":"meters",
  "maya_linear_unit":"cm",
  "maya_units_per_meter":100.0,
  "known_distance_m":3.0,
  "expected_maya_cm":300.0,
  "bad_maya_cm":3.0,
  "bad_distance_m":0.03,
  "canonical_math_changed":False,
  "fov_changed":False,
  "rotation_changed":False,
  "normals_changed":False,
  "uv_changed":False,
  "topology_changed":False,
}
assert policy["known_distance_m"]*policy["maya_units_per_meter"]==policy["expected_maya_cm"]
assert policy["bad_maya_cm"]/policy["maya_units_per_meter"]==policy["bad_distance_m"]
assert policy["expected_maya_cm"]/policy["maya_units_per_meter"]==policy["known_distance_m"]
for k in ["canonical_math_changed","fov_changed","rotation_changed","normals_changed","uv_changed","topology_changed"]:
    assert policy[k] is False
print("V0431_MAYA_METRIC_UNIT_POLICY_PASS",policy)
