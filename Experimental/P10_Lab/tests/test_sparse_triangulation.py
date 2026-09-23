import json
import sqlite3
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MAX_IMAGE_ID = 2**31 - 1


def pair_id(a, b):
    a, b = sorted((int(a), int(b)))
    return a * MAX_IMAGE_ID + b


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
                "qvec": [1.0, 0.0, 0.0, 0.0],
                "tvec": [float(i), 0.0, 0.0],
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

    def _database(self, root: Path, *, frame_count=4, camera_count=1, db_order=None, disconnected=()):
        db = sqlite3.connect(root / "database.db")
        db.execute("CREATE TABLE cameras(camera_id INTEGER PRIMARY KEY, model INTEGER, width INTEGER, height INTEGER, params BLOB, prior_focal_length INTEGER)")
        db.execute("CREATE TABLE rigs(rig_id INTEGER PRIMARY KEY, ref_sensor_id INTEGER, ref_sensor_type INTEGER)")
        db.execute("CREATE TABLE rig_sensors(rig_id INTEGER, sensor_id INTEGER, sensor_type INTEGER, sensor_from_rig BLOB)")
        db.execute("CREATE TABLE frames(frame_id INTEGER PRIMARY KEY, rig_id INTEGER)")
        db.execute("CREATE TABLE frame_data(frame_id INTEGER, data_id INTEGER, sensor_id INTEGER, sensor_type INTEGER)")
        db.execute("CREATE TABLE images(image_id INTEGER PRIMARY KEY, name TEXT UNIQUE, camera_id INTEGER)")
        db.execute("CREATE TABLE keypoints(image_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
        db.execute("CREATE TABLE descriptors(image_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB)")
        db.execute("CREATE TABLE two_view_geometries(pair_id INTEGER PRIMARY KEY, rows INTEGER, cols INTEGER, data BLOB, config INTEGER)")
        for source_camera_id in range(1, camera_count + 1):
            db_camera_id = 100 + source_camera_id
            db_rig_id = 500 + source_camera_id
            fx = 700.0 + source_camera_id
            params = struct.pack("<4d", fx, fx, 320.0, 180.0)
            db.execute("INSERT INTO cameras VALUES (?,?,?,?,?,?)", (db_camera_id, 1, 640, 360, params, 1))
            db.execute("INSERT INTO rigs VALUES (?,?,?)", (db_rig_id, db_camera_id, 0))

        order = list(range(frame_count)) if db_order is None else list(db_order)
        db_id_for_frame = {}
        for db_image_id, frame_index in enumerate(order, start=20):
            camera_id = 100 + (1 + (frame_index % camera_count))
            name = f"frame_{frame_index:06d}.png"
            db.execute("INSERT INTO images VALUES (?,?,?)", (db_image_id, name, camera_id))
            source_camera_id = 1 + (frame_index % camera_count)
            db_rig_id = 500 + source_camera_id
            db_frame_id = 900 + frame_index
            db.execute("INSERT INTO frames VALUES (?,?)", (db_frame_id, db_rig_id))
            db.execute(
                "INSERT INTO frame_data VALUES (?,?,?,?)",
                (db_frame_id, db_image_id, camera_id, 0),
            )
            rows = 0 if frame_index in disconnected else 64
            db.execute("INSERT INTO keypoints VALUES (?,?,?,?)", (db_image_id, rows, 4, b"x"))
            db.execute("INSERT INTO descriptors VALUES (?,?,?,?)", (db_image_id, rows, 128, b"x"))
            db_id_for_frame[frame_index] = db_image_id

        active = [i for i in range(frame_count) if i not in disconnected]
        for a, b in zip(active, active[1:]):
            ida, idb = db_id_for_frame[a], db_id_for_frame[b]
            db.execute(
                "INSERT INTO two_view_geometries VALUES (?,?,?,?,?)",
                (pair_id(ida, idb), 17, 2, b"x", 2),
            )
        db.commit()
        db.close()
        return db_id_for_frame

    def test_plan_uses_exhaustive_matcher_for_current_small_preview(self):
        from p10_lab.sparse_triangulation import build_sparse_plan
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp), frame_count=81)
            plan = build_sparse_plan(root, colmap_executable="colmap")
        self.assertEqual(plan.matcher, "exhaustive_matcher")
        self.assertEqual(plan.frame_count, 81)
        self.assertFalse(plan.refine_intrinsics)
        self.assertEqual(
            plan.manifest()["image_id_policy"],
            "DATABASE_IDS_SYNCHRONIZED_BEFORE_TRIANGULATION",
        )

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

    def test_database_sync_rewrites_ids_and_uses_exact_database_rigs_frames(self):
        from p10_lab.sparse_triangulation import build_sparse_plan, _write_database_synced_model
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp), frame_count=4, camera_count=2)
            ids = self._database(root, frame_count=4, camera_count=2, db_order=[2, 0, 3, 1])
            plan = build_sparse_plan(root)
            synced = _write_database_synced_model(plan)
            images_txt = (synced.text_path / "images.txt").read_text(encoding="utf-8")
            self.assertIn(f"{ids[0]} 1 0 0 0 0 0 0 101 frame_000000.png", images_txt)
            self.assertIn(f"{ids[1]} 1 0 0 0 1 0 0 102 frame_000001.png", images_txt)
            rigs_txt = (synced.text_path / "rigs.txt").read_text(encoding="utf-8")
            frames_txt = (synced.text_path / "frames.txt").read_text(encoding="utf-8")
            self.assertIn("501 1 CAMERA 101", rigs_txt)
            self.assertIn("502 1 CAMERA 102", rigs_txt)
            self.assertIn(f"900 501 1 0 0 0 0 0 0 1 CAMERA 101 {ids[0]}", frames_txt)
            self.assertIn(f"901 502 1 0 0 0 1 0 0 1 CAMERA 102 {ids[1]}", frames_txt)
            diag = json.loads(synced.diagnostics_path.read_text(encoding="utf-8"))
            self.assertEqual(diag["selected_component_count"], 4)
            self.assertEqual(diag["dropped_image_count"], 0)
            self.assertEqual(
                diag["rig_frame_policy"],
                "DATABASE_ASSIGNED_TRIVIAL_RIG_AND_FRAME_IDS",
            )

    def test_database_sync_preserves_multiple_verified_components(self):
        from p10_lab.sparse_triangulation import build_sparse_plan, _write_database_synced_model
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp), frame_count=4, camera_count=1)
            ids = self._database(root, frame_count=4, camera_count=1)
            db = sqlite3.connect(root / "database.db")
            db.execute(
                "DELETE FROM two_view_geometries WHERE pair_id=?",
                (pair_id(ids[1], ids[2]),),
            )
            db.commit()
            db.close()

            plan = build_sparse_plan(root)
            synced = _write_database_synced_model(plan)
            diag = json.loads(synced.diagnostics_path.read_text(encoding="utf-8"))

            self.assertEqual(diag["verified_component_count"], 2)
            self.assertTrue(diag["all_verified_components_preserved"])
            self.assertEqual(diag["component_policy"], "ALL_VERIFIED_MATCH_COMPONENTS_FIXED_P9_WORLD")
            self.assertEqual(diag["dropped_image_count"], 0)
            self.assertEqual(set(diag["selected_image_ids"]), set(ids.values()))
            images_txt = (synced.text_path / "images.txt").read_text(encoding="utf-8")
            for index in range(4):
                self.assertIn(f"frame_{index:06d}.png", images_txt)

    def test_database_sync_drops_disconnected_featureless_view(self):
        from p10_lab.sparse_triangulation import build_sparse_plan, _write_database_synced_model
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp), frame_count=5, camera_count=1)
            ids = self._database(root, frame_count=5, camera_count=1, disconnected=(4,))
            plan = build_sparse_plan(root)
            synced = _write_database_synced_model(plan)
            diag = json.loads(synced.diagnostics_path.read_text(encoding="utf-8"))
            self.assertEqual(diag["selected_component_count"], 4)
            self.assertEqual(diag["dropped_image_count"], 1)
            self.assertIn(ids[4], diag["dropped_image_ids"])
            self.assertNotIn(
                "frame_000004.png",
                (synced.text_path / "images.txt").read_text(encoding="utf-8"),
            )

    def test_database_sync_fails_if_no_verified_component(self):
        from p10_lab.sparse_triangulation import build_sparse_plan, _write_database_synced_model
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp), frame_count=3)
            self._database(root, frame_count=3, disconnected=(0, 1, 2))
            plan = build_sparse_plan(root)
            with self.assertRaises(ValueError):
                _write_database_synced_model(plan)

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

    def test_sparse_rebuild_deletes_stale_database_before_feature_extraction(self):
        from p10_lab.sparse_triangulation import run_sparse_triangulation
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp))
            stale = root / "database.db"
            stale.write_bytes(b"stale-camera-state")
            with patch("p10_lab.sparse_triangulation.subprocess.run") as run:
                run.return_value.returncode = 2
                run.return_value.stdout = ""
                run.return_value.stderr = "expected stop"
                with self.assertRaises(RuntimeError):
                    run_sparse_triangulation(root, colmap_executable="colmap")
            self.assertFalse(stale.exists())

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
