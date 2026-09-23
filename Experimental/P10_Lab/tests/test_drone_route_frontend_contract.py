from pathlib import Path
import unittest


class DroneRouteFrontendContractTests(unittest.TestCase):
    def test_package_exposes_web_directory(self):
        import p10_lab

        self.assertEqual(p10_lab.WEB_DIRECTORY, "./web/js")
        root=Path(p10_lab.__file__).resolve().parent
        self.assertTrue((root/"web"/"js"/"drone_route_editor.js").is_file())

    def test_frontend_contains_required_artist_controls(self):
        import p10_lab

        path=Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js"
        source=path.read_text(encoding="utf-8")
        for required in (
            'NODE_CLASS = "ConceptGhostP10DroneRouteAuthoring"',
            '"+ Drone"',
            '"− Drone"',
            '"SPIN_360"',
            '"Excluir ponto"',
            '"Desfazer"',
            '"Limpar rota"',
            'node.addDOMWidget',
            'route_plan_json',
            'editor_base_preview',
            'pointerdown',
            'pointermove',
            'onExecuted',
            'collision_preflight',
            'blockedSegment',
            '#ff3b58',
            'colisão precisa ser revalidada',
            'state.plan.route_authority = "ARTIST_AUTHORED"',
        ):
            self.assertIn(required, source)

    def test_route_authoring_node_is_registered(self):
        import p10_lab

        self.assertIn("ConceptGhostP10DroneRouteAuthoring", p10_lab.NODE_CLASS_MAPPINGS)
        cls=p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10DroneRouteAuthoring"]
        required=cls.INPUT_TYPES()["required"]
        self.assertIn("route_plan_json",required)
        self.assertIn("frames_per_drone",required)
        self.assertIn("min_clearance_m",required)
        self.assertEqual(cls.RETURN_NAMES[0],"route_triview")


if __name__=="__main__":
    unittest.main()
