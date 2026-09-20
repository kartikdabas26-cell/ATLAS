from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data.loaders import DATA_ROOT, load_comtrade_trade_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize UN Comtrade wheat trade fixture data")
    parser.add_argument("--input", type=Path, default=DATA_ROOT / "raw" / "comtrade" / "wheat-global-trade.csv")
    parser.add_argument("--output", type=Path, default=DATA_ROOT / "processed" / "comtrade-wheat-trade.json")
    args = parser.parse_args()

    bundle = load_comtrade_trade_csv(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    print(f"Normalized {len(bundle.records)} Comtrade wheat records to {args.output}")


if __name__ == "__main__":
    main()
