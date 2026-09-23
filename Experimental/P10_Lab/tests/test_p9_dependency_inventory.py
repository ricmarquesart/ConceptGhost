import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class P9DependencyInventoryTests(unittest.TestCase):
    def _fixture(self, root: Path):
        for rel in [
            "manifest.json",
            "source/source.png",
            "camera/camera.json",
            "maya/PrimaryMesh.npz",
            "maya/primary_mesh_payload.json",
            "package/official_outputs_contract.json",
            "output_index.json",
            "geometry/canonical/pointcloud.ply",
            "diagnostics/geometry_health.json",
            "diagnostics/semantics.json",
        ]:
            path=root/rel
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(("fixture:"+rel).encode("utf-8"))
        return SimpleNamespace(
            root=root.resolve(),
            run_id=root.name,
            scene_contract_id="scene1",
            branch_mode="Refined / P9 Clone · P10 Reserved",
            source_image=(root/"source/source.png").resolve(),
            camera=(root/"camera/camera.json").resolve(),
            primary_mesh=(root/"maya/PrimaryMesh.npz").resolve(),
            primary_mesh_payload=(root/"maya/primary_mesh_payload.json").resolve(),
            official_outputs_contract=(root/"package/official_outputs_contract.json").resolve(),
            output_index=(root/"output_index.json").resolve(),
            optional={
                "point_cloud":(root/"geometry/canonical/pointcloud.ply").resolve(),
                "geometry_health":(root/"diagnostics/geometry_health.json").resolve(),
            },
        )

    def test_inventory_references_full_run_and_freezes_critical_hashes(self):
        from p10_lab.p9_dependency_inventory import build_p9_dependency_inventory
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"run1"; root.mkdir()
            boundary=self._fixture(root)
            with patch("p10_lab.p9_dependency_inventory.validate_official_run",return_value=boundary):
                inventory=build_p9_dependency_inventory(root)
            self.assertEqual(inventory["p9_authority_policy"],"REFERENCE_FULL_PERSISTED_RUN; DO_NOT_COPY_OR_REDUCE")
            self.assertIn("camera",inventory["critical"])
            self.assertIn("primary_mesh",inventory["critical"])
            self.assertGreaterEqual(inventory["persisted_file_count"],10)
            persisted={x["relative_path"] for x in inventory["persisted_files"]}
            self.assertIn("diagnostics/semantics.json",persisted)

    def test_validation_fails_when_critical_p9_bytes_change(self):
        from p10_lab.p9_dependency_inventory import write_p9_dependency_inventory,validate_p9_dependency_inventory
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"run1"; root.mkdir()
            boundary=self._fixture(root)
            inv=Path(tmp)/"inventory.json"
            with patch("p10_lab.p9_dependency_inventory.validate_official_run",return_value=boundary):
                write_p9_dependency_inventory(root,inv)
                (root/"camera/camera.json").write_text("changed",encoding="utf-8")
                with self.assertRaisesRegex(ValueError,"changed after Route Setup"):
                    validate_p9_dependency_inventory(inv)


if __name__=="__main__":
    unittest.main()
