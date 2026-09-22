import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class PreFusionMeshTests(unittest.TestCase):
    def _dataset(self, root: Path):
        dense = root / "dense"
        dense.mkdir(parents=True)
        (dense / "fused.ply").write_text(
            "ply\n"
            "format ascii 1.0\n"
            "element vertex 4\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "property float nx\n"
            "property float ny\n"
            "property float nz\n"
            "property uchar red\n"
            "property uchar green\n"
            "property uchar blue\n"
            "end_header\n"
            "0 0 0 0 1 0 255 0 0\n"
            "1 0 0 0 1 0 0 255 0\n"
            "1 1 0 0 1 0 0 0 255\n"
            "0 1 0 0 1 0 255 255 255\n",
            encoding="utf-8",
        )
        return root

    def _write_ascii_mesh(self, path: Path):
        path.write_text(
            "ply\n"
            "format ascii 1.0\n"
            "element vertex 4\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "element face 2\n"
            "property list uchar int vertex_index\n"
            "end_header\n"
            "0 0 0\n"
            "1 0 0\n"
            "1 1 0\n"
            "0 1 0\n"
            "3 0 1 2\n"
            "3 0 0 3\n",
            encoding="utf-8",
        )

    def _write_binary_mesh(self, path: Path):
        header = (
            "ply\n"
            "format binary_little_endian 1.0\n"
            "element vertex 4\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "element face 2\n"
            "property list uchar int vertex_index\n"
            "end_header\n"
        ).encode("ascii")
        with path.open("wb") as stream:
            stream.write(header)
            for xyz in ((0,0,0),(1,0,0),(1,1,0),(0,1,0)):
                stream.write(struct.pack("<fff", *xyz))
            stream.write(struct.pack("<Biii", 3, 0, 1, 2))
            stream.write(struct.pack("<Biii", 3, 0, 2, 3))

    def test_default_plan_uses_bounded_poisson_first_pass(self):
        from p10_lab.prefusion_mesh import build_prefusion_mesh_plan
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_prefusion_mesh_plan(self._dataset(Path(tmp)), colmap_executable="colmap")
        self.assertEqual(plan.poisson_depth, 10)
        self.assertEqual(plan.poisson_trim, 10.0)
        self.assertEqual(plan.point_weight, 1.0)
        self.assertEqual(len(plan.steps), 1)
        step = plan.steps[0]
        self.assertEqual(step.command, "poisson_mesher")
        joined = " ".join(step.args)
        self.assertIn("--PoissonMeshing.depth 10", joined)
        self.assertIn("--PoissonMeshing.trim 10", joined)
        self.assertIn("--PoissonMeshing.point_weight 1", joined)
        self.assertIn("--PoissonMeshing.color 1", joined)

    def test_ascii_mesh_health_detects_degenerate_sample_and_writes_preview(self):
        from p10_lab.prefusion_mesh import analyze_and_render_mesh
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh = root / "mesh.ply"
            preview = root / "preview.svg"
            self._write_ascii_mesh(mesh)
            result = analyze_and_render_mesh(mesh, preview, max_preview_faces=100)
            self.assertEqual(result["vertex_count"], 4)
            self.assertEqual(result["face_count"], 2)
            self.assertEqual(result["sampled_face_count"], 2)
            self.assertEqual(result["degenerate_face_sample_count"], 1)
            self.assertAlmostEqual(result["degenerate_face_sample_fraction"], 0.5)
            self.assertTrue(preview.is_file())
            svg = preview.read_text(encoding="utf-8")
            self.assertIn("TOP XZ", svg)
            self.assertIn("FRONT XY", svg)
            self.assertIn("SIDE ZY", svg)
            self.assertIn("faces 2", svg)

    def test_binary_colmap_style_mesh_header_and_faces_are_supported(self):
        from p10_lab.prefusion_mesh import analyze_and_render_mesh
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh = root / "mesh.ply"
            preview = root / "preview.svg"
            self._write_binary_mesh(mesh)
            result = analyze_and_render_mesh(mesh, preview, max_preview_faces=100)
            self.assertEqual(result["vertex_count"], 4)
            self.assertEqual(result["face_count"], 2)
            self.assertEqual(result["invalid_face_index_sample_count"], 0)
            self.assertEqual(result["degenerate_face_sample_count"], 0)

    def test_runner_fails_closed_if_poisson_mesher_fails(self):
        from p10_lab.prefusion_mesh import run_prefusion_meshing
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp))
            with patch("p10_lab.prefusion_mesh.subprocess.run") as run:
                run.return_value.returncode = 4
                run.return_value.stdout = ""
                run.return_value.stderr = "poisson failed"
                with self.assertRaises(RuntimeError):
                    run_prefusion_meshing(root, colmap_executable="colmap")

    def test_existing_mesh_is_not_overwritten_by_default(self):
        from p10_lab.prefusion_mesh import run_prefusion_meshing
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dataset(Path(tmp))
            mesh = root / "dense" / "pre_fusion_mesh.ply"
            mesh.write_bytes(b"existing")
            with self.assertRaises(ValueError):
                run_prefusion_meshing(root, colmap_executable="colmap")


if __name__ == "__main__":
    unittest.main()
