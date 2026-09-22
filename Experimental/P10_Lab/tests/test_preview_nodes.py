import json
import tempfile
import unittest
from pathlib import Path

from tests.test_p9_boundary import _write_official_run


class Gate2PreviewNodeTests(unittest.TestCase):
    def _nodes(self):
        try:
            from p10_lab.preview_nodes import (
                ConceptGhostP10BundleLoader,
                ConceptGhostP10CompletionBundleBuilder,
            )
        except ImportError as error:
            self.fail(f"Gate 2 preview nodes are missing: {error}")
        return ConceptGhostP10CompletionBundleBuilder, ConceptGhostP10BundleLoader

    def test_builder_node_creates_bundle_and_machine_readable_diagnostics(self):
        builder_cls, _ = self._nodes()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run = _write_official_run(root / "run-baseline", branch_mode="Baseline / P9")
            output = root / "ConceptGhost_P9_CompletionBundle.zip"

            node = builder_cls()
            response = node.build(str(run), str(output))
            self.assertIn("ui", response)
            self.assertIn("text", response["ui"])
            bundle_path, diagnostics = response["result"]
            report = json.loads(diagnostics)
            self.assertEqual(json.loads(response["ui"]["text"][0])["status"], "PASS")

            self.assertEqual(Path(bundle_path), output.resolve())
            self.assertTrue(output.is_file())
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["source_stage"], "baseline")
            self.assertEqual(report["scene_contract_id"], "cgsc_test_identity")
            self.assertEqual(len(report["bundle_sha256"]), 64)

    def test_loader_node_exposes_normalized_authority_paths_and_diagnostics(self):
        builder_cls, loader_cls = self._nodes()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run = _write_official_run(root / "run-refined", branch_mode="Refined / P9 Clone")
            output = root / "p9.zip"
            builder_cls().build(str(run), str(output))

            response = loader_cls().load(str(output), str(root / "cache"))
            self.assertIn("ui", response)
            self.assertIn("text", response["ui"])
            bundle_root, source, camera, mesh, diagnostics = response["result"]
            report = json.loads(diagnostics)

            self.assertTrue(Path(bundle_root).is_dir())
            self.assertTrue(Path(source).is_file())
            self.assertTrue(Path(camera).is_file())
            self.assertTrue(Path(mesh).is_file())
            self.assertEqual(Path(mesh).suffix, ".npz")
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["source_stage"], "p9")
            self.assertEqual(report["source_equivalent_to"], "baseline")
            self.assertIn("primary_mesh_payload", report["optional_inputs"])

    def test_package_exports_comfyui_node_mappings(self):
        import p10_lab

        self.assertIn("ConceptGhostP10CompletionBundleBuilder", p10_lab.NODE_CLASS_MAPPINGS)
        self.assertIn("ConceptGhostP10BundleLoader", p10_lab.NODE_CLASS_MAPPINGS)
        self.assertEqual(
            p10_lab.NODE_DISPLAY_NAME_MAPPINGS["ConceptGhostP10BundleLoader"],
            "P10 P9 Bundle Loader / Validator",
        )

    def test_node_contract_is_comfyui_discoverable_without_importing_comfyui(self):
        builder_cls, loader_cls = self._nodes()
        for cls in (builder_cls, loader_cls):
            inputs = cls.INPUT_TYPES()
            self.assertIn("required", inputs)
            self.assertTrue(cls.RETURN_TYPES)
            self.assertTrue(cls.RETURN_NAMES)
            self.assertTrue(cls.FUNCTION)
            self.assertEqual(cls.CATEGORY, "ConceptGhost/P10 Lab")
            self.assertTrue(cls.OUTPUT_NODE)


if __name__ == "__main__":
    unittest.main()
