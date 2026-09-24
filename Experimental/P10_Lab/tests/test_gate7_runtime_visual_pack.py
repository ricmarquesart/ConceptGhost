import json
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image
except ImportError:
    Image = None


def _write_mesh(path: Path):
    vertices=[
        (-0.8,-0.8,4.0),(0.8,-0.8,4.0),(0.8,0.8,4.0),(-0.8,0.8,4.0),
        (-0.5,-0.5,5.0),(0.5,-0.5,5.0),(0.5,0.5,5.0),(-0.5,0.5,5.0),
    ]
    faces=[
        (0,1,2),(0,2,3),(4,5,6),(4,6,7),
        (0,1,5),(0,5,4),(1,2,6),(1,6,5),
    ]
    lines=[
        "ply","format ascii 1.0",
        f"element vertex {len(vertices)}",
        "property float x","property float y","property float z",
        f"element face {len(faces)}",
        "property list uchar int vertex_indices","end_header",
    ]
    lines.extend(f"{x} {y} {z}" for x,y,z in vertices)
    lines.extend(f"3 {a} {b} {c}" for a,b,c in faces)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("\n".join(lines)+"\n",encoding="ascii")


def _write_candidate(path: Path):
    vertices=[
        (-0.8,-0.8,4.0,1,1,0.95),(0.8,-0.8,4.0,1,1,0.95),
        (0.8,0.8,4.0,1,2,0.62),(-0.8,0.8,4.0,1,2,0.62),
        (-0.4,-0.4,5.0,2,3,0.82),(0.4,-0.4,5.0,2,3,0.82),
        (0.4,0.4,5.0,2,3,0.82),(-0.4,0.4,5.0,2,3,0.82),
    ]
    faces=[
        (0,1,2,1,1),(0,2,3,1,1),
        (4,5,6,2,3),(4,6,7,2,3),
    ]
    lines=[
        "ply","format ascii 1.0",
        "element vertex 8",
        "property float x","property float y","property float z",
        "property uchar cg_layer","property uchar cg_provenance",
        "property float cg_confidence",
        "element face 4",
        "property list uchar int vertex_indices",
        "property uchar cg_layer","property uchar cg_provenance",
        "end_header",
    ]
    lines.extend(
        f"{x} {y} {z} {layer} {prov} {conf}"
        for x,y,z,layer,prov,conf in vertices
    )
    lines.extend(
        f"3 {a} {b} {c} {layer} {prov}"
        for a,b,c,layer,prov in faces
    )
    path.write_text("\n".join(lines)+"\n",encoding="ascii")


class Gate7RuntimeNodeContractTests(unittest.TestCase):
    def test_nodes_are_registered_as_separate_runtime_and_terminal_visual_branch(self):
        import p10_lab

        self.assertIn("ConceptGhostP10Gate7Runtime",p10_lab.NODE_CLASS_MAPPINGS)
        self.assertIn("ConceptGhostP10Gate7VisualEvidencePack",p10_lab.NODE_CLASS_MAPPINGS)
        runtime=p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10Gate7Runtime"]
        visual=p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10Gate7VisualEvidencePack"]
        self.assertEqual(runtime.CATEGORY,"ConceptGhost/P10 Refined")
        self.assertEqual(visual.CATEGORY,"ConceptGhost/P10 Visual Evidence")
        self.assertTrue(runtime.OUTPUT_NODE)
        self.assertTrue(visual.OUTPUT_NODE)
        self.assertTrue(
            runtime.INPUT_TYPES()["required"]["reconstruction_runtime_manifest_path"][1]["forceInput"]
        )
        self.assertTrue(
            visual.INPUT_TYPES()["required"]["gate7_runtime_manifest_path"][1]["forceInput"]
        )

    def test_runtime_source_never_promotes_gate8(self):
        import p10_lab.gate7_runtime as runtime
        source=Path(runtime.__file__).read_text(encoding="utf-8")
        self.assertIn('"gate8_promotion": False',source)
        self.assertIn('"ready_for_gate8": False',source)
        self.assertIn("ARTIST_VISUAL_REVIEW_REQUIRED",source)
        self.assertIn("DR9R_R15_RUNTIME_UX_ACCEPTANCE_REQUIRED",source)


    def test_runtime_self_heals_incomplete_dense_geometric_evidence(self):
        import p10_lab.gate7_runtime as runtime

        source=Path(runtime.__file__).read_text(encoding="utf-8")
        for token in (
            "G7_0_DENSE_GEOMETRIC_PREFLIGHT",
            "_repair_gate6_dense_evidence_for_gate7",
            "repair_dense_geometric_evidence",
            "REPAIRED_FOR_GATE7_GEOMETRIC_COVERAGE",
            "AUTO_REPAIR_EXPLICIT_REGISTERED_REFERENCES_IF_BELOW_70_PERCENT",
            "sparse_rebuilt",
            "wan_rebuilt",
        ):
            self.assertIn(token,source)
        self.assertIn('"p9_authority_changed":False',source)


class Gate7VisualPackTests(unittest.TestCase):
    @unittest.skipIf(np is None or Image is None,"NumPy/Pillow unavailable")
    def test_visual_pack_outputs_every_gate_and_keeps_promotion_blocked(self):
        from p10_lab.gate7_visual_pack import build_gate7_visual_evidence_pack

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            scene,p9,attempt="scene-1","p9-1","attempt-1"

            before_mesh=root/"pre_fusion_mesh.ply"
            candidate=root/"protected_fusion_candidate.ply"
            _write_mesh(before_mesh)
            _write_candidate(candidate)

            sparse=root/"dataset"/"sparse"/"known"
            sparse.mkdir(parents=True)
            (sparse/"cameras.txt").write_text(
                "1 PINHOLE 640 360 450 450 320 180\n",encoding="utf-8"
            )
            frames=[
                {"camera_id":1,"global_frame_index":0,"path_name":"drone_a","qvec":[1,0,0,0],"tvec":[0,0,0]},
                {"camera_id":1,"global_frame_index":1,"path_name":"drone_a","qvec":[1,0,0,0],"tvec":[-0.1,0,0]},
                {"camera_id":1,"global_frame_index":2,"path_name":"drone_b","qvec":[1,0,0,0],"tvec":[0.1,0,0]},
            ]
            dataset=root/"dataset"/"dataset_manifest.json"
            dataset.parent.mkdir(parents=True,exist_ok=True)
            dataset.write_text(json.dumps({
                "schema":"ConceptGhost.P10KnownCameraColmapDataset.v0.2",
                "run_id":p9,"scene_contract_id":scene,
                "camera_authority":"P9_BASELINE_WORLD_DERIVED",
                "known_sparse_model_dir":str(sparse.resolve()),
                "frames":frames,
            }),encoding="utf-8")

            registration=root/"registration.json"
            registration.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7Registration.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "registration_policy":"KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION",
                "scale":1.0,"sim3_refit_allowed":False,"p9_authority_changed":False,
                "dataset_manifest_path":str(dataset.resolve()),
                "pre_fusion_mesh_path":str(before_mesh.resolve()),
            }),encoding="utf-8")

            p9_points=np.asarray([
                [-0.8,-0.8,4],[0.8,-0.8,4],[0.8,0.8,4],[-0.8,0.8,4]
            ],dtype=np.float32)
            p10_points=np.asarray([
                [-0.4,-0.4,5],[0.4,-0.4,5],[0.4,0.4,5],[-0.4,0.4,5]
            ],dtype=np.float32)
            prov_npz=root/"provenance.npz"
            np.savez_compressed(
                prov_npz,
                p9_points=p9_points,
                p9_labels=np.asarray([1,1,2,2],dtype=np.uint8),
                p10_points=p10_points,
                p10_labels=np.asarray([3,3,4,6],dtype=np.uint8),
            )
            provenance=root/"provenance.json"
            provenance.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7Provenance.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "official_geometry_changed":False,
                "evidence_npz_path":str(prov_npz.resolve()),
            }),encoding="utf-8")

            confidence_npz=root/"confidence.npz"
            np.savez_compressed(
                confidence_npz,
                p10_points=p10_points,
                p10_confidence=np.asarray([0.9,0.7,0.3,0.12],dtype=np.float32),
            )
            confidence=root/"confidence.json"
            confidence.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7GeometryConfidence.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "geometry_confidence_refine":False,"official_geometry_changed":False,
                "evidence_npz_path":str(confidence_npz.resolve()),
            }),encoding="utf-8")

            overlay_npz=root/"overlay.npz"
            np.savez_compressed(
                overlay_npz,
                p10_points=p10_points,
                p10_confidence_after_free_space=np.asarray([0.9,0.18,0.05,0.12],dtype=np.float32),
            )
            overlay=root/"overlay.json"
            overlay.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7ConfidenceFreeSpaceOverlay.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "evidence_npz_path":str(overlay_npz.resolve()),
            }),encoding="utf-8")

            free_npz=root/"free.npz"
            np.savez_compressed(
                free_npz,
                voxel_centers=np.asarray([
                    [-0.2,0,4.5],[0.2,0,4.5],[0,0.3,4.5],[0,-0.3,4.5]
                ],dtype=np.float32),
                state=np.asarray([1,2,3,0],dtype=np.uint8),
                free_effective_votes=np.asarray([0,5,2,1],dtype=np.int16),
                occupied_effective_votes=np.asarray([4,0,2,0],dtype=np.int16),
            )
            free=root/"free.json"
            free.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "official_geometry_changed":False,
                "constraints_npz_path":str(free_npz.resolve()),
            }),encoding="utf-8")

            fusion=root/"fusion.json"
            fusion.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7ProtectedFusionCandidate.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "candidate_ply_path":str(candidate.resolve()),
                "candidate_is_official_geometry":False,"official_geometry_changed":False,
                "p9_policy":{"all_p9_faces_copied_unchanged":True,"p9_faces_removed":0,"p9_vertices_moved":0},
            }),encoding="utf-8")

            review_png=root/"review.png"
            Image.new("RGB",(800,600),(28,30,34)).save(review_png)
            review=root/"review.json"
            review.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7VisualReview.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "candidate_is_official_geometry":False,"official_geometry_changed":False,
                "preview_png_path":str(review_png.resolve()),
            }),encoding="utf-8")

            runtime=root/"runtime.json"
            runtime.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7Runtime.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "ready_for_visual_evidence_pack":True,
                "artifacts":{
                    "registration_manifest_path":str(registration.resolve()),
                    "provenance_manifest_path":str(provenance.resolve()),
                    "confidence_manifest_path":str(confidence.resolve()),
                    "free_space_constraints_manifest_path":str(free.resolve()),
                    "confidence_free_space_overlay_manifest_path":str(overlay.resolve()),
                    "protected_fusion_manifest_path":str(fusion.resolve()),
                    "visual_review_manifest_path":str(review.resolve()),
                },
            }),encoding="utf-8")

            result=build_gate7_visual_evidence_pack(runtime,root/"visual")
            self.assertEqual(result["status"],"PASS")
            self.assertEqual(set(result["visual_evidence_manifests"]),{
                "G7.1","G7.2","G7.2C","G7.3","G7.4","G7.5","G7.6"
            })
            for path in result["visual_evidence_manifests"].values():
                self.assertTrue(Path(path).is_file())
            for key,path in result["key_outputs"].items():
                self.assertTrue(Path(path).is_file(),key)
            self.assertFalse(result["promotion"]["gate7_accepted"])
            self.assertFalse(result["promotion"]["ready_for_gate8"])
            self.assertTrue(result["terminal_visual_branch"])
            self.assertFalse(result["feeds_geometry_pipeline"])


if __name__=="__main__":
    unittest.main()
