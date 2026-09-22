import unittest


class P10LayoutTests(unittest.TestCase):
    def _workflow(self):
        sizes = {
            2100:(620,520), 2101:(360,300), 2102:(360,300), 2103:(260,100),
            2104:(360,300), 2105:(360,300), 2106:(260,100), 2107:(360,300),
            2108:(360,300), 2200:(430,90), 2201:(430,82), 2202:(430,58),
            2203:(430,106), 2204:(460,125), 2205:(460,125), 2206:(430,60),
            2207:(650,520), 2208:(520,420), 2300:(680,390), 2301:(560,430),
        }
        nodes=[{"id":i,"pos":[0,0],"size":list(size)} for i,size in sizes.items()]
        # Proven v1.53 Refined guide that used to overlap Gate 5/6.
        nodes.append({"id":1063,"pos":[10940,7990],"size":[1500,520]})
        return {"nodes":nodes,"links":[]}

    @staticmethod
    def _overlap(a,b):
        ax,ay=a["pos"]; aw,ah=a["size"]
        bx,by=b["pos"]; bw,bh=b["size"]
        return min(ax+aw,bx+bw)>max(ax,bx) and min(ay+ah,by+bh)>max(ay,by)

    def test_known_p10_nodes_do_not_overlap_each_other_or_refined_guide(self):
        from p10_lab.workflow_integration import organize_p10_layout
        wf=organize_p10_layout(self._workflow())
        nodes=wf["nodes"]
        for i,a in enumerate(nodes):
            for b in nodes[i+1:]:
                self.assertFalse(
                    self._overlap(a,b),
                    f"layout overlap: {a['id']} vs {b['id']}",
                )

    def test_p10_visual_lane_is_below_existing_refined_graph(self):
        from p10_lab.workflow_integration import organize_p10_layout
        wf=organize_p10_layout(self._workflow())
        for node in wf["nodes"]:
            if 2100 <= node["id"] <= 2301:
                self.assertGreaterEqual(node["pos"][1], 9600)

    def test_layout_only_changes_positions(self):
        from copy import deepcopy
        from p10_lab.workflow_integration import organize_p10_layout
        wf=self._workflow()
        before=deepcopy(wf)
        organize_p10_layout(wf)
        for old,new in zip(before["nodes"],wf["nodes"]):
            self.assertEqual(old["id"],new["id"])
            self.assertEqual(old["size"],new["size"])
        self.assertEqual(before["links"],wf["links"])


if __name__=="__main__":
    unittest.main()
