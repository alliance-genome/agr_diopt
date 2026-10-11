import type { ResultRow, SearchResponse } from "./types";
export function download(name: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function cell(value: unknown) {
  let s = value == null ? "" : String(value);
  s = s.replace(/[\t\r\n]/g, " ");
  if (/^[\s]*[=+@-]/.test(s)) s = "'" + s; // Protect spreadsheet users; canonical JSON stays unchanged.
  return s;
}
export function exportTsv(rows: ResultRow[], response: SearchResponse) {
  const headers = [
    "input_identifier",
    "mapping",
    "input_species",
    "input_gene_id",
    "output_species",
    "output_gene_id",
    "output_symbol",
    "stored_score",
    "confidence",
    "best_forward",
    "best_reverse",
    "unique_methods",
    "evidence_rows",
    "methods",
    "dataset_id",
  ];
  const lines = rows.map(({ input, pair: p }) =>
    [
      input.identifier,
      input.candidates[0]?.provenance ?? input.candidates[0]?.identifier_type ?? null,
      response.query.input_species,
      p.input_gene_id,
      response.query.output_species,
      p.output_gene_id,
      p.output_symbol,
      p.stored_score,
      p.confidence,
      p.best_forward,
      p.best_reverse,
      p.methods.filter((m) => m.name !== null).length,
      p.evidence_row_count,
      p.methods.map((m) => m.name ?? "Unknown method").join("; "),
      response.dataset_id,
    ]
      .map(cell)
      .join("\t"),
  );
  download(
    "diopt-results.tsv",
    [headers.join("\t"), ...lines].join("\n") + "\n",
    "text/tab-separated-values;charset=utf-8",
  );
}
