import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class DenseReconstructionTests(unittest.TestCase):
    def _dataset(self, root: Path):
        images = root / "images"
        sparse = root / "sparse" / "triangulated"
        images.mkdir(parents=True)
        sparse.mkdir(parents=True)
        (images / "frame_000000.png").write_bytes(b"png")
        for name in ("cameras.bin", "images.bin", "points3D.bin"):
            (sparse / name).write_bytes(b"x")
        return root

    def test_default_plan_is_bounded_for_11gb_first_pass(self):
        from p10_lab.dense_reconstruction import build_dense_plan
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp))
            plan = build_dense_plan(root, colmap_executable="colmap")

        self.assertEqual(plan.max_image_size, 832)
        self.assertEqual(plan.patch_match_cache_gb, 4.0)
        self.assertEqual(plan.fusion_cache_gb, 4.0)
        self.assertEqual(plan.min_num_pixels, 2)
        self.assertTrue(plan.geom_consistency)

        commands = [step.command for step in plan.steps]
        self.assertEqual(
            commands,
            ["image_undistorter", "patch_match_stereo", "stereo_fusion"],
        )

    def test_patch_match_plan_uses_single_gpu_and_bounded_iterations(self):
        from p10_lab.dense_reconstruction import build_dense_plan
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_dense_plan(self._dataset(Path(tmp)), colmap_executable="colmap")
        patch_step = next(s for s in plan.steps if s.command == "patch_match_stereo")
        joined = " ".join(patch_step.args)
        self.assertIn("--PatchMatchStereo.gpu_index 0", joined)
        self.assertIn("--PatchMatchStereo.max_image_size 832", joined)
        self.assertIn("--PatchMatchStereo.cache_size 4", joined)
        self.assertIn("--PatchMatchStereo.num_iterations 3", joined)
        self.assertIn("--PatchMatchStereo.geom_consistency 1", joined)
        self.assertIn("--PatchMatchStereo.write_consistency_graph 1", joined)
        self.assertNotIn("--PatchMatchStereo.geom_consistency true", joined)


    def test_explicit_source_selection_covers_every_registered_reference(self):
        from p10_lab.dense_reconstruction import _select_patch_match_sources

        rows=[]
        frames={}
        for index in range(8):
            name=f"frame_{index:06d}.png"
            rows.append({
                "name":name,
                "qvec":(1.0,0.0,0.0,0.0),
                "tvec":(-float(index)*0.2,0.0,0.0),
                "camera_id":1,
            })
            frames[name]={
                "image_name":name,
                "path_name":"drone_a" if index<4 else "drone_b",
                "global_frame_index":index,
            }
        selected=_select_patch_match_sources(
            rows,frames,max_sources=6,same_route_budget=3,cross_route_budget=3
        )
        self.assertEqual(set(selected),set(frames))
        self.assertTrue(all(len(values)>=2 for values in selected.values()))
        self.assertTrue(all(
            any(frames[source]["path_name"]!=frames[name]["path_name"] for source in values)
            for name,values in selected.items()
        ))

    def test_dense_geometric_evidence_requires_registered_coverage_not_nonzero_count(self):
        from p10_lab.dense_reconstruction import inspect_dense_geometric_evidence

        with tempfile.TemporaryDirectory() as tmp:
            dataset=Path(tmp)
            dense=dataset/"dense"
            sparse=dense/"sparse"
            sparse.mkdir(parents=True)
            registered=[
                {
                    "name":f"frame_{index:06d}.png",
                    "qvec":(1.0,0.0,0.0,0.0),
                    "tvec":(0.0,0.0,0.0),
                    "camera_id":1,
                }
                for index in range(10)
            ]
            for index in range(4):
                name=f"frame_{index:06d}.png"
                depth=dense/"stereo"/"depth_maps"/f"{name}.geometric.bin"
                graph=dense/"stereo"/"consistency_graphs"/f"{name}.geometric.bin"
                depth.parent.mkdir(parents=True,exist_ok=True)
                graph.parent.mkdir(parents=True,exist_ok=True)
                depth.write_bytes(b"x")
                graph.write_bytes(b"x")
            with patch(
                "p10_lab.dense_reconstruction.load_colmap_sparse_images",
                return_value=(tuple(registered),"BINARY"),
            ):
                result=inspect_dense_geometric_evidence(dataset,min_coverage_ratio=0.70)
            self.assertEqual(result["registered_image_count"],10)
            self.assertEqual(result["usable_registered_geometric_image_count"],4)
            self.assertAlmostEqual(result["geometric_evidence_coverage_ratio"],0.4)
            self.assertFalse(result["gate7_geometric_evidence_ready"])

    def test_fusion_plan_requires_two_supporting_pixels_first_pass(self):
        from p10_lab.dense_reconstruction import build_dense_plan
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_dense_plan(self._dataset(Path(tmp)), colmap_executable="colmap")
        fusion = next(s for s in plan.steps if s.command == "stereo_fusion")
        joined = " ".join(fusion.args)
        self.assertIn("--StereoFusion.min_num_pixels 2", joined)
        self.assertIn("--StereoFusion.max_image_size 832", joined)
        self.assertIn("--StereoFusion.cache_size 4", joined)

    def test_ascii_ply_produces_visual_preview_and_health_metrics(self):
        from p10_lab.dense_reconstruction import analyze_and_render_fused_cloud
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ply = root / "fused.ply"
            ply.write_text(
                "ply\n"
                "format ascii 1.0\n"
                "element vertex 5\n"
                "property float x\n"
                "property float y\n"
                "property float z\n"
                "property uchar red\n"
                "property uchar green\n"
                "property uchar blue\n"
                "end_header\n"
                "0 0 0 255 0 0\n"
                "1 0 1 0 255 0\n"
                "2 1 2 0 0 255\n"
                "3 1 3 255 255 0\n"
                "4 2 4 255 255 255\n",
                encoding="utf-8",
            )
            svg = root / "preview.svg"
            result = analyze_and_render_fused_cloud(ply, svg, max_preview_points=100)

            self.assertEqual(result["vertex_count"], 5)
            self.assertEqual(result["sampled_point_count"], 5)
            self.assertEqual(result["bounds"]["x"], [0.0, 4.0])
            self.assertEqual(result["bounds"]["y"], [0.0, 2.0])
            self.assertEqual(result["bounds"]["z"], [0.0, 4.0])
            self.assertTrue(svg.is_file())
            content = svg.read_text(encoding="utf-8")
            self.assertIn("TOP XZ", content)
            self.assertIn("FRONT XY", content)
            self.assertIn("SIDE ZY", content)

    def test_runner_fails_closed_if_colmap_command_fails(self):
        from p10_lab.dense_reconstruction import run_dense_reconstruction
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp))
            with patch("p10_lab.dense_reconstruction.subprocess.run") as run:
                run.return_value.returncode = 3
                run.return_value.stdout = ""
                run.return_value.stderr = "failed"
                with self.assertRaises(RuntimeError):
                    run_dense_reconstruction(root, colmap_executable="colmap")

    def test_existing_fused_cloud_is_not_overwritten_by_default(self):
        from p10_lab.dense_reconstruction import run_dense_reconstruction
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp))
            dense = root / "dense"
            dense.mkdir()
            (dense / "fused.ply").write_bytes(b"existing")
            with self.assertRaises(ValueError):
                run_dense_reconstruction(root, colmap_executable="colmap")


if __name__ == "__main__":
    unittest.main()
