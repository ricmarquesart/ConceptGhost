import hashlib
import json
import tempfile
import unittest
from pathlib import Path


class ReleaseIntegrityTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, data: bytes = b"x") -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def _fixture(self, root: Path, revision: str = "r8"):
        from p10_lab.release_integrity import MIN_COUNTS, REQUIRED_GATE6_PATHS

        for relative in REQUIRED_GATE6_PATHS:
            self._write(root, relative)

        master = root / "ConceptGhost_Master_v1.53.0.json"
        master.write_text("{}", encoding="utf-8")

        for relative, minimum in MIN_COUNTS.items():
            folder = root / relative
            folder.mkdir(parents=True, exist_ok=True)
            existing = sum(1 for child in folder.iterdir() if child.is_file())
            for i in range(existing, minimum):
                self._write(root, f"{relative}/placeholder_{i:03d}.txt")

        workflow_rel = (
            f"Payload/workflows/"
            f"ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_PREVIEW_{revision}.json"
        )
        self._write(root, workflow_rel, b"{}")

        sparse = root / "Payload/custom_nodes/ConceptGhost_P10_Lab/sparse_triangulation.py"
        sparse.write_text("print('authority')\n", encoding="utf-8")
        raw = sparse.read_bytes()
        blob = hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()

        release = {
            "release": (
                f"ConceptGhost_v1.54_P10_Gate06_REFINED_RECONSTRUCTION_PREVIEW_{revision}"
            ),
            "workflow": workflow_rel,
            "installed_sparse_authority_git_blob_sha1": blob,
        }
        (root / "P10_GATE6_RELEASE.json").write_text(
            json.dumps(release), encoding="utf-8"
        )
        (root / "03_INSTALL_ALL.bat").write_text(
            f"echo ConceptGhost Gate 6 {revision}\n", encoding="utf-8"
        )
        (root / "README_P10_GATE6_RECONSTRUCTION.md").write_text(
            f"# Gate 6 {revision}\n", encoding="utf-8"
        )

        # Build checksums last so every listed byte reflects the final fixture.
        checksummed = [
            "03_INSTALL_ALL.bat",
            "P10_GATE6_RELEASE.json",
            "Payload/custom_nodes/ConceptGhost_Stage68/nodes.py",
            "Payload/custom_nodes/ConceptGhost_P10_Lab/sparse_triangulation.py",
        ]
        lines = []
        for relative in checksummed:
            digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
            lines.append(f"{digest}  {relative}")
        (root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_complete_fixture_passes(self):
        from p10_lab.release_integrity import validate_gate6_complete_bundle
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            result = validate_gate6_complete_bundle(root, expected_revision="r8")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["revision"], "r8")

    def test_missing_stage68_nodes_fails(self):
        from p10_lab.release_integrity import ReleaseIntegrityError, validate_gate6_complete_bundle
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            (root / "Payload/custom_nodes/ConceptGhost_Stage68/nodes.py").unlink()
            with self.assertRaises(ReleaseIntegrityError):
                validate_gate6_complete_bundle(root, expected_revision="r8")

    def test_partial_p10_folder_fails(self):
        from p10_lab.release_integrity import ReleaseIntegrityError, validate_gate6_complete_bundle
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            folder = root / "Payload/custom_nodes/ConceptGhost_P10_Lab"
            for path in sorted(folder.glob("placeholder_*.txt"))[:8]:
                path.unlink()
            with self.assertRaises(ReleaseIntegrityError):
                validate_gate6_complete_bundle(root, expected_revision="r8")

    def test_revision_mismatch_fails(self):
        from p10_lab.release_integrity import ReleaseIntegrityError, validate_gate6_complete_bundle
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, revision="r8")
            with self.assertRaises(ReleaseIntegrityError):
                validate_gate6_complete_bundle(root, expected_revision="r9")

    def test_sparse_authority_blob_mismatch_fails(self):
        from p10_lab.release_integrity import ReleaseIntegrityError, validate_gate6_complete_bundle
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            sparse = root / "Payload/custom_nodes/ConceptGhost_P10_Lab/sparse_triangulation.py"
            sparse.write_text("print('stale')\n", encoding="utf-8")
            with self.assertRaises(ReleaseIntegrityError):
                validate_gate6_complete_bundle(root, expected_revision="r8")

    def test_checksum_mismatch_fails(self):
        from p10_lab.release_integrity import ReleaseIntegrityError, validate_gate6_complete_bundle
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            target = root / "Payload/custom_nodes/ConceptGhost_Stage68/nodes.py"
            target.write_text("changed", encoding="utf-8")
            with self.assertRaises(ReleaseIntegrityError):
                validate_gate6_complete_bundle(root, expected_revision="r8")


if __name__ == "__main__":
    unittest.main()
