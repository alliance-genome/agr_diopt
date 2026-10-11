"""Resolve machine-specific locations without hard-coding them in scripts.

Order: environment variable, then the private API config
(~/.config/diopt-prototype/api-env.json), then a default.
"""

import json, os, pathlib

PRIVATE = pathlib.Path.home() / ".config/diopt-prototype"
REPO = pathlib.Path(__file__).resolve().parents[1]


def _private_config(private):
    try:
        return json.loads((pathlib.Path(private) / "api-env.json").read_text())
    except FileNotFoundError:
        return {}


def setting(name, default, environ=os.environ, private=PRIVATE):
    return environ.get(name) or _private_config(private).get(name) or default


def data_dir(environ=os.environ, private=PRIVATE):
    default = str(pathlib.Path.home() / "diopt-data")
    return pathlib.Path(setting("DIOPT_DATA_DIR", default, environ, private)).expanduser()


def api_binary(environ=os.environ, private=PRIVATE):
    default = str(REPO / "services/diopt-api/target/release/diopt-api")
    return pathlib.Path(setting("DIOPT_API_BINARY", default, environ, private)).expanduser()
