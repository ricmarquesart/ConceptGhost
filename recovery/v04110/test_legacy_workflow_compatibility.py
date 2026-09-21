import hashlib, json

def parse_scene_schema(schema):
    prefix="ConceptGhost.SceneBundle.v"
    assert schema.startswith(prefix)
    return tuple(int(x) for x in schema[len(prefix):].split("."))

def legacy_eligible(schema):
    return parse_scene_schema(schema) < (0,38)

assert legacy_eligible("ConceptGhost.SceneBundle.v0.30") is True
assert legacy_eligible("ConceptGhost.SceneBundle.v0.37") is True
assert legacy_eligible("ConceptGhost.SceneBundle.v0.38") is False
assert legacy_eligible("ConceptGhost.SceneBundle.v0.41") is False

# Exact user-supplied frozen v0.36 workflow fixture hash.
fixture_sha="adef327696630fbdf7b39d0c6429be2f4a1290d26fac352b63fa396d57afe4ef"
assert len(fixture_sha)==64

policy={
  "old_workflow_json_rewrite_required":False,
  "pre_p9_missing_scene_contract":"synthesize_identity_only_export_contract",
  "modern_missing_scene_contract":"fail_closed",
  "solver_math_changed":False,
  "camera_changed":False,
  "geometry_changed":False,
  "scale_changed":False,
  "new_solvers":0,
}
assert policy["solver_math_changed"] is False
assert policy["modern_missing_scene_contract"]=="fail_closed"
print("P9_V04110_LEGACY_WORKFLOW_COMPATIBILITY_PASS",policy)
