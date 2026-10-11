export function ResultsGuide({ open, setOpen }: { open: boolean; setOpen: (open: boolean) => void }) {
  return (
    <details id="about-scores" className="score-guide" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>About the scores and methods</summary>
      <div className="guide-overview">
        <p>
          <strong>DIOPT score</strong>
          DIOPT combines ortholog predictions from multiple resources. The score counts the
          resources supporting a gene pair and is shown against the maximum for the species
          pair, for example 11/13. The maximum varies by species pair because method coverage differs.
        </p>
        <p>
          <strong>Methods column</strong>
          Each square is one prediction method that covers this species pair. A filled square
          means the method predicts this pair; an outlined square means it covers the species
          pair but does not predict this pair. A dashed square means coverage for that method is
          not recorded. Hover a square, or use a screen reader, to hear the method name.
        </p>
        <p>
          <strong>Confidence and ordering</strong>
          Confidence combines the score with whether the pair is a best match in either
          direction. Results start with high, then moderate, then low confidence, with higher
          scores first within each rank. Scores and flags are displayed as supplied by DRSC.
        </p>
      </div>
      <details className="guide-details">
        <summary>How confidence and best matches are defined</summary>
        <div className="guide-body">
          <p>
            Forward best means the pair has the highest DIOPT score for the input gene in the
            output species. Reverse best asks the same question starting from the output gene
            back toward the input species. Best scores can be shared by more than one match.
            "Yes (adjusted)" is shown where the source data marks the forward best match as adjusted.
          </p>
          <dl className="rank-definitions">
            <div><dt><span className="confidence high">High</span></dt><dd>Best in both directions, with a score of at least 2.</dd></div>
            <div><dt><span className="confidence moderate">Moderate</span></dt><dd>Best in one direction with a score of at least 2, or a score of at least 4 when neither direction is best.</dd></div>
            <div><dt><span className="confidence low">Low</span></dt><dd>All other pairs.</dd></div>
          </dl>
          <p>
            These are the rank definitions described in the{" "}
            <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC13104911/">2026 DIOPT update preprint</a>.
            This prototype displays the supplied rank rather than recalculating it.
          </p>
        </div>
      </details>
      <nav className="guide-sources" aria-label="DIOPT documentation and publications">
        <h3>Documentation and publications</h3>
        <ul>
          <li><a href="https://www.flyrnai.org/DIOPT_documentation_v10.html">DRSC documentation</a>: methods, species coverage, and maximum scores.</li>
          <li><a href="https://pubmed.ncbi.nlm.nih.gov/21880147/">Hu et al., 2011 · BMC Bioinformatics</a>: the original DIOPT publication.</li>
          <li><a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC13104911/">Hu et al., 2026 · DIOPT update</a>: preprint; not peer reviewed in the linked version.</li>
        </ul>
      </nav>
    </details>
  );
}
