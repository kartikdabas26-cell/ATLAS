from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.data.comtrade import ComtradeTradeRecord


def load_comtrade_csv(path: str | Path) -> list[ComtradeTradeRecord]:
    csv_path = Path(path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Comtrade file not found: {csv_path}")

    frame = pd.read_csv(csv_path)

    required_columns = {
        "year",
        "commodity_code",
        "commodity",
        "producer",
        "importer",
        "producer_code",
        "importer_code",
        "primary_value",
        "net_weight",
        "is_reported",
        "is_aggregate",
    }

    missing = required_columns - set(frame.columns)

    if missing:
        raise ValueError(
            f"Missing required Comtrade columns: {sorted(missing)}"
        )

    records: list[ComtradeTradeRecord] = []

    for row in frame.to_dict(orient="records"):
        net_weight = row["net_weight"]

        if pd.isna(net_weight):
            net_weight = None

        records.append(
            ComtradeTradeRecord(
                year=int(row["year"]),
                commodity_code=str(row["commodity_code"]),
                commodity=str(row["commodity"]),
                producer=str(row["producer"]),
                importer=str(row["importer"]),
                producer_code=int(row["producer_code"]),
                importer_code=int(row["importer_code"]),
                primary_value=float(row["primary_value"]),
                net_weight=net_weight,
                is_reported=bool(row["is_reported"]),
                is_aggregate=bool(row["is_aggregate"]),
            )
        )

    return records
