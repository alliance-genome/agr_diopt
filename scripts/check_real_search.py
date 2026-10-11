#!/usr/bin/env python3
"""Compare returned fields to source rows, and prepare a fixed real-data benchmark corpus."""

import collections, json, pathlib, subprocess, urllib.request

import diopt_paths

root = diopt_paths.data_dir()
cmd = [
    "docker",
    "exec",
    "diopt-prototype-db",
    "mariadb",
    "--defaults-extra-file=/run/diopt-secrets/reader.cnf",
    "-N",
    "-B",
    "diopt",
]


def sql(query):
    return subprocess.check_output(cmd + ["-e", query], text=True).splitlines()


def search(query):
    with urllib.request.urlopen(
        urllib.request.Request(
            "http://127.0.0.1:43100/v1/orthologs/search",
            data=json.dumps(query).encode(),
            headers={"Content-Type": "application/json"},
        ),
        timeout=15,
    ) as r:
        return json.load(r)


cases = []
verified = []
for source, target in [(7227, 9606), (9606, 7227)]:
    symbols = sql(
        f"SELECT g.symbol FROM Gene_Information g WHERE g.speciesid={source} AND g.symbol IS NOT NULL AND EXISTS (SELECT 1 FROM Ortholog_Pair_Best b WHERE b.species1={source} AND b.geneid1=g.geneid AND b.species2={target}) ORDER BY g.geneid LIMIT 100;"
    )
    if not symbols:
        raise SystemExit("No examples for requested pair")
    for n in [1, 10, 100]:
        cases.append(
            {
                "input_species": source,
                "output_species": target,
                "identifiers": symbols[:n],
                "mapping_mode": "unambiguous",
                "result_filter": "none",
            }
        )
    extra_symbols = ["rut", "ey"] if source == 7227 else ["ADCY1", "PAX6"]
    queries = [cases[-3]] + [
        dict(cases[-3], identifiers=[symbol]) for symbol in extra_symbols
    ]
    for query in queries:
        response = search(query)
        item = response["results"][0]
        if item["status"] != "mapped":
            raise SystemExit(
                "First real example did not map uniquely; choose another verified example"
            )
        gene = int(item["candidates"][0]["gene_id"])
        expected = sql(
            f"SELECT geneid2,IFNULL(score,'NULL'),IFNULL(best_score,'NULL'),IFNULL(best_score_rev,'NULL'),IFNULL(confidence,'NULL') FROM Ortholog_Pair_Best WHERE species1={source} AND geneid1={gene} AND species2={target} ORDER BY geneid2;"
        )
        expected_order = sql(
            f"SELECT geneid2 FROM Ortholog_Pair_Best WHERE species1={source} AND geneid1={gene} AND species2={target} ORDER BY CASE confidence WHEN 'high' THEN 0 WHEN 'moderate' THEN 1 WHEN 'low' THEN 2 ELSE 3 END, score DESC, geneid2;"
        )
        assert [row["output_gene_id"] for row in item["orthologs"]] == expected_order
        actual = []
        for row in sorted(item["orthologs"], key=lambda r: int(r["output_gene_id"])):
            actual.append(
                "\t".join(
                    "NULL" if x is None else str(x)
                    for x in [
                        row["output_gene_id"],
                        row["stored_score"],
                        row["best_forward"],
                        row["best_reverse"],
                        row["confidence"],
                    ]
                )
            )
            output = int(row["output_gene_id"])
            evidence = sql(
                f"SELECT prediction_method FROM Ortholog_Pair WHERE speciesid1={source} AND geneid1={gene} AND speciesid2={target} AND geneid2={output};"
            )
            counts = collections.Counter(
                None if name == "NULL" else name for name in evidence
            )
            assert counts == {m["name"]: m["rows"] for m in row["methods"]}
            assert len(evidence) == row["evidence_row_count"]
        assert actual == expected
        max_rows = sql(
            f"SELECT max_score FROM Ortholog_Max_Score WHERE species1={source} AND species2={target};"
        )
        assert response["max_score"] == (
            int(max_rows[0]) if max_rows and max_rows[0] != "NULL" else None
        )
        assert response["contract_version"] == "prototype-3"
        assert "weighted_score" not in json.dumps(response)
        covered = set(response["species_pair_methods"])
        for row in item["orthologs"]:
            assert {m["name"] for m in row["methods"] if m["name"]} <= covered, row[
                "output_gene_id"
            ]
        verified.append(
            {
                "query": query,
                "dataset_id": response["dataset_id"],
                "pairs": len(actual),
                "field_and_evidence_comparison": "passed",
            }
        )
(root / "benchmarks").mkdir(parents=True, exist_ok=True)
(root / "benchmarks/real-corpus.json").write_text(json.dumps(cases, indent=2) + "\n")
(root / "benchmarks/source-comparison.json").write_text(
    json.dumps(verified, indent=2) + "\n"
)
print("Real source-row comparisons passed for both species directions. Corpus saved.")
