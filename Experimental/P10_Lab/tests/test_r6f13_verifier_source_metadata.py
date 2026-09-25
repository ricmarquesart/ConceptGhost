from pathlib import Path


def test_r6f13_builder_removes_stale_dr9r_source_sha_pin() -> None:
    builder = (
        Path(__file__).resolve().parents[1]
        / "release_hotfixes"
        / "gate7_r6f12_p9_baseline_quality_restore"
        / "build_gate7_r6f12_from_r15.py"
    )
    text = builder.read_text(encoding="utf-8")
    assert "invalid DR9R source commit metadata" in text
    assert "unexpected DR9R source commit" not in text
    assert "re.fullmatch(r'[0-9a-f]{40}',source_commit)" in text
