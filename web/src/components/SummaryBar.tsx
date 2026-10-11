import type { RefObject } from "react";
import { ArrowRight, Download, FileText, Pencil } from "lucide-react";
import type { SearchResponse } from "../types";
import { summarizeIdentifiers } from "../format";

export function SummaryBar(props: {
  response: SearchResponse;
  pairCount: number;
  speciesName: (id: number) => string;
  headingRef: RefObject<HTMLHeadingElement | null>;
  onEdit: () => void;
  onExportTsv: () => void;
  onExportJson: () => void;
}) {
  const { response, pairCount, speciesName } = props;
  return (
    <div className="summary-bar">
      <div className="summary-text">
        <h2 ref={props.headingRef} tabIndex={-1}>
          {speciesName(response.query.input_species)}
          <ArrowRight size={18} aria-hidden="true" />
          <span className="sr-only"> to </span>
          {speciesName(response.query.output_species)} orthologs
        </h2>
        <p>
          {summarizeIdentifiers(response.query.identifiers)} · {pairCount.toLocaleString()}{" "}
          {pairCount === 1 ? "ortholog pair" : "ortholog pairs"}
        </p>
      </div>
      <div className="summary-actions">
        <button type="button" className="secondary" onClick={props.onEdit}>
          <Pencil size={15} /> Edit search
        </button>
        <button type="button" className="secondary" disabled={!pairCount} onClick={props.onExportTsv}>
          <Download size={15} /> All results · TSV
        </button>
        <button type="button" className="secondary" onClick={props.onExportJson}>
          <FileText size={15} /> Query + results · JSON
        </button>
      </div>
    </div>
  );
}
