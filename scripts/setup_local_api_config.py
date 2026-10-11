#!/usr/bin/env python3
"""Create the read-only database account and the private API configuration.

Run after start_local_database.py and after loading DIOPT tables into the `diopt`
database. Credentials stay in ~/.config/diopt-prototype/ and never enter argv or Git.
Without --dataset-id, only the account and grants are created (enough for the
synthetic fixture).
"""

import argparse, json, os, pathlib, re, subprocess, time

import diopt_paths

CONTAINER = "diopt-prototype-db"


def api_config(dataset_id, coverage, web_dir, password, data_dir, port="43100"):
    return {
        "DIOPT_DB_HOST": "127.0.0.1",
        "DIOPT_DB_PORT": "43306",
        "DIOPT_DB_USER": "diopt_reader",
        "DIOPT_DB_PASSWORD": password,
        "DIOPT_DB_NAME": "diopt",
        "DIOPT_LOCAL_DB": "true",
        "DIOPT_DATASET_ID": dataset_id,
        "DIOPT_PORT": port,
        "DIOPT_WEB_DIR": str(web_dir),
        "DIOPT_METHOD_COVERAGE": str(coverage),
        "DIOPT_DATA_DIR": str(data_dir),
    }


def grant_sql(password):
    # start_local_database.py generates URL-safe tokens; anything else is refused, never quoted.
    if not re.fullmatch(r"[A-Za-z0-9_-]+", password):
        raise ValueError("Reader password must be URL-safe characters only.")
    return (
        f"CREATE USER IF NOT EXISTS 'diopt_reader'@'%' IDENTIFIED BY '{password}';\n"
        f"ALTER USER 'diopt_reader'@'%' IDENTIFIED BY '{password}';\n"
        "GRANT SELECT ON diopt.* TO 'diopt_reader'@'%';\n"
        "GRANT SELECT ON diopt_fixture.* TO 'diopt_reader'@'%';\n"
    )


def write_config(path, config, replace):
    path = pathlib.Path(path)
    if path.exists() and not replace:
        raise SystemExit(f"{path} already exists; pass --replace to overwrite it.")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def wait_for_database(ping, attempts=60, pause=time.sleep):
    """First-time MariaDB init takes several seconds after `docker run`."""
    for attempt in range(attempts):
        if ping():
            return
        if attempt + 1 < attempts:
            pause(1)
    raise SystemExit("The database did not become ready; check `docker logs diopt-prototype-db`.")


def _ping():
    return subprocess.run(
        ["docker", "exec", CONTAINER, "mariadb-admin",
         "--defaults-extra-file=/run/diopt-secrets/root.cnf", "ping"],
        capture_output=True,
    ).returncode == 0


def main():
    data = diopt_paths.data_dir()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-id", help="label for the loaded data, e.g. diopt-YYYY-MM-DD")
    ap.add_argument("--coverage", type=pathlib.Path, default=data / "derived/method-coverage.json")
    ap.add_argument("--web-dir", type=pathlib.Path, default=diopt_paths.REPO / "web/dist")
    ap.add_argument("--replace", action="store_true", help="overwrite an existing api-env.json")
    args = ap.parse_args()
    secret = diopt_paths.PRIVATE / "reader-password"
    if not secret.exists():
        raise SystemExit(f"{secret} not found; run scripts/start_local_database.py first.")
    password = secret.read_text().strip()
    wait_for_database(_ping)
    subprocess.run(
        [
            "docker", "exec", "-i", CONTAINER, "mariadb",
            "--defaults-extra-file=/run/diopt-secrets/root.cnf",
        ],
        input=grant_sql(password),
        text=True,
        check=True,
    )
    print("Read-only account diopt_reader can SELECT from diopt and diopt_fixture.")
    if args.dataset_id:
        write_config(
            diopt_paths.PRIVATE / "api-env.json",
            api_config(args.dataset_id, args.coverage, args.web_dir, password, data),
            args.replace,
        )
        print(f"Wrote {diopt_paths.PRIVATE / 'api-env.json'}")


if __name__ == "__main__":
    main()
