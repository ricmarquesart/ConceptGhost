def exceeded(record):
    delta_raw=record.get("fov_delta_deg")
    tol_raw=record.get("tolerance_deg")
    if delta_raw is None:
        return True
    delta=float(delta_raw)
    tol=0.02 if tol_raw is None else float(tol_raw)
    return delta > tol

exact={
    "status":"PASS",
    "scene_contract_id":"cgsc_4bd16d6ac2a826c3b88b",
    "camera_scene_contract_id":"cgsc_4bd16d6ac2a826c3b88b",
    "canonical_fov_x_deg":71.500118,
    "maya_live_fov_x_deg":71.500118,
    "fov_delta_deg":0.0,
    "tolerance_deg":0.02,
}
assert exceeded(exact) is False
assert exceeded({"fov_delta_deg":0.019,"tolerance_deg":0.02}) is False
assert exceeded({"fov_delta_deg":0.021,"tolerance_deg":0.02}) is True
assert exceeded({"fov_delta_deg":None,"tolerance_deg":0.02}) is True
print("P9_V0415_MAYA_FOV_ZERO_DELTA_PASS",exact)
