import json
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None


class MoGeDiagnosticsTests(unittest.TestCase):
    def test_control_defaults_and_profile_tap_are_diagnostic_only(self):
        from p10_lab.moge_diagnostics import (
            ConceptGhostMoGeDiagnosticsControl,
            ConceptGhostMoGeDiagnosticProfileTap,
        )
        control=ConceptGhostMoGeDiagnosticsControl()
        enabled,save_raw,render_3d,extras,_=control.configure(False,True,True,True)
        self.assertFalse(enabled)
        self.assertTrue(save_raw)
        base={"selected_profile":"High Fidelity Split Clean","diagnostic_return_per_step":False,"model":"x"}
        tapped,report=ConceptGhostMoGeDiagnosticProfileTap().apply(base,True)
        self.assertFalse(base["diagnostic_return_per_step"])
        self.assertTrue(tapped["diagnostic_return_per_step"])
        self.assertEqual(tapped["selected_profile"],base["selected_profile"])
        self.assertIn('"official_geometry_impact": false',report.lower())

    def test_disabled_mode_writes_nothing(self):
        if np is None:
            self.skipTest("NumPy unavailable in dependency-light CI lane")
        from p10_lab.moge_diagnostics import ConceptGhostMoGeDepthDiagnostics
        with tempfile.TemporaryDirectory() as tmp:
            node=ConceptGhostMoGeDepthDiagnostics()
            result=node.run(
                {},
                np.zeros((1,8,8,3),dtype=np.float32),
                "street",
                tmp,
                False,True,True,True,
                "",
            )
            self.assertEqual(result["result"][1],"")
            self.assertFalse((Path(tmp)/"_diagnostics").exists())
            report=json.loads(result["result"][3])
            self.assertEqual(report["status"],"DISABLED")
            self.assertFalse(report["geometry_impact"])

    def test_enabled_mode_exports_native_and_derived_depth_evidence(self):
        if np is None:
            self.skipTest("NumPy unavailable in dependency-light CI lane")
        from p10_lab.moge_diagnostics import ConceptGhostMoGeDepthDiagnostics
        h,w=18,24
        yy,xx=np.mgrid[:h,:w]
        depth=(2.0+xx*0.2+yy*0.05).astype(np.float32)
        mask=np.ones((h,w),dtype=bool)
        mask[:2,:3]=False
        normal=np.dstack([
            np.zeros((h,w),dtype=np.float32),
            np.zeros((h,w),dtype=np.float32),
            np.ones((h,w),dtype=np.float32),
        ])
        points=np.dstack([
            (xx-w/2)*0.05,
            (yy-h/2)*0.05,
            depth,
        ]).astype(np.float32)
        image=np.zeros((1,h,w,3),dtype=np.float32)
        image[0,...,0]=xx/max(1,w-1)
        image[0,...,1]=yy/max(1,h-1)
        geometry={
            "depth_metric_native":depth,
            "mask_native":mask,
            "normal_native":normal,
            "points_metric_native":points,
            "intrinsics_native":np.array([[500,0,w/2],[0,500,h/2],[0,0,1]],dtype=np.float32),
            "depth_per_step_0":depth*1.03,
            "conceptghost_model":"test-model",
            "conceptghost_geometry_profile":"test-profile",
        }
        with tempfile.TemporaryDirectory() as tmp:
            result=ConceptGhostMoGeDepthDiagnostics().run(
                geometry,image,"street",tmp,True,True,True,True,"{}"
            )
            diag=Path(result["result"][1])
            manifest=Path(result["result"][2])
            self.assertTrue(diag.is_dir())
            self.assertTrue(manifest.is_file())
            payload=json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"],"PASS")
            self.assertFalse(payload["geometry_impact"])
            self.assertTrue((diag/"01_original_input.png").is_file())
            self.assertTrue((diag/"02_depth_grayscale.png").is_file())
            self.assertTrue((diag/"03_depth_heatmap.png").is_file())
            self.assertTrue((diag/"04_inverse_depth.png").is_file())
            self.assertTrue((diag/"05_depth_bands.png").is_file())
            self.assertTrue((diag/"06_depth_contours.png").is_file())
            self.assertTrue((diag/"07_depth_discontinuities.png").is_file())
            self.assertTrue((diag/"08_normals.png").is_file())
            self.assertTrue((diag/"09_mask.png").is_file())
            self.assertTrue((diag/"11_pointcloud_preview.png").is_file())
            self.assertTrue((diag/"12_pointcloud_sampled.ply").is_file())
            self.assertTrue((diag/"00_moge_depth_diagnostics_mosaic.png").is_file())
            self.assertTrue((diag/"raw/depth_native.npy").is_file())
            self.assertTrue((diag/"raw/points_native.npy").is_file())
            self.assertTrue((diag/"refinement_steps/depth_per_step_0.npy").is_file())
            self.assertIn("native_vs_derived",payload)
            self.assertEqual(
                payload["native_vs_derived"]["primary_mesh_preview"],
                "Not duplicated here. Official P9 PrimaryMesh/Primary Master remains the downstream authoritative derived mesh preview.",
            )


if __name__=="__main__":
    unittest.main()
