import tempfile
import unittest
from pathlib import Path

import numpy as np


class FlightScaleTests(unittest.TestCase):
    def _api(self):
        try:
            from p10_lab.flight_scale import derive_flight_scale_from_primary_mesh
        except ImportError as error:
            self.fail(f"Gate 4.1 robust flight-scale module is missing: {error}")
        return derive_flight_scale_from_primary_mesh

    def test_uses_median_camera_depth_not_far_outlier_radius(self):
        derive = self._api()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mesh.npz"
            np.savez(
                path,
                vertices=np.array(
                    [[0.0, 0.0, -10.0], [1.0, 0.0, -11.0], [2.0, 0.0, -12.0], [999.0, 0.0, -999.0]],
                    dtype=np.float32,
                ),
                camera_depth=np.array([10.0, 11.0, 12.0, 999.0], dtype=np.float32),
            )

            scale, evidence = derive(path)

        self.assertAlmostEqual(scale.radius, 11.5, places=6)
        self.assertEqual(evidence.method, "PRIMARY_MESH_MEDIAN_CAMERA_DEPTH")
        self.assertGreater(evidence.max_depth, 900.0)
        self.assertLess(scale.radius, evidence.max_depth / 50.0)

    def test_rejects_missing_camera_depth(self):
        derive = self._api()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mesh.npz"
            np.savez(path, vertices=np.zeros((3, 3), dtype=np.float32))
            with self.assertRaises(ValueError):
                derive(path)

    def test_rejects_nonpositive_or_nonfinite_depths(self):
        derive = self._api()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mesh.npz"
            np.savez(
                path,
                vertices=np.zeros((4, 3), dtype=np.float32),
                camera_depth=np.array([0.0, -1.0, np.nan, np.inf], dtype=np.float32),
            )
            with self.assertRaises(ValueError):
                derive(path)


if __name__ == "__main__":
    unittest.main()
