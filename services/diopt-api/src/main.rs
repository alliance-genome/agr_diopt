use diopt_api::{AppState, domain::Species};
use sqlx::mysql::{MySqlConnectOptions, MySqlPoolOptions, MySqlSslMode};
use std::{env, sync::Arc, time::Duration};
use tower_http::services::ServeDir;
fn required(name: &str) -> Result<String, Box<dyn std::error::Error>> {
    let value = env::var(name).map_err(|_| format!("Missing environment variable: {name}"))?;
    if value.is_empty() {
        return Err(format!("Empty environment variable: {name}").into());
    }
    Ok(value)
}
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter("diopt_api=info")
        .init();
    let host = required("DIOPT_DB_HOST")?;
    let local = env::var("DIOPT_LOCAL_DB").as_deref() == Ok("true");
    if local && host != "127.0.0.1" && host != "localhost" {
        return Err("Local DB exception requires a loopback host".into());
    }
    let mut options = MySqlConnectOptions::new()
        .host(&host)
        .port(required("DIOPT_DB_PORT")?.parse()?)
        .username(&required("DIOPT_DB_USER")?)
        .password(&required("DIOPT_DB_PASSWORD")?)
        .database(&required("DIOPT_DB_NAME")?)
        .ssl_mode(if local {
            MySqlSslMode::Disabled
        } else {
            MySqlSslMode::VerifyIdentity
        });
    if !local {
        options = options.ssl_ca(required("DIOPT_DB_CA")?);
    }
    let pool = MySqlPoolOptions::new()
        .max_connections(5)
        .acquire_timeout(Duration::from_secs(3))
        .after_connect(|connection, _| {
            Box::pin(async move {
                sqlx::query("SET SESSION max_statement_time=8")
                    .execute(connection)
                    .await?;
                Ok(())
            })
        })
        .connect_with(options)
        .await?;
    for table in [
        "Species",
        "Gene_Information",
        "GeneID_Mapping",
        "Ortholog_Pair_Best",
        "Ortholog_Pair",
        "Prediction_Method",
        "Ortholog_Max_Score",
    ] {
        sqlx::query(&format!("SELECT 1 FROM `{table}` LIMIT 0"))
            .execute(&pool)
            .await?;
    }
    // The source's species 0 is an "All" menu sentinel, not a searchable species.
    let species=sqlx::query_as::<_,Species>("SELECT speciesid AS id,species_name AS name,common_name FROM Species WHERE speciesid > 0 ORDER BY display_order,species_name").fetch_all(&pool).await?;
    let dataset_id = required("DIOPT_DATASET_ID")?;
    let coverage_path = required("DIOPT_METHOD_COVERAGE")?;
    let coverage = diopt_api::domain::parse_coverage(
        &std::fs::read_to_string(&coverage_path)
            .map_err(|e| format!("Cannot read DIOPT_METHOD_COVERAGE {coverage_path}: {e}"))?,
        &dataset_id,
    )?;
    let species_pairs = diopt_api::load_species_pairs(&pool, coverage).await?;
    let state = AppState {
        pool,
        species: Arc::new(species),
        dataset_id,
        species_pairs: Arc::new(species_pairs),
    };
    let web = env::var("DIOPT_WEB_DIR").unwrap_or_else(|_| "web/dist".into());
    let app = diopt_api::router(state).fallback_service(ServeDir::new(web));
    let port = env::var("DIOPT_PORT")
        .unwrap_or_else(|_| "43100".into())
        .parse::<u16>()?;
    let listener = tokio::net::TcpListener::bind((std::net::Ipv4Addr::LOCALHOST, port)).await?;
    if let Ok(address) = env::var("DIOPT_LAN_IP") {
        let address: std::net::Ipv4Addr = address.parse()?;
        if !address.is_private() {
            return Err("DIOPT_LAN_IP must be a private IPv4 address".into());
        }
        let lan = tokio::net::TcpListener::bind((address, port)).await?;
        let lan_app = app.clone();
        tokio::spawn(async move {
            if let Err(error) = axum::serve(lan, lan_app)
                .with_graceful_shutdown(async {
                    let _ = tokio::signal::ctrl_c().await;
                })
                .await
            {
                tracing::error!(%error, "LAN listener failed");
            }
        });
        tracing::info!(%address, port, "DIOPT LAN preview listening");
    }
    tracing::info!(port, "DIOPT local prototype listening");
    axum::serve(listener, app)
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
