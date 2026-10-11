import type { Pair, ResultRow } from "./types";

export type SortKey = "source" | "score" | "methods" | "symbol";
export type MethodState = "match" | "no match" | "coverage unknown";

export const parseIdentifiers = (text: string) =>
  text
    .split(/[,\t\n\r]+/)
    .map((t) => t.trim())
    .filter(Boolean);

// Same ordering as the API and build_method_coverage.py: lowercase code-point order.
const byLowercase = (a: string, b: string) => {
  const x = a.toLowerCase(),
    y = b.toLowerCase();
  return x < y ? -1 : x > y ? 1 : a < b ? -1 : a > b ? 1 : 0;
};

export function methodColumns(pairMethods: string[], pairs: Pair[]): string[] {
  const names = new Set(pairMethods);
  for (const p of pairs) for (const m of p.methods) if (m.name) names.add(m.name);
  return [...names].sort(byLowercase);
}

export function methodState(name: string, pair: Pair, covered: Set<string>): MethodState {
  if (pair.methods.some((m) => m.name === name)) return "match";
  return covered.has(name) ? "no match" : "coverage unknown";
}

export const matchedCount = (pair: Pair) =>
  new Set(pair.methods.map((m) => m.name).filter(Boolean)).size;

// Summarizes the same columns the strip renders, so the label always agrees with the squares.
export function methodsLabel(pair: Pair, columns: string[], covered: Set<string>): string {
  const n = matchedCount(pair);
  if (!covered.size) return `${n} ${n === 1 ? "method" : "methods"}`;
  return `${n}/${columns.length} methods`;
}

export function scoreLabel(score: number | null, max: number | null): string {
  if (score == null) return "—";
  return max == null ? String(score) : `${score}/${max}`;
}

export function bestMatchLabel(value: string | null): string {
  if (value == null) return "—";
  return value === "Yes_Adjusted" ? "Yes (adjusted)" : value;
}

export function stableIdLabel(p: Pair): string {
  const id = p.output_species_specific_id,
    type = p.output_species_specific_id_type;
  if (!id) return `Gene ID: ${p.output_gene_id}`;
  if (type && id.toLowerCase().startsWith(`${type.toLowerCase()}:`)) return id;
  return `${type || "Identifier"}:${id}`;
}

export function summarizeIdentifiers(ids: string[], shown = 3): string {
  if (ids.length <= shown) return ids.join(", ");
  return `${ids.slice(0, shown).join(", ")} +${ids.length - shown} more`;
}

export function sortRows(rows: ResultRow[], sort: SortKey): ResultRow[] {
  if (sort === "source") return rows;
  return [...rows].sort(
    (a, b) =>
      a.input.index - b.input.index ||
      (sort === "score"
        ? (b.pair.stored_score ?? -1) - (a.pair.stored_score ?? -1)
        : sort === "methods"
          ? matchedCount(b.pair) - matchedCount(a.pair)
          : (a.pair.output_symbol ?? a.pair.output_gene_id).localeCompare(
              b.pair.output_symbol ?? b.pair.output_gene_id,
            )),
  );
}

export function datasetNote(datasetId: string): string {
  if (datasetId.startsWith("synthetic-"))
    return "Synthetic test data only. These are demonstration records, not biological results.";
  return `DIOPT ortholog predictions supplied by DRSC. Dataset ${datasetId}.`;
}
