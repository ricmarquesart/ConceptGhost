import unittest
from pathlib import Path


class DA3SourceLayoutTests(unittest.TestCase):
    def test_stage4_loader_uses_readable_source_parts(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        loader = (scripts / "cg_da3_baseline.py").read_text(encoding="utf-8")
        parts = sorted(scripts.glob("cg_da3_baseline_part*.pyinc"))
        self.assertGreaterEqual(len(parts), 4)
        self.assertIn("exec(compile", loader)
        joined = "\n".join(p.read_text(encoding="utf-8") for p in parts)
        self.assertIn("def plan_da3_baseline", joined)
        self.assertIn("def apply_da3_baseline", joined)
        self.assertIn("DA3_PINNED_COMMIT", joined)


if __name__ == "__main__":
    unittest.main()
