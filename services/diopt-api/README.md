# DIOPT search API and web app

Axum/SQLx API and React/TypeScript researcher interface for searching DIOPT ortholog
predictions. Search is read-only against a MariaDB (MySQL-family) copy of the DIOPT
tables described in [`docs/schema/`](../../docs/schema/). This is a prototype; its output
has not yet been validated against the DRSC DIOPT release.

## Requirements

Rust 1.98.1 (pinned in `rust-toolchain.toml`), Node 24 with npm, Python 3, and Docker.
Run every command from the repository root.

## Configuration

Machine-specific values live outside the repository, in `~/.config/diopt-prototype/`
(owner-only permissions). `scripts/run_local_api.py` passes `api-env.json` from there to
the API as environment variables; `services/diopt-api/.env.example` lists every field.
Python scripts resolve two locations in this order: environment variable, then
`api-env.json`, then the default. The browser scripts under `web/tests/` read
`DIOPT_DATA_DIR` from the environment only.

| Setting | Default | Purpose |
| --- | --- | --- |
| `DIOPT_DATA_DIR` | `~/diopt-data` | Database files, manifests, benchmarks, derived files |
| `DIOPT_API_BINARY` | `services/diopt-api/target/release/diopt-api` | API executable used by `run_local_api.py` |
| `DIOPT_METHOD_COVERAGE` | none (required) | Output of `scripts/build_method_coverage.py` |

## Quick start with synthetic data

No real data is needed. The fixture rows are deliberately synthetic, not biological results.

```sh
python3 scripts/start_local_database.py        # MariaDB on 127.0.0.1:43306
python3 scripts/setup_local_api_config.py      # read-only account for diopt and diopt_fixture
docker exec diopt-prototype-db mariadb --defaults-extra-file=/run/diopt-secrets/root.cnf \
  -e "CREATE DATABASE IF NOT EXISTS diopt_fixture"
docker exec -i diopt-prototype-db mariadb --defaults-extra-file=/run/diopt-secrets/root.cnf \
  diopt_fixture < services/diopt-api/tests/fixtures/search.sql
cargo +1.98.1 build --release --locked --manifest-path services/diopt-api/Cargo.toml
npm ci --prefix web && npm run build --prefix web
DIOPT_PORT=43111 python3 scripts/run_local_api.py --fixture
```

Open `http://127.0.0.1:43111`. To recreate the fixture after editing
`tests/fixtures/search.sql`, run `DROP DATABASE IF EXISTS diopt_fixture` first.

## Real data

1. Start the database: `python3 scripts/start_local_database.py`.
2. Create the account and API config, naming the data you are about to load. This also
   waits until the new database finishes its first-time setup:
   `python3 scripts/setup_local_api_config.py --dataset-id diopt-YYYY-MM-DD`.
3. Load a DIOPT MySQL dump containing the tables in [`docs/schema/`](../../docs/schema/)
   into the `diopt` database, for example
   `docker exec -i diopt-prototype-db mariadb --defaults-extra-file=/run/diopt-secrets/root.cnf diopt < dump.sql`.
4. Precompute method coverage (about a minute on a full dataset):
   `python3 scripts/build_method_coverage.py`. Rerun it after every data refresh. The API
   refuses to start when the coverage file was built for a different dataset.
5. Build the API and web app as above, then run `python3 scripts/run_local_api.py` and open
   `http://127.0.0.1:43100`.

MariaDB listens only on `127.0.0.1:43306`; the API binds loopback. Set `DIOPT_LAN_IP` to a
private (RFC 1918) IPv4 address to add a LAN listener for internal previews. This is a research
preview, not an authenticated public deployment. The container is limited to 8 GiB with
a 6 GiB buffer pool; adjust `scripts/start_local_database.py` on smaller machines. The
database image is pinned by digest. Credentials are generated into the private directory,
mounted read-only into the container, and never placed in argv or Git. For a remote
database, disable `DIOPT_LOCAL_DB` and supply `DIOPT_DB_CA` for verified TLS.

## Supported behavior

- Explicit input and output species, 1–100 identifiers, original order and repeats preserved.
- Highest-priority identifier mappings; ties across genes are returned as ambiguous.
- No biological result filter yet; best-match semantics await confirmation from DRSC.
- Stored score, the species pair's maximum score, confidence and best flags are reported unchanged.
- Each response lists the prediction methods that cover the species pair, from the precomputed coverage file.
- Supporting methods and raw evidence-row counts are separate quantities.
- Conflicting duplicate pair records cause a clear error rather than arbitrary selection.
  Gene IDs serialize as strings.
- At most 10,000 returned rows, 20,000 mapping rows, and 100,000 method rows per request;
  exceeding a bound returns an explicit error. Nothing is silently truncated.
- Ten-second request deadline; eight-second database statement limit; at most five
  database connections. Scientific values are never inferred from timeouts or empty data.

The web app offers species selection, pasted or file inputs, mapping-status details, a
per-method evidence strip, sorting within each input gene, and TSV/JSON exports. TSV
exports all returned rows in the selected order, neutralizes formula-leading values, and
flattens embedded tabs and newlines. JSON holds the exact query and response. There is no
query history, analytics, or account system.

## API

- `GET /health/live`: process liveness.
- `GET /health/ready`: database connection check; startup also verifies seven tables.
- `GET /v1/species`: species metadata and dataset identifier.
- `POST /v1/orthologs/search`: JSON body, maximum 128 KiB.

```json
{"input_species":7227,"output_species":9606,"identifiers":["ey"],"mapping_mode":"unambiguous","result_filter":"none"}
```

Unsupported modes and unknown fields are rejected. Responses distinguish `mapped`,
`ambiguous`, `unmapped`, and `no_orthologs`, and carry dataset, request, and contract
identifiers, plus `species_pair_methods` and `max_score` for the species pair. Database
errors are sanitized; logs omit submitted gene lists and credentials.

## Tests

```sh
cargo +1.98.1 test --locked --manifest-path services/diopt-api/Cargo.toml
cargo +1.98.1 clippy --locked --manifest-path services/diopt-api/Cargo.toml --all-targets -- -D warnings
python3 -m unittest discover -s scripts/tests
npm run test:unit --prefix web
npm test --prefix web          # browser tests; needs the fixture API on port 43111
```

- The ignored Rust database test needs the `diopt_fixture` schema. Pass the reader password
  through the environment: `DIOPT_TEST_PASSWORD="$(cat ~/.config/diopt-prototype/reader-password)" cargo +1.98.1 test --locked --manifest-path services/diopt-api/Cargo.toml --test search -- --ignored`.
- Browser tests target port 43111 unless `DIOPT_BASE_URL` is set. Install Chromium with
  `npx --prefix web playwright install chromium`, or set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`.
- With real data loaded and the API running, `python3 scripts/check_real_search.py`
  compares returned scores, flags and evidence with the source rows in both fly/human
  directions and writes a benchmark corpus. `node web/tests/real-smoke.cjs` and
  `node web/tests/theme-groups.cjs` then exercise the browser against real data.
  `scripts/benchmark_local_search.py --corpus ... --output ...` records a workload.
- Screenshots go to `DIOPT_SCREENSHOT_DIR` (default `test-results/screenshots`).
- None of these replace scientific parity review with DRSC.
