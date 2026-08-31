"""Offline owner entry point for adopting the authorized germanium artifact.

This module never downloads. It copies one exact, hash-verified custody artifact
into isolated connector raw storage and then records the truthful carrier/intake
rows. Importing it has no side effects.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.engine import Connection, Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import (  # noqa: E402
    _path_inside_repo_or_onedrive,
    _sqlite_database_path,
    settings,
)
from app.db.session import SessionLocal  # noqa: E402
from app.models.models import ConnectorRun, ConnectorRunTarget, uuid_str  # noqa: E402
from app.services.layer3_connector_source_intake import (  # noqa: E402
    ADOPTED_EXTERNAL_ACQUIRED_AT,
    ADOPTED_EXTERNAL_ACQUISITION_GIT_REF,
    ADOPTED_EXTERNAL_ACQUISITION_RECORD_PATH,
    ADOPTED_EXTERNAL_ACQUISITION_RECORD_SHA256,
    ADOPTED_EXTERNAL_ARTIFACT_BYTES,
    ADOPTED_EXTERNAL_ARTIFACT_SHA256,
    ADOPTED_EXTERNAL_CONNECTOR_KEY,
    ADOPTED_EXTERNAL_DOI,
    ADOPTED_EXTERNAL_DOWNLOAD_URI,
    ADOPTED_EXTERNAL_FILENAME,
    ADOPTED_EXTERNAL_ITEM_ID,
    ADOPTED_EXTERNAL_SOURCE_INTAKE_OPERATOR_DECISION,
    ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY,
    ADOPTED_EXTERNAL_SOURCE_MODE,
    ConnectorSourceIntakeError,
    adopted_external_provenance,
    record_adopted_external_source_intake,
)


ACQUISITION_RECORD_PATH = ADOPTED_EXTERNAL_ACQUISITION_RECORD_PATH
ACQUISITION_RECORD_SHA256 = ADOPTED_EXTERNAL_ACQUISITION_RECORD_SHA256
EXPECTED_ACQUISITION_RECORD_SHA256 = ADOPTED_EXTERNAL_ACQUISITION_RECORD_SHA256
ARTIFACT_SHA256 = ADOPTED_EXTERNAL_ARTIFACT_SHA256
EXPECTED_ARTIFACT_SHA256 = ADOPTED_EXTERNAL_ARTIFACT_SHA256
EXACT_MIRROR_RUN = "20260830T170556947Z-c0f90bb45a294d1bb84fe3c9855b7fce"
EXPECTED_FINALIZED_NAME = (
    "mcs2023-germa_salient."
    f"{ADOPTED_EXTERNAL_ARTIFACT_SHA256}.csv"
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_relative_path(value: str) -> Path:
    requested = Path(str(value).replace("\\", "/"))
    if (
        requested.is_absolute()
        or ".." in requested.parts
        or requested.as_posix() != ACQUISITION_RECORD_PATH
    ):
        raise RuntimeError("Unsafe or non-authorized acquisition record path.")
    return requested


def _resolve_acquisition_record(
    custody_root: Path,
    acquisition_record_path: str,
) -> Path:
    root = custody_root.resolve(strict=False)
    relative = _safe_relative_path(acquisition_record_path)
    candidates = [root / relative]
    if root.name == EXACT_MIRROR_RUN:
        candidates.append(root / "acquisition-record.json")
    else:
        candidates.append(root / EXACT_MIRROR_RUN / "acquisition-record.json")
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("Unsafe acquisition record path.") from exc
        if resolved.is_file():
            return resolved
    raise RuntimeError("The exact M8 acquisition record was not found in custody.")


def _validated_record(record_path: Path) -> dict[str, Any]:
    raw = record_path.read_bytes()
    if _sha256_bytes(raw) != EXPECTED_ACQUISITION_RECORD_SHA256:
        raise RuntimeError("Acquisition record hash mismatch.")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Acquisition record is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Acquisition record must be a JSON object.")
    download = (value.get("stages") or {}).get("download")
    expected_fields = {
        "schema": "project6.instrument-acquisition.v1",
        "doi": ADOPTED_EXTERNAL_DOI,
        "doi_source": "asserted",
        "item_id": ADOPTED_EXTERNAL_ITEM_ID,
        "filename": ADOPTED_EXTERNAL_FILENAME,
        "observed_download_uri": ADOPTED_EXTERNAL_DOWNLOAD_URI,
        "license": "CC0-1.0",
        "license_source": "asserted",
        "artifact_finalized_name": EXPECTED_FINALIZED_NAME,
        "artifact_sha256": EXPECTED_ARTIFACT_SHA256,
        "artifact_bytes": ADOPTED_EXTERNAL_ARTIFACT_BYTES,
    }
    if any(value.get(key) != expected for key, expected in expected_fields.items()):
        raise RuntimeError("Acquisition record identity or artifact metadata mismatch.")
    expected_download = {
        "url": ADOPTED_EXTERNAL_DOWNLOAD_URI,
        "url_effective": ADOPTED_EXTERNAL_DOWNLOAD_URI,
        "body_bytes": ADOPTED_EXTERNAL_ARTIFACT_BYTES,
        "body_sha256": EXPECTED_ARTIFACT_SHA256,
        "ended_at": ADOPTED_EXTERNAL_ACQUIRED_AT,
    }
    if not isinstance(download, dict) or any(
        download.get(key) != expected
        for key, expected in expected_download.items()
    ):
        raise RuntimeError("Acquisition record download-stage evidence mismatch.")
    return value


def _resolve_artifact(custody_root: Path, record_path: Path, record: dict[str, Any]) -> Path:
    root = custody_root.resolve(strict=False)
    finalized_name = str(record.get("artifact_finalized_name") or "")
    if Path(finalized_name).name != finalized_name or finalized_name != EXPECTED_FINALIZED_NAME:
        raise RuntimeError("Acquisition record finalized artifact name is not admitted.")
    candidates = [
        root / "acquisitions" / "artifact" / finalized_name,
        record_path.parent.parent / "artifact" / finalized_name,
    ]
    if root.name == EXACT_MIRROR_RUN:
        candidates.append(root / finalized_name)
    else:
        candidates.append(root / EXACT_MIRROR_RUN / finalized_name)
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    raise RuntimeError("The exact finalized M8 artifact was not found in custody.")


def _assert_safe_runtime_storage(db: Session) -> Path:
    storage_root = Path(settings.storage_dir).resolve(strict=False)
    if storage_root.is_file() or _path_inside_repo_or_onedrive(storage_root):
        raise RuntimeError("Unsafe storage root: repository and OneDrive paths are refused.")
    bind = db.get_bind()
    if isinstance(bind, Engine):
        database_url = bind.url
    elif isinstance(bind, Connection):
        database_url = bind.engine.url
    else:
        raise RuntimeError("Unsupported database bind for adopted external intake.")
    database_path = _sqlite_database_path(str(database_url))
    if database_path is not None and _path_inside_repo_or_onedrive(database_path):
        raise RuntimeError("Unsafe SQLite database path: repository and OneDrive paths are refused.")
    raw_root = Path(settings.connector_raw_dir).resolve(strict=False)
    try:
        relative_raw_root = raw_root.relative_to(storage_root)
    except ValueError as exc:
        raise RuntimeError(
            "Connector raw storage resolves outside the configured storage root."
        ) from exc
    if not relative_raw_root.parts:
        raise RuntimeError("Connector raw storage must be below the configured storage root.")
    return raw_root


def _copy_verified_artifact(source: Path, raw_root: Path) -> tuple[Path, str]:
    source_bytes = source.read_bytes()
    if (
        len(source_bytes) != ADOPTED_EXTERNAL_ARTIFACT_BYTES
        or _sha256_bytes(source_bytes) != EXPECTED_ARTIFACT_SHA256
    ):
        raise RuntimeError("Custody artifact hash or byte-count mismatch before copy.")
    resolved_raw_root = raw_root.resolve(strict=False)
    intended_destination = (
        resolved_raw_root
        / "adopted"
        / EXPECTED_ARTIFACT_SHA256[:8]
        / ADOPTED_EXTERNAL_FILENAME
    )
    destination = intended_destination.resolve(strict=False)
    try:
        destination.relative_to(resolved_raw_root)
    except ValueError as exc:
        raise RuntimeError(
            "Adoption destination resolves outside connector raw storage."
        ) from exc
    disposition = "copied"
    if destination.exists():
        if not destination.is_file():
            raise RuntimeError("Adoption destination exists but is not a file.")
        existing = destination.read_bytes()
        if (
            len(existing) != ADOPTED_EXTERNAL_ARTIFACT_BYTES
            or _sha256_bytes(existing) != EXPECTED_ARTIFACT_SHA256
        ):
            raise RuntimeError("Adoption destination hash mismatch; refusing overwrite.")
        disposition = "reused_exact"
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        resolved_parent = destination.parent.resolve(strict=True)
        try:
            resolved_parent.relative_to(resolved_raw_root)
        except ValueError as exc:
            raise RuntimeError(
                "Adoption destination parent escapes connector raw storage."
            ) from exc
        destination = resolved_parent / destination.name
        try:
            with destination.open("xb") as handle:
                handle.write(source_bytes)
        except FileExistsError:
            existing = destination.read_bytes()
            if (
                len(existing) != ADOPTED_EXTERNAL_ARTIFACT_BYTES
                or _sha256_bytes(existing) != EXPECTED_ARTIFACT_SHA256
            ):
                raise RuntimeError(
                    "Adoption destination appeared concurrently with a mismatched hash."
                )
            disposition = "reused_exact"
    resolved_after_copy = destination.resolve(strict=True)
    try:
        resolved_after_copy.relative_to(resolved_raw_root)
    except ValueError as exc:
        raise RuntimeError(
            "Adoption destination escaped connector raw storage during copy."
        ) from exc
    destination = resolved_after_copy
    copied_bytes = destination.read_bytes()
    if (
        len(copied_bytes) != ADOPTED_EXTERNAL_ARTIFACT_BYTES
        or _sha256_bytes(copied_bytes) != EXPECTED_ARTIFACT_SHA256
    ):
        raise RuntimeError("Adoption destination hash mismatch after copy.")
    return destination, disposition


def _request_basis(provenance: dict[str, str]) -> dict[str, Any]:
    return {
        "source_family": ADOPTED_EXTERNAL_SOURCE_INTAKE_SOURCE_FAMILY,
        "operator_decision": ADOPTED_EXTERNAL_SOURCE_INTAKE_OPERATOR_DECISION,
        "connector_key": ADOPTED_EXTERNAL_CONNECTOR_KEY,
        "source_mode": ADOPTED_EXTERNAL_SOURCE_MODE,
        "artifact_surface": ADOPTED_EXTERNAL_SOURCE_MODE,
        "sciencebase_item_id": ADOPTED_EXTERNAL_ITEM_ID,
        "sciencebase_file_name": ADOPTED_EXTERNAL_FILENAME,
        "sciencebase_download_uri": ADOPTED_EXTERNAL_DOWNLOAD_URI,
        "adoption_provenance": dict(provenance),
    }


def adopt_external_source_intake(
    db: Session,
    *,
    custody_root: Path | str,
    client_request_id: str,
    acquisition_record_path: str,
) -> dict[str, Any]:
    """Copy and record one exact adopted artifact in a single DB transaction."""
    if not settings.layer3_adopted_external_source_intake_enabled:
        raise ConnectorSourceIntakeError(
            "adopted_external_source_intake_unavailable",
            "Adopted external source intake is not enabled.",
            http_status=409,
        )
    raw_root = _assert_safe_runtime_storage(db)
    custody = Path(custody_root)
    record_path = _resolve_acquisition_record(custody, acquisition_record_path)
    record = _validated_record(record_path)
    source = _resolve_artifact(custody, record_path, record)
    destination, disposition = _copy_verified_artifact(source, raw_root)

    provenance = adopted_external_provenance()
    acquired_at = datetime.fromisoformat(
        ADOPTED_EXTERNAL_ACQUIRED_AT.replace("Z", "+00:00")
    )
    run_id = uuid_str()
    target_id = uuid_str()
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key=ADOPTED_EXTERNAL_CONNECTOR_KEY,
        source_system="sciencebase",
        source_mode=ADOPTED_EXTERNAL_SOURCE_MODE,
        status="completed",
        request_config_json=_request_basis(provenance),
        discovered_count=1,
        selected_count=1,
        downloaded_count=1,
        terminal_target_count=1,
        consumed_bytes=ADOPTED_EXTERNAL_ARTIFACT_BYTES,
        completed_at=acquired_at,
    )
    target = ConnectorRunTarget(
        connector_run_target_id=target_id,
        connector_run_id=run_id,
        ordinal=1,
        sciencebase_item_id=ADOPTED_EXTERNAL_ITEM_ID,
        sciencebase_item_url=(
            f"https://www.sciencebase.gov/catalog/item/{ADOPTED_EXTERNAL_ITEM_ID}"
        ),
        sciencebase_file_name=ADOPTED_EXTERNAL_FILENAME,
        sciencebase_download_uri=ADOPTED_EXTERNAL_DOWNLOAD_URI,
        artifact_surface=ADOPTED_EXTERNAL_SOURCE_MODE,
        artifact_locator_type="adopted_storage_ref",
        source_artifact_key=(
            "adopted-external://sciencebase/"
            f"{ADOPTED_EXTERNAL_ITEM_ID}/{ADOPTED_EXTERNAL_FILENAME}"
        ),
        downloaded_sha256=ADOPTED_EXTERNAL_ARTIFACT_SHA256,
        raw_storage_ref=str(destination),
        source_reference_json={
            "doi": ADOPTED_EXTERNAL_DOI,
            "acquisition_git_ref": ADOPTED_EXTERNAL_ACQUISITION_GIT_REF,
            "acquisition_record_path": ADOPTED_EXTERNAL_ACQUISITION_RECORD_PATH,
            "acquisition_record_sha256": ADOPTED_EXTERNAL_ACQUISITION_RECORD_SHA256,
        },
        permission_snapshot_json={
            "license": "CC0-1.0",
            "license_source": "asserted",
            "public_read_confirmed": True,
            "public_read_evidence_source": (
                "standalone-instrument acquisition record, not this run"
            ),
            "acquisition_record_path": ADOPTED_EXTERNAL_ACQUISITION_RECORD_PATH,
            "acquisition_record_sha256": ADOPTED_EXTERNAL_ACQUISITION_RECORD_SHA256,
        },
        access_level_summary=(
            "public-read evidenced by standalone acquisition record"
        ),
        public_read_confirmed=True,
        status="downloaded",
        downloaded_at=acquired_at,
    )
    try:
        db.add_all([run, target])
        db.flush()
        intake = record_adopted_external_source_intake(
            db,
            client_request_id=str(client_request_id),
            connector_key=run.connector_key,
            connector_run_id=run_id,
            connector_run_target_id=target_id,
            source_label="MCS 2023 germanium salient values",
            source_description=(
                "Offline adoption of the owner-authorized standalone-instrument artifact."
            ),
            media_type="text/csv",
            freshness_timestamp=ADOPTED_EXTERNAL_ACQUIRED_AT,
            adoption_provenance=provenance,
        )
    except Exception:
        db.rollback()
        raise
    return {
        **intake,
        "copy_disposition": disposition,
        "acquisition_record_path": ADOPTED_EXTERNAL_ACQUISITION_RECORD_PATH,
        "content_sha256": ADOPTED_EXTERNAL_ARTIFACT_SHA256,
        "raw_storage_ref": str(destination),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline adoption of the exact owner-authorized M8 artifact."
    )
    parser.add_argument("--custody-root", type=Path, required=True)
    parser.add_argument(
        "--acquisition-record-path",
        required=True,
        choices=[ACQUISITION_RECORD_PATH],
    )
    parser.add_argument(
        "--client-request-id",
        default=None,
        help="Optional explicit idempotency key; omission generates a distinct key.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    client_request_id = args.client_request_id or f"adopt-external-{uuid_str()}"
    with SessionLocal() as db:
        result = adopt_external_source_intake(
            db,
            custody_root=args.custody_root,
            acquisition_record_path=args.acquisition_record_path,
            client_request_id=client_request_id,
        )
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
