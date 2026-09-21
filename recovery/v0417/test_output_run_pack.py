from pathlib import Path
import tempfile

def branch_scene_name(scene_name, selected_branch):
    return str(scene_name), ("refined_fusion" if selected_branch=="Refined Solver Fusion" else "baseline_v036")

for branch in ["Baseline v0.36","Refined Solver Fusion"]:
    scene,slug=branch_scene_name("concept_scene",branch)
    assert scene=="concept_scene"
assert branch_scene_name("concept_scene","Baseline v0.36")[1]=="baseline_v036"
assert branch_scene_name("concept_scene","Refined Solver Fusion")[1]=="refined_fusion"

required={"acceptance","benchmark","camera","diagnostics","geometry","logs","maya","meshes","package","source","validation"}
with tempfile.TemporaryDirectory() as td:
    root=Path(td)/"ConceptGhost_Output"/"concept_scene"
    run=root/"20260921T000000_000000Z_deadbeef"
    for rel in required:
        (run/rel).mkdir(parents=True,exist_ok=True)
    assert required.issubset({p.name for p in run.iterdir() if p.is_dir()})
    ma=run/"maya"/"ConceptGhost_concept_scene_Ghost.ma"
    ma.write_text("// Maya ASCII",encoding="utf-8")
    (root/"LATEST_RUN.txt").write_text(str(run),encoding="utf-8")
    (root/"LATEST_MAYA_SCENE.txt").write_text(str(ma),encoding="utf-8")
    assert Path((root/"LATEST_MAYA_SCENE.txt").read_text()).name=="ConceptGhost_concept_scene_Ghost.ma"

official=[
 "maya/ConceptGhost_concept_scene_Ghost.ma",
 "maya/ConceptGhost_concept_scene_Ghost.fbx",
 "maya/ConceptGhost_concept_scene_GhostFullScene.fbx",
 "maya/ConceptGhost_concept_scene_CameraOnly.fbx",
 "maya/ConceptGhost_concept_scene_PrimaryMesh.npz",
 "camera/camera.json",
 "geometry/canonical/pointcloud.ply",
 "geometry/canonical/pointcloud.usda",
 "manifest.json",
 "output_index.json",
]
assert len(official)==10
print("P9_V0417_OUTPUT_RUN_PACK_PASS",{"scene_root":"concept_scene","official_core":len(official),"new_solvers":0})
