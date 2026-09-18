from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_nodes" / "ConceptGhost_Stage68"
sys.path.insert(0, str(PKG))

def test_write_usda_points_json_safe_metadata(tmp_path):
    import conceptghost_io
    path = tmp_path / "pointcloud.usda"
    xyz = np.array([[1.0, 2.0, 3.0], [-1.5, 0.25, 4.0]], dtype=np.float32)
    rgb = np.array([[255, 128, 0], [10, 20, 30]], dtype=np.uint8)
    metadata = {
        "engine": "MoGe-3",
        "point_count": np.int64(2),
        "score": np.float32(0.75),
        "intrinsics": np.eye(3, dtype=np.float32),
    }
    result = conceptghost_io.write_usda_points(path, xyz, rgb, point_width=0.01, metadata=metadata)
    assert result == path
    text = path.read_text(encoding="utf-8")
    assert 'custom string conceptghost:metadata' in text
    assert '\\"engine\\": \\"MoGe-3\\"' in text
    assert '\\"point_count\\": 2' in text
    assert '\\"intrinsics\\"' in text
