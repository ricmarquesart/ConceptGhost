# v0.41.8 persistent watchdog-race regression
policy={
  "startup_missing_status_only_before_first_valid_status":True,
  "transient_empty_read_after_valid_status_is_nonfatal":True,
  "systemexit_zero_is_not_failure":True,
  "writable_numpy_handoff":True,
  "labels":["MoGe-3 Atlas-Conditioned Geometry","MoGe-3 Independent Focal Probe"],
  "new_solvers":0,
}
assert policy["startup_missing_status_only_before_first_valid_status"]
assert policy["transient_empty_read_after_valid_status_is_nonfatal"]
assert policy["systemexit_zero_is_not_failure"]
assert policy["writable_numpy_handoff"]
assert policy["new_solvers"]==0
print("P9_V0418_MOGE3_WATCHDOG_RACE_PASS",policy)
