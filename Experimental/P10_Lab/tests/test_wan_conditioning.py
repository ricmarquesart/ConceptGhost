import unittest


class WanConditioningNodeTests(unittest.TestCase):
    def test_node_is_registered(self):
        import p10_lab
        self.assertIn(
            "ConceptGhostP10WanMaskedConditioning",
            p10_lab.NODE_CLASS_MAPPINGS,
        )
        cls = p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10WanMaskedConditioning"]
        self.assertEqual(cls.CATEGORY, "ConceptGhost/P10 Refined")
        self.assertEqual(
            cls.RETURN_NAMES,
            ("positive", "negative", "latent"),
        )

    def test_contract_uses_hole_mask_white_equals_generate(self):
        from p10_lab.wan_conditioning import ConceptGhostP10WanMaskedConditioning
        inputs = ConceptGhostP10WanMaskedConditioning.INPUT_TYPES()
        required = inputs["required"]
        self.assertIn("control_video", required)
        self.assertIn("hole_mask", required)
        self.assertIn("width", required)
        self.assertIn("height", required)
        self.assertIn("length", required)
        self.assertEqual(
            ConceptGhostP10WanMaskedConditioning.MASK_POLICY,
            "WHITE_IS_HOLE_GENERATE_BLACK_IS_KNOWN",
        )

    def test_temporal_groups_match_wan_four_frame_packing(self):
        from p10_lab.wan_conditioning import wan_temporal_groups
        self.assertEqual(
            wan_temporal_groups(9),
            ((0, 1), (1, 5), (5, 9)),
        )
        self.assertEqual(
            wan_temporal_groups(1),
            ((0, 1),),
        )

    def test_invalid_length_fails_closed(self):
        from p10_lab.wan_conditioning import wan_temporal_groups
        with self.assertRaises(ValueError):
            wan_temporal_groups(0)


if __name__ == "__main__":
    unittest.main()
