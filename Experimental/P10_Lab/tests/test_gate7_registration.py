import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class Gate7RegistrationTests(unittest.TestCase):
    def _fixture(self, root: Path):
        p9 = root / "p9_run"
        p9.mkdir()
        attempt = root / "attempt"
        attempt.mkdir()
        dataset = root / "dataset"
        dataset.mkdir()
        dense = dataset / "dense"
        dense.mkdir()
        mesh = dense / "pre_fusion_mesh.ply"
        mesh.write_text("ply\n", encoding="utf-8")

        wan = root / "wan_manifest.json"
        wan.write_text(
            json.dumps(
                {
                    "schema": "ConceptGhost.P10WanSequential.v0.2",
                    "scene_contract_id": "scene-abc",
                    "source_run_id": "p9_run",
                    "source_p9_run_dir": str(p9.resolve()),
                    "p10_attempt_id": "attempt-001",
                    "p10_attempt_root": str(attempt.resolve()),
                    "route_plan_sha256": "a" * 64,
                }
            ),
            encoding="utf-8",
        )

        (dataset / "dataset_manifest.json").write_text(
            json.dumps(
                {
                    "schema": "ConceptGhost.P10KnownCameraColmapDataset.v0.2",
                    "run_id": "p9_run",
                    "scene_contract_id": "scene-abc",
                    "reconstruction_strategy": "KNOWN_CAMERA_COLMAP_PRIMARY",
                    "camera_authority": "P9_BASELINE_WORLD_DERIVED",
                    "coordinate_conversion": {
                        "source": "CONCEPTGHOST_MAYA_CAMERA_C2W_XRIGHT_YUP_MINUSZ_FORWARD",
                        "target": "COLMAP_W2C_XRIGHT_YDOWN_ZFORWARD",
                        "axis_transform": "diag(1,-1,-1)",
                    },
                }
            ),
            encoding="utf-8",
        )

        runtime = root / "reconstruction_runtime_manifest.json"
        runtime.write_text(
            json.dumps(
                {
                    "schema": "ConceptGhost.P10ReconstructionRuntime.v0.2",
                    "runtime_status": "PASS",
                    "geometry_quality_status": "PASS",
                    "gate7_promotion_allowed": True,
                    "wan_manifest_path": str(wan.resolve()),
                    "dataset_root": str(dataset.resolve()),
                    "pre_fusion_mesh_path": str(mesh.resolve()),
                    "p10_attempt_id": "attempt-001",
                    "p10_attempt_root": str(attempt.resolve()),
                    "route_plan_sha256": "a" * 64,
                }
            ),
            encoding="utf-8",
        )
        boundary = SimpleNamespace(
            root=p9.resolve(),
            run_id="p9_run",
            scene_contract_id="scene-abc",
        )
        return p9, runtime, boundary

    def test_known_camera_gate6_registers_by_identity_without_sim3_refit(self):
        from p10_lab.gate7_registration import build_gate7_registration

        with tempfile.TemporaryDirectory() as tmp:
            p9, runtime, boundary = self._fixture(Path(tmp))
            with patch("p10_lab.gate7_registration.validate_official_run", return_value=boundary):
                result = build_gate7_registration(p9, runtime)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["subgate"], "7.1")
        self.assertEqual(
            result["registration_policy"],
            "KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION",
        )
        self.assertEqual(result["registration_solver"], "NOT_RUN_BY_DESIGN")
        self.assertEqual(result["coordinate_space"], "P9_CANONICAL_WORLD_METERS")
        self.assertEqual(result["scale"], 1.0)
        self.assertEqual(result["translation_m"], [0.0, 0.0, 0.0])
        self.assertEqual(
            result["transform_p10_to_p9"],
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
        )
        self.assertFalse(result["p9_authority_changed"])
        self.assertFalse(result["sim3_refit_allowed"])
        self.assertTrue(result["ready_for_gate7_2"])

    def test_gate6_fail_is_not_promoted(self):
        from p10_lab.contracts import ContractError
        from p10_lab.gate7_registration import build_gate7_registration

        with tempfile.TemporaryDirectory() as tmp:
            p9, runtime, boundary = self._fixture(Path(tmp))
            payload = json.loads(runtime.read_text(encoding="utf-8"))
            payload["geometry_quality_status"] = "FAIL"
            payload["gate7_promotion_allowed"] = False
            runtime.write_text(json.dumps(payload), encoding="utf-8")
            with patch("p10_lab.gate7_registration.validate_official_run", return_value=boundary):
                with self.assertRaises(ContractError):
                    build_gate7_registration(p9, runtime)

    def test_mismatched_p9_run_is_fail_closed(self):
        from p10_lab.contracts import ContractError
        from p10_lab.gate7_registration import build_gate7_registration

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p9, runtime, boundary = self._fixture(root)
            wan_path = Path(json.loads(runtime.read_text(encoding="utf-8"))["wan_manifest_path"])
            payload = json.loads(wan_path.read_text(encoding="utf-8"))
            wrong = root / "other_p9"
            wrong.mkdir()
            payload["source_p9_run_dir"] = str(wrong.resolve())
            wan_path.write_text(json.dumps(payload), encoding="utf-8")
            with patch("p10_lab.gate7_registration.validate_official_run", return_value=boundary):
                with self.assertRaises(ContractError):
                    build_gate7_registration(p9, runtime)

    def test_non_p9_camera_authority_is_fail_closed(self):
        from p10_lab.contracts import ContractError
        from p10_lab.gate7_registration import build_gate7_registration

        with tempfile.TemporaryDirectory() as tmp:
            p9, runtime, boundary = self._fixture(Path(tmp))
            runtime_payload = json.loads(runtime.read_text(encoding="utf-8"))
            dataset_root = Path(runtime_payload["dataset_root"])
            manifest = dataset_root / "dataset_manifest.json"
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["camera_authority"] = "FREE_SOLVE"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with patch("p10_lab.gate7_registration.validate_official_run", return_value=boundary):
                with self.assertRaises(ContractError):
                    build_gate7_registration(p9, runtime)


if __name__ == "__main__":
    unittest.main()
