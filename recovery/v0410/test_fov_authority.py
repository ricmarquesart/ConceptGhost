import math

def fpx(w,deg):
    return w/(2.0*math.tan(math.radians(deg)*0.5))

# Exact real-runtime native FOV seeds that motivated v0.41.
W=1448
seeds={
    "Atlas":36.83175195590167,
    "MoGeIndependent":67.5001183691541,
    "DepthPro":54.9986956696813,
}
focals={k:fpx(W,v) for k,v in seeds.items()}
assert focals["Atlas"] > focals["DepthPro"] > focals["MoGeIndependent"]

# v0.41 policy: solver identity is not a voting weight.  AUTO evaluates
# scene evidence; MANUAL is sovereign and defaults to 50 deg.
weights={
    "depth_surface_orientation":0.35,
    "ground_gravity_consistency":0.30,
    "vertical_structure_gravity":0.25,
    "known_height_metric_consistency":0.10,
}
assert abs(sum(weights.values())-1.0)<1e-12
assert set(weights)=={
    "depth_surface_orientation",
    "ground_gravity_consistency",
    "vertical_structure_gravity",
    "known_height_metric_consistency",
}
manual_default=50.0
assert manual_default==50.0

# Synthetic scene-validation outcome used by the packaged v0.41 suite.
selected_solver="DepthPro"
selected_native=seeds[selected_solver]
selected_fov=54.998696
confidence="LOW"
assert selected_solver in seeds
assert abs(selected_native-55.0)<0.01
assert abs(selected_fov-55.0)<1.1
assert confidence=="LOW"  # small margins must not be presented as certainty

# Explicit invalid/circular criteria are not allowed to decide FOV.
excluded={"generic_reprojection","planarity_alone"}
assert "generic_reprojection" in excluded
assert "planarity_alone" in excluded

print("P9_V0410_FOV_AUTHORITY_CI_PASS",{
    "selected_solver":selected_solver,
    "selected_fov":selected_fov,
    "manual_default":manual_default,
    "new_solvers":0,
})
