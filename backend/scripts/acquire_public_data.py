from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.acquisition import (  # noqa: E402
    AcquisitionError,
    acquire_cached_file,
    acquire_comtrade_preview,
    validate_comtrade_json,
)
from app.data.loaders import DATA_ROOT  # noqa: E402


DEFAULT_FAOSTAT_BULK_URL = (
    "https://bulks-faostat.fao.org/production/"
    "Crops_Livestock_E_All_Data_(Normalized).zip"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acquire versioned public ATLAS source artifacts without overwriting raw data."
    )
    subparsers = parser.add_subparsers(dest="source", required=True)

    faostat = subparsers.add_parser("faostat")
    faostat.add_argument("--url", default=os.environ.get("ATLAS_FAOSTAT_URL", DEFAULT_FAOSTAT_BULK_URL))
    faostat.add_argument(
        "--output",
        type=Path,
        default=DATA_ROOT / "raw" / "faostat" / "faostat-crops-livestock.zip",
    )
    faostat.add_argument("--version", default="unspecified")

    comtrade = subparsers.add_parser("comtrade")
    comtrade.add_argument("--reporter-code", type=int, required=True)
    comtrade.add_argument("--period", required=True, help="YYYY or YYYY,YYYY")
    comtrade.add_argument(
        "--output",
        type=Path,
        default=DATA_ROOT / "raw" / "comtrade" / "comtrade-hs1001-preview.json",
    )

    args = parser.parse_args()
    try:
        if args.source == "faostat":
            result = acquire_cached_file(
                url=args.url,
                raw_path=args.output,
                dataset_name="FAOSTAT Crops and livestock products",
                source_version=args.version,
                min_bytes=1024,
            )
            print(
                f"FAOSTAT artifact {result.retrieval_status}: "
                f"{result.raw_path} sha256={result.sha256}"
            )
            return

        result = acquire_comtrade_preview(
            raw_path=args.output,
            reporter_code=args.reporter_code,
            period=args.period,
        )
        rows = validate_comtrade_json(result.raw_path)
        print(
            f"Comtrade artifact {result.retrieval_status}: "
            f"{result.raw_path} rows={rows} sha256={result.sha256}"
        )
    except AcquisitionError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
