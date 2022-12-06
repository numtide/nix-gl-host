import unittest
import os

from nixglhost_wrapper import CacheDirContent, LibraryPath, ResolvedLib


class TestCacheSerializer(unittest.TestCase):
    def test_hostdso_json_golden_test(self):
        lp = LibraryPath(
            glx=[
                ResolvedLib(
                    "dummyglx.so",
                    "/lib",
                    "/lib/dummyglx.so",
                    "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9406",
                )
            ],
            cuda=[
                ResolvedLib(
                    "dummycuda.so",
                    "/lib",
                    "/lib/dummycuda.so",
                    "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9407",
                )
            ],
            generic=[
                ResolvedLib(
                    "dummygeneric.so",
                    "/lib",
                    "/lib/dummygeneric.so",
                    "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9408",
                )
            ],
            egl=[
                ResolvedLib(
                    "dummyegl.so",
                    "/lib",
                    "/lib/dummyegl.so",
                    "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9409",
                )
            ],
            path="/path/to/lib/dir",
        )
        cdc = CacheDirContent([lp])
        json = cdc.to_json()

        self.assertIsNotNone(json)
        golden_cdc = CacheDirContent.from_json(json)
        self.assertEqual(cdc, golden_cdc)
        self.assertEqual(cdc.to_json(), golden_cdc.to_json())

    def test_eq_commut_jsons(self):
        """Checks that object equality is not sensible to JSON keys commutations"""
        cwd = os.path.dirname(os.path.realpath(__file__))
        with open(
            os.path.join(cwd, "..", "tests", "fixtures", "json_permut", "1.json"),
            "r",
            encoding="utf8",
        ) as f:
            cdc_json = f.read()
        with open(
            os.path.join(cwd, "..", "tests", "fixtures", "json_permut", "2.json"),
            "r",
            encoding="utf8",
        ) as f:
            commut_cdc_json = f.read()
        with open(
            os.path.join(
                cwd, "..", "tests", "fixtures", "json_permut", "not-equal.json"
            ),
            "r",
            encoding="utf8",
        ) as f:
            wrong_cdc_json = f.read()
        cdc = CacheDirContent.from_json(cdc_json)
        commut_cdc = CacheDirContent.from_json(commut_cdc_json)
        wrong_cdc = CacheDirContent.from_json(wrong_cdc_json)
        self.assertEqual(cdc, commut_cdc)
        self.assertNotEqual(cdc, wrong_cdc)
        self.assertNotEqual(commut_cdc, wrong_cdc)


if __name__ == "__main__":
    unittest.main()
