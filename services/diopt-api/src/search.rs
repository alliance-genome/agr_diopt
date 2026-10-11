use crate::{AppError, AppState, domain::*};
use sqlx::{MySql, QueryBuilder, Row};
use std::collections::{BTreeSet, HashMap, HashSet};
use std::time::Instant;

pub async fn search(
    state: &AppState,
    request: SearchRequest,
    request_id: String,
) -> Result<SearchResponse, AppError> {
    let started = Instant::now();
    request.validate().map_err(AppError::invalid)?;
    if ![request.input_species, request.output_species]
        .iter()
        .all(|id| state.species.iter().any(|s| s.id == *id))
    {
        return Err(AppError::invalid(
            "The requested species is not present in this dataset.",
        ));
    }
    let terms: Vec<_> = request
        .identifiers
        .iter()
        .map(|s| s.trim().to_string())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let mut qb = QueryBuilder::<MySql>::new(
        "SELECT q.input_index, CAST(m.geneid AS CHAR) AS gene_id, g.symbol, g.species_specific_geneid AS species_specific_id, m.idvalue2 AS matched_identifier, m.idvalue AS lookup_identifier, m.idtype AS identifier_type, m.extra_info AS provenance, CAST(CASE WHEN BINARY m.idvalue2 = BINARY q.term AND m.extra_info = 'Entrez official symbol' THEN 4 WHEN m.extra_info = 'Entrez official symbol' THEN 3 WHEN BINARY m.idvalue2 = BINARY q.term THEN 2 ELSE 1 END AS SIGNED INTEGER) AS priority FROM (",
    );
    for (i, term) in terms.iter().enumerate() {
        if i > 0 {
            qb.push(" UNION ALL ");
        }
        qb.push("SELECT ")
            .push_bind(i as i32)
            .push(" AS input_index, ")
            .push_bind(term)
            .push(" AS term");
    }
    qb.push(") q JOIN GeneID_Mapping m ON m.idvalue = q.term LEFT JOIN Gene_Information g ON g.geneid=m.geneid AND g.speciesid=m.speciesid WHERE m.speciesid=")
        .push_bind(request.input_species).push(" AND m.geneid IS NOT NULL ORDER BY q.input_index, m.genemappingid LIMIT 20001");
    let mapped = qb
        .build_query_as::<Candidate>()
        .fetch_all(&state.pool)
        .await?;
    if mapped.len() > 20000 {
        return Err(AppError::limit());
    }
    let mut candidates_by_index: HashMap<i32, Vec<Candidate>> = HashMap::new();
    for row in mapped {
        let term = &terms[row.input_index as usize];
        // Database collation may match accents beyond the legacy equality/case rules.
        if row.matched_identifier.as_deref() != Some(term.as_str())
            && !row
                .lookup_identifier
                .as_ref()
                .is_some_and(|value| value.to_lowercase() == term.to_lowercase())
        {
            continue;
        }
        candidates_by_index
            .entry(row.input_index)
            .or_default()
            .push(row);
    }
    let candidates: Vec<Vec<Candidate>> = (0..terms.len())
        .map(|i| best_candidates(candidates_by_index.remove(&(i as i32)).unwrap_or_default()))
        .collect();
    let ids: BTreeSet<_> = candidates
        .iter()
        .filter(|x| x.len() == 1)
        .map(|x| x[0].gene_id.clone())
        .collect();
    let mut pairs: HashMap<String, Vec<Pair>> = HashMap::new();
    let mut query_count = 1;
    if !ids.is_empty() {
        let mut q = QueryBuilder::<MySql>::new(
            "SELECT CAST(b.geneid1 AS CHAR) AS input_gene_id, CAST(b.geneid2 AS CHAR) AS output_gene_id, g.symbol AS output_symbol, g.species_specific_geneid AS output_species_specific_id, g.species_specific_geneid_type AS output_species_specific_id_type, b.score AS stored_score, CAST(b.best_score AS CHAR) AS best_forward, CAST(b.best_score_rev AS CHAR) AS best_reverse, CAST(b.confidence AS CHAR) AS confidence FROM Ortholog_Pair_Best b LEFT JOIN Gene_Information g ON g.geneid=b.geneid2 AND g.speciesid=b.species2 WHERE b.species1=",
        );
        q.push_bind(request.input_species)
            .push(" AND b.species2=")
            .push_bind(request.output_species)
            .push(" AND b.geneid1 IN (");
        {
            let mut list = q.separated(",");
            for id in &ids {
                list.push_bind(id);
            }
        }
        q.push(") ORDER BY b.geneid1, CASE b.confidence WHEN 'high' THEN 0 WHEN 'moderate' THEN 1 WHEN 'low' THEN 2 ELSE 3 END, b.score DESC, b.geneid2 LIMIT 10001");
        let mut rows = q.build_query_as::<Pair>().fetch_all(&state.pool).await?;
        query_count += 1;
        if rows.len() > 10000 {
            return Err(AppError::limit());
        }
        let mut seen = HashSet::new();
        for row in &rows {
            if !seen.insert((row.input_gene_id.clone(), row.output_gene_id.clone())) {
                return Err(AppError::data(
                    "Duplicate ortholog-pair records require review; results were not merged.",
                ));
            }
        }
        let mut q = QueryBuilder::<MySql>::new(
            "SELECT CAST(geneid1 AS CHAR) AS input_id, CAST(geneid2 AS CHAR) AS output_id, prediction_method FROM Ortholog_Pair WHERE speciesid1=",
        );
        q.push_bind(request.input_species)
            .push(" AND speciesid2=")
            .push_bind(request.output_species)
            .push(" AND geneid1 IN (");
        {
            let mut list = q.separated(",");
            for id in &ids {
                list.push_bind(id);
            }
        }
        q.push(") LIMIT 100001");
        let evidence = q.build().fetch_all(&state.pool).await?;
        query_count += 1;
        if evidence.len() > 100000 {
            return Err(AppError::limit());
        }
        let mut grouped: HashMap<
            (String, String),
            std::collections::BTreeMap<Option<String>, u64>,
        > = HashMap::new();
        for row in evidence {
            let key = (
                row.try_get::<String, _>("input_id")?,
                row.try_get::<String, _>("output_id")?,
            );
            let method = row.try_get::<Option<String>, _>("prediction_method")?;
            *grouped.entry(key).or_default().entry(method).or_default() += 1;
        }
        for row in &mut rows {
            if let Some(methods) =
                grouped.remove(&(row.input_gene_id.clone(), row.output_gene_id.clone()))
            {
                row.evidence_row_count = methods.values().sum();
                row.methods = methods
                    .into_iter()
                    .map(|(name, rows)| MethodEvidence { name, rows })
                    .collect();
            }
        }
        for row in rows {
            pairs
                .entry(row.input_gene_id.clone())
                .or_default()
                .push(row);
        }
    }
    let mut results = vec![];
    let mut total = 0;
    for (index, identifier) in request.identifiers.iter().enumerate() {
        let i = terms
            .binary_search(&identifier.trim().to_string())
            .expect("term came from request");
        let c = candidates[i].clone();
        let orthologs = if c.len() == 1 {
            pairs.get(&c[0].gene_id).cloned().unwrap_or_default()
        } else {
            vec![]
        };
        total += orthologs.len();
        if total > 10000 {
            return Err(AppError::limit());
        }
        let status = if c.is_empty() {
            "unmapped"
        } else if c.len() > 1 {
            "ambiguous"
        } else if orthologs.is_empty() {
            "no_orthologs"
        } else {
            "mapped"
        };
        results.push(InputResult {
            index,
            identifier: identifier.clone(),
            status,
            candidates: c,
            orthologs,
        });
    }
    let pair_info = state
        .species_pairs
        .get(&(request.input_species, request.output_species))
        .cloned()
        .unwrap_or_default();
    Ok(SearchResponse {
        dataset_id: state.dataset_id.clone(),
        scientific_release: None,
        contract_version: "prototype-3",
        request_id,
        species_pair_methods: pair_info.methods,
        max_score: pair_info.max_score,
        query: request,
        results,
        elapsed_ms: started.elapsed().as_millis(),
        database_queries: query_count,
    })
}
