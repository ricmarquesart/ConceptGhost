from pathlib import Path
import shutil
import subprocess
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
            'pointerdown',
            'pointermove',
            'onExecuted',
            'collision_preflight',
            'blockedSegment',
            '#ff3b58',
            'execute Queue Prompt para aplicar/revalidar',
            'state.plan.route_authority = "ARTIST_AUTHORED"',
            'route_plan_dirty',
            '"Resetar rota"',
            '"Enquadrar tudo"',
            'delete state.plan.route_plan_sha256',
            'function perspectivePanel()',
            'drawPerspectiveScene()',
            'orbitDragging',
            'orbitPanning',
            'orthoViews',
            'orthoPanning',
            'ensureRouteVisible',
            'resetViewportFraming',
            'sanitizeNumericWidgets',
            'drawOrthographicScene',
            'worldFromPanel',
            'wheel',
            'Shift+drag',
            'inspection only',
            '"LOOK_AT_TARGET"',
            '"LOOK_ALONG_PATH"',
            '"MANUAL_DIRECTION"',
            '"Editar alvo"',
            'orientationSelect',
            'look_target',
            'manual_direction',
            'targetDragging',
            'orientationTip',
            'function zoomControlRects(panel)',
            'function hitZoomControl(x, y)',
            'function applyPanelZoom(panel, factor, anchorPoint = null)',
            'function zoomAtCanvasPoint(xy, factor)',
            'function drawZoomControls(panel)',
            'root.addEventListener("wheel"',
            'event.stopPropagation()',
            'event.stopImmediatePropagation?.()',
            '{ passive: false, capture: true }',
            'zoomControl.action === "in" ? 1.35 : (1 / 1.35)',
        ):
            self.assertIn(required, source)

    def test_frontend_has_no_static_background_dependency(self):
        import p10_lab

        path=Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js"
        source=path.read_text(encoding="utf-8")
        self.assertNotIn("loadBackground(",source)
        self.assertNotIn("editor_base_preview",source)
        self.assertNotIn('"Resetar cena"',source)
        self.assertIn('"Resetar rota"',source)
        self.assertEqual(source.count('chainCallback(node, "onExecuted"'),1)


    def test_frontend_has_no_duplicate_or_malformed_declarations(self):
        import p10_lab

        path=Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js"
        source=path.read_text(encoding="utf-8")
        self.assertNotIn("function pushHistory()    };", source)
        self.assertEqual(source.count("function pushHistory() {"), 1)
        self.assertEqual(source.count("function perspectivePanel() {"), 1)
        self.assertEqual(source.count("function eventCoordinates(event) {"), 1)
        self.assertEqual(source.count('droneSelect.addEventListener("change", () => {'), 1)

    def test_route_editor_zoom_is_isolated_from_comfy_workspace(self):
        import p10_lab

        path=Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js"
        source=path.read_text(encoding="utf-8")
        self.assertIn('root.addEventListener("wheel"', source)
        self.assertNotIn('canvas.addEventListener("wheel"', source)
        self.assertIn('{ passive: false, capture: true }', source)
        self.assertIn('event.stopPropagation()', source)
        self.assertIn('event.stopImmediatePropagation?.()', source)
        self.assertIn('zoomAtCanvasPoint(xy, factor)', source)

    def test_each_route_view_has_explicit_zoom_buttons(self):
        import p10_lab

        path=Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js"
        source=path.read_text(encoding="utf-8")
        self.assertIn('function zoomControlRects(panel)', source)
        self.assertIn('function hitZoomControl(x, y)', source)
        self.assertIn('function drawZoomControls(panel)', source)
        self.assertIn('if (perspective) drawZoomControls(perspective);', source)
        self.assertIn('for (const panel of state.projection.panels || []) drawZoomControls(panel);', source)
        self.assertIn('zoomControl.action === "in" ? 1.35 : (1 / 1.35)', source)

    def test_route_edits_preserve_artist_zoom_and_pan(self):
        import p10_lab

        path=Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js"
        source=path.read_text(encoding="utf-8")
        persist_block=source.split("function persist() {",1)[1].split("function setPlan",1)[0]
        self.assertNotIn("ensureRouteVisible()", persist_block)
        stop_block=source.split("const stopDrag = (event) => {",1)[1].split('canvas.addEventListener("pointerup"',1)[0]
        self.assertNotIn("ensureRouteVisible()", stop_block)
        self.assertIn("MAX_ORTHO_ZOOM = 160.0", source)
        self.assertIn("MAX_PERSPECTIVE_ZOOM = 48.0", source)
        self.assertIn("if (needsInitialFraming) ensureRouteVisible();", source)

    def test_route_editor_has_portable_export_import(self):
        import p10_lab

        path=Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js"
        source=path.read_text(encoding="utf-8")
        for required in (
            '"Exportar trajeto"',
            '"Importar trajeto"',
            'ROUTE_PRESET_SCHEMA = "ConceptGhost.P10DroneRoutePreset.v0.1"',
            "function portableRoutePreset()",
            "function exportRoutePreset()",
            "async function importRoutePresetFile(file)",
            'route_authority: "ARTIST_AUTHORED"',
            "delete imported.route_plan_sha256",
            "source_scene_contract_id",
        ):
            self.assertIn(required, source)

    def test_route_editor_uses_higher_detail_four_view(self):
        import p10_lab
        import p10_lab.route_authoring_node as node
        import p10_lab.drone_route_preview as preview

        frontend=(Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js").read_text(encoding="utf-8")
        backend=Path(node.__file__).read_text(encoding="utf-8")
        preview_source=Path(preview.__file__).read_text(encoding="utf-8")
        self.assertIn("GEOMETRY_DRAW_BUDGET = 50000", frontend)
        self.assertIn("max_points=50000", backend)
        self.assertIn("panel_width: int=720", preview_source)
        self.assertIn("panel_height: int=660", preview_source)

    def test_frontend_javascript_parses_when_node_is_available(self):
        import p10_lab

        node=shutil.which("node")
        if not node:
            self.skipTest("node executable unavailable")
        path=Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js"
        result=subprocess.run(
            [node, "--check", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_route_authoring_node_is_registered(self):
        import p10_lab

        self.assertIn("ConceptGhostP10DroneRouteAuthoring", p10_lab.NODE_CLASS_MAPPINGS)
        cls=p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10DroneRouteAuthoring"]
        required=cls.INPUT_TYPES()["required"]
        self.assertIn("route_plan_json",required)
        self.assertIn("frames_per_drone",required)
        self.assertIn("min_clearance_m",required)
        self.assertEqual(cls.RETURN_NAMES[0],"route_workspace")


if __name__=="__main__":
    unittest.main()
