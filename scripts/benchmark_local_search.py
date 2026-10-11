#!/usr/bin/env python3
"""Measure local Rust API requests using a fixed, documented real-data corpus."""

import argparse, concurrent.futures, json, pathlib, statistics, time, urllib.request, urllib.error

ap = argparse.ArgumentParser()
ap.add_argument("--corpus", type=pathlib.Path, required=True)
ap.add_argument("--output", type=pathlib.Path, required=True)
ap.add_argument("--build-label", default="unrecorded")
args = ap.parse_args()
corpus = json.loads(args.corpus.read_text())
runs = []


def run(case):
    body = json.dumps(case).encode()
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(
                "http://127.0.0.1:43100/v1/orthologs/search",
                data=body,
                headers={"Content-Type": "application/json"},
            ),
            timeout=15,
        ) as r:
            data = json.load(r)
            return {
                "status": r.status,
                "wall_ms": round((time.perf_counter() - start) * 1000, 2),
                "server_ms": data["elapsed_ms"],
                "queries": data["database_queries"],
                "rows": sum(len(x["orthologs"]) for x in data["results"]),
                "dataset_id": data["dataset_id"],
            }
    except urllib.error.HTTPError as e:
        return {
            "status": e.code,
            "wall_ms": round((time.perf_counter() - start) * 1000, 2),
            "error": json.load(e),
        }


for case in corpus:
    cold = run(case)
    runs.append(
        {
            "label": case["identifiers"][:1],
            "inputs": len(case["identifiers"]),
            "phase": "first_observed_not_controlled_cold",
            "runs": [cold],
        }
    )
    samples = [run(case) for _ in range(10)]
    runs.append(
        {"inputs": len(case["identifiers"]), "phase": "warm_serial", "runs": samples}
    )
# Bounded concurrency experiment on the largest supplied case.
for concurrency in [5, 20]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        samples = list(pool.map(run, [corpus[-1]] * 20))
    runs.append(
        {
            "inputs": len(corpus[-1]["identifiers"]),
            "phase": "warm_concurrent",
            "concurrency": concurrency,
            "runs": samples,
        }
    )
for group in runs:
    times = sorted(x["wall_ms"] for x in group["runs"])
    group["p50_ms"] = statistics.median(times)
    group["p95_ms"] = times[max(0, __import__("math").ceil(len(times) * 0.95) - 1)]
args.output.write_text(
    json.dumps(
        {
            "build": args.build_label,
            "note": "No Python baseline or controlled cold-cache comparison. Concurrent p95 from 20 samples only.",
            "groups": runs,
        },
        indent=2,
    )
    + "\n"
)
print("Benchmark saved:", args.output)
