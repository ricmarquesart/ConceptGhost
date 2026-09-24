import json
import struct
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None


def _write_float_map(path: Path, array):
    h, w = array.shape[:2]
    channels = 1 if array.ndim == 2 else array.shape[2]
    arr = array[:, :, None] if array.ndim == 2 else array
    serialized = arr.transpose(1, 0, 2).reshape(-1, order="F").astype("<f4")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(f"{w}&{h}&{channels}&".encode("ascii"))
        stream.write(serialized.tobytes())


def _write_consistency(path: Path, width: int, height: int, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    values = []
    for row, col, sources in records:
        values.extend([row, col, len(sources), *sources])
    with path.open("wb") as stream:
        stream.write(f"{width}&{height}&1&".encode("ascii"))
        if values:
            stream.write(struct.pack("<" + "i" * len(values), *values))


class ColmapDenseIOTests(unittest.TestCase):
    @unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
    def test_depth_and_consistency_roundtrip(self):
        from p10_lab.colmap_dense_io import (
            read_colmap_consistency_graph,
            read_colmap_float_map,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = np.asarray([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
            depth_path = root / "depth.bin"
            _write_float_map(depth_path, depth)
            loaded = read_colmap_float_map(depth_path, expected_channels=1)
            np.testing.assert_allclose(loaded, depth)

            graph_path = root / "graph.bin"
            _write_consistency(
                graph_path,
                3,
                2,
                [(0, 1, [0, 2]), (1, 2, [1])],
            )
            header, records = read_colmap_consistency_graph(
                graph_path,
                selected_pixels=[(0, 1)],
                max_source_index=2,
            )
            self.assertEqual(header, (3, 2, 1))
            self.assertEqual(records, {(0, 1): (0, 2)})

    def test_dense_reader_contract_is_fail_closed(self):
        import p10_lab.colmap_dense_io as dense_io

        source = Path(dense_io.__file__).read_text(encoding="utf-8")
        self.assertIn("payload size mismatch", source)
        self.assertIn("requires PINHOLE", source)
        self.assertIn("out-of-range source image index", source)
        self.assertIn("C = -R^T t", source)


class Gate7FreeSpaceTests(unittest.TestCase):
    @unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
    def test_constraint_classifier_preserves_source_and_confirms_only_independent_free(self):
        from p10_lab.free_space_constraints import FreeSpaceState, classify_free_space

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw.npz"
            np.savez_compressed(
                raw,
                voxel_keys=np.asarray([[0,0,0],[1,0,0],[2,0,0],[3,0,0]], dtype=np.int32),
                voxel_centers=np.asarray([[0,0,0],[1,0,0],[2,0,0],[3,0,0]], dtype=np.float32),
                free_effective_votes=np.asarray([5,4,3,4], dtype=np.int16),
                occupied_effective_votes=np.asarray([0,2,0,5], dtype=np.int16),
                free_route_count=np.asarray([2,2,2,2], dtype=np.int16),
                occupied_route_count=np.asarray([0,1,0,2], dtype=np.int16),
                free_frame_count=np.asarray([5,4,3,4], dtype=np.int16),
                occupied_frame_count=np.asarray([0,2,0,5], dtype=np.int16),
                free_max_cross_route_angle_deg=np.asarray([12,12,1,15], dtype=np.float32),
                occupied_max_cross_route_angle_deg=np.asarray([0,0,0,10], dtype=np.float32),
                free_consistency_mean=np.asarray([3,3,3,3], dtype=np.float32),
                occupied_consistency_mean=np.asarray([0,3,0,3], dtype=np.float32),
                p9_source_protected=np.asarray([0,0,0,1], dtype=np.uint8),
            )
            manifest = root / "free_space_evidence_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema":"ConceptGhost.P10Gate7FreeSpaceEvidence.v0.1",
                        "status":"PASS",
                        "scene_contract_id":"scene",
                        "p9_run_id":"p9",
                        "p10_attempt_id":"attempt",
                        "coordinate_space":"P9_CANONICAL_WORLD_METERS",
                        "evidence_npz_path":str(raw.resolve()),
                        "official_geometry_changed":False,
                        "p9_authority_changed":False,
                        "ready_for_free_space_classification":True,
                    }
                ),
                encoding="utf-8",
            )
            result = classify_free_space(manifest, root/"classified")
            with np.load(result["constraints_npz_path"], allow_pickle=False) as payload:
                states = payload["state"].tolist()
            self.assertEqual(states[0], int(FreeSpaceState.CONFIRMED_FREE))
            self.assertEqual(states[1], int(FreeSpaceState.CONFLICT))
            self.assertEqual(states[2], int(FreeSpaceState.UNKNOWN))
            self.assertEqual(states[3], int(FreeSpaceState.OCCUPIED))
            self.assertEqual(result["authority_rules"]["CONFIRMED_FREE"], "NO_FILL_NO_BRIDGE_CONSTRAINT")
            self.assertFalse(result["ready_for_destructive_fusion"])
            self.assertFalse(result["official_geometry_changed"])

    @unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
    def test_evidence_builder_consumes_geometric_depth_and_never_carves_behind_surface(self):
        from p10_lab.free_space_evidence import build_free_space_evidence

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root/"dataset"
            dense = dataset/"dense"
            (dense/"sparse").mkdir(parents=True)
            (dense/"images").mkdir()
            (dense/"stereo"/"depth_maps").mkdir(parents=True)
            (dense/"stereo"/"consistency_graphs").mkdir(parents=True)

            frames=[]
            image_rows=[]
            for i, route in enumerate(["drone_a","drone_b","drone_a"], start=1):
                name=f"frame_{i-1:06d}.png"
                frames.append({
                    "image_id":i,"camera_id":1,"global_frame_index":i-1,
                    "path_name":route,"path_frame_index":0,"image_name":name,
                })
                image_rows.append(f"{i} 1 0 0 0 0 0 0 1 {name}\n\n")
                depth=np.full((4,4), 2.0, dtype=np.float32)
                _write_float_map(dense/"stereo"/"depth_maps"/f"{name}.geometric.bin", depth)
                records=[(r,c,[0,1]) for r in range(4) for c in range(4)]
                _write_consistency(
                    dense/"stereo"/"consistency_graphs"/f"{name}.geometric.bin",
                    4,4,records,
                )
            (dense/"sparse"/"cameras.txt").write_text(
                "1 PINHOLE 4 4 4 4 2 2\n", encoding="utf-8"
            )
            (dense/"sparse"/"images.txt").write_text("".join(image_rows), encoding="utf-8")
            dataset_manifest=dataset/"dataset_manifest.json"
            dataset_manifest.write_text(
                json.dumps({
                    "schema":"ConceptGhost.P10KnownCameraColmapDataset.v0.2",
                    "run_id":"p9",
                    "scene_contract_id":"scene",
                    "camera_authority":"P9_BASELINE_WORLD_DERIVED",
                    "image_authority":"SOURCE_PRESERVED_P10_COMPOSITE",
                    "frames":frames,
                }),
                encoding="utf-8",
            )
            registration=root/"registration.json"
            registration.write_text(
                json.dumps({"dataset_manifest_path":str(dataset_manifest.resolve())}),
                encoding="utf-8",
            )
            provenance_evidence=root/"provenance_evidence.npz"
            np.savez_compressed(
                provenance_evidence,
                p9_points=np.asarray([[0,0,2]],dtype=np.float32),
                p9_labels=np.asarray([1],dtype=np.uint8),
            )
            provenance=root/"provenance.json"
            provenance.write_text(
                json.dumps({
                    "registration_manifest_path":str(registration.resolve()),
                    "thresholds":{"scene_diagonal_m":4.0},
                }),
                encoding="utf-8",
            )
            confidence_evidence=root/"confidence.npz"
            np.savez_compressed(
                confidence_evidence,
                p9_points=np.asarray([[0,0,2]],dtype=np.float32),
                p9_provenance_labels=np.asarray([1],dtype=np.uint8),
            )
            confidence=root/"confidence.json"
            confidence.write_text(
                json.dumps({
                    "schema":"ConceptGhost.P10Gate7GeometryConfidence.v0.1",
                    "status":"PASS",
                    "geometry_confidence_refine":False,
                    "official_geometry_changed":False,
                    "p9_authority_changed":False,
                    "ready_for_gate7_3":True,
                    "scene_contract_id":"scene",
                    "p9_run_id":"p9",
                    "p10_attempt_id":"attempt",
                    "provenance_manifest_path":str(provenance.resolve()),
                    "evidence_npz_path":str(confidence_evidence.resolve()),
                }),
                encoding="utf-8",
            )
            result=build_free_space_evidence(
                confidence,
                root/"out",
                max_pixels_per_frame=16,
                min_consistent_sources=2,
                min_voxel_size_m=0.1,
                max_voxel_size_m=0.1,
                free_step_voxels=1.0,
                max_free_samples_per_ray=32,
            )
            self.assertEqual(result["status"],"PASS")
            self.assertGreater(result["sampling"]["accepted_consistent_rays"],0)
            self.assertEqual(result["ray_policy"]["behind_surface"],"UNKNOWN_NEVER_FREE")
            self.assertFalse(result["official_geometry_changed"])
            with np.load(result["evidence_npz_path"], allow_pickle=False) as payload:
                self.assertGreater(len(payload["voxel_keys"]),0)
                self.assertGreater(int(payload["p9_source_protected"].sum()),0)

    @unittest.skipIf(np is None, "NumPy unavailable in minimal CI")
    def test_free_space_overlay_caps_confidence_without_mutating_p9(self):
        from p10_lab.free_space_confidence import build_confidence_free_space_overlay
        from p10_lab.free_space_constraints import FreeSpaceState

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            confidence_npz=root/"confidence.npz"
            np.savez_compressed(
                confidence_npz,
                p9_points=np.asarray([[0,0,0]],dtype=np.float32),
                p9_provenance_labels=np.asarray([1],dtype=np.uint8),
                p9_confidence=np.asarray([0.95],dtype=np.float32),
                p9_confidence_class=np.asarray([3],dtype=np.uint8),
                p10_points=np.asarray([[0.1,0,0],[1.1,0,0],[2.1,0,0],[3.1,0,0]],dtype=np.float32),
                p10_provenance_labels=np.asarray([3,3,3,3],dtype=np.uint8),
                p10_confidence=np.asarray([0.8,0.8,0.8,0.8],dtype=np.float32),
                p10_confidence_class=np.asarray([3,3,3,3],dtype=np.uint8),
            )
            confidence_manifest=root/"confidence.json"
            confidence_manifest.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7GeometryConfidence.v0.1",
                "status":"PASS",
                "scene_contract_id":"scene",
                "p9_run_id":"p9",
                "p10_attempt_id":"attempt",
                "geometry_confidence_refine":False,
                "confidence_thresholds":{"HIGH":0.75,"NEUTRAL":0.40,"LOW":0.20,"VERY_LOW":0.0},
                "evidence_npz_path":str(confidence_npz.resolve()),
            }),encoding="utf-8")

            constraints_npz=root/"constraints.npz"
            np.savez_compressed(
                constraints_npz,
                voxel_keys=np.asarray([[0,0,0],[1,0,0],[2,0,0]],dtype=np.int32),
                voxel_centers=np.asarray([[0.5,0.5,0.5],[1.5,0.5,0.5],[2.5,0.5,0.5]],dtype=np.float32),
                state=np.asarray([
                    int(FreeSpaceState.CONFIRMED_FREE),
                    int(FreeSpaceState.CONFLICT),
                    int(FreeSpaceState.OCCUPIED),
                ],dtype=np.uint8),
                free_effective_votes=np.asarray([3,2,0],dtype=np.int16),
                occupied_effective_votes=np.asarray([0,1,3],dtype=np.int16),
                free_ratio=np.asarray([1,0.66,0],dtype=np.float32),
                free_route_count=np.asarray([2,2,0],dtype=np.int16),
                free_max_cross_route_angle_deg=np.asarray([10,10,0],dtype=np.float32),
                p9_source_protected=np.asarray([0,0,1],dtype=np.uint8),
            )
            constraints_manifest=root/"constraints.json"
            constraints_manifest.write_text(json.dumps({
                "schema":"ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1",
                "status":"PASS",
                "scene_contract_id":"scene",
                "p9_run_id":"p9",
                "p10_attempt_id":"attempt",
                "voxel":{"voxel_size_m":1.0},
                "constraints_npz_path":str(constraints_npz.resolve()),
                "ready_for_destructive_fusion":False,
            }),encoding="utf-8")

            result=build_confidence_free_space_overlay(
                confidence_manifest,
                constraints_manifest,
                root/"overlay",
            )
            with np.load(result["evidence_npz_path"],allow_pickle=False) as payload:
                before=payload["p10_confidence_before_free_space"]
                after=payload["p10_confidence_after_free_space"]
                p9=payload["p9_confidence"]
            self.assertAlmostEqual(float(after[0]),0.05,places=5)
            self.assertAlmostEqual(float(after[1]),0.18,places=5)
            self.assertAlmostEqual(float(after[2]),float(before[2]),places=5)
            self.assertAlmostEqual(float(after[3]),float(before[3]),places=5)
            self.assertAlmostEqual(float(p9[0]),0.95,places=5)
            self.assertFalse(result["geometry_confidence_refine"])
            self.assertFalse(result["ready_for_destructive_fusion"])

    def test_source_contract_never_equates_unknown_with_free(self):
        import p10_lab.free_space_constraints as constraints
        import p10_lab.free_space_evidence as evidence
        import p10_lab.free_space_confidence as confidence_overlay

        a=Path(evidence.__file__).read_text(encoding="utf-8")
        b=Path(constraints.__file__).read_text(encoding="utf-8")
        c=Path(confidence_overlay.__file__).read_text(encoding="utf-8")
        self.assertIn('"behind_surface": "UNKNOWN_NEVER_FREE"', a)
        self.assertIn("NO_FILL_NO_BRIDGE_CONSTRAINT", b)
        self.assertIn("UNKNOWN_NEVER_FREE", a)
        self.assertIn("P9_SOURCE_PROTECTED", b)
        self.assertIn('"ready_for_destructive_fusion": False', b)
        self.assertIn('"UNKNOWN": "NO_PENALTY"', c)
        self.assertIn('"P9_CONFIDENCE": "UNCHANGED"', c)


class DelaunayEvidenceTests(unittest.TestCase):
    def test_delaunay_plan_uses_dense_workspace_and_keeps_poisson_separate(self):
        from p10_lab.prefusion_mesh import build_delaunay_evidence_plan

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            dense=root/"dense"
            (dense/"sparse").mkdir(parents=True)
            (dense/"images").mkdir()
            (dense/"stereo"/"depth_maps").mkdir(parents=True)
            (dense/"fused.ply").write_text("ply\n",encoding="ascii")
            plan=build_delaunay_evidence_plan(root)
            step=plan.steps[0]
            self.assertEqual(step.command,"delaunay_mesher")
            self.assertIn("--input_path",step.args)
            self.assertEqual(plan.mesh_path.name,"pre_fusion_mesh_delaunay.ply")
            self.assertEqual(plan.comparison_path.name,"free_space_meshing_comparison.json")
            self.assertNotEqual(plan.mesh_path, dense/"pre_fusion_mesh.ply")


if __name__=="__main__":
    unittest.main()
