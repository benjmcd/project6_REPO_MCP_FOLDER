from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import types
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any, Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


SUMMARY_SCHEMA_ID = "aps.local_corpus_e2e_summary.v1"
SUMMARY_SCHEMA_VERSION = 1
EXPECTED_INTERPRETER = ROOT / ".venvs" / "phase7a-py311" / "Scripts" / "python.exe"
DEFAULT_RUNTIME_PARENT = ROOT / "backend" / "app" / "storage_test_runtime" / "lc_e2e"
DEFAULT_CORPUS_ROOT = ROOT / "data_demo" / "nrc_adams_documents_for_testing"
DOCUMENT_TYPES_JSON = (
    ROOT
    / "backend"
    / "app"
    / "services"
    / "nrc_adams_resources"
    / "document_types.json"
)
RUN_POLL_TIMEOUT_SECONDS = 900.0
RUN_POLL_INTERVAL_SECONDS = 0.25
LOCAL_PROOF_CONNECTOR_LEASE_TTL_SECONDS = 1800
HISTORICAL_OCR_FILE_COUNT = 19
HISTORICAL_TABLE_FILE_COUNT = 28
ALEMBIC_STUB_FINDING = {
    "code": "phase7a_alembic_import_surface_stubbed",
    "message": (
        "The Phase 7A interpreter does not provide the third-party Alembic package, and backend/alembic shadows the "
        "import name as a namespace package. The proof tool injects a harness-local Alembic stub so backend/main.py "
        "can load under DB_INIT_MODE=none without changing backend contracts or shared environments."
    ),
}
LEASE_TTL_OVERRIDE_FINDING = {
    "code": "proof_runtime_connector_lease_ttl_override",
    "message": (
        "The isolated proof runtime raises CONNECTOR_LEASE_TTL_SECONDS to 1800 so the largest local-corpus OCR/table "
        "targets do not self-expire the run lease before the post-processing state transition."
    ),
}
_ALEMBIC_STUB_INSTALLED = False


@dataclass(frozen=True)
class CorpusFolderSpec:
    folder_name: str
    slug: str
    document_type: str
    allow_unknown_document_type: bool = False
    source: str = "known"


UNKNOWN_LOCAL_CORPUS_DOCUMENT_TYPE = "Unknown Local Corpus Document"
CORPUS_ROOT_GROUP_NAME = "__corpus_root__"


KNOWN_CORPUS_FOLDERS: dict[str, CorpusFolderSpec] = {
    spec.folder_name: spec
    for spec in (
        CorpusFolderSpec("exemption_from_nrc_requirements_documents_for_testing", "exemption", "Exemption from NRC Requirements"),
        CorpusFolderSpec("handbook_documents_for_testing", "handbook", "Handbook"),
        CorpusFolderSpec("inspection_reports_for_testing", "inspection", "Inspection Report"),
        CorpusFolderSpec(
            "license-application_for_combined_license_documents_for_testing",
            "combined-license",
            "License-Application for Combined License (COLA)",
        ),
        CorpusFolderSpec(
            "license-application_for_facility _operating_license_documents_for_testing",
            "facility-operating-license",
            "License-Application for Facility Operating License (Amend/Renewal) DKT 50",
        ),
        CorpusFolderSpec("licensee_event_reports_for_testing", "licensee-event", "Licensee Event Report (LER)"),
        CorpusFolderSpec("notice_of_violation_documents_for_testing", "notice-of-violation", "Notice of Violation"),
        CorpusFolderSpec("part_21_correspondence_documents_for_testing", "part-21", "Part 21 Correspondence"),
        CorpusFolderSpec("regulatory_guidance_documents_for_testing", "regulatory-guidance", "Regulatory Guidance"),
        CorpusFolderSpec("strategic_plan_documents_for_testing", "strategic-plan", "Strategic Plan"),
        CorpusFolderSpec(
            "technical_specification_amendment_documents_for_testing",
            "technical-spec-amendment",
            "Technical Specification Amendment",
            allow_unknown_document_type=True,
        ),
        CorpusFolderSpec("weekly_information_report_documents_for_testing", "weekly-information-report", "Weekly Information Report"),
    )
}

GATE_SPECS: tuple[tuple[str, str, str], ...] = (
    ("artifact_ingestion", "nrc_aps_artifact_ingestion_gate.py", "artifact_ingestion.json"),
    ("content_index", "nrc_aps_content_index_gate.py", "content_index.json"),
    ("evidence_bundle", "nrc_aps_evidence_bundle_gate.py", "evidence_bundle.json"),
    ("evidence_citation_pack", "nrc_aps_evidence_citation_pack_gate.py", "evidence_citation_pack.json"),
    ("evidence_report", "nrc_aps_evidence_report_gate.py", "evidence_report.json"),
    ("evidence_report_export", "nrc_aps_evidence_report_export_gate.py", "evidence_report_export.json"),
    ("evidence_report_export_package", "nrc_aps_evidence_report_export_package_gate.py", "evidence_report_export_package.json"),
    ("context_packet", "nrc_aps_context_packet_gate.py", "context_packet.json"),
    ("context_dossier", "nrc_aps_context_dossier_gate.py", "context_dossier.json"),
    ("deterministic_insight_artifact", "nrc_aps_deterministic_insight_artifact_gate.py", "deterministic_insight_artifact.json"),
    ("deterministic_challenge_artifact", "nrc_aps_deterministic_challenge_artifact_gate.py", "deterministic_challenge_artifact.json"),
    ("deterministic_challenge_review_packet", "nrc_aps_deterministic_challenge_review_packet_gate.py", "deterministic_challenge_review_packet.json"),
)


class ProofError(RuntimeError):
    pass


class _FakeRequest:
    def __init__(self, url: str):
        self.url = url


class _FakeJsonResponse:
    def __init__(self, *, url: str, status_code: int, payload: dict[str, Any], headers: dict[str, str] | None = None):
        self.request = _FakeRequest(url)
        self.url = url
        self.status_code = int(status_code)
        self._payload = dict(payload)
        self.text = json.dumps(payload, sort_keys=True)
        self.headers = dict(headers or {"content-type": "application/json"})
        self.history: list[Any] = []

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise ProofError(f"fake NRC response status={self.status_code} for {self.url}")


@dataclass(frozen=True)
class LocalCorpusDocument:
    ordinal: int
    accession_number: str
    title: str
    document_type: str
    folder_name: str
    folder_slug: str
    allow_unknown_document_type: bool
    file_path: Path
    document_date: str
    date_added_timestamp: str
    url: str

    def search_result(self) -> dict[str, Any]:
        return {
            "score": 1.0,
            "document": {
                "AccessionNumber": self.accession_number,
                "DocumentTitle": self.title,
                "DocumentType": self.document_type,
                "DocumentDate": self.document_date,
                "DateAddedTimestamp": self.date_added_timestamp,
                "Url": self.url,
            },
        }

    def document_detail(self) -> dict[str, Any]:
        return {
            "document": {
                "AccessionNumber": self.accession_number,
                "DocumentTitle": self.title,
                "DocumentType": self.document_type,
                "DocumentDate": self.document_date,
                "DateAddedTimestamp": self.date_added_timestamp,
                "Url": self.url,
                "content": self.title,
            }
        }


class LocalCorpusNrcClient:
    def __init__(self, docs: list[LocalCorpusDocument]):
        self.docs = list(docs)
        self.docs_by_accession = {doc.accession_number: doc for doc in self.docs}
        self.docs_by_url = {doc.url: doc for doc in self.docs}
        self.search_payloads: list[dict[str, Any]] = []
        self.document_ids: list[str] = []
        self.download_urls: list[str] = []

    def search(self, payload: dict[str, Any], *, scope_key: str | None = None) -> _FakeJsonResponse:
        del scope_key
        outbound = dict(payload or {})
        self.search_payloads.append(outbound)
        skip = max(0, _coerce_int(outbound.get("skip"), 0))
        take = max(1, _coerce_int(outbound.get("take"), _coerce_int(outbound.get("page_size"), 100)))
        page = self.docs[skip : skip + take]
        body = {"count": len(self.docs), "results": [doc.search_result() for doc in page]}
        return _FakeJsonResponse(url="https://adams-api.nrc.gov/aps/api/search", status_code=200, payload=body)

    def get_document(self, accession_number: str) -> _FakeJsonResponse:
        doc = self.docs_by_accession.get(str(accession_number))
        if doc is None:
            return _FakeJsonResponse(
                url=f"https://adams-api.nrc.gov/aps/api/search/{accession_number}",
                status_code=404,
                payload={"error": "document_not_found"},
            )
        self.document_ids.append(doc.accession_number)
        return _FakeJsonResponse(
            url=f"https://adams-api.nrc.gov/aps/api/search/{doc.accession_number}",
            status_code=200,
            payload=doc.document_detail(),
        )

    def download_artifact(self, url: str, *, max_redirects: int, max_file_bytes: int | None = None) -> Any:
        del max_redirects
        doc = self.docs_by_url.get(str(url))
        if doc is None:
            raise ProofError(f"unexpected download URL: {url}")
        content = _safe_local_read_bytes(doc.file_path)
        if max_file_bytes is not None and len(content) > int(max_file_bytes):
            raise ProofError(f"fixture exceeds max_file_bytes: {doc.file_path}")
        self.download_urls.append(doc.url)
        digest = hashlib.sha256(content).hexdigest()
        last_modified = format_datetime(datetime.fromtimestamp(_safe_local_stat(doc.file_path).st_mtime, tz=timezone.utc), usegmt=True)
        return type(
            "LocalApsDownloadResult",
            (),
            {
                "content": content,
                "status_code": 200,
                "final_url": doc.url,
                "redirect_count": 0,
                "etag": f"sha256:{digest}",
                "last_modified": last_modified,
                "content_type": "application/pdf",
                "sha256": digest,
                "headers": {"content-type": "application/pdf", "content-length": str(len(content))},
                "auth_required": True,
            },
        )()

    def record_parse_failure(self, **kwargs: Any) -> None:
        del kwargs


@dataclass
class RuntimeContext:
    client: TestClient
    session_factory: Any
    env: dict[str, str]
    database_path: Path
    storage_dir: Path


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _round_up_to_mib(value: int) -> int:
    mib = 1024 * 1024
    return max(mib, ((int(value) + mib - 1) // mib) * mib)


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_stable_json(payload), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProofError(f"expected JSON object at {path}")
    return payload


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise ProofError(message)


def _load_document_types_reference() -> set[str]:
    payload = _read_json(DOCUMENT_TYPES_JSON)
    values = payload.get("document_types")
    _assert(isinstance(values, list), "document_types.json must expose a document_types list")
    return {str(item).strip() for item in values if str(item).strip()}


def _normalize_title(stem: str) -> str:
    return re.sub(r"\s+", " ", stem.replace("_", " ")).strip()


def _slugify_corpus_group_name(name: str) -> str:
    if name == CORPUS_ROOT_GROUP_NAME:
        return "corpus-root"
    normalized = name.strip().lower()
    normalized = normalized.replace("_documents_for_testing", "")
    normalized = normalized.replace("_for_testing", "")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    return normalized or "corpus"


def _strip_windows_extended_prefix(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value


def _to_filesystem_io_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    raw = str(path)
    if raw.startswith("\\\\?\\"):
        return Path(raw)
    if not path.is_absolute():
        raw = str((Path.cwd() / path).absolute())
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw.lstrip("\\"))
    return Path("\\\\?\\" + raw)


def _safe_local_stat(path: Path) -> os.stat_result:
    return _to_filesystem_io_path(path).stat()


def _safe_local_read_bytes(path: Path) -> bytes:
    return _to_filesystem_io_path(path).read_bytes()


def _walk_corpus_pdfs(corpus_root: Path) -> list[Path]:
    pdfs: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(str(_to_filesystem_io_path(corpus_root))):
        dirnames.sort(key=str.lower)
        for filename in sorted(filenames, key=str.lower):
            if Path(filename).suffix.lower() != ".pdf":
                continue
            pdfs.append(Path(_strip_windows_extended_prefix(os.path.join(dirpath, filename))))
    return pdfs


def _group_corpus_pdfs(corpus_root: Path) -> tuple[dict[str, list[Path]], list[str]]:
    normalized_root = Path(_strip_windows_extended_prefix(str(corpus_root.resolve())))
    grouped: dict[str, list[Path]] = {}
    for pdf_path in _walk_corpus_pdfs(normalized_root):
        relative = pdf_path.relative_to(normalized_root)
        group_name = relative.parts[0] if len(relative.parts) > 1 else CORPUS_ROOT_GROUP_NAME
        grouped.setdefault(group_name, []).append(pdf_path)

    ignored_empty_dirs = sorted(
        child.name
        for child in normalized_root.iterdir()
        if child.is_dir() and child.name not in grouped
    )
    return grouped, ignored_empty_dirs


def _resolve_corpus_folder_spec(folder_name: str) -> CorpusFolderSpec:
    if folder_name == CORPUS_ROOT_GROUP_NAME:
        return CorpusFolderSpec(
            folder_name=folder_name,
            slug=_slugify_corpus_group_name(folder_name),
            document_type=UNKNOWN_LOCAL_CORPUS_DOCUMENT_TYPE,
            allow_unknown_document_type=True,
            source="root",
        )

    known = KNOWN_CORPUS_FOLDERS.get(folder_name)
    if known is not None:
        return known

    return CorpusFolderSpec(
        folder_name=folder_name,
        slug=_slugify_corpus_group_name(folder_name),
        document_type=UNKNOWN_LOCAL_CORPUS_DOCUMENT_TYPE,
        allow_unknown_document_type=True,
        source="dynamic",
    )


def _extract_accession_number(stem: str, *, ordinal: int, seen: set[str]) -> str:
    match = re.search(r"\b(ML\d{6,})\b", stem, flags=re.IGNORECASE)
    if match:
        accession = match.group(1).upper()
        _assert(accession not in seen, f"duplicate accession number in local corpus: {accession}")
        seen.add(accession)
        return accession
    accession = f"LOCALAPS{ordinal:05d}"
    _assert(accession not in seen, f"duplicate generated accession number in local corpus: {accession}")
    seen.add(accession)
    return accession


def _build_local_corpus_documents(corpus_root: Path) -> tuple[list[LocalCorpusDocument], dict[str, Any]]:
    _assert(corpus_root.resolve() == DEFAULT_CORPUS_ROOT.resolve(), f"corpus root must be {DEFAULT_CORPUS_ROOT}")
    _assert(corpus_root.exists(), f"corpus root not found: {corpus_root}")

    document_types_reference = _load_document_types_reference()
    pdf_groups, ignored_empty_dirs = _group_corpus_pdfs(corpus_root)
    _assert(pdf_groups, f"no PDF files found under corpus root: {corpus_root}")

    folder_counts: dict[str, int] = {}
    folder_specs: list[dict[str, Any]] = []
    docs: list[LocalCorpusDocument] = []
    seen_accessions: set[str] = set()
    seen_slugs: set[str] = set()
    ordinal = 0

    for folder_name in sorted(pdf_groups, key=str.lower):
        spec = _resolve_corpus_folder_spec(folder_name)
        _assert(spec.slug not in seen_slugs, f"duplicate corpus folder slug resolved for {folder_name}: {spec.slug}")
        seen_slugs.add(spec.slug)
        if not spec.allow_unknown_document_type:
            _assert(spec.document_type in document_types_reference, f"document type missing from document_types.json: {spec.document_type}")
        pdfs = pdf_groups[folder_name]
        folder_counts[spec.slug] = len(pdfs)
        folder_specs.append(
            {
                "folder_name": spec.folder_name,
                "slug": spec.slug,
                "document_type": spec.document_type,
                "allow_unknown_document_type": spec.allow_unknown_document_type,
                "source": spec.source,
                "pdf_count": len(pdfs),
            }
        )
        for pdf_path in pdfs:
            ordinal += 1
            mtime = datetime.fromtimestamp(_safe_local_stat(pdf_path).st_mtime, tz=timezone.utc)
            accession = _extract_accession_number(pdf_path.stem, ordinal=ordinal, seen=seen_accessions)
            docs.append(
                LocalCorpusDocument(
                    ordinal=ordinal,
                    accession_number=accession,
                    title=_normalize_title(pdf_path.stem),
                    document_type=spec.document_type,
                    folder_name=spec.folder_name,
                    folder_slug=spec.slug,
                    allow_unknown_document_type=spec.allow_unknown_document_type,
                    file_path=pdf_path,
                    document_date=mtime.date().isoformat(),
                    date_added_timestamp=mtime.isoformat().replace("+00:00", "Z"),
                    url=f"https://adams.nrc.gov/local-corpus/{accession}.pdf",
                )
            )

    _assert("Technical Specification, Amendment" in document_types_reference, "document_types.json must contain Technical Specification, Amendment")
    _assert("Technical Specification Amendment" not in document_types_reference, "document_types.json unexpectedly already contains Technical Specification Amendment")

    return docs, {
        "corpus_root": str(corpus_root),
        "folder_counts": folder_counts,
        "total_pdfs": len(docs),
        "folder_specs": folder_specs,
        "dynamic_folder_names": [item["folder_name"] for item in folder_specs if item["source"] == "dynamic"],
        "root_level_pdf_count": sum(item["pdf_count"] for item in folder_specs if item["source"] == "root"),
        "ignored_empty_top_level_dirs": ignored_empty_dirs,
        "document_type_reference_path": str(DOCUMENT_TYPES_JSON),
        "technical_spec_runtime_type": "Technical Specification Amendment",
        "technical_spec_reference_type": "Technical Specification, Amendment",
    }


def _ghostscript_path() -> str | None:
    for candidate in ("gswin64c.exe", "gswin64c", "gs.exe", "gs"):
        resolved = shutil.which(candidate)
        if resolved:
            return str(Path(resolved).resolve())
    common = [
        Path("C:/Program Files/gs/gs10.06.0/bin/gswin64c.EXE"),
        Path("C:/Program Files/gs/gs10.05.1/bin/gswin64c.EXE"),
        Path("C:/Program Files/gs/gs10.04.0/bin/gswin64c.EXE"),
    ]
    for path in common:
        if path.exists():
            return str(path.resolve())
    return None


def _run_preflight(runtime_root: Path) -> tuple[list[LocalCorpusDocument], dict[str, Any], list[dict[str, Any]]]:
    docs, corpus_shape = _build_local_corpus_documents(DEFAULT_CORPUS_ROOT)

    _assert(EXPECTED_INTERPRETER.exists(), f"expected Phase 7A interpreter missing: {EXPECTED_INTERPRETER}")
    _assert(Path(sys.executable).resolve() == EXPECTED_INTERPRETER.resolve(), f"tool must run with {EXPECTED_INTERPRETER}, got {Path(sys.executable).resolve()}")

    imported_modules: list[dict[str, Any]] = []
    for module_name in ("fitz", "camelot", "paddleocr", "matplotlib", "ruptures", "statsmodels", "sklearn", "multipart"):
        module = importlib.import_module(module_name)
        imported_modules.append(
            {
                "module": module_name,
                "loaded_from": str(Path(getattr(module, "__file__", "built-in")).resolve()) if getattr(module, "__file__", None) else "built-in",
            }
        )

    aps_settings = importlib.import_module("app.services.nrc_aps_settings")
    paddle_dirs = {
        "PADDLE_MODEL_DIR": Path(str(getattr(aps_settings, "PADDLE_MODEL_DIR"))),
        "PADDLE_DET_MODEL_DIR": Path(str(getattr(aps_settings, "PADDLE_DET_MODEL_DIR"))),
        "PADDLE_REC_MODEL_DIR": Path(str(getattr(aps_settings, "PADDLE_REC_MODEL_DIR"))),
        "PADDLE_CLS_MODEL_DIR": Path(str(getattr(aps_settings, "PADDLE_CLS_MODEL_DIR"))),
    }
    for name, path in paddle_dirs.items():
        _assert(path.exists(), f"{name} missing: {path}")

    ghostscript = _ghostscript_path()
    _assert(ghostscript is not None, "Ghostscript executable not found")

    if runtime_root.exists():
        _assert(runtime_root.resolve().is_relative_to(DEFAULT_RUNTIME_PARENT.resolve()), f"runtime_root must stay under {DEFAULT_RUNTIME_PARENT}")
        _assert(not any(runtime_root.iterdir()), f"runtime_root must be empty when provided: {runtime_root}")

    findings: list[dict[str, Any]] = [
        {
            "code": "technical_spec_document_type_vocabulary_mismatch",
            "message": (
                "The local proof maps technical_specification_amendment_documents_for_testing to "
                "'Technical Specification Amendment' to exercise the live advanced-table routing key, "
                "while document_types.json still canonically lists 'Technical Specification, Amendment'."
            ),
        },
        {
            "code": "idempotency_key_run_id_dependency_unavailable",
            "message": (
                "The submit route assigns connector_run_id server-side, so the proof uses a runtime-stamp-derived "
                "Idempotency-Key instead of a value derived from the fresh run ID."
            ),
        },
        {
            "code": "monolithic_router_dependency_surface",
            "message": (
                "The live NRC proof must boot the full API router, which currently imports unrelated analysis/profiling/"
                "transform services and therefore depends on their runtime packages even though this proof exercises only "
                "NRC APS endpoints."
            ),
        },
        dict(LEASE_TTL_OVERRIDE_FINDING),
    ]

    dynamic_folder_names = [str(name) for name in (corpus_shape.get("dynamic_folder_names") or []) if str(name).strip()]
    if dynamic_folder_names:
        findings.append(
            {
                "code": "dynamic_local_corpus_folder_set",
                "message": (
                    "The local corpus contains additional top-level PDF folders outside the historical fixed corpus set. "
                    "The proof now discovers folders from disk deterministically and assigns placeholder document-type "
                    f"metadata to dynamic folders: {', '.join(dynamic_folder_names)}."
                ),
            }
        )

    ignored_empty_top_level_dirs = [str(name) for name in (corpus_shape.get("ignored_empty_top_level_dirs") or []) if str(name).strip()]
    if ignored_empty_top_level_dirs:
        findings.append(
            {
                "code": "ignored_empty_local_corpus_dirs",
                "message": (
                    "Top-level corpus directories without PDFs were ignored by the proof corpus scan: "
                    f"{', '.join(ignored_empty_top_level_dirs)}."
                ),
            }
        )

    root_level_pdf_count = int(corpus_shape.get("root_level_pdf_count") or 0)
    if root_level_pdf_count > 0:
        findings.append(
            {
                "code": "root_level_local_corpus_pdfs",
                "message": (
                    "The local corpus contains PDFs directly under the corpus root; the proof grouped them under the "
                    f"'corpus-root' synthetic folder ({root_level_pdf_count} PDFs)."
                ),
            }
        )

    return docs, {
        "interpreter_path": str(Path(sys.executable).resolve()),
        "expected_interpreter_path": str(EXPECTED_INTERPRETER.resolve()),
        "corpus_shape": corpus_shape,
        "imports": imported_modules,
        "ghostscript_path": ghostscript,
        "paddle_model_dirs": {name: str(path) for name, path in paddle_dirs.items()},
        "isolated_runtime_overrides": {
            "CONNECTOR_LEASE_TTL_SECONDS": LOCAL_PROOF_CONNECTOR_LEASE_TTL_SECONDS,
        },
        "runtime_root": str(runtime_root),
    }, findings


def _allocate_runtime_root() -> Path:
    DEFAULT_RUNTIME_PARENT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    candidate = DEFAULT_RUNTIME_PARENT / stamp
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = DEFAULT_RUNTIME_PARENT / f"{stamp}_{suffix:02d}"
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def _resolve_runtime_root(raw_runtime_root: str) -> Path:
    if not str(raw_runtime_root).strip():
        return _allocate_runtime_root()

    runtime_root = Path(raw_runtime_root).resolve()
    _assert(runtime_root.is_relative_to(DEFAULT_RUNTIME_PARENT.resolve()), f"runtime_root must stay under {DEFAULT_RUNTIME_PARENT}")
    return runtime_root


def _purge_app_modules() -> None:
    for module_name in list(sys.modules):
        if module_name in {"app", "main"} or module_name.startswith("app."):
            sys.modules.pop(module_name, None)


def _raise_unexpected_alembic_usage(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    raise ProofError("Alembic stub was invoked unexpectedly while DB_INIT_MODE=none should have bypassed migrations")


def _install_alembic_stub_if_needed() -> dict[str, Any]:
    global _ALEMBIC_STUB_INSTALLED

    try:
        from alembic import command as alembic_command  # type: ignore
        from alembic.config import Config as alembic_config  # type: ignore

        del alembic_command, alembic_config
        return {}
    except Exception:
        previous_modules = {
            "alembic": sys.modules.get("alembic"),
            "alembic.command": sys.modules.get("alembic.command"),
            "alembic.config": sys.modules.get("alembic.config"),
        }

        command_module = types.ModuleType("alembic.command")
        command_module.upgrade = _raise_unexpected_alembic_usage  # type: ignore[attr-defined]
        command_module.stamp = _raise_unexpected_alembic_usage  # type: ignore[attr-defined]

        config_module = types.ModuleType("alembic.config")

        class _StubConfig:
            def __init__(self, *args: Any, **kwargs: Any):
                del args, kwargs

            def set_main_option(self, *args: Any, **kwargs: Any) -> None:
                del args, kwargs

        config_module.Config = _StubConfig  # type: ignore[attr-defined]

        alembic_module = types.ModuleType("alembic")
        alembic_module.command = command_module  # type: ignore[attr-defined]
        alembic_module.config = config_module  # type: ignore[attr-defined]

        sys.modules["alembic"] = alembic_module
        sys.modules["alembic.command"] = command_module
        sys.modules["alembic.config"] = config_module
        _ALEMBIC_STUB_INSTALLED = True
        return previous_modules


def _restore_stubbed_modules(previous_modules: dict[str, Any]) -> None:
    for module_name, module in previous_modules.items():
        if module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = module


@contextmanager
def _isolated_runtime(fake_client: LocalCorpusNrcClient, runtime_root: Path) -> Iterator[RuntimeContext]:
    storage_dir = runtime_root / "storage"
    database_path = runtime_root / "lc.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    storage_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["STORAGE_DIR"] = str(storage_dir)
    env["DB_INIT_MODE"] = "none"
    env["CONNECTOR_LEASE_TTL_SECONDS"] = str(LOCAL_PROOF_CONNECTOR_LEASE_TTL_SECONDS)
    env["NRC_ADAMS_APS_SUBSCRIPTION_KEY"] = "test-nrc-key"
    env["NRC_ADAMS_APS_API_BASE_URL"] = "https://adams-api.nrc.gov"

    for key, value in env.items():
        os.environ[key] = value

    _purge_app_modules()
    alembic_restore = _install_alembic_stub_if_needed()
    main_module = importlib.import_module("main")
    from app.api.deps import get_db  # noqa: WPS433
    from app.db.session import Base  # noqa: WPS433
    from app.services import connectors_nrc_adams  # noqa: WPS433

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Iterator[Any]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    original_get_client = connectors_nrc_adams.get_nrc_adams_client
    connectors_nrc_adams.get_nrc_adams_client = lambda config: fake_client
    main_module.app.dependency_overrides[get_db] = override_get_db

    with TestClient(main_module.app) as client:
        try:
            yield RuntimeContext(
                client=client,
                session_factory=session_factory,
                env=env,
                database_path=database_path,
                storage_dir=storage_dir,
            )
        finally:
            connectors_nrc_adams.get_nrc_adams_client = original_get_client
            main_module.app.dependency_overrides.clear()
            engine.dispose()
            _restore_stubbed_modules(alembic_restore)
            _purge_app_modules()


def _post_json(client: TestClient, path: str, payload: dict[str, Any], *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    response = client.post(path, json=payload, headers=headers or {})
    _assert(response.status_code < 400, f"POST {path} failed: {response.status_code} {response.text}")
    data = response.json()
    _assert(isinstance(data, dict), f"POST {path} did not return a JSON object")
    return data


def _get_json(client: TestClient, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.get(path, params=params or {})
    _assert(response.status_code < 400, f"GET {path} failed: {response.status_code} {response.text}")
    data = response.json()
    _assert(isinstance(data, dict), f"GET {path} did not return a JSON object")
    return data


def _poll_run_detail(client: TestClient, run_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + RUN_POLL_TIMEOUT_SECONDS
    terminal_statuses = {"completed", "completed_with_errors", "failed", "cancelled"}
    while time.monotonic() < deadline:
        payload = _get_json(client, f"/api/v1/connectors/runs/{run_id}")
        if str(payload.get("status") or "") in terminal_statuses:
            return payload
        time.sleep(RUN_POLL_INTERVAL_SECONDS)
    raise ProofError(f"connector run {run_id} did not reach a terminal state before timeout")


def _collect_all_content_units(client: TestClient, run_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    offset = 0
    total = None
    while total is None or offset < total:
        page = _get_json(client, f"/api/v1/connectors/runs/{run_id}/content-units", params={"limit": 200, "offset": offset})
        page_items = [dict(item) for item in (page.get("items") or []) if isinstance(item, dict)]
        if total is None:
            total = int(page.get("total") or 0)
        items.extend(page_items)
        if not page_items:
            break
        offset += len(page_items)
    return items


def _collect_all_targets(client: TestClient, run_id: str) -> list[dict[str, Any]]:
    payload = _get_json(client, f"/api/v1/connectors/runs/{run_id}/targets", params={"limit": 100, "offset": 0})
    return [dict(item) for item in (payload.get("targets") or []) if isinstance(item, dict)]


def _create_persisted_artifact(
    client: TestClient,
    *,
    post_path: str,
    get_path: str,
    payload: dict[str, Any],
    id_key: str,
    ref_key: str,
) -> dict[str, Any]:
    created = _post_json(client, post_path, payload)
    artifact_id = str(created.get(id_key) or "").strip()
    artifact_ref = str(created.get(ref_key) or "").strip()
    _assert(artifact_id, f"{post_path} did not return {id_key}")
    _assert(bool(created.get("persisted")), f"{post_path} did not persist the artifact")
    _assert(artifact_ref, f"{post_path} did not return {ref_key}")
    _assert(Path(artifact_ref).exists(), f"persisted artifact ref does not exist on disk: {artifact_ref}")
    fetched = _get_json(client, get_path.format(artifact_id=artifact_id))
    _assert(str(fetched.get(id_key) or "") == artifact_id, f"GET {get_path} returned the wrong {id_key}")
    _assert(bool(fetched.get("persisted")), f"GET {get_path} did not return persisted=true")
    _assert(str(fetched.get(ref_key) or "") == artifact_ref, f"GET {get_path} returned the wrong {ref_key}")
    return {"created": created, "fetched": fetched}


def _select_downstream_rows(content_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_content_ids: set[str] = set()
    seen_target_ids: set[str] = set()
    for row in content_units:
        content_id = str(row.get("content_id") or "").strip()
        target_id = str(row.get("target_id") or "").strip()
        if not content_id or not target_id:
            continue
        if content_id in seen_content_ids or target_id in seen_target_ids:
            continue
        selected.append(row)
        seen_content_ids.add(content_id)
        seen_target_ids.add(target_id)
        if len(selected) == 2:
            return selected
    raise ProofError("unable to select two distinct content_id/target_id rows for downstream branching")


def _extract_search_token(content_units: list[dict[str, Any]]) -> str:
    for row in content_units:
        chunk_text = str(row.get("chunk_text") or "")
        match = re.search(r"[A-Za-z]{4,}", chunk_text)
        if match:
            return match.group(0)
    raise ProofError("unable to derive a search smoke token from persisted content units")


def _resolve_visual_artifact_path(artifact_storage_dir: Path, visual_ref: str) -> Path:
    raw = str(visual_ref or "").strip()
    if not raw:
        raise ProofError("visual_artifact_ref missing")
    path = Path(raw)
    if path.is_absolute():
        return path
    return artifact_storage_dir / raw.replace("/", os.sep)


def _collect_advanced_metrics(runtime: RuntimeContext, run_id: str, docs: list[LocalCorpusDocument]) -> dict[str, Any]:
    from app.models import ConnectorRunTarget  # noqa: WPS433

    session = runtime.session_factory()
    try:
        target_rows = (
            session.query(ConnectorRunTarget)
            .filter(ConnectorRunTarget.connector_run_id == run_id)
            .order_by(ConnectorRunTarget.ordinal.asc())
            .all()
        )
        target_by_id = {str(row.connector_run_target_id): row for row in target_rows}
    finally:
        session.close()

    docs_by_accession = {doc.accession_number: doc for doc in docs}
    artifact_storage_dir = runtime.storage_dir / "artifacts"
    per_target: list[dict[str, Any]] = []
    unknown_doc_type_failures: list[str] = []
    unresolved_visual_refs: list[str] = []

    for target_id, target_row in target_by_id.items():
        source_reference = dict(target_row.source_reference_json or {})
        target_ref = str(source_reference.get("aps_artifact_ingestion_ref") or "").strip()
        _assert(target_ref, f"missing aps_artifact_ingestion_ref for target {target_id}")
        target_payload = _read_json(Path(target_ref))
        extraction = dict(target_payload.get("extraction") or {})
        diagnostics_ref = str(extraction.get("diagnostics_ref") or "").strip()
        _assert(diagnostics_ref, f"missing diagnostics_ref for target {target_id}")
        diagnostics_payload = _read_json(Path(diagnostics_ref))
        page_summaries = [dict(item) for item in (diagnostics_payload.get("page_summaries") or []) if isinstance(item, dict)]
        ordered_units = [dict(item) for item in (diagnostics_payload.get("ordered_units") or []) if isinstance(item, dict)]
        visual_refs = [dict(item) for item in (diagnostics_payload.get("visual_page_refs") or []) if isinstance(item, dict)]
        reported_ocr_page_count = int(diagnostics_payload.get("ocr_page_count") or extraction.get("ocr_page_count") or 0)
        fallback_ocr_page_count = sum(1 for item in page_summaries if str(item.get("source") or "").strip() == "ocr")
        ocr_attempted_page_count = sum(1 for item in page_summaries if bool(item.get("ocr_attempted")))
        derived_ocr_page_count = max(reported_ocr_page_count, fallback_ocr_page_count)
        ocr_image_supplement_unit_count = sum(
            1 for item in ordered_units if str(item.get("unit_kind") or "").strip() == "ocr_image_supplement"
        )
        ocr_exercised = bool(
            derived_ocr_page_count > 0
            or ocr_attempted_page_count > 0
            or ocr_image_supplement_unit_count > 0
        )
        table_unit_count = sum(1 for item in ordered_units if str(item.get("unit_kind") or "").strip() == "pdf_table")
        for visual_row in visual_refs:
            visual_artifact_ref = str(visual_row.get("visual_artifact_ref") or "").strip()
            if not visual_artifact_ref:
                continue
            resolved_visual_path = _resolve_visual_artifact_path(artifact_storage_dir, visual_artifact_ref)
            if not resolved_visual_path.exists():
                unresolved_visual_refs.append(str(resolved_visual_path))
        normalized = dict(source_reference.get("aps_normalized") or {})
        document_type_known = normalized.get("document_type_known")
        accession_number = str(target_row.sciencebase_item_id or target_payload.get("accession_number") or "").strip()
        corpus_doc = docs_by_accession.get(accession_number)
        _assert(corpus_doc is not None, f"unable to map target {target_id} accession {accession_number} back to the local corpus")
        if document_type_known is False and not corpus_doc.allow_unknown_document_type:
            unknown_doc_type_failures.append(accession_number)
        if not isinstance(document_type_known, bool):
            raise ProofError(f"document_type_known missing or non-boolean for target {target_id}")
        per_target.append(
            {
                "target_id": target_id,
                "accession_number": accession_number,
                "folder_slug": corpus_doc.folder_slug,
                "document_type": corpus_doc.document_type,
                "document_type_known": document_type_known,
                "derived_ocr_page_count": derived_ocr_page_count,
                "fallback_ocr_page_count": fallback_ocr_page_count,
                "ocr_attempted_page_count": ocr_attempted_page_count,
                "ocr_image_supplement_unit_count": ocr_image_supplement_unit_count,
                "ocr_exercised": ocr_exercised,
                "table_unit_count": table_unit_count,
                "visual_ref_count": len(visual_refs),
                "extractor_id": str(diagnostics_payload.get("extractor_id") or extraction.get("extractor_id") or ""),
                "diagnostics_ref": diagnostics_ref,
                "target_artifact_ref": target_ref,
            }
        )

    ocr_file_count = sum(1 for row in per_target if bool(row["ocr_exercised"]))
    table_file_count = sum(1 for row in per_target if int(row["table_unit_count"]) > 0)
    visual_ref_total = sum(int(row["visual_ref_count"]) for row in per_target)

    _assert(ocr_file_count >= 1, "no persisted local-corpus file exercised OCR-assisted extraction")
    _assert(table_file_count >= 1, "no persisted local-corpus file produced a pdf_table ordered unit")
    _assert(not unknown_doc_type_failures, f"document_type_known was false outside the technical-spec corpus slice: {unknown_doc_type_failures}")
    _assert(not unresolved_visual_refs, f"some emitted visual_artifact_ref paths do not resolve: {unresolved_visual_refs}")

    return {
        "ocr_file_count": ocr_file_count,
        "table_file_count": table_file_count,
        "visual_ref_total": visual_ref_total,
        "historical_comparison_only": {
            "historical_ocr_file_count": HISTORICAL_OCR_FILE_COUNT,
            "historical_table_file_count": HISTORICAL_TABLE_FILE_COUNT,
        },
        "per_target": per_target,
        "unresolved_visual_refs": unresolved_visual_refs,
        "technical_spec_unknown_accessions": [
            row["accession_number"]
            for row in per_target
            if row["folder_slug"] == "technical-spec-amendment" and row["document_type_known"] is False
        ],
    }


def _run_gate_scripts(runtime: RuntimeContext, run_id: str, runtime_root: Path) -> dict[str, Any]:
    reports_dir = runtime_root / "gate_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    gate_results: dict[str, Any] = {}
    for gate_name, script_name, report_name in GATE_SPECS:
        report_path = reports_dir / report_name
        command = [sys.executable, str(ROOT / "tools" / script_name), "--run-id", run_id, "--report", str(report_path)]
        completed = subprocess.run(command, cwd=str(ROOT), env=runtime.env, capture_output=True, text=True)
        payload = _read_json(report_path)
        passed = bool(payload.get("passed"))
        _assert(completed.returncode == 0, f"gate {gate_name} exited with {completed.returncode}: {completed.stderr}")
        _assert(passed, f"gate {gate_name} reported passed=false")
        gate_results[gate_name] = {
            "script": script_name,
            "report_path": str(report_path),
            "passed": passed,
            "checked_runs": int(payload.get("checked_runs") or 0),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    return gate_results


def _verify_report_ref_set(detail_payload: dict[str, Any], key: str, expected_refs: list[str]) -> None:
    report_refs = detail_payload.get("report_refs") or {}
    actual = [str(item) for item in (report_refs.get(key) or []) if str(item).strip()]
    _assert(len(actual) == len(expected_refs), f"unexpected report ref count for {key}: {actual}")
    _assert(set(actual) == set(expected_refs), f"unexpected report refs for {key}: {actual}")


def _verify_failure_ref_list(detail_payload: dict[str, Any], key: str) -> None:
    report_refs = detail_payload.get("report_refs") or {}
    failures = list(report_refs.get(key) or [])
    _assert(failures == [], f"expected no failure refs for {key}, found {failures}")


def _execute_proof(runtime: RuntimeContext, docs: list[LocalCorpusDocument], runtime_root: Path, fake_client: LocalCorpusNrcClient) -> dict[str, Any]:
    from app.models import ConnectorRunTarget  # noqa: WPS433

    execution_stamp = runtime_root.name
    idempotency_key = f"local-corpus-e2e-{execution_stamp}"
    total_docs = len(docs)
    page_size = 10
    corpus_total_bytes = sum(_safe_local_stat(doc.file_path).st_size for doc in docs)
    corpus_max_file_bytes = max(_safe_local_stat(doc.file_path).st_size for doc in docs)
    submit_payload = {
        "mode": "strict_builder",
        "wire_shape_mode": "shape_a",
        "run_mode": "metadata_only",
        "artifact_pipeline_mode": "hydrate_process",
        "artifact_required_for_target_success": True,
        "include_document_details": True,
        "page_size": page_size,
        "max_items": total_docs,
        "max_file_bytes": _round_up_to_mib(corpus_max_file_bytes),
        "max_run_bytes": _round_up_to_mib(corpus_total_bytes),
        "content_parse_timeout_seconds": 0,
        "report_verbosity": "standard",
        "client_request_id": idempotency_key,
    }
    submitted = _post_json(runtime.client, "/api/v1/connectors/nrc-adams-aps/runs", submit_payload, headers={"Idempotency-Key": idempotency_key})
    run_id = str(submitted.get("connector_run_id") or "").strip()
    _assert(run_id, "run submission did not return connector_run_id")
    detail = _poll_run_detail(runtime.client, run_id)
    _assert(str(detail.get("status") or "") == "completed", f"run ended in unexpected status: {detail.get('status')}")
    _assert(int(detail.get("discovered_count") or 0) == total_docs, f"run did not discover {total_docs} documents")
    _assert(int(detail.get("selected_count") or 0) == total_docs, f"run did not select {total_docs} documents")
    _assert(int(detail.get("downloaded_count") or 0) == total_docs, f"run did not download {total_docs} documents")
    _assert(int(detail.get("failed_count") or 0) == 0, "run reported failed targets")
    _assert(int(detail.get("terminal_target_count") or 0) == total_docs, "not all targets reached a terminal state")
    _assert(int(detail.get("nonterminal_target_count") or 0) == 0, "run left nonterminal targets")

    report_refs = dict(detail.get("report_refs") or {})
    artifact_ingestion_ref = str(report_refs.get("aps_artifact_ingestion") or "").strip()
    content_index_ref = str(report_refs.get("aps_content_index") or "").strip()
    _assert(artifact_ingestion_ref, "run detail missing aps_artifact_ingestion ref")
    _assert(content_index_ref, "run detail missing aps_content_index ref")
    _assert(report_refs.get("aps_artifact_ingestion_failure") in (None, ""), "run detail unexpectedly reported aps_artifact_ingestion_failure")
    _assert(report_refs.get("aps_content_index_failure") in (None, ""), "run detail unexpectedly reported aps_content_index_failure")
    _assert(Path(artifact_ingestion_ref).exists(), f"aps_artifact_ingestion ref missing on disk: {artifact_ingestion_ref}")
    _assert(Path(content_index_ref).exists(), f"aps_content_index ref missing on disk: {content_index_ref}")
    artifact_run_payload = _read_json(Path(artifact_ingestion_ref))
    _assert(len(list(artifact_run_payload.get("target_artifacts") or [])) == total_docs, f"artifact-ingestion run artifact did not carry {total_docs} target rows")

    targets = _collect_all_targets(runtime.client, run_id)
    _assert(len(targets) == total_docs, f"targets route did not return {total_docs} target rows")
    _assert(all(str(row.get("status") or "").strip() not in {"failed", "cancelled"} for row in targets), "targets route exposed failed/cancelled targets")

    content_units = _collect_all_content_units(runtime.client, run_id)
    _assert(content_units, "content-units route returned no persisted rows")
    distinct_pairs = {
        (str(item.get("target_id") or "").strip(), str(item.get("content_id") or "").strip())
        for item in content_units
        if str(item.get("target_id") or "").strip() and str(item.get("content_id") or "").strip()
    }
    _assert(len(distinct_pairs) >= 2, "fewer than two distinct (target_id, content_id) pairs were persisted")

    token = _extract_search_token(content_units)
    search_payload = _post_json(runtime.client, "/api/v1/connectors/nrc-adams-aps/content-search", {"query": token, "run_id": run_id, "limit": 10, "offset": 0})
    _assert(int(search_payload.get("total") or 0) >= 1, "content-search smoke returned no hits")

    selected_rows = _select_downstream_rows(content_units)
    bundle_a = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/evidence-bundles", get_path="/api/v1/connectors/nrc-adams-aps/evidence-bundles/{artifact_id}", payload={"run_id": run_id, "target_ids": [selected_rows[0]["target_id"]], "persist_bundle": True}, id_key="bundle_id", ref_key="bundle_ref")
    bundle_b = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/evidence-bundles", get_path="/api/v1/connectors/nrc-adams-aps/evidence-bundles/{artifact_id}", payload={"run_id": run_id, "target_ids": [selected_rows[1]["target_id"]], "persist_bundle": True}, id_key="bundle_id", ref_key="bundle_ref")
    citation_pack_a = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/citation-packs", get_path="/api/v1/connectors/nrc-adams-aps/citation-packs/{artifact_id}", payload={"bundle_id": bundle_a["created"]["bundle_id"], "persist_pack": True}, id_key="citation_pack_id", ref_key="citation_pack_ref")
    citation_pack_b = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/citation-packs", get_path="/api/v1/connectors/nrc-adams-aps/citation-packs/{artifact_id}", payload={"bundle_id": bundle_b["created"]["bundle_id"], "persist_pack": True}, id_key="citation_pack_id", ref_key="citation_pack_ref")
    evidence_report_a = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/evidence-reports", get_path="/api/v1/connectors/nrc-adams-aps/evidence-reports/{artifact_id}", payload={"citation_pack_id": citation_pack_a["created"]["citation_pack_id"], "persist_report": True}, id_key="evidence_report_id", ref_key="evidence_report_ref")
    evidence_report_b = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/evidence-reports", get_path="/api/v1/connectors/nrc-adams-aps/evidence-reports/{artifact_id}", payload={"citation_pack_id": citation_pack_b["created"]["citation_pack_id"], "persist_report": True}, id_key="evidence_report_id", ref_key="evidence_report_ref")
    export_a = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/evidence-report-exports", get_path="/api/v1/connectors/nrc-adams-aps/evidence-report-exports/{artifact_id}", payload={"evidence_report_id": evidence_report_a["created"]["evidence_report_id"], "persist_export": True}, id_key="evidence_report_export_id", ref_key="evidence_report_export_ref")
    export_b = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/evidence-report-exports", get_path="/api/v1/connectors/nrc-adams-aps/evidence-report-exports/{artifact_id}", payload={"evidence_report_id": evidence_report_b["created"]["evidence_report_id"], "persist_export": True}, id_key="evidence_report_export_id", ref_key="evidence_report_export_ref")
    export_package = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/evidence-report-export-packages", get_path="/api/v1/connectors/nrc-adams-aps/evidence-report-export-packages/{artifact_id}", payload={"evidence_report_export_ids": [export_a["created"]["evidence_report_export_id"], export_b["created"]["evidence_report_export_id"]], "persist_package": True}, id_key="evidence_report_export_package_id", ref_key="evidence_report_export_package_ref")
    package_context_packet = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/context-packets", get_path="/api/v1/connectors/nrc-adams-aps/context-packets/{artifact_id}", payload={"evidence_report_export_package_id": export_package["created"]["evidence_report_export_package_id"], "persist_context_packet": True}, id_key="context_packet_id", ref_key="context_packet_ref")
    export_context_packet_a = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/context-packets", get_path="/api/v1/connectors/nrc-adams-aps/context-packets/{artifact_id}", payload={"evidence_report_export_id": export_a["created"]["evidence_report_export_id"], "persist_context_packet": True}, id_key="context_packet_id", ref_key="context_packet_ref")
    export_context_packet_b = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/context-packets", get_path="/api/v1/connectors/nrc-adams-aps/context-packets/{artifact_id}", payload={"evidence_report_export_id": export_b["created"]["evidence_report_export_id"], "persist_context_packet": True}, id_key="context_packet_id", ref_key="context_packet_ref")
    context_dossier = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/context-dossiers", get_path="/api/v1/connectors/nrc-adams-aps/context-dossiers/{artifact_id}", payload={"context_packet_ids": [export_context_packet_a["created"]["context_packet_id"], export_context_packet_b["created"]["context_packet_id"]], "persist_dossier": True}, id_key="context_dossier_id", ref_key="context_dossier_ref")
    insight_artifact = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/deterministic-insight-artifacts", get_path="/api/v1/connectors/nrc-adams-aps/deterministic-insight-artifacts/{artifact_id}", payload={"context_dossier_id": context_dossier["created"]["context_dossier_id"], "persist_insight_artifact": True}, id_key="deterministic_insight_artifact_id", ref_key="deterministic_insight_artifact_ref")
    challenge_artifact = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/deterministic-challenge-artifacts", get_path="/api/v1/connectors/nrc-adams-aps/deterministic-challenge-artifacts/{artifact_id}", payload={"deterministic_insight_artifact_id": insight_artifact["created"]["deterministic_insight_artifact_id"], "persist_challenge_artifact": True}, id_key="deterministic_challenge_artifact_id", ref_key="deterministic_challenge_artifact_ref")
    review_packet = _create_persisted_artifact(runtime.client, post_path="/api/v1/connectors/nrc-adams-aps/deterministic-challenge-review-packets", get_path="/api/v1/connectors/nrc-adams-aps/deterministic-challenge-review-packets/{artifact_id}", payload={"deterministic_challenge_artifact_id": challenge_artifact["created"]["deterministic_challenge_artifact_id"], "persist_review_packet": True}, id_key="deterministic_challenge_review_packet_id", ref_key="deterministic_challenge_review_packet_ref")

    _assert(str(package_context_packet["created"].get("source_family") or "") == "evidence_report_export_package", "package-derived context packet did not use evidence_report_export_package source_family")
    _assert(str(export_context_packet_a["created"].get("source_family") or "") == "evidence_report_export", "export-derived context packet A did not use evidence_report_export source_family")
    _assert(str(export_context_packet_b["created"].get("source_family") or "") == "evidence_report_export", "export-derived context packet B did not use evidence_report_export source_family")
    _assert(int(context_dossier["created"].get("source_packet_count") or 0) == 2, "context dossier did not retain two source packets")
    review_created = review_packet["created"]
    _assert(int(review_created.get("total_challenges") or 0) == int(review_created.get("blocker_count") or 0) + int(review_created.get("review_item_count") or 0) + int(review_created.get("acknowledgement_count") or 0), "review packet challenge category counts do not add up")

    detail_after_chain = _get_json(runtime.client, f"/api/v1/connectors/runs/{run_id}")
    _verify_report_ref_set(detail_after_chain, "aps_evidence_bundles", [bundle_a["created"]["bundle_ref"], bundle_b["created"]["bundle_ref"]])
    _verify_report_ref_set(detail_after_chain, "aps_evidence_citation_packs", [citation_pack_a["created"]["citation_pack_ref"], citation_pack_b["created"]["citation_pack_ref"]])
    _verify_report_ref_set(detail_after_chain, "aps_evidence_reports", [evidence_report_a["created"]["evidence_report_ref"], evidence_report_b["created"]["evidence_report_ref"]])
    _verify_report_ref_set(detail_after_chain, "aps_evidence_report_exports", [export_a["created"]["evidence_report_export_ref"], export_b["created"]["evidence_report_export_ref"]])
    _verify_report_ref_set(detail_after_chain, "aps_evidence_report_export_packages", [export_package["created"]["evidence_report_export_package_ref"]])
    _verify_report_ref_set(detail_after_chain, "aps_context_packets", [package_context_packet["created"]["context_packet_ref"], export_context_packet_a["created"]["context_packet_ref"], export_context_packet_b["created"]["context_packet_ref"]])
    _verify_report_ref_set(detail_after_chain, "aps_context_dossiers", [context_dossier["created"]["context_dossier_ref"]])
    _verify_report_ref_set(detail_after_chain, "aps_deterministic_insight_artifacts", [insight_artifact["created"]["deterministic_insight_artifact_ref"]])
    _verify_report_ref_set(detail_after_chain, "aps_deterministic_challenge_artifacts", [challenge_artifact["created"]["deterministic_challenge_artifact_ref"]])
    _verify_report_ref_set(detail_after_chain, "aps_deterministic_challenge_review_packets", [review_packet["created"]["deterministic_challenge_review_packet_ref"]])

    for failure_key in ("aps_evidence_bundle_failures", "aps_evidence_citation_pack_failures", "aps_evidence_report_failures", "aps_evidence_report_export_failures", "aps_evidence_report_export_package_failures", "aps_context_packet_failures", "aps_context_dossier_failures", "aps_deterministic_insight_artifact_failures", "aps_deterministic_challenge_artifact_failures", "aps_deterministic_challenge_review_packet_failures"):
        _verify_failure_ref_list(detail_after_chain, failure_key)

    gate_results = _run_gate_scripts(runtime, run_id, runtime_root)
    advanced_metrics = _collect_advanced_metrics(runtime, run_id, docs)

    session = runtime.session_factory()
    try:
        target_rows = session.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).order_by(ConnectorRunTarget.ordinal.asc()).all()
        target_outcomes = [
            {
                "target_id": str(row.connector_run_target_id),
                "ordinal": int(row.ordinal or 0),
                "status": str(row.status or ""),
                "accession_number": str(row.sciencebase_item_id or ""),
                "artifact_ref": str(dict(row.source_reference_json or {}).get("aps_artifact_ingestion_ref") or ""),
            }
            for row in target_rows
        ]
    finally:
        session.close()

    skips = [_coerce_int(payload.get("skip"), 0) for payload in fake_client.search_payloads]
    takes = [
        max(1, _coerce_int(payload.get("take"), _coerce_int(payload.get("page_size"), 100)))
        for payload in fake_client.search_payloads
    ]
    expected_skips = list(range(0, total_docs, page_size))
    _assert(sorted(set(skips)) == expected_skips, f"unexpected search skip sequence: {skips}")
    _assert(all(take == page_size for take in takes), f"unexpected search take values: {takes}")
    _assert(len(fake_client.document_ids) == total_docs, f"expected {total_docs} document detail fetches, observed {len(fake_client.document_ids)}")
    _assert(len(fake_client.download_urls) == total_docs, f"expected {total_docs} artifact downloads, observed {len(fake_client.download_urls)}")

    return {
        "run_id": run_id,
        "submission": {"connector_run_id": run_id, "status": submitted.get("status"), "poll_url": submitted.get("poll_url"), "idempotency_key": idempotency_key},
        "run_detail": detail_after_chain,
        "search_smoke": {"token": token, "hit_count": int(search_payload.get("total") or 0)},
        "selected_branch_rows": [{"target_id": str(row.get("target_id") or ""), "content_id": str(row.get("content_id") or ""), "chunk_id": str(row.get("chunk_id") or ""), "accession_number": str(row.get("accession_number") or "")} for row in selected_rows],
        "downstream_artifacts": {
            "evidence_bundles": [{"id": bundle_a["created"]["bundle_id"], "ref": bundle_a["created"]["bundle_ref"]}, {"id": bundle_b["created"]["bundle_id"], "ref": bundle_b["created"]["bundle_ref"]}],
            "citation_packs": [{"id": citation_pack_a["created"]["citation_pack_id"], "ref": citation_pack_a["created"]["citation_pack_ref"]}, {"id": citation_pack_b["created"]["citation_pack_id"], "ref": citation_pack_b["created"]["citation_pack_ref"]}],
            "evidence_reports": [{"id": evidence_report_a["created"]["evidence_report_id"], "ref": evidence_report_a["created"]["evidence_report_ref"]}, {"id": evidence_report_b["created"]["evidence_report_id"], "ref": evidence_report_b["created"]["evidence_report_ref"]}],
            "evidence_report_exports": [{"id": export_a["created"]["evidence_report_export_id"], "ref": export_a["created"]["evidence_report_export_ref"]}, {"id": export_b["created"]["evidence_report_export_id"], "ref": export_b["created"]["evidence_report_export_ref"]}],
            "evidence_report_export_packages": [{"id": export_package["created"]["evidence_report_export_package_id"], "ref": export_package["created"]["evidence_report_export_package_ref"]}],
            "context_packets": [{"id": package_context_packet["created"]["context_packet_id"], "ref": package_context_packet["created"]["context_packet_ref"]}, {"id": export_context_packet_a["created"]["context_packet_id"], "ref": export_context_packet_a["created"]["context_packet_ref"]}, {"id": export_context_packet_b["created"]["context_packet_id"], "ref": export_context_packet_b["created"]["context_packet_ref"]}],
            "context_dossiers": [{"id": context_dossier["created"]["context_dossier_id"], "ref": context_dossier["created"]["context_dossier_ref"]}],
            "deterministic_insight_artifacts": [{"id": insight_artifact["created"]["deterministic_insight_artifact_id"], "ref": insight_artifact["created"]["deterministic_insight_artifact_ref"]}],
            "deterministic_challenge_artifacts": [{"id": challenge_artifact["created"]["deterministic_challenge_artifact_id"], "ref": challenge_artifact["created"]["deterministic_challenge_artifact_ref"]}],
            "deterministic_challenge_review_packets": [{"id": review_packet["created"]["deterministic_challenge_review_packet_id"], "ref": review_packet["created"]["deterministic_challenge_review_packet_ref"]}],
        },
        "gate_results": gate_results,
        "advanced_metrics": advanced_metrics,
        "target_outcomes": target_outcomes,
        "client_trace": {"search_call_count": len(fake_client.search_payloads), "search_skips": skips, "search_takes": takes, "document_fetch_count": len(fake_client.document_ids), "download_count": len(fake_client.download_urls)},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local NRC APS corpus through the live downstream chain in an isolated runtime.")
    parser.add_argument(
        "--runtime-root",
        default="",
        help=f"Optional empty runtime directory under {DEFAULT_RUNTIME_PARENT}. If omitted, the tool creates a fresh timestamped runtime.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime_root = _resolve_runtime_root(args.runtime_root)
    summary_path = runtime_root / "local_corpus_e2e_summary.json"
    summary: dict[str, Any] = {
        "schema_id": SUMMARY_SCHEMA_ID,
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generated_at_utc": _utc_iso(),
        "passed": False,
        "runtime_root": str(runtime_root),
        "database_path": None,
        "database_url": None,
        "storage_dir": None,
        "interpreter_path": str(Path(sys.executable).resolve()),
        "run_id": None,
        "corpus_root": str(DEFAULT_CORPUS_ROOT),
        "corpus_pdf_count": 0,
        "preflight": {},
        "submission": {},
        "run_detail": {},
        "search_smoke": {},
        "selected_branch_rows": [],
        "downstream_artifacts": {},
        "gate_results": {},
        "advanced_metrics": {},
        "client_trace": {},
        "observed_non_blocking_findings": [],
        "failure": None,
    }

    exit_code = 1
    try:
        docs, preflight, findings = _run_preflight(runtime_root)
        summary["preflight"] = preflight
        summary["corpus_pdf_count"] = len(docs)
        summary["observed_non_blocking_findings"] = findings
        runtime_root.mkdir(parents=True, exist_ok=True)

        fake_client = LocalCorpusNrcClient(docs)
        with _isolated_runtime(fake_client, runtime_root) as runtime:
            summary["database_path"] = str(runtime.database_path)
            summary["database_url"] = runtime.env["DATABASE_URL"]
            summary["storage_dir"] = str(runtime.storage_dir)
            proof_payload = _execute_proof(runtime, docs, runtime_root, fake_client)
            summary.update(proof_payload)
            summary["run_id"] = proof_payload["run_id"]
            summary["passed"] = True
            exit_code = 0
    except Exception as exc:  # noqa: BLE001
        summary["failure"] = {
            "error_class": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        if _ALEMBIC_STUB_INSTALLED and not any(
            str(item.get("code") or "") == ALEMBIC_STUB_FINDING["code"]
            for item in summary["observed_non_blocking_findings"]
            if isinstance(item, dict)
        ):
            summary["observed_non_blocking_findings"].append(dict(ALEMBIC_STUB_FINDING))
        summary["generated_at_utc"] = _utc_iso()
        _write_json(summary_path, summary)
        print(str(summary_path))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
