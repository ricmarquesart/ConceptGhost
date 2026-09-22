import unittest


class ReconstructionAssetManifestTests(unittest.TestCase):
    def test_colmap_cuda_asset_is_frozen(self):
        from p10_lab.reconstruction_assets import COLMAP_WINDOWS_CUDA
        self.assertEqual(COLMAP_WINDOWS_CUDA.version, "4.2.0")
        self.assertEqual(COLMAP_WINDOWS_CUDA.archive_name, "colmap-x64-windows-cuda.zip")
        self.assertEqual(COLMAP_WINDOWS_CUDA.archive_bytes, 380970811)
        self.assertEqual(
            COLMAP_WINDOWS_CUDA.sha256,
            "991e0bae403a496fcc4de0c1f1f428619bf12f8000978f77bc6799d9bfeac23e",
        )
        self.assertTrue(COLMAP_WINDOWS_CUDA.cuda_required)

    def test_manifest_estimates_incremental_disk(self):
        from p10_lab.reconstruction_assets import manifest
        payload=manifest()
        self.assertEqual(payload["colmap"]["version"],"4.2.0")
        self.assertGreater(payload["colmap"]["estimated_installed_gb"],0.5)
        self.assertLess(payload["colmap"]["estimated_installed_gb"],2.5)


if __name__=="__main__":
    unittest.main()
