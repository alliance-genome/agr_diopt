import { useMemo } from "react";
import { Info } from "lucide-react";
import type { InputResult, Pair, ResultRow, SearchResponse } from "../types";
import { bestMatchLabel, methodColumns, scoreLabel, stableIdLabel, type SortKey } from "../format";
import { MethodCells, MethodHeader, MobileMethods } from "./MethodStrip";

const PAGE_SIZE = 25;

function BestFlag({ value, direction }: { value: string | null; direction: string }) {
  if (value === null)
    return (
      <span title="Not supplied">
        —<span className="sr-only"> {direction} best match not supplied</span>
      </span>
    );
  return (
    <span>
      <span className="sr-only">{direction} best match: </span>
      {bestMatchLabel(value)}
    </span>
  );
}

function InputIssues({ results, hasRows }: { results: InputResult[]; hasRows: boolean }) {
  const issues = results.filter((r) => r.status !== "mapped");
  if (!issues.length) return null;
  const count = (status: InputResult["status"]) => results.filter((r) => r.status === status).length;
  const extras: [InputResult["status"], string][] = [
    ["ambiguous", "ambiguous"],
    ["unmapped", "unmapped"],
    ["no_orthologs", "without orthologs"],
  ];
  return (
    <div className="input-issues">
      <p role="status">
        <strong>
          {count("mapped")} of {results.length} inputs {count("mapped") === 1 ? "has" : "have"} orthologs
        </strong>
        {extras.map(([status, text]) => (count(status) ? <span key={status}> · {count(status)} {text}</span> : null))}
      </p>
      <details className="issues" open={!hasRows}>
        <summary>
          <Info size={16} />
          {issues.length} {issues.length === 1 ? "identifier needs" : "identifiers need"} attention
        </summary>
        <ul>
          {issues.map((i) => (
            <li key={i.index}>
              <strong>{i.identifier}</strong>
              <span>
                {i.status === "unmapped"
                  ? "No identifier match in the input species. Check the spelling or identifier type."
                  : i.status === "no_orthologs"
                    ? "Gene mapped, but no orthologs were found for this species pair."
                    : `Ambiguous match: ${i.candidates.map((c) => `${c.symbol || c.gene_id} (${c.species_specific_id || c.gene_id})`).join(", ")}. Try a specific stable identifier.`}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}

export function ResultsTable(props: {
  response: SearchResponse;
  rows: ResultRow[];
  page: number;
  setPage: (updater: (p: number) => number) => void;
  sort: SortKey;
  setSort: (s: SortKey) => void;
  speciesName: (id: number) => string;
}) {
  const { response, rows, page, setPage, sort, setSort, speciesName } = props;
  const columns = useMemo(
    () => methodColumns(response.species_pair_methods, rows.map((r) => r.pair)),
    [response, rows],
  );
  const covered = useMemo(() => new Set(response.species_pair_methods), [response]);
  const visible = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const groups = visible.reduce<{ input: InputResult; rows: ResultRow[]; continued: boolean }[]>((acc, row) => {
    const last = acc[acc.length - 1];
    if (last?.input.index === row.input.index) last.rows.push(row);
    else
      acc.push({
        input: row.input,
        rows: [row],
        continued: page > 0 && rows[page * PAGE_SIZE - 1]?.input.index === row.input.index,
      });
    return acc;
  }, []);
  const strip = (p: Pair) => (
    <>
      <MethodCells pair={p} columns={columns} covered={covered} />
      <MobileMethods pair={p} columns={columns} covered={covered} />
    </>
  );
  return (
    <>
      <InputIssues results={response.results} hasRows={rows.length > 0} />
      {rows.length ? (
        <>
          <div className="table-toolbar">
            <label className="sort-label">
              Sort within gene
              <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
                <option value="source">Confidence, score</option>
                <option value="score">Score</option>
                <option value="methods">Supporting methods</option>
                <option value="symbol">Ortholog symbol</option>
              </select>
            </label>
          </div>
          <p className="table-hint">Scroll the table sideways to see confidence and methods.</p>
          <div className="table-scroll" role="region" aria-label="Ortholog comparison table" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">Ortholog</th>
                  <th scope="col" className="numeric">Score<span className="th-sub">of species-pair max</span></th>
                  <th scope="col">Best match<span className="th-sub">forward / reverse</span></th>
                  <th scope="col">Confidence</th>
                  <th scope="col">
                    Methods
                    <MethodHeader columns={columns} />
                  </th>
                </tr>
              </thead>
              {groups.map((group) => (
                <tbody key={`${group.input.index}-${group.rows[0].key}`}>
                  <tr className="input-group">
                    <th scope="rowgroup" colSpan={5}>
                      <div className="gene-context">
                        <strong>{group.input.candidates[0]?.symbol || group.rows[0].pair.input_gene_id}</strong>
                        <span>{speciesName(response.query.input_species)}</span>
                        {group.input.identifier !== group.input.candidates[0]?.symbol ? (
                          <span>Input: {group.input.identifier}</span>
                        ) : null}
                        <span>
                          {group.input.orthologs.length} orthologs{group.continued ? " · continued" : ""}
                        </span>
                      </div>
                    </th>
                  </tr>
                  {group.rows.map(({ key, pair: p }) => (
                    <tr key={key} className="result-row">
                      <td>
                        <strong>{p.output_symbol || p.output_gene_id}</strong>
                        <small>{stableIdLabel(p)}</small>
                      </td>
                      <td className="numeric">{scoreLabel(p.stored_score, response.max_score)}</td>
                      <td className="best-match">
                        <BestFlag value={p.best_forward} direction="Forward" />
                        <span aria-hidden="true"> / </span>
                        <BestFlag value={p.best_reverse} direction="Reverse" />
                      </td>
                      <td>
                        <span className={`confidence ${p.confidence || "unknown"}`}>{p.confidence || "Unknown"}</span>
                      </td>
                      <td>{strip(p)}</td>
                    </tr>
                  ))}
                </tbody>
              ))}
            </table>
          </div>
          <div className="pagination">
            <span>
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, rows.length)} of {rows.length} pairs ·{" "}
              {response.elapsed_ms.toLocaleString()} ms server time · Dataset <code>{response.dataset_id}</code>
            </span>
            <div>
              <button type="button" className="secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                Previous
              </button>
              <span>{page + 1} / {pages}</span>
              <button type="button" className="secondary" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)}>
                Next
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className="no-results">
          <h3>No ortholog pairs to display.</h3>
          <p>Review the identifier details above, or try another species pair.</p>
        </div>
      )}
    </>
  );
}
