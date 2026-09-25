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
            '"Points Low"',
            '"Points Medium"',
            '"Points High"',
            '"Mesh Surface"',
            '"Mesh Wireframe"',
            'previewModeSelect',
            'pointSizeInput',
            'function activePointLod()',
            'function activeMeshLod()',
            'function drawPerspectiveMesh(mode)',
            'function drawOrthographicMesh(panel, mode)',
            'Selected Camera View',
            'cameraPreviewCanvas',
            'function cameraBasisForLook(rawLook)',
            'function projectSelectedCamera(raw)',
            'function selectedFrustumCorners(mission, pointIndex)',
            'function drawSelectedFrustum(projectFn, mission, pointIndex, color)',
            'function drawSelectedCameraView()',
            'function nearestPerspectivePoint(x, y)',
            '"Reset Pivot"',
            '"Pivot to Selected Camera"',
            '"Pivot to Scene"',
            'function drawPivotGizmo()',
            'function hitPivotAxis(x,y)',
            'state.orbitYaw -= dx * 0.008',
            '"Aim deste ponto"',
            '"Usar padrão"',
            'point.look_direction',
            'spin_pitch_deg',
            'spin_yaw_start_deg',
            'P10DroneRoutePreset.v0.2',
            'routeRowsForExport',
            'readableRouteExports',
            '"look_right"',
            '"aim_authority"',
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
        self.assertIn('drawZoomControls(perspective);', source)
        self.assertIn('drawZoomControls(panel);', source)
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
            'ROUTE_PRESET_SCHEMA = "ConceptGhost.P10DroneRoutePreset.v0.2"',
            'ConceptGhost.P10DroneRoutePreset.v0.1',
            'LEGACY_ROUTE_PRESET_SCHEMAS',
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
        self.assertIn("GEOMETRY_DRAW_BUDGET = 100000", frontend)
        self.assertIn("max_points=100000", backend)
        self.assertIn("panel_width: int=720", preview_source)
        self.assertIn("panel_height: int=660", preview_source)





    def test_route_editor_per_waypoint_and_portable_export_contract(self):
        import p10_lab

        frontend=(Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js").read_text(encoding="utf-8")
        for token in (
            "Aim deste ponto","Usar padrão","point.look_direction",
            "spin_pitch_deg","spin_yaw_start_deg",
            "ConceptGhost.P10DroneRoutePreset.v0.2",
            "LEGACY_ROUTE_PRESET_SCHEMAS",
            "routeRowsForExport","readableRouteExports",
            "look_right","look_up","look_forward","yaw_deg","pitch_deg","aim_authority",
            ".csv",".txt",
        ):
            self.assertIn(token,frontend)

    def test_perspective_pivot_contract_is_display_only(self):
        import p10_lab
        import p10_lab.route_authoring_node as node

        frontend=(Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js").read_text(encoding="utf-8")
        backend=Path(node.__file__).read_text(encoding="utf-8")
        for token in (
            "Reset Pivot","Pivot to Selected Camera","Pivot to Scene",
            "X / Right","Y / Up","Z / Forward",
            "drawPivotGizmo","hitPivotAxis","movePivotAlongAxis",
            "state.orbitYaw -= dx * 0.008",
        ):
            self.assertIn(token,frontend)
        self.assertIn('"perspective_pivot_gimbal":True',backend)
        self.assertIn('"orbit_horizontal_default":"CONVENTIONAL_VIEWPORT"',backend)

    def test_route_editor_selected_camera_preview_contract(self):
        import p10_lab
        import p10_lab.route_authoring_node as route_node
        import p10_lab.selected_camera_preview as selected_preview

        frontend=(Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js").read_text(encoding="utf-8")
        backend=Path(route_node.__file__).read_text(encoding="utf-8")
        preview_source=Path(selected_preview.__file__).read_text(encoding="utf-8")
        for token in (
            "Selected Camera View",
            "cameraPreviewCanvas",
            "camera_preview_contract",
            "drawSelectedFrustum",
            "projectSelectedCamera",
            "nearestPerspectivePoint",
        ):
            self.assertIn(token,frontend+backend)
        self.assertIn("ConceptGhostP10SelectedDroneCameraPreview",preview_source)
        self.assertIn('"preview_authority":"DISPLAY_ONLY"',preview_source)
        self.assertIn('"p9_authority_changed":False',preview_source)
        self.assertIn('"selected_camera_authoritative_refresh_node":"ConceptGhostP10SelectedDroneCameraPreview"',backend)

    def test_route_editor_preview_lods_are_display_only(self):
        import p10_lab
        import p10_lab.route_authoring_node as node
        import p10_lab.drone_route_preview as preview

        frontend=(Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js").read_text(encoding="utf-8")
        backend=Path(node.__file__).read_text(encoding="utf-8")
        preview_source=Path(preview.__file__).read_text(encoding="utf-8")
        for token in (
            "POINTS_LOW","POINTS_MEDIUM","POINTS_HIGH",
            "MESH_SURFACE","MESH_WIREFRAME",
            "DISPLAY_ONLY_P9_PRIMARYMESH_LOD",
        ):
            self.assertIn(token,frontend+backend+preview_source)
        self.assertIn('"mesh_preview_is_display_only":True',backend)
        self.assertIn('"authority":"DISPLAY_ONLY_NEVER_GEOMETRY_AUTHORITY"',preview_source)
        self.assertIn("max_mesh_faces=60000",backend)
        self.assertIn("MESH_DRAW_BUDGET = 60000",frontend)

    def test_route_editor_r6g_layout_and_local_controls(self):
        import p10_lab

        source=(Path(p10_lab.__file__).resolve().parent/"web"/"js"/"drone_route_editor.js").read_text(encoding="utf-8")
        for token in (
            'grid-template-columns:minmax(0,1fr) minmax(0,1fr)',
            'workspaceRow.append(cameraPreviewWrap, canvasWrap)',
            'cameraPreviewCanvas.width = 960',
            'const size = 32;',
            'function viewActionControlRects(panel)',
            'function hitViewActionControl(x, y)',
            'function drawViewActionControls(panel)',
            '"MOVE_LEFT","←"',
            '"MOVE_UP","↑"',
            '"MOVE_DOWN","↓"',
            '"MOVE_RIGHT","→"',
            '"YAW_MINUS","Y−"',
            '"YAW_PLUS","Y+"',
            '"PITCH_MINUS","P−"',
            '"PITCH_PLUS","P+"',
            '"DELETE","DEL"',
            '"PIVOT_RESET",label:"Reset Pivot"',
            '"PIVOT_SCENE",label:"Pivot Scene"',
            '"PIVOT_SELECTED",label:"Pivot Cam"',
            'function moveSelectedWaypoint(panel, action)',
            'function adjustSelectedAim(action)',
            'function deleteSelectedWaypoint()',
        ):
            self.assertIn(token,source)
        toolbar=source.split("toolbar.append(",1)[1].split(");",1)[0]
        self.assertNotIn("resetPivot",toolbar)
        self.assertNotIn("pivotToSelected",toolbar)
        self.assertNotIn("pivotToScene",toolbar)


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
