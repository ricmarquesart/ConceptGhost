import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_p9_boundary import _write_official_run


class PanoramaResultPublisherTests(unittest.TestCase):
    def test_publisher_materializes_cg02_and_marks_functional_pass(self):
        from p10_lab.result_output_contract import initialize_result_output_tree
        from p10_lab.result_output_nodes import ConceptGhostP10PanoramaResultPublisher

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=_write_official_run(
                root/"run1",
                branch_mode="Refined / P9 Clone",
                scene_id="scene1",
            )
            attempt=root/"output"/"conceptghost"/"p10_attempts"/"run1"/"attempt1"
            attempt.mkdir(parents=True)
            manifest={
                "schema":"ConceptGhost.P10Attempt.v0.1",
                "p10_attempt_id":"attempt1",
                "parent_p9_run_id":"run1",
                "scene_contract_id":"scene1",
                "source_p9_run_dir":str(p9.resolve()),
            }
            (attempt/"attempt_manifest.json").write_text(
                json.dumps(manifest),encoding="utf-8"
            )
            initialize_result_output_tree(
                attempt,
                p10_attempt_id="attempt1",
                p9_run_id="run1",
                scene_contract_id="scene1",
                source_p9_run_dir=p9,
            )

            def fake_save(path, image, grayscale=False):
                path=Path(path)
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b"png")
                return {
                    "path":str(path),
                    "sha256":"a"*64,
                    "width":2048,
                    "height":1024,
                    "mode":"L" if grayscale else "RGB",
                }

            def fake_sheet(path, panels):
                path=Path(path)
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b"sheet")
                return {"path":str(path),"sha256":"b"*64}

            node=ConceptGhostP10PanoramaResultPublisher()
            with patch("p10_lab.result_output_nodes._save_image",side_effect=fake_save), \
                 patch("p10_lab.result_output_nodes._make_contact_sheet",side_effect=fake_sheet):
                response=node.publish(
                    str(attempt),
                    "attempt1",
                    str(p9),
                    "scene1",
                    object(),object(),object(),object(),object(),object(),object(),object(),
                    '{"workflow":"author-krea-360"}',
                )

            final_erp, cg02_manifest_path, diagnostics=response["result"]
            self.assertIsNotNone(final_erp)
            self.assertTrue(Path(cg02_manifest_path).is_file())
            stage=attempt/"RESULTS"/"CG_02_PANORAMA_360"
            self.assertTrue((stage/"OUTPUTS"/"01_raw_generated_erp.png").is_file())
            self.assertTrue((stage/"OUTPUTS"/"06_final_erp.png").is_file())
            self.assertTrue((stage/"PREVIEWS"/"panorama_process_contact_sheet.png").is_file())
            status=json.loads((stage/"STATUS.json").read_text(encoding="utf-8"))
            self.assertEqual(status["runtime_status"],"PASS")
            self.assertEqual(status["functional_status"],"PASS")
            self.assertEqual(status["artist_quality_status"],"PENDING")
            self.assertEqual(json.loads(diagnostics)["stage"],"CG_02")


if __name__=="__main__":
    unittest.main()
