from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.data.contracts import DataBundle, MetricType


def _trade_records(bundle: DataBundle, year: int) -> list[Any]:
    return [
        record
        for record in bundle.records
        if record.reference_year == year
        and record.metric in {MetricType.IMPORTS, MetricType.EXPORTS}
        and record.partner_region
        and record.unit == "USD"
    ]


def calculate_importer_dependencies(
    bundle: DataBundle,
    year: int,
    production_bundle: DataBundle | None = None,
) -> list[dict[str, Any]]:
    """Calculate descriptive supplier shares and HHI from observed trade values.

    Missing supplier-partner observations are not converted to zero. The result reports only
    observed records and explicitly marks coverage as incomplete when a bundle is provisional.
    """

    by_importer: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for record in _trade_records(bundle, year):
        if record.flow and record.flow.lower() == "export":
            by_importer[record.partner_region or ""][record.region_name] += float(record.value)

    metrics: list[dict[str, Any]] = []
    for importer, suppliers in sorted(by_importer.items()):
        total = sum(suppliers.values())
        shares = {
            supplier: round(value / total, 6)
            for supplier, value in suppliers.items()
        } if total else {}
        hhi = round(sum(share * share for share in shares.values()), 6)
        ranked = sorted(shares.items(), key=lambda item: (-item[1], item[0]))
        metrics.append(
            {
                "importer": importer,
                "year": year,
                "total_import_value_usd": round(total, 2),
                "imports_by_supplier_usd": {
                    supplier: round(suppliers[supplier], 2)
                    for supplier in sorted(suppliers)
                },
                "supplier_dependency_share": shares,
                "supplier_concentration_hhi": hhi,
                "top_suppliers": [
                    {"supplier": supplier, "share": share}
                    for supplier, share in ranked[:5]
                ],
                "active_supplier_count": len(suppliers),
                "production_baseline": _production_baseline(
                    production_bundle, importer, year
                ),
                "missing_supplier_data": bundle.source_status.value != "observed",
                "source": bundle.dataset_metadata.model_dump()
                if bundle.dataset_metadata
                else None,
                "coverage": "observed_records_only",
                "methodology": "Supplier share = observed supplier trade value / observed importer supplier total; HHI = sum of squared shares.",
                "status": "observed" if bundle.source_status.value == "observed" else "provisional",
            }
        )
    return metrics


def calculate_multi_year_dependencies(
    bundle: DataBundle,
    years: list[int] | None = None,
    production_bundle: DataBundle | None = None,
) -> list[dict[str, Any]]:
    available_years = sorted(
        {record.reference_year for record in bundle.records}
        if years is None
        else set(years)
    )
    result: list[dict[str, Any]] = []
    previous: dict[str, dict[str, Any]] = {}
    for year in available_years:
        current = calculate_importer_dependencies(bundle, year, production_bundle)
        for metric in current:
            previous_metric = previous.get(metric["importer"])
            metric["year_over_year"] = None
            if previous_metric:
                old_total = previous_metric["total_import_value_usd"]
                metric["year_over_year"] = {
                    "total_import_value_change_usd": round(
                        metric["total_import_value_usd"] - old_total, 2
                    ),
                    "total_import_value_change_percent": round(
                        ((metric["total_import_value_usd"] - old_total) / old_total) * 100,
                        2,
                    ) if old_total else None,
                }
            previous[metric["importer"]] = metric
            result.append(metric)
    return result


def _production_baseline(
    bundle: DataBundle | None,
    country: str,
    year: int,
) -> dict[str, Any] | None:
    if bundle is None:
        return None
    records = [
        record
        for record in bundle.records
        if record.region_name == country
        and record.reference_year == year
        and record.metric == MetricType.PRODUCTION
        and record.unit == "tonnes"
        and record.notes is None
    ]
    if not records:
        return None
    record = records[0]
    return {
        "value": record.value,
        "unit": record.unit,
        "source": record.source.value,
        "status": record.status.value,
    }
