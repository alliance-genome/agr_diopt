#!/usr/bin/env python3
"""Start the isolated prototype MariaDB; credentials never enter argv or Git."""

import os, pathlib, secrets, subprocess, json

import diopt_paths

os.umask(0o077)
private = pathlib.Path.home() / ".config/diopt-prototype"
private.mkdir(parents=True, exist_ok=True, mode=0o700)
root = diopt_paths.data_dir()
data = root / "databases/search-v1"
data.mkdir(parents=True, exist_ok=True)
password = private / "root-password"
if not password.exists():
    password.write_text(secrets.token_urlsafe(36))
cnf = private / "root.cnf"
if not cnf.exists():
    cnf.write_text(
        "[client]\nuser=root\npassword=" + password.read_text().strip() + "\n"
    )
reader = private / "reader-password"
if not reader.exists():
    reader.write_text(secrets.token_urlsafe(36))
reader_cnf = private / "reader.cnf"
if not reader_cnf.exists():
    reader_cnf.write_text(
        "[client]\nuser=diopt_reader\npassword=" + reader.read_text().strip() + "\n"
    )
name = "diopt-prototype-db"
image = (
    "mariadb@sha256:70cc072b29b4a89ae07abb2d4da2c64678a7f2dfe092751bb51c87d67dc1338b"
)
exists = (
    subprocess.run(["docker", "inspect", name], capture_output=True).returncode == 0
)
if exists:
    raise SystemExit("Container already exists; inspect it rather than replacing it.")
subprocess.run(
    [
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "--restart",
        "unless-stopped",
        "--memory",
        "8g",
        "--memory-swap",
        "8g",
        "--cpus",
        "4",
        "-p",
        "127.0.0.1:43306:3306",
        "-v",
        str(data) + ":/var/lib/mysql",
        "-v",
        str(private) + ":/run/diopt-secrets:ro",
        "-e",
        "MARIADB_ROOT_PASSWORD_FILE=/run/diopt-secrets/root-password",
        "-e",
        "MARIADB_DATABASE=diopt",
        image,
        "--innodb-buffer-pool-size=6G",
        "--max-allowed-packet=256M",
    ],
    check=True,
    stdout=subprocess.DEVNULL,
)
(root / "manifests").mkdir(parents=True, exist_ok=True)
(root / "manifests/database.json").write_text(
    json.dumps(
        {
            "container": name,
            "image": image,
            "bind": "127.0.0.1:43306",
            "data_directory": str(data),
        },
        indent=2,
    )
    + "\n"
)
print("Started isolated MariaDB on 127.0.0.1:43306")
