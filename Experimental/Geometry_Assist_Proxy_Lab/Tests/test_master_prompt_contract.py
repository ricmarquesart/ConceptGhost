from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "package" / "Config" / "geometry_assist_config.json"


def main() -> int:
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    prompt = cfg["prompt"].lower()
    negative = cfg["negative_prompt"].lower()

    assert cfg["schema"] == "ConceptGhost.GeometryAssistDiagnostic.Config.v5"
    assert cfg["defaults"]["profile"] == "GEOMETRY_ASSIST_MOGE_MASTER"
    assert cfg["defaults"]["prompt_intent"] == "MONOCULAR_GEOMETRY_READABILITY"

    for marker in [
        "monocular 3d estimation",
        "preserve camera",
        "perspective",
        "composition",
        "silhouettes",
        "proportions",
        "architecture",
        "object layout",
        "reduce painterly ambiguity",
        "clarify planes",
        "occlusions",
        "contact shadows",
        "depth layering",
        "neutral readable lighting",
    ]:
        assert marker in prompt, marker

    for marker in [
        "changed camera",
        "changed fov",
        "moved objects",
        "changed proportions",
        "warped architecture",
        "hallucinated structures",
        "cinematic relighting",
        "scene redesign",
    ]:
        assert marker in negative, marker

    # Avoid drifting back toward a beauty/photorealism objective.
    assert "photoreal" not in prompt
    assert "cinematic" not in prompt
    assert len(cfg["prompt"].split()) < 35
    assert len(cfg["negative_prompt"].split()) < 35

    print("Geometry Assist MoGe master prompt contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
