from __future__ import annotations

from pathlib import Path

from app.data.comtrade_loader import load_comtrade_csv


COMTRADE_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "raw"
    / "comtrade"
    / "wheat-europe-north-africa-2024.csv"
)


def load_real_trade_records():
    """
    Load the verified 2024 UN Comtrade bilateral wheat trade records.
    """

    return load_comtrade_csv(COMTRADE_PATH)


def build_trade_edges():
    """
    Convert Comtrade records into ATLAS knowledge-graph edges.

    The graph source/target are country IDs.
    Data provenance remains in data_source.
    """

    records = load_real_trade_records()

    edges = []

    for record in records:
        source = (
            record.producer
            .strip()
            .lower()
            .replace(" ", "_")
        )

        target = (
            record.importer
            .strip()
            .lower()
            .replace(" ", "_")
        )

        edges.append(
            {
                "source": source,
                "target": target,
                "relationship": "SUPPLIES_TO",
                "commodity": record.commodity,
                "commodity_code": record.commodity_code,
                "year": record.year,
                "trade_value": record.primary_value,
                "net_weight": record.net_weight,
                "source_name": record.source,
                "status": record.status,
                "is_reported": record.is_reported,
                "is_aggregate": record.is_aggregate,
            }
        )

    return edges