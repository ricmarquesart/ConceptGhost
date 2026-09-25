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


def _write_tri_mesh(path: Path):
    lines = [
        "ply",
        "format ascii 1.0",
        "element vertex 6",
        "property float x",
        "property float y",
        "property float z",
        "element face 2",
        "property list uchar int vertex_indices",
        "end_header",
        "0 0 0",
        "1 0 0",
        "0 1 0",
        "3 0 0",
        "4 0 0",
        "3 1 0",
        "3 0 1 2",
        "3 3 4 5",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _write_candidate(path: Path):
    # Two P9 faces and one accepted P10 face.
    vertices = [
        (0,0,0,1,1,0.95),
        (1,0,0,1,1,0.95),
        (0,1,0,1,1,0.95),
        (1,1,0,1,2,0.62),
        (3,0,0,2,3,0.82),
        (4,0,0,2,3,0.82),
        (3,1,0,2,3,0.82),
    ]
    faces = [
        (0,1,2,1,1),
        (1,3,2,1,1),
        (4,5,6,2,3),
    ]
    lines = [
        "ply",
        "format ascii 1.0",
        "comment ConceptGhost Gate 7.4 protected fusion candidate",
        f"element vertex {len(vertices)}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar cg_layer",
        "property uchar cg_provenance",
        "property float cg_confidence",
        f"element face {len(faces)}",
        "property list uchar int vertex_indices",
        "property uchar cg_layer",
        "property uchar cg_provenance",
        "end_header",
    ]
    lines.extend(
        f"{x} {y} {z} {layer} {prov} {confidence}"
        for x,y,z,layer,prov,confidence in vertices
    )
    lines.extend(
        f"3 {a} {b} {c} {layer} {prov}"
        for a,b,c,layer,prov in faces
    )
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


class Gate7VisualReviewTests(unittest.TestCase):
    def _fixture(self, root: Path):
        candidate = root / "protected_fusion_candidate.ply"
        _write_candidate(candidate)

        p10 = root / "pre_fusion_mesh.ply"
        _write_tri_mesh(p10)

        face_evidence = root / "protected_fusion_face_provenance.npz"
        np.savez_compressed(
            face_evidence,
            p10_rejected_face_indices=np.asarray([1], dtype=np.int64),
            p10_face_reason_code=np.asarray([0, 1], dtype=np.uint8),
        )

        constraints_npz = root / "free_space_constraints.npz"
        np.savez_compressed(
            constraints_npz,
            voxel_keys=np.asarray([[2,0,0],[5,0,0]], dtype=np.int32),
            voxel_centers=np.asarray([[2.5,0.5,0.5],[5.5,0.5,0.5]], dtype=np.float32),
            state=np.asarray([2,3], dtype=np.uint8),
        )
        constraints = root / "free_space_constraints_manifest.json"
        constraints.write_text(json.dumps({
            "schema":"ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1",
            "status":"PASS",
            "scene_contract_id":"scene-1",
            "p9_run_id":"p9-1",
            "p10_attempt_id":"attempt-1",
            "voxel":{"voxel_size_m":1.0},
            "constraints_npz_path":str(constraints_npz.resolve()),
            "official_geometry_changed":False,
            "p9_authority_changed":False,
            "ready_for_destructive_fusion":False,
        }), encoding="utf-8")

        dataset = root / "dataset_manifest.json"
        dataset.write_text(json.dumps({
            "schema":"ConceptGhost.P10KnownCameraColmapDataset.v0.2",
            "scene_contract_id":"scene-1",
            "run_id":"p9-1",
            "camera_authority":"P9_BASELINE_WORLD_DERIVED",
            "frames":[
                {
                    "global_frame_index":0,
                    "path_name":"drone_a",
                    "qvec":[1,0,0,0],
                    "tvec":[0,0,-5],
                },
                {
                    "global_frame_index":1,
                    "path_name":"drone_b",
                    "qvec":[1,0,0,0],
                    "tvec":[-4,0,-5],
                },
            ],
        }), encoding="utf-8")

        registration = root / "gate7_registration.json"
        registration.write_text(json.dumps({
            "schema":"ConceptGhost.P10Gate7Registration.v0.1",
            "status":"PASS",
            "scene_contract_id":"scene-1",
            "p9_run_id":"p9-1",
            "p10_attempt_id":"attempt-1",
            "dataset_manifest_path":str(dataset.resolve()),
        }), encoding="utf-8")

        fusion = root / "protected_fusion_candidate_manifest.json"
        fusion.write_text(json.dumps({
            "schema":"ConceptGhost.P10Gate7ProtectedFusionCandidate.v0.1",
            "status":"PASS",
            "scene_contract_id":"scene-1",
            "p9_run_id":"p9-1",
            "p10_attempt_id":"attempt-1",
            "coordinate_space":"P9_CANONICAL_WORLD_METERS",
            "candidate_ply_path":str(candidate.resolve()),
            "face_provenance_npz_path":str(face_evidence.resolve()),
            "candidate_is_official_geometry":False,
            "official_geometry_changed":False,
            "p9_authority_changed":False,
            "destructive_cleanup_performed":False,
            "ready_for_gate7_5":True,
            "counts":{"p9_faces":2,"p10_input_faces":2,"p10_accepted_faces":1},
            "inputs":{
                "p10_prefusion_mesh_path":str(p10.resolve()),
                "free_space_constraints_manifest_path":str(constraints.resolve()),
                "registration_manifest_path":str(registration.resolve()),
            },
        }), encoding="utf-8")
        return fusion

    @unittest.skipIf(np is None or Image is None, "NumPy/Pillow unavailable in minimal CI")
    def test_review_renders_all_required_layers_without_promotion(self):
        from p10_lab.gate7_visual_review import build_gate7_visual_review

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fusion = self._fixture(root)
            result = build_gate7_visual_review(fusion, root/"review", panel_size=360)

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["subgate"], "7.5")
            self.assertEqual(
                result["views"],
                ["PERSPECTIVE","TOP_XZ","FRONT_XY","SIDE_ZY"],
            )
            self.assertTrue(result["metric_isotropic_orthographic"])
            for key in (
                "p9_geometry",
                "p9_source_protected",
                "p10_accepted",
                "p10_rejected",
                "confirmed_free",
                "conflict",
                "camera_context",
            ):
                self.assertTrue(result["review_layers"][key])
            self.assertEqual(result["render_counts"]["p9_faces"], 2)
            self.assertEqual(result["render_counts"]["p10_accepted_faces"], 1)
            self.assertEqual(result["completion_effectiveness"]["status"], "PASS")
            self.assertAlmostEqual(result["completion_effectiveness"]["accepted_face_fraction"], 0.5)
            self.assertEqual(result["render_counts"]["p10_rejected_faces"], 1)
            self.assertEqual(result["render_counts"]["confirmed_free_voxels"], 1)
            self.assertEqual(result["render_counts"]["conflict_voxels"], 1)
            self.assertEqual(result["render_counts"]["camera_count"], 2)
            self.assertFalse(result["candidate_is_official_geometry"])
            self.assertFalse(result["official_geometry_changed"])
            self.assertEqual(result["artist_review_status"], "PENDING")
            self.assertFalse(result["ready_for_gate8"])
            self.assertIn("ARTIST_VISUAL_REVIEW_PENDING", result["promotion_blockers"])

            preview = Path(result["preview_png_path"])
            self.assertTrue(preview.is_file())
            with Image.open(preview) as image:
                self.assertGreater(image.width, 700)
                self.assertGreater(image.height, 700)

    @unittest.skipIf(np is None or Image is None, "NumPy/Pillow unavailable in minimal CI")
    def test_zero_p10_contribution_is_explicit_quality_failure_and_blocker(self):
        from p10_lab.gate7_visual_review import build_gate7_visual_review

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fusion=self._fixture(root)
            data=json.loads(fusion.read_text(encoding="utf-8"))
            data["counts"]["p10_input_faces"]=2
            data["counts"]["p10_accepted_faces"]=0
            fusion.write_text(json.dumps(data),encoding="utf-8")

            result=build_gate7_visual_review(fusion,root/"review",panel_size=360)
            self.assertEqual(result["status"],"PASS")
            self.assertEqual(result["completion_effectiveness"]["status"],"FAIL")
            self.assertEqual(result["completion_effectiveness"]["p10_accepted_faces"],0)
            self.assertIn("NO_P10_GEOMETRIC_CONTRIBUTION",result["promotion_blockers"])
            self.assertFalse(result["ready_for_gate8"])


    @unittest.skipIf(np is None or Image is None, "NumPy/Pillow unavailable in minimal CI")
    def test_officialized_candidate_is_rejected(self):
        from p10_lab.contracts import ContractError
        from p10_lab.gate7_visual_review import build_gate7_visual_review

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fusion = self._fixture(root)
            data = json.loads(fusion.read_text(encoding="utf-8"))
            data["candidate_is_official_geometry"] = True
            fusion.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ContractError):
                build_gate7_visual_review(fusion, root/"review", panel_size=360)

    def test_comfyui_node_is_registered_but_not_workflow_promoted_by_this_test(self):
        import p10_lab

        self.assertIn("ConceptGhostP10Gate7VisualReview", p10_lab.NODE_CLASS_MAPPINGS)
        cls = p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10Gate7VisualReview"]
        self.assertEqual(cls.CATEGORY, "ConceptGhost/P10 Refined")
        self.assertTrue(cls.OUTPUT_NODE)
        self.assertEqual(
            cls.RETURN_NAMES,
            (
                "review_image",
                "preview_png_path",
                "visual_review_manifest_path",
                "diagnostics_json",
            ),
        )
        self.assertTrue(
            cls.INPUT_TYPES()["required"]["protected_fusion_manifest_path"][1].get("forceInput")
        )

    def test_source_contract_keeps_visual_review_non_promoting(self):
        import p10_lab.gate7_visual_review as review

        source = Path(review.__file__).read_text(encoding="utf-8")
        self.assertIn('"mode": "VISUAL_REVIEW_ONLY_NO_PROMOTION"', source)
        self.assertIn('"artist_review_status": "PENDING"', source)
        self.assertIn('"ready_for_gate8": False', source)
        self.assertIn("ARTIST_VISUAL_REVIEW_PENDING", source)
        self.assertIn("DR9R_R15_RUNTIME_UX_ACCEPTANCE_PENDING", source)
        self.assertIn('"candidate_is_official_geometry": False', source)


if __name__ == "__main__":
    unittest.main()
