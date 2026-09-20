from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DEFAULT_STORE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "runtime"
    / "saved_scenarios.json"
)


def _store_path() -> Path:
    configured_path = os.environ.get("ATLAS_SCENARIO_STORE", "").strip()
    return Path(configured_path) if configured_path else DEFAULT_STORE


def _read() -> list[dict]:
    path = _store_path()
    if not path.exists():
        return []

    try:
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            return []
        value = json.loads(content)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Saved scenario store is unreadable.") from exc

    if not isinstance(value, list):
        raise RuntimeError("Saved scenario store has an invalid format.")

    if not all(isinstance(item, dict) for item in value):
        raise RuntimeError("Saved scenario store has invalid entries.")

    return value


def _write(items: list[dict]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    handle, temporary = tempfile.mkstemp(
        prefix="saved-scenarios-",
        suffix=".json",
        dir=path.parent,
    )

    try:
        with os.fdopen(handle, "w", encoding="utf-8") as output:
            json.dump(items, output, indent=2, sort_keys=True)
            output.write("\n")

        os.replace(temporary, path)

    except (OSError, TypeError, ValueError) as exc:
        try:
            os.unlink(temporary)
        except OSError:
            pass

        raise RuntimeError("Saved scenario store could not be written.") from exc


def list_saved_scenarios(owner_id: str) -> list[dict]:
    owner_id = owner_id.strip()
    if not owner_id:
        raise ValueError("owner_id is required")

    return [
        item
        for item in _read()
        if item.get("owner_id") == owner_id
    ]


def get_saved_scenario(
    scenario_id: str,
    owner_id: str,
) -> dict | None:
    owner_id = owner_id.strip()
    if not owner_id:
        raise ValueError("owner_id is required")

    return next(
        (
            item
            for item in _read()
            if item.get("id") == scenario_id
            and item.get("owner_id") == owner_id
        ),
        None,
    )


def save_scenario(
    name: str,
    scenario: dict,
    owner_id: str,
) -> dict:
    owner_id = owner_id.strip()
    if not owner_id:
        raise ValueError("owner_id is required")

    item = {
        "id": uuid4().hex,
        "owner_id": owner_id,
        "name": name.strip(),
        "scenario": scenario,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    items = _read()
    items.append(item)
    _write(items)

    return item