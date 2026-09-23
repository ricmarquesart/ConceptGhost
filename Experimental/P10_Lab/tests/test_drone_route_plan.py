import unittest


class DroneRoutePlanTests(unittest.TestCase):
    def test_plan_supports_one_to_seven_drones(self):
        from p10_lab.drone_route_plan import DroneMission, DroneRoutePlan, DroneWaypoint

        missions=tuple(
            DroneMission(
                name=f"drone_{i+1}",
                mode="PATH",
                waypoints=(DroneWaypoint(0,0,0),DroneWaypoint(0,0,1+i)),
            )
            for i in range(7)
        )
        plan=DroneRoutePlan(missions=missions)
        self.assertEqual(len(plan.missions),7)
        with self.assertRaises(ValueError):
            DroneRoutePlan(missions=missions+(missions[0],))

    def test_path_sampling_uses_exact_global_frame_count(self):
        from p10_lab.drone_route_plan import DroneMission, DroneWaypoint, sample_mission

        mission=DroneMission(
            "drone_1","PATH",
            (DroneWaypoint(0,0,0),DroneWaypoint(0,0,10)),
        )
        path=sample_mission(mission,30)
        self.assertEqual(len(path.waypoints),30)
        self.assertAlmostEqual(path.waypoints[0].forward,0.0)
        self.assertAlmostEqual(path.waypoints[-1].forward,10.0)
        self.assertTrue(all(p.look_forward>0.99 for p in path.waypoints))

    def test_look_at_target_tracks_fixed_scene_target(self):
        from p10_lab.drone_route_plan import DroneMission, DroneWaypoint, sample_mission

        mission=DroneMission(
            "drone_target",
            "PATH",
            (DroneWaypoint(-2,0,0),DroneWaypoint(2,0,0)),
            orientation_mode="LOOK_AT_TARGET",
            look_target=DroneWaypoint(0,0,5),
        )
        path=sample_mission(mission,5)
        self.assertEqual(len(path.waypoints),5)
        self.assertGreater(path.waypoints[0].look_right,0.0)
        self.assertAlmostEqual(path.waypoints[2].look_right,0.0,places=6)
        self.assertLess(path.waypoints[-1].look_right,0.0)
        self.assertTrue(all(p.look_forward>0.8 for p in path.waypoints))

    def test_manual_direction_is_constant_for_path(self):
        from p10_lab.drone_route_plan import DroneMission, DroneWaypoint, sample_mission

        mission=DroneMission(
            "drone_manual",
            "PATH",
            (DroneWaypoint(0,0,0),DroneWaypoint(0,0,10)),
            orientation_mode="MANUAL_DIRECTION",
            manual_direction=DroneWaypoint(1,1,0),
        )
        path=sample_mission(mission,7)
        expected=2**-0.5
        for point in path.waypoints:
            self.assertAlmostEqual(point.look_right,expected,places=6)
            self.assertAlmostEqual(point.look_up,expected,places=6)
            self.assertAlmostEqual(point.look_forward,0.0,places=6)

    def test_reorient_after_collision_hold_preserves_look_at_target(self):
        from p10_lab.drone_route_plan import (
            DroneMission,DroneWaypoint,apply_hold_and_resume_clearance,
            reorient_path_for_mission,sample_mission,
        )

        mission=DroneMission(
            "drone_target","PATH",
            (DroneWaypoint(-2,0,0),DroneWaypoint(2,0,0)),
            orientation_mode="LOOK_AT_TARGET",
            look_target=DroneWaypoint(0,0,5),
        )
        sampled=sample_mission(mission,5)
        safe,_=apply_hold_and_resume_clearance(
            sampled,
            lambda point: 0.0 if -0.1<=point.right<=1.1 else 1.0,
            min_clearance=0.5,
        )
        oriented=reorient_path_for_mission(mission,safe)
        for point in oriented.waypoints:
            dx=-point.right
            dz=5.0-point.forward
            length=(dx*dx+dz*dz)**0.5
            self.assertAlmostEqual(point.look_right,dx/length,places=6)
            self.assertAlmostEqual(point.look_forward,dz/length,places=6)

    def test_legacy_v01_bound_hash_migrates_to_v02(self):
        from p10_lab.drone_route_plan import (
            DroneMission,DroneRoutePlan,DroneWaypoint,_legacy_v01_route_hash,
            parse_bound_route_plan,
        )

        plan=DroneRoutePlan(
            missions=(DroneMission(
                "drone_1","PATH",
                (DroneWaypoint(0,0,0),DroneWaypoint(0,0,5)),
            ),),
        )
        payload={
            "schema":"ConceptGhost.P10DroneRoutePlan.v0.1",
            "binding_schema":"ConceptGhost.P10BoundDroneRoutePlan.v0.1",
            "coordinate_space":"P9_CAMERA_LOCAL_RIGHT_UP_FORWARD_METERS",
            "maximum_drone_count":7,
            "frames_per_drone":30,
            "collision_mode":"HOLD_AND_RESUME",
            "min_clearance_m":0.20,
            "missions":[{
                "name":"drone_1",
                "mode":"PATH",
                "enabled":True,
                "waypoints":[
                    {"right":0.0,"up":0.0,"forward":0.0},
                    {"right":0.0,"up":0.0,"forward":5.0},
                ],
            }],
            "scene_contract_id":"scene",
            "source_run_id":"run",
            "route_authority":"ARTIST_AUTHORED",
        }
        payload["route_plan_sha256"]=_legacy_v01_route_hash(
            plan,
            scene_contract_id="scene",
            source_run_id="run",
            route_authority="ARTIST_AUTHORED",
        )
        restored,authority,new_hash=parse_bound_route_plan(
            payload,
            expected_scene_contract_id="scene",
            expected_source_run_id="run",
            require_hash=True,
        )
        self.assertEqual(restored.missions[0].orientation_mode,"LOOK_ALONG_PATH")
        self.assertEqual(authority,"ARTIST_AUTHORED")
        self.assertEqual(len(new_hash),64)
        self.assertNotEqual(new_hash,payload["route_plan_sha256"])

    def test_spin_360_stays_fixed_and_rotates_full_yaw(self):
        from p10_lab.drone_route_plan import DroneMission, DroneWaypoint, sample_mission

        mission=DroneMission("drone_1","SPIN_360",(DroneWaypoint(2,3,4),))
        path=sample_mission(mission,12)
        self.assertEqual(len(path.waypoints),12)
        self.assertTrue(all((p.right,p.up,p.forward)==(2.0,3.0,4.0) for p in path.waypoints))
        self.assertTrue(any(p.look_right>0.95 for p in path.waypoints))
        self.assertTrue(any(p.look_forward<-0.95 for p in path.waypoints))

    def test_hold_and_resume_never_outputs_blocked_position(self):
        from p10_lab.drone_route_plan import (
            DroneMission,
            DroneWaypoint,
            apply_hold_and_resume_clearance,
            sample_mission,
        )

        mission=DroneMission(
            "drone_1","PATH",
            (DroneWaypoint(0,0,0),DroneWaypoint(0,0,10)),
        )
        path=sample_mission(mission,11)

        def clearance(point):
            return 0.0 if 4.0<=point.forward<=6.0 else 1.0

        safe,report=apply_hold_and_resume_clearance(
            path,
            clearance_query=clearance,
            min_clearance=0.5,
        )
        self.assertEqual(len(safe.waypoints),11)
        self.assertEqual(report.held_frame_count,3)
        self.assertEqual(report.resumed_frame_count,1)
        self.assertTrue(all(not (4.0<=p.forward<=6.0) for p in safe.waypoints))
        self.assertGreaterEqual(report.minimum_output_clearance,0.5)

    def test_hold_resume_does_not_teleport_across_blocked_segment(self):
        from p10_lab.drone_route_plan import (
            DroneMission,
            DroneWaypoint,
            apply_hold_and_resume_clearance,
            sample_mission,
        )

        mission=DroneMission(
            "drone_1","PATH",
            (DroneWaypoint(-2,0,0),DroneWaypoint(2,0,0)),
        )
        path=sample_mission(mission,5)

        def point_clearance(point):
            return 1.0

        def segment_blocked(start,end):
            return min(start.right,end.right)<=0.0<=max(start.right,end.right)

        safe,report=apply_hold_and_resume_clearance(
            path,
            point_clearance,
            min_clearance=0.5,
            segment_is_blocked=segment_blocked,
        )
        rights=[p.right for p in safe.waypoints]
        self.assertTrue(all(value<=0.0 for value in rights))
        self.assertGreater(report.held_frame_count,0)

    def test_hold_fails_closed_when_route_starts_inside_geometry(self):
        from p10_lab.drone_route_plan import (
            DroneMission,
            DroneWaypoint,
            apply_hold_and_resume_clearance,
            sample_mission,
        )

        mission=DroneMission(
            "drone_1","PATH",
            (DroneWaypoint(0,0,0),DroneWaypoint(0,0,2)),
        )
        path=sample_mission(mission,3)
        with self.assertRaises(ValueError):
            apply_hold_and_resume_clearance(
                path,
                lambda p: 0.0 if p.forward<0.1 else 1.0,
                min_clearance=0.5,
            )

    def test_bound_route_hash_is_deterministic_and_scene_specific(self):
        from p10_lab.drone_route_plan import (
            DroneMission,DroneRoutePlan,DroneWaypoint,
            bind_route_plan,parse_bound_route_plan,
        )

        plan=DroneRoutePlan(
            missions=(DroneMission("drone_1","PATH",(
                DroneWaypoint(0,0,0),DroneWaypoint(0,0,5)
            )),),
            frames_per_drone=30,
        )
        a=bind_route_plan(
            plan,scene_contract_id="sceneA",source_run_id="runA",
            route_authority="ARTIST_AUTHORED",
        )
        b=bind_route_plan(
            plan,scene_contract_id="sceneA",source_run_id="runA",
            route_authority="ARTIST_AUTHORED",
        )
        self.assertEqual(a["route_plan_sha256"],b["route_plan_sha256"])
        restored,authority,digest=parse_bound_route_plan(
            a,expected_scene_contract_id="sceneA",expected_source_run_id="runA",
            require_hash=True,
        )
        self.assertEqual(restored,plan)
        self.assertEqual(authority,"ARTIST_AUTHORED")
        self.assertEqual(digest,a["route_plan_sha256"])

        with self.assertRaises(ValueError):
            parse_bound_route_plan(
                a,expected_scene_contract_id="sceneB",expected_source_run_id="runA"
            )
        with self.assertRaises(ValueError):
            parse_bound_route_plan(
                a,expected_scene_contract_id="sceneA",expected_source_run_id="runB"
            )

    def test_bound_route_rejects_tampering_but_allows_unhashed_dirty_edit(self):
        from p10_lab.drone_route_plan import (
            DroneMission,DroneRoutePlan,DroneWaypoint,
            bind_route_plan,parse_bound_route_plan,
        )
        plan=DroneRoutePlan(
            missions=(DroneMission("drone_1","PATH",(
                DroneWaypoint(0,0,0),DroneWaypoint(0,0,5)
            )),),
        )
        payload=bind_route_plan(
            plan,scene_contract_id="scene",source_run_id="run",
            route_authority="EDITABLE_SEED",
        )
        tampered=dict(payload)
        tampered["frames_per_drone"]=31
        with self.assertRaises(ValueError):
            parse_bound_route_plan(
                tampered,expected_scene_contract_id="scene",expected_source_run_id="run"
            )

        dirty=dict(tampered)
        dirty.pop("route_plan_sha256",None)
        restored,authority,digest=parse_bound_route_plan(
            dirty,expected_scene_contract_id="scene",expected_source_run_id="run"
        )
        self.assertEqual(restored.frames_per_drone,31)
        self.assertEqual(authority,"EDITABLE_SEED")
        self.assertEqual(len(digest),64)

    def test_roundtrip_manifest(self):
        from p10_lab.drone_route_plan import DroneMission, DroneRoutePlan, DroneWaypoint

        plan=DroneRoutePlan(
            missions=(DroneMission("drone_1","SPIN_360",(DroneWaypoint(1,2,3),)),),
            frames_per_drone=30,
            min_clearance_m=0.25,
        )
        restored=DroneRoutePlan.from_dict(plan.to_dict())
        self.assertEqual(restored,plan)


if __name__ == "__main__":
    unittest.main()
