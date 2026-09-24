import json
import tempfile
import unittest
import zipfile
from pathlib import Path


class RunAuditBundleTests(unittest.TestCase):
    def test_node_is_registered_and_terminal(self):
        import p10_lab

        self.assertIn("ConceptGhostP10RunAuditBundle", p10_lab.NODE_CLASS_MAPPINGS)
        node = p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10RunAuditBundle"]
        self.assertEqual(node.CATEGORY, "ConceptGhost/P10 Diagnostics")
        self.assertTrue(node.OUTPUT_NODE)
        required = node.INPUT_TYPES()["required"]
        self.assertTrue(required["gate7_runtime_manifest_path"][1]["forceInput"])
        self.assertTrue(required["visual_pack_manifest_path"][1]["forceInput"])

    def test_bundle_requires_and_includes_reconstruction_runtime_and_future_safe_evidence(self):
        from p10_lab.run_audit_bundle import build_run_audit_bundle

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p9 = root / "p9"
            attempt = root / "attempt"
            p9.mkdir()
            attempt.mkdir()

            (p9 / "manifest.json").write_text(
                json.dumps({"status": {"run_status": "PASS"}}),
                encoding="utf-8",
            )
            (p9 / "diagnostics").mkdir()
            (p9 / "diagnostics" / "geometry_health.json").write_text(
                json.dumps({"pass": True}),
                encoding="utf-8",
            )
            (p9 / "maya").mkdir()
            (p9 / "maya" / "maya_worker_stdout.txt").write_text("PASS\n", encoding="utf-8")
            # Heavy P9 payload must never enter the audit zip.
            (p9 / "maya" / "scene.ma").write_text("heavy", encoding="utf-8")

            gate6 = attempt / "gate6" / "reconstruction_runtime_manifest.json"
            gate6.parent.mkdir(parents=True)
            gate6.write_text(
                json.dumps({
                    "schema": "ConceptGhost.P10ReconstructionRuntime.v0.2",
                    "status": "PASS",
                    "geometry_quality_status": "WARN",
                }),
                encoding="utf-8",
            )
            (attempt / "gate6" / "gate6_geometry_quality.json").write_text(
                json.dumps({"status": "WARN", "alerts": ["EXAMPLE"]}),
                encoding="utf-8",
            )
            # Simulates a future gate added after Gate 7. The collector should
            # pick it up automatically without code changes.
            future = attempt / "gate8" / "future_gate_diagnostic.json"
            future.parent.mkdir(parents=True)
            future.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
            heavy = attempt / "gate8" / "future_mesh.ply"
            heavy.write_text("ply\n", encoding="ascii")

            gate7 = attempt / "gate7" / "gate7_runtime_manifest.json"
            gate7.parent.mkdir(parents=True)
            gate7.write_text(
                json.dumps({
                    "schema": "ConceptGhost.P10Gate7Runtime.v0.1",
                    "status": "PASS",
                    "scene_contract_id": "scene",
                    "p9_run_id": "p9run",
                    "p10_attempt_id": "attempt1",
                    "p9_run_dir": str(p9),
                    "p10_attempt_root": str(attempt),
                    "gate6_runtime_manifest_path": str(gate6),
                }),
                encoding="utf-8",
            )
            visual = attempt / "gate7" / "visual_evidence" / "gate7_visual_evidence_pack.json"
            visual.parent.mkdir(parents=True)
            visual.write_text(
                json.dumps({"schema": "ConceptGhost.P10Gate7VisualEvidencePack.v0.1", "status": "PASS"}),
                encoding="utf-8",
            )
            (visual.parent / "review.png").write_bytes(b"png")

            result = build_run_audit_bundle(gate7, visual)
            bundle = Path(result["bundle_path"])
            self.assertTrue(bundle.is_file())
            self.assertTrue(result["reconstruction_runtime_manifest_included"])
            self.assertEqual(result["status"], "PASS")

            with zipfile.ZipFile(bundle, "r") as archive:
                names = set(archive.namelist())
            self.assertIn(
                "p10_attempt/gate6/reconstruction_runtime_manifest.json",
                names,
            )
            self.assertIn(
                "p10_attempt/gate8/future_gate_diagnostic.json",
                names,
            )
            self.assertIn(
                "p9_authority/diagnostics/geometry_health.json",
                names,
            )
            self.assertNotIn("p10_attempt/gate8/future_mesh.ply", names)
            self.assertNotIn("p9_authority/maya/scene.ma", names)
            self.assertIn("RUN_AUDIT_BUNDLE_index.json", names)


if __name__ == "__main__":
    unittest.main()
