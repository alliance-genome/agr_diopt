import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

scripts = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(scripts))  # the script imports diopt_paths
spec = importlib.util.spec_from_file_location("setup_cfg", scripts / "setup_local_api_config.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SetupTests(unittest.TestCase):
    def test_api_config_has_every_required_key(self):
        c = module.api_config("ds-1", pathlib.Path("/d/cov.json"), pathlib.Path("/w"), "pw", pathlib.Path("/d"))
        self.assertEqual(c["DIOPT_DATASET_ID"], "ds-1")
        self.assertEqual(c["DIOPT_METHOD_COVERAGE"], "/d/cov.json")
        self.assertEqual(c["DIOPT_WEB_DIR"], "/w")
        self.assertEqual(c["DIOPT_DB_USER"], "diopt_reader")
        self.assertEqual(c["DIOPT_DB_PASSWORD"], "pw")
        self.assertEqual(c["DIOPT_DB_NAME"], "diopt")
        self.assertEqual(c["DIOPT_DATA_DIR"], "/d")
        self.assertEqual(c["DIOPT_PORT"], "43100")

    def test_grant_sql_is_select_only_and_rejects_unsafe_passwords(self):
        sql = module.grant_sql("abc_DEF-123")
        self.assertIn("GRANT SELECT ON diopt.* TO 'diopt_reader'@'%'", sql)
        self.assertIn("GRANT SELECT ON diopt_fixture.* TO 'diopt_reader'@'%'", sql)
        self.assertNotIn("ALL PRIVILEGES", sql)
        with self.assertRaises(ValueError):
            module.grant_sql("x'; DROP DATABASE diopt; --")

    def test_refuses_to_overwrite_existing_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "api-env.json"
            path.write_text('{"keep": true}')
            with self.assertRaises(SystemExit):
                module.write_config(path, {"new": 1}, replace=False)
            self.assertEqual(json.loads(path.read_text()), {"keep": True})
            module.write_config(path, {"new": 1}, replace=True)
            self.assertEqual(json.loads(path.read_text()), {"new": 1})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_wait_for_database_retries_then_gives_up(self):
        answers = iter([False, False, True])
        pauses = []
        module.wait_for_database(lambda: next(answers), attempts=5, pause=pauses.append)
        self.assertEqual(len(pauses), 2)
        with self.assertRaises(SystemExit):
            module.wait_for_database(lambda: False, attempts=3, pause=lambda _: None)


if __name__ == "__main__":
    unittest.main()
