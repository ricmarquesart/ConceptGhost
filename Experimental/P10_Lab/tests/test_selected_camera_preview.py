import unittest


class SelectedCameraPreviewTests(unittest.TestCase):
    def test_route_local_basis_is_orthonormal_for_default_and_custom_look(self):
        from p10_lab.selected_camera_preview import route_local_camera_basis

        for look in ((0.0,0.0,1.0),(0.5,-0.25,1.0),(0.0,1.0,0.01)):
            right,up,forward=route_local_camera_basis(look)
            dot=lambda a,b:sum(x*y for x,y in zip(a,b))
            length=lambda a:dot(a,a)**0.5
            self.assertAlmostEqual(length(right),1.0,places=7)
            self.assertAlmostEqual(length(up),1.0,places=7)
            self.assertAlmostEqual(length(forward),1.0,places=7)
            self.assertAlmostEqual(dot(right,up),0.0,places=7)
            self.assertAlmostEqual(dot(right,forward),0.0,places=7)
            self.assertAlmostEqual(dot(up,forward),0.0,places=7)

    def test_mission_waypoint_look_respects_existing_orientation_authority(self):
        from p10_lab.drone_route_plan import DroneMission,DroneWaypoint
        from p10_lab.selected_camera_preview import mission_waypoint_look

        target=DroneWaypoint(0.0,0.0,5.0)
        look_at=DroneMission(
            "a","PATH",(DroneWaypoint(0,0,0),DroneWaypoint(1,0,0)),
            orientation_mode="LOOK_AT_TARGET",look_target=target,
        )
        self.assertEqual(mission_waypoint_look(look_at,0),(0.0,0.0,1.0))

        manual=DroneMission(
            "b","PATH",(DroneWaypoint(0,0,0),DroneWaypoint(1,0,0)),
            orientation_mode="MANUAL_DIRECTION",manual_direction=DroneWaypoint(1,0,0),
        )
        self.assertEqual(mission_waypoint_look(manual,0),(1.0,0.0,0.0))

        tangent=DroneMission(
            "c","PATH",(DroneWaypoint(0,0,0),DroneWaypoint(2,0,0)),
            orientation_mode="LOOK_ALONG_PATH",
        )
        self.assertEqual(mission_waypoint_look(tangent,0),(1.0,0.0,0.0))

    def test_selected_camera_node_is_registered(self):
        import p10_lab

        self.assertIn("ConceptGhostP10SelectedDroneCameraPreview",p10_lab.NODE_CLASS_MAPPINGS)
        cls=p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10SelectedDroneCameraPreview"]
        required=cls.INPUT_TYPES()["required"]
        for name in ("run_dir","route_plan_json","mission_index","waypoint_index","preview_mode","preview_width"):
            self.assertIn(name,required)
        self.assertEqual(cls.RETURN_NAMES[0],"selected_camera_preview")


if __name__=="__main__":
    unittest.main()
