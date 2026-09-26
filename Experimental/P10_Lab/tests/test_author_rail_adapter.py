import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_p9_boundary import _write_official_run


class AuthorRailAdapterTests(unittest.TestCase):
    def test_path_is_converted_to_author_per_point_look_and_origin_is_explicit(self):
        from p10_lab.author_rail_adapter import mission_to_author_anchors
        from p10_lab.drone_route_plan import DroneMission, DroneWaypoint

        mission=DroneMission(
            "drone_1",
            "PATH",
            (
                DroneWaypoint(0.2,0.1,0.4),
                DroneWaypoint(0.4,0.2,1.0),
                DroneWaypoint(0.1,0.3,1.5),
            ),
            orientation_mode="LOOK_ALONG_PATH",
        )
        anchors,details=mission_to_author_anchors(mission)
        rows=[line for line in anchors.splitlines() if line.strip()]
        self.assertEqual(len(rows),4)
        self.assertTrue(rows[0].startswith("0.000000, 0.000000, 0.000000"))
        self.assertTrue(details["prepended_panorama_origin"])
        self.assertEqual(details["author_orientation"],"per_point_look")
        self.assertEqual(details["author_frame_length"],81)

    def test_look_at_target_is_preserved_as_per_anchor_target(self):
        from p10_lab.author_rail_adapter import mission_to_author_anchors
        from p10_lab.drone_route_plan import DroneMission, DroneWaypoint

        target=DroneWaypoint(0.0,0.5,2.0)
        mission=DroneMission(
            "drone_1",
            "PATH",
            (DroneWaypoint(0,0,0),DroneWaypoint(0.2,0.1,1.0)),
            orientation_mode="LOOK_AT_TARGET",
            look_target=target,
        )
        anchors,_=mission_to_author_anchors(mission)
        rows=anchors.splitlines()
        self.assertTrue(rows[0].endswith("0.000000, 0.500000, 2.000000"))
        self.assertTrue(rows[1].endswith("0.000000, 0.500000, 2.000000"))

    def test_spin_mission_fails_closed_in_author_camera_plot_v1(self):
        from p10_lab.author_rail_adapter import mission_to_author_anchors
        from p10_lab.contracts import ContractError
        from p10_lab.drone_route_plan import DroneMission, DroneWaypoint

        mission=DroneMission(
            "spin",
            "SPIN_360",
            (DroneWaypoint(0,0,0),),
        )
        with self.assertRaisesRegex(ContractError,"requires PATH"):
            mission_to_author_anchors(mission)

    def test_rail_gate_publishes_physical_evidence_before_pass(self):
        from p10_lab.author_rail_adapter import ConceptGhostP10AuthorRailGate
        from p10_lab.drone_route_plan import (
            DroneMission,DroneRoutePlan,DroneWaypoint,bind_route_plan,
        )
        from p10_lab.result_output_contract import initialize_result_output_tree

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=_write_official_run(
                root/"run1",
                branch_mode="Refined / P9 Clone",
                scene_id="scene1",
            )
            plan=DroneRoutePlan(
                missions=(
                    DroneMission(
                        "drone_1","PATH",
                        (DroneWaypoint(0,0,0),DroneWaypoint(0,0,1)),
                        orientation_mode="LOOK_ALONG_PATH",
                    ),
                ),
                frames_per_drone=30,
            )
            bound=bind_route_plan(
                plan,
                scene_contract_id="scene1",
                source_run_id="run1",
                route_authority="ARTIST_AUTHORED",
            )
            attempt=root/"output"/"conceptghost"/"p10_attempts"/"run1"/"attempt1"
            attempt.mkdir(parents=True)
            (attempt/"attempt_manifest.json").write_text(json.dumps({
                "schema":"ConceptGhost.P10Attempt.v0.1",
                "p10_attempt_id":"attempt1",
                "parent_p9_run_id":"run1",
                "scene_contract_id":"scene1",
                "source_p9_run_dir":str(p9.resolve()),
            }),encoding="utf-8")
            initialize_result_output_tree(
                attempt,
                p10_attempt_id="attempt1",
                p9_run_id="run1",
                scene_contract_id="scene1",
                source_p9_run_dir=p9,
            )
            rail=root/"author_rail.json"
            rail.write_text(json.dumps([[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]]),encoding="utf-8")

            def fake_save(path,image,grayscale=False):
                path=Path(path)
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b"png")
                return {"path":str(path),"sha256":"a"*64,"width":640,"height":360,"mode":"RGB"}

            with patch("p10_lab.author_rail_adapter._save_image",side_effect=fake_save):
                result=ConceptGhostP10AuthorRailGate().publish(
                    str(attempt),
                    "attempt1",
                    str(p9),
                    "scene1",
                    json.dumps(bound),
                    0,
                    "0,0,0,0,0,1\n0,0,1,0,0,2",
                    "drone_1",
                    object(),
                    object(),
                    object(),
                    str(rail),
                )

            self.assertEqual(result[3],"drone_1")
            stage=attempt/"RESULTS"/"CG_04_CAMERA_RAILS"
            self.assertTrue((stage/"OUTPUTS"/"drone_1"/"rail.json").is_file())
            self.assertTrue((stage/"PREVIEWS"/"drone_1_camera_path.png").is_file())
            status=json.loads((stage/"STATUS.json").read_text(encoding="utf-8"))
            self.assertEqual(status["functional_status"],"PASS")


if __name__=="__main__":
    unittest.main()
