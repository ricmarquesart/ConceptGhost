import inspect
import unittest
from pathlib import Path


class DR9RCloseoutTests(unittest.TestCase):
    def test_p9_authority_lock_and_no_p9_rewrite_contract(self):
        from p10_lab import geometry_quality
        source=inspect.getsource(geometry_quality)
        self.assertIn("P9_ACCEPTED_IMMUTABLE_UPSTREAM",source)
        self.assertIn("p9_authority_changed",source)
        self.assertIn("DESCRIPTIVE_ONLY_FOR_GENERATED_UNSEEN_SURFACES",source)

    def test_route_workspace_has_four_views_and_orientation_authority(self):
        from p10_lab import drone_route_preview,drone_route_plan
        preview=inspect.getsource(drone_route_preview)
        route=inspect.getsource(drone_route_plan)
        self.assertIn("PERSPECTIVE_PLUS_ORTHOGRAPHIC_ISOTROPIC",preview)
        self.assertIn("PERSPECTIVE_ORBIT",preview)
        self.assertIn("LOOK_AT_TARGET",route)
        self.assertIn("LOOK_ALONG_PATH",route)
        self.assertIn("MANUAL_DIRECTION",route)

    def test_p9_only_audit_and_multi_component_sparse_are_present(self):
        from p10_lab import p9_roundtrip_audit,sparse_triangulation
        audit=inspect.getsource(p9_roundtrip_audit)
        sparse=inspect.getsource(sparse_triangulation)
        self.assertIn("P9_ONLY",audit.upper())
        self.assertIn("_verified_connected_components",sparse)
        self.assertIn("ALL_VERIFIED_MATCH_COMPONENTS_FIXED_P9_WORLD",sparse)
        self.assertIn("mission_contribution",sparse)

    def test_metric_overlay_and_gate6_quality_authority_are_present(self):
        from p10_lab import geometry_quality,reconstruction_overlay,reconstruction_runtime
        overlay=inspect.getsource(reconstruction_overlay)
        quality=inspect.getsource(geometry_quality)
        runtime=inspect.getsource(reconstruction_runtime)
        self.assertIn("METRIC_ISOTROPIC_COMMON_BOUNDS",overlay)
        self.assertIn("ConceptGhost.P10Gate6GeometryQuality.v0.1",quality)
        self.assertIn("geometry_quality_status",runtime)
        self.assertIn("gate7_promotion_allowed",runtime)

    def test_two_stage_handoff_is_explicit(self):
        from p10_lab import route_handoff,workflow_integration
        handoff=inspect.getsource(route_handoff)
        workflow=inspect.getsource(workflow_integration)
        self.assertIn("WAITING_FOR_ARTIST_ROUTE",handoff)
        self.assertIn("ConceptGhost.P10ProductionEntry.v0.1",handoff)
        self.assertIn("integrate_route_setup_refined_preview",workflow)
        self.assertIn("integrate_p10_production_from_entry",workflow)
        self.assertIn('"p9_solver_present":False',workflow)

    def test_immutable_attempt_contract_spans_gate4_gate5_gate6(self):
        from p10_lab import (
            camera_sequence,control_sequence,reconstruction_node,
            reconstruction_runtime,refined_evidence,route_handoff,wan_sequence,
        )
        self.assertIn("NEVER_OVERWRITE_PRIOR_P10_ATTEMPT",inspect.getsource(route_handoff))
        self.assertIn("LATEST_P10_RUN.json",inspect.getsource(route_handoff))
        self.assertIn("p10_attempt_root",inspect.getsource(control_sequence))
        self.assertIn("p10_attempt_root",inspect.getsource(camera_sequence))
        self.assertIn('root=attempt_root/"gate4"',inspect.getsource(refined_evidence))
        self.assertIn('output_root=attempt_root/"gate5"',inspect.getsource(wan_sequence))
        self.assertIn('output_root=attempt_root/"gate6"',inspect.getsource(reconstruction_node))
        self.assertIn("COMPLETE_GEOMETRY_FAIL",inspect.getsource(reconstruction_runtime))

    def test_cross_attempt_mixing_is_fail_closed(self):
        from p10_lab import reconstruction_inputs
        source=inspect.getsource(reconstruction_inputs)
        self.assertIn("attempt id mismatch",source)
        self.assertIn("attempt root mismatch",source)

    def test_final_user_test_policy_remains_deferred_until_complete_bundle(self):
        plan=(
            Path(__file__).resolve().parents[1]
            /"docs"/"18_DR9R_RUNTIME_FINDINGS_REFINEMENT_PLAN.md"
        ).read_text(encoding="utf-8")
        self.assertIn("USER TEST DEFERRED",plan)
        self.assertIn("DR9R-E",plan)
        self.assertIn("Only after DR9R-B1..B6, DR9R-C and DR9R-D are complete",plan)


if __name__=="__main__":
    unittest.main()
