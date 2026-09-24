import tempfile
import unittest
from pathlib import Path


class DroneRoutePreviewTests(unittest.TestCase):
    def test_bounds_cover_long_scene_without_using_one_global_square_scale(self):
        try:
            import numpy as np
        except ImportError as error:
            self.skipTest(str(error))
        from p10_lab.drone_route_preview import measure_route_preview_bounds

        vertices=np.asarray([
            [-5.0,-2.0,1.0],
            [ 5.0, 3.0,145.0],
            [ 0.0, 0.0,70.0],
            [ 2.0, 1.0,30.0],
        ],dtype=np.float64)
        bounds=measure_route_preview_bounds(vertices,lower_percentile=0,upper_percentile=100)
        self.assertGreater(bounds.forward.span,bounds.right.span*5)
        self.assertGreater(bounds.up.span,0)

    def test_projection_manifest_links_three_views_to_same_axes(self):
        from p10_lab.drone_route_preview import AxisExtent,RoutePreviewBounds,_projection_manifest

        bounds=RoutePreviewBounds(
            right=AxisExtent(-5,5),
            up=AxisExtent(-2,3),
            forward=AxisExtent(0,100),
        )
        projection=_projection_manifest(bounds,600,560,14)
        panels={p["name"]:p for p in projection["panels"]}
        self.assertEqual((panels["TOP"]["x_axis"],panels["TOP"]["y_axis"]),("right","forward"))
        self.assertEqual((panels["SIDE"]["x_axis"],panels["SIDE"]["y_axis"]),("forward","up"))
        self.assertEqual((panels["FRONT"]["x_axis"],panels["FRONT"]["y_axis"]),("right","up"))
        self.assertEqual(projection["projection_mode"],"PERSPECTIVE_PLUS_ORTHOGRAPHIC_ISOTROPIC")
        for panel in panels.values():
            self.assertEqual(panel["projection_mode"],"ORTHOGRAPHIC_ISOTROPIC")
            ppm=panel["pixels_per_meter"]
            plot=panel["plot_rect_px"]
            xspan=panel["x_extent"]["max"]-panel["x_extent"]["min"]
            yspan=panel["y_extent"]["max"]-panel["y_extent"]["min"]
            self.assertAlmostEqual(xspan*ppm,plot["width"],places=6)
            self.assertAlmostEqual(yspan*ppm,plot["height"],places=6)

    def test_renderer_returns_single_three_panel_image_and_route_metadata(self):
        try:
            import numpy as np
            import torch
        except ImportError as error:
            self.skipTest(str(error))

        from p10_lab.drone_route_plan import DroneMission,DroneRoutePlan,DroneWaypoint
        from p10_lab.drone_route_preview import render_route_authoring_preview
        from p10_lab.panorama import CameraAuthority

        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"mesh.npz"
            # World camera is identity; P10 local forward is -Z.
            vertices=np.asarray([
                [-4.0,-2.0,-5.0],
                [ 4.0, 3.0,-120.0],
                [ 0.0, 0.0,-60.0],
                [ 2.0, 1.0,-30.0],
            ],dtype=np.float32)
            np.savez(path,vertices=vertices)
            camera=CameraAuthority(
                scene_contract_id="test_scene",
                schema="ConceptGhost.CameraBundle.test",
                width=100,
                height=100,
                fx=80.0,
                fy=80.0,
                cx=50.0,
                cy=50.0,
                lens_model="pinhole",
                world_matrix=(
                    (1.0,0.0,0.0,0.0),
                    (0.0,1.0,0.0,0.0),
                    (0.0,0.0,1.0,0.0),
                    (0.0,0.0,0.0,1.0),
                ),
            )
            plan=DroneRoutePlan(missions=(
                DroneMission("drone_1","PATH",(
                    DroneWaypoint(0,0,5),
                    DroneWaypoint(1,-1,100),
                )),
            ))
            image,projection,diagnostics=render_route_authoring_preview(
                path,camera,plan,panel_width=400,panel_height=360,gap=10,max_geometry_points=1000
            )
            self.assertIsInstance(image,torch.Tensor)
            self.assertEqual(tuple(image.shape),(1,750,830,3))
            self.assertEqual(len(projection["panels"]),3)
            self.assertEqual(diagnostics["route_plan"]["missions"][0]["name"],"drone_1")


    def test_interactive_preview_geometry_exposes_point_lods_and_bounded_mesh(self):
        try:
            import numpy as np
        except ImportError as error:
            self.skipTest(str(error))

        from p10_lab.drone_route_preview import build_route_preview_geometry
        from p10_lab.panorama import CameraAuthority

        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"mesh.npz"
            vertices=np.asarray([
                [-1.0,-1.0,-2.0],[1.0,-1.0,-2.0],[1.0,1.0,-2.0],[-1.0,1.0,-2.0],
                [-1.0,-1.0,-4.0],[1.0,-1.0,-4.0],[1.0,1.0,-4.0],[-1.0,1.0,-4.0],
            ],dtype=np.float32)
            faces=np.asarray([
                [0,1,2],[0,2,3],[4,6,5],[4,7,6],
                [0,4,5],[0,5,1],[1,5,6],[1,6,2],
                [2,6,7],[2,7,3],[3,7,4],[3,4,0],
            ],dtype=np.int32)
            np.savez(path,vertices=vertices,faces=faces)
            camera=CameraAuthority(
                scene_contract_id="preview_lod",
                schema="ConceptGhost.CameraBundle.test",
                width=100,height=100,fx=80.0,fy=80.0,cx=50.0,cy=50.0,
                lens_model="pinhole",
                world_matrix=(
                    (1.0,0.0,0.0,0.0),(0.0,1.0,0.0,0.0),
                    (0.0,0.0,1.0,0.0),(0.0,0.0,0.0,1.0),
                ),
            )
            geometry=build_route_preview_geometry(path,camera,max_points=1000,max_mesh_faces=100)
            self.assertEqual(geometry["schema"],"ConceptGhost.P10RoutePreviewGeometry.v0.2")
            self.assertEqual(geometry["default_mode"],"POINTS_MEDIUM")
            self.assertEqual(set(geometry["point_lods"]),{"POINTS_LOW","POINTS_MEDIUM","POINTS_HIGH"})
            self.assertTrue(geometry["mesh_lod"]["available"])
            self.assertEqual(geometry["mesh_lod"]["source_face_count"],12)
            self.assertLessEqual(geometry["mesh_lod"]["face_count"],100)
            self.assertEqual(geometry["mesh_lod"]["authority"],"DISPLAY_ONLY_P9_PRIMARYMESH_LOD")
            self.assertEqual(geometry["authority"],"DISPLAY_ONLY_NEVER_GEOMETRY_AUTHORITY")
            self.assertEqual(geometry["points"],geometry["point_lods"]["POINTS_MEDIUM"]["points"])


if __name__=="__main__":
    unittest.main()
