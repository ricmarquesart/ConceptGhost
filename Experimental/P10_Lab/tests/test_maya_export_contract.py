import tempfile
import unittest
from pathlib import Path


class DualMayaDeliverableContractTests(unittest.TestCase):
    def test_p10_target_is_separate_from_p9(self):
        from p10_lab.maya_export_contract import derive_p10_refined_maya_target
        with tempfile.TemporaryDirectory() as tmp:
            p9=Path(tmp)/"ConceptGhost_scene_P9.ma"
            target=derive_p10_refined_maya_target(p9)
            self.assertEqual(target.name,"ConceptGhost_scene_P10_Refined.ma")
            self.assertNotEqual(target,p9.resolve())

    def test_overwrite_p9_fails_closed(self):
        from p10_lab.maya_export_contract import validate_dual_maya_targets
        with tempfile.TemporaryDirectory() as tmp:
            p9=Path(tmp)/"scene.ma"
            with self.assertRaisesRegex(ValueError,"never overwrite"):
                validate_dual_maya_targets(p9,p9)


if __name__=="__main__":
    unittest.main()
