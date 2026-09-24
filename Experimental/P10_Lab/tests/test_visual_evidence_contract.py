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


def _write_mesh(path: Path, offset: float = 0.0):
    vertices = [
        (-0.8 + offset, -0.8, 4.0),
        (0.8 + offset, -0.8, 4.0),
        (0.8 + offset, 0.8, 4.0),
        (-0.8 + offset, 0.8, 4.0),
        (-0.5 + offset, -0.5, 5.0),
        (0.5 + offset, -0.5, 5.0),
        (0.5 + offset, 0.5, 5.0),
        (-0.5 + offset, 0.5, 5.0),
    ]
    faces = [
        (0,1,2),(0,2,3),
        (4,5,6),(4,6,7),
        (0,1,5),(0,5,4),
        (1,2,6),(1,6,5),
        (2,3,7),(2,7,6),
        (3,0,4),(3,4,7),
    ]
    lines = [
        "ply","format ascii 1.0",
        f"element vertex {len(vertices)}",
        "property float x","property float y","property float z",
        f"element face {len(faces)}",
        "property list uchar int vertex_indices",
        "end_header",
    ]
    lines.extend(f"{x} {y} {z}" for x,y,z in vertices)
    lines.extend(f"3 {a} {b} {c}" for a,b,c in faces)
    path.write_text("\n".join(lines)+"\n", encoding="ascii")


class VisualEvidenceContractTests(unittest.TestCase):
    def test_every_known_gate_requires_preview_and_comparison(self):
        from p10_lab.visual_evidence_contract import VISUAL_EVIDENCE_RULES

        expected = {"G7.1","G7.2","G7.2C","G7.3","G7.4","G7.5","G7.6"}
        self.assertTrue(expected.issubset(VISUAL_EVIDENCE_RULES))
        for gate in expected:
            self.assertTrue(VISUAL_EVIDENCE_RULES[gate]["preview"])
            self.assertTrue(VISUAL_EVIDENCE_RULES[gate]["comparison"])

    def test_terminal_visual_manifest_cannot_feed_geometry(self):
        from p10_lab.visual_evidence_contract import (
            build_visual_evidence_manifest,
            validate_visual_evidence_manifest,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            preview=root/"preview.png"; preview.write_bytes(b"preview")
            comparison=root/"comparison.gif"; comparison.write_bytes(b"comparison")
            result=build_visual_evidence_manifest(
                "G7.4",
                root/"manifest",
                preview_artifacts=[preview],
                comparison_artifacts=[comparison],
                metadata={"before":"prefusion","after":"protected_fusion"},
            )
            checked=validate_visual_evidence_manifest(result["manifest_path"],"G7.4")
            branch=checked["branch_contract"]
            self.assertTrue(branch["terminal_visual_branch"])
            self.assertFalse(branch["feeds_geometry_pipeline"])
            self.assertFalse(branch["may_modify_geometry"])
            self.assertFalse(branch["may_modify_p9"])
            self.assertFalse(branch["may_promote_result"])


class VisualComparisonTests(unittest.TestCase):
    @unittest.skipIf(np is None or Image is None, "NumPy/Pillow unavailable")
    def test_confidence_before_after_is_same_projection_and_blue_red(self):
        from p10_lab.visual_comparisons import render_confidence_before_after

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            points=np.asarray([
                [0,0,0],[1,0,0],[0,1,0],[1,1,0],[0.5,0.5,1]
            ],dtype=np.float32)
            before_npz=root/"before.npz"
            np.savez_compressed(
                before_npz,
                p10_points=points,
                p10_confidence=np.asarray([0.9,0.8,0.6,0.4,0.2],dtype=np.float32),
            )
            after_npz=root/"after.npz"
            np.savez_compressed(
                after_npz,
                p10_points=points,
                p10_confidence_after_free_space=np.asarray([0.9,0.8,0.2,0.1,0.05],dtype=np.float32),
            )
            confidence=root/"confidence.json"
            confidence.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7GeometryConfidence.v0.1",
                "scene_contract_id":"scene",
                "p9_run_id":"p9",
                "p10_attempt_id":"attempt",
                "evidence_npz_path":str(before_npz.resolve()),
            }),encoding="utf-8")
            overlay=root/"overlay.json"
            overlay.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7ConfidenceFreeSpaceOverlay.v0.1",
                "scene_contract_id":"scene",
                "p9_run_id":"p9",
                "p10_attempt_id":"attempt",
                "evidence_npz_path":str(after_npz.resolve()),
            }),encoding="utf-8")
            result=render_confidence_before_after(confidence,overlay,root/"out",panel_size=320)
            self.assertTrue(Path(result["comparison_png_path"]).is_file())
            self.assertTrue(result["same_metric_projection"])
            self.assertEqual(result["high_confidence_color"],"BLUE")
            self.assertEqual(result["low_confidence_color"],"RED")
            self.assertGreater(result["changed_point_count"],0)
            self.assertFalse(result["feeds_geometry_pipeline"])

    @unittest.skipIf(np is None or Image is None, "NumPy/Pillow unavailable")
    def test_same_camera_before_after_replay_generates_three_gifs(self):
        from p10_lab.visual_comparisons import render_drone_mesh_before_after_replay

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            before=root/"before.ply"; after=root/"after.ply"
            _write_mesh(before,0.0); _write_mesh(after,0.15)

            sparse=root/"sparse"/"known"
            sparse.mkdir(parents=True)
            (sparse/"cameras.txt").write_text(
                "1 PINHOLE 640 360 450 450 320 180\n",
                encoding="utf-8",
            )
            frames=[]
            for i,tx in enumerate((0.0,-0.15,-0.30)):
                frames.append({
                    "camera_id":1,
                    "global_frame_index":i,
                    "path_name":"drone_a",
                    "qvec":[1.0,0.0,0.0,0.0],
                    "tvec":[tx,0.0,0.0],
                })
            dataset=root/"dataset_manifest.json"
            dataset.write_text(json.dumps({
                "schema":"ConceptGhost.P10KnownCameraColmapDataset.v0.2",
                "run_id":"p9",
                "scene_contract_id":"scene",
                "camera_authority":"P9_BASELINE_WORLD_DERIVED",
                "known_sparse_model_dir":str(sparse.resolve()),
                "frames":frames,
            }),encoding="utf-8")

            result=render_drone_mesh_before_after_replay(
                dataset,before,after,root/"replay",
                width=320,height=180,max_frames=3,max_faces=100,duration_ms=20,
            )
            for key in ("before_gif_path","after_gif_path","comparison_gif_path"):
                path=Path(result[key])
                self.assertTrue(path.is_file())
                with Image.open(path) as image:
                    self.assertEqual(getattr(image,"n_frames",1),3)
            contract=result["camera_contract"]
            self.assertTrue(contract["same_qvec_tvec_on_both_sides"])
            self.assertTrue(contract["same_intrinsics_on_both_sides"])
            self.assertTrue(contract["same_frame_selection_on_both_sides"])
            self.assertFalse(result["feeds_geometry_pipeline"])


if __name__=="__main__":
    unittest.main()
