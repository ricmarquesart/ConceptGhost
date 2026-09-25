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
            (p9 / "logs").mkdir()
            (p9 / "logs" / "stage06_07_progress.log").write_text("P9 LOG\n", encoding="utf-8")
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
            self.assertIn(
                "p9_authority/logs/stage06_07_progress.log",
                names,
            )
            self.assertNotIn("p10_attempt/gate8/future_mesh.ply", names)
            self.assertNotIn("p9_authority/maya/scene.ma", names)
            self.assertIn("RUN_AUDIT_BUNDLE_index.json", names)
            self.assertIn("RUN_TECHNICAL_SUMMARY.json", names)
            self.assertIn("RUN_TECHNICAL_SUMMARY.txt", names)
            self.assertTrue((p9/"RUN_TECHNICAL_SUMMARY.json").is_file())
            self.assertTrue((p9/"RUN_TECHNICAL_SUMMARY.txt").is_file())



    def test_technical_summary_exposes_zero_p10_contribution_as_fail(self):
        from p10_lab.run_audit_bundle import build_run_audit_bundle

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=root/"p9"
            attempt=root/"attempt"
            p9.mkdir()
            attempt.mkdir()

            gate6=attempt/"gate6"/"reconstruction_runtime_manifest.json"
            gate6.parent.mkdir(parents=True)
            gate6.write_text(json.dumps({
                "schema":"ConceptGhost.P10ReconstructionRuntime.v0.2",
                "status":"PASS",
                "p10_attempt_root":str(attempt),
            }),encoding="utf-8")

            quality=attempt/"gate6"/"gate6_geometry_quality.json"
            quality.write_text(json.dumps({
                "status":"WARN",
                "sparse":{"point_count":64,"verified_component_count":12,"quality_status":"PASS"},
                "prefusion_mesh":{"vertex_count":12184,"face_count":21089,"mesh_health_status":"PASS"},
            }),encoding="utf-8")

            fusion=attempt/"gate7"/"g7_4"/"protected_fusion_candidate_manifest.json"
            fusion.parent.mkdir(parents=True)
            fusion.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7ProtectedFusionCandidate.v0.1",
                "status":"PASS",
                "counts":{
                    "p10_input_faces":21089,
                    "p10_accepted_faces":0,
                    "p10_rejected_faces":21089,
                    "p10_candidate_vertices":0,
                },
                "reason_counts":{
                    "P9_SOURCE_PROTECTED_OVERLAP":16090,
                    "FREE_SPACE_CONFLICT":4379,
                    "CONFIRMED_FREE_VETO":620,
                },
            }),encoding="utf-8")

            gate7=attempt/"gate7"/"gate7_runtime_manifest.json"
            gate7.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7Runtime.v0.1",
                "status":"PASS",
                "p9_run_id":"p9run",
                "p10_attempt_id":"attempt1",
                "p9_run_dir":str(p9),
                "p10_attempt_root":str(attempt),
                "gate6_runtime_manifest_path":str(gate6),
            }),encoding="utf-8")

            result=build_run_audit_bundle(gate7)
            summary=json.loads((p9/"RUN_TECHNICAL_SUMMARY.json").read_text(encoding="utf-8"))
            comp=summary["completion_effectiveness"]
            self.assertEqual(comp["status"],"FAIL")
            self.assertEqual(comp["p10_input_faces"],21089)
            self.assertEqual(comp["p10_accepted_faces"],0)
            self.assertEqual(comp["rejection_reason_counts"]["P9_SOURCE_PROTECTED_OVERLAP"],16090)
            self.assertTrue(summary["interpretation"]["runtime_pass_is_not_quality_pass"])
            self.assertTrue(summary["interpretation"]["gate8_should_not_promote_when_completion_effectiveness_fail"])
            self.assertEqual(result["completion_effectiveness"]["status"],"FAIL")


    def test_bulk_generated_frames_are_omitted_but_diagnostic_previews_remain(self):
        from p10_lab.run_audit_bundle import build_partial_run_audit_bundle

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=root/"p9"
            attempt=root/"attempt"
            p9.mkdir()
            gate6=attempt/"gate6"/"reconstruction_runtime_manifest.json"
            gate6.parent.mkdir(parents=True)
            gate6.write_text(json.dumps({
                "schema":"ConceptGhost.P10ReconstructionRuntime.v0.2",
                "runtime_status":"PASS",
                "run_id":"p9",
                "p10_attempt_id":"attempt",
                "p10_attempt_root":str(attempt),
            }),encoding="utf-8")

            dense_images=attempt/"gate6"/"dataset"/"dense"/"images"
            dense_images.mkdir(parents=True)
            (dense_images/"frame_000000.png").write_bytes(b"bulk")
            dataset_images=attempt/"gate6"/"dataset"/"images"
            dataset_images.mkdir(parents=True)
            (dataset_images/"frame_000000.png").write_bytes(b"bulk")
            control_frames=attempt/"gate4"/"control_sequence"/"frames"
            control_frames.mkdir(parents=True)
            (control_frames/"frame_0000.png").write_bytes(b"bulk")
            control_masks=attempt/"gate4"/"control_sequence"/"masks"
            control_masks.mkdir(parents=True)
            (control_masks/"frame_0000.png").write_bytes(b"bulk")
            wan_raw=attempt/"gate5"/"wan_raw"/"00_drone_1"
            wan_raw.mkdir(parents=True)
            (wan_raw/"frame_0000.png").write_bytes(b"bulk")
            composite=attempt/"gate5"/"composite"/"00_drone_1"
            composite.mkdir(parents=True)
            (composite/"frame_0000.png").write_bytes(b"bulk")

            useful=attempt/"gate6"/"diagnostics"
            useful.mkdir(parents=True)
            (useful/"metric_overlay.png").write_bytes(b"preview")
            gate4=attempt/"gate4"
            gate4.mkdir(exist_ok=True)
            (gate4/"raw_holes_contact_sheet.png").write_bytes(b"sheet")

            result=build_partial_run_audit_bundle(p9,gate6,output_root=root/"audit")
            with zipfile.ZipFile(result["bundle_path"],"r") as archive:
                names=set(archive.namelist())

            self.assertNotIn("p10_attempt/gate6/dataset/dense/images/frame_000000.png",names)
            self.assertNotIn("p10_attempt/gate6/dataset/images/frame_000000.png",names)
            self.assertNotIn("p10_attempt/gate4/control_sequence/frames/frame_0000.png",names)
            self.assertNotIn("p10_attempt/gate4/control_sequence/masks/frame_0000.png",names)
            self.assertNotIn("p10_attempt/gate5/wan_raw/00_drone_1/frame_0000.png",names)
            self.assertNotIn("p10_attempt/gate5/composite/00_drone_1/frame_0000.png",names)
            self.assertIn("p10_attempt/gate6/diagnostics/metric_overlay.png",names)
            self.assertIn("p10_attempt/gate4/raw_holes_contact_sheet.png",names)
            reasons={row["reason"] for row in result["omitted"]}
            self.assertIn("BULK_DENSE_IMAGE_EXCLUDED_KEEP_MANIFEST_LOGS_PREVIEWS",reasons)
            self.assertIn("BULK_DATASET_IMAGE_EXCLUDED_KEEP_MANIFEST_LOGS_PREVIEWS",reasons)
            self.assertIn("BULK_CONTROL_FRAME_OR_MASK_EXCLUDED_KEEP_GIF_CONTACT_SHEET",reasons)
            self.assertIn("BULK_WAN_OR_COMPOSITE_FRAME_EXCLUDED_KEEP_DRONE_GIFS_AND_CONTACT_SHEETS",reasons)

    def test_p9_authority_is_prioritized_before_optional_p10_when_budget_is_tight(self):
        from p10_lab.run_audit_bundle import build_partial_run_audit_bundle

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=root/"p9"
            attempt=root/"attempt"
            p9.mkdir()
            attempt.mkdir()
            (p9/"manifest.json").write_text(json.dumps({"status":{"run_status":"PASS"}}),encoding="utf-8")
            (p9/"logs").mkdir()
            p9log=p9/"logs"/"critical.log"
            p9log.write_text("P9"*80,encoding="utf-8")
            gate6=attempt/"gate6"/"reconstruction_runtime_manifest.json"
            gate6.parent.mkdir(parents=True)
            gate6.write_text(json.dumps({
                "schema":"ConceptGhost.P10ReconstructionRuntime.v0.2",
                "runtime_status":"PASS",
                "run_id":"p9",
                "p10_attempt_id":"attempt",
                "p10_attempt_root":str(attempt),
            }),encoding="utf-8")
            optional=attempt/"a_optional"
            optional.mkdir()
            for index in range(5):
                (optional/f"optional_{index}.txt").write_text("x"*180,encoding="utf-8")

            budget=gate6.stat().st_size+(p9/"manifest.json").stat().st_size+p9log.stat().st_size+64
            result=build_partial_run_audit_bundle(
                p9,gate6,output_root=root/"audit",max_total_bytes=budget
            )
            with zipfile.ZipFile(result["bundle_path"],"r") as archive:
                names=set(archive.namelist())
            self.assertIn("p9_authority/manifest.json",names)
            self.assertIn("p9_authority/logs/critical.log",names)

    def test_required_reconstruction_manifest_is_reserved_before_optional_size_budget(self):
        from p10_lab.run_audit_bundle import build_partial_run_audit_bundle

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=root/"p9"
            attempt=root/"attempt"
            p9.mkdir()
            attempt.mkdir()
            gate6=attempt/"z_gate6"/"reconstruction_runtime_manifest.json"
            gate6.parent.mkdir(parents=True)
            gate6.write_text(json.dumps({
                "schema":"ConceptGhost.P10ReconstructionRuntime.v0.2",
                "runtime_status":"PASS",
                "run_id":"p9",
                "p10_attempt_id":"attempt",
                "p10_attempt_root":str(attempt),
            }),encoding="utf-8")

            # Optional evidence sorts before z_gate6 and would consume the
            # total budget under the old alphabetical admission policy.
            optional=attempt/"a_optional"
            optional.mkdir()
            for index in range(4):
                (optional/f"evidence_{index}.txt").write_text("x"*180,encoding="utf-8")

            failure=attempt/"gate7_failure_manifest.json"
            failure.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7Failure.v0.1",
                "status":"FAIL",
            }),encoding="utf-8")

            minimum_required=gate6.stat().st_size+failure.stat().st_size+16
            result=build_partial_run_audit_bundle(
                p9,gate6,
                gate7_failure_manifest_path=failure,
                output_root=root/"audit",
                max_total_bytes=minimum_required,
            )
            self.assertTrue(result["reconstruction_runtime_manifest_included"])
            required_rows=[row for row in result["files"] if row.get("required")]
            self.assertGreaterEqual(len(required_rows),2)
            with zipfile.ZipFile(result["bundle_path"],"r") as archive:
                names=set(archive.namelist())
            self.assertIn("p10_attempt/z_gate6/reconstruction_runtime_manifest.json",names)

    def test_default_storage_is_project_sidecar_and_partial_failure_is_supported(self):
        from p10_lab.run_audit_bundle import (
            build_partial_run_audit_bundle,
            default_project_audit_root,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=root/"20260924T080238_094583Z_408c9a94"
            attempt=root/"local_attempt"
            p9.mkdir()
            attempt.mkdir()
            (p9/"manifest.json").write_text(
                json.dumps({"status":{"run_status":"PASS"}}),
                encoding="utf-8",
            )
            gate6=attempt/"gate6"/"reconstruction_runtime_manifest.json"
            gate6.parent.mkdir(parents=True)
            gate6.write_text(json.dumps({
                "schema":"ConceptGhost.P10ReconstructionRuntime.v0.2",
                "runtime_status":"PASS",
                "run_id":p9.name,
                "p10_attempt_id":"attempt-123",
                "p10_attempt_root":str(attempt),
            }),encoding="utf-8")
            failure=attempt/"gate7"/"gate7_failure_manifest.json"
            failure.parent.mkdir(parents=True)
            failure.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7Failure.v0.1",
                "status":"FAIL",
                "failed_stage":"G7_3_FREE_SPACE_EVIDENCE",
            }),encoding="utf-8")

            expected=default_project_audit_root(p9,"attempt-123")
            self.assertEqual(expected, p9.resolve())
            result=build_partial_run_audit_bundle(
                p9,gate6,gate7_failure_manifest_path=failure
            )
            self.assertEqual(result["status"],"PARTIAL_FAILURE")
            self.assertEqual(Path(result["bundle_path"]).parent.resolve(),expected.resolve())
            self.assertTrue((p9/"LATEST_AUDIT.txt").is_file())
            self.assertTrue((p9/"LATEST_AUDIT_INDEX.json").is_file())
            with zipfile.ZipFile(result["bundle_path"],"r") as archive:
                names=set(archive.namelist())
            self.assertIn(
                "p10_attempt/gate6/reconstruction_runtime_manifest.json",names
            )
            self.assertIn(
                "p10_attempt/gate7/gate7_failure_manifest.json",names
            )

if __name__ == "__main__":
    unittest.main()
