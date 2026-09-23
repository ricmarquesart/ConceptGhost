import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


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
        with tempfile.TemporaryDirectory() as tmp,              patch("p10_lab.route_handoff.validate_official_run",return_value=boundary):
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
        with tempfile.TemporaryDirectory() as tmp,              patch("p10_lab.route_handoff.validate_official_run",return_value=boundary):
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
        with tempfile.TemporaryDirectory() as tmp,              patch("p10_lab.route_handoff.validate_official_run",return_value=boundary):
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
            loaded={
                "validated":True,
                "source_run_id":"run1",
                "scene_contract_id":"scene1",
                "route_plan_sha256":"a"*64,
                "source_p9_run_dir":str(Path(tmp)/"p9"),
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
