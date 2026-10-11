#!/usr/bin/env python3
"""Precompute which prediction methods cover each species pair.

Run once per data refresh. The live per-pair query takes ~15 s on the production
Ortholog_Pair table (63.6M rows); this single scan takes under a minute.
"""

import argparse, datetime, json, os, pathlib, subprocess

QUERY = (
    "SELECT speciesid1, speciesid2, prediction_method FROM Ortholog_Pair "
    "WHERE prediction_method IS NOT NULL AND speciesid1 IS NOT NULL AND speciesid2 IS NOT NULL "
    "GROUP BY speciesid1, speciesid2, prediction_method"
)
PRIVATE = pathlib.Path.home() / ".config/diopt-prototype"


def build(rows, dataset_id, generated_at):
    pairs = {}
    for line in rows:
        parts = line.split("\t")
        if len(parts) != 3:
            raise ValueError(f"Unexpected coverage row: {line!r}")
        source, target, method = parts
        pairs.setdefault(f"{int(source)}:{int(target)}", set()).add(method)
    return {
        "dataset_id": dataset_id,
        "generated_at": generated_at,
        "pairs": {
            key: sorted(methods, key=str.lower) for key, methods in sorted(pairs.items())
        },
    }


def resolve_settings(dataset_id, output, load_config):
    """Fill missing settings from the private API config, reading it only when needed."""
    if dataset_id is not None and output is not None:
        return dataset_id, output
    config = load_config()
    return (
        dataset_id or config["DIOPT_DATASET_ID"],
        output or pathlib.Path(config["DIOPT_METHOD_COVERAGE"]),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--database", default="diopt")
    ap.add_argument("--dataset-id")
    ap.add_argument(
        "--output",
        type=pathlib.Path,
        help="defaults to DIOPT_METHOD_COVERAGE in the private API config",
    )
    args = ap.parse_args()
    dataset_id, args.output = resolve_settings(
        args.dataset_id,
        args.output,
        lambda: json.loads((PRIVATE / "api-env.json").read_text()),
    )
    rows = subprocess.check_output(
        [
            "docker", "exec", "diopt-prototype-db", "mariadb",
            "--defaults-extra-file=/run/diopt-secrets/reader.cnf",
            "-N", "-B", args.database, "-e", QUERY,
        ],
        text=True,
    ).splitlines()
    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    data = build(rows, dataset_id, generated_at)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(temporary, args.output)
    print(f"Wrote {len(data['pairs'])} species pairs from {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
