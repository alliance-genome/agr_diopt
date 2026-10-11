import { test } from "node:test";
import assert from "node:assert/strict";
import {
  bestMatchLabel,
  datasetNote,
  matchedCount,
  methodColumns,
  methodState,
  methodsLabel,
  parseIdentifiers,
  scoreLabel,
  sortRows,
  stableIdLabel,
  summarizeIdentifiers,
} from "../../src/format.ts";
import type { Pair, ResultRow } from "../../src/types.ts";

const pair = (over: Partial<Pair> = {}): Pair => ({
  input_gene_id: "1",
  output_gene_id: "2",
  output_symbol: "B",
  output_species_specific_id: null,
  output_species_specific_id_type: null,
  stored_score: 3,
  best_forward: "Yes",
  best_reverse: "No",
  confidence: "high",
  methods: [{ name: "Panther", rows: 1 }, { name: null, rows: 1 }],
  evidence_row_count: 2,
  ...over,
});

test("parseIdentifiers splits on newlines, commas, and tabs", () => {
  assert.deepEqual(parseIdentifiers(" rut,\ney\tCG3038\n\n"), ["rut", "ey", "CG3038"]);
});

test("methodColumns unions coverage with matched names, case-insensitive order", () => {
  const cols = methodColumns(["Panther", "eggNOG"], [pair({ methods: [{ name: "Stale", rows: 1 }] })]);
  assert.deepEqual(cols, ["eggNOG", "Panther", "Stale"]);
});

test("methodState never reports 'no match' for methods outside coverage", () => {
  const p = pair();
  assert.equal(methodState("Panther", p, new Set(["Panther", "OMA"])), "match");
  assert.equal(methodState("OMA", p, new Set(["Panther", "OMA"])), "no match");
  assert.equal(methodState("OMA", p, new Set()), "coverage unknown");
});

test("matchedCount ignores unnamed and duplicate methods", () => {
  assert.equal(matchedCount(pair({ methods: [{ name: "A", rows: 2 }, { name: "A", rows: 1 }, { name: null, rows: 1 }] })), 1);
});

test("methodsLabel agrees with the squares it summarizes", () => {
  assert.equal(methodsLabel(pair(), ["OMA", "Panther"], new Set(["Panther", "OMA"])), "1/2 methods");
  // Stale coverage: "Stale" matched but isn't covered. Its column still renders as a match, so it counts.
  const stale = pair({ methods: [{ name: "Stale", rows: 1 }, { name: "Panther", rows: 1 }] });
  assert.equal(methodsLabel(stale, ["Panther", "Stale"], new Set(["Panther"])), "2/2 methods");
  assert.equal(methodsLabel(pair(), ["Panther"], new Set()), "1 method");
});

test("scoreLabel handles missing score and missing max", () => {
  assert.equal(scoreLabel(11, 13), "11/13");
  assert.equal(scoreLabel(11, null), "11");
  assert.equal(scoreLabel(null, 13), "—");
  assert.equal(scoreLabel(0, 13), "0/13");
  // An older API omits max_score entirely; never render "undefined".
  assert.equal(scoreLabel(11, undefined as unknown as null), "11");
});

test("bestMatchLabel maps known values and keeps others verbatim", () => {
  assert.equal(bestMatchLabel("Yes"), "Yes");
  assert.equal(bestMatchLabel("Yes_Adjusted"), "Yes (adjusted)");
  assert.equal(bestMatchLabel("Maybe"), "Maybe");
  assert.equal(bestMatchLabel(null), "—");
});

test("stableIdLabel avoids doubling the prefix", () => {
  assert.equal(stableIdLabel(pair({ output_species_specific_id: "HGNC:232", output_species_specific_id_type: "HGNC" })), "HGNC:232");
  assert.equal(stableIdLabel(pair({ output_species_specific_id: "232", output_species_specific_id_type: "HGNC" })), "HGNC:232");
  assert.equal(stableIdLabel(pair()), "Gene ID: 2");
});

test("summarizeIdentifiers truncates after three", () => {
  assert.equal(summarizeIdentifiers(["a", "b"]), "a, b");
  assert.equal(summarizeIdentifiers(Array.from({ length: 100 }, (_, i) => `g${i}`)), "g0, g1, g2 +97 more");
});

test("sortRows keeps input order first, then sorts within each input", () => {
  const input = (index: number) => ({ index, identifier: String(index), status: "mapped" as const, candidates: [], orthologs: [] });
  const rows: ResultRow[] = [
    { key: "a", input: input(1), pair: pair({ stored_score: 1, output_symbol: "Z" }) },
    { key: "b", input: input(0), pair: pair({ stored_score: 2, output_symbol: "Y" }) },
    { key: "c", input: input(1), pair: pair({ stored_score: 5, output_symbol: "A" }) },
  ];
  assert.deepEqual(sortRows(rows, "source").map((r) => r.key), ["a", "b", "c"]);
  assert.deepEqual(sortRows(rows, "score").map((r) => r.key), ["b", "c", "a"]);
  assert.deepEqual(sortRows(rows, "symbol").map((r) => r.key), ["b", "c", "a"]);
});

test("datasetNote is neutral and independent of private dataset-ID conventions", () => {
  assert.equal(
    datasetNote("synthetic-fixture-not-biological-results"),
    "Synthetic test data only. These are demonstration records, not biological results.",
  );
  for (const id of ["drsc-2026-09-28-b3e3", "diopt-2026-09-28"]) {
    const note = datasetNote(id);
    assert.equal(note, `DIOPT ortholog predictions supplied by DRSC. Dataset ${id}.`);
    assert.doesNotMatch(note, /hand.?off|pending|September/i);
  }
});
