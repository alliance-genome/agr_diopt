pub mod domain;
pub mod search;
use axum::{
    Json, Router,
    extract::{DefaultBodyLimit, State, rejection::JsonRejection},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
};
use domain::{SearchRequest, Species, SpeciesPairInfo, SpeciesPairs};
use serde_json::{Value, json};
use sqlx::MySqlPool;
use std::{collections::HashMap, sync::Arc, time::Duration};

#[derive(Clone)]
pub struct AppState {
    pub pool: MySqlPool,
    pub species: Arc<Vec<Species>>,
    pub dataset_id: String,
    pub species_pairs: Arc<SpeciesPairs>,
}

/// Merge precomputed method coverage with Ortholog_Max_Score (≈169 rows) into startup state.
pub async fn load_species_pairs(
    pool: &MySqlPool,
    coverage: HashMap<(i32, i32), Vec<String>>,
) -> Result<SpeciesPairs, sqlx::Error> {
    let mut pairs: SpeciesPairs = coverage
        .into_iter()
        .map(|(key, methods)| {
            (
                key,
                SpeciesPairInfo {
                    methods,
                    max_score: None,
                },
            )
        })
        .collect();
    let rows: Vec<(i32, i32, Option<i32>)> =
        sqlx::query_as("SELECT species1, species2, max_score FROM Ortholog_Max_Score")
            .fetch_all(pool)
            .await?;
    for (source, target, max_score) in rows {
        pairs.entry((source, target)).or_default().max_score = max_score;
    }
    Ok(pairs)
}
pub struct AppError {
    pub status: StatusCode,
    pub message: &'static str,
}
impl AppError {
    pub fn invalid(message: &'static str) -> Self {
        Self {
            status: StatusCode::BAD_REQUEST,
            message,
        }
    }
    pub fn limit() -> Self {
        Self {
            status: StatusCode::UNPROCESSABLE_ENTITY,
            message: "This query exceeds the prototype result limit. Search fewer identifiers.",
        }
    }
    pub fn data(message: &'static str) -> Self {
        Self {
            status: StatusCode::CONFLICT,
            message,
        }
    }
}
impl From<sqlx::Error> for AppError {
    fn from(error: sqlx::Error) -> Self {
        tracing::error!(code=?error.as_database_error().and_then(|e|e.code()),"database operation failed");
        Self {
            status: StatusCode::SERVICE_UNAVAILABLE,
            message: "The database could not complete this request. Please retry.",
        }
    }
}
impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        (self.status, Json(json!({"error":self.message}))).into_response()
    }
}

async fn species(State(state): State<AppState>) -> Json<Value> {
    Json(json!({"species":state.species,"dataset_id":state.dataset_id,"scientific_release":null}))
}
async fn ready(State(state): State<AppState>) -> Result<Json<Value>, AppError> {
    tokio::time::timeout(
        Duration::from_secs(2),
        sqlx::query("SELECT 1").execute(&state.pool),
    )
    .await
    .map_err(|_| AppError {
        status: StatusCode::SERVICE_UNAVAILABLE,
        message: "Database readiness check timed out.",
    })??;
    Ok(Json(
        json!({"status":"ready","dataset_id":state.dataset_id}),
    ))
}
async fn search_route(
    State(state): State<AppState>,
    body: Result<Json<SearchRequest>, JsonRejection>,
) -> Response {
    let id = uuid::Uuid::new_v4().to_string();
    let result = match body {
        Err(_) => Err(AppError::invalid(
            "Invalid JSON request. Supply two species and a list of identifiers (maximum body: 128 KiB).",
        )),
        Ok(Json(query)) => match tokio::time::timeout(
            Duration::from_secs(10),
            search::search(&state, query, id.clone()),
        )
        .await
        {
            Ok(result) => result,
            Err(_) => Err(AppError {
                status: StatusCode::GATEWAY_TIMEOUT,
                message: "Search timed out. Try a smaller list.",
            }),
        },
    };
    match result {
        Ok(response) => {
            tracing::info!(request_id=%id,elapsed_ms=response.elapsed_ms,queries=response.database_queries,"search completed");
            Json(response).into_response()
        }
        Err(e) => (e.status, Json(json!({"error":e.message,"request_id":id}))).into_response(),
    }
}
pub fn router(state: AppState) -> Router {
    Router::new()
        .route(
            "/health/live",
            get(|| async { Json(json!({"status":"alive"})) }),
        )
        .route("/health/ready", get(ready))
        .route("/v1/species", get(species))
        .route("/v1/orthologs/search", post(search_route))
        .layer(DefaultBodyLimit::max(128 * 1024))
        .with_state(state)
}
