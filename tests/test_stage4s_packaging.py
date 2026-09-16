import unittest
from pathlib import Path


class Stage4SPackagingTests(unittest.TestCase):
    def test_ci_builds_validated_stage4s_release_artifact(self):
        workflow = Path('.github/workflows/tests.yml').read_text(encoding='utf-8')
        required = [
            'release-package:',
            'needs: unit-tests',
            'ConceptGhost_Stage04S_v0.4.6.zip',
            'ConceptGhost_Stage04S_v0.4.6_SHA256.txt',
            'ConceptGhost_Stage04S_v0.4.6_validation.txt',
            'stage04s_v0.4.6_tests.log',
            'stage04s_v0.4.6_smoke.log',
            'actions/upload-artifact@v4',
            'ConceptGhost_Stage04S_v0.4.6_READY',
            'git archive --format=zip',
            'Expand-Archive',
            'CRLF',
            'scripts/cg_find_python.ps1',
        ]
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, workflow)


if __name__ == '__main__':
    unittest.main()
