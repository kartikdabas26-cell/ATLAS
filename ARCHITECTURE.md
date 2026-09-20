# ATLAS architecture

ATLAS has four deliberately separated layers:

1. **Acquisition and raw data** (`backend/app/data/acquisition.py`, `backend/data/raw/`) cache source artifacts and sidecar provenance without silently overwriting files.
2. **Normalization and reconciliation** (`backend/app/data/loaders.py`) validate identifiers, years, units, duplicates, missing values, and negative values. Rejected rows remain visible in quality reports.
3. **Observed graph and derived metrics** (`backend/app/graph/builder.py`, `backend/app/data/dependency.py`) build production nodes and observed country-level trade edges. Europe aggregate edges are derived and excluded from quantitative exposure.
4. **Deterministic simulation and explanation** (`backend/app/simulation/engine.py`, `backend/app/explanation/builder.py`) calculate scenario outputs, timelines, provenance, and a non-generative explanation of those outputs.

The FastAPI layer is the contract boundary. The React frontend consumes it and does not independently calculate scenario impacts.

Named scenarios are persisted through the small atomic JSON store in
`backend/data/runtime/` (configurable with `ATLAS_SCENARIO_STORE`). The comparison endpoint
runs two validated requests through the same engine and returns the original results plus
model-derived summary fields.
