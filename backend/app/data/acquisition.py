from __future__ import annotations

import hashlib
import json
import random
import time
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AcquisitionError(RuntimeError):
    """Raised when a source cannot be safely acquired or validated."""


@dataclass(frozen=True)
class AcquisitionResult:
    raw_path: Path
    metadata_path: Path
    sha256: str
    retrieval_status: str
    from_cache: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _metadata_path(raw_path: Path) -> Path:
    return raw_path.with_suffix(raw_path.suffix + ".metadata.json")


def _validate_payload(path: Path, *, minimum_bytes: int = 32) -> None:
    if not path.exists() or not path.is_file():
        raise AcquisitionError(f"Downloaded source file does not exist: {path}")
    if path.stat().st_size < minimum_bytes:
        raise AcquisitionError(f"Downloaded source file is unexpectedly small: {path}")


def acquire_cached_file(
    *,
    url: str,
    raw_path: Path,
    dataset_name: str,
    query_parameters: dict[str, str | int | float] | None = None,
    source_version: str | None = None,
    timeout_seconds: float = 30.0,
    retries: int = 3,
    min_bytes: int = 32,
    expected_sha256: str | None = None,
    user_agent: str = "ATLAS-data-acquirer/1.0",
) -> AcquisitionResult:
    """Acquire a source file without overwriting an existing raw artifact.

    The cache is used first. A failed network attempt never replaces a valid cached file.
    Raw files are immutable by default: reusing a filename with different content requires
    the caller to choose a new versioned path.
    """

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = _metadata_path(raw_path)

    if raw_path.exists():
        _validate_payload(raw_path, minimum_bytes=min_bytes)
        digest = sha256_file(raw_path)
        if expected_sha256 and digest != expected_sha256:
            raise AcquisitionError(
                f"Cached checksum mismatch for {raw_path}: expected {expected_sha256}, got {digest}"
            )
        return AcquisitionResult(
            raw_path=raw_path,
            metadata_path=metadata_path,
            sha256=digest,
            retrieval_status="cached",
            from_cache=True,
        )

    request = Request(url, headers={"User-Agent": user_agent, "Accept": "*/*"})
    last_error: Exception | None = None

    for attempt in range(max(1, retries)):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload = response.read()
            if len(payload) < min_bytes:
                raise AcquisitionError(f"Source response is unexpectedly small: {url}")

            temporary_path = raw_path.with_suffix(raw_path.suffix + ".part")
            temporary_path.write_bytes(payload)
            _validate_payload(temporary_path, minimum_bytes=min_bytes)
            digest = sha256_file(temporary_path)
            if expected_sha256 and digest != expected_sha256:
                temporary_path.unlink(missing_ok=True)
                raise AcquisitionError(
                    f"Downloaded checksum mismatch: expected {expected_sha256}, got {digest}"
                )
            temporary_path.replace(raw_path)

            metadata = {
                "source_organization": "official public source",
                "dataset_name": dataset_name,
                "url": url,
                "retrieval_timestamp": datetime.now(UTC).isoformat(),
                "source_version": source_version,
                "query_parameters": query_parameters or {},
                "sha256": digest,
                "retrieval_status": "downloaded",
            }
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            return AcquisitionResult(
                raw_path=raw_path,
                metadata_path=metadata_path,
                sha256=digest,
                retrieval_status="downloaded",
                from_cache=False,
            )
        except (HTTPError, URLError, TimeoutError, OSError, AcquisitionError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(min(2**attempt + random.random(), 4.0))

    raise AcquisitionError(f"Unable to acquire {dataset_name} from {url}: {last_error}")


def acquire_comtrade_preview(
    *,
    raw_path: Path,
    reporter_code: int,
    period: str,
    partner_code: int = 0,
    max_records: int = 500,
    timeout_seconds: float = 30.0,
) -> AcquisitionResult:
    """Acquire one deterministic UN Comtrade HS1001 preview response.

    The endpoint is public and credential-free. The response is stored as raw JSON with
    the exact query recorded in sidecar metadata. Larger downloads should be paginated by
    callers using separate versioned raw paths.
    """

    url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
    query = {
        "reporterCode": reporter_code,
        "period": period,
        "cmdCode": "1001",
        "partnerCode": partner_code,
        "flowCode": "M,X",
        "motCode": 0,
        "maxRecords": max_records,
        "aggregateBy": "cmdCode",
    }
    query_string = "&".join(f"{key}={value}" for key, value in query.items())
    return acquire_cached_file(
        url=f"{url}?{query_string}",
        raw_path=raw_path,
        dataset_name="UN Comtrade HS1001 wheat preview",
        query_parameters=query,
        source_version=period,
        timeout_seconds=timeout_seconds,
        min_bytes=64,
    )


def load_acquisition_metadata(path: Path) -> dict[str, object]:
    metadata_path = _metadata_path(path)
    if not metadata_path.exists():
        raise AcquisitionError(f"Missing acquisition metadata sidecar: {metadata_path}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def validate_csv_columns(path: Path, required_columns: set[str]) -> list[str]:
    """Validate a downloaded CSV before any normalization is attempted."""

    _validate_payload(path, minimum_bytes=1)
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            fieldnames = csv.DictReader(handle).fieldnames
    except (OSError, UnicodeError, csv.Error) as exc:
        raise AcquisitionError(f"Malformed CSV source file {path}: {exc}") from exc
    if not fieldnames:
        raise AcquisitionError(f"CSV source file has no header: {path}")
    missing = sorted(required_columns.difference(fieldnames))
    if missing:
        raise AcquisitionError(
            f"CSV source file {path} is missing required columns: {missing}"
        )
    return fieldnames


def validate_comtrade_json(path: Path) -> int:
    """Validate the public Comtrade response envelope before transformation."""

    _validate_payload(path, minimum_bytes=1)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcquisitionError(f"Malformed Comtrade JSON source file {path}: {exc}") from exc
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise AcquisitionError("Comtrade response does not contain a data list")
    return len(rows)
