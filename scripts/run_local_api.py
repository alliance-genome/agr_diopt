#!/usr/bin/env python3
"""Launch the local API without putting database credentials on the command line."""

import argparse, json, os, pathlib

import diopt_paths

ap = argparse.ArgumentParser()
ap.add_argument("--fixture", action="store_true")
ap.add_argument(
    "--binary",
    type=pathlib.Path,
    default=None,
    help="defaults to DIOPT_API_BINARY (environment or private config), else cargo's release build",
)
args = ap.parse_args()
private = pathlib.Path.home() / ".config/diopt-prototype"
if args.fixture:
    config = {
        "DIOPT_DB_HOST": "127.0.0.1",
        "DIOPT_DB_PORT": "43306",
        "DIOPT_DB_USER": "diopt_reader",
        "DIOPT_DB_PASSWORD": (private / "reader-password").read_text().strip(),
        "DIOPT_DB_NAME": "diopt_fixture",
        "DIOPT_LOCAL_DB": "true",
        "DIOPT_DATASET_ID": "synthetic-fixture-not-biological-results",
        "DIOPT_WEB_DIR": os.environ.get(
            "DIOPT_WEB_DIR", str(pathlib.Path(__file__).resolve().parents[1] / "web/dist")
        ),
        "DIOPT_METHOD_COVERAGE": str(
            pathlib.Path(__file__).resolve().parents[1]
            / "services/diopt-api/tests/fixtures/method-coverage.json"
        ),
    }
else:
    config = json.loads((private / "api-env.json").read_text())
binary = args.binary or diopt_paths.api_binary()
os.execve(binary, [str(binary)], dict(os.environ, **config))
