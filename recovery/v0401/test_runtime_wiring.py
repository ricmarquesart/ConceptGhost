import json

# Minimal persisted workflow fragment from v0.40.1 canonical workflow.
workflow={
  "last_link_id":241,
  "nodes":[
    {"id":1005,"type":"ConceptGhostCameraRouter","outputs":[
      {"name":"camera_bundle","links":[131,192,204]},
      {"name":"camera_report","links":[]},
      {"name":"atlas_fov_x_deg","links":[241]}
    ]},
    {"id":1011,"type":"ConceptGhostMoGeEvidence","inputs":[
      {"name":"moge_geometry","link":94},
      {"name":"source_image","link":81},
      {"name":"preset","link":85},
      {"name":"atlas_fov_x_deg","link":241},
      {"name":"profile_config","link":116}
    ]}
  ],
  "links":[[241,1005,2,1011,3,"FLOAT"]]
}
nodes={n["id"]:n for n in workflow["nodes"]}
link=workflow["links"][0]
assert link==[241,1005,2,1011,3,"FLOAT"]
assert nodes[1005]["outputs"][2]["name"]=="atlas_fov_x_deg"
assert 241 in nodes[1005]["outputs"][2]["links"]
assert nodes[1011]["inputs"][3]["name"]=="atlas_fov_x_deg"
assert nodes[1011]["inputs"][3]["link"]==241
print("P9_V0401_RUNTIME_WIRING_PASS",{"link_id":241})
