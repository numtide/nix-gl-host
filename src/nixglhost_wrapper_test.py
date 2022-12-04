import unittest

from nixglhost_wrapper import HostDSOs, ResolvedLib


class TestCacheSerializer(unittest.TestCase):
    def hostdso_json_golden_test(self):
        hds = HostDSOs(
            glx={
                "dummyglx.so": ResolvedLib(
                    "dummyglx.so",
                    "/lib/dummyglx.so",
                    "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9406",
                )
            },
            cuda={
                "dummycuda.so": ResolvedLib(
                    "dummycuda.so",
                    "/lib/dummycuda.so",
                    "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9407",
                )
            },
            generic={
                "dummygeneric.so": ResolvedLib(
                    "dummygeneric.so",
                    "/lib/dummygeneric.so",
                    "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9408",
                )
            },
        )
        json_hds = hds.to_json()
        self.assertIsNotNone(json_hds)
        golden_hds = HostDSOs.from_json(json_hds)
        self.assertEqual(hds, golden_hds)
        self.assertEqual(hds.to_json(), golden_hds.to_json())

    def test_eq_commut_jsons(self):
        """Checks that object equality is not sensible to JSON keys commutations"""
        hds_json = '{"version": 1, "glx": {"dummyglx.so": {"name": "dummyglx.so", "fullpath": "/lib/dummyglx.so", "sha256": "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9406"}}, "cuda": {"dummycuda.so": {"name": "dummycuda.so", "fullpath": "/lib/dummycuda.so", "sha256": "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9407"}, "dummycuda2.so": {"name": "dummycuda2.so", "fullpath": "/lib/dummycuda2.so", "sha256": "131edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9407"}}, "generic": {"dummygeneric.so": {"name": "dummygeneric.so", "fullpath": "/lib/dummygeneric.so", "sha256": "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9408"}}}'
        commut_hds_json = '{"version": 1, "glx": {"dummyglx.so": {"name": "dummyglx.so", "fullpath": "/lib/dummyglx.so", "sha256": "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9406"}}, "cuda": {"dummycuda2.so": {"name": "dummycuda2.so", "fullpath": "/lib/dummycuda2.so", "sha256": "131edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9407"}, "dummycuda.so": {"name": "dummycuda.so", "fullpath": "/lib/dummycuda.so", "sha256": "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9407"}}, "generic": {"dummygeneric.so": {"name": "dummygeneric.so", "fullpath": "/lib/dummygeneric.so", "sha256": "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9408"}}}'
        hds = HostDSOs.from_json(hds_json)
        commut_hds = HostDSOs.from_json(commut_hds_json)
        self.assertEqual(hds, commut_hds)
        self.assertEqual(hds.to_json(), commut_hds.to_json())


if __name__ == "__main__":
    unittest.main()
