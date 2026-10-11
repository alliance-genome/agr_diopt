use axum::{
    body::{Body, to_bytes},
    http::{Request, StatusCode},
};
use diopt_api::{AppState, router};
use sqlx::mysql::MySqlPoolOptions;
use std::sync::Arc;
use tower::ServiceExt;

#[tokio::test]
async fn invalid_requests_fail_before_database_access() {
    let state = AppState {
        pool: MySqlPoolOptions::new()
            .connect_lazy("mysql://unused@127.0.0.1:1/unused")
            .unwrap(),
        species: Arc::new(vec![]),
        dataset_id: "test".into(),
        species_pairs: Arc::new(Default::default()),
    };
    for body in [
        "{",
        r#"{"input_species":1,"output_species":2,"identifiers":[],"result_filter":"none"}"#,
        r#"{"input_species":1,"output_species":2,"identifiers":["x"],"result_filter":"best"}"#,
    ] {
        let response = router(state.clone())
            .oneshot(
                Request::post("/v1/orthologs/search")
                    .header("content-type", "application/json")
                    .body(Body::from(body))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
        let json: serde_json::Value =
            serde_json::from_slice(&to_bytes(response.into_body(), 20000).await.unwrap()).unwrap();
        assert!(json["error"].is_string());
        assert!(json["request_id"].is_string());
    }
    let response = router(state)
        .oneshot(Request::get("/health/live").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
}
