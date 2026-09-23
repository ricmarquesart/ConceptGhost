import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOTFIX = ROOT / "release_hotfixes" / "r10"
R9_RELEASE = ROOT / "releases" / "DR9R_R9_INSTALLER_HOTFIX_PACKAGE_20260923.json"


class DR9RR10NestedInstallerContractTests(unittest.TestCase):
    def _script(self, name):
        path = HOTFIX / "Installer" / name
        self.assertTrue(path.is_file(), f"missing r10 installer hotfix: {path}")
        return path.read_text(encoding="utf-8-sig")

    def test_gate5_uses_current_production_workflow_privately_in_dr9r_mode(self):
        source = self._script("install_gate5.ps1")
        self.assertIn('CONCEPTGHOST_INTERNAL_BASE_WORKFLOW_ONLY', source)
        self.assertIn('workflows\\02_ConceptGhost_P10_PRODUCTION.json', source)
        self.assertIn('internal\\workflows', source)
        self.assertIn('02_ConceptGhost_P10_PRODUCTION_GATE5_VERIFY.json', source)
        self.assertIn('ConceptGhost_v1.54_P10_Gate05_REFINED_WAN_PREVIEW_r1.json', source)
        self.assertLess(source.index('if ($InternalBaseWorkflowOnly)'), source.index('} else {'))

    def test_gate6_uses_current_production_workflow_privately_in_dr9r_mode(self):
        source = self._script("install_gate6.ps1")
        self.assertIn('CONCEPTGHOST_INTERNAL_BASE_WORKFLOW_ONLY', source)
        self.assertIn('workflows\\02_ConceptGhost_P10_PRODUCTION.json', source)
        self.assertIn('internal\\workflows', source)
        self.assertIn('02_ConceptGhost_P10_PRODUCTION_GATE6_VERIFY.json', source)
        self.assertIn('ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_PREVIEW_r10.json', source)
        self.assertLess(source.index('if ($InternalBaseWorkflowOnly)'), source.index('} else {'))

    def test_r10_does_not_change_the_public_two_workflow_contract(self):
        release = json.loads(R9_RELEASE.read_text(encoding="utf-8"))
        self.assertEqual(
            release["workflows"],
            [
                "01_ConceptGhost_P10_ROUTE_SETUP.json",
                "02_ConceptGhost_P10_PRODUCTION.json",
            ],
        )
        readme = (HOTFIX / "README.md").read_text(encoding="utf-8")
        self.assertIn("exactly `01_ConceptGhost_P10_ROUTE_SETUP.json` and `02_ConceptGhost_P10_PRODUCTION.json`", readme)

    def test_hotfix_is_installer_only(self):
        paths = sorted(
            p.relative_to(HOTFIX).as_posix()
            for p in HOTFIX.rglob("*")
            if p.is_file()
        )
        self.assertEqual(
            paths,
            [
                "Installer/install_gate5.ps1",
                "Installer/install_gate6.ps1",
                "README.md",
            ],
        )


if __name__ == "__main__":
    unittest.main()
