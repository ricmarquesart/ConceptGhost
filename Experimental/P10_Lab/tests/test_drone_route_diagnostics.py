import unittest


class DroneRouteDiagnosticsTests(unittest.TestCase):
    def _api(self):
        from p10_lab.drone_route_diagnostics import build_drone_route_diagnostics
        from p10_lab.drone_route_plan import DroneMission,DroneRoutePlan,DroneWaypoint
        from p10_lab.path_planner import CameraPath
        return build_drone_route_diagnostics,DroneMission,DroneRoutePlan,DroneWaypoint,CameraPath

    def test_clean_artist_route_is_pass(self):
        build,DroneMission,DroneRoutePlan,DroneWaypoint,CameraPath=self._api()
        plan=DroneRoutePlan(
            missions=(DroneMission("drone_1","PATH",(
                DroneWaypoint(0,0,0),DroneWaypoint(0,0,10)
            )),),
            frames_per_drone=3,
            min_clearance_m=0.2,
        )
        emitted=CameraPath("drone_1",(
            DroneWaypoint(0,0,0).to_relative(),
            DroneWaypoint(0,0,5).to_relative(),
            DroneWaypoint(0,0,10).to_relative(),
        ))
        out=build(
            plan,(emitted,),
            {"drone_1":[0.4,0.5,0.6]},
            {"drone_1":[0.6,0.5,0.4]},
            [],
            route_authority="ARTIST_AUTHORED",
            route_plan_sha256="a"*64,
            scene_contract_id="scene",
            source_run_id="run",
        )
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["active_drone_count"],1)
        self.assertEqual(out["missions"][0]["emitted_frame_count"],3)
        self.assertAlmostEqual(out["missions"][0]["authored_route_length_m"],10.0)
        self.assertAlmostEqual(out["missions"][0]["p9_coverage"]["mean"],0.5)

    def test_collision_hold_is_warn_not_fail(self):
        build,DroneMission,DroneRoutePlan,DroneWaypoint,CameraPath=self._api()
        plan=DroneRoutePlan(
            missions=(DroneMission("drone_1","PATH",(
                DroneWaypoint(0,0,0),DroneWaypoint(0,0,2)
            )),),
            frames_per_drone=3,
        )
        emitted=CameraPath("drone_1",(
            DroneWaypoint(0,0,0).to_relative(),
            DroneWaypoint(0,0,0).to_relative(),
            DroneWaypoint(0,0,2).to_relative(),
        ))
        hold=[{
            "mission_name":"drone_1",
            "held_frame_count":1,
            "resumed_frame_count":1,
            "minimum_candidate_clearance":0.0,
            "minimum_output_clearance":0.5,
        }]
        out=build(
            plan,(emitted,),
            {"drone_1":[0.5,0.5,0.5]},
            {"drone_1":[0.5,0.5,0.5]},
            hold,
            route_authority="ARTIST_AUTHORED",
            route_plan_sha256="b"*64,
            scene_contract_id="scene",
            source_run_id="run",
        )
        self.assertEqual(out["status"],"WARN")
        self.assertEqual(out["total_held_frame_count"],1)
        self.assertIn("COLLISION_HOLD_APPLIED",out["missions"][0]["alerts"])

    def test_frame_count_mismatch_fails_closed_in_diagnostics(self):
        build,DroneMission,DroneRoutePlan,DroneWaypoint,CameraPath=self._api()
        plan=DroneRoutePlan(
            missions=(DroneMission("drone_1","PATH",(
                DroneWaypoint(0,0,0),DroneWaypoint(0,0,2)
            )),),
            frames_per_drone=3,
        )
        emitted=CameraPath("drone_1",(
            DroneWaypoint(0,0,0).to_relative(),
            DroneWaypoint(0,0,2).to_relative(),
        ))
        out=build(
            plan,(emitted,),
            {"drone_1":[0.5,0.5]},
            {"drone_1":[0.5,0.5]},
            [],
            route_authority="ARTIST_AUTHORED",
            route_plan_sha256="c"*64,
            scene_contract_id="scene",
            source_run_id="run",
        )
        self.assertEqual(out["status"],"FAIL")
        self.assertIn("FRAME_COUNT_MISMATCH",out["missions"][0]["alerts"])

    def test_spin_360_reports_zero_authored_translation(self):
        build,DroneMission,DroneRoutePlan,DroneWaypoint,CameraPath=self._api()
        anchor=DroneWaypoint(1,2,3)
        plan=DroneRoutePlan(
            missions=(DroneMission("drone_1","SPIN_360",(anchor,)),),
            frames_per_drone=2,
        )
        emitted=CameraPath("drone_1",(anchor.to_relative(),anchor.to_relative()))
        out=build(
            plan,(emitted,),
            {"drone_1":[0.3,0.3]},
            {"drone_1":[0.7,0.7]},
            [],
            route_authority="ARTIST_AUTHORED",
            route_plan_sha256="d"*64,
            scene_contract_id="scene",
            source_run_id="run",
        )
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["missions"][0]["mode"],"SPIN_360")
        self.assertEqual(out["missions"][0]["authored_route_length_m"],0.0)


if __name__=="__main__":
    unittest.main()
