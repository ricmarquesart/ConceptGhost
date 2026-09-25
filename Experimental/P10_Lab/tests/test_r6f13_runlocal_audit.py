from pathlib import Path

from p10_lab.run_audit_bundle import default_project_audit_root


def test_r6f13_audit_root_is_dynamic_p9_run_folder(tmp_path: Path) -> None:
    p9_run = tmp_path / "artist_output" / "scene_name" / "20260925_RUN"
    resolved = default_project_audit_root(p9_run, "P10_ATTEMPT")
    assert resolved == p9_run.resolve()
    assert "P10_AUDIT" not in resolved.parts
