import json
import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None


class Gate7CloseoutTests(unittest.TestCase):
    def test_source_closeout_is_complete_but_gate8_remains_blocked(self):
        from p10_lab.gate7_closeout import audit_gate7_source_contract

        result = audit_gate7_source_contract()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["source_contract_complete"])
        self.assertTrue(result["preview_package_ready_for_build"])
        self.assertFalse(result["preview_package_published"])
        self.assertFalse(result["runtime_gate7_accepted"])
        self.assertFalse(result["ready_for_gate8"])
        self.assertIn(
            "GATE7_ARTIST_VISUAL_REVIEW_PENDING",
            result["promotion_blockers"],
        )

    @unittest.skipIf(Image is None, "Pillow unavailable")
    def test_runtime_closeout_requires_visual_evidence_and_explicit_approvals(self):
        from p10_lab.gate7_closeout import build_gate7_runtime_closeout
        from p10_lab.visual_evidence_contract import build_visual_evidence_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scene, p9, attempt = "scene-1", "p9-1", "attempt-1"

            def write(name, payload):
                path = root / name
                path.write_text(json.dumps(payload), encoding="utf-8")
                return path

            registration = write("registration.json", {
                "schema":"ConceptGhost.P10Gate7Registration.v0.1",
                "status":"PASS",
                "scene_contract_id":scene,
                "p9_run_id":p9,
                "p10_attempt_id":attempt,
                "registration_policy":"KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION",
                "scale":1.0,
                "sim3_refit_allowed":False,
                "p9_authority_changed":False,
            })
            provenance = write("provenance.json", {
                "schema":"ConceptGhost.P10Gate7Provenance.v0.1",
                "status":"PASS",
                "scene_contract_id":scene,
                "p9_run_id":p9,
                "p10_attempt_id":attempt,
                "official_geometry_changed":False,
            })
            confidence = write("confidence.json", {
                "schema":"ConceptGhost.P10Gate7GeometryConfidence.v0.1",
                "status":"PASS",
                "scene_contract_id":scene,
                "p9_run_id":p9,
                "p10_attempt_id":attempt,
                "geometry_confidence_refine":False,
                "official_geometry_changed":False,
            })
            free_space = write("free_space.json", {
                "schema":"ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1",
                "status":"PASS",
                "scene_contract_id":scene,
                "p9_run_id":p9,
                "p10_attempt_id":attempt,
                "official_geometry_changed":False,
            })
            fusion = write("fusion.json", {
                "schema":"ConceptGhost.P10Gate7ProtectedFusionCandidate.v0.1",
                "status":"PASS",
                "scene_contract_id":scene,
                "p9_run_id":p9,
                "p10_attempt_id":attempt,
                "candidate_is_official_geometry":False,
                "official_geometry_changed":False,
                "p9_policy":{
                    "all_p9_faces_copied_unchanged":True,
                    "p9_faces_removed":0,
                    "p9_vertices_moved":0,
                },
            })

            review_png = root / "review.png"
            Image.new("RGB", (360, 240), (30, 30, 35)).save(review_png)
            review = write("review.json", {
                "schema":"ConceptGhost.P10Gate7VisualReview.v0.1",
                "status":"PASS",
                "scene_contract_id":scene,
                "p9_run_id":p9,
                "p10_attempt_id":attempt,
                "candidate_is_official_geometry":False,
                "official_geometry_changed":False,
                "preview_png_path":str(review_png.resolve()),
            })

            evidence_paths = []
            for gate in ("G7.1","G7.2","G7.2C","G7.3","G7.4","G7.5"):
                slug = gate.replace(".","_")
                preview = root / f"{slug}_preview.png"
                compare = root / f"{slug}_comparison.png"
                Image.new("RGB", (220, 140), (45, 50, 60)).save(preview)
                Image.new("RGB", (220, 140), (60, 45, 50)).save(compare)
                result = build_visual_evidence_manifest(
                    gate,
                    root / f"{slug}_visual",
                    preview_artifacts=[preview],
                    comparison_artifacts=[compare],
                    metadata={"before":"reference","after":"result"},
                )
                evidence_paths.append(result["manifest_path"])

            blocked = build_gate7_runtime_closeout(
                registration,
                provenance,
                confidence,
                free_space,
                fusion,
                review,
                evidence_paths,
                root / "closeout_blocked",
                dr9r_runtime_accepted=False,
                artist_visual_review_approved=False,
            )
            self.assertTrue(blocked["runtime_evidence_chain_complete"])
            self.assertTrue(blocked["visual_evidence_complete"])
            self.assertFalse(blocked["promotion"]["gate7_accepted"])
            self.assertFalse(blocked["promotion"]["ready_for_gate8"])
            self.assertEqual(len(blocked["promotion"]["blockers"]), 2)
            self.assertTrue(Path(blocked["visual_evidence_index_png_path"]).is_file())
            self.assertTrue(Path(blocked["input_output_summary_png_path"]).is_file())

            accepted = build_gate7_runtime_closeout(
                registration,
                provenance,
                confidence,
                free_space,
                fusion,
                review,
                evidence_paths,
                root / "closeout_accepted",
                dr9r_runtime_accepted=True,
                artist_visual_review_approved=True,
            )
            self.assertTrue(accepted["promotion"]["gate7_accepted"])
            self.assertTrue(accepted["promotion"]["ready_for_gate8"])
            self.assertEqual(accepted["promotion"]["blockers"], [])
            self.assertFalse(accepted["official_geometry_changed_by_closeout"])

    @unittest.skipIf(Image is None, "Pillow unavailable")
    def test_missing_visual_gate_fails_closed(self):
        from p10_lab.contracts import ContractError
        from p10_lab.gate7_closeout import build_gate7_runtime_closeout
        from p10_lab.visual_evidence_contract import build_visual_evidence_manifest

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            scene,p9,attempt="scene","p9","attempt"
            def write(name,payload):
                path=root/name
                path.write_text(json.dumps(payload),encoding="utf-8")
                return path

            registration=write("r.json",{
                "schema":"ConceptGhost.P10Gate7Registration.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "registration_policy":"KNOWN_CAMERA_P9_WORLD_IDENTITY_REGISTRATION",
                "scale":1.0,"sim3_refit_allowed":False,"p9_authority_changed":False,
            })
            provenance=write("p.json",{
                "schema":"ConceptGhost.P10Gate7Provenance.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "official_geometry_changed":False,
            })
            confidence=write("c.json",{
                "schema":"ConceptGhost.P10Gate7GeometryConfidence.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "geometry_confidence_refine":False,"official_geometry_changed":False,
            })
            free=write("f.json",{
                "schema":"ConceptGhost.P10Gate7FreeSpaceConstraints.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "official_geometry_changed":False,
            })
            fusion=write("u.json",{
                "schema":"ConceptGhost.P10Gate7ProtectedFusionCandidate.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "candidate_is_official_geometry":False,"official_geometry_changed":False,
                "p9_policy":{"all_p9_faces_copied_unchanged":True,"p9_faces_removed":0,"p9_vertices_moved":0},
            })
            review_png=root/"review.png";Image.new("RGB",(100,100)).save(review_png)
            review=write("v.json",{
                "schema":"ConceptGhost.P10Gate7VisualReview.v0.1","status":"PASS",
                "scene_contract_id":scene,"p9_run_id":p9,"p10_attempt_id":attempt,
                "candidate_is_official_geometry":False,"official_geometry_changed":False,
                "preview_png_path":str(review_png.resolve()),
            })
            preview=root/"one.png";compare=root/"two.png"
            Image.new("RGB",(50,50)).save(preview);Image.new("RGB",(50,50)).save(compare)
            only=build_visual_evidence_manifest(
                "G7.4",root/"e",preview_artifacts=[preview],comparison_artifacts=[compare]
            )
            with self.assertRaises(ContractError):
                build_gate7_runtime_closeout(
                    registration,provenance,confidence,free,fusion,review,
                    [only["manifest_path"]],root/"out",
                )


if __name__=="__main__":
    unittest.main()
