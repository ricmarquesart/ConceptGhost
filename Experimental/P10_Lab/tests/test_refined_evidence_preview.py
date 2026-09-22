import json
import unittest
from pathlib import Path


class RefinedEvidencePreviewTests(unittest.TestCase):
    def test_integrated_evidence_node_is_registered_and_output_visible(self):
        import p10_lab

        self.assertIn("ConceptGhostP10RefinedEvidencePreview", p10_lab.NODE_CLASS_MAPPINGS)
        cls = p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10RefinedEvidencePreview"]
        self.assertTrue(cls.OUTPUT_NODE)
        self.assertEqual(cls.CATEGORY, "ConceptGhost/P10 Refined")
        self.assertEqual(
            cls.RETURN_NAMES,
            (
                "p9_3d_partial_erp",
                "source_authority_erp",
                "source_lock_mask",
                "flight_views",
                "hole_masks",
                "trajectory_map",
                "flight_gif_path",
                "diagnostics_json",
            ),
        )

    def test_gate4_integrated_workflow_links_refined_run_dir_into_p10_evidence(self):
        preview = (
            Path(__file__).resolve().parents[1]
            / "previews"
            / "Gate04"
            / "ConceptGhost_Master_v1.54_P10_Gate04_PREVIEW_r1.json"
        )
        self.assertTrue(preview.is_file())
        workflow = json.loads(preview.read_text(encoding="utf-8"))
        by_id = {node["id"]: node for node in workflow["nodes"]}
        evidence = next(
            node for node in workflow["nodes"]
            if node["type"] == "ConceptGhostP10RefinedEvidencePreview"
        )
        self.assertIn("REFINED/P10", evidence.get("title", ""))
        incoming = [
            link for link in workflow["links"]
            if link[3] == evidence["id"] and link[4] == 0
        ]
        self.assertEqual(len(incoming), 1)
        source = by_id[incoming[0][1]]
        self.assertEqual(source["id"], 1015)
        self.assertEqual(source["type"], "ConceptGhostExportBundle")


if __name__ == "__main__":
    unittest.main()
