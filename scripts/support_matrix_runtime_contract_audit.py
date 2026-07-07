from __future__ import annotations

import argparse
import ast
import contextlib
import functools
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = REPO_ROOT / "backend"
CONFIG_PATH = BACKEND_ROOT / "app" / "core" / "config.py"
MATRIX_PATH = REPO_ROOT / "config" / "support_matrix.yaml"
SEC_AUDIT_PATH = REPO_ROOT / "scripts" / "sec_xbrl_offline_honesty_audit.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from support_matrix_constants import EXPECTED_STATUS_BY_ID, PINNED_FALSE_FLAGS

SEC_DELEGATED_CAPABILITIES = {
    "sec_value_reveal",
    "sec_controlled_value_reveal_submit",
    "arelle_internal_value_store",
    "arelle_corpus_validation",
    "sec_xbrl_production_admission_evaluator",
    "sec_offline_replay_path",
    "layer3_sec_xbrl_offline_evidence_loader",
    "layer3_sec_xbrl_offline_companyfacts_stage",
    "layer3_sec_xbrl_offline_companyfacts_oracle_packet",
    "layer3_sec_xbrl_e2e_offline_orchestrator",
    "layer3_sec_xbrl_offline_evidence_proof_capability",
    "offline_staged_redaction_value_store_resolution",
}


class MatrixContractError(RuntimeError):
    pass


class _FakeScienceBaseAdapter:
    def search_page(self, *, q: str, filters: list[Any], offset: int, page_size: int, sort: str, order: str) -> Any:
        items = [] if offset else [{"id": "item-1"}]
        return type(
            "SearchPage",
            (),
            {
                "items": items,
                "offset": offset,
                "page_size": page_size,
                "total": len(items),
                "nextlink": None,
                "prevlink": None,
                "raw_query_metadata": {},
            },
        )()

    def hydrate_item(self, item_id: str) -> dict[str, Any]:
        return {
            "id": item_id,
            "title": "Runtime Contract Item",
            "identifiers": [{"type": "DOI", "value": "10.1234/runtime-contract"}],
            "files": [{"name": "contract.csv", "downloadUri": "https://www.sciencebase.gov/catalog/file/contract.csv"}],
            "distributionLinks": [],
            "webLinks": [],
        }

    def extract_artifacts(self, item: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "surface": "files",
                "name": raw["name"],
                "url": raw["downloadUri"],
                "locator_type": "downloadUri",
                "checksum_type": None,
                "checksum_value": None,
                "source_reference": raw,
            }
            for raw in item.get("files", [])
        ]

    def download_artifact(self, *, url: str, timeout_seconds: int, max_redirects: int, headers: dict[str, str] | None = None) -> Any:
        content = b"year,value\n2023,1\n2024,2\n2025,3\n"
        return type(
            "DownloadResult",
            (),
            {
                "content": content,
                "status_code": 200,
                "final_url": url,
                "redirect_count": 0,
                "etag": "runtime-contract-etag",
                "last_modified": "Mon, 01 Jan 2024 00:00:00 GMT",
                "content_type": "text/csv",
                "sha256": "runtime_contract_csv_sha",
                "headers": {},
                "resolved_ip": "8.8.8.8",
            },
        )()


class _FakeSenateLdaClient:
    auth_mode = "anonymous"

    def __init__(self) -> None:
        self.detail_calls: list[str] = []

    def list_filings(self, **kwargs: Any) -> dict[str, Any]:
        page = int(dict(kwargs.get("params") or {}).get("page", 1))
        if page > 1:
            return {"count": 1, "next": None, "previous": None, "results": []}
        return {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "filing_uuid": "runtime-filing-1",
                    "url": "https://lda.senate.gov/api/v1/filings/runtime-filing-1/",
                    "filing_type": "LD-2",
                    "filing_year": 2025,
                    "filing_period": "mid_year",
                    "dt_posted": "2025-07-01",
                    "filing_document_url": "https://lda.senate.gov/runtime-filing-1.pdf",
                    "filing_document_content_type": "application/pdf",
                    "registrant": {"name": "Runtime Registrant"},
                    "client": {"name": "Runtime Client"},
                }
            ],
        }

    def get_filing_detail(self, *, filing_uuid: str, **kwargs: Any) -> dict[str, Any]:
        self.detail_calls.append(filing_uuid)
        return {
            "filing_uuid": filing_uuid,
            "url": f"https://lda.senate.gov/api/v1/filings/{filing_uuid}/",
            "filing_type": "LD-2",
            "filing_year": 2025,
            "filing_period": "mid_year",
            "dt_posted": "2025-07-01",
            "filing_document_url": f"https://lda.senate.gov/{filing_uuid}.pdf",
            "filing_document_content_type": "application/pdf",
            "registrant": {"name": "Runtime Registrant"},
            "client": {"name": "Runtime Client"},
        }


class _FakeWorldBankClient:
    auth_mode = "anonymous"

    def list_sources(self, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"id": "2", "name": "World Development Indicators"}]

    def list_indicators(self, *, source_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"id": "SP.POP.TOTL", "name": "Population, total", "source": {"id": source_id}}]

    def list_countries(self, *, countries: list[str], **kwargs: Any) -> list[dict[str, Any]]:
        return [{"id": country, "name": country} for country in countries]

    def list_indicator_observations(self, *, country: str, indicator: str, **kwargs: Any) -> list[dict[str, Any]]:
        return [
            {
                "countryiso3code": country,
                "date": "2022",
                "value": 333287557,
                "indicator": {"id": indicator, "value": "Population, total"},
                "country": {"id": country[:2], "value": country},
            }
        ]


class _FakeCftcCotClient:
    auth_mode = "anonymous"

    def download_artifact(self, *, url: str, timeout_seconds: int, max_redirects: int, headers: dict[str, str] | None = None, rate_limiter: Any = None, retry_counters: dict[str, Any] | None = None, **_kwargs: Any) -> Any:
        if retry_counters is not None:
            retry_counters["requests_total"] = int(retry_counters.get("requests_total", 0)) + 1
        content = (
            "Market_and_Exchange_Names,As_of_Date_In_Form_YYMMDD,As_of_Date_Form_YYYY-MM-DD,"
            "CFTC_Contract_Market_Code,CFTC_Market_Code,CFTC_Region_Code,CFTC_Commodity_Code,"
            "Open_Interest_All,Noncommercial_Positions_Long_All,Noncommercial_Positions_Short_All,"
            "Noncommercial_Positions_Spreading_All,Commercial_Positions_Long_All,Commercial_Positions_Short_All,"
            "Total_Reportable_Positions_Long_All,Total_Reportable_Positions_Short_All,"
            "Nonreportable_Positions_Long_All,Nonreportable_Positions_Short_All\n"
            "RUNTIME WHEAT - CHICAGO BOARD OF TRADE,240625,2024-06-25,001602,001,0,001,"
            "400000,100000,50000,25000,150000,175000,275000,250000,125000,150000\n"
        ).encode("utf-8")
        from app.services.sciencebase_connector.contracts import DownloadResult

        return DownloadResult(
            content=content,
            status_code=200,
            final_url=url,
            redirect_count=0,
            etag="runtime-cftc-etag",
            last_modified="Mon, 01 Jul 2024 00:00:00 GMT",
            content_type="text/plain; charset=utf-8",
            sha256="runtime_cftc_cot_sha",
            headers={},
            resolved_ip="8.8.8.8",
        )


def _load_json_compatible_yaml(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@contextlib.contextmanager
def _temporary_env(name: str, value: str) -> Iterator[None]:
    old_value = os.environ.get(name)
    had_value = name in os.environ
    os.environ[name] = value
    try:
        yield
    finally:
        if had_value and old_value is not None:
            os.environ[name] = old_value
        else:
            os.environ.pop(name, None)


def _load_sec_audit() -> Any:
    spec = importlib.util.spec_from_file_location("sec_xbrl_offline_honesty_audit", SEC_AUDIT_PATH)
    if spec is None or spec.loader is None:
        raise MatrixContractError(f"Cannot load SEC XBRL audit: {SEC_AUDIT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=1)
def _sec_audit_report() -> dict[str, Any]:
    report = _load_sec_audit().build_report()
    if report.get("status") != "pass":
        raise MatrixContractError(f"SEC XBRL delegated audit failed: {report.get('errors')}")
    return report


def _path_ref_from_evidence_token(token: str) -> str | None:
    raw = token.strip()
    if not raw or raw.startswith("PR-"):
        return None
    candidate = raw.split("::", 1)[0].split(":", 1)[0].strip()
    if candidate.startswith(("./", "README.md", "backend/", "tests/", "docs/", "config/")):
        return candidate[2:] if candidate.startswith("./") else candidate
    return None


def _evidence_check(capability: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    refs = []
    missing = []
    for token in str(capability.get("evidence") or "").split(";"):
        path_ref = _path_ref_from_evidence_token(token)
        if path_ref is None:
            continue
        refs.append(path_ref)
        if not (repo_root / path_ref).exists():
            missing.append(path_ref)
    if not refs:
        missing.append("<no file evidence refs>")
    return {"file_refs": refs, "missing_refs": missing, "passed": not missing}


def _settings_default_by_alias() -> dict[str, Any]:
    def literal_or_none(node: ast.AST) -> Any:
        try:
            return ast.literal_eval(node)
        except (TypeError, ValueError):
            return None

    tree = ast.parse(CONFIG_PATH.read_text(encoding="utf-8"), filename=str(CONFIG_PATH))
    defaults: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Settings":
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.value, ast.Call):
                continue
            call = statement.value
            if not isinstance(call.func, ast.Name) or call.func.id != "Field":
                continue
            alias = None
            default = None
            for keyword in call.keywords:
                if keyword.arg == "alias":
                    alias = literal_or_none(keyword.value)
                elif keyword.arg == "default":
                    default = literal_or_none(keyword.value)
            if alias:
                defaults[str(alias)] = default
        break
    return defaults


@contextlib.contextmanager
def _runtime_db() -> Iterator[tuple[Any, Path]]:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import bootstrap_storage_tree, settings
    from app.db.session import Base

    with tempfile.TemporaryDirectory(prefix="support_matrix_runtime_") as raw:
        root = Path(raw)
        storage = root / "storage"
        old_storage = settings.storage_dir
        settings.storage_dir = str(storage)
        bootstrap_storage_tree(storage)
        engine = create_engine(f"sqlite:///{(root / 'runtime.db').as_posix()}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        try:
            yield session_factory, storage
        finally:
            settings.storage_dir = old_storage
            engine.dispose()


def _probe_sec_delegated() -> dict[str, Any]:
    report = _sec_audit_report()
    return {"delegated_to": "sec_xbrl_offline_honesty_audit", "status": report["status"]}


def _probe_method_analytics() -> dict[str, Any]:
    import pandas as pd
    from app.services.analysis import SUPPORTED_ANALYSIS_METHOD_IDS, _descriptive_column_summary, analysis_method_registry

    registry = analysis_method_registry()
    summary = _descriptive_column_summary(pd.Series([1, 2, 3]), is_time_column=False)
    if "descriptive_summary" not in registry or summary.get("inferred_class") != "numeric":
        raise MatrixContractError("descriptive summary runtime contract failed")
    return {"methods": list(SUPPORTED_ANALYSIS_METHOD_IDS), "summary_mean": summary["numeric_summary"]["mean"]}


@functools.lru_cache(maxsize=1)
def _sciencebase_runtime() -> dict[str, Any]:
    from app.models import ConnectorRunTarget
    from app.services import connectors_sciencebase as sb

    with _runtime_db() as (session_factory, _storage):
        db = session_factory()
        old_session_local = sb.SessionLocal
        old_adapter = sb.get_sciencebase_adapter
        old_resolve_host = sb._resolve_host_ip
        try:
            sb.SessionLocal = session_factory
            sb.get_sciencebase_adapter = lambda config: _FakeScienceBaseAdapter()
            sb._resolve_host_ip = lambda hostname: "8.8.8.8"
            run, _created = sb.submit_connector_run(
                db,
                connector_key="sciencebase_public",
                payload={"q": "runtime", "run_mode": "one_shot_import", "allowed_extensions": [".csv"], "max_items": 1},
                idempotency_key="support-matrix-sciencebase-runtime",
            )
            db.commit()
            run_id = run.connector_run_id
            db.close()
            sb.execute_connector_run(run_id)
            db = session_factory()
            run = db.get(type(run), run_id)
            if run is None:
                raise MatrixContractError("sciencebase run missing after execution")
            detail = sb.serialize_connector_run(db, run)
            events = sb.list_connector_run_events(db, connector_run_id=run_id)
            targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).all()
            if detail.get("status") != "completed" or not targets:
                raise MatrixContractError(f"sciencebase run did not complete: {detail}")
            return {"detail": detail, "events_total": events["total"], "target_statuses": sorted({t.status for t in targets})}
        finally:
            sb.SessionLocal = old_session_local
            sb.get_sciencebase_adapter = old_adapter
            sb._resolve_host_ip = old_resolve_host
            db.close()


@functools.lru_cache(maxsize=1)
def _senate_runtime() -> dict[str, Any]:
    from app.models import ConnectorRunTarget
    from app.services import connectors_senate_lda as senate
    from app.services import connectors_sciencebase as sb

    with _runtime_db() as (session_factory, _storage):
        db = session_factory()
        old_session_local = senate.SessionLocal
        old_client = senate.get_senate_lda_client
        old_sleep = senate.time.sleep
        old_wait = senate._RateLimiter.wait
        try:
            senate.SessionLocal = session_factory
            senate.get_senate_lda_client = lambda config: _FakeSenateLdaClient()
            senate.time.sleep = lambda seconds: None
            senate._RateLimiter.wait = lambda self: None
            run, _created = senate.submit_senate_lda_run(
                db,
                payload={"client_name": "Runtime", "filing_year": 2025, "page_size": 25, "max_items": 1, "include_filing_detail": False},
                idempotency_key="support-matrix-senate-runtime",
            )
            db.commit()
            run_id = run.connector_run_id
            db.close()
            senate.execute_senate_lda_run(run_id)
            db = session_factory()
            run = db.get(type(run), run_id)
            if run is None:
                raise MatrixContractError("senate run missing after execution")
            detail = sb.serialize_connector_run(db, run)
            targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).all()
            auth_mode = dict(run.effective_search_params_json or {}).get("auth_mode")
            if detail.get("status") != "completed" or auth_mode != "anonymous" or not targets:
                raise MatrixContractError(f"senate run did not complete anonymously: {detail}")
            return {"detail": detail, "target_statuses": sorted({t.status for t in targets}), "auth_mode": auth_mode}
        finally:
            senate.SessionLocal = old_session_local
            senate.get_senate_lda_client = old_client
            senate.time.sleep = old_sleep
            senate._RateLimiter.wait = old_wait
            db.close()


@functools.lru_cache(maxsize=1)
def _worldbank_runtime() -> dict[str, Any]:
    from app.models import ConnectorRunTarget
    from app.services import connectors_sciencebase as sb
    from app.services import connectors_worldbank as wb

    with _runtime_db() as (session_factory, _storage):
        db = session_factory()
        old_session_local = wb.SessionLocal
        old_client = wb.get_worldbank_client
        old_sleep = wb.time.sleep
        old_wait = wb._RateLimiter.wait
        try:
            wb.SessionLocal = session_factory
            wb.get_worldbank_client = lambda config: _FakeWorldBankClient()
            wb.time.sleep = lambda seconds: None
            wb._RateLimiter.wait = lambda self: None
            run, _created = wb.submit_worldbank_run(
                db,
                payload={"indicators": ["SP.POP.TOTL"], "countries": ["USA"], "date_range": "2022:2022", "max_items": 1},
                idempotency_key="support-matrix-worldbank-runtime",
            )
            db.commit()
            run_id = run.connector_run_id
            db.close()
            wb.execute_worldbank_run(run_id)
            db = session_factory()
            run = db.get(type(run), run_id)
            if run is None:
                raise MatrixContractError("worldbank run missing after execution")
            detail = sb.serialize_connector_run(db, run)
            targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).all()
            auth_mode = dict(run.effective_search_params_json or {}).get("auth_mode")
            if detail.get("status") != "completed" or auth_mode != "anonymous" or not targets:
                raise MatrixContractError(f"worldbank run did not complete anonymously: {detail}")
            return {"detail": detail, "target_statuses": sorted({t.status for t in targets}), "auth_mode": auth_mode}
        finally:
            wb.SessionLocal = old_session_local
            wb.get_worldbank_client = old_client
            wb.time.sleep = old_sleep
            wb._RateLimiter.wait = old_wait
            db.close()


@functools.lru_cache(maxsize=1)
def _cftc_cot_runtime() -> dict[str, Any]:
    from app.models import ConnectorRunTarget
    from app.services import connectors_cftc_cot as cftc
    from app.services import connectors_sciencebase as sb

    with _runtime_db() as (session_factory, _storage):
        db = session_factory()
        old_session_local = cftc.SessionLocal
        old_client = cftc.get_cftc_cot_client
        old_resolve_host = cftc._resolve_host_ip
        old_sleep = cftc.time.sleep
        old_wait = cftc._RateLimiter.wait
        try:
            cftc.SessionLocal = session_factory
            cftc.get_cftc_cot_client = lambda config: _FakeCftcCotClient()
            cftc._resolve_host_ip = lambda hostname: "8.8.8.8"
            cftc.time.sleep = lambda seconds: None
            cftc._RateLimiter.wait = lambda self: None
            run, _created = cftc.submit_cftc_cot_run(
                db,
                payload={"report_variant": "legacy_futures_only", "max_rows": 1},
                idempotency_key="support-matrix-cftc-cot-runtime",
            )
            db.commit()
            run_id = run.connector_run_id
            db.close()
            cftc.execute_cftc_cot_run(run_id)
            db = session_factory()
            run = db.get(type(run), run_id)
            if run is None:
                raise MatrixContractError("cftc cot run missing after execution")
            detail = sb.serialize_connector_run(db, run)
            targets = db.query(ConnectorRunTarget).filter(ConnectorRunTarget.connector_run_id == run_id).all()
            auth_mode = dict(run.effective_search_params_json or {}).get("auth_mode")
            if detail.get("status") != "completed" or auth_mode != "anonymous" or not targets:
                raise MatrixContractError(f"cftc cot run did not complete anonymously: {detail}")
            return {"detail": detail, "target_statuses": sorted({t.status for t in targets}), "auth_mode": auth_mode}
        finally:
            cftc.SessionLocal = old_session_local
            cftc.get_cftc_cot_client = old_client
            cftc._resolve_host_ip = old_resolve_host
            cftc.time.sleep = old_sleep
            cftc._RateLimiter.wait = old_wait
            db.close()


def _probe_sciencebase() -> dict[str, Any]:
    result = _sciencebase_runtime()
    return {"status": result["detail"]["status"], "target_statuses": result["target_statuses"]}


def _probe_senate() -> dict[str, Any]:
    result = _senate_runtime()
    return {"status": result["detail"]["status"], "auth_mode": result["auth_mode"]}


def _probe_worldbank() -> dict[str, Any]:
    result = _worldbank_runtime()
    return {"status": result["detail"]["status"], "auth_mode": result["auth_mode"], "target_statuses": result["target_statuses"]}


def _probe_cftc_cot() -> dict[str, Any]:
    result = _cftc_cot_runtime()
    return {"status": result["detail"]["status"], "auth_mode": result["auth_mode"], "target_statuses": result["target_statuses"]}


def _probe_connector_observability() -> dict[str, Any]:
    result = _sciencebase_runtime()
    if result["events_total"] <= 0 or "report_refs" not in result["detail"]:
        raise MatrixContractError("connector observability fields missing")
    return {"events_total": result["events_total"], "report_refs": sorted(result["detail"]["report_refs"])}


def _probe_layer3_ui() -> dict[str, Any]:
    from fastapi.testclient import TestClient
    from main import app

    response = TestClient(app).get("/review/layer3")
    if response.status_code != 200 or "<title>Layer 3 Workbench</title>" not in response.text:
        raise MatrixContractError("Layer 3 workbench UI route failed")
    return {"status_code": response.status_code, "content_type": response.headers.get("content-type")}


def _probe_health_openapi() -> dict[str, Any]:
    from fastapi.testclient import TestClient
    import main

    with _runtime_db() as (session_factory, _storage):
        old_session_local = main.SessionLocal
        main.SessionLocal = session_factory
        try:
            client = TestClient(main.app)
            health = client.get("/health")
            ready = client.get("/ready")
            openapi = client.get("/openapi.json")
        finally:
            main.SessionLocal = old_session_local
    if health.status_code != 200 or ready.status_code != 200 or openapi.status_code != 200:
        raise MatrixContractError("health/ready/openapi runtime route failed")
    return {"health": health.json(), "ready": ready.json().get("status"), "openapi_paths": len(openapi.json().get("paths", {}))}


def _probe_analysis_inventory_off() -> dict[str, Any]:
    from app.core.config import settings
    from app.services import layer3_workbench

    old_value = settings.layer3_analysis_product_package_inventory_enabled
    settings.layer3_analysis_product_package_inventory_enabled = False
    try:
        payload = {"aps_evidence_bundle": {"existing": True}}
        result = layer3_workbench._merge_analysis_product_inventory_extras(None, "session-id", payload)
    finally:
        settings.layer3_analysis_product_package_inventory_enabled = old_value
    if result is not payload or "analysis_product_inventory" in json.dumps(result, sort_keys=True):
        raise MatrixContractError("analysis product inventory did not stay default-off")
    return {"enabled": False, "payload_unchanged": True}


def _probe_ocr_off() -> dict[str, Any]:
    from app.services import nrc_aps_document_processing as dp

    fixture = REPO_ROOT / "tests" / "fixtures" / "nrc_aps_docs" / "v1" / "scanned.pdf"
    old_available = dp.nrc_aps_ocr.tesseract_available
    old_run = dp.nrc_aps_ocr.run_tesseract_ocr
    old_advanced = dp.nrc_aps_advanced_ocr.run_advanced_ocr
    dp.nrc_aps_ocr.tesseract_available = lambda: False
    dp.nrc_aps_ocr.run_tesseract_ocr = lambda **kwargs: (_ for _ in ()).throw(AssertionError("ocr engine called"))
    dp.nrc_aps_advanced_ocr.run_advanced_ocr = lambda **kwargs: None
    try:
        try:
            dp.process_document(content=fixture.read_bytes(), declared_content_type="application/pdf")
        except ValueError as exc:
            if "ocr_required_but_unavailable" in str(exc):
                return {"blocked_error": "ocr_required_but_unavailable", "engine_called": False}
            raise
        raise MatrixContractError("OCR missing-engine path did not fail closed")
    finally:
        dp.nrc_aps_ocr.tesseract_available = old_available
        dp.nrc_aps_ocr.run_tesseract_ocr = old_run
        dp.nrc_aps_advanced_ocr.run_advanced_ocr = old_advanced


def _probe_nrc_replay() -> dict[str, Any]:
    from app.services import nrc_aps_replay_gate

    corpus = REPO_ROOT / "tests" / "fixtures" / "nrc_aps_replay" / "v1"
    with tempfile.TemporaryDirectory(prefix="nrc_replay_runtime_") as raw:
        report = nrc_aps_replay_gate.validate_replay_corpus(corpus_dir=corpus, report_path=Path(raw) / "report.json")
    if not report.passed or report.total_cases <= 0:
        raise MatrixContractError("NRC APS replay corpus validation failed")
    return {"passed": report.passed, "total_cases": report.total_cases, "failed_cases": report.failed_cases}


def _expect_workbench_error(fn: Callable[[], Any], code: str) -> dict[str, Any]:
    from app.services.layer3_workbench_error import Layer3WorkbenchError

    try:
        fn()
    except Layer3WorkbenchError as exc:
        if exc.error_code != code:
            raise MatrixContractError(f"expected {code}, got {exc.error_code}") from exc
        return {"error_code": exc.error_code, "http_status": exc.http_status, "status": exc.status}
    raise MatrixContractError(f"expected Layer3WorkbenchError {code}")


def _probe_sec_live_network_default_off() -> dict[str, Any]:
    from app.core.config import settings
    from app.services import layer3_sec_edgar_live_source_artifact as live
    from app.services.layer3_workbench_error import Layer3WorkbenchError

    class _AuditFakeSecClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def fetch_complete_submission_text(self, **kwargs: Any) -> Any:
            self.calls.append(dict(kwargs))
            return live.SecEdgarFetchResult(
                status_code=200,
                content=b"<SEC-DOCUMENT>support matrix live source artifact proof</SEC-DOCUMENT>\n",
                final_url=str(kwargs["url"]),
            )

    request = {
        "client_request_id": "support-matrix-sec-live-source-artifact",
        "acquisition_mode": "sec_edgar_text_table_live_source_artifact_acquisition_v1",
        "operator_decision": "acquire_sec_edgar_text_table_live_source_artifact",
        "cik_or_filer_ref": "0000320193",
        "accession_or_submission_id": "0000320193-24-000123",
        "form_type": "10-K",
        "filing_date": "2024-11-01",
        "operator_confirmation": True,
    }
    old_live_enabled = settings.layer3_sec_edgar_live_network_enabled
    old_user_agent = settings.layer3_sec_edgar_user_agent
    old_storage_dir = settings.storage_dir
    old_rate_limit = settings.layer3_sec_edgar_rate_limit_per_second
    old_max_live_requests = settings.layer3_sec_edgar_max_live_requests_per_process
    old_max_bytes = settings.layer3_sec_edgar_max_bytes
    old_timeout_seconds = settings.layer3_sec_edgar_timeout_seconds
    old_client = live.SEC_EDGAR_CLIENT
    old_sleep = live.SEC_EDGAR_SLEEP
    old_enforce_rate_limit = live._enforce_rate_limit
    with live._SEC_LIVE_REQUEST_COUNT_LOCK:
        old_live_request_count = live._SEC_LIVE_REQUEST_COUNT
    fake_client = _AuditFakeSecClient()
    with tempfile.TemporaryDirectory(prefix="sec_live_matrix_") as raw:
        try:
            settings.storage_dir = str(Path(raw) / "storage")
            settings.layer3_sec_edgar_live_network_enabled = False
            settings.layer3_sec_edgar_user_agent = ""
            settings.layer3_sec_edgar_rate_limit_per_second = 1
            settings.layer3_sec_edgar_max_live_requests_per_process = 10
            settings.layer3_sec_edgar_max_bytes = 25_000_000
            settings.layer3_sec_edgar_timeout_seconds = 20
            live.SEC_EDGAR_CLIENT = fake_client
            live.SEC_EDGAR_SLEEP = lambda _seconds: None
            live._enforce_rate_limit = lambda: None
            with live._SEC_LIVE_REQUEST_COUNT_LOCK:
                live._SEC_LIVE_REQUEST_COUNT = 0
            try:
                live.acquire_sec_edgar_text_table_live_source_artifact(request)
            except Layer3WorkbenchError as exc:
                disabled_codes = ("live_network_disabled", "ci_network_disabled")
                if not any(code in exc.error_code for code in disabled_codes):
                    raise MatrixContractError(f"expected live network disabled guard, got {exc.error_code}") from exc
                default_off_error = exc
            else:
                raise MatrixContractError("SEC live network acquisition unexpectedly succeeded while default-off")
            if fake_client.calls:
                raise MatrixContractError("SEC live network default-off guard allowed a fetch call")

            settings.layer3_sec_edgar_live_network_enabled = True
            settings.layer3_sec_edgar_user_agent = "Project6 Support Matrix contact@example.com"
            response = live.acquire_sec_edgar_text_table_live_source_artifact(request)
            visible_status = response["operator_visible_live_source_artifact_status"]
            return {
                "default_off_error_code": default_off_error.error_code,
                "default_off_http_status": default_off_error.http_status,
                "default_off_status": default_off_error.status,
                "default_off_fetch_calls": 0,
                "explicit_enabled_status": response["live_source_artifact_receipt_status"],
                "explicit_enabled_schema_id": response["schema_id"],
                "explicit_enabled_network_request_made": response["cache"]["network_request_made"],
                "explicit_enabled_fake_client_calls": len(fake_client.calls),
                "explicit_enabled_raw_url_exposed": visible_status["raw_url_exposed"],
                "explicit_enabled_raw_local_path_exposed": visible_status["raw_local_path_exposed"],
                "explicit_enabled_artifact_bytes_exposed": visible_status["artifact_bytes_exposed"],
                "production_readiness_claimed": False,
            }
        finally:
            with live._SEC_LIVE_REQUEST_COUNT_LOCK:
                live._SEC_LIVE_REQUEST_COUNT = old_live_request_count
            live.SEC_EDGAR_CLIENT = old_client
            live.SEC_EDGAR_SLEEP = old_sleep
            live._enforce_rate_limit = old_enforce_rate_limit
            settings.layer3_sec_edgar_live_network_enabled = old_live_enabled
            settings.layer3_sec_edgar_user_agent = old_user_agent
            settings.storage_dir = old_storage_dir
            settings.layer3_sec_edgar_rate_limit_per_second = old_rate_limit
            settings.layer3_sec_edgar_max_live_requests_per_process = old_max_live_requests
            settings.layer3_sec_edgar_max_bytes = old_max_bytes
            settings.layer3_sec_edgar_timeout_seconds = old_timeout_seconds


def _probe_real_provider_delivery_unsupported() -> dict[str, Any]:
    from app.services import layer3_provider_public_url

    return _expect_workbench_error(
        lambda: layer3_provider_public_url.provider_public_url_prepare(None, {"public_url": "https://example.invalid/file"}),
        "provider_public_url_prepare_scope_not_admitted",
    )


def _probe_model_egress_unsupported() -> dict[str, Any]:
    from app.services.layer3_egress_policy import EgressPolicyError, assert_executor_egress_allowed

    try:
        assert_executor_egress_allowed("agent", model_egress_enabled=False)
    except EgressPolicyError as exc:
        return {"error_code": exc.error_code, "http_status": exc.http_status}
    raise MatrixContractError("model egress unexpectedly allowed")


def _probe_nonlocal_unsupported() -> dict[str, Any]:
    from app.core.config import Settings

    try:
        Settings(DEPLOYMENT_MODE="nonlocal", ALLOWED_ORIGINS="*", AUTH_OWNER="none", DATABASE_URL="sqlite:///blocked.db")
    except ValueError as exc:
        return {"blocked": True, "message": str(exc).splitlines()[0]}
    raise MatrixContractError("nonlocal unsafe profile unexpectedly configured")


def _probe_ha_unsupported() -> dict[str, Any]:
    from app.services import connectors_sciencebase as sb
    from app.services.sciencebase_connector.contracts import SubmissionConflictError

    with _runtime_db() as (session_factory, _storage):
        db = session_factory()
        try:
            sb.submit_connector_run(db, connector_key="sciencebase_public", payload={"q": "one"}, idempotency_key="ha-one")
            db.commit()
            try:
                sb.submit_connector_run(db, connector_key="sciencebase_public", payload={"q": "two"}, idempotency_key="ha-two")
            except SubmissionConflictError as exc:
                return {"blocked": True, "error": str(exc)}
        finally:
            db.close()
    raise MatrixContractError("second active connector run was unexpectedly admitted")


def _probe_keyed_connectors_unsupported() -> dict[str, Any]:
    from app.core.config import settings
    from app.services import connectors_nrc_adams
    from app.services.sciencebase_connector.contracts import SubmissionConflictError

    old_key = settings.nrc_adams_subscription_key
    settings.nrc_adams_subscription_key = ""
    try:
        try:
            connectors_nrc_adams.get_nrc_adams_client({})
        except SubmissionConflictError as exc:
            return {"blocked": True, "error": str(exc), "senate_key_configured": bool(settings.senate_lda_api_key)}
    finally:
        settings.nrc_adams_subscription_key = old_key
    raise MatrixContractError("keyed NRC APS client was admitted without a subscription key")


def _probe_signed_reference_unsupported() -> dict[str, Any]:
    from app.services import layer3_workbench

    old_secret = os.environ.pop("LAYER3_SIGNED_REFERENCE_SECRET", None)
    try:
        return _expect_workbench_error(
            lambda: layer3_workbench.external_export_download_generate_signed_reference(None, {"client_request_id": "signed-ref"}),
            "external_export_download_signed_reference_secret_required",
        )
    finally:
        if old_secret is not None:
            os.environ["LAYER3_SIGNED_REFERENCE_SECRET"] = old_secret


PROBES: dict[str, Callable[[], dict[str, Any]]] = {
    "method_aware_analytics_vertical": _probe_method_analytics,
    "sciencebase_public_connector_slice": _probe_sciencebase,
    "senate_lda_anonymous_connector_slice": _probe_senate,
    "worldbank_indicators_anonymous_connector_slice": _probe_worldbank,
    "cftc_cot_anonymous_connector_slice": _probe_cftc_cot,
    "connector_run_observability": _probe_connector_observability,
    "layer3_workbench_ui": _probe_layer3_ui,
    "health_readiness_openapi": _probe_health_openapi,
    "analysis_product_package_inventory": _probe_analysis_inventory_off,
    "ocr_external_engine": _probe_ocr_off,
    "nrc_aps_replay_corpus_gate": _probe_nrc_replay,
    "sec_live_network_egress": _probe_sec_live_network_default_off,
    "real_provider_delivery": _probe_real_provider_delivery_unsupported,
    "model_agent_egress": _probe_model_egress_unsupported,
    "nonlocal_multi_trust_multi_identity": _probe_nonlocal_unsupported,
    "high_availability": _probe_ha_unsupported,
    "keyed_connectors": _probe_keyed_connectors_unsupported,
    "signed_reference_export": _probe_signed_reference_unsupported,
}
for _capability_id in SEC_DELEGATED_CAPABILITIES:
    PROBES[_capability_id] = _probe_sec_delegated


def _capability_result(capability: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    capability_id = str(capability.get("id") or "")
    declared_status = str(capability.get("status") or "")
    expected_status = EXPECTED_STATUS_BY_ID.get(capability_id)
    evidence = _evidence_check(capability, repo_root=repo_root)
    errors: list[str] = []
    if expected_status is None:
        errors.append(f"undeclared capability probe: {capability_id}")
    elif declared_status != expected_status:
        errors.append(f"status drift for {capability_id}: expected {expected_status}, got {declared_status}")
    if not evidence["passed"]:
        errors.append(f"evidence refs unresolved for {capability_id}: {evidence['missing_refs']}")
    probe_payload: dict[str, Any] = {}
    probe = PROBES.get(capability_id)
    if probe is None:
        errors.append(f"missing runtime probe for {capability_id}")
    else:
        try:
            probe_payload = probe()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"runtime probe failed for {capability_id}: {exc}")
    return {
        "id": capability_id,
        "declared_status": declared_status,
        "expected_status": expected_status,
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "evidence": evidence,
        "runtime_probe": probe_payload,
    }


def build_report(matrix_path: Path | str = MATRIX_PATH, *, repo_root: Path | str = REPO_ROOT) -> dict[str, Any]:
    with _temporary_env("DB_INIT_MODE", "none"):
        return _build_report_with_scoped_env(matrix_path, repo_root=repo_root)


def _build_report_with_scoped_env(matrix_path: Path | str = MATRIX_PATH, *, repo_root: Path | str = REPO_ROOT) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    matrix_file = Path(matrix_path).resolve()
    matrix = _load_json_compatible_yaml(matrix_file)
    capabilities = list(matrix.get("capabilities") or [])
    results = [_capability_result(capability, repo_root=repo) for capability in capabilities]
    declared_ids = {item["id"] for item in results}
    missing = sorted(set(EXPECTED_STATUS_BY_ID) - declared_ids)
    extra = sorted(declared_ids - set(EXPECTED_STATUS_BY_ID))
    errors = [error for item in results for error in item["errors"]]
    if missing:
        errors.append(f"missing capabilities: {missing}")
    if extra:
        errors.append(f"unexpected capabilities: {extra}")

    defaults = _settings_default_by_alias()
    pinned_false = []
    for flag in matrix.get("pinned_false_flags", []):
        value = defaults.get(str(flag))
        passed = value is False
        pinned_false.append({"flag": flag, "default": value, "status": "pass" if passed else "fail"})
        if not passed:
            errors.append(f"pinned false flag default drift: {flag}={value!r}")

    coverage_by_status: dict[str, list[str]] = {}
    for result in results:
        coverage_by_status.setdefault(str(result["declared_status"]), []).append(str(result["id"]))

    return {
        "schema_id": "project6.support_matrix_runtime_contract_audit.v1",
        "status": "pass" if not errors else "fail",
        "matrix_path": str(matrix_file),
        "profile": matrix.get("profile"),
        "overlays": matrix.get("overlays"),
        "capability_count": len(results),
        "coverage_by_status": {key: sorted(value) for key, value in sorted(coverage_by_status.items())},
        "capabilities": results,
        "pinned_false_flags": pinned_false,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit support_matrix runtime contracts without mutating repo state.")
    parser.add_argument("--matrix", default=str(MATRIX_PATH), help="support_matrix.yaml path")
    args = parser.parse_args(argv)
    with contextlib.redirect_stdout(sys.stderr):
        report = build_report(Path(args.matrix))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
