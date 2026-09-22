import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class SparseTriangulationTests(unittest.TestCase):
    def _dataset(self, root: Path, frame_count=4, camera_count=1):
        images = root / "images"
        sparse = root / "sparse" / "known"
        images.mkdir(parents=True)
        sparse.mkdir(parents=True)
        frames = []
        for i in range(frame_count):
            name = f"frame_{i:06d}.png"
            (images / name).write_bytes(b"png")
            camera_id = 1 + (i % camera_count)
            frames.append({
                "image_id": i + 1,
                "camera_id": camera_id,
                "global_frame_index": i,
                "image_name": name,
            })
        manifest = {
            "schema": "ConceptGhost.P10KnownCameraColmapDataset.v0.1",
            "run_id": "run1",
            "scene_contract_id": "scene1",
            "frame_count": frame_count,
            "camera_count": camera_count,
            "reconstruction_strategy": "KNOWN_CAMERA_COLMAP_PRIMARY",
            "images_dir": str(images),
            "known_sparse_model_dir": str(sparse),
            "frames": frames,
        }
        (root / "dataset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        lines = []
        for camera_id in range(1, camera_count + 1):
            fx = 700.0 + camera_id
            lines.append(f"{camera_id} PINHOLE 640 360 {fx} {fx} 320 180")
        (sparse / "cameras.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (sparse / "images.txt").write_text("", encoding="utf-8")
        (sparse / "points3D.txt").write_text("", encoding="utf-8")
        return root

    def test_plan_uses_exhaustive_matcher_for_current_small_preview(self):
        from p10_lab.sparse_triangulation import build_sparse_plan
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp), frame_count=81)
            plan = build_sparse_plan(root, colmap_executable="colmap")
        self.assertEqual(plan.matcher, "exhaustive_matcher")
        self.assertEqual(plan.frame_count, 81)
        self.assertFalse(plan.refine_intrinsics)

    def test_plan_switches_to_sequential_for_larger_future_dataset(self):
        from p10_lab.sparse_triangulation import build_sparse_plan
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp), frame_count=121)
            plan = build_sparse_plan(root, colmap_executable="colmap")
        self.assertEqual(plan.matcher, "sequential_matcher")
        self.assertEqual(plan.sequential_overlap, 12)

    def test_feature_extraction_is_grouped_by_known_camera_intrinsics(self):
        from p10_lab.sparse_triangulation import build_sparse_plan
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp), frame_count=4, camera_count=2)
            plan = build_sparse_plan(root, colmap_executable="colmap")
        feature_steps = [step for step in plan.steps if step.command == "feature_extractor"]
        self.assertEqual(len(feature_steps), 2)
        self.assertIn("--ImageReader.camera_model", feature_steps[0].args)
        self.assertIn("PINHOLE", feature_steps[0].args)
        self.assertIn("--ImageReader.single_camera", feature_steps[0].args)
        self.assertIn("1", feature_steps[0].args)

    def test_point_triangulator_keeps_known_frames_and_intrinsics_fixed(self):
        from p10_lab.sparse_triangulation import build_sparse_plan
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp))
            plan = build_sparse_plan(root, colmap_executable="colmap")
        step = next(step for step in plan.steps if step.command == "point_triangulator")
        joined = " ".join(step.args)
        self.assertIn("--clear_points 1", joined)
        self.assertIn("--refine_intrinsics 0", joined)
        self.assertIn("sparse/known", joined.replace("\\", "/"))
        self.assertIn("sparse/triangulated", joined.replace("\\", "/"))

    def test_runner_fails_closed_if_colmap_command_fails(self):
        from p10_lab.sparse_triangulation import run_sparse_triangulation
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp))
            with patch("p10_lab.sparse_triangulation.subprocess.run") as run:
                run.return_value.returncode = 2
                run.return_value.stdout = "bad"
                run.return_value.stderr = "failed"
                with self.assertRaises(RuntimeError):
                    run_sparse_triangulation(root, colmap_executable="colmap")

    def test_existing_completed_sparse_output_is_not_overwritten_by_default(self):
        from p10_lab.sparse_triangulation import run_sparse_triangulation
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp))
            out = root / "sparse" / "triangulated"
            out.mkdir(parents=True)
            (out / "cameras.bin").write_bytes(b"x")
            with self.assertRaises(ValueError):
                run_sparse_triangulation(root, colmap_executable="colmap")


if __name__ == "__main__":
    unittest.main()
