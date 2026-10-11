import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/lato/400.css";
import "@fontsource/lato/700.css";
import "./style.css";
import type { Species, SearchResponse, ResultRow } from "./types";
import { download, exportTsv } from "./export";
import { parseIdentifiers, sortRows, type SortKey } from "./format";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { SearchCard } from "./components/SearchCard";
import { SummaryBar } from "./components/SummaryBar";
import { ResultsGuide } from "./components/ResultsGuide";
import { ResultsTable } from "./components/ResultsTable";

function App() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || "light");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("diopt-theme", theme); } catch { /* Storage may be disabled. */ }
  }, [theme]);
  const [guideOpen, setGuideOpen] = useState(false);
  const [datasetId, setDatasetId] = useState("");
  const [species, setSpecies] = useState<Species[]>([]),
    [metadataError, setMetadataError] = useState(""),
    [metadataAttempt, setMetadataAttempt] = useState(0);
  const [inputSpecies, setInputSpecies] = useState(7227),
    [outputSpecies, setOutputSpecies] = useState(9606),
    [text, setText] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false),
    [page, setPage] = useState(0),
    [sort, setSort] = useState<SortKey>("source");
  const controller = useRef<AbortController | null>(null),
    resultHeading = useRef<HTMLHeadingElement>(null),
    focusResults = useRef(false);
  const terms = useMemo(() => parseIdentifiers(text), [text]);
  useEffect(() => {
    const c = new AbortController();
    setMetadataError("");
    fetch("/v1/species", { signal: c.signal })
      .then(async (r) => {
        if (!r.ok) throw Error();
        return r.json();
      })
      .then((data) => {
        setDatasetId(data.dataset_id);
        setSpecies(data.species);
        if (!data.species.some((s: Species) => s.id === 7227)) setInputSpecies(data.species[0]?.id ?? 0);
        if (!data.species.some((s: Species) => s.id === 9606)) setOutputSpecies(data.species[1]?.id ?? 0);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setMetadataError("The dataset is unavailable. Retry to load the species list.");
      });
    return () => c.abort();
  }, [metadataAttempt]);
  useEffect(() => () => controller.current?.abort(), []);
  // The heading mounts only after the response renders, so focus it from an effect, not a timeout.
  useEffect(() => {
    if (response && focusResults.current) {
      focusResults.current = false;
      resultHeading.current?.focus();
    }
  }, [response]);
  const rows = useMemo<ResultRow[]>(
    () =>
      response?.results.flatMap((input) =>
        input.orthologs.map((pair) => ({ key: `${input.index}:${pair.output_gene_id}`, input, pair })),
      ) ?? [],
    [response],
  );
  const sorted = useMemo(() => sortRows(rows, sort), [rows, sort]);
  const dirty =
    response &&
    (response.query.input_species !== inputSpecies ||
      response.query.output_species !== outputSpecies ||
      JSON.stringify(response.query.identifiers) !== JSON.stringify(terms));
  const speciesName = (id: number) =>
    species.find((s) => s.id === id)?.common_name || species.find((s) => s.id === id)?.name || String(id);
  async function search(e: React.FormEvent) {
    e.preventDefault();
    controller.current?.abort();
    const c = new AbortController();
    controller.current = c;
    setError("");
    setLoading(true);
    try {
      const r = await fetch("/v1/orthologs/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: c.signal,
        body: JSON.stringify({
          input_species: inputSpecies,
          output_species: outputSpecies,
          identifiers: terms,
          mapping_mode: "unambiguous",
          result_filter: "none",
        }),
      });
      const data = await r.json();
      if (!r.ok) throw Error(data.error || "Search failed. Please retry.");
      if (c.signal.aborted) return;
      setResponse(data);
      setEditing(false);
      setPage(0);
      setSort("source");
      focusResults.current = true;
    } catch (e) {
      if (c.signal.aborted) return;
      setError(e instanceof Error ? e.message : "Search failed. Please retry.");
    } finally {
      if (controller.current === c) setLoading(false);
    }
  }
  function cancel() {
    controller.current?.abort();
    setLoading(false);
    setError("Search cancelled. Your input is preserved.");
  }
  function editSearch() {
    setEditing(true);
    setTimeout(() => document.getElementById("search-input")?.focus(), 0);
  }
  const showCard = !response || editing;
  return (
    <>
      <a className="skip" href="#main">Skip to main content</a>
      <Header theme={theme} onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")} />
      <main id="main">
        <div className={response ? "intro compact" : "intro"}>
          <h1>DIOPT</h1>
          <p className="subtitle">DRSC Integrative Ortholog Prediction Tool</p>
          {!response ? (
            <p className="description">
              Finds ortholog candidates between species by combining predictions from multiple
              ortholog prediction methods. Enter genes from one species to list their predicted
              orthologs in another.
            </p>
          ) : null}
        </div>
        {showCard ? (
          <SearchCard
            species={species}
            metadataError={metadataError}
            onRetryMetadata={() => setMetadataAttempt((x) => x + 1)}
            inputSpecies={inputSpecies}
            outputSpecies={outputSpecies}
            setInputSpecies={setInputSpecies}
            setOutputSpecies={setOutputSpecies}
            text={text}
            setText={setText}
            terms={terms}
            loading={loading}
            error={error}
            setError={setError}
            onSubmit={search}
            onCancel={cancel}
            editing={Boolean(response)}
            onClose={() => setEditing(false)}
          />
        ) : null}
        {!response ? (
          <p className="intro-links">
            <a href="https://pubmed.ncbi.nlm.nih.gov/21880147/">Cite DIOPT</a>
            {" · "}
            <a href="#about-scores" onClick={() => setGuideOpen(true)}>About the scores and methods</a>
          </p>
        ) : null}
        {loading ? (
          <div className="loading" role="status">
            <p>Searching for orthologs…</p>
            <div />
            <div />
          </div>
        ) : null}
        {response ? (
          <section className="results" aria-label="Ortholog results" aria-busy={loading}>
            <SummaryBar
              response={response}
              pairCount={rows.length}
              speciesName={speciesName}
              headingRef={resultHeading}
              onEdit={editSearch}
              onExportTsv={() => exportTsv(sorted, response)}
              onExportJson={() => download("diopt-search.json", JSON.stringify(response, null, 2), "application/json")}
            />
            {dirty ? (
              <p className="change-notice">Search inputs have changed. These results still belong to your previous search.</p>
            ) : null}
            <ResultsTable
              response={response}
              rows={sorted}
              page={page}
              setPage={setPage}
              sort={sort}
              setSort={(s) => { setSort(s); setPage(0); }}
              speciesName={speciesName}
            />
          </section>
        ) : null}
        <ResultsGuide open={guideOpen} setOpen={setGuideOpen} />
      </main>
      <Footer datasetId={datasetId} />
    </>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
