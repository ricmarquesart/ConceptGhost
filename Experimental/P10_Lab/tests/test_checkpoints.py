import json
import tempfile
import unittest
from pathlib import Path

from p10_lab.checkpoints import (
    PreviewArtifact,
    PreviewRole,
    VisualCheckpoint,
    checkpoint_context_digest,
    load_checkpoint_manifest,
    required_preview_roles,
    write_checkpoint_manifest,
)
from p10_lab.contracts import ContractError
from p10_lab.pipeline import Stage


class VisualCheckpointTests(unittest.TestCase):
    context_digest = "a" * 64

    def _control_checkpoint(self) -> VisualCheckpoint:
        artifact = PreviewArtifact(
            role=PreviewRole.CONTROL_VIDEO,
            relative_path="flights/flight_01/control.mp4",
            media_type="video/mp4",
            sha256="b" * 64,
            provenance="p9_raw_hole_control",
        )
        return VisualCheckpoint(
            stage=Stage.CONTROL_RENDER,
            flight_id="flight_01",
            artifacts=(artifact,),
            validated=True,
            context_digest=self.context_digest,
        )

    def test_pipeline_requires_four_distinct_node_visible_preview_roles(self):
        self.assertEqual(
            required_preview_roles(),
            (
                PreviewRole.CONTROL_VIDEO,
                PreviewRole.HOLE_MASK_VIDEO,
                PreviewRole.WAN_FILLED_VIDEO,
                PreviewRole.SOURCE_COMPOSITE_VIDEO,
            ),
        )

    def test_checkpoint_digest_detects_changed_preview_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            preview = root / "flights" / "flight_01" / "control.mp4"
            preview.parent.mkdir(parents=True)
            preview.write_bytes(b"raw-control-video")
            artifact = PreviewArtifact.from_file(
                root=root,
                role=PreviewRole.CONTROL_VIDEO,
                path=preview,
                media_type="video/mp4",
                provenance="p9_raw_hole_control",
            )
            checkpoint = VisualCheckpoint(
                stage=Stage.CONTROL_RENDER,
                flight_id="flight_01",
                artifacts=(artifact,),
                validated=True,
                context_digest=self.context_digest,
            )

            self.assertTrue(checkpoint.can_resume(root, self.context_digest))
            self.assertFalse(checkpoint.can_resume(root, "c" * 64))
            preview.write_bytes(b"changed")
            self.assertFalse(checkpoint.can_resume(root, self.context_digest))

    def test_preview_paths_cannot_escape_checkpoint_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            outside = root.parent / "outside.mp4"
            outside.write_bytes(b"outside")
            self.addCleanup(outside.unlink, missing_ok=True)

            with self.assertRaises(ContractError):
                PreviewArtifact.from_file(
                    root=root,
                    role=PreviewRole.CONTROL_VIDEO,
                    path=outside,
                    media_type="video/mp4",
                    provenance="invalid",
                )

    def test_manifest_writer_rejects_flights_symlink_outside_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "checkpoints"
            outside = workspace / "outside"
            root.mkdir()
            outside.mkdir()
            try:
                (root / "flights").symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Directory symlinks are unavailable: {error}")

            with self.assertRaises(ContractError):
                write_checkpoint_manifest(root, self._control_checkpoint())

            self.assertFalse((outside / "flight_01").exists())

    def test_manifest_writer_does_not_follow_predictable_temporary_symlink(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            root = workspace / "checkpoints"
            manifest_dir = root / "flights" / "flight_01"
            manifest_dir.mkdir(parents=True)
            outside = workspace / "outside.txt"
            outside.write_text("do-not-change", encoding="utf-8")
            predictable_temp = manifest_dir / "control_render.checkpoint.json.tmp"
            try:
                predictable_temp.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"File symlinks are unavailable: {error}")

            manifest_path = write_checkpoint_manifest(root, self._control_checkpoint())

            self.assertEqual(outside.read_text(encoding="utf-8"), "do-not-change")
            self.assertTrue(predictable_temp.is_symlink())
            self.assertTrue(manifest_path.is_file())

    def test_artifact_path_rejects_embedded_nul(self):
        with self.assertRaises(ContractError):
            PreviewArtifact(
                role=PreviewRole.CONTROL_VIDEO,
                relative_path="flights/flight_01/control\x00.mp4",
                media_type="video/mp4",
                sha256="b" * 64,
                provenance="p9_raw_hole_control",
            )

    def test_resume_treats_symlink_resolution_failure_as_nonresumable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            preview = root / "flights" / "flight_01" / "control.mp4"
            preview.parent.mkdir(parents=True)
            try:
                preview.symlink_to(preview.name)
            except OSError as error:
                self.skipTest(f"File symlinks are unavailable: {error}")

            self.assertFalse(
                self._control_checkpoint().can_resume(root, self.context_digest)
            )

    def test_checkpoint_manifest_round_trip_remains_resumable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            preview = root / "flights" / "flight_02" / "mask.mp4"
            preview.parent.mkdir(parents=True)
            preview.write_bytes(b"binary-hole-mask-video")
            artifact = PreviewArtifact.from_file(
                root=root,
                role=PreviewRole.HOLE_MASK_VIDEO,
                path=preview,
                media_type="video/mp4",
                provenance="p10_disocclusion_mask",
            )
            checkpoint = VisualCheckpoint(
                stage=Stage.DISOCCLUSION_MASK,
                flight_id="flight_02",
                artifacts=(artifact,),
                validated=True,
                context_digest=self.context_digest,
            )

            manifest_path = write_checkpoint_manifest(root, checkpoint)
            loaded = load_checkpoint_manifest(manifest_path)

            self.assertEqual(manifest_path.name, "disocclusion_mask.checkpoint.json")
            self.assertEqual(loaded, checkpoint)
            self.assertTrue(loaded.can_resume(root, self.context_digest))

    def test_flight_id_rejects_unix_and_windows_path_traversal(self):
        artifact = PreviewArtifact(
            role=PreviewRole.CONTROL_VIDEO,
            relative_path="flights/flight_01/control.mp4",
            media_type="video/mp4",
            sha256="b" * 64,
            provenance="p9_raw_hole_control",
        )
        invalid_ids = (
            "../../../escaped",
            r"..\..\escaped",
            "/absolute",
            r"C:\escaped",
            ".",
            "..",
        )
        for flight_id in invalid_ids:
            with self.subTest(flight_id=flight_id), self.assertRaises(ContractError):
                VisualCheckpoint(
                    stage=Stage.CONTROL_RENDER,
                    flight_id=flight_id,
                    artifacts=(artifact,),
                    validated=True,
                    context_digest=self.context_digest,
                )

    def test_artifact_must_belong_to_the_checkpoint_flight(self):
        artifact = PreviewArtifact(
            role=PreviewRole.CONTROL_VIDEO,
            relative_path="flights/flight_01/control.mp4",
            media_type="video/mp4",
            sha256="b" * 64,
            provenance="p9_raw_hole_control",
        )

        with self.assertRaises(ContractError):
            VisualCheckpoint(
                stage=Stage.CONTROL_RENDER,
                flight_id="flight_02",
                artifacts=(artifact,),
                validated=True,
                context_digest=self.context_digest,
            )

    def test_manifest_rejects_string_boolean_and_malformed_artifact_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "invalid.json"
            base = {
                "checkpoint_version": 1,
                "stage": "control_render",
                "flight_id": "flight_01",
                "validated": "false",
                "context_digest": self.context_digest,
                "artifacts": [
                    {
                        "role": "control_video",
                        "relative_path": "flights/flight_01/control.mp4",
                        "media_type": "video/mp4",
                        "sha256": "b" * 64,
                        "provenance": "p9_raw_hole_control",
                    }
                ],
            }
            manifest.write_text(json.dumps(base), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_checkpoint_manifest(manifest)

            base["validated"] = True
            base["artifacts"][0]["sha256"] = "not-a-sha256"
            manifest.write_text(json.dumps(base), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_checkpoint_manifest(manifest)

    def test_context_digest_changes_with_source_or_flight_definition(self):
        common = {
            "source_inputs": {"mesh": "1" * 64, "camera": "2" * 64},
            "flight_definition": {"name": "left_arc", "waypoints": [0, 1]},
            "control_policy": {"fill_holes": False},
            "adapter_versions": {"renderer": "splatkit-pinned"},
        }
        first = checkpoint_context_digest(source_run_id="run-a", **common)
        second = checkpoint_context_digest(source_run_id="run-b", **common)

        self.assertNotEqual(first, second)
        self.assertEqual(len(first), 64)


if __name__ == "__main__":
    unittest.main()
