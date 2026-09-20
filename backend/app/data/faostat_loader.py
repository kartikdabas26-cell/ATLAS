from __future__ import annotations

from pathlib import Path

import pandas as pd


FAOSTAT_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "raw"
    / "faostat"
    / "wheat-production.csv"
)


def load_faostat_wheat_production(
    path: str | Path = FAOSTAT_PATH,
    year: int = 2024,
) -> list[dict]:
    """
    Load observed FAOSTAT wheat production for a specific year.

    Values are kept in tonnes and the original FAOSTAT production flag
    is preserved rather than interpreted or discarded.
    """

    csv_path = Path(path)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"FAOSTAT wheat production file not found: {csv_path}"
        )

    frame = pd.read_csv(csv_path)

    required_columns = {
        "country_name_en",
        "year",
        "production_tonnes",
        "production_tonnes_flag",
    }

    missing = required_columns - set(frame.columns)

    if missing:
        raise ValueError(
            f"Missing required FAOSTAT columns: {sorted(missing)}"
        )

    selected = frame[frame["year"] == year].copy()

    records: list[dict] = []

    for row in selected.to_dict(orient="records"):
        production = row["production_tonnes"]

        if pd.isna(production):
            continue

        flag = row["production_tonnes_flag"]

        if pd.isna(flag):
            flag = None

        records.append(
            {
                "country_name": str(row["country_name_en"]),
                "year": int(row["year"]),
                "production_tonnes": float(production),
                "production_flag": (
                    str(flag) if flag is not None else None
                ),
                "data_source": "FAOSTAT",
                "data_status": "observed",
            }
        )

    return records


def build_production_lookup(
    path: str | Path = FAOSTAT_PATH,
    year: int = 2024,
) -> dict[str, dict]:
    """
    Return FAOSTAT production indexed by normalized country name.
    """

    records = load_faostat_wheat_production(
        path=path,
        year=year,
    )

    lookup: dict[str, dict] = {}

    for record in records:
        key = record["country_name"].strip().lower()

        lookup[key] = record

    return lookup