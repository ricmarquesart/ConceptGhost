from enum import IntEnum


class GeometrySource(IntEnum):
    OBSERVED_P9_BASELINE = 1
    P9_BASELINE_LOW_CONFIDENCE = 2
    P10_GENERATED_VIEW = 3
    P10_RECONSTRUCTED = 4
    P10_TRANSITION = 5
    P10_REPAIRED = 6


def source_name(value: int) -> str:
    return GeometrySource(value).name
