import unittest
from pathlib import Path


class Stage4SPackagingTests(unittest.TestCase):
    def test_ci_builds_validated_stage4s_release_artifact(self):
        workflow = Path('.github/workflows/tests.yml').read_text(encoding='utf-8')
        required = [
            'release-package:',
            'needs: unit-tests',
            'ConceptGhost_Stage04S_v0.4.5.zip',
            'ConceptGhost_Stage04S_v0.4.5_SHA256.txt',
            'ConceptGhost_Stage04S_v0.4.5_validation.txt',
            'stage04s_v0.4.5_tests.log',
            'stage04s_v0.4.5_smoke.log',
            'actions/upload-artifact@v4',
            'ConceptGhost_Stage04S_v0.4.5_READY',
            'git archive --format=zip',
            'Expand-Archive',
            'CRLF',
        ]
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, workflow)


if __name__ == '__main__':
    unittest.main()
