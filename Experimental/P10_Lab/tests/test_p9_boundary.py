import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from p10_lab.contracts import CompletionBundle, ContractError


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_official_run(
    root: Path,
    *,
    branch_mode: str,
    scene_id: str = "cgsc_test_identity",
    mesh_bytes: bytes = b"primary-mesh",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "source").mkdir()
    (root / "source" / "source.png").write_bytes(b"png-source")
    _write_json(
        root / "camera" / "camera.json",
        {
            "valid": True,
            "scene_contract_id": scene_id,
            "image_width": 1448,
            "image_height": 1086,
            "intrinsics": {"fx_px": 2174.4, "fy_px": 2174.4, "cx_px": 724.0, "cy_px": 543.0},
            "extrinsics": {"camera_world_matrix": [[1,0,0,0],[0,1,0,1.7],[0,0,1,0],[0,0,0,1]]},
        },
    )
    maya = root / "maya"
    maya.mkdir()
    mesh = maya / "ConceptGhost_concept_scene_PrimaryMesh.npz"
    mesh.write_bytes(mesh_bytes)
    _write_json(
        maya / "primary_mesh_payload.json",
        {
            "schema": "ConceptGhost.PrimarySolverMeshPayload.v0.31",
            "scene_contract_id": scene_id,
            "geometry_profile": "Low Resolution",
            "normal_gate": "PASS",
            "alignment": "EXACT_CANONICAL_XYZ_SUBSET",
        },
    )
    _write_json(root / "diagnostics" / "geometry_health.json", {"pass": True})
    pc = root / "geometry" / "canonical" / "pointcloud.ply"
    pc.parent.mkdir(parents=True)
    pc.write_bytes(b"ply\n")
    identity = {
        "scene_contract_id": scene_id,
        "camera_scene_contract_id": scene_id,
        "canonical_geometry_scene_contract_id": scene_id,
        "primary_mesh_scene_contract_id": scene_id,
        "maya_scene_contract_id": scene_id,
        "status": "PASS",
    }
    manifest = {
        "schema": "ConceptGhost.Manifest.v0.31",
        "run_id": root.name,
        "branch_mode": branch_mode,
        "scene_contract_id": scene_id,
        "geometry_profile": "Low Resolution",
        "identity_chain": identity,
        "coordinate_convention": {"handedness": "right-handed", "up_axis": "+Y", "camera_forward": "-Z"},
        "scale_authority": {"authority": "AUTOMATIC_BASELINE_SCALE", "p10_scale_override_allowed": False},
        "status": {"run_status": "PASS", "authoritative": True, "deliverable_package_complete": True},
        "hero_mesh": {"payload": {"scene_contract_id": scene_id}},
    }
    _write_json(root / "manifest.json", manifest)
    _write_json(
        root / "output_index.json",
        {
            "schema": "ConceptGhost.OutputIndex.v0.31",
            "run_id": root.name,
            "scene_contract_id": scene_id,
            "official": {"primary_mesh": {"role": "OFFICIAL_MODELING_REFERENCE_MESH"}},
        },
    )
    _write_json(
        root / "package" / "official_outputs_contract.json",
        {
            "schema": "ConceptGhost.OfficialRunPack.v0.43",
            "status": "PASS",
            "branch_mode": branch_mode,
            "missing_core": [],
            "missing_maya": [],
        },
    )
    return root


class P9BoundaryTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab import p9_boundary
        except ImportError as error:
            self.fail(f"Gate 2 boundary module is missing: {error}")
        return p9_boundary

    def test_builds_and_loads_completion_bundle_from_real_run_pack_shape(self):
        api = self._api()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run = _write_official_run(root / "run-baseline", branch_mode="Baseline / P9")
            result = api.build_completion_bundle(run, root / "ConceptGhost_P9_CompletionBundle.zip")
            bundle = api.load_completion_bundle(result.zip_path, extract_root=root / "cache")

            self.assertEqual(bundle.source_stage, "baseline")
            self.assertEqual(bundle.source_run_id, "run-baseline")
            self.assertEqual(bundle.scene_contract_id, "cgsc_test_identity")
            self.assertEqual(bundle.source_branch_mode, "Baseline / P9")
            self.assertEqual(bundle.primary_mesh.suffix, ".npz")
            self.assertEqual(bundle.file_sha256["primary_mesh"], api.sha256_file(bundle.primary_mesh))
            self.assertIn("point_cloud", bundle.optional)

    def test_refined_p9_run_is_baseline_equivalent_but_labeled_p9(self):
        api = self._api()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run = _write_official_run(root / "run-refined", branch_mode="Refined / P9 Clone")
            result = api.build_completion_bundle(run, root / "p9.zip")
            bundle = api.load_completion_bundle(result.zip_path, extract_root=root / "cache")
            self.assertEqual(bundle.source_stage, "p9")
            self.assertEqual(bundle.source_equivalent_to, "baseline")

    def test_official_refined_p10_reserved_label_is_accepted_as_p9_boundary(self):
        api = self._api()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run = _write_official_run(
                root / "run-refined-reserved",
                branch_mode="Refined / P9 Clone · P10 Reserved",
            )
            boundary = api.validate_official_run(run)
            self.assertEqual(boundary.source_stage, "p9")
            self.assertEqual(
                boundary.branch_mode,
                "Refined / P9 Clone · P10 Reserved",
            )

    def test_near_match_refined_label_is_still_rejected_fail_closed(self):
        api = self._api()
        with tempfile.TemporaryDirectory() as temp_dir:
            run = _write_official_run(
                Path(temp_dir) / "run",
                branch_mode="Refined / P9 Clone · Experimental",
            )
            with self.assertRaises(ContractError):
                api.validate_official_run(run)

    def test_identity_chain_mismatch_is_rejected(self):
        api = self._api()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run = _write_official_run(root / "run", branch_mode="Baseline / P9")
            manifest_path = run / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["identity_chain"]["primary_mesh_scene_contract_id"] = "wrong"
            _write_json(manifest_path, manifest)
            with self.assertRaises(ContractError):
                api.validate_official_run(run)

    def test_unknown_branch_mode_is_rejected(self):
        api = self._api()
        with tempfile.TemporaryDirectory() as temp_dir:
            run = _write_official_run(Path(temp_dir) / "run", branch_mode="Legacy Refined")
            with self.assertRaises(ContractError):
                api.validate_official_run(run)

    def test_bundle_bytes_are_hash_validated(self):
        api = self._api()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run = _write_official_run(root / "run", branch_mode="Baseline / P9")
            result = api.build_completion_bundle(run, root / "bundle.zip")
            bundle = api.load_completion_bundle(result.zip_path, extract_root=root / "cache")
            bundle.camera.write_text("{}", encoding="utf-8")
            with self.assertRaises(ContractError):
                CompletionBundle.from_directory(bundle.root)

    def test_baseline_and_p9_identity_comparison_detects_mesh_divergence(self):
        api = self._api()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline = _write_official_run(root / "baseline", branch_mode="Baseline / P9")
            refined = _write_official_run(root / "refined", branch_mode="Refined / P9 Clone")
            same = api.compare_baseline_p9_identity(baseline, refined)
            self.assertTrue(same.passed)
            (refined / "maya" / "ConceptGhost_concept_scene_PrimaryMesh.npz").write_bytes(b"different")
            changed = api.compare_baseline_p9_identity(baseline, refined)
            self.assertFalse(changed.passed)
            self.assertIn("primary_mesh", changed.mismatches)

    def test_zip_loader_rejects_path_traversal(self):
        api = self._api()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bad = root / "bad.zip"
            with zipfile.ZipFile(bad, "w") as archive:
                archive.writestr("../escape.txt", "bad")
            with self.assertRaises(ContractError):
                api.load_completion_bundle(bad, extract_root=root / "cache")


if __name__ == "__main__":
    unittest.main()
