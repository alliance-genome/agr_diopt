export type Species = {
  id: number;
  name: string | null;
  common_name: string | null;
};
export type Candidate = {
  gene_id: string;
  symbol: string | null;
  species_specific_id: string | null;
  matched_identifier: string | null;
  identifier_type: string | null;
  provenance: string | null;
  priority: number;
};
export type Pair = {
  input_gene_id: string;
  output_gene_id: string;
  output_symbol: string | null;
  output_species_specific_id: string | null;
  output_species_specific_id_type: string | null;
  stored_score: number | null;
  best_forward: string | null;
  best_reverse: string | null;
  confidence: string | null;
  methods: { name: string | null; rows: number }[];
  evidence_row_count: number;
};
export type InputResult = {
  index: number;
  identifier: string;
  status: "mapped" | "ambiguous" | "unmapped" | "no_orthologs";
  candidates: Candidate[];
  orthologs: Pair[];
};
export type SearchQuery = {
  input_species: number;
  output_species: number;
  identifiers: string[];
  mapping_mode: "unambiguous";
  result_filter: "none";
};
export type SearchResponse = {
  dataset_id: string;
  scientific_release: null | string;
  contract_version: string;
  request_id: string;
  query: SearchQuery;
  species_pair_methods: string[];
  max_score: number | null;
  results: InputResult[];
  elapsed_ms: number;
  database_queries: number;
};
export type ResultRow = { key: string; input: InputResult; pair: Pair };
