import unittest


class Gate5WorkflowIntegrationTests(unittest.TestCase):
    def _base(self):
        return {
            "last_node_id": 2005,
            "last_link_id": 178,
            "nodes": [
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

    def test_gate5_patch_adds_wan_only_downstream_of_refined_evidence(self):
        from p10_lab.workflow_integration import integrate_gate5_refined_preview
        patched = integrate_gate5_refined_preview(self._base())

        by_type = {}
        for node in patched["nodes"]:
            by_type.setdefault(node["type"], []).append(node)

        self.assertIn("ConceptGhostP10RefinedEvidencePreview", by_type)
        self.assertIn("ConceptGhostP10WanSequentialSampler", by_type)
        self.assertIn("UNETLoader", by_type)
        self.assertIn("CLIPLoader", by_type)
        self.assertIn("VAELoader", by_type)
        self.assertIn("LoraLoaderModelOnly", by_type)

        evidence = by_type["ConceptGhostP10RefinedEvidencePreview"][0]
        sampler = by_type["ConceptGhostP10WanSequentialSampler"][0]
        links_to_sampler = [link for link in patched["links"] if link[3] == sampler["id"]]

        source_slots = {(link[1], link[2], link[4]) for link in links_to_sampler}
        self.assertIn((evidence["id"], 3, 4), source_slots)  # flight_views -> control_video
        self.assertIn((evidence["id"], 4, 5), source_slots)  # hole_masks -> hole_mask
        self.assertIn((evidence["id"], 7, 6), source_slots)  # manifest -> control_manifest_path

    def test_gate5_patch_does_not_link_wan_to_baseline_export(self):
        from p10_lab.workflow_integration import integrate_gate5_refined_preview
        patched = integrate_gate5_refined_preview(self._base())
        sampler = next(
            node for node in patched["nodes"]
            if node["type"] == "ConceptGhostP10WanSequentialSampler"
        )
        incoming = [link for link in patched["links"] if link[3] == sampler["id"]]
        self.assertFalse(any(link[1] == 15 for link in incoming))

    def test_gate5_sampler_defaults_match_11gb_policy(self):
        from p10_lab.workflow_integration import integrate_gate5_refined_preview
        patched = integrate_gate5_refined_preview(self._base())
        sampler = next(
            node for node in patched["nodes"]
            if node["type"] == "ConceptGhostP10WanSequentialSampler"
        )
        self.assertEqual(sampler["widgets_values"], [0, 832, 480, 33, 4, 1.0])
        self.assertEqual(sampler["inputs"][7]["name"], "clip_vision_output")
        self.assertEqual(sampler["inputs"][8]["name"], "wan_seed")
        self.assertEqual(sampler["inputs"][9]["name"], "width")
        self.assertEqual(sampler["inputs"][10]["name"], "height")
        self.assertEqual(sampler["inputs"][11]["name"], "max_window_length")
        self.assertEqual(sampler["inputs"][12]["name"], "steps")
        self.assertEqual(sampler["inputs"][13]["name"], "cfg")

    def test_wan_seed_name_avoids_comfy_implicit_seed_control(self):
        from p10_lab.wan_sequence import ConceptGhostP10WanSequentialSampler
        required = ConceptGhostP10WanSequentialSampler.INPUT_TYPES()["required"]
        self.assertIn("wan_seed", required)
        self.assertNotIn("seed", required)

    def test_gate5_model_filenames_are_canonical(self):
        from p10_lab.workflow_integration import integrate_gate5_refined_preview
        patched = integrate_gate5_refined_preview(self._base())
        by_id = {node["id"]: node for node in patched["nodes"]}
        self.assertEqual(
            by_id[2200]["widgets_values"][0],
            "wan\\wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors",
        )
        self.assertEqual(
            by_id[2201]["widgets_values"][0],
            "wan\\lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16.safetensors",
        )
        self.assertEqual(
            by_id[2203]["widgets_values"][0],
            "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        )
        self.assertEqual(
            by_id[2206]["widgets_values"][0],
            "wan_2.1_vae.safetensors",
        )


if __name__ == "__main__":
    unittest.main()
