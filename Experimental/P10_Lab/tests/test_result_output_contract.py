import json
import tempfile
import unittest
from pathlib import Path

from tests.test_p9_boundary import _write_official_run


class ResultOutputContractTests(unittest.TestCase):
    def test_initializes_all_artist_result_stages_and_seeds_p9_evidence(self):
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
            result=initialize_result_output_tree(
                attempt,
                p10_attempt_id="attempt1",
                p9_run_id="run1",
                scene_contract_id="scene1",
                source_p9_run_dir=p9,
            )
            result_root=Path(result["result_root"])
            self.assertEqual(result["stage_count"],19)
            self.assertFalse(result["manual_backfill_required"])
            index_path=result_root/"RESULT_INDEX.json"
            self.assertTrue(index_path.is_file())
            index=json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(
                index["result_tree_location_policy"],
                "DURABLE_SIBLING_P10_BESIDE_P9_SCENE_FROM_CREATION",
            )
            self.assertTrue((result_root/"CG_00_P9_AUTHORITY"/"OUTPUTS"/"source_concept.png").is_file())
            self.assertTrue((result_root/"CG_00_P9_AUTHORITY"/"OUTPUTS"/"camera.json").is_file())
            self.assertTrue((result_root/"CG_00_P9_AUTHORITY"/"PREVIEWS"/"source_concept.png").is_file())
            self.assertTrue((result_root/"CG_18_COMPLETE_RELEASE"/"MANIFESTS").is_dir())

    def test_functional_pass_is_rejected_without_physical_outputs_previews_and_manifests(self):
        from p10_lab.contracts import ContractError
        from p10_lab.result_output_contract import initialize_result_output_tree,update_stage_status

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p9=_write_official_run(
                root/"run1",
                branch_mode="Refined / P9 Clone",
                scene_id="scene1",
            )
            attempt=root/"attempt1"
            attempt.mkdir()
            initialize_result_output_tree(
                attempt,
                p10_attempt_id="attempt1",
                p9_run_id="run1",
                scene_contract_id="scene1",
                source_p9_run_dir=p9,
            )
            with self.assertRaisesRegex(ContractError,"cannot be functional PASS"):
                update_stage_status(
                    attempt,
                    p10_attempt_id="attempt1",
                    p9_run_id="run1",
                    scene_contract_id="scene1",
                    stage_code="CG_02",
                    runtime_status="PASS",
                    functional_status="PASS",
                    artist_quality_status="PENDING",
                )


if __name__=="__main__":
    unittest.main()
