import { useRef, type FormEvent } from "react";
import { ArrowLeftRight, Search, Upload, X } from "lucide-react";
import type { Species } from "../types";

const EXAMPLES = [
  { label: "rut", detail: "fly to human", input: 7227, output: 9606, text: "rut" },
  { label: "PAX6", detail: "human to fly", input: 9606, output: 7227, text: "PAX6" },
  { label: "rut, ey, CG3038", detail: "fly to human", input: 7227, output: 9606, text: "rut\ney\nCG3038" },
];

const speciesLabel = (s: Species) =>
  `${s.common_name || s.name || s.id}${s.common_name && s.name ? ` · ${s.name}` : ""}`;

export type SearchCardProps = {
  species: Species[];
  metadataError: string;
  onRetryMetadata: () => void;
  inputSpecies: number;
  outputSpecies: number;
  setInputSpecies: (id: number) => void;
  setOutputSpecies: (id: number) => void;
  text: string;
  setText: (t: string) => void;
  terms: string[];
  loading: boolean;
  error: string;
  setError: (e: string) => void;
  onSubmit: (e: FormEvent) => void;
  onCancel: () => void;
  editing: boolean;
  onClose: () => void;
};

export function SearchCard(props: SearchCardProps) {
  const { species, inputSpecies, outputSpecies, text, terms, loading, error } = props;
  const file = useRef<HTMLInputElement>(null);
  const ready = species.length > 0;
  async function upload(f: File | undefined) {
    if (!f) return;
    if (f.size > 128 * 1024) {
      props.setError("Choose a text file smaller than 128 KiB.");
      return;
    }
    try {
      props.setText(await f.text());
      props.setError("");
    } catch {
      props.setError("This file could not be read. Try pasting the identifiers.");
    }
    if (file.current) file.current.value = "";
  }
  const speciesSelect = (id: string, labelText: string, value: number, set: (n: number) => void) => (
    <div className="field">
      <label htmlFor={id}>{labelText}</label>
      <select id={id} value={value} onChange={(e) => set(Number(e.target.value))} disabled={!ready}>
        {ready
          ? species.map((s) => <option key={s.id} value={s.id}>{speciesLabel(s)}</option>)
          : <option>Loading species…</option>}
      </select>
    </div>
  );
  return (
    <form className={`search-card${props.editing ? " editing" : ""}`} onSubmit={props.onSubmit} aria-label="Ortholog search">
      {props.metadataError ? (
        <div role="alert" className="error">
          {props.metadataError}
          <button type="button" className="secondary" onClick={props.onRetryMetadata}>Retry species list</button>
        </div>
      ) : null}
      <div className="species-row">
        {speciesSelect("input-species", "From species", inputSpecies, props.setInputSpecies)}
        <button
          type="button"
          className="secondary swap-button"
          aria-label="Swap species"
          title="Swap species"
          disabled={!ready}
          onClick={() => {
            props.setInputSpecies(outputSpecies);
            props.setOutputSpecies(inputSpecies);
          }}
        >
          <ArrowLeftRight size={16} />
        </button>
        {speciesSelect("output-species", "To species", outputSpecies, props.setOutputSpecies)}
      </div>
      <div className="label-row">
        <label htmlFor="search-input">Gene identifiers</label>
        <span className={terms.length > 100 ? "over-limit" : ""}>{terms.length} / 100</span>
      </div>
      <textarea
        id="search-input"
        value={text}
        onChange={(e) => props.setText(e.target.value)}
        placeholder={"Gene symbols or stable IDs\nOne per line, or separated by commas"}
        aria-describedby="input-help"
        rows={6}
      />
      <p className="help" id="input-help">
        Use identifiers from the From species. Official symbols are matched first; ambiguous matches are reported, not guessed.
      </p>
      <input hidden ref={file} type="file" accept=".txt,.tsv,.csv" onChange={(e) => void upload(e.target.files?.[0])} />
      <div className="input-actions">
        <button type="button" className="link-button" onClick={() => file.current?.click()}>
          <Upload size={15} /> Import text file
        </button>
        <button type="button" className="link-button" onClick={() => props.setText("")} disabled={!text}>
          Clear
        </button>
      </div>
      <div className="examples">
        <span>Examples:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.label}
            type="button"
            className="link-button"
            aria-label={`Load example: ${ex.label}, ${ex.detail}`}
            disabled={!species.some((s) => s.id === ex.input) || !species.some((s) => s.id === ex.output)}
            onClick={() => {
              props.setInputSpecies(ex.input);
              props.setOutputSpecies(ex.output);
              props.setText(ex.text);
              props.setError("");
              document.getElementById("search-input")?.focus();
            }}
          >
            {ex.label} ({ex.detail})
          </button>
        ))}
      </div>
      {inputSpecies === outputSpecies ? <p className="error" role="alert">Choose two different species.</p> : null}
      {error ? <p role="alert" className="error">{error}</p> : null}
      <div className="card-actions">
        {props.editing && !loading ? (
          <button type="button" className="link-button" onClick={props.onClose}>Close search</button>
        ) : null}
        {loading ? (
          <button type="button" className="link-button" onClick={props.onCancel}>
            <X size={14} /> Cancel search
          </button>
        ) : null}
        <button
          className="primary"
          type="submit"
          disabled={!ready || terms.length === 0 || terms.length > 100 || inputSpecies === outputSpecies || loading}
        >
          <Search size={17} />
          {loading ? "Searching…" : "Find orthologs"}
        </button>
      </div>
    </form>
  );
}
