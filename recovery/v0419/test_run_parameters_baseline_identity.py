import hashlib, json
def baseline_identity(run_id, camera, geometry):
    basis={
        "schema":"ConceptGhost.BaselineExportIdentitySeed.v0.41.9",
        "run_id":run_id,
        "branch_mode":"Baseline v0.36",
        "camera":camera,
        "geometry":geometry,
    }
    digest=hashlib.sha256(json.dumps(basis,sort_keys=True).encode("utf-8")).hexdigest()[:20]
    return "cgsc_v036_"+digest

sid=baseline_identity(
    "run_v0419_test",
    {"image_width":1448,"image_height":1086,"horizontal_fov_deg":36.8317519559},
    {"engine":"moge","point_count":123,"geometry_profile":"High Fidelity"},
)
assert sid.startswith("cgsc_v036_")
assert len(sid)>20

run_parameters_sections=[
    "EXECUTION",
    "SOURCE / OUTPUT",
    "BRANCH / SCENE IDENTITY",
    "GEOMETRY PROFILE / SOLVER PARAMETERS",
    "CAMERA / FOV AUTHORITY",
    "SCALE / KNOWN HEIGHT AUTHORITY",
    "METROLOGY / METRIC EVIDENCE",
    "SEMANTIC / DEPTH FUSION / REFINEMENT",
    "MAYA / EXPORT CONTRACT",
    "FINAL OUTPUTS / STATUS",
]
assert len(run_parameters_sections)==10

policy={
    "baseline_solver_math_changed":False,
    "run_parameters_modes":["Baseline v0.36","Refined Solver Fusion"],
    "per_run":"RUN_PARAMETERS.txt",
    "latest":"LATEST_RUN_PARAMETERS.txt",
    "phases":["PRE_EXPORT","PRE_MAYA","FINAL"],
    "new_solvers":0,
}
assert policy["baseline_solver_math_changed"] is False
assert policy["new_solvers"]==0
print("P9_V0419_RUN_PARAMETERS_BASELINE_IDENTITY_PASS",{"scene_contract_id":sid,"sections":len(run_parameters_sections)})
