use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};

#[derive(Debug, Deserialize, Serialize, Clone)]
#[serde(deny_unknown_fields)]
pub struct SearchRequest {
    pub input_species: i32,
    pub output_species: i32,
    pub identifiers: Vec<String>,
    #[serde(default = "mapping_default")]
    pub mapping_mode: String,
    #[serde(default = "filter_default")]
    pub result_filter: String,
}
fn mapping_default() -> String {
    "unambiguous".into()
}
fn filter_default() -> String {
    "none".into()
}
impl SearchRequest {
    pub fn validate(&self) -> Result<(), &'static str> {
        if self.mapping_mode != "unambiguous" || self.result_filter != "none" {
            return Err(
                "This prototype supports unambiguous mapping and no biological filtering only.",
            );
        }
        if self.input_species <= 0
            || self.output_species <= 0
            || self.input_species == self.output_species
        {
            return Err("Choose two different species.");
        }
        if self.identifiers.is_empty() || self.identifiers.len() > 100 {
            return Err("Enter between 1 and 100 identifiers.");
        }
        if self.identifiers.iter().any(|s| {
            s.trim().is_empty() || s.chars().count() > 512 || s.chars().any(char::is_control)
        }) {
            return Err(
                "Identifiers must be nonempty, at most 512 characters, and contain no control characters.",
            );
        }
        Ok(())
    }
}
#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct Species {
    pub id: i32,
    pub name: Option<String>,
    pub common_name: Option<String>,
}
#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct Candidate {
    #[serde(skip)]
    pub input_index: i32,
    pub gene_id: String,
    pub symbol: Option<String>,
    pub species_specific_id: Option<String>,
    pub matched_identifier: Option<String>,
    #[serde(skip)]
    pub lookup_identifier: Option<String>,
    pub identifier_type: Option<String>,
    pub provenance: Option<String>,
    pub priority: i32,
}
#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct Pair {
    pub input_gene_id: String,
    pub output_gene_id: String,
    pub output_symbol: Option<String>,
    pub output_species_specific_id: Option<String>,
    pub output_species_specific_id_type: Option<String>,
    pub stored_score: Option<i32>,
    pub best_forward: Option<String>,
    pub best_reverse: Option<String>,
    pub confidence: Option<String>,
    #[sqlx(skip)]
    pub methods: Vec<MethodEvidence>,
    #[sqlx(skip)]
    pub evidence_row_count: u64,
}
#[derive(Debug, Clone, Serialize)]
pub struct MethodEvidence {
    pub name: Option<String>,
    pub rows: u64,
}
#[derive(Debug, Serialize)]
pub struct InputResult {
    pub index: usize,
    pub identifier: String,
    pub status: &'static str,
    pub candidates: Vec<Candidate>,
    pub orthologs: Vec<Pair>,
}
#[derive(Debug, Serialize)]
pub struct SearchResponse {
    pub dataset_id: String,
    pub scientific_release: Option<String>,
    pub contract_version: &'static str,
    pub request_id: String,
    pub query: SearchRequest,
    pub species_pair_methods: Vec<String>,
    pub max_score: Option<i32>,
    pub results: Vec<InputResult>,
    pub elapsed_ms: u128,
    pub database_queries: usize,
}

/// Per-species-pair data loaded once at startup (static per dataset).
#[derive(Debug, Clone, Default)]
pub struct SpeciesPairInfo {
    pub methods: Vec<String>,
    pub max_score: Option<i32>,
}
pub type SpeciesPairs = HashMap<(i32, i32), SpeciesPairInfo>;

#[derive(Deserialize)]
struct CoverageFile {
    dataset_id: String,
    pairs: BTreeMap<String, Vec<String>>,
}

/// Parse the precomputed method-coverage file; a file built for another dataset is an error.
pub fn parse_coverage(
    json: &str,
    expected_dataset_id: &str,
) -> Result<HashMap<(i32, i32), Vec<String>>, String> {
    let file: CoverageFile =
        serde_json::from_str(json).map_err(|e| format!("Invalid method coverage file: {e}"))?;
    if file.dataset_id != expected_dataset_id {
        return Err(format!(
            "Method coverage file is for dataset {} but the API serves {}; rerun scripts/build_method_coverage.py",
            file.dataset_id, expected_dataset_id
        ));
    }
    let mut pairs = HashMap::new();
    for (key, mut methods) in file.pairs {
        let parsed = key
            .split_once(':')
            .and_then(|(a, b)| Some((a.parse().ok()?, b.parse().ok()?)))
            .ok_or_else(|| format!("Invalid species pair key in method coverage file: {key}"))?;
        methods.sort_by(|a, b| {
            a.to_lowercase()
                .cmp(&b.to_lowercase())
                .then_with(|| a.cmp(b))
        });
        methods.dedup();
        pairs.insert(parsed, methods);
    }
    Ok(pairs)
}

/// Keep every distinct highest-priority gene; never resolve biological ties by row order.
pub fn best_candidates(rows: Vec<Candidate>) -> Vec<Candidate> {
    let Some(maximum) = rows.iter().map(|x| x.priority).max() else {
        return vec![];
    };
    let mut genes = BTreeMap::new();
    for row in rows.into_iter().filter(|x| x.priority == maximum) {
        genes.entry(row.gene_id.clone()).or_insert(row);
    }
    genes.into_values().collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    fn candidate(id: &str, priority: i32) -> Candidate {
        Candidate {
            input_index: 0,
            gene_id: id.into(),
            symbol: None,
            species_specific_id: None,
            matched_identifier: None,
            lookup_identifier: None,
            identifier_type: None,
            provenance: None,
            priority,
        }
    }
    #[test]
    fn ranking_preserves_ambiguous_genes_but_collapses_duplicate_evidence() {
        let result = best_candidates(vec![
            candidate("1", 3),
            candidate("2", 4),
            candidate("3", 4),
            candidate("2", 4),
        ]);
        assert_eq!(
            result
                .iter()
                .map(|x| x.gene_id.as_str())
                .collect::<Vec<_>>(),
            vec!["2", "3"]
        );
    }
    #[test]
    fn coverage_parses_sorts_and_dedupes() {
        let json = r#"{"dataset_id":"d","generated_at":"t","pairs":{"7227:9606":["Panther","eggNOG","Compara","Panther","eggNOG"]}}"#;
        let pairs = parse_coverage(json, "d").unwrap();
        assert_eq!(pairs[&(7227, 9606)], vec!["Compara", "eggNOG", "Panther"]);
    }
    #[test]
    fn coverage_from_another_dataset_is_rejected() {
        let json = r#"{"dataset_id":"old","generated_at":"t","pairs":{}}"#;
        let error = parse_coverage(json, "new").unwrap_err();
        assert!(error.contains("old") && error.contains("new"), "{error}");
    }
    #[test]
    fn coverage_with_malformed_pair_key_is_rejected() {
        let json = r#"{"dataset_id":"d","generated_at":"t","pairs":{"7227-9606":["A"]}}"#;
        assert!(parse_coverage(json, "d").is_err());
    }
    #[test]
    fn invalid_modes_and_limits_are_rejected() {
        let mut q = SearchRequest {
            input_species: 7227,
            output_species: 9606,
            identifiers: vec!["a' OR 1=1 --".into()],
            mapping_mode: mapping_default(),
            result_filter: filter_default(),
        };
        assert!(q.validate().is_ok()); // SQL values are bound, not sanitized into different identifiers.
        q.result_filter = "best".into();
        assert!(q.validate().is_err());
        q.result_filter = filter_default();
        q.identifiers = vec!["x".into(); 101];
        assert!(q.validate().is_err());
    }
}
