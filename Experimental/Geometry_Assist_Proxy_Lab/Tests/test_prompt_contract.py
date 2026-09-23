from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "package" / "Runtime" / "worker" / "geometry_assist_worker.py"

spec = importlib.util.spec_from_file_location("geometry_assist_worker", WORKER)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class FakeTokenizer:
    model_max_length = 77

    def __call__(self, text, truncation=False, add_special_tokens=True):
        # Deterministic stand-in used only to exercise the contract data flow.
        count = len(text.split()) + (2 if add_special_tokens else 0)
        return {"input_ids": list(range(count))}


def main() -> int:
    ok = module.validate_prompt_contract(
        [("tokenizer", FakeTokenizer()), ("tokenizer_2", FakeTokenizer())],
        "same scene preserve camera",
        "changed camera crop",
        77,
    )
    assert ok["tokenizer"]["prompt_tokens"] == 6
    assert ok["tokenizer"]["negative_prompt_tokens"] == 5
    assert ok["tokenizer_2"]["max_tokens"] == 77

    try:
        module.validate_prompt_contract(
            [("tokenizer", FakeTokenizer())],
            " ".join(["x"] * 80),
            "safe",
            77,
        )
    except RuntimeError as exc:
        assert "Prompt contract exceeded CLIP context" in str(exc)
    else:
        raise AssertionError("oversized prompt must fail closed")

    src = WORKER.read_text(encoding="utf-8")
    assert '"prompt_tokenizers": prompt_contract' in src
    assert '"prompt_tokens": prompt_tokens' in src
    assert '"negative_prompt_tokens": negative_tokens' in src
    assert '"prompt_tokens": prompt_tokens,\n            "negative_prompt_tokens": negative_tokens,\n            "runtime_seconds"' not in src

    print("Geometry Assist prompt contract regression: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
