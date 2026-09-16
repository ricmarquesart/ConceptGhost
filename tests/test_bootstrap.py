import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.cg_bootstrap import (
    build_inventory,
    build_parser,
    download_to_temp_and_move,
    classify_comfyui_root,
    discover_comfyui,
    parse_minimal_yaml,
    run_setup,
    run_uninstall,
    sha256_file,
)


class BootstrapTests(unittest.TestCase):
    def test_parse_minimal_yaml_nested_scalars(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "config.yml"
            p.write_text(
                """
project:
  root: C:\\ConceptGhost
  output_root: C:\\ConceptGhost\\output
comfyui:
  root: auto
storage:
  verify_hashes: true
  threshold: 1.25
""".strip(),
                encoding="utf-8",
            )
            cfg = parse_minimal_yaml(p)
            self.assertEqual(cfg["project"]["root"], r"C:\ConceptGhost")
            self.assertEqual(cfg["comfyui"]["root"], "auto")
            self.assertIs(cfg["storage"]["verify_hashes"], True)
            self.assertEqual(cfg["storage"]["threshold"], 1.25)

    def test_external_download_is_blocked_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PermissionError):
                download_to_temp_and_move("https://example.invalid/file", Path(td) / "x", allow=False)

    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.bin"
            p.write_bytes(b"abc")
            self.assertEqual(
                sha256_file(p),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )

    def test_classify_portable_comfyui_root(self):
        with tempfile.TemporaryDirectory() as td:
            dist = Path(td) / "ComfyUI_windows_portable"
            root = dist / "ComfyUI"
            (dist / "python_embeded").mkdir(parents=True)
            root.mkdir(parents=True)
            (root / "main.py").write_text("# marker", encoding="utf-8")
            (dist / "python_embeded" / "python.exe").write_bytes(b"")
            info = classify_comfyui_root(root)
            self.assertEqual(info["mode"], "portable")
            self.assertTrue(info["python_executable"].endswith("python.exe"))

    def test_discover_comfy_desktop_from_installations_json(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            appdata = base / "AppData" / "Roaming"
            install_root = base / "ComfyUI-Installs" / "ConceptGhostTest"
            comfy_root = install_root / "ComfyUI"
            python_exe = comfy_root / ".venv" / "Scripts" / "python.exe"
            python_exe.parent.mkdir(parents=True)
            python_exe.write_bytes(b"")
            (comfy_root / "main.py").write_text("# marker", encoding="utf-8")
            (install_root / ".comfyui-desktop-2").write_text("tracked", encoding="utf-8")

            desktop_data = appdata / "Comfy Desktop"
            desktop_data.mkdir(parents=True)
            (desktop_data / "installations.json").write_text(
                json.dumps([
                    {
                        "id": "local-test",
                        "name": "Local Test",
                        "status": "installed",
                        "installPath": str(install_root),
                    }
                ]),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"APPDATA": str(appdata)}, clear=False):
                found = discover_comfyui()

            matches = [x for x in found if Path(x["root"]) == comfy_root.resolve()]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["mode"], "desktop")
            self.assertEqual(Path(matches[0]["python_executable"]), python_exe.resolve())
            self.assertIn("installations.json", matches[0]["discovery_source"])

    def test_cli_accepts_project_root_after_subcommand(self):
        args = build_parser().parse_args(["setup", "--project-root", r"D:\Ghost", "--apply"])
        self.assertEqual(args.project_root, r"D:\Ghost")
        self.assertTrue(args.apply)

    def test_setup_dry_run_does_not_create_project_root(self):
        with tempfile.TemporaryDirectory() as td:
            package_root = Path(__file__).resolve().parents[1]
            target = Path(td) / "ConceptGhost"
            result = run_setup(
                package_root=package_root,
                project_root=target,
                dry_run=True,
            )
            self.assertFalse(target.exists())
            self.assertGreater(len(result["planned_operations"]), 0)
            self.assertEqual(len(result["future_download_estimates"]), 2)
            self.assertEqual(result["status"], "dry-run")

    def test_setup_apply_creates_structure_and_manifests(self):
        with tempfile.TemporaryDirectory() as td:
            package_root = Path(__file__).resolve().parents[1]
            target = Path(td) / "ConceptGhost"
            result = run_setup(
                package_root=package_root,
                project_root=target,
                dry_run=False,
            )
            self.assertEqual(result["status"], "applied")
            self.assertGreater(result["actual_project_bytes_added"], 0)
            for rel in [
                "scripts",
                "logs",
                "manifests",
                "workflows/reference/atlas",
                "workflows/reference/da3",
                "workflows/reference/moge",
                "workflows/project",
                "output",
                "cache/downloads",
                "maya",
            ]:
                self.assertTrue((target / rel).exists(), rel)
            self.assertTrue((target / "SETUP.bat").exists())
            self.assertTrue((target / "config.yml").exists())
            self.assertTrue((target / "manifests/install_manifest.json").exists())
            self.assertTrue((target / "manifests/disk_ledger.json").exists())
            self.assertTrue((target / "manifests/disk_ledger.csv").exists())
            manifest = json.loads((target / "manifests/install_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], 1)
            self.assertTrue(any(x["relative_path"] == "SETUP.bat" for x in manifest["managed_files"]))

    def test_setup_apply_is_idempotent_for_payload(self):
        with tempfile.TemporaryDirectory() as td:
            package_root = Path(__file__).resolve().parents[1]
            target = Path(td) / "ConceptGhost"
            run_setup(package_root=package_root, project_root=target, dry_run=False)
            first_hash = sha256_file(target / "scripts/cg_bootstrap.py")
            run_setup(package_root=package_root, project_root=target, dry_run=False)
            second_hash = sha256_file(target / "scripts/cg_bootstrap.py")
            self.assertEqual(first_hash, second_hash)
            self.assertFalse((target / "config.yml.new").exists())

    def test_existing_config_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            package_root = Path(__file__).resolve().parents[1]
            target = Path(td) / "ConceptGhost"
            target.mkdir(parents=True)
            config = target / "config.yml"
            config.write_text("project:\n  root: Z:\\KeepMe\n", encoding="utf-8")
            run_setup(package_root=package_root, project_root=target, dry_run=False)
            self.assertIn("Z:\\KeepMe", config.read_text(encoding="utf-8"))
            self.assertTrue((target / "config.default.yml").exists())

    def test_uninstall_preserves_outputs_and_modified_files(self):
        with tempfile.TemporaryDirectory() as td:
            package_root = Path(__file__).resolve().parents[1]
            target = Path(td) / "ConceptGhost"
            run_setup(package_root=package_root, project_root=target, dry_run=False)
            output_file = target / "output" / "keep.txt"
            output_file.write_text("artist output", encoding="utf-8")
            managed = target / "scripts/cg_bootstrap.py"
            managed.write_text(managed.read_text(encoding="utf-8") + "\n# user edit\n", encoding="utf-8")
            result = run_uninstall(project_root=target, dry_run=False, preserve_output=True, force=False)
            self.assertTrue(output_file.exists())
            self.assertTrue(managed.exists())
            self.assertTrue(any("modified" in x["reason"] for x in result["skipped"]))

    def test_inventory_marks_existing_da3_model_preexisting(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            dist = base / "ComfyUI_windows_portable"
            root = dist / "ComfyUI"
            (dist / "python_embeded").mkdir(parents=True)
            (dist / "python_embeded" / "python.exe").write_bytes(b"")
            (root / "models" / "depthanything3").mkdir(parents=True)
            (root / "custom_nodes" / "ComfyUI-DepthAnythingV3").mkdir(parents=True)
            (root / "comfy_extras").mkdir(parents=True)
            (root / "main.py").write_text("# marker", encoding="utf-8")
            (root / "comfy_extras" / "nodes_moge.py").write_text("# native", encoding="utf-8")
            model = root / "models" / "depthanything3" / "da3_base.safetensors"
            model.write_bytes(b"existing-model")
            inventory, _ = build_inventory(base / "ConceptGhost", str(root), hash_models=True)
            models = inventory["comfyui"]["components"]["models"]
            self.assertEqual(len(models), 1)
            self.assertTrue(models[0]["preexisting"])
            self.assertEqual(models[0]["sha256"], sha256_file(model))
            self.assertTrue(inventory["comfyui"]["components"]["native_moge"])

    def test_setup_preserves_unmanaged_conflicting_payload(self):
        with tempfile.TemporaryDirectory() as td:
            package_root = Path(__file__).resolve().parents[1]
            target = Path(td) / "ConceptGhost"
            target.mkdir(parents=True)
            original = target / "SETUP.bat"
            original.write_text("user version", encoding="utf-8")
            run_setup(package_root=package_root, project_root=target, dry_run=False)
            self.assertEqual(original.read_text(encoding="utf-8"), "user version")
            self.assertTrue((target / "SETUP.bat.new").exists())

    def test_setup_launcher_pauses_before_exit(self):
        package_root = Path(__file__).resolve().parents[1]
        bat = (package_root / "SETUP.bat").read_text(encoding="utf-8", errors="ignore").lower()
        self.assertIn("press any key to close", bat)
        self.assertIn("pause >nul", bat)
        self.assertLess(bat.rfind("pause >nul"), bat.rfind("exit /b"))


if __name__ == "__main__":
    unittest.main()
