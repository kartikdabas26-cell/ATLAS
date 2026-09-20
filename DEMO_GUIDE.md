# ATLAS demo guide

1. Start the backend with `cd backend; uvicorn app.main:app --reload`.
2. Start the frontend with `cd frontend; npm run dev`.
3. Run the default Europe production-shock scenario and inspect the timeline and Butterfly Map.
4. Review the observed supplier concentration cards and the provenance/uncertainty section.
5. Use **Export JSON** for machine-readable output or **Export report** for a text summary.
6. Try a logistics, climate, input, or energy scenario through the API to see the explicit unavailable response; do not infer a numerical result for those domains.

The checked-in datasets are reproducible fixtures. Run the acquisition and ingestion commands in `README.md` when testing a refreshed source artifact.
