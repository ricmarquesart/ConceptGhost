from copy import deepcopy
from pathlib import Path
import hashlib
import json
import tempfile
import unittest


class DR8FinalCloseoutTests(unittest.TestCase):
    def _base_workflow(self):
        return {
            "last_node_id": 2005,
            "last_link_id": 178,
            "nodes": [
                {
                    "id": 2,
                    "type": "ConceptGhostMasterConfig",
                    "order": 0,
                    "widgets_values": [
                        "concept_scene",
                        "Max Reference",
                        "Auto",
                        "MoGe-3",
                        "High Fidelity",
                        False,
                        r"G:\My Drive\ConceptGhost\Outputs\ConceptGhost",
                    ],
                    "inputs": [],
                    "outputs": [],
                },
                {
                    "id": 1015,
                    "type": "ConceptGhostExportBundle",
                    "title": "REFINED/P9 CLONE · P10 RESERVED · 06 · EXPORT",
                    "order": 1,
                    "outputs": [{"name": "run_dir", "type": "STRING", "links": []}],
                },
                {
                    "id": 15,
                    "type": "ConceptGhostExportBundle",
                    "title": "BASELINE/P9 · 06 · EXPORT",
                    "order": 2,
                    "outputs": [{"name": "run_dir", "type": "STRING", "links": []}],
                },
            ],
            "links": [],
        }

    def test_workflow_closeout_is_p10_only_and_preserves_baseline(self):
        from p10_lab.workflow_integration import integrate_gate6_refined_preview

        base = self._base_workflow()
        original = deepcopy(base)
        patched = integrate_gate6_refined_preview(base)

        # Integration must never mutate the caller's Baseline/P9 graph.
        self.assertEqual(base, original)

        original_baseline = next(node for node in original["nodes"] if node["id"] == 15)
        patched_baseline = next(node for node in patched["nodes"] if node["id"] == 15)
        self.assertEqual(patched_baseline, original_baseline)

        master_original = next(node for node in original["nodes"] if node["id"] == 2)
        master_patched = next(node for node in patched["nodes"] if node["id"] == 2)
        self.assertEqual(master_original["widgets_values"][4], "High Fidelity")
        self.assertEqual(master_patched["widgets_values"][4], "High Fidelity Split Clean")

        by_type = {node["type"]: node for node in patched["nodes"]}
        route = by_type["ConceptGhostP10DroneRouteAuthoring"]
        evidence = by_type["ConceptGhostP10RefinedEvidencePreview"]
        wan = by_type["ConceptGhostP10WanSequentialSampler"]
        reconstruction = by_type["ConceptGhostP10ReconstructionRuntime"]

        self.assertEqual(wan["outputs"][2]["name"], "wan_manifest_path")
        self.assertEqual(wan["outputs"][4]["name"], "drone_preview_index_path")

        links = patched["links"]
        self.assertTrue(any(
            link[1] == route["id"] and link[2] == 1
            and link[3] == evidence["id"] and link[4] == 4
            for link in links
        ))
        self.assertTrue(any(
            link[1] == evidence["id"] and link[2] == 7
            and link[3] == wan["id"] and link[4] == 6
            for link in links
        ))
        self.assertTrue(any(
            link[1] == wan["id"] and link[2] == 2
            and link[3] == reconstruction["id"] and link[4] == 0
            for link in links
        ))
        self.assertTrue(any(
            link[1] == evidence["id"] and link[2] == 8
            and link[3] == reconstruction["id"] and link[4] == 1
            for link in links
        ))

    def test_two_drone_route_sampling_identity_and_diagnostics_closeout(self):
        from p10_lab.drone_route_diagnostics import build_drone_route_diagnostics
        from p10_lab.drone_route_plan import (
            DroneMission,
            DroneRoutePlan,
            DroneWaypoint,
            bind_route_plan,
            parse_bound_route_plan,
            sample_route_plan,
        )

        plan = DroneRoutePlan(
            missions=(
                DroneMission(
                    "drone_1",
                    "PATH",
                    (
                        DroneWaypoint(0, 2, 0),
                        DroneWaypoint(0, 1, 8),
                        DroneWaypoint(2, 0, 16),
                    ),
                ),
                DroneMission(
                    "drone_2",
                    "SPIN_360",
                    (DroneWaypoint(4, 3, 10),),
                ),
            ),
            frames_per_drone=6,
            min_clearance_m=0.20,
        )
        bound = bind_route_plan(
            plan,
            scene_contract_id="sceneA",
            source_run_id="runA",
            route_authority="ARTIST_AUTHORED",
        )
        restored, authority, digest = parse_bound_route_plan(
            bound,
            expected_scene_contract_id="sceneA",
            expected_source_run_id="runA",
            require_hash=True,
        )
        self.assertEqual(restored, plan)
        self.assertEqual(authority, "ARTIST_AUTHORED")
        self.assertEqual(digest, bound["route_plan_sha256"])

        sampled = sample_route_plan(plan)
        self.assertEqual([path.name for path in sampled], ["drone_1", "drone_2"])
        self.assertEqual([len(path.waypoints) for path in sampled], [6, 6])

        diagnostics = build_drone_route_diagnostics(
            plan,
            sampled,
            {
                "drone_1": [0.5] * 6,
                "drone_2": [0.4] * 6,
            },
            {
                "drone_1": [0.5] * 6,
                "drone_2": [0.6] * 6,
            },
            [{
                "mission_name": "drone_1",
                "held_frame_count": 1,
                "resumed_frame_count": 1,
                "minimum_candidate_clearance": 0.0,
                "minimum_output_clearance": 0.4,
            }],
            route_authority="ARTIST_AUTHORED",
            route_plan_sha256=digest,
            scene_contract_id="sceneA",
            source_run_id="runA",
        )
        self.assertEqual(diagnostics["schema"], "ConceptGhost.P10DroneRouteDiagnostics.v0.1")
        self.assertEqual(diagnostics["mission_order"], ["drone_1", "drone_2"])
        self.assertEqual(diagnostics["active_drone_count"], 2)
        self.assertEqual(diagnostics["total_emitted_frame_count"], 12)
        self.assertEqual(diagnostics["status"], "WARN")
        self.assertEqual(diagnostics["missions"][0]["status"], "WARN")
        self.assertEqual(diagnostics["missions"][1]["status"], "PASS")
        self.assertEqual(diagnostics["missions"][1]["mode"], "SPIN_360")

        with self.assertRaises(ValueError):
            parse_bound_route_plan(
                bound,
                expected_scene_contract_id="sceneA",
                expected_source_run_id="runB",
            )

    def test_split_wan_windows_reassemble_one_exact_sequence_per_drone(self):
        from p10_lab.wan_sequence import (
            MissionRange,
            _window_ranges,
            collect_mission_composite_frames,
        )

        missions = (
            MissionRange("drone_1", 0, 6, "drone_1"),
            MissionRange("drone_2", 6, 12, "drone_2"),
        )
        windows = tuple(
            window
            for mission in missions
            for window in _window_ranges(mission, 4)
        )
        self.assertEqual(
            [window.mission_name for window in windows],
            ["drone_1", "drone_1", "drone_2", "drone_2"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = []
            for window_index, window in enumerate(windows):
                folder = root / f"{window_index:02d}_{window.name}"
                folder.mkdir(parents=True)
                for local_index, global_index in enumerate(range(window.start, window.end)):
                    (folder / f"frame_{local_index:04d}.png").write_bytes(
                        f"{window.mission_name}:{global_index}".encode("utf-8")
                    )
                records.append({
                    "window_index": window_index,
                    "name": window.name,
                    "mission_name": window.mission_name,
                    "source_start": window.start,
                    "source_end": window.end,
                    "decoded_frame_count": window.length,
                    "composite_dir": str(folder),
                })

            grouped = collect_mission_composite_frames(records, missions)
            self.assertEqual(len(grouped["drone_1"]), 6)
            self.assertEqual(len(grouped["drone_2"]), 6)
            self.assertEqual(
                grouped["drone_1"][0].read_bytes(),
                b"drone_1:0",
            )
            self.assertEqual(
                grouped["drone_1"][-1].read_bytes(),
                b"drone_1:5",
            )
            self.assertEqual(
                grouped["drone_2"][0].read_bytes(),
                b"drone_2:6",
            )
            self.assertEqual(
                grouped["drone_2"][-1].read_bytes(),
                b"drone_2:11",
            )

    def test_preview_index_freshness_binds_route_context_gif_and_source_bytes(self):
        from p10_lab.wan_sequence import (
            MissionRange,
            _ordered_frame_set_sha256,
            determine_preview_invalidation_reason,
            validate_drone_preview_freshness,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            comp = root / "composite"
            comp.mkdir()
            sources = []
            for index in range(2):
                path = comp / f"frame_{index:04d}.png"
                path.write_bytes(f"frame-{index}".encode("utf-8"))
                sources.append(path)

            gif = root / "drone_01_drone_1_preview.gif"
            gif.write_bytes(b"GIF89a-closeout")
            gif_hash = hashlib.sha256(gif.read_bytes()).hexdigest()
            source_hash = _ordered_frame_set_sha256(tuple(sources))
            index_path = root / "drone_preview_index.json"
            index = {
                "schema": "ConceptGhost.P10DronePreviewIndex.v0.2",
                "status": "PASS",
                "run_id": "runA",
                "scene_contract_id": "sceneA",
                "source_run_id": "runA",
                "source_type": "GATE5_FINAL_COMPOSITE",
                "source_control_manifest_sha256": "c" * 64,
                "route_plan_sha256": "a" * 64,
                "generation_context_sha256": "b" * 64,
                "mission_order": ["drone_1"],
                "mission_modes": {"drone_1": "PATH"},
                "drone_count": 1,
                "fps": 10,
                "max_width": 640,
                "loop": "INFINITE",
                "index_filename": index_path.name,
                "index_subfolder": "drone_previews",
                "index_path": str(index_path),
                "previews": [{
                    "drone_index": 1,
                    "mission_name": "drone_1",
                    "mode": "PATH",
                    "frame_count": 2,
                    "global_frame_start": 0,
                    "global_frame_end_exclusive": 2,
                    "fps": 10,
                    "frame_duration_ms": 100,
                    "preview_width": 640,
                    "preview_height": 360,
                    "source_type": "GATE5_FINAL_COMPOSITE",
                    "source_frame_set_sha256": source_hash,
                    "gif_filename": gif.name,
                    "gif_subfolder": "drone_previews",
                    "gif_path": str(gif),
                    "gif_sha256": gif_hash,
                }],
            }
            index_path.write_text(json.dumps(index), encoding="utf-8")

            missions = (MissionRange("drone_1", 0, 2, "drone_1"),)
            records = [{
                "window_index": 0,
                "name": "drone_1",
                "mission_name": "drone_1",
                "source_start": 0,
                "source_end": 2,
                "decoded_frame_count": 2,
                "composite_dir": str(comp),
            }]
            modes = {"drone_1": "PATH"}

            validate_drone_preview_freshness(
                index,
                records,
                missions,
                modes,
                route_plan_sha256="a" * 64,
                generation_context_sha256="b" * 64,
                source_control_manifest_sha256="c" * 64,
            )

            previous_manifest = {
                "route_plan_sha256": "a" * 64,
                "source_control_manifest_sha256": "c" * 64,
                "generation_context_sha256": "b" * 64,
                "drone_preview_index_sha256": hashlib.sha256(
                    index_path.read_bytes()
                ).hexdigest(),
            }
            self.assertEqual(
                determine_preview_invalidation_reason(
                    previous_manifest,
                    index_path,
                    route_plan_sha256="a" * 64,
                    source_control_manifest_sha256="c" * 64,
                    generation_context_sha256="b" * 64,
                ),
                "SAME_CONTEXT_EXPLICIT_REGENERATION",
            )

            sources[1].write_bytes(b"changed-final-composite")
            with self.assertRaises(ValueError):
                validate_drone_preview_freshness(
                    index,
                    records,
                    missions,
                    modes,
                    route_plan_sha256="a" * 64,
                    generation_context_sha256="b" * 64,
                    source_control_manifest_sha256="c" * 64,
                )

    def test_frontend_closeout_contract_contains_artist_controls_and_stale_guards(self):
        import p10_lab

        source = (
            Path(p10_lab.__file__).resolve().parent
            / "web" / "js" / "drone_route_editor.js"
        ).read_text(encoding="utf-8")
        for required in (
            '"+ Drone"',
            '"− Drone"',
            '"SPIN_360"',
            '"Resetar rota"',
            'state.plan.route_authority = "ARTIST_AUTHORED"',
            'delete state.plan.route_plan_sha256',
            'state.collisionStale = true',
            'blockedSegment',
            '#ff3b58',
        ):
            self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main()
