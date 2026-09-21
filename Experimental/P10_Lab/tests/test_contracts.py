import json
from pathlib import Path

from p10_lab.contracts import CompletionBundle, CONTRACT_VERSION
from p10_lab.path_planner import default_paths
from p10_lab.contracts import SceneScale


def test_p9_bundle_and_default_paths(tmp_path: Path):
    for name in ["source.png", "camera.json", "mesh.ply", "run.json"]:
        (tmp_path / name).write_text("x", encoding="utf-8")

    manifest = {
        "contract_version": CONTRACT_VERSION,
        "source_stage": "p9",
        "source_equivalent_to": "baseline",
        "source_run_id": "unit-test",
        "source_image": "source.png",
        "camera": "camera.json",
        "primary_mesh": "mesh.ply",
        "run_metadata": "run.json",
        "optional": {}
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    bundle = CompletionBundle.from_directory(tmp_path)
    assert bundle.source_stage == "p9"
    assert bundle.source_run_id == "unit-test"

    paths = default_paths(SceneScale(10.0))
    assert [p.name for p in paths] == ["left_arc", "right_arc", "forward_probe"]
    assert all(len(p.waypoints) >= 4 for p in paths)


def test_baseline_equivalent_bundle_is_accepted_for_lab_compatibility(tmp_path: Path):
    for name in ["source.png", "camera.json", "mesh.ply", "run.json"]:
        (tmp_path / name).write_text("x", encoding="utf-8")

    manifest = {
        "contract_version": CONTRACT_VERSION,
        "source_stage": "baseline",
        "source_equivalent_to": "baseline",
        "source_run_id": "baseline-compat-test",
        "source_image": "source.png",
        "camera": "camera.json",
        "primary_mesh": "mesh.ply",
        "run_metadata": "run.json",
        "optional": {}
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    bundle = CompletionBundle.from_directory(tmp_path)
    assert bundle.source_stage == "baseline"
