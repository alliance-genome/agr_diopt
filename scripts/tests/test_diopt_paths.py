import importlib.util
import json
import pathlib
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "diopt_paths",
    pathlib.Path(__file__).resolve().parents[1] / "diopt_paths.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.private = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_environment_wins_over_private_config(self):
        (self.private / "api-env.json").write_text(json.dumps({"DIOPT_DATA_DIR": "/from/config"}))
        path = module.data_dir({"DIOPT_DATA_DIR": "/from/env"}, self.private)
        self.assertEqual(path, pathlib.Path("/from/env"))

    def test_private_config_used_when_environment_unset(self):
        (self.private / "api-env.json").write_text(json.dumps({"DIOPT_API_BINARY": "/from/config/api"}))
        self.assertEqual(module.api_binary({}, self.private), pathlib.Path("/from/config/api"))

    def test_default_without_env_or_config(self):
        self.assertEqual(module.data_dir({}, self.private), pathlib.Path.home() / "diopt-data")
        self.assertEqual(
            module.api_binary({}, self.private),
            module.REPO / "services/diopt-api/target/release/diopt-api",
        )


if __name__ == "__main__":
    unittest.main()
