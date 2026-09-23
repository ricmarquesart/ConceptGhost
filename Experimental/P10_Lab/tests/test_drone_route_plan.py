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
