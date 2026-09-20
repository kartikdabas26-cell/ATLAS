from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from app.data.contracts import (
    DataBundle,
    DataQualityReport,
    DataSource,
    DataStatus,
    DatasetMetadata,
    MetricType,
    RegionData,
    TradeRecord,
)

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"


def normalize_country_name(value: str | None) -> str:
    if value is None:
        return ""

    cleaned = value.strip()
    aliases = {
        "United States of America": "United States",
        "USA": "United States",
        "Czechia": "Czech Republic",
        "Russian Federation": "Russia",
        "Bosnia and Herz.": "Bosnia and Herzegovina",
    }
    return aliases.get(cleaned, cleaned)


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None

    cleaned = value.strip()
    if cleaned == "" or cleaned.lower() in {"na", "n/a", "null", "none"}:
        return None

    return float(cleaned.replace(",", ""))


def validate_records(records: Iterable[TradeRecord]) -> list[TradeRecord]:
    validated: list[TradeRecord] = []

    for record in records:
        if record.value < 0:
            raise ValueError(
                f"Negative value is not allowed for {record.metric.value}: "
                f"{record.region_name}"
            )
        validated.append(record)

    return validated


def build_data_bundle(
    records: Iterable[TradeRecord],
    *,
    commodity: str = "wheat",
    reference_year: int,
    source_status: DataStatus = DataStatus.OBSERVED,
    dataset_metadata: DatasetMetadata | None = None,
    quality_report: DataQualityReport | None = None,
) -> DataBundle:
    validated_records = validate_records(records)

    return DataBundle(
        commodity=commodity,
        reference_year=reference_year,
        records=validated_records,
        source_status=source_status,
        dataset_metadata=dataset_metadata,
        quality_report=quality_report or DataQualityReport(),
    )


def region_to_records(region: RegionData) -> list[TradeRecord]:
    records: list[TradeRecord] = []

    for metric_name, value in (
        ("production", region.production),
        ("imports", region.imports),
        ("exports", region.exports),
    ):
        if value is None:
            continue

        records.append(
            TradeRecord(
                region_id=region.region_id,
                region_name=region.region_name,
                commodity="wheat",
                metric=metric_name,
                value=value,
                unit=region.unit,
                reference_year=region.reference_year,
                source=region.source,
                status=region.status,
                source_reference=region.source_reference,
            )
        )

    return records


def _default_faostat_metadata(reference_year: int) -> DatasetMetadata:
    return DatasetMetadata(
        source_organization="FAOSTAT",
        dataset_name="Crops and livestock products",
        url="https://www.fao.org/faostat/en/#data/QCL",
        retrieval_date="2025-01-01",
        retrieval_status="local_fixture",
        source_version="2024-fixture",
        reference_year=reference_year,
        geographic_coverage="global",
        units="tonnes",
        methodology_notes="Production values are normalized as wheat production quantity in tonnes for the selected reference year.",
        limitations="This fixture captures a subset of public FAOSTAT wheat data for deterministic repository testing.",
    )


def _default_comtrade_metadata(reference_year: int) -> DatasetMetadata:
    return DatasetMetadata(
        source_organization="UN Comtrade",
        dataset_name="HS1001 Wheat and meslin",
        url="https://comtradeplus.un.org/",
        retrieval_date="2025-01-01",
        retrieval_status="local_fixture",
        source_version="2024-fixture",
        reference_year=reference_year,
        geographic_coverage="global",
        units="USD and kg",
        methodology_notes="Trade flows are normalized to exporter-to-partner wheat trade records with value and quantity preserved separately.",
        limitations="This fixture is a deterministic, local subset of public trade data and does not replace a full live Comtrade export.",
    )


def load_faostat_production_csv(path: Path) -> DataBundle:
    if not path.exists():
        raise FileNotFoundError(f"Missing FAOSTAT fixture: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"country", "year", "production_tonnes"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"FAOSTAT fixture is missing required columns: {sorted(required)}")

        records: list[TradeRecord] = []
        quality = DataQualityReport(row_count=0)
        seen: set[tuple[str, int]] = set()

        for row in reader:
            if not row or not any((value or "").strip() for value in row.values()):
                continue

            quality.row_count += 1
            country = normalize_country_name(row.get("country"))
            try:
                year = int((row.get("year") or "").strip())
            except ValueError:
                quality.invalid_years.append(-1)
                quality.rejected_rows += 1
                quality.warnings.append(f"Malformed year at row {quality.row_count}")
                continue
            try:
                production = parse_float(row.get("production_tonnes"))
                harvested = parse_float(row.get("harvested_area_ha"))
                yield_value = parse_float(row.get("yield_kg_ha"))
            except ValueError as exc:
                quality.rejected_rows += 1
                quality.warnings.append(
                    f"Malformed numeric value at row {quality.row_count}: {exc}"
                )
                continue

            if not country:
                quality.missing_values.append(f"row {quality.row_count}: country")
                quality.rejected_rows += 1
                continue
            if not 1900 <= year <= 2100:
                quality.invalid_years.append(year)
                quality.rejected_rows += 1
                continue

            if production is None:
                quality.missing_values.append(f"row {quality.row_count}: production_tonnes")
            if production is not None and production < 0:
                quality.negative_values.append(f"{country}:{year}")
                quality.rejected_rows += 1
                continue
            if production == 0:
                quality.zero_values.append(f"{country}:{year}:production")

            key = (country, year)
            if key in seen:
                quality.duplicate_rows += 1
                quality.warnings.append(f"Duplicate FAOSTAT row for {country} in {year}")
                quality.rejected_rows += 1
                continue
            seen.add(key)
            quality.accepted_rows += 1
            quality.normalized_countries.append(country)
            quality.year_min = year if quality.year_min is None else min(quality.year_min, year)
            quality.year_max = year if quality.year_max is None else max(quality.year_max, year)
            quality.commodity_coverage.append("wheat")

            if production is not None:
                records.append(
                    TradeRecord(
                        region_id=country.lower().replace(" ", "_"),
                        region_name=country,
                        commodity="wheat",
                        metric=MetricType.PRODUCTION,
                        value=float(production),
                        unit="tonnes",
                        reference_year=year,
                        source=DataSource.FAO,
                        status=DataStatus.OBSERVED,
                        source_reference=str(path),
                    )
                )

            if harvested is not None:
                records.append(
                    TradeRecord(
                        region_id=country.lower().replace(" ", "_"),
                        region_name=country,
                        commodity="wheat",
                        metric=MetricType.PRODUCTION,
                        value=float(harvested),
                        unit="hectares",
                        reference_year=year,
                        source=DataSource.FAO,
                        status=DataStatus.OBSERVED,
                        source_reference=str(path),
                        notes="harvested_area_ha",
                    )
                )

            if yield_value is not None:
                records.append(
                    TradeRecord(
                        region_id=country.lower().replace(" ", "_"),
                        region_name=country,
                        commodity="wheat",
                        metric=MetricType.PRODUCTION,
                        value=float(yield_value),
                        unit="kg_ha",
                        reference_year=year,
                        source=DataSource.FAO,
                        status=DataStatus.OBSERVED,
                        source_reference=str(path),
                        notes="yield_kg_ha",
                    )
                )

    ref_year = max((int(r.reference_year) for r in records), default=2024)
    return build_data_bundle(
        records,
        commodity="wheat",
        reference_year=ref_year,
        source_status=DataStatus.OBSERVED,
        dataset_metadata=_default_faostat_metadata(ref_year),
        quality_report=quality,
    )


def load_comtrade_trade_csv(path: Path) -> DataBundle:
    if not path.exists():
        raise FileNotFoundError(f"Missing Comtrade fixture: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"reporter", "partner", "year", "flow", "commodity_code", "trade_value_usd", "quantity_kg"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"Comtrade fixture is missing required columns: {sorted(required)}")

        quality = DataQualityReport(row_count=0)
        records: list[TradeRecord] = []
        seen: set[tuple[str, str, int, str, str]] = set()

        for row in reader:
            if not row or not any((value or "").strip() for value in row.values()):
                continue

            quality.row_count += 1
            reporter = normalize_country_name(row.get("reporter"))
            partner = normalize_country_name(row.get("partner"))
            try:
                year = int((row.get("year") or "").strip())
                value_usd = parse_float(row.get("trade_value_usd"))
                quantity_kg = parse_float(row.get("quantity_kg"))
            except ValueError as exc:
                quality.rejected_rows += 1
                quality.warnings.append(
                    f"Malformed trade value at row {quality.row_count}: {exc}"
                )
                continue
            flow = (row.get("flow") or "").strip()

            if not reporter or not partner:
                quality.missing_values.append(f"row {quality.row_count}: reporter/partner")
                quality.rejected_rows += 1
                continue
            if not 1900 <= year <= 2100:
                quality.invalid_years.append(year)
                quality.rejected_rows += 1
                continue
            if value_usd is not None and value_usd < 0:
                quality.negative_values.append(f"{reporter}->{partner}:{year}")
                quality.rejected_rows += 1
                continue
            if value_usd == 0 or quantity_kg == 0:
                quality.zero_values.append(f"{reporter}->{partner}:{year}")
            if quantity_kg is not None and quantity_kg < 0:
                quality.negative_values.append(f"{reporter}->{partner}:{year}:quantity")
                quality.rejected_rows += 1
                continue
            if value_usd is None and quantity_kg is None:
                quality.missing_values.append(
                    f"row {quality.row_count}: trade_value_usd/quantity_kg"
                )
                quality.rejected_rows += 1
                continue

            key = (reporter, partner, year, flow, row.get("commodity_code") or "")
            if key in seen:
                quality.duplicate_rows += 1
                quality.warnings.append(f"Duplicate trade row for {reporter}->{partner} in {year}")
                quality.rejected_rows += 1
                continue
            seen.add(key)
            if not flow:
                quality.missing_values.append(f"row {quality.row_count}: flow")
                quality.rejected_rows += 1
                continue
            quality.accepted_rows += 1
            quality.normalized_countries.extend((reporter, partner))
            quality.year_min = year if quality.year_min is None else min(quality.year_min, year)
            quality.year_max = year if quality.year_max is None else max(quality.year_max, year)
            quality.commodity_coverage.append(row.get("commodity_code") or "unknown")

            if value_usd is not None:
                metric = MetricType.EXPORTS if flow.lower() == "export" else MetricType.IMPORTS
                records.append(
                    TradeRecord(
                        region_id=reporter.lower().replace(" ", "_"),
                        region_name=reporter,
                        commodity="wheat",
                        metric=metric,
                        value=float(value_usd),
                        unit="USD",
                        reference_year=year,
                        source=DataSource.UN_COMTRADE,
                        status=DataStatus.OBSERVED,
                        source_reference=str(path),
                        notes=f"flow={flow};partner={partner};commodity_code={row.get('commodity_code')}",
                        partner_region=partner,
                        flow=flow,
                    )
                )

            if quantity_kg is not None:
                records.append(
                    TradeRecord(
                        region_id=reporter.lower().replace(" ", "_"),
                        region_name=reporter,
                        commodity="wheat",
                        metric=MetricType.EXPORTS if flow.lower() == "export" else MetricType.IMPORTS,
                        value=float(quantity_kg),
                        unit="kg",
                        reference_year=year,
                        source=DataSource.UN_COMTRADE,
                        status=DataStatus.OBSERVED,
                        source_reference=str(path),
                        notes=f"flow={flow};partner={partner};quantity_kg",
                        partner_region=partner,
                        flow=flow,
                    )
                )

    ref_year = max((int(record.reference_year) for record in records), default=2024)
    return build_data_bundle(
        records,
        commodity="wheat",
        reference_year=ref_year,
        source_status=DataStatus.PROVISIONAL,
        dataset_metadata=_default_comtrade_metadata(ref_year),
        quality_report=quality,
    )


def demo_wheat_bundle(reference_year: int = 2025) -> DataBundle:
    records = [
        TradeRecord(
            region_id="europe",
            region_name="Europe",
            metric="production",
            value=150.0,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="europe",
            region_name="Europe",
            metric="exports",
            value=60.0,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="russia",
            region_name="Russia",
            metric="production",
            value=85.0,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="russia",
            region_name="Russia",
            metric="exports",
            value=45.0,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="canada",
            region_name="Canada",
            metric="production",
            value=35.0,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="canada",
            region_name="Canada",
            metric="exports",
            value=25.0,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="egypt",
            region_name="Egypt",
            metric="production",
            value=9.0,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="egypt",
            region_name="Egypt",
            metric="imports",
            value=12.0,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="morocco",
            region_name="Morocco",
            metric="production",
            value=7.5,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="morocco",
            region_name="Morocco",
            metric="imports",
            value=8.0,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="algeria",
            region_name="Algeria",
            metric="production",
            value=3.5,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
        TradeRecord(
            region_id="algeria",
            region_name="Algeria",
            metric="imports",
            value=9.0,
            unit="million tonnes",
            reference_year=reference_year,
            source=DataSource.ATLAS_DEMO,
            status=DataStatus.PROVISIONAL,
            source_reference="ATLAS demo graph",
        ),
    ]

    return build_data_bundle(
        records,
        commodity="wheat",
        reference_year=reference_year,
        source_status=DataStatus.PROVISIONAL,
    )