import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    import numpy as np
except ImportError:
    np = None


def _write_mesh(path: Path, triangles):
    vertices=[]
    faces=[]
    for tri in triangles:
        base=len(vertices)
        vertices.extend(tri)
        faces.append((base,base+1,base+2))
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


class Gate7ProtectedFusionTests(unittest.TestCase):
    def _fixture(self, root: Path):
        p9=root/"p9";p9.mkdir()
        primary=p9/"primary_mesh.npz"
        p9_vertices=np.asarray([
            [0.0,0.0,0.0],[0.4,0.0,0.0],[0.0,0.4,0.0],[0.4,0.4,0.0]
        ],dtype=np.float32)
        p9_faces=np.asarray([[0,1,2],[1,3,2]],dtype=np.int32)
        grid=np.asarray([[0,0],[1,0],[0,1],[1,1]],dtype=np.int32)
        np.savez(primary,vertices=p9_vertices,faces=p9_faces,grid_xy=grid)

        dataset=root/"dataset";dense=dataset/"dense";dense.mkdir(parents=True)
        dataset_manifest=dataset/"dataset_manifest.json"
        dataset_manifest.write_text(json.dumps({"schema":"dataset"}),encoding="utf-8")

        p10=dense/"pre_fusion_mesh.ply"
        triangles=[
            ((0.10,0.10,0.0),(0.30,0.10,0.0),(0.10,0.30,0.0)),
            ((5.00,0.00,0.0),(5.30,0.00,0.0),(5.00,0.30,0.0)),
            ((8.00,0.00,0.0),(8.30,0.00,0.0),(8.00,0.30,0.0)),
            ((11.00,0.00,0.0),(11.30,0.00,0.0),(11.00,0.30,0.0)),
        ]
        _write_mesh(p10,triangles)
        delaunay=dense/"pre_fusion_mesh_delaunay.ply"
        _write_mesh(delaunay,[triangles[1]])

        registration=root/"registration.json"
        registration.write_text(json.dumps({
            "schema":"ConceptGhost.P10Gate7Registration.v0.1",
            "status":"PASS",
            "ready_for_gate7_2":True,
            "registration_policy":"KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION",
            "sim3_refit_allowed":False,
            "scale":1.0,
            "p9_run_id":"p9-run",
            "scene_contract_id":"scene-1",
            "p10_attempt_id":"attempt-1",
            "pre_fusion_mesh_path":str(p10.resolve()),
            "dataset_manifest_path":str(dataset_manifest.resolve()),
        }),encoding="utf-8")

        support_points=np.asarray([
            [0.1667,0.1667,0.0],
            [5.10,0.10,0.0],
            [8.10,0.10,0.0],
            [11.10,0.10,0.0],
        ],dtype=np.float32)
        overlay_npz=root/"overlay.npz"
        np.savez_compressed(
            overlay_npz,
            p10_points=support_points,
            p10_provenance_labels=np.asarray([3,3,3,3],dtype=np.uint8),
            p10_confidence_after_free_space=np.asarray([0.8,0.8,0.8,0.2],dtype=np.float32),
        )
        provenance=root/"provenance.json"
        provenance.write_text(json.dumps({
            "thresholds":{"scene_diagonal_m":100.0}
        }),encoding="utf-8")
        confidence=root/"confidence.json"
        confidence.write_text(json.dumps({
            "provenance_manifest_path":str(provenance.resolve())
        }),encoding="utf-8")
        overlay=root/"overlay.json"
        overlay.write_text(json.dumps({
            "schema":"ConceptGhost.P10Gate7ConfidenceFreeSpaceOverlay.v0.1",
            "status":"PASS",
            "scene_contract_id":"scene-1",
            "p9_run_id":"p9-run",
            "p10_attempt_id":"attempt-1",
            "official_geometry_changed":False,
            "p9_authority_changed":False,
            "ready_for_destructive_fusion":False,
            "evidence_npz_path":str(overlay_npz.resolve()),
            "source_confidence_manifest_path":str(confidence.resolve()),
        }),encoding="utf-8")

        constraint_npz=root/"constraints.npz"
        np.savez_compressed(
            constraint_npz,
            voxel_keys=np.asarray([[8,0,0]],dtype=np.int32),
            voxel_centers=np.asarray([[8.5,0.5,0.5]],dtype=np.float32),
            state=np.asarray([2],dtype=np.uint8),
        )
        constraints=root/"constraints.json"
        constraints.write_text(json.dumps({
            "schema":"ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1",
            "status":"PASS",
            "scene_contract_id":"scene-1",
            "p9_run_id":"p9-run",
            "p10_attempt_id":"attempt-1",
            "official_geometry_changed":False,
            "p9_authority_changed":False,
            "ready_for_destructive_fusion":False,
            "voxel":{"voxel_size_m":1.0},
            "constraints_npz_path":str(constraint_npz.resolve()),
        }),encoding="utf-8")

        boundary=SimpleNamespace(
            root=p9.resolve(),
            run_id="p9-run",
            scene_contract_id="scene-1",
            primary_mesh=primary.resolve(),
        )
        return p9,registration,overlay,constraints,boundary

    @unittest.skipIf(np is None,"NumPy unavailable in minimal CI")
    def test_candidate_is_additive_and_preserves_all_p9_faces(self):
        from p10_lab.protected_fusion import build_protected_fusion_candidate

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9,registration,overlay,constraints,boundary=self._fixture(root)
            with patch("p10_lab.protected_fusion.validate_official_run",return_value=boundary):
                result=build_protected_fusion_candidate(
                    p9,registration,overlay,constraints,root/"out"
                )

            self.assertEqual(result["status"],"PASS")
            self.assertEqual(result["subgate"],"7.4")
            self.assertEqual(result["counts"]["p9_faces"],2)
            self.assertEqual(result["p9_policy"]["p9_faces_removed"],0)
            self.assertEqual(result["p9_policy"]["p9_vertices_moved"],0)
            self.assertEqual(result["counts"]["p10_accepted_faces"],1)
            self.assertEqual(result["counts"]["p10_rejected_faces"],3)
            self.assertEqual(result["reason_counts"]["ACCEPTED_P10_MULTIVIEW"],1)
            self.assertEqual(result["reason_counts"]["P9_SOURCE_PROTECTED_OVERLAP"],1)
            self.assertEqual(result["reason_counts"]["CONFIRMED_FREE_VETO"],1)
            self.assertEqual(result["reason_counts"]["LOW_CONFIDENCE"],1)
            self.assertFalse(result["candidate_is_official_geometry"])
            self.assertFalse(result["official_geometry_changed"])
            self.assertFalse(result["destructive_cleanup_performed"])
            self.assertFalse(result["ready_for_destructive_fusion"])
            self.assertTrue(result["ready_for_gate7_5"])
            self.assertTrue(Path(result["candidate_ply_path"]).is_file())

            with np.load(result["face_provenance_npz_path"],allow_pickle=False) as evidence:
                accepted=evidence["p10_accepted_face_indices"].tolist()
                reasons=evidence["p10_face_reason_code"].tolist()
            self.assertEqual(accepted,[1])
            self.assertEqual(reasons,[3,0,1,5])

    @unittest.skipIf(np is None,"NumPy unavailable in minimal CI")
    def test_non_unit_registration_is_rejected(self):
        from p10_lab.contracts import ContractError
        from p10_lab.protected_fusion import build_protected_fusion_candidate

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9,registration,overlay,constraints,boundary=self._fixture(root)
            data=json.loads(registration.read_text(encoding="utf-8"))
            data["scale"]=1.1
            registration.write_text(json.dumps(data),encoding="utf-8")
            with patch("p10_lab.protected_fusion.validate_official_run",return_value=boundary):
                with self.assertRaises(ContractError):
                    build_protected_fusion_candidate(
                        p9,registration,overlay,constraints,root/"out"
                    )

    def test_source_contract_keeps_gate7_4_non_destructive(self):
        import p10_lab.protected_fusion as fusion

        source=Path(fusion.__file__).read_text(encoding="utf-8")
        self.assertIn('"all_p9_faces_copied_unchanged": True',source)
        self.assertIn('"p9_faces_removed": 0',source)
        self.assertIn('"p9_vertices_moved": 0',source)
        self.assertIn('"confirmed_free": "HARD_VETO"',source)
        self.assertIn('"candidate_is_official_geometry": False',source)
        self.assertIn('"destructive_cleanup_performed": False',source)
        self.assertIn('"ready_for_destructive_fusion": False',source)
        self.assertIn("P10_MULTIVIEW_SUPPORTED",source)


if __name__=="__main__":
    unittest.main()
