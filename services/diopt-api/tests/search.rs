use diopt_api::{
    AppState,
    domain::{SearchRequest, Species},
    search::search,
};
use sqlx::mysql::{MySqlConnectOptions, MySqlPoolOptions, MySqlSslMode};
use std::{env, sync::Arc};

#[tokio::test]
#[ignore = "requires the diopt_fixture schema; see services/diopt-api/README.md"]
async fn synthetic_database_contract() {
    let options = MySqlConnectOptions::new()
        .host("127.0.0.1")
        .port(43306)
        .username("diopt_reader")
        .password(&env::var("DIOPT_TEST_PASSWORD").expect("DIOPT_TEST_PASSWORD"))
        .database("diopt_fixture")
        .ssl_mode(MySqlSslMode::Disabled);
    let pool = MySqlPoolOptions::new()
        .max_connections(2)
        .connect_with(options)
        .await
        .unwrap();
    let species = sqlx::query_as::<_, Species>(
        "SELECT speciesid AS id,species_name AS name,common_name FROM Species",
    )
    .fetch_all(&pool)
    .await
    .unwrap();
    let coverage = diopt_api::domain::parse_coverage(
        include_str!("fixtures/method-coverage.json"),
        "synthetic-fixture-not-biological-results",
    )
    .unwrap();
    let species_pairs = diopt_api::load_species_pairs(&pool, coverage)
        .await
        .unwrap();
    let state = AppState {
        pool,
        species: Arc::new(species),
        dataset_id: "synthetic-fixture-not-biological-results".into(),
        species_pairs: Arc::new(species_pairs),
    };
    let query = SearchRequest {
        input_species: 7227,
        output_species: 9606,
        identifiers: vec![
            "ProbeA",
            "Shared",
            "Unknown",
            "NoPair",
            "ProbeA",
            "' OR 1=1 --",
        ]
        .into_iter()
        .map(String::from)
        .collect(),
        mapping_mode: "unambiguous".into(),
        result_filter: "none".into(),
    };
    let result = search(&state, query, "test".into())
        .await
        .map_err(|e| e.message)
        .unwrap();
    assert_eq!(result.database_queries, 3);
    assert_eq!(result.contract_version, "prototype-3");
    assert_eq!(
        result.species_pair_methods,
        vec!["Method A", "Method B", "Method C"]
    );
    assert_eq!(result.max_score, Some(5));
    // No Ortholog_Max_Score row or coverage for the reverse pair: both stay empty.
    let reverse = search(
        &state,
        SearchRequest {
            input_species: 9606,
            output_species: 7227,
            identifiers: vec!["TargetA".into()],
            mapping_mode: "unambiguous".into(),
            result_filter: "none".into(),
        },
        "reverse".into(),
    )
    .await
    .map_err(|e| e.message)
    .unwrap();
    assert!(reverse.species_pair_methods.is_empty());
    assert_eq!(reverse.max_score, None);
    let json = serde_json::to_value(&result).unwrap();
    assert!(
        json["results"][0]["orthologs"][0]
            .get("weighted_score")
            .is_none(),
        "weighted_score must not be serialized"
    );
    assert_eq!(
        result.results.iter().map(|x| x.status).collect::<Vec<_>>(),
        vec![
            "mapped",
            "ambiguous",
            "unmapped",
            "no_orthologs",
            "mapped",
            "unmapped"
        ]
    );
    let first = &result.results[0];
    assert_eq!(first.candidates[0].gene_id, "101");
    assert_eq!(first.orthologs.len(), 2);
    let pair = first
        .orthologs
        .iter()
        .find(|x| x.output_gene_id == "201")
        .unwrap();
    assert_eq!(pair.stored_score, Some(5));
    assert_eq!(pair.best_forward.as_deref(), Some("Yes_Adjusted"));
    assert_eq!(pair.evidence_row_count, 3);
    assert_eq!(pair.methods.len(), 2);
    assert_eq!(pair.methods[0].rows, 2);
    let null = first
        .orthologs
        .iter()
        .find(|x| x.output_gene_id == "202")
        .unwrap();
    assert!(null.confidence.is_none());
    assert!(null.stored_score.is_none());
    assert_eq!(result.results[1].candidates.len(), 2);
    assert_eq!(result.results[4].orthologs.len(), 2);
    // The cross-species row with score 99 and its method must not leak into results.
    assert!(first.orthologs.iter().all(|x| x.output_gene_id != "203"));
    assert!(
        !pair
            .methods
            .iter()
            .any(|m| m.name.as_deref() == Some("Wrong species method"))
    );
    let query = SearchRequest {
        input_species: 7227,
        output_species: 9606,
        identifiers: vec!["probea".into()],
        mapping_mode: "unambiguous".into(),
        result_filter: "none".into(),
    };
    let result = search(&state, query, "case".into())
        .await
        .map_err(|e| e.message)
        .unwrap();
    assert_eq!(result.results[0].candidates[0].gene_id, "101");
    assert_eq!(result.results[0].candidates[0].priority, 3);
    let query = SearchRequest {
        input_species: 7227,
        output_species: 9606,
        identifiers: vec!["ProbeÁ".into()],
        mapping_mode: "unambiguous".into(),
        result_filter: "none".into(),
    };
    let result = search(&state, query, "accent".into())
        .await
        .map_err(|e| e.message)
        .unwrap();
    assert_eq!(result.results[0].status, "unmapped");
    let make_query = |name: &str| SearchRequest {
        input_species: 7227,
        output_species: 9606,
        identifiers: vec![name.into()],
        mapping_mode: "unambiguous".into(),
        result_filter: "none".into(),
    };
    let result = search(&state, make_query("Large"), "large".into())
        .await
        .map_err(|e| e.message)
        .unwrap();
    assert_eq!(
        result.results[0].orthologs[0].output_gene_id,
        "9007199254740993"
    );
    let ranked = search(&state, make_query("Ranking"), "ranking".into())
        .await
        .map_err(|e| e.message)
        .unwrap();
    assert_eq!(
        ranked.results[0]
            .orthologs
            .iter()
            .map(|p| p.output_gene_id.as_str())
            .collect::<Vec<_>>(),
        vec!["214", "212", "216", "213", "211", "215"]
    );
    let error = search(&state, make_query("Conflict"), "duplicate".into())
        .await
        .err()
        .unwrap();
    assert_eq!(error.status, axum::http::StatusCode::CONFLICT);
}
