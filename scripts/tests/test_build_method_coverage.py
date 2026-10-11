import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location(
    "coverage",
    pathlib.Path(__file__).resolve().parents[1] / "build_method_coverage.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BuildTests(unittest.TestCase):
    def test_groups_sorts_case_insensitively_and_dedupes(self):
        rows = [
            "7227\t9606\tPanther",
            "7227\t9606\teggNOG",
            "7227\t9606\tCompara",
            "7227\t9606\tPanther",
            "9606\t7227\tUser_Submission",
        ]
        data = module.build(rows, "diopt-test-x", "2026-10-11T00:00:00Z")
        self.assertEqual(data["dataset_id"], "diopt-test-x")
        self.assertEqual(data["generated_at"], "2026-10-11T00:00:00Z")
        self.assertEqual(
            data["pairs"],
            {
                "7227:9606": ["Compara", "eggNOG", "Panther"],
                "9606:7227": ["User_Submission"],
            },
        )

    def test_rejects_malformed_rows(self):
        with self.assertRaises(ValueError):
            module.build(["7227\t9606"], "d", "t")


class SettingsTests(unittest.TestCase):
    def test_explicit_arguments_never_read_private_config(self):
        def fail():
            raise AssertionError("private config must not be read")

        dataset_id, output = module.resolve_settings("d", pathlib.Path("/tmp/x.json"), fail)
        self.assertEqual((dataset_id, output), ("d", pathlib.Path("/tmp/x.json")))

    def test_missing_arguments_fall_back_to_private_config(self):
        config = {"DIOPT_DATASET_ID": "d", "DIOPT_METHOD_COVERAGE": "/tmp/c.json"}
        dataset_id, output = module.resolve_settings(None, None, lambda: config)
        self.assertEqual((dataset_id, output), ("d", pathlib.Path("/tmp/c.json")))


if __name__ == "__main__":
    unittest.main()
