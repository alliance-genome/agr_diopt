import { datasetNote } from "../format";

export function Footer({ datasetId }: { datasetId: string }) {
  return (
    <footer className="site-footer">
      <div>
        <strong>DIOPT at the Alliance</strong>
        <span>
          Research prototype. Source software and data provided by the{" "}
          <a href="https://www.flyrnai.org/">DRSC</a>.
        </span>
      </div>
      <div>
        {datasetId ? <span>{datasetNote(datasetId)}</span> : null}
        <a href="https://pubmed.ncbi.nlm.nih.gov/21880147/">Cite DIOPT: Hu et al., 2011</a>
      </div>
    </footer>
  );
}
