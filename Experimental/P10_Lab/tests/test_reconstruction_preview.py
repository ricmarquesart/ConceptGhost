import unittest


class ReconstructionPreviewNodeTests(unittest.TestCase):
    def test_node_is_registered_and_visible(self):
        import p10_lab
        self.assertIn("ConceptGhostP10ReconstructionRuntime",p10_lab.NODE_CLASS_MAPPINGS)
        cls=p10_lab.NODE_CLASS_MAPPINGS["ConceptGhostP10ReconstructionRuntime"]
        self.assertEqual(cls.CATEGORY,"ConceptGhost/P10 Refined")
        self.assertTrue(cls.OUTPUT_NODE)
        self.assertEqual(
            cls.RETURN_NAMES,
            ("mesh_preview","pre_fusion_mesh","gate6_output_root","runtime_manifest_path","diagnostics_json"),
        )

    def test_manifest_inputs_are_connection_only(self):
        from p10_lab.reconstruction_node import ConceptGhostP10ReconstructionRuntime
        required=ConceptGhostP10ReconstructionRuntime.INPUT_TYPES()["required"]
        self.assertTrue(required["wan_manifest_path"][1].get("forceInput"))
        self.assertTrue(required["camera_manifest_path"][1].get("forceInput"))
        self.assertTrue(required["resume_existing"][1]["default"])


class Gate6WorkflowIntegrationTests(unittest.TestCase):
    def _base(self):
        return {
            "last_node_id":2005,
            "last_link_id":178,
            "nodes":[
                {"id":1015,"type":"ConceptGhostExportBundle","title":"REFINED/P9 CLONE · P10 RESERVED · 06 · EXPORT","order":1,
                 "outputs":[{"name":"run_dir","type":"STRING","links":[]}]},
                {"id":15,"type":"ConceptGhostExportBundle","title":"BASELINE/P9 · 06 · EXPORT","order":2,
                 "outputs":[{"name":"run_dir","type":"STRING","links":[]}]},
            ],
            "links":[],
        }

    def test_gate6_defaults_master_geometry_to_split_clean(self):
        from p10_lab.workflow_integration import integrate_gate6_refined_preview

        workflow=self._base()
        workflow["nodes"].append({
            "id":2,
            "type":"ConceptGhostMasterConfig",
            "order":0,
            "widgets_values":[
                "concept_scene",
                "Max Reference",
                "Auto",
                "MoGe-3",
                "High Fidelity",
                False,
                r"G:\\My Drive\\ConceptGhost\\Outputs\\ConceptGhost",
            ],
            "inputs":[],
            "outputs":[],
        })
        wf=integrate_gate6_refined_preview(workflow)
        master=next(node for node in wf["nodes"] if node.get("id")==2)
        self.assertEqual(master["widgets_values"][4],"High Fidelity Split Clean")

    def test_gate6_patch_connects_wan_and_camera_manifests(self):
        from p10_lab.workflow_integration import integrate_gate6_refined_preview
        wf=integrate_gate6_refined_preview(self._base())
        by_id={n["id"]:n for n in wf["nodes"]}
        self.assertEqual(by_id[2300]["type"],"ConceptGhostP10ReconstructionRuntime")
        self.assertEqual(by_id[2301]["type"],"PreviewImage")
        incoming=[link for link in wf["links"] if link[3]==2300]
        self.assertTrue(any(link[1]==2207 and link[2]==2 and link[4]==0 for link in incoming))
        self.assertTrue(any(link[1]==2100 and link[2]==8 and link[4]==1 for link in incoming))
        self.assertFalse(any(link[1]==15 for link in incoming))

    def test_gate6_artist_route_chain_is_connected_end_to_end(self):
        from p10_lab.workflow_integration import integrate_gate6_refined_preview
        wf=integrate_gate6_refined_preview(self._base())
        nodes={node["type"]:node for node in wf["nodes"] if node.get("type") in {
            "ConceptGhostP10DroneRouteAuthoring",
            "ConceptGhostP10RefinedEvidencePreview",
            "ConceptGhostP10WanSequentialSampler",
            "ConceptGhostP10ReconstructionRuntime",
        }}
        route=nodes["ConceptGhostP10DroneRouteAuthoring"]
        evidence=nodes["ConceptGhostP10RefinedEvidencePreview"]
        wan=nodes["ConceptGhostP10WanSequentialSampler"]
        reconstruction=nodes["ConceptGhostP10ReconstructionRuntime"]

        self.assertTrue(any(
            link[1]==route["id"] and link[2]==1
            and link[3]==evidence["id"] and link[4]==4
            for link in wf["links"]
        ))
        self.assertTrue(any(
            link[1]==evidence["id"] and link[2]==7
            and link[3]==wan["id"] and link[4]==6
            for link in wf["links"]
        ))
        self.assertTrue(any(
            link[1]==wan["id"] and link[2]==2
            and link[3]==reconstruction["id"] and link[4]==0
            for link in wf["links"]
        ))
        self.assertTrue(any(
            link[1]==evidence["id"] and link[2]==8
            and link[3]==reconstruction["id"] and link[4]==1
            for link in wf["links"]
        ))

    def test_production_workflow_labels_gate4_gate5_gate6_groups_and_outputs(self):
        from p10_lab.workflow_integration import integrate_p10_production_from_entry
        wf=integrate_p10_production_from_entry(self._base())
        titles=[str(group.get("title") or "") for group in wf.get("groups",[])]
        self.assertTrue(any(title.startswith("GATE 4") for title in titles))
        self.assertTrue(any(title.startswith("GATE 5") for title in titles))
        self.assertTrue(any(title.startswith("GATE 6") for title in titles))
        by_id={node["id"]:node for node in wf["nodes"]}
        self.assertIn("GATE 4 OUTPUT",by_id[2100]["title"])
        self.assertIn("GATE 5 OUTPUT",by_id[2207]["title"])
        self.assertIn("GATE 6",by_id[2300]["title"])
        self.assertIn("RAW P10 GEOMETRY",by_id[2301]["title"])

    def test_gate6_preview_is_connected_to_reconstruction_output(self):
        from p10_lab.workflow_integration import integrate_gate6_refined_preview
        wf=integrate_gate6_refined_preview(self._base())
        self.assertTrue(any(
            link[1]==2300 and link[2]==0 and link[3]==2301 and link[4]==0
            for link in wf["links"]
        ))


if __name__=="__main__":
    unittest.main()
