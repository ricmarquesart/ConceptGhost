import unittest


class RouteCollisionPreflightTests(unittest.TestCase):
    def _cloud(self):
        from p10_lab.mesh_clearance import ClearanceCloud
        return ClearanceCloud(
            points=((0.0,0.0,0.0),),
            source_point_count=1,
            retained_point_count=1,
            sampling_stride=1,
            grid_cell_size=0.25,
        )

    def test_preflight_marks_only_crossing_segment_blocked(self):
        from p10_lab.drone_route_plan import DroneMission,DroneRoutePlan,DroneWaypoint
        from p10_lab.route_collision import preflight_drone_route_plan

        plan=DroneRoutePlan(
            missions=(
                DroneMission(
                    "drone_1","PATH",
                    (
                        DroneWaypoint(-2.0,0.0,0.0),
                        DroneWaypoint(-1.0,0.0,0.0),
                        DroneWaypoint(1.0,0.0,0.0),
                        DroneWaypoint(2.0,0.0,0.0),
                    ),
                ),
            ),
            min_clearance_m=0.2,
        )
        report=preflight_drone_route_plan(
            plan,self._cloud(),sample_step=0.05
        )
        mission=report.missions[0]
        self.assertTrue(mission.blocked)
        self.assertEqual(mission.blocked_segment_count,1)
        self.assertFalse(mission.segments[0].blocked)
        self.assertTrue(mission.segments[1].blocked)
        self.assertFalse(mission.segments[2].blocked)

    def test_spin_anchor_inside_clearance_is_blocked(self):
        from p10_lab.drone_route_plan import DroneMission,DroneRoutePlan,DroneWaypoint
        from p10_lab.route_collision import preflight_drone_route_plan

        plan=DroneRoutePlan(
            missions=(DroneMission("drone_1","SPIN_360",(DroneWaypoint(0.0,0.0,0.0),)),),
            min_clearance_m=0.2,
        )
        report=preflight_drone_route_plan(plan,self._cloud())
        self.assertEqual(report.blocked_mission_count,1)
        self.assertTrue(report.missions[0].start_blocked)

    def test_clear_path_reports_zero_blocked_segments(self):
        from p10_lab.drone_route_plan import DroneMission,DroneRoutePlan,DroneWaypoint
        from p10_lab.route_collision import preflight_drone_route_plan

        plan=DroneRoutePlan(
            missions=(
                DroneMission(
                    "drone_1","PATH",
                    (DroneWaypoint(2.0,0.0,0.0),DroneWaypoint(4.0,0.0,0.0)),
                ),
            ),
            min_clearance_m=0.2,
        )
        report=preflight_drone_route_plan(plan,self._cloud(),sample_step=0.05)
        self.assertEqual(report.blocked_mission_count,0)
        self.assertEqual(report.blocked_segment_count,0)
        self.assertFalse(report.missions[0].blocked)


if __name__=="__main__":
    unittest.main()
