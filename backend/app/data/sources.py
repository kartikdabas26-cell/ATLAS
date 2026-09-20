from __future__ import annotations

from dataclasses import dataclass

from app.data.contracts import DataSource


@dataclass(frozen=True)
class SourceDefinition:
    name: DataSource
    description: str
    url: str
    expected_data: tuple[str, ...]


FAO_SOURCE = SourceDefinition(
    name=DataSource.FAO,
    description="Food and agriculture statistics used for production data.",
    url="https://www.fao.org/faostat/",
    expected_data=(
        "wheat production",
        "agricultural production",
        "regional production",
    ),
)


UN_COMTRADE_SOURCE = SourceDefinition(
    name=DataSource.UN_COMTRADE,
    description="International trade statistics used for wheat import/export data.",
    url="https://comtradeplus.un.org/",
    expected_data=(
        "wheat imports",
        "wheat exports",
        "trade flows",
        "reporting country",
        "partner country",
    ),
)


NOAA_SOURCE = SourceDefinition(
    name=DataSource.NOAA,
    description="Climate and environmental datasets reserved for later ATLAS phases.",
    url="https://www.noaa.gov/",
    expected_data=(
        "climate observations",
        "weather data",
    ),
)


ATLAS_DEMO_SOURCE = SourceDefinition(
    name=DataSource.ATLAS_DEMO,
    description="Provisional demonstration inputs used while real public data is being integrated.",
    url="",
    expected_data=(
        "demo production",
        "demo imports",
        "demo exports",
    ),
)


SOURCE_REGISTRY: dict[DataSource, SourceDefinition] = {
    DataSource.FAO: FAO_SOURCE,
    DataSource.UN_COMTRADE: UN_COMTRADE_SOURCE,
    DataSource.NOAA: NOAA_SOURCE,
    DataSource.ATLAS_DEMO: ATLAS_DEMO_SOURCE,
}


def get_source(source: DataSource) -> SourceDefinition:
    """Return the registered definition for an ATLAS data source."""
    try:
        return SOURCE_REGISTRY[source]
    except KeyError as exc:
        raise ValueError(f"Unknown ATLAS data source: {source}") from exc


def list_sources() -> list[SourceDefinition]:
    """Return all registered ATLAS data sources."""
    return list(SOURCE_REGISTRY.values())