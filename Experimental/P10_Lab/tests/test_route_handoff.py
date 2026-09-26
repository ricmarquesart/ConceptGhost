import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.test_p9_boundary import _write_official_run


class RouteHandoffTests(unittest.TestCase):
    def _bound_plan(self, authority="ARTIST_AUTHORED"):
        from p10_lab.drone_route_plan import DroneMission,DroneRoutePlan,DroneWaypoint,bind_route_plan
        plan=DroneRoutePlan(
            missions=(DroneMission(
                "drone_1","PATH",
                (DroneWaypoint(0,0,0),DroneWaypoint(0,0,5)),
                orientation_mode="LOOK_AT_TARGET",
                look_target=DroneWaypoint(0,0,3),
            ),),
            frames_per_drone=30,
        )
        return bind_route_plan(
            plan,
            scene_contract_id="scene1",
            source_run_id="run1",
            route_authority=authority,
        )

    def test_seed_route_waits_without_starting_production(self):
        from p10_lab.route_handoff import commit_route_setup
        boundary=SimpleNamespace(scene_contract_id="scene1",run_id="run1")
        with tempfile.TemporaryDirectory() as tmp, \
             patch("p10_lab.route_handoff.validate_official_run",return_value=boundary), \
             patch("p10_lab.route_handoff.write_p9_dependency_inventory",return_value={"inventory_sha256":"i"*64,"persisted_file_count":7}):
            result=commit_route_setup(
                Path(tmp)/"p9",
                json.dumps(self._bound_plan("EDITABLE_SEED")),
                Path(tmp)/"route_setup",
            )
            self.assertEqual(result["status"],"WAITING_FOR_ARTIST_ROUTE")
            self.assertFalse(result["production_ready"])
            self.assertEqual(result["production_entry_path"],"")

    def test_artist_route_commits_and_loads_without_modifying_p9(self):
        from p10_lab.route_handoff import commit_route_setup,load_production_entry
        boundary=SimpleNamespace(scene_contract_id="scene1",run_id="run1")
        with tempfile.TemporaryDirectory() as tmp, \
             patch("p10_lab.route_handoff.validate_official_run",return_value=boundary), \
             patch("p10_lab.route_handoff.write_p9_dependency_inventory",return_value={"inventory_sha256":"i"*64,"persisted_file_count":7}), \
             patch("p10_lab.route_handoff.validate_p9_dependency_inventory",return_value={"inventory_sha256":"i"*64,"persisted_file_count":7}):
            p9=Path(tmp)/"p9"
            p9.mkdir()
            result=commit_route_setup(
                p9,
                json.dumps(self._bound_plan()),
                Path(tmp)/"route_setup",
            )
            self.assertEqual(result["status"],"READY")
            loaded=load_production_entry(result["production_entry_path"])
            self.assertTrue(loaded["validated"])
            self.assertEqual(loaded["source_p9_run_dir"],str(p9.resolve()))
            self.assertIn('"route_authority": "ARTIST_AUTHORED"',loaded["route_plan_json"])
            self.assertFalse(loaded["p9_authority_changed"])

    def test_committed_route_tamper_fails_closed(self):
        from p10_lab.route_handoff import commit_route_setup,load_production_entry
        boundary=SimpleNamespace(scene_contract_id="scene1",run_id="run1")
        with tempfile.TemporaryDirectory() as tmp, \
             patch("p10_lab.route_handoff.validate_official_run",return_value=boundary), \
             patch("p10_lab.route_handoff.write_p9_dependency_inventory",return_value={"inventory_sha256":"i"*64,"persisted_file_count":7}), \
             patch("p10_lab.route_handoff.validate_p9_dependency_inventory",return_value={"inventory_sha256":"i"*64,"persisted_file_count":7}):
            result=commit_route_setup(
                Path(tmp)/"p9",
                json.dumps(self._bound_plan()),
                Path(tmp)/"route_setup",
            )
            entry=json.loads(Path(result["production_entry_path"]).read_text(encoding="utf-8"))
            Path(entry["committed_route_path"]).write_text("{}",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"bytes changed"):
                load_production_entry(result["production_entry_path"])


    def test_each_production_attempt_is_unique_and_preserves_prior_directory(self):
        from p10_lab.route_handoff import create_p10_attempt
        with tempfile.TemporaryDirectory() as tmp:
            p9=_write_official_run(
                Path(tmp)/"run1",
                branch_mode="Refined / P9 Clone",
                scene_id="scene1",
            )
            loaded={
                "validated":True,
                "source_run_id":"run1",
                "scene_contract_id":"scene1",
                "route_plan_sha256":"a"*64,
                "source_p9_run_dir":str(p9),
                "production_entry_path":str(Path(tmp)/"entry.json"),
                "route_authority":"ARTIST_AUTHORED",
            }
            first=create_p10_attempt(loaded,Path(tmp)/"output")
            second=create_p10_attempt(loaded,Path(tmp)/"output")
            self.assertNotEqual(first["p10_attempt_id"],second["p10_attempt_id"])
            self.assertTrue(Path(first["attempt_root"]).is_dir())
            self.assertTrue(Path(second["attempt_root"]).is_dir())
            pointer=json.loads(Path(second["latest_pointer_path"]).read_text(encoding="utf-8"))
            self.assertEqual(pointer["p10_attempt_id"],second["p10_attempt_id"])
            self.assertTrue(Path(first["attempt_manifest_path"]).is_file())
            first_manifest=json.loads(Path(first["attempt_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(
                first_manifest["gate_output_initialization"]["mode"],
                "AUTOMATIC_AT_ATTEMPT_CREATION",
            )
            self.assertFalse(
                first_manifest["gate_output_initialization"]["manual_backfill_required"]
            )
            gate_root=Path(first_manifest["gate_output_root"])
            self.assertTrue((gate_root/"GATE_01_FOUNDATION_RUN").is_dir())
            self.assertTrue((gate_root/"GATE_02_P9_TO_P10_HANDOFF").is_dir())
            self.assertTrue((gate_root/"GATE_03_KNOWN_UNKNOWN").is_dir())

            result_root=Path(first_manifest["result_output_root"])
            self.assertTrue((result_root/"RESULT_INDEX.json").is_file())
            self.assertTrue((result_root/"CG_00_P9_AUTHORITY"/"OUTPUTS"/"source_concept.png").is_file())
            self.assertTrue((result_root/"CG_00_P9_AUTHORITY"/"OUTPUTS"/"camera.json").is_file())
            self.assertTrue((result_root/"CG_00_P9_AUTHORITY"/"PREVIEWS"/"source_concept.png").is_file())
            self.assertTrue((result_root/"CG_18_COMPLETE_RELEASE"/"OUTPUTS").is_dir())
            self.assertFalse(
                first_manifest["result_output_contract"]["manual_backfill_required"]
            )
            self.assertTrue(
                first_manifest["result_output_contract"]["physical_evidence_required_for_functional_pass"]
            )

    def test_auto_latest_resolves_committed_entry(self):
        from p10_lab.route_handoff import _resolve_production_entry_path
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            target=output/"conceptghost"/"p10_route_setup"/"run1"/"production_entry.json"
            target.parent.mkdir(parents=True)
            target.write_text("{}",encoding="utf-8")
            pointer=output/"conceptghost"/"p10_route_setup"/"LATEST_PRODUCTION_ENTRY.json"
            pointer.write_text(json.dumps({
                "schema":"ConceptGhost.P10LatestProductionEntryPointer.v0.1",
                "production_entry_path":str(target),
                "pointer_only":True,
            }),encoding="utf-8")
            self.assertEqual(_resolve_production_entry_path("AUTO_LATEST",output),target.resolve())


    def test_auto_latest_without_route_creates_p9_source_entry_for_cg02_cg03(self):
        from p10_lab.route_handoff import _load_entry_by_schema,_resolve_production_entry_path
        boundary=SimpleNamespace(
            root=None,
            scene_contract_id="scene1",
            run_id="run1",
        )
        inventory={
            "inventory_sha256":"i"*64,
            "persisted_file_count":7,
            "source_run_id":"run1",
            "scene_contract_id":"scene1",
        }
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"output"
            p9=Path(tmp)/"p9"
            p9.mkdir()
            boundary.root=p9.resolve()
            route_setup=output/"conceptghost"/"p10_route_setup"/"run1"
            route_setup.mkdir(parents=True)
            (route_setup/"route_setup_status.json").write_text(json.dumps({
                "source_p9_run_dir":str(p9),
                "source_run_id":"run1",
                "scene_contract_id":"scene1",
            }),encoding="utf-8")

            def fake_write(_run_dir,path):
                Path(path).parent.mkdir(parents=True,exist_ok=True)
                Path(path).write_text("{}",encoding="utf-8")
                return inventory

            with patch("p10_lab.route_handoff.validate_official_run",return_value=boundary), \
                 patch("p10_lab.route_handoff.write_p9_dependency_inventory",side_effect=fake_write), \
                 patch("p10_lab.route_handoff.validate_p9_dependency_inventory",return_value=inventory):
                resolved=_resolve_production_entry_path("AUTO_LATEST",output)
                loaded=_load_entry_by_schema(resolved)

            self.assertEqual(resolved.name,"source_entry.json")
            self.assertTrue(loaded["source_only"])
            self.assertEqual(loaded["route_authority"],"DEFERRED_UNTIL_CG04")
            self.assertEqual(loaded["route_required_from_stage"],"CG_04_CAMERA_RAILS")
            self.assertIn("ROUTE_NOT_REQUIRED_FOR_CG02_CG03",loaded["route_plan_json"])

    def test_source_only_attempt_has_no_fake_route_hash(self):
        from p10_lab.route_handoff import create_p10_attempt
        with tempfile.TemporaryDirectory() as tmp:
            p9=_write_official_run(
                Path(tmp)/"run1",
                branch_mode="Refined / P9 Clone",
                scene_id="scene1",
            )
            loaded={
                "validated":True,
                "source_only":True,
                "source_run_id":"run1",
                "scene_contract_id":"scene1",
                "route_plan_sha256":"",
                "source_p9_run_dir":str(p9),
                "production_entry_path":str(Path(tmp)/"source_entry.json"),
                "route_authority":"DEFERRED_UNTIL_CG04",
                "route_required_from_stage":"CG_04_CAMERA_RAILS",
            }
            attempt=create_p10_attempt(loaded,Path(tmp)/"output")
            manifest=json.loads(Path(attempt["attempt_manifest_path"]).read_text(encoding="utf-8"))
            self.assertTrue(manifest["source_only_entry"])
            self.assertIsNone(manifest["route_plan_sha256"])
            self.assertEqual(manifest["route_required_from_stage"],"CG_04_CAMERA_RAILS")


class TwoStageWorkflowTests(unittest.TestCase):
    def _base(self):
        return {
            "last_node_id":2005,
            "last_link_id":178,
            "nodes":[
                {
                    "id":1015,
                    "type":"ConceptGhostExportBundle",
                    "title":"REFINED/P9 CLONE · P10 RESERVED · 06 · EXPORT",
                    "order":1,
                    "outputs":[{"name":"run_dir","type":"STRING","links":[]}],
                },
                {
                    "id":15,
                    "type":"ConceptGhostExportBundle",
                    "title":"BASELINE/P9 · 06 · EXPORT",
                    "order":2,
                    "outputs":[{"name":"run_dir","type":"STRING","links":[]}],
                },
            ],
            "links":[],
        }

    def test_route_setup_stops_before_wan_and_gate6(self):
        from p10_lab.workflow_integration import integrate_route_setup_refined_preview
        patched=integrate_route_setup_refined_preview(self._base())
        types={node["type"] for node in patched["nodes"]}
        self.assertIn("ConceptGhostP10DroneRouteAuthoring",types)
        self.assertIn("ConceptGhostP10RouteCommit",types)
        self.assertNotIn("ConceptGhostP10RefinedEvidencePreview",types)
        self.assertNotIn("ConceptGhostP10WanSequentialSampler",types)
        self.assertNotIn("ConceptGhostP10ReconstructionRuntime",types)

    def test_production_workflow_has_no_p9_solver_dependency(self):
        from p10_lab.workflow_integration import integrate_p10_production_from_entry
        patched=integrate_p10_production_from_entry(self._base())
        types={node["type"] for node in patched["nodes"]}
        self.assertIn("ConceptGhostP10ProductionEntryLoader",types)
        self.assertIn("ConceptGhostP10RefinedEvidencePreview",types)
        self.assertIn("ConceptGhostP10WanSequentialSampler",types)
        self.assertIn("ConceptGhostP10ReconstructionRuntime",types)
        self.assertNotIn("ConceptGhostExportBundle",types)
        self.assertFalse(patched["extra"]["conceptghost"]["p9_solver_present"])

        by_type={node["type"]:node for node in patched["nodes"]}
        loader=by_type["ConceptGhostP10ProductionEntryLoader"]
        evidence=by_type["ConceptGhostP10RefinedEvidencePreview"]
        incoming=[link for link in patched["links"] if link[3]==evidence["id"]]
        self.assertTrue(any(link[1]==loader["id"] and link[2]==0 for link in incoming))
        self.assertTrue(any(link[1]==loader["id"] and link[2]==1 for link in incoming))
        self.assertTrue(any(link[1]==loader["id"] and link[2]==2 for link in incoming))
        self.assertEqual(
            [item["name"] for item in loader["outputs"]],
            ["run_dir","route_plan_json","p10_attempt_root","p10_attempt_id","diagnostics_json"],
        )


if __name__=="__main__":
    unittest.main()
