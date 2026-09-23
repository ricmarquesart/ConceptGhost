import unittest


class RefinedEvidencePreviewTests(unittest.TestCase):
    def test_integrated_evidence_node_is_registered_and_output_visible(self):
        import p10_lab

        self.assertIn("ConceptGhostP10RefinedEvidencePreview", p10_lab.NODE_CLASS_MAPPINGS)
        cls = p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10RefinedEvidencePreview"]
        self.assertTrue(cls.OUTPUT_NODE)
        self.assertEqual(cls.CATEGORY, "ConceptGhost/P10 Refined")
        inputs = cls.INPUT_TYPES()
        self.assertTrue(inputs["required"]["run_dir"][1].get("forceInput"))
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
                "control_manifest_path",
                "camera_manifest_path",
                "diagnostics_json",
            ),
        )

    def test_workflow_patcher_links_only_refined_export_run_dir(self):
        from p10_lab.workflow_integration import integrate_gate4_refined_preview

        workflow = {
            "last_node_id": 2005,
            "last_link_id": 178,
            "nodes": [
                {
                    "id": 1015,
                    "type": "ConceptGhostExportBundle",
                    "title": "REFINED/P9 CLONE · P10 RESERVED · 06 · EXPORT",
                    "outputs": [{"name": "run_dir", "type": "STRING", "links": [92]}],
                },
                {
                    "id": 15,
                    "type": "ConceptGhostExportBundle",
                    "title": "BASELINE/P9 · 06 · EXPORT",
                    "outputs": [{"name": "run_dir", "type": "STRING", "links": [12]}],
                },
            ],
            "links": [],
        }

        patched = integrate_gate4_refined_preview(workflow)
        evidence = next(
            node for node in patched["nodes"]
            if node["type"] == "ConceptGhostP10RefinedEvidencePreview"
        )
        incoming = [
            link for link in patched["links"]
            if link[3] == evidence["id"] and link[4] == 0
        ]

        self.assertEqual(len(incoming), 1)
        self.assertEqual(incoming[0][1], 1015)
        self.assertNotEqual(incoming[0][1], 15)
        self.assertIn(incoming[0][0], patched["nodes"][0]["outputs"][0]["links"])
        route_author = next(
            node for node in patched["nodes"]
            if node["type"] == "ConceptGhostP10DroneRouteAuthoring"
        )
        route_links = [
            link for link in patched["links"]
            if link[1] == route_author["id"] and link[3] == evidence["id"]
        ]
        self.assertEqual(len(route_links), 1)
        self.assertEqual(route_links[0][2], 1)
        self.assertEqual(route_links[0][4], 4)
        self.assertEqual(patched["last_node_id"], evidence["id"])
        self.assertEqual(evidence["widgets_values"], [1024, 640, 4])
        self.assertEqual(
            [item["name"] for item in evidence["inputs"]],
            ["run_dir", "panorama_width", "view_width", "steps_per_segment", "route_plan_json"],
        )


if __name__ == "__main__":
    unittest.main()
