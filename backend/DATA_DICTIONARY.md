# ATLAS data dictionary

## Data categories

- **Observed source data**: values directly reported by FAOSTAT or UN Comtrade.
- **Derived metrics**: normalized country identifiers, supplier shares, HHI, and dependency weights calculated from observed rows.
- **Modeled scenario output**: production loss, deficit indicators, price-pressure indicators, timelines, intervention effects, and risk classes.
- **Provisional assumptions**: propagation delays, price-pressure coefficient, and alternate-supply offsets.

## Normalized records

`TradeRecord` preserves:

- `region_name` and normalized `region_id`
- `partner_region` for bilateral trade
- `flow` (`Export` or `Import`)
- `reference_year`
- `commodity`
- `metric`
- `value` and `unit`
- source and status
- source reference and notes

Trade value in USD and physical quantity in kg are separate records. A missing value is
not converted into zero. A reported zero remains a zero-valued observed record.

## Dependency metrics

For each importer and year:

- `total_import_value_usd`: sum of observed exporter values
- `imports_by_supplier_usd`: observed supplier values
- `supplier_dependency_share`: supplier value divided by observed importer total
- `supplier_concentration_hhi`: sum of squared supplier shares
- `top_suppliers`: descending supplier shares
- `active_supplier_count`: number of observed suppliers
- `missing_supplier_data`: true for provisional/incomplete bundle coverage

These are descriptive observed-data metrics, not forecasts.

## Scenario comparison and saved scenarios

`POST /api/scenario/compare` runs `scenario_a` and `scenario_b` independently and exposes
their actual model summaries: affected node IDs, total supply loss, average deficit,
average modeled price pressure, risk, active cascade pathways, intervention effect, and
provenance. It does not create a composite score.

Saved scenarios contain only a user-provided name, validated scenario parameters, an opaque
ID, and a UTC creation timestamp. The local JSON store is an MVP persistence mechanism and
is not a multi-user database.

## Provenance

Acquired raw artifacts use a sidecar JSON file containing source URL, retrieval timestamp,
query parameters, source version, retrieval status, and SHA-256 checksum. Raw artifacts
are never overwritten by the acquisition adapter.
