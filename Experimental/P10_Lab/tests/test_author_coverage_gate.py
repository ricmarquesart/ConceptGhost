import json
import math
import tempfile
import unittest
from pathlib import Path

from tests.test_p9_boundary import _write_official_run


class AuthorCoverageGateTests(unittest.TestCase):
    def _write_rail(self, path: Path, phase: float):
        try:
            import numpy as np
        except ImportError as error:
            self.skipTest(f"NumPy unavailable: {error}")
        mats=[]
        for index in range(81):
            t=index/80.0
            angle=2.0*math.pi*t
            x=0.25*math.sin(angle+phase)*t
            z=1.5*t + 0.10*math.cos(angle+phase)
            y=0.15*math.sin(2.0*angle+phase)
            c2w=np.eye(4,dtype=float)
            c2w[:3,3]=[x,y,z]
            w2c=np.linalg.inv(c2w)
            mats.append(w2c.tolist())
        # force exact common panorama origin at frame 0
        mats[0]=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        path.write_text(json.dumps(mats),encoding="utf-8")

    def test_publishes_five_rail_coverage_evidence(self):
        try:
            import numpy  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError as error:
            self.skipTest(f"Coverage runtime deps unavailable: {error}")

        from p10_lab.author_coverage_gate import ConceptGhostP10AuthorCoverageGate
        from p10_lab.result_output_contract import initialize_result_output_tree

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=_write_official_run(
                root/"run1",
                branch_mode="Refined / P9 Clone",
                scene_id="scene1",
            )
            attempt=root/"output"/"conceptghost"/"p10_attempts"/"run1"/"attempt1"
            attempt.mkdir(parents=True)
            (attempt/"attempt_manifest.json").write_text(json.dumps({
                "schema":"ConceptGhost.P10Attempt.v0.1",
                "p10_attempt_id":"attempt1",
                "parent_p9_run_id":"run1",
                "scene_contract_id":"scene1",
                "source_p9_run_dir":str(p9.resolve()),
            }),encoding="utf-8")
            initialize_result_output_tree(
                attempt,
                p10_attempt_id="attempt1",
                p9_run_id="run1",
                scene_contract_id="scene1",
                source_p9_run_dir=p9,
            )
            rails=[]
            for index in range(5):
                path=root/f"rail_{index+1}.json"
                self._write_rail(path,index*0.35)
                rails.append(path)

            ready,manifest_path,_=ConceptGhostP10AuthorCoverageGate().publish(
                str(attempt),"attempt1","scene1",*(str(path) for path in rails)
            )
            self.assertTrue(ready)
            self.assertTrue(Path(manifest_path).is_file())
            stage=attempt/"RESULTS"/"CG_05_CAMERA_COVERAGE"
            self.assertTrue((stage/"OUTPUTS"/"combined_camera_positions.csv").is_file())
            self.assertTrue((stage/"PREVIEWS"/"combined_author_rail_top_view.png").is_file())
            status=json.loads((stage/"STATUS.json").read_text(encoding="utf-8"))
            self.assertEqual(status["functional_status"],"PASS")
            self.assertEqual(status["artist_quality_status"],"PENDING")


if __name__=="__main__":
    unittest.main()
