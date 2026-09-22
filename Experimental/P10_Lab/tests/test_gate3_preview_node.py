import unittest


class Gate3PanoramaPreviewNodeTests(unittest.TestCase):
    def _node(self):
        try:
            from p10_lab.preview_nodes import ConceptGhostP10PanoramaPreview
        except ImportError as error:
            self.fail(f"Gate 3.5 panorama preview node is missing: {error}")
        return ConceptGhostP10PanoramaPreview

    def test_gate3_preview_node_is_registered(self):
        import p10_lab

        self.assertIn("ConceptGhostP10PanoramaPreview", p10_lab.NODE_CLASS_MAPPINGS)
        self.assertEqual(
            p10_lab.NODE_DISPLAY_NAME_MAPPINGS["ConceptGhostP10PanoramaPreview"],
            "P10 Temporary Panorama / Authority Preview",
        )

    def test_gate3_preview_node_contract_exposes_visual_outputs(self):
        cls = self._node()
        inputs = cls.INPUT_TYPES()

        self.assertIn("bundle_path", inputs["required"])
        self.assertIn("panorama_width", inputs["required"])
        self.assertIn("cache_root", inputs["required"])
        self.assertEqual(cls.RETURN_TYPES, ("IMAGE", "MASK", "MASK", "STRING"))
        self.assertEqual(
            cls.RETURN_NAMES,
            (
                "temporary_panorama",
                "source_lock_mask",
                "generation_candidate_mask",
                "diagnostics_json",
            ),
        )
        self.assertEqual(cls.FUNCTION, "preview")
        self.assertEqual(cls.CATEGORY, "ConceptGhost/P10 Lab")
        self.assertTrue(cls.OUTPUT_NODE)

    def test_panorama_width_contract_is_even_two_to_one_and_bounded(self):
        cls = self._node()

        self.assertEqual(cls._panorama_height(2048), 1024)
        self.assertEqual(cls._panorama_height(512), 256)

        for bad in (0, 511, 513, 8194, True, 1024.0):
            with self.assertRaises(ValueError):
                cls._panorama_height(bad)


if __name__ == "__main__":
    unittest.main()
