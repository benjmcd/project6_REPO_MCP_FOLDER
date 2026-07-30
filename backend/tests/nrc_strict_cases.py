"""Strict-parser cases explicitly loaded by the parent and guarded-child launchers."""

from __future__ import annotations

from collections.abc import Iterator
import hashlib
import importlib
import inspect
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any, Callable, NoReturn

import pytest


_GUARDED_CHILD_ENV = "PROJECT6_NRC_STRICT_GUARDED_CHILD"
_GUARDED_CHILD = os.environ.get(_GUARDED_CHILD_ENV) == "1"
_NETWORK_ATTEMPTS: list[str] = []
_GUARDED_REQUESTS: Any = None
_ORIGINAL_SOCKET_TYPE = socket.socket
_GUARDS_INSTALLED_BEFORE_SERVICE_IMPORTS = False
_STRICT_SERVICE_MODULES = (
    "app.services.nrc_aps_strict_parse",
    "app.services.nrc_aps_document_processing",
)


class _TestNetworkDenied(RuntimeError):
    pass


class _TestSubprocessDenied(RuntimeError):
    pass


def _record_network_attempt(label: str) -> NoReturn:
    _NETWORK_ATTEMPTS.append(label)
    raise _TestNetworkDenied(f"strict_test_network_refused:{label}")


class _DeniedSocket(_ORIGINAL_SOCKET_TYPE):
    def connect(self, *_args: Any, **_kwargs: Any) -> None:
        _record_network_attempt("socket.connect")

    def connect_ex(self, *_args: Any, **_kwargs: Any) -> int:
        _record_network_attempt("socket.connect_ex")

    def bind(self, *_args: Any, **_kwargs: Any) -> None:
        _record_network_attempt("socket.bind")

    def sendto(self, *_args: Any, **_kwargs: Any) -> int:
        _record_network_attempt("socket.sendto")


def _deny_network(label: str) -> Callable[..., Any]:
    def denied(*_args: Any, **_kwargs: Any) -> Any:
        _record_network_attempt(label)

    return denied


def _install_test_network_denial() -> None:
    global _GUARDED_REQUESTS
    # Requests/urllib3 performs a caught local IPv6 bind capability probe at
    # import time. Load the test dependency first, then deny every transport
    # surface before either strict production module is imported.
    _GUARDED_REQUESTS = importlib.import_module("requests")
    setattr(socket, "socket", _DeniedSocket)
    setattr(
        socket,
        "create_connection",
        _deny_network("socket.create_connection"),
    )
    for name in (
        "getaddrinfo",
        "gethostbyname",
        "gethostbyname_ex",
        "gethostbyaddr",
        "getnameinfo",
        "getfqdn",
    ):
        if callable(getattr(socket, name, None)):
            setattr(socket, name, _deny_network(f"socket.{name}"))

    setattr(
        _GUARDED_REQUESTS.sessions.Session,
        "request",
        _deny_network("requests.Session.request"),
    )
    setattr(
        _GUARDED_REQUESTS.api,
        "request",
        _deny_network("requests.api.request"),
    )


def _deny_subprocess(label: str) -> Callable[..., Any]:
    def denied(*_args: Any, **_kwargs: Any) -> Any:
        raise _TestSubprocessDenied(f"strict_test_subprocess_refused:{label}")

    return denied


def _install_test_subprocess_denial() -> None:
    setattr(subprocess, "Popen", _deny_subprocess("subprocess.Popen"))
    for name in sorted(dir(os)):
        if (
            name == "system"
            or name == "startfile"
            or name.startswith("spawn")
            or name.startswith("exec")
            or name.startswith("posix_spawn")
        ) and callable(getattr(os, name, None)):
            setattr(os, name, _deny_subprocess(f"os.{name}"))


if _GUARDED_CHILD:
    assert not any(name in sys.modules for name in _STRICT_SERVICE_MODULES)
    _install_test_network_denial()
    _install_test_subprocess_denial()
    _GUARDS_INSTALLED_BEFORE_SERVICE_IMPORTS = True
    from app.services import nrc_aps_strict_parse as strict

    strict.install_subprocess_denial_guard()
    from app.services import nrc_aps_document_processing as processing
else:
    from app.services import nrc_aps_document_processing as processing
    from app.services import nrc_aps_strict_parse as strict


@pytest.fixture(autouse=True)
def _assert_guarded_child_made_no_network_attempts() -> Iterator[None]:
    if not _GUARDED_CHILD:
        yield
        return

    attempts_before_test = tuple(_NETWORK_ATTEMPTS)
    _NETWORK_ATTEMPTS.clear()
    assert not attempts_before_test, (
        f"guarded child attempted network before test: {attempts_before_test!r}"
    )

    yield

    attempts_during_test = tuple(_NETWORK_ATTEMPTS)
    _NETWORK_ATTEMPTS.clear()
    assert not attempts_during_test, (
        f"guarded child attempted network during test: {attempts_during_test!r}"
    )


_DETECTION = {"effective_content_type": "application/pdf"}
_STRONG_TEXT = " ".join(f"token{i}" for i in range(80))


class _FakePage:
    def __init__(self, number: int = 0, *, images: list[tuple[Any, ...]] | None = None) -> None:
        self.number = number
        self.rect = SimpleNamespace(width=612.0, height=792.0)
        self._images = list(images or [])
        self.pixmap_calls = 0

    def get_images(self) -> list[tuple[Any, ...]]:
        return list(self._images)

    def get_drawings(self) -> list[Any]:
        return []

    def get_pixmap(self, *_: Any, **__: Any) -> Any:
        self.pixmap_calls += 1
        raise AssertionError("strict parser must never rasterize")


class _FakeDocument:
    def __init__(
        self,
        page_count: int,
        page_factory: Callable[[int], _FakePage] | None = None,
    ) -> None:
        self.page_count = page_count
        self.needs_pass = False
        self.closed = False
        self._page_factory = page_factory or (lambda index: _FakePage(index))
        self.pages: list[_FakePage] = []

    def load_page(self, index: int) -> _FakePage:
        page = self._page_factory(index)
        self.pages.append(page)
        return page

    def close(self) -> None:
        self.closed = True


class _FakeTable:
    bbox = (0.0, 0.0, 10.0, 10.0)

    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = rows

    def extract(self) -> list[list[str]]:
        return self._rows


class _FakeTablePage(_FakePage):
    def __init__(self, rows: list[list[str]], number: int = 0) -> None:
        super().__init__(number)
        self._table = _FakeTable(rows)

    def find_tables(self) -> Any:
        return SimpleNamespace(tables=[self._table])

    def get_text(self, *_: Any, **__: Any) -> dict[str, list[Any]]:
        return {"blocks": []}

    def annots(self) -> list[Any]:
        return []


def _strict_config(**overrides: Any) -> dict[str, Any]:
    return processing.default_processing_config(
        {
            "strict_parse_profile": strict.STRICT_PARSE_PROFILE_ID,
            "document_processing_engine": processing.APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
            "document_processing_engine_explicit": True,
            "ocr_enabled": False,
            "visual_lane_mode": processing.APS_VISUAL_LANE_MODE_BASELINE,
            "content_parse_timeout_seconds": 0,
            **overrides,
        }
    )


def _valid_result(**overrides: Any) -> dict[str, Any]:
    return {
        "extractor_id": processing.APS_PDF_EXTRACTOR_ID,
        "ocr_page_count": 0,
        "degradation_codes": [],
        "ordered_units": [],
        "normalized_text": "",
        **overrides,
    }


def _patch_one_page(
    monkeypatch: pytest.MonkeyPatch,
    *,
    text: str = _STRONG_TEXT,
    images: list[tuple[Any, ...]] | None = None,
) -> _FakeDocument:
    document = _FakeDocument(1, lambda index: _FakePage(index, images=images))
    monkeypatch.setattr(processing.fitz, "open", lambda **_: document)
    monkeypatch.setattr(
        processing,
        "_extract_native_pdf_units",
        lambda page, **_: [
            {
                "page_number": page.number + 1,
                "unit_kind": "pdf_text_block",
                "text": text,
                "bbox": [0.0, 0.0, 1.0, 1.0],
            }
        ],
    )
    return document


def _run_strict_pdf(config: dict[str, Any]) -> dict[str, Any]:
    return processing._process_pdf(
        content=b"%PDF",
        detection=_DETECTION,
        config=config,
        deadline=None,
    )


def test_frozen_profile_constants_are_exact() -> None:
    assert strict.STRICT_PARSE_PROFILE_ID == "dual_live_proof_v1"
    assert strict.STRICT_PARSE_MAX_PAGES == 500
    assert strict.STRICT_PARSE_MAX_RENDERED_PIXELS == 0
    assert strict.STRICT_PARSE_MAX_TEXT_BYTES == 20_000_000
    assert strict.STRICT_PARSE_MAX_TABLE_ROWS == 10_000
    assert strict.STRICT_PARSE_MAX_TABLE_COLUMNS == 200
    assert strict.STRICT_PARSE_MAX_TEMP_BYTES == 0
    assert strict.STRICT_PARSE_MAX_PEAK_RSS_BYTES == 2_147_483_648
    assert strict.STRICT_PARSE_MAX_WALL_SECONDS == 300
    assert strict.STRICT_PARSE_MAX_CPU_SECONDS == 300
    assert strict.STRICT_PARSE_MAX_OUTPUT_BYTES == 30_000_000
    assert strict.STRICT_PARSE_MAX_SUBPROCESS_SPAWNS == 0


def test_strict_entry_signature_has_no_override_surface() -> None:
    signature = inspect.signature(strict.parse_admitted_blob_strict)
    assert list(signature.parameters) == ["blob_path", "expected_sha256"]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )


def test_subprocess_denial_guard_wraps_every_available_primitive_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    targets: list[tuple[Any, str]] = [(subprocess, "Popen")]
    for name in dir(os):
        if (
            name == "system"
            or name == "startfile"
            or name.startswith("spawn")
            or name.startswith("exec")
            or name.startswith("posix_spawn")
        ) and callable(getattr(os, name, None)):
            targets.append((os, name))

    for owner, name in targets:
        monkeypatch.setattr(owner, name, getattr(owner, name))

    strict.install_subprocess_denial_guard()
    first_wrappers = {(id(owner), name): getattr(owner, name) for owner, name in targets}
    strict.install_subprocess_denial_guard()

    for owner, name in targets:
        wrapper = getattr(owner, name)
        assert wrapper is first_wrappers[(id(owner), name)]
        with pytest.raises(strict.StrictParseViolation, match="strict_subprocess_spawn_refused"):
            wrapper()


def test_entry_rehashes_blob_builds_only_pinned_config_and_restores_tempdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blob = tmp_path / "admitted.pdf"
    blob.write_bytes(b"%PDF admitted bytes")
    expected = hashlib.sha256(blob.read_bytes()).hexdigest()
    calls: list[dict[str, Any]] = []
    guard_calls = 0
    original_tempdir = tempfile.tempdir

    def record_guard() -> None:
        nonlocal guard_calls
        guard_calls += 1

    def fake_process_document(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        scratch = Path(tempfile.gettempdir())
        assert scratch.is_dir()
        assert list(scratch.iterdir()) == []
        return _valid_result()

    monkeypatch.setattr(strict, "install_subprocess_denial_guard", record_guard)
    monkeypatch.setattr(processing, "process_document", fake_process_document)

    result = strict.parse_admitted_blob_strict(
        blob_path=blob,
        expected_sha256=expected,
    )

    assert result == _valid_result()
    assert guard_calls == 1
    assert tempfile.tempdir == original_tempdir
    assert calls == [
        {
            "content": blob.read_bytes(),
            "declared_content_type": "application/pdf",
            "config": {
                "strict_parse_profile": strict.STRICT_PARSE_PROFILE_ID,
                "content_parse_max_pages": strict.STRICT_PARSE_MAX_PAGES,
                "content_parse_timeout_seconds": strict.STRICT_PARSE_MAX_WALL_SECONDS,
                "document_processing_engine": processing.APS_DOCUMENT_PROCESSING_ENGINE_BASELINE,
                "document_processing_engine_explicit": True,
                "ocr_enabled": False,
                "visual_lane_mode": processing.APS_VISUAL_LANE_MODE_BASELINE,
            },
        }
    ]


def test_entry_rejects_blob_hash_mismatch_before_processing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blob = tmp_path / "admitted.pdf"
    blob.write_bytes(b"%PDF admitted bytes")
    monkeypatch.setattr(strict, "install_subprocess_denial_guard", lambda: None)
    monkeypatch.setattr(
        processing,
        "process_document",
        lambda **_: pytest.fail("hash mismatch must stop before processing"),
    )

    with pytest.raises(strict.StrictParseViolation, match="strict_blob_sha256_mismatch"):
        strict.parse_admitted_blob_strict(
            blob_path=blob,
            expected_sha256="0" * 64,
        )


def test_entry_rejects_temp_disk_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blob = tmp_path / "admitted.pdf"
    blob.write_bytes(b"%PDF admitted bytes")
    monkeypatch.setattr(strict, "install_subprocess_denial_guard", lambda: None)

    def fake_process_document(**_: Any) -> dict[str, Any]:
        Path(tempfile.gettempdir(), "residual.bin").write_bytes(b"x")
        return _valid_result()

    monkeypatch.setattr(processing, "process_document", fake_process_document)

    with pytest.raises(strict.StrictParseViolation, match="strict_temp_disk_limit_exceeded"):
        strict.parse_admitted_blob_strict(
            blob_path=blob,
            expected_sha256=hashlib.sha256(blob.read_bytes()).hexdigest(),
        )


def test_entry_rejects_canonical_output_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blob = tmp_path / "admitted.pdf"
    blob.write_bytes(b"%PDF admitted bytes")
    monkeypatch.setattr(strict, "install_subprocess_denial_guard", lambda: None)
    monkeypatch.setattr(strict, "STRICT_PARSE_MAX_OUTPUT_BYTES", 1)
    monkeypatch.setattr(processing, "process_document", lambda **_: _valid_result())

    with pytest.raises(strict.StrictParseViolation, match="strict_output_limit_exceeded"):
        strict.parse_admitted_blob_strict(
            blob_path=blob,
            expected_sha256=hashlib.sha256(blob.read_bytes()).hexdigest(),
        )


@pytest.mark.parametrize(
    ("result", "error"),
    [
        (_valid_result(extractor_id="other"), "strict_extractor_refused"),
        (_valid_result(ocr_page_count=1), "strict_ocr_page_count_refused"),
        (_valid_result(degradation_codes=["ocr_fallback_used"]), "strict_degradation_refused"),
        (_valid_result(degradation_codes=["visual_capture_failed"]), "strict_degradation_refused"),
        (
            {
                key: value
                for key, value in _valid_result().items()
                if key != "degradation_codes"
            },
            "strict_degradation_refused",
        ),
        (_valid_result(degradation_codes="ocr_fallback_used"), "strict_degradation_refused"),
        (_valid_result(degradation_codes=["benign", 7]), "strict_degradation_refused"),
    ],
)
def test_entry_rejects_nonbaseline_postconditions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    result: dict[str, Any],
    error: str,
) -> None:
    blob = tmp_path / "admitted.pdf"
    blob.write_bytes(b"%PDF admitted bytes")
    monkeypatch.setattr(strict, "install_subprocess_denial_guard", lambda: None)
    monkeypatch.setattr(processing, "process_document", lambda **_: result)

    with pytest.raises(strict.StrictParseViolation, match=error):
        strict.parse_admitted_blob_strict(
            blob_path=blob,
            expected_sha256=hashlib.sha256(blob.read_bytes()).hexdigest(),
        )


def test_strict_501_page_cap_fails_while_generic_path_admits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    documents: list[_FakeDocument] = []

    def fake_open(**_: Any) -> _FakeDocument:
        document = _FakeDocument(501)
        documents.append(document)
        return document

    monkeypatch.setattr(processing.fitz, "open", fake_open)
    monkeypatch.setattr(
        processing,
        "_extract_native_pdf_units",
        lambda page, **_: [{"page_number": page.number + 1, "text": _STRONG_TEXT}],
    )
    monkeypatch.setattr(processing.nrc_aps_ocr, "tesseract_available", lambda: False)
    monkeypatch.setattr(
        processing.nrc_aps_advanced_ocr,
        "run_advanced_ocr",
        lambda **_: pytest.fail("OCR must remain unreachable"),
    )

    with pytest.raises(strict.StrictParseViolation, match="strict_page_limit_exceeded"):
        _run_strict_pdf(_strict_config(content_parse_max_pages=50_000))
    assert documents[0].pages == []

    result = processing._process_pdf(
        content=b"%PDF",
        detection=_DETECTION,
        config=processing.default_processing_config(
            {
                "content_parse_max_pages": 500,
                "content_parse_timeout_seconds": 0,
                "ocr_enabled": False,
            }
        ),
        deadline=None,
    )
    assert result["page_count"] == 501
    assert all(page.pixmap_calls == 0 for page in documents[1].pages)


def test_generic_hybrid_gate_honors_ocr_disabled_without_degradation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = _patch_one_page(monkeypatch, images=[(0, 0, 200, 200)])
    monkeypatch.setattr(processing.nrc_aps_ocr, "tesseract_available", lambda: True)
    monkeypatch.setattr(
        processing,
        "_run_page_ocr",
        lambda **_: pytest.fail("ocr_enabled=false must close hybrid OCR"),
    )
    monkeypatch.setattr(
        processing.nrc_aps_advanced_ocr,
        "run_advanced_ocr",
        lambda **_: pytest.fail("advanced OCR must remain unreachable"),
    )

    result = processing._process_pdf(
        content=b"%PDF",
        detection=_DETECTION,
        config=processing.default_processing_config(
            {"ocr_enabled": False, "content_parse_timeout_seconds": 0}
        ),
        deadline=None,
    )

    assert result["ocr_page_count"] == 0
    assert "ocr_hybrid_failed" not in result["degradation_codes"]
    assert document.pages[0].pixmap_calls == 0


def test_forced_strict_hybrid_entry_is_refused_before_ocr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = _patch_one_page(monkeypatch, images=[(0, 0, 200, 200)])
    monkeypatch.setattr(processing.nrc_aps_ocr, "tesseract_available", lambda: True)
    monkeypatch.setattr(
        processing,
        "_run_page_ocr",
        lambda **_: pytest.fail("strict refusal must precede OCR"),
    )

    with pytest.raises(strict.StrictParseViolation, match="strict_ocr_path_refused"):
        _run_strict_pdf(_strict_config(ocr_enabled=True))
    assert document.pages[0].pixmap_calls == 0


def test_weak_native_strict_page_uses_no_ocr_or_rendering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = _patch_one_page(monkeypatch, text="few")
    monkeypatch.setattr(processing.nrc_aps_ocr, "tesseract_available", lambda: True)
    monkeypatch.setattr(
        processing,
        "_run_page_ocr",
        lambda **_: pytest.fail("Tesseract must remain unreachable"),
    )
    monkeypatch.setattr(
        processing.nrc_aps_advanced_ocr,
        "run_advanced_ocr",
        lambda **_: pytest.fail("advanced OCR must remain unreachable"),
    )

    result = _run_strict_pdf(_strict_config())

    assert result["ocr_page_count"] == 0
    assert not set(result["degradation_codes"]) & strict.STRICT_PARSE_FORBIDDEN_DEGRADATION_CODES
    assert document.pages[0].pixmap_calls == 0


def test_strict_complex_table_route_refuses_before_advanced_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_type = next(iter(processing.nrc_aps_settings.COMPLEX_TABLE_DOC_TYPES))
    monkeypatch.setattr(
        processing,
        "_load_advanced_table_parser",
        lambda: pytest.fail("Camelot adapter must remain unreachable"),
    )

    with pytest.raises(strict.StrictParseViolation, match="strict_advanced_table_refused"):
        processing._extract_native_pdf_units(
            _FakeTablePage([]),
            config=_strict_config(document_type=document_type),
            pdf_content=b"%PDF",
        )


def test_generic_complex_table_route_lazy_loads_advanced_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_type = next(iter(processing.nrc_aps_settings.COMPLEX_TABLE_DOC_TYPES))
    calls: list[dict[str, Any]] = []

    def extract_advanced_table(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {"tables": [], "exclusion_bboxes": []}

    adapter = SimpleNamespace(extract_advanced_table=extract_advanced_table)
    monkeypatch.setattr(
        processing,
        "_load_advanced_table_parser",
        lambda: adapter,
    )

    result = processing._extract_native_pdf_units(
        _FakeTablePage([]),
        config=processing.default_processing_config(
            {"document_type": document_type}
        ),
        pdf_content=b"%PDF",
    )

    assert result == []
    assert calls == [{"pdf_source": b"%PDF", "page_index_0": 0}]


def test_strict_table_refusal_closes_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_type = next(iter(processing.nrc_aps_settings.COMPLEX_TABLE_DOC_TYPES))
    document = _FakeDocument(1, lambda index: _FakeTablePage([], number=index))
    monkeypatch.setattr(processing.fitz, "open", lambda **_: document)
    monkeypatch.setattr(
        processing,
        "_load_advanced_table_parser",
        lambda: pytest.fail("Camelot adapter must remain unreachable"),
    )

    with pytest.raises(strict.StrictParseViolation, match="strict_advanced_table_refused"):
        _run_strict_pdf(_strict_config(document_type=document_type))
    assert document.closed


def test_strict_text_bound_counts_utf8_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "\N{LATIN SMALL LETTER E WITH ACUTE}" * (
        strict.STRICT_PARSE_MAX_TEXT_BYTES // 2 + 1
    )
    _patch_one_page(monkeypatch, text=text)
    monkeypatch.setattr(processing, "_normalize_text", lambda value: value)
    monkeypatch.setattr(
        processing,
        "_quality_metrics",
        lambda *_args, **_kwargs: {
            "quality_status": processing.APS_QUALITY_STATUS_STRONG,
            "char_count": len(text),
            "token_count": 30,
        },
    )
    monkeypatch.setattr(processing, "_normalize_query_tokens", lambda _: ["token"] * 30)
    monkeypatch.setattr(processing.nrc_aps_ocr, "tesseract_available", lambda: False)

    with pytest.raises(strict.StrictParseViolation, match="strict_text_limit_exceeded"):
        _run_strict_pdf(_strict_config())


def test_strict_table_row_bound_is_document_global() -> None:
    config = _strict_config()
    processing._extract_native_pdf_units(
        _FakeTablePage([["x"]] * 6_000, number=0),
        config=config,
        pdf_content=b"%PDF",
    )

    with pytest.raises(strict.StrictParseViolation, match="strict_table_row_limit_exceeded"):
        processing._extract_native_pdf_units(
            _FakeTablePage([["x"]] * 4_001, number=1),
            config=config,
            pdf_content=b"%PDF",
        )


def test_strict_table_column_bound() -> None:
    with pytest.raises(strict.StrictParseViolation, match="strict_table_column_limit_exceeded"):
        processing._extract_native_pdf_units(
            _FakeTablePage([["x"] * 201]),
            config=_strict_config(),
            pdf_content=b"%PDF",
        )


def test_strict_peak_memory_breach_fails_at_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = _patch_one_page(monkeypatch)
    monkeypatch.setattr(processing.nrc_aps_ocr, "tesseract_available", lambda: False)
    samples = iter([0, strict.STRICT_PARSE_MAX_PEAK_RSS_BYTES + 1])
    monkeypatch.setattr(
        processing,
        "_peak_rss_bytes",
        lambda: next(samples),
    )

    with pytest.raises(strict.StrictParseViolation, match="strict_memory_limit_exceeded"):
        _run_strict_pdf(_strict_config())
    assert document.closed


def test_strict_cpu_breach_fails_at_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_one_page(monkeypatch)
    monkeypatch.setattr(processing.nrc_aps_ocr, "tesseract_available", lambda: False)
    monkeypatch.setattr(processing, "_peak_rss_bytes", lambda: 0)
    samples = iter([0.0, strict.STRICT_PARSE_MAX_CPU_SECONDS + 1.0])
    monkeypatch.setattr(processing.time, "process_time", lambda: next(samples))

    with pytest.raises(strict.StrictParseViolation, match="strict_cpu_limit_exceeded"):
        _run_strict_pdf(_strict_config())


def test_strict_deadline_breach_fails() -> None:
    with pytest.raises(ValueError, match="content_parse_timeout_exceeded"):
        processing._process_pdf(
            content=b"%PDF",
            detection=_DETECTION,
            config=_strict_config(),
            deadline=0.0,
        )


def test_strict_deadline_after_open_closes_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = _FakeDocument(1)
    monkeypatch.setattr(processing.fitz, "open", lambda **_: document)
    samples = iter([0.0, 2.0])
    monkeypatch.setattr(processing.time, "monotonic", lambda: next(samples))

    with pytest.raises(ValueError, match="content_parse_timeout_exceeded"):
        processing._process_pdf(
            content=b"%PDF",
            detection=_DETECTION,
            config=_strict_config(),
            deadline=1.0,
        )
    assert document.closed


def test_guarded_child_network_denial_self_probe() -> None:
    assert _GUARDS_INSTALLED_BEFORE_SERVICE_IMPORTS

    def socket_call(method_name: str, *args: Any) -> Callable[[], Any]:
        def callback() -> Any:
            candidate = socket.socket()
            try:
                return getattr(candidate, method_name)(*args)
            finally:
                candidate.close()

        return callback

    def session_request() -> Any:
        with _GUARDED_REQUESTS.Session() as session:
            return session.get("https://example.invalid")

    probes: list[tuple[str, Callable[[], Any]]] = [
        ("socket.connect", socket_call("connect", ("127.0.0.1", 9))),
        ("socket.connect_ex", socket_call("connect_ex", ("127.0.0.1", 9))),
        ("socket.bind", socket_call("bind", ("127.0.0.1", 0))),
        ("socket.sendto", socket_call("sendto", b"x", ("127.0.0.1", 9))),
        (
            "socket.create_connection",
            lambda: socket.create_connection(("example.invalid", 443)),
        ),
        ("socket.getaddrinfo", lambda: socket.getaddrinfo("example.invalid", 443)),
        ("socket.gethostbyname", lambda: socket.gethostbyname("example.invalid")),
        (
            "socket.gethostbyname_ex",
            lambda: socket.gethostbyname_ex("example.invalid"),
        ),
        ("socket.gethostbyaddr", lambda: socket.gethostbyaddr("127.0.0.1")),
        (
            "socket.getnameinfo",
            lambda: socket.getnameinfo(("127.0.0.1", 443), 0),
        ),
        ("socket.getfqdn", lambda: socket.getfqdn("example.invalid")),
        (
            "requests.api.request",
            lambda: _GUARDED_REQUESTS.get("https://example.invalid"),
        ),
        ("requests.Session.request", session_request),
    ]

    observed: tuple[str, ...] = ()
    try:
        for label, callback in probes:
            with pytest.raises(_TestNetworkDenied, match=re.escape(label)):
                callback()
    finally:
        observed = tuple(_NETWORK_ATTEMPTS)
        _NETWORK_ATTEMPTS.clear()

    assert observed == tuple(label for label, _callback in probes)


test_guarded_child_network_denial_self_probe.__test__ = _GUARDED_CHILD
