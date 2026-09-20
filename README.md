# ATLAS

ATLAS is a deterministic consequence-simulation engine for modeling how a supply shock in one region can cascade through trade relationships, import dependence, logistics networks, and downstream market effects.

## What it includes

- FastAPI backend with a scenario execution API
- NetworkX-based knowledge graph for producer/importer/logistics relationships
- Deterministic temporal cascade engine for 1–36 month horizons
- Intervention comparison between baseline, shock, and alternate-supply scenarios
- React + Vite frontend for scenario controls and graph display
- Test suite covering key API and simulation behaviors

## Architecture

- `backend/app/main.py` exposes HTTP endpoints for graph loading and scenario execution
- `backend/app/graph/builder.py` builds the wheat knowledge graph from structured local data fixtures
- `backend/app/simulation/engine.py` computes production loss, trade exposure, timeline, and comparison summaries
- `backend/app/data/*` provides normalized data contracts and loaders
- `backend/app/data/acquisition.py` provides checksum-aware cached public-source acquisition
- `backend/app/data/dependency.py` computes multi-year supplier shares and HHI
- `backend/data/raw/` stores reproducible source fixtures
- `backend/data/metadata/` stores source provenance information
- `backend/scripts/ingest_*.py` generates normalized processed outputs from the raw fixtures
- `frontend/src/App.jsx` renders the scenario controls and summary dashboard
- `frontend/src/ButterflyMap.jsx` renders the graph visualization layer

## Data ingestion and provenance

ATLAS now includes a reproducible local ingestion foundation for wheat production and wheat trade data:

- `backend/data/raw/faostat/wheat-production.csv` provides multi-year FAOSTAT wheat production values
- `backend/data/raw/comtrade/wheat-global-trade.csv` provides a deterministic, local wheat trade subset
- `backend/data/metadata/*` records the data source, coverage, units, and limitations for each dataset
- `backend/scripts/ingest_faostat.py` and `backend/scripts/ingest_comtrade.py` generate processed outputs under `backend/data/processed/`
- `backend/scripts/acquire_public_data.py` downloads versioned raw artifacts when an official source URL is available, and uses the cache when offline
- `backend/DATA_DICTIONARY.md` defines observed, derived, modeled, and provisional fields

The graph builder consumes these normalized records instead of relying solely on the older demo graph, while preserving the legacy API contract.

The checked-in CSVs are deterministic repository fixtures derived from the cited public sources,
not a claim that a live archive was downloaded during every run. The acquisition adapter stores
raw downloads separately, records SHA-256 checksums and query metadata in sidecar JSON, and never
silently overwrites an existing raw artifact.

### Reproducible acquisition

```bash
cd backend
python scripts/acquire_public_data.py faostat --version 2024
python scripts/acquire_public_data.py comtrade --reporter-code 250 --period 2024
python scripts/ingest_faostat.py
python scripts/ingest_comtrade.py
```

The FAOSTAT command uses the official bulk archive URL by default and supports
`ATLAS_FAOSTAT_URL` or `--url` for a documented source change. The Comtrade command uses
the credential-free UN Comtrade public preview API for HS1001 and stores the exact query.
Network acquisition is explicit; tests use local fixtures and do not require internet access.

## Data model and assumptions

The current implementation intentionally keeps the simulation deterministic and evidence-based:

- production shock is applied as a percentage reduction to baseline production
- direct trade impacts are modeled using graph dependency weights
- temporal propagation is based on edge delay metadata and month-level activation
- alternate supply is modeled as a proportional offset to loss rather than as a guaranteed real-world intervention
- the system distinguishes modeled scenarios from observed forecast data
- supplier dependency shares and HHI are descriptive metrics calculated only from observed trade rows
- missing supplier observations remain incomplete coverage and are not converted to zero

Supported scenario types are `production_shock`, `supplier_disruption`, and `trade_disruption`.
`logistics_disruption` is typed but returns an explicit unsupported response until observed
route/port capacity data is available.

## Local setup

Backend:

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

## Firebase sign-in and deployment security

ATLAS uses Firebase Authentication with Google Sign-In. The browser obtains a Firebase
ID token and sends it as a Bearer token to FastAPI. `/health` remains public; scenario,
graph, data, export, and saved-scenario APIs require a verified Firebase token.

1. Create a Firebase project and register a Web app.
2. In **Authentication**, enable the Google provider.
3. Add local and production frontend hostnames under **Authorized domains**.
4. Configure the Firebase Admin SDK on the backend using either a service-account JSON
   value or Application Default Credentials. Never commit the credential.
5. Set the frontend variables:

Copy `frontend/.env.example` to `frontend/.env.local`, then replace the placeholders
with the values from the Firebase Web app configuration:

```text
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project
VITE_FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
VITE_API_URL=http://127.0.0.1:8000
```

Set the backend variables:

Copy `backend/.env.example` to a local environment file or set these variables in the
same terminal that starts Uvicorn. The service-account JSON must remain private:

```text
FIREBASE_ADMIN_CREDENTIALS_JSON=<service-account-json>
# Or use GOOGLE_APPLICATION_CREDENTIALS=/secure/path/service-account.json
ATLAS_FRONTEND_ORIGIN=http://127.0.0.1:5173
```

### Local startup after configuration

1. In Firebase Console, enable **Authentication > Sign-in method > Google**.
2. Under **Authentication > Settings > Authorized domains**, add `127.0.0.1` and
   `localhost` if they are not already present.
3. In the project root, start the backend with the backend variables loaded:

   ```powershell
   cd backend
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

   The backend automatically loads `backend/.env`. Set
   `GOOGLE_APPLICATION_CREDENTIALS` there to the private JSON file downloaded from
   Firebase. Alternatively, set `FIREBASE_ADMIN_CREDENTIALS_JSON` there instead.

4. In a second terminal, start the frontend:

   ```powershell
   cd frontend
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

5. Open `http://127.0.0.1:5173/` and select **Continue with Google**. Restart Vite
   after changing `.env.local`, because Vite reads environment variables at startup.

For production, use HTTPS, set `ATLAS_FRONTEND_ORIGIN` to the exact deployed frontend
origin, configure the production domain in Firebase Authorized domains, and provide the
Admin SDK credentials through the deployment secret manager. Firebase client sign-out
is performed by the frontend. Rate limiting is applied in memory to expensive scenario
endpoints; use a shared gateway or distributed limiter when running multiple processes.

## Environment variables

The frontend supports a `VITE_API_URL` environment variable when running in a non-default backend host/port. For example:

```bash
VITE_API_URL=http://127.0.0.1:8000
```

## API quick reference

- `GET /` - service metadata
- `GET /health` - health check
- `GET /api/graph` - graph payload
- `GET /api/graph/node/{node_id}` - graph node inspection
- `POST /api/scenario/run` - run scenario engine
- `POST /api/scenario/explain` - deterministic explanation package
- `POST /api/scenario/node/{node_id}` - node-specific scenario output
- `POST /api/scenario/export?format=json` - downloadable deterministic scenario JSON
- `POST /api/scenario/export?format=report` - downloadable human-readable scenario report
- `POST /api/scenario/compare` - compare two deterministic scenario runs
- `POST /api/scenarios` - save a named local scenario
- `GET /api/scenarios` and `GET /api/scenarios/{id}` - list or retrieve saved scenarios
- `POST /api/scenarios/{id}/run` - rerun a saved scenario
- `GET /api/data/dependencies?year=2024` - multi-year supplier dependency metrics
- `GET /api/data/provenance` - source metadata and reconciliation reports
- `GET /api/data/coverage` - current dataset, graph, and domain-layer coverage
- `GET /api/data/layers/{layer}` - climate, logistics, inputs, or energy availability
- `POST /auth/logout` - client-compatible logout acknowledgement
- `GET /api/auth/me` - current signed-in user

All `/api/*` routes require an `Authorization: Bearer <Firebase ID token>` header.
`/health` and `/` are public operational endpoints. The frontend obtains tokens through
Firebase's normal auth persistence and does not place them in URLs or local storage.

## Testing

Backend tests are in `backend/tests` and cover:

- graph integrity
- direct trade impact calculations
- temporal propagation logic
- API contracts
- invalid region handling
- cached acquisition and source validation
- malformed, duplicate, missing, zero, and negative data quality cases
- multi-year dependency shares and concentration
- supplier disruption and explicit unsupported scenario behavior
- domain-layer coverage and unavailable-data responses

## Known limitations

- the checked-in data is a bounded fixture subset, not a complete global historical archive
- the acquisition adapter is implemented but no live network download is performed automatically by the simulation
- route, port, climate, fertilizer, and energy datasets are not yet integrated
- temporal delays and price pressure are model assumptions, not empirical forecasts
- saved scenarios use a local JSON store under `backend/data/runtime/` and are intended for a single local MVP instance
- the explanation layer is deterministic and does not allow the LLM to fabricate numerical results
- exports contain the same backend simulation payload shown in the UI; they do not add forecasts

## Output classification

- **Observed data**: values loaded from the cited FAOSTAT and UN Comtrade fixtures or validated acquired files.
- **Derived metrics**: supplier shares, HHI, graph aggregations, and coverage reports calculated from observed rows.
- **Modeled output**: scenario shocks, temporal propagation, deficits, pressure indicators, and interventions.
- **Provisional/unavailable**: structural relationships or domain scenarios without validated observations. These are labeled and are not used to fabricate quantitative results.

## Completion status

### Core engine

Implemented and tested: observed fixture-backed wheat graph, deterministic production/supplier/trade
scenarios, temporal propagation, intervention comparison, dependency metrics, provenance, and
reconciliation reports.

### Domain coverage

Climate observations, route capacity, ports, fertilizer coefficients, and energy coefficients have
typed interfaces and explicit coverage endpoints, but are currently unavailable or provisional.
ATLAS does not fabricate these observations or use unsupported domain values in calculations.

### Responsible AI

ATLAS outputs are modeled scenarios, not guaranteed forecasts. Derived metrics describe observed
coverage; provisional edges and assumptions are labeled; missing data is not equivalent to zero;
and human review is required for policy decisions.

## Deployment notes

- FastAPI can be served via `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- the frontend should point to the deployed backend through `VITE_API_URL`
- no secrets or API keys are required for the default deterministic experience
