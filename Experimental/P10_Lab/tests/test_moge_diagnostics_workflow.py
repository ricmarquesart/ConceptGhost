import unittest


class MoGeDiagnosticsWorkflowTests(unittest.TestCase):
    def _workflow(self):
        return {
            "last_node_id":1038,
            "last_link_id":119,
            "nodes":[
                {
                    "id":2,"type":"ConceptGhostMasterConfig","order":1,
                    "outputs":[
                        {"name":"preset","type":"STRING","links":[]},
                        {"name":"camera_mode","type":"STRING","links":[]},
                        {"name":"moge_version","type":"STRING","links":[]},
                        {"name":"geometry_profile","type":"STRING","links":[]},
                        {"name":"extra_diagnostics","type":"BOOLEAN","links":[119]},
                        {"name":"scene_name","type":"STRING","links":[]},
                        {"name":"output_root","type":"STRING","links":[]},
                    ],
                },
                {
                    "id":68,"type":"ConceptGhostV43RunModeSwitch","order":2,
                    "outputs":[
                        {"name":"baseline_image","type":"IMAGE","links":[]},
                        {"name":"refined_image","type":"IMAGE","links":[105]},
                    ],
                },
                {
                    "id":1038,"type":"ConceptGhostGeometryProfile","order":3,
                    "inputs":[
                        {"name":"geometry_profile","type":"STRING","link":108},
                        {"name":"preset","type":"STRING","link":109},
                        {"name":"moge_version","type":"STRING","link":113},
                        {"name":"extra_diagnostics","type":"BOOLEAN","link":119},
                    ],
                    "outputs":[
                        {"name":"profile_config","type":"CG_GEOMETRY_PROFILE","links":[110]},
                        {"name":"profile_report","type":"STRING","links":[]},
                    ],
                },
                {
                    "id":1036,"type":"ConceptGhostMoGe3Inference","order":4,
                    "inputs":[
                        {"name":"image","type":"IMAGE","link":105},
                        {"name":"preset","type":"STRING","link":106},
                        {"name":"atlas_fov_x_deg","type":"FLOAT","link":107},
                        {"name":"profile_config","type":"CG_GEOMETRY_PROFILE","link":110},
                        {"name":"draft_gate","type":"STRING","link":178},
                    ],
                    "outputs":[
                        {"name":"moge_geometry","type":"MOGE_GEOMETRY","links":[]},
                        {"name":"report","type":"STRING","links":[]},
                    ],
                },
            ],
            "links":[
                [105,68,1,1036,0,"IMAGE"],
                [110,1038,0,1036,3,"CG_GEOMETRY_PROFILE"],
                [119,2,4,1038,3,"BOOLEAN"],
            ],
            "groups":[],
        }

    def test_optional_group_is_off_and_side_branch_only(self):
        from p10_lab.workflow_integration import integrate_moge_depth_diagnostics
        patched=integrate_moge_depth_diagnostics(self._workflow())
        by_id={n["id"]:n for n in patched["nodes"]}
        control=by_id[2084]
        self.assertEqual(control["widgets_values"],[False,True,True,True])
        self.assertEqual(by_id[2087]["type"],"ConceptGhostMoGeDepthDiagnostics")
        self.assertEqual(by_id[2088]["type"],"PreviewImage")
        group=next(g for g in patched["groups"] if "MoGe Depth Diagnostics" in g["title"])
        self.assertIn("OFF BY DEFAULT",group["title"])

        # Original official profile still exists and diagnostic tap is inserted only
        # on the MoGe inference edge.
        moge=by_id[1036]
        tap=by_id[2086]
        self.assertEqual(moge["inputs"][3]["link"],tap["outputs"][0]["links"][0])
        self.assertTrue(any(link[1]==1038 and link[3]==2086 for link in patched["links"]))
        self.assertFalse(any(link[1]==2087 and link[3] in {1036,1038} for link in patched["links"]))

    def test_notes_cover_required_authority_and_retention_sections(self):
        from p10_lab.workflow_integration import integrate_moge_depth_diagnostics
        patched=integrate_moge_depth_diagnostics(self._workflow())
        notes=next(n for n in patched["nodes"] if n["id"]==2085)["widgets_values"][0]
        for heading in (
            "Purpose","Inputs","What it does","Outputs","Authority","Geometry impact",
            "Default state","Failure/fallback","TEMP / retention","Next stage",
        ):
            self.assertIn(heading,notes)


if __name__=="__main__":
    unittest.main()
