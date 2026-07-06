from __future__ import annotations

import ast
import hashlib
import json
import runpy
import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_sec_xbrl_sidecar
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


_HYGIENE_CLASS = layer3_sec_xbrl_sidecar.StorageRootHygieneClass
_STRUCTURAL_HYGIENE_CLASSES = [
    _HYGIENE_CLASS.REPO_RELATIVE,
    _HYGIENE_CLASS.GIT_TRACKED,
    _HYGIENE_CLASS.ONEDRIVE_CLOUD_SYNC,
    _HYGIENE_CLASS.STATIC_PUBLIC_SERVED,
    _HYGIENE_CLASS.GENERATED_ARTIFACT,
    _HYGIENE_CLASS.SHARED_AUTHORITY,
    _HYGIENE_CLASS.MISSING_UNREADABLE,
    _HYGIENE_CLASS.PERMISSION_BROAD,
]
_OVERRIDEABLE_HYGIENE_CLASSES = [
    _HYGIENE_CLASS.DOWNLOADS_LIKE,
    _HYGIENE_CLASS.TEMP_LIKE,
]
_NON_ACCEPTED_HYGIENE_CLASSES = _STRUCTURAL_HYGIENE_CLASSES + _OVERRIDEABLE_HYGIENE_CLASSES


def _storage_root_for_hygiene_class(
    tmp_path: Path,
    hygiene_class: layer3_sec_xbrl_sidecar.StorageRootHygieneClass,
) -> Path:
    if hygiene_class is _HYGIENE_CLASS.REPO_RELATIVE:
        return Path(__file__).resolve().parents[2]
    if hygiene_class is _HYGIENE_CLASS.GIT_TRACKED:
        try:
            subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
        except (OSError, subprocess.CalledProcessError):
            pytest.skip("git executable is required for external worktree hygiene coverage")
        external_repo = tmp_path / "external-repo"
        storage_root = external_repo / "storage"
        storage_root.mkdir(parents=True)
        subprocess.run(["git", "-C", str(external_repo), "init"], capture_output=True, text=True, check=True)
        return storage_root
    if hygiene_class is _HYGIENE_CLASS.ONEDRIVE_CLOUD_SYNC:
        storage_root = tmp_path / "Downloads" / "OneDrive_Tenant" / "storage"
        storage_root.mkdir(parents=True)
        return storage_root
    if hygiene_class is _HYGIENE_CLASS.STATIC_PUBLIC_SERVED:
        storage_root = tmp_path / "static" / "storage"
        storage_root.mkdir(parents=True)
        return storage_root
    if hygiene_class is _HYGIENE_CLASS.GENERATED_ARTIFACT:
        storage_root = tmp_path / "reports" / "storage"
        storage_root.mkdir(parents=True)
        return storage_root
    if hygiene_class is _HYGIENE_CLASS.SHARED_AUTHORITY:
        storage_root = tmp_path / "shared" / "storage"
        storage_root.mkdir(parents=True)
        return storage_root
    if hygiene_class is _HYGIENE_CLASS.MISSING_UNREADABLE:
        return tmp_path / "private-storage" / "missing"
    if hygiene_class is _HYGIENE_CLASS.PERMISSION_BROAD:
        return Path.home()
    if hygiene_class is _HYGIENE_CLASS.DOWNLOADS_LIKE:
        storage_root = tmp_path / "Downloads"
        storage_root.mkdir()
        return storage_root
    if hygiene_class is _HYGIENE_CLASS.TEMP_LIKE:
        storage_root = tmp_path / "private-storage"
        storage_root.mkdir()
        return storage_root
    raise AssertionError(f"Unhandled hygiene class {hygiene_class!r}")


def test_sec_xbrl_sidecar_emits_resolved_semantics_and_redacts_response(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )

    assert response["status"] == "ready"
    assert response["resolved_fact_count"] == 2
    assert response["parity"]["regex_fact_authority_count"] == 1
    assert response["parity"]["recovered_vs_regex"] == 1
    assert response["coverage"]["period_resolved_count"] == 2
    assert response["coverage"]["unit_resolved_count"] == 2
    assert response["coverage"]["explicit_dimension_fact_count"] == 1
    assert response["coverage"]["typed_dimension_fact_count"] == 1
    assert response["coverage"]["hidden_fact_count"] == 1
    assert response["coverage"]["continued_fact_count"] == 1
    assert response["coverage"]["concept_resolved_from_dts_count"] == 2
    assert "987654321000000" not in json.dumps(response, sort_keys=True)

    receipt = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
        response["sidecar_receipt_id"],
        expected_sidecar_receipt_hash=response["sidecar_receipt_hash"],
    )
    assert "value" not in receipt["resolved_fact_records"][0]
    assert receipt["internal_value_store"]["store_state"] == "not_created_internal_value_store_flag_off"
    assert receipt["diagnostics"]["raw_fact_values_retained_internal_value_store"] is False
    assert receipt["diagnostics"]["internal_value_store_retention_policy"] == (
        "not_created_without_internal_value_store_flag"
    )
    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(receipt)
    assert excinfo.value.error_code == "sec_edgar_arelle_sidecar_internal_value_store_not_persisted"
    assert receipt["resolved_fact_projection"][0]["value_redacted"] is True
    assert "value" not in receipt["resolved_fact_projection"][0]
    assert receipt["diagnostics"]["app_runtime_imported_arelle"] is False
    assert receipt["diagnostics"]["taxonomy_package_count"] == 1
    assert receipt["diagnostics"]["taxonomy_package_invalid_count"] == 1
    assert receipt["diagnostics"]["taxonomy_package_invalid_hashes"] == [_hash("invalid-taxonomy")]
    assert receipt["negative_invariants"]["material_bridge_mutated"] is False


def test_sec_xbrl_sidecar_internal_value_store_requires_explicit_gate(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_internal_value_store_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_xbrl_storage_root_hygiene_override_ack", True, raising=False)

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )

    receipt = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
        response["sidecar_receipt_id"],
        expected_sidecar_receipt_hash=response["sidecar_receipt_hash"],
    )
    assert receipt["internal_value_store"]["store_state"] == "persisted"
    assert receipt["internal_value_store"]["retention_policy"] == "sec_xbrl_public_financial_value_retention_v1"
    assert receipt["internal_value_store"]["storage_root_hygiene_override"] is True
    assert receipt["internal_value_store"]["storage_root_hygiene_reason_code"] == (
        "storage_root_hygiene_temp_like_override_ack"
    )
    assert len(receipt["internal_value_store"]["storage_namespace_hash"]) == 64
    value_store = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(receipt)
    assert value_store["value_records"][0]["effective_value"] == "987654321000000"
    assert value_store["value_records"][0]["lexical_value"] == "987654321"
    assert value_store["retention_policy"] == "sec_xbrl_public_financial_value_retention_v1"
    assert value_store["storage_root_hygiene_override"] is True
    assert value_store["storage_root_hygiene_reason_code"] == "storage_root_hygiene_temp_like_override_ack"
    assert value_store["storage_namespace_hash"] == receipt["internal_value_store"]["storage_namespace_hash"]
    assert receipt["diagnostics"]["raw_fact_values_retained_internal_value_store"] is True
    assert receipt["diagnostics"]["internal_value_store_retention_policy"] == (
        "sec_xbrl_public_financial_value_retention_v1"
    )
    projected = json.dumps({"receipt": receipt, "value_store": value_store}, sort_keys=True)
    assert str(tmp_path) not in projected


def test_sec_xbrl_sidecar_internal_value_store_rejects_temp_root_without_override_ack(
    monkeypatch,
    tmp_path,
):
    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_internal_value_store_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_xbrl_storage_root_hygiene_override_ack", False, raising=False)

    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
            _request(companyfacts_count=1)
        )

    assert excinfo.value.error_code == "sec_edgar_arelle_sidecar_storage_root_hygiene_temp_like"
    assert excinfo.value.blocked_fields == ["storage_root_hygiene"]


def test_sec_xbrl_sidecar_value_store_path_rejects_repo_root_even_with_override_ack(
    monkeypatch,
):
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setattr(settings, "storage_dir", str(repo_root))
    monkeypatch.setattr(settings, "layer3_sec_xbrl_storage_root_hygiene_override_ack", True, raising=False)

    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_sec_xbrl_sidecar._value_store_path("sec-edgar-arelle-resolved-fact-authority-" + "a" * 24)

    assert excinfo.value.error_code == "sec_edgar_arelle_sidecar_storage_root_hygiene_repo_relative"
    assert excinfo.value.blocked_fields == ["storage_root_hygiene"]


def test_sec_xbrl_sidecar_downloads_like_storage_root_requires_override_ack(tmp_path):
    downloads_root = tmp_path / "Downloads"
    downloads_root.mkdir()

    rejected = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        downloads_root,
        override_ack=False,
    )
    accepted = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        downloads_root,
        override_ack=True,
    )

    assert rejected.accepted is False
    assert rejected.reason_code == "storage_root_hygiene_downloads_like"
    assert accepted.accepted is True
    assert accepted.override is True
    assert accepted.reason_code == "storage_root_hygiene_downloads_like_override_ack"
    assert len(accepted.namespace_hash) == 64


@pytest.mark.parametrize("hygiene_class", _NON_ACCEPTED_HYGIENE_CLASSES)
def test_sec_xbrl_sidecar_storage_hygiene_rejects_every_non_accepted_class_without_override_ack(
    tmp_path,
    hygiene_class,
):
    storage_root = _storage_root_for_hygiene_class(tmp_path, hygiene_class)

    result = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        storage_root,
        override_ack=False,
    )

    assert result.accepted is False
    assert result.override is False
    assert result.hygiene_class is hygiene_class
    assert result.reason_code == f"storage_root_hygiene_{hygiene_class.value}"


@pytest.mark.parametrize("hygiene_class", _STRUCTURAL_HYGIENE_CLASSES)
def test_sec_xbrl_sidecar_storage_hygiene_structural_classes_ignore_override_ack(
    tmp_path,
    hygiene_class,
):
    storage_root = _storage_root_for_hygiene_class(tmp_path, hygiene_class)

    result = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        storage_root,
        override_ack=True,
    )

    assert result.accepted is False
    assert result.override is False
    assert result.hygiene_class is hygiene_class
    assert result.reason_code == f"storage_root_hygiene_{hygiene_class.value}"


@pytest.mark.parametrize("hygiene_class", _OVERRIDEABLE_HYGIENE_CLASSES)
def test_sec_xbrl_sidecar_storage_hygiene_only_name_classes_accept_override_without_raw_path(
    tmp_path,
    hygiene_class,
):
    storage_root = _storage_root_for_hygiene_class(tmp_path, hygiene_class)

    result = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        storage_root,
        override_ack=True,
    )
    metadata = result.metadata()

    assert result.accepted is True
    assert result.override is True
    assert result.hygiene_class is hygiene_class
    assert result.reason_code == f"storage_root_hygiene_{hygiene_class.value}_override_ack"
    assert metadata["storage_namespace_hash"] == result.namespace_hash
    assert len(result.namespace_hash) == 64
    assert str(storage_root) not in json.dumps(metadata, sort_keys=True)


@pytest.mark.parametrize("onedrive_part", ["OneDrive-Tenant", "OneDrive_Tenant"])
def test_sec_xbrl_sidecar_storage_hygiene_onedrive_variants_precede_downloads_override(
    tmp_path,
    onedrive_part,
):
    storage_root = tmp_path / "Downloads" / onedrive_part / "storage"
    storage_root.mkdir(parents=True)

    result = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        storage_root,
        override_ack=True,
    )

    assert result.accepted is False
    assert result.hygiene_class is _HYGIENE_CLASS.ONEDRIVE_CLOUD_SYNC
    assert result.reason_code == "storage_root_hygiene_onedrive_cloud_sync"


@pytest.mark.parametrize("downloads_part", ["Downloads", "DOWNLOADS"])
def test_sec_xbrl_sidecar_storage_hygiene_downloads_case_and_trailing_separator(
    tmp_path,
    downloads_part,
):
    storage_root = tmp_path / downloads_part
    storage_root.mkdir()
    storage_root_with_separator = Path(str(storage_root) + "/")

    rejected = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        storage_root_with_separator,
        override_ack=False,
    )
    accepted = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        storage_root_with_separator,
        override_ack=True,
    )

    assert rejected.accepted is False
    assert rejected.hygiene_class is _HYGIENE_CLASS.DOWNLOADS_LIKE
    assert rejected.reason_code == "storage_root_hygiene_downloads_like"
    assert accepted.accepted is True
    assert accepted.override is True
    assert accepted.hygiene_class is _HYGIENE_CLASS.DOWNLOADS_LIKE
    assert accepted.reason_code == "storage_root_hygiene_downloads_like_override_ack"


@pytest.mark.parametrize("onedrive_part", ["onedrive-contoso", "ONEDRIVE_CONTOSO"])
def test_sec_xbrl_sidecar_storage_hygiene_onedrive_case_variants_precede_downloads_override(
    tmp_path,
    onedrive_part,
):
    storage_root = tmp_path / "Downloads" / onedrive_part / "storage"
    storage_root.mkdir(parents=True)

    result = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        storage_root,
        override_ack=True,
    )

    assert result.accepted is False
    assert result.hygiene_class is _HYGIENE_CLASS.ONEDRIVE_CLOUD_SYNC
    assert result.reason_code == "storage_root_hygiene_onedrive_cloud_sync"


def test_sec_xbrl_sidecar_storage_hygiene_rejects_symlink_into_repo_root(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    storage_root = tmp_path / "linked-repo"
    try:
        storage_root.symlink_to(repo_root, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    result = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        storage_root,
        override_ack=True,
    )

    assert result.accepted is False
    assert result.hygiene_class is _HYGIENE_CLASS.REPO_RELATIVE
    assert result.reason_code == "storage_root_hygiene_repo_relative"


@pytest.mark.parametrize(
    "path_text",
    ["C:/Users", "C:/Program Files", "C:/Program Files (x86)", "C:/ProgramData"],
)
def test_sec_xbrl_sidecar_permission_broad_includes_windows_class_roots(path_text):
    assert layer3_sec_xbrl_sidecar._path_is_permission_broad(Path(path_text)) is True


def test_sec_xbrl_sidecar_rejects_external_git_worktree_storage_root(tmp_path):
    try:
        subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git executable is required for external worktree hygiene coverage")
    external_repo = tmp_path / "external-repo"
    storage_root = external_repo / "storage"
    storage_root.mkdir(parents=True)
    subprocess.run(["git", "-C", str(external_repo), "init"], capture_output=True, text=True, check=True)

    rejected = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        storage_root,
        override_ack=True,
    )

    assert rejected.accepted is False
    assert rejected.hygiene_class == layer3_sec_xbrl_sidecar.StorageRootHygieneClass.GIT_TRACKED
    assert rejected.reason_code == "storage_root_hygiene_git_tracked"


def test_sec_xbrl_sidecar_storage_hygiene_handles_missing_git(monkeypatch, tmp_path):
    storage_root = tmp_path / "storage"
    storage_root.mkdir()

    def missing_git(*_args, **_kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(layer3_sec_xbrl_sidecar.subprocess, "run", missing_git)

    accepted = layer3_sec_xbrl_sidecar._classify_value_store_storage_root(
        storage_root,
        override_ack=True,
    )

    assert accepted.accepted is True
    assert accepted.hygiene_class == layer3_sec_xbrl_sidecar.StorageRootHygieneClass.TEMP_LIKE
    assert accepted.reason_code == "storage_root_hygiene_temp_like_override_ack"


def test_sec_xbrl_sidecar_internal_value_store_source_has_no_deletion_path():
    """Canary for accidental direct deletion APIs, not adversarial evasion."""
    source = Path(layer3_sec_xbrl_sidecar.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_delete_call_names: set[str] = set()
    imported_delete_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"os", "shutil"}:
                    imported_delete_modules.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module in {"os", "shutil"}:
            for alias in node.names:
                if alias.name in {"remove", "rmtree"}:
                    imported_delete_call_names.add(alias.asname or alias.name)

    assert "unlink(" not in source
    assert "rmtree(" not in source
    assert ".remove(" not in source
    assert "os.remove(" not in source
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            assert func.attr not in {"unlink", "rmdir", "remove", "rmtree"}
            if isinstance(func.value, ast.Name) and func.value.id in imported_delete_modules:
                assert func.attr not in {"remove", "rmtree"}
        elif isinstance(func, ast.Name):
            assert func.id not in imported_delete_call_names


def test_sec_xbrl_sidecar_internal_value_store_missing_fails_closed(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_internal_value_store_enabled", True)
    monkeypatch.setattr(settings, "layer3_sec_xbrl_storage_root_hygiene_override_ack", True, raising=False)
    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )
    receipt = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
        response["sidecar_receipt_id"],
        expected_sidecar_receipt_hash=response["sidecar_receipt_hash"],
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_value_store_path", lambda _receipt_id: tmp_path / "missing.json")

    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_internal_value_store(receipt)

    assert excinfo.value.error_code == "sec_edgar_arelle_sidecar_internal_value_store_missing"


def test_sec_xbrl_sidecar_fails_closed_when_arelle_is_absent(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _blocked_arelle_runner)

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=None)
    )

    assert response["status"] == "blocked"
    assert response["sidecar_receipt_id"] is None
    assert response["status_projection"]["ready"] is False
    assert response["status_projection"]["blocked_reasons"][0]["reason"] == "arelle_nonzero_exit"
    assert (
        response["status_projection"]["blocked_reasons"][0]["arelle_error_reason"]
        == "taxonomy_package_valid_package_missing"
    )
    assert response["negative_invariants"]["arelle_imported_into_app_runtime"] is False


def test_sec_xbrl_sidecar_rejects_silent_low_fact_cap(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)

    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
            {**_request(companyfacts_count=1), "max_facts": 10}
        )

    assert excinfo.value.error_code == "sec_edgar_arelle_sidecar_max_facts_too_low"


def test_sec_xbrl_sidecar_fails_closed_on_independent_fact_undercount(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar,
        "_independent_inline_fact_tally",
        lambda _documents: {
            "inline_fact_count": 3,
            "scanned_document_count": 1,
            "inline_document_count": 1,
            "document_tally": [{"document_index": 1, "inline_fact_count": 3}],
        },
    )

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )

    assert response["status"] == "blocked"
    assert response["status_projection"]["blocked_reasons"][0]["reason"] == "arelle_independent_inline_fact_count_mismatch"
    assert response["status_projection"]["blocked_reasons"][0]["independent_inline_fact_count"] == 3
    assert response["status_projection"]["blocked_reasons"][0]["arelle_fact_count"] == 2


def test_sec_xbrl_sidecar_fails_closed_on_unresolved_arelle_semantic_references(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _semantic_unresolved_arelle_runner)

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )

    assert response["status"] == "blocked"
    reasons = {item["reason"] for item in response["status_projection"]["blocked_reasons"]}
    assert reasons == {"arelle_context_period_unresolved", "arelle_unit_ref_unresolved"}


def test_sec_xbrl_sidecar_blocks_model_errors_from_arelle_payload(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _model_error_arelle_runner)

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )

    assert response["status"] == "blocked"
    assert response["status_projection"]["blocked_reasons"][0]["reason"] == "arelle_model_errors_present"


def test_sec_xbrl_sidecar_blocks_unresolved_concepts_but_allows_resolved_extensions(monkeypatch, tmp_path):
    _install_receipt_fakes(monkeypatch, tmp_path, _concept_unresolved_arelle_runner)

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )

    assert response["status"] == "blocked"
    assert response["status_projection"]["blocked_reasons"][0]["reason"] == "arelle_concept_dts_unresolved"

    _install_receipt_fakes(monkeypatch, tmp_path, _ready_arelle_runner)
    ready = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        {**_request(companyfacts_count=1), "client_request_id": "sidecar-extension-ready"}
    )
    assert ready["status"] == "ready"
    assert ready["diagnostics"]["resolved_structural_semantics"]["extension_concept_count"] == 1


@pytest.mark.parametrize("taxonomy_year", ["2024"])
def test_sec_xbrl_sidecar_blocks_unprovisioned_taxonomy_year_before_arelle(monkeypatch, tmp_path, taxonomy_year):
    def unexpected_runner(*_args, **_kwargs):
        raise AssertionError("unprovisioned taxonomy year must block before Arelle")

    inline_document = (
        '<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">'
        f'<link:schemaRef xlink:href="https://xbrl.fasb.org/us-gaap/{taxonomy_year}/elts/us-gaap-{taxonomy_year}.xsd" />'
        '<ix:nonFraction name="us-gaap:Assets" contextRef="c" unitRef="u">1</ix:nonFraction>'
        "</html>"
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", unexpected_runner)
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar,
        "_taxonomy_package_files",
        lambda: [tmp_path / "us-gaap-2025.zip", tmp_path / "srt-2025.zip", tmp_path / "sec-2025.zip"],
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: tmp_path / "cache")

    result = layer3_sec_xbrl_sidecar._run_arelle(
        primary_document=inline_document,
        max_facts=layer3_sec_xbrl_sidecar.MIN_MAX_FACTS,
        submission_documents=[{"filename": "primary.htm", "type": "10-K", "text": inline_document, "primary": "true"}],
    )

    assert result["status"] == "blocked"
    assert result["reasons"][0]["reason"] == "taxonomy_year_unprovisioned"
    assert result["reasons"][0]["detected_taxonomy_years"] == [taxonomy_year]
    assert result["reasons"][0]["provisioned_taxonomy_years"] == ["2025"]


def test_sec_xbrl_sidecar_blocks_unprovisioned_sec_family_vintage_before_arelle(monkeypatch, tmp_path):
    def unexpected_runner(*_args, **_kwargs):
        raise AssertionError("unprovisioned SEC family vintage must block before Arelle")

    inline_document = (
        '<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">'
        '<link:schemaRef xlink:href="https://xbrl.sec.gov/cyd/2025/cyd-2025.xsd" />'
        '<ix:nonFraction name="us-gaap:Assets" contextRef="c" unitRef="u">1</ix:nonFraction>'
        "</html>"
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", unexpected_runner)
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar,
        "_taxonomy_package_files",
        lambda: [
            tmp_path / "us-gaap-2025.zip",
            tmp_path / "srt-2025.zip",
            tmp_path / "sec-2025.zip",
            tmp_path / "cyd-2024.zip",
        ],
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: tmp_path / "cache")

    result = layer3_sec_xbrl_sidecar._run_arelle(
        primary_document=inline_document,
        max_facts=layer3_sec_xbrl_sidecar.MIN_MAX_FACTS,
        submission_documents=[{"filename": "primary.htm", "type": "10-K", "text": inline_document, "primary": "true"}],
    )

    assert result["status"] == "blocked"
    assert result["reasons"][0]["reason"] == "taxonomy_family_vintage_unprovisioned"
    assert result["reasons"][0]["detected_taxonomy_family_vintages"] == ["cyd/2025"]
    assert result["reasons"][0]["provisioned_taxonomy_family_vintages"] == ["cyd/2024"]
    assert result["reasons"][0]["unprovisioned_taxonomy_family_vintages"] == ["cyd/2025"]


def test_sec_xbrl_sidecar_allows_provisioned_cyd_family_vintage_before_arelle(monkeypatch, tmp_path):
    captured: dict[str, list[str]] = {}

    def ready_runner(command, *_args, **_kwargs):
        captured["command"] = list(command)
        return _ready_arelle_runner()

    inline_document = (
        '<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">'
        '<link:schemaRef xlink:href="https://xbrl.sec.gov/cyd/2024/cyd-2024.xsd" />'
        '<ix:nonFraction name="us-gaap:Assets" contextRef="c" unitRef="u">1</ix:nonFraction>'
        "</html>"
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", ready_runner)
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar,
        "_taxonomy_package_files",
        lambda: [
            tmp_path / "us-gaap-2024.zip",
            tmp_path / "srt-2024.zip",
            tmp_path / "sec-2024.zip",
            tmp_path / "cyd-2024.zip",
        ],
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_internet_connectivity", lambda: "offline")

    result = layer3_sec_xbrl_sidecar._run_arelle(
        primary_document=inline_document,
        max_facts=layer3_sec_xbrl_sidecar.MIN_MAX_FACTS,
        submission_documents=[{"filename": "primary.htm", "type": "10-K", "text": inline_document, "primary": "true"}],
    )

    taxonomy_args = [
        Path(captured["command"][index + 1]).name
        for index, value in enumerate(captured["command"])
        if value == "--taxonomy-package"
    ]
    assert result["status"] == "ready"
    assert taxonomy_args == ["us-gaap-2024.zip", "srt-2024.zip", "sec-2024.zip", "cyd-2024.zip"]


def test_sec_xbrl_sidecar_allows_provisioned_cyd_2025_from_provisioner_package_set(monkeypatch, tmp_path):
    captured: dict[str, list[str]] = {}
    provisioner = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools" / "sec-xbrl-arelle-provision.py"))
    package_names = [spec["name"] for spec in provisioner["taxonomy_specs"](years=["2025"])]

    def ready_runner(command, *_args, **_kwargs):
        captured["command"] = list(command)
        return _ready_arelle_runner()

    inline_document = (
        '<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">'
        '<link:schemaRef xlink:href="https://xbrl.sec.gov/cyd/2025/cyd-2025.xsd" />'
        '<ix:nonFraction name="us-gaap:Assets" contextRef="c" unitRef="u">1</ix:nonFraction>'
        "</html>"
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", ready_runner)
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar,
        "_taxonomy_package_files",
        lambda: [tmp_path / name for name in package_names],
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_internet_connectivity", lambda: "offline")

    result = layer3_sec_xbrl_sidecar._run_arelle(
        primary_document=inline_document,
        max_facts=layer3_sec_xbrl_sidecar.MIN_MAX_FACTS,
        submission_documents=[{"filename": "primary.htm", "type": "10-K", "text": inline_document, "primary": "true"}],
    )

    taxonomy_args = [
        Path(captured["command"][index + 1]).name
        for index, value in enumerate(captured["command"])
        if value == "--taxonomy-package"
    ]
    assert result["status"] == "ready"
    assert taxonomy_args == ["us-gaap-2025.zip", "srt-2025.zip", "IFRSAT-2025.zip", "sec-2025.zip", "cyd-2025.zip"]


def test_sec_xbrl_sidecar_allows_provisioned_ifrs_2025_from_provisioner_package_set(monkeypatch, tmp_path):
    captured: dict[str, list[str]] = {}
    provisioner = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools" / "sec-xbrl-arelle-provision.py"))
    package_names = [spec["name"] for spec in provisioner["taxonomy_specs"](years=["2025"])]

    def ready_runner(command, *_args, **_kwargs):
        captured["command"] = list(command)
        return _ready_arelle_runner()

    inline_document = (
        '<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">'
        '<link:schemaRef xlink:href="https://xbrl.ifrs.org/taxonomy/2025-03-27/full_ifrs/full_ifrs-cor_2025-03-27.xsd" />'
        '<ix:nonFraction name="ifrs-full:Assets" contextRef="c" unitRef="u">1</ix:nonFraction>'
        "</html>"
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", ready_runner)
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar,
        "_taxonomy_package_files",
        lambda: [tmp_path / name for name in package_names],
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_internet_connectivity", lambda: "offline")

    result = layer3_sec_xbrl_sidecar._run_arelle(
        primary_document=inline_document,
        max_facts=layer3_sec_xbrl_sidecar.MIN_MAX_FACTS,
        submission_documents=[{"filename": "primary.htm", "type": "20-F", "text": inline_document, "primary": "true"}],
    )

    taxonomy_args = [
        Path(captured["command"][index + 1]).name
        for index, value in enumerate(captured["command"])
        if value == "--taxonomy-package"
    ]
    assert "2025" in layer3_sec_xbrl_sidecar._taxonomy_package_years([tmp_path / "IFRSAT-2025.zip"])
    assert result["status"] == "ready"
    assert taxonomy_args == ["us-gaap-2025.zip", "srt-2025.zip", "IFRSAT-2025.zip", "sec-2025.zip", "cyd-2025.zip"]


def test_sec_xbrl_sidecar_allows_provisioned_2026_taxonomy_year_before_arelle(monkeypatch, tmp_path):
    captured: dict[str, list[str]] = {}

    def ready_runner(command, *_args, **_kwargs):
        captured["command"] = list(command)
        return _ready_arelle_runner()

    inline_document = (
        '<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">'
        '<link:schemaRef xlink:href="https://xbrl.fasb.org/us-gaap/2026/elts/us-gaap-2026.xsd" />'
        '<ix:nonFraction name="us-gaap:Assets" contextRef="c" unitRef="u">1</ix:nonFraction>'
        "</html>"
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", ready_runner)
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar,
        "_taxonomy_package_files",
        lambda: [tmp_path / "us-gaap-2026.zip", tmp_path / "srt-2026.zip", tmp_path / "sec-2026.zip"],
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_internet_connectivity", lambda: "offline")

    result = layer3_sec_xbrl_sidecar._run_arelle(
        primary_document=inline_document,
        max_facts=layer3_sec_xbrl_sidecar.MIN_MAX_FACTS,
        submission_documents=[{"filename": "primary.htm", "type": "10-K", "text": inline_document, "primary": "true"}],
    )

    taxonomy_args = [
        Path(captured["command"][index + 1]).name
        for index, value in enumerate(captured["command"])
        if value == "--taxonomy-package"
    ]
    assert result["status"] == "ready"
    assert taxonomy_args == ["us-gaap-2026.zip", "srt-2026.zip", "sec-2026.zip"]


def test_sec_xbrl_sidecar_blocks_no_inline_submission_before_arelle(monkeypatch, tmp_path):
    def unexpected_runner(*_args, **_kwargs):
        raise AssertionError("no-inline submissions must block before Arelle")

    _install_receipt_fakes(monkeypatch, tmp_path, unexpected_runner, content=b"""
<SEC-DOCUMENT>
<DOCUMENT>
<TYPE>10-K
<FILENAME>primary.htm
<TEXT><html><body>ordinary pre-inline filing</body></html></TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
""")

    response = layer3_sec_xbrl_sidecar.derive_sec_edgar_arelle_resolved_fact_authority_sidecar(
        _request(companyfacts_count=1)
    )

    assert response["status"] == "blocked"
    assert response["status_projection"]["blocked_reasons"][0]["reason"] == "no_inline_facts_pre_inline_era"


def test_sec_xbrl_sidecar_stages_submission_documents_for_dts_loading():
    primary = "<html><head></head><body>inline</body></html>"
    wrapped_schema = "\r\n<XBRL>\r\n<?xml version=\"1.0\" encoding=\"utf-8\"?>\r\n<schema />\r\n</XBRL>\r\n"
    inline = '<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><body><ix:nonFraction name="a" contextRef="c">1</ix:nonFraction></body></html>'
    inline_exhibit = '<html xmlns:ixt="http://www.xbrl.org/2013/inlineXBRL"><body><ixt:nonNumeric name="b" contextRef="c">x</ixt:nonNumeric></body></html>'
    content = f"""
<SEC-DOCUMENT>
<DOCUMENT>
<TYPE>10-K
<FILENAME>primary.htm
<TEXT>{primary}</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-101.SCH
<FILENAME>issuer.xsd
<TEXT>{wrapped_schema}</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-101.INS
<FILENAME>instance.htm
<TEXT>{inline}</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-99.2
<FILENAME>exhibit.htm
<TEXT>{inline_exhibit}</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
""".encode("utf-8")

    documents = layer3_sec_xbrl_sidecar._submission_documents(
        content,
        primary_document_hash=_hash(primary),
    )

    assert documents[0]["primary"] == "true"
    assert documents[1]["filename"] == "issuer.xsd"
    assert documents[1]["text"].startswith("<?xml")
    assert "<XBRL>" not in documents[1]["text"]
    tally = layer3_sec_xbrl_sidecar._independent_inline_fact_tally(documents)
    assert tally["inline_fact_count"] == 2
    assert tally["inline_document_count"] == 2
    assert tally["document_tally"][0]["document_type"] == "EX-101.INS"
    assert tally["document_tally"][1]["document_type"] == "EX-99.2"


def test_sec_xbrl_sidecar_submission_documents_use_parser_decode_parity():
    primary = "<html><body>caf\xe9</body></html>"
    content = f"""
<SEC-DOCUMENT>
<DOCUMENT>
<TYPE>10-K
<FILENAME>primary.htm
<TEXT>{primary}</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
""".encode("cp1252")

    documents = layer3_sec_xbrl_sidecar._submission_documents(
        content,
        primary_document_hash=_hash(primary),
    )

    assert documents[0]["text"] == primary


def test_sec_xbrl_sidecar_submission_documents_fail_closed_on_unsupported_encoding():
    content = b"""
<SEC-DOCUMENT>
<DOCUMENT>
<TYPE>10-K
<FILENAME>primary.htm
<TEXT><html>\x81</html></TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
"""

    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_sec_xbrl_sidecar._submission_documents(
            content,
            primary_document_hash=_hash("<html></html>"),
        )

    assert excinfo.value.error_code == "sec_edgar_arelle_sidecar_submission_decode_failed"


def test_sec_xbrl_arelle_tool_prefers_context_dates_and_corrects_adjusted_end_datetimes():
    tool = runpy.run_path(str(Path(__file__).resolve().parents[2] / "tools" / "sec-xbrl-arelle.py"), run_name="sec_xbrl_arelle_test")
    period_payload = tool["_period_payload"]

    instant_context = SimpleNamespace(
        isForeverPeriod=False,
        isInstantPeriod=True,
        isStartEndPeriod=False,
        instantDate="2025-12-31",
        instantDatetime=datetime(2026, 1, 1),
    )
    duration_context = SimpleNamespace(
        isForeverPeriod=False,
        isInstantPeriod=False,
        isStartEndPeriod=True,
        startDate=None,
        startDatetime=datetime(2025, 1, 1),
        endDate=None,
        endDatetime=datetime(2026, 1, 1),
    )

    assert period_payload(instant_context)["instant"] == "2025-12-31"
    assert period_payload(duration_context) == {
        "type": "duration",
        "start": "2025-01-01",
        "end": "2025-12-31",
        "instant": None,
        "forever": False,
        "resolved": True,
    }


def test_sec_xbrl_sidecar_arelle_connectivity_guard_covers_reveal_and_egress_flags():
    guarded = {flag for flag, _settings_attr in layer3_sec_xbrl_sidecar._ARELLE_CONNECTIVITY_FORCE_OFFLINE_FLAGS}

    assert guarded == {
        "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
        "LAYER3_SEC_EDGAR_OFFICIAL_TICKER_RESOLUTION_ENABLED",
        "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_NONLOCAL_AUTHORIZED",
        "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
        "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
        "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
        "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    }


def test_sec_xbrl_sidecar_honors_online_connectivity_only_when_guard_flags_clear(monkeypatch):
    _clear_arelle_connectivity_guard_flags(monkeypatch)
    monkeypatch.setenv("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY", "online")

    assert layer3_sec_xbrl_sidecar._taxonomy_internet_connectivity() == "online"


@pytest.mark.parametrize(
    ("flag_name", "settings_attr"),
    layer3_sec_xbrl_sidecar._ARELLE_CONNECTIVITY_FORCE_OFFLINE_FLAGS,
)
def test_sec_xbrl_sidecar_forces_arelle_offline_when_reveal_or_egress_flag_armed(
    monkeypatch,
    flag_name: str,
    settings_attr: str,
):
    _clear_arelle_connectivity_guard_flags(monkeypatch)
    monkeypatch.setenv("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY", "online")
    monkeypatch.setattr(settings, settings_attr, True)

    assert layer3_sec_xbrl_sidecar._armed_arelle_connectivity_force_offline_flags() == [flag_name]
    assert layer3_sec_xbrl_sidecar._taxonomy_internet_connectivity() == "offline"


def test_sec_xbrl_sidecar_arelle_command_forces_offline_when_live_egress_flag_armed(monkeypatch, tmp_path):
    captured: dict[str, list[str]] = {}

    def runner(command, *_args, **_kwargs):
        captured["command"] = command
        return _ready_arelle_runner()

    _clear_arelle_connectivity_guard_flags(monkeypatch)
    monkeypatch.setenv("SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY", "online")
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", True)
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", runner)
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_package_files", lambda: [tmp_path / "taxonomy.zip"])
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: tmp_path / "cache")

    result = layer3_sec_xbrl_sidecar._run_arelle(
        primary_document="<html></html>",
        max_facts=layer3_sec_xbrl_sidecar.MIN_MAX_FACTS,
        submission_documents=[],
    )

    command = captured["command"]
    connectivity_arg = command[command.index("--internet-connectivity") + 1]
    assert result["status"] == "ready"
    assert connectivity_arg == "offline"


def _clear_arelle_connectivity_guard_flags(monkeypatch) -> None:
    for _flag_name, settings_attr in layer3_sec_xbrl_sidecar._ARELLE_CONNECTIVITY_FORCE_OFFLINE_FLAGS:
        monkeypatch.setattr(settings, settings_attr, False)


def _install_receipt_fakes(monkeypatch, tmp_path, runner, *, content: bytes | None = None):
    if content is None:
        content = b"""
<SEC-DOCUMENT>
<DOCUMENT>
<TYPE>10-K
<FILENAME>primary.htm
<TEXT><html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><body><ix:nonFraction name="us-gaap:Assets" contextRef="c" unitRef="u">1</ix:nonFraction></body></html></TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
"""
    parsed = {
        "primary_document_hash": _hash("primary-doc"),
        "document_inventory": [{"document_index": 1}],
        "content_order": [{"segment_index": 1}],
        "table_candidate_inventory": [],
        "inline_xbrl_marker_inventory": [{"marker_index": 1}],
    }
    parser = {
        "parser_receipt_id": "sec-edgar-html-inline-xbrl-parser-" + "a" * 24,
        "parser_receipt_hash": _hash("parser"),
        "connector_receipt_id": "sec-edgar-real-filing-acquisition-connector-" + "b" * 24 + "-" + "c" * 24,
        "connector_receipt_hash": _hash("connector"),
        "connector_example_id": "example",
        "live_source_artifact_receipt_id": "sec-edgar-text-table-live-source-artifact-" + "d" * 24 + "-" + "e" * 24,
        "live_source_artifact_receipt_hash": _hash("live"),
        "source_artifact_receipt_hash": _hash("source-artifact"),
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "primary_document_hash": parsed["primary_document_hash"],
        "document_inventory_hash": stable_hash(parsed["document_inventory"]),
        "content_order_hash": stable_hash(parsed["content_order"]),
        "table_candidate_inventory_hash": stable_hash(parsed["table_candidate_inventory"]),
        "inline_xbrl_marker_inventory_hash": stable_hash(parsed["inline_xbrl_marker_inventory"]),
    }
    live_receipt = {
        "source_artifact_receipt": {
            "source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
            "content_sha256": parser["content_sha256"],
        }
    }
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "layer3_sec_edgar_arelle_fact_authority_cutover_enabled", True)
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar.layer3_sec_edgar_html_inline_xbrl_parser,
        "read_sec_edgar_html_inline_xbrl_source_family_parser_receipt",
        lambda *_args, **_kwargs: dict(parser),
    )
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar.layer3_sec_edgar_real_filing_acquisition_connector,
        "read_sec_edgar_real_filing_acquisition_connector_receipt",
        lambda *_args, **_kwargs: {"connector_receipt_hash": parser["connector_receipt_hash"]},
    )
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar.layer3_sec_edgar_live_source_artifact,
        "read_sec_edgar_text_table_live_source_artifact_bytes",
        lambda *_args, **_kwargs: (dict(live_receipt), content),
    )
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar.layer3_sec_edgar_html_inline_xbrl_parser,
        "reparse_sec_edgar_html_inline_xbrl_source_family_for_material_bridge",
        lambda *_args, **_kwargs: {"primary_document_text": "<html>primary</html>", "parsed": parsed},
    )
    monkeypatch.setattr(
        layer3_sec_xbrl_sidecar.layer3_sec_edgar_html_inline_xbrl_fact_authority,
        "read_sec_edgar_html_inline_xbrl_fact_authority_receipt",
        lambda *_args, **_kwargs: {"fact_authority_receipt_hash": _hash("regex"), "fact_count": 1},
    )
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "ARELLE_SUBPROCESS_RUNNER", runner)
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_package_files", lambda: [tmp_path / "taxonomy.zip"])
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(layer3_sec_xbrl_sidecar, "_taxonomy_internet_connectivity", lambda: "offline")


def _request(*, companyfacts_count):
    payload = {
        "client_request_id": "sidecar-test",
        "sidecar_mode": layer3_sec_xbrl_sidecar.SIDECAR_MODE,
        "operator_decision": layer3_sec_xbrl_sidecar.OPERATOR_DECISION,
        "parser_receipt_id": "sec-edgar-html-inline-xbrl-parser-" + "a" * 24,
        "parser_receipt_hash": _hash("parser"),
        "regex_fact_authority_receipt_id": "sec-edgar-html-inline-xbrl-fact-authority-" + "f" * 24,
        "regex_fact_authority_receipt_hash": _hash("regex"),
        "operator_confirmation": True,
    }
    if companyfacts_count is not None:
        payload["companyfacts_standard_fact_count"] = companyfacts_count
        payload["companyfacts_oracle_confidence"] = "primary_companyfacts_standard_taxonomy_accession_scope"
    return payload


def _ready_arelle_runner(*_args, **_kwargs):
    payload = {
        "schema_id": "tools.sec_xbrl_arelle_extract.v1",
        "arelle_version": layer3_sec_xbrl_sidecar.ARELLE_VERSION,
        "taxonomy_package_loaded": True,
        "taxonomy_package_count": 1,
        "taxonomy_package_hashes": [_hash("taxonomy")],
        "taxonomy_package_invalid_count": 1,
        "taxonomy_package_invalid_hashes": [_hash("invalid-taxonomy")],
        "fact_count": 2,
        "diagnostics": {
            "model_error_count": 0,
            "concept_resolved_from_dts_count": 2,
            "concept_dts_unresolved_count": 0,
            "period_unresolved_with_context_ref_count": 0,
            "unit_unresolved_with_unit_ref_count": 0,
        },
        "document_set": {"loaded_document_count": 5, "entry_document_loaded": True},
        "facts": [
            {
                "source_order": 1,
                "concept": {"qname": "us-gaap:Revenue", "namespace": "http://fasb.org/us-gaap/2024", "local_name": "Revenue", "standard": True, "extension": False, "resolved_from_dts": True},
                "context_id": "ctx-1",
                "unit_id": "usd",
                "period": {"type": "duration", "start": "2025-01-01", "end": "2025-12-31", "instant": None, "forever": False, "resolved": True},
                "unit": {"resolved": True, "measures": ["iso4217:USD"], "currency": "iso4217:USD", "numerator": ["iso4217:USD"], "denominator": []},
                "dimensions": {"explicit": [{"axis": {"qname": "us-gaap:SegmentAxis"}, "member": {"qname": "us-gaap:SoftwareMember"}}], "typed": [], "resolved": True},
                "decimals": "-6",
                "precision": None,
                "scale": "0",
                "sign": None,
                "format": None,
                "hidden": True,
                "continued": True,
                "continued_at": "cont-1",
                "footnote_count": 0,
                "value": "987654321000000",
                "effective_value": "987654321000000",
                "lexical_value": "987654321",
            },
            {
                "source_order": 2,
                "concept": {"qname": "issuer:CustomMetric", "namespace": "http://example.invalid/issuer", "local_name": "CustomMetric", "standard": False, "extension": True, "resolved_from_dts": True},
                "context_id": "ctx-2",
                "unit_id": "shares",
                "period": {"type": "instant", "start": None, "end": None, "instant": "2025-12-31", "forever": False, "resolved": True},
                "unit": {"resolved": True, "measures": ["xbrli:shares"], "currency": None, "numerator": ["xbrli:shares"], "denominator": []},
                "dimensions": {"explicit": [], "typed": [{"axis": {"qname": "issuer:TypedAxis"}, "member_qname": {"qname": "issuer:TypedMember"}, "value": "typed-code"}], "resolved": True},
                "hidden": False,
                "continued": False,
                "footnote_count": 0,
                "sign": "-",
                "scale": None,
                "decimals": "0",
                "format": None,
                "value": "-123456789",
                "effective_value": "-123456789",
                "lexical_value": "123456789",
            },
        ],
    }
    return subprocess.CompletedProcess(args=["fake"], returncode=0, stdout=json.dumps(payload) + "\n", stderr="")


def _semantic_unresolved_arelle_runner(*_args, **_kwargs):
    completed = _ready_arelle_runner()
    payload = json.loads(completed.stdout.strip())
    payload["diagnostics"]["period_unresolved_with_context_ref_count"] = 1
    payload["diagnostics"]["unit_unresolved_with_unit_ref_count"] = 1
    return subprocess.CompletedProcess(args=["fake"], returncode=0, stdout=json.dumps(payload) + "\n", stderr="")


def _model_error_arelle_runner(*_args, **_kwargs):
    completed = _ready_arelle_runner()
    payload = json.loads(completed.stdout.strip())
    payload["diagnostics"]["model_error_count"] = 1
    return subprocess.CompletedProcess(args=["fake"], returncode=0, stdout=json.dumps(payload) + "\n", stderr="")


def _concept_unresolved_arelle_runner(*_args, **_kwargs):
    completed = _ready_arelle_runner()
    payload = json.loads(completed.stdout.strip())
    payload["diagnostics"]["concept_resolved_from_dts_count"] = 1
    payload["diagnostics"]["concept_dts_unresolved_count"] = 1
    payload["facts"][1]["concept"]["resolved_from_dts"] = False
    return subprocess.CompletedProcess(args=["fake"], returncode=0, stdout=json.dumps(payload) + "\n", stderr="")


def _blocked_arelle_runner(*_args, **_kwargs):
    return subprocess.CompletedProcess(
        args=["fake"],
        returncode=2,
        stdout='{"reason":"taxonomy_package_valid_package_missing","error_class":"RuntimeError"}\n',
        stderr="missing",
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
