import json
import tempfile
import unittest
from pathlib import Path


class AuthorDatasetProjectTests(unittest.TestCase):
    def test_author_dataset_is_created_inside_current_attempt(self):
        from p10_lab.author_dataset_project import ConceptGhostP10AuthorDatasetProject

        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"output"
            attempt=output/"conceptghost"/"p10_attempts"/"run1"/"attempt1"
            attempt.mkdir(parents=True)
            (attempt/"attempt_manifest.json").write_text(json.dumps({
                "schema":"ConceptGhost.P10Attempt.v0.1",
                "p10_attempt_id":"attempt1",
                "parent_p9_run_id":"run1",
                "scene_contract_id":"scene1",
            }),encoding="utf-8")

            dataset_dir,rgb,mask,wan,diag=ConceptGhostP10AuthorDatasetProject().make(
                str(attempt),"attempt1","scene1"
            )
            dataset=Path(dataset_dir)
            self.assertEqual(dataset.resolve(),(attempt/"author_dataset").resolve())
            self.assertTrue((dataset/"condition").is_dir())
            self.assertTrue((dataset/"camera_plot").is_dir())
            self.assertTrue((dataset/"wan_inpaint").is_dir())
            self.assertTrue((dataset/"_work").is_dir())
            self.assertTrue((dataset/"conceptghost_author_dataset_project.json").is_file())
            self.assertIn("conceptghost/p10_attempts/run1/attempt1/author_dataset",rgb)
            self.assertTrue(rgb.endswith("/camera_plot/control_rgb"))
            self.assertTrue(mask.endswith("/camera_plot/control_mask"))
            self.assertTrue(wan.endswith("/wan_inpaint/wan_video"))
            self.assertEqual(json.loads(diag)["normal_backfill_required"],False)


if __name__=="__main__":
    unittest.main()
