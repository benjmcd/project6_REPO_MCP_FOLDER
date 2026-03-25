from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ReplayExpected:
    parse_status: str
    status_class: str
    schema_variant: str | None = None
    results_key: str | None = None
    raw_total_key: str | None = None
    count_returned: int | None = None
    total_hits: int | None = None
    accession_numbers: list[str] = field(default_factory=list)
    wrapper_variant: str | None = None
    projection_keys: list[str] = field(default_factory=list)
    roundtrip_payload_hash: str | None = None
    dialect_order: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReplayExpected:
        return cls(
            parse_status=str(payload.get("parse_status") or ""),
            status_class=str(payload.get("status_class") or ""),
            schema_variant=payload.get("schema_variant"),
            results_key=payload.get("results_key"),
            raw_total_key=payload.get("raw_total_key"),
            count_returned=payload.get("count_returned"),
            total_hits=payload.get("total_hits"),
            accession_numbers=[str(item) for item in payload.get("accession_numbers", []) if str(item).strip()],
            wrapper_variant=payload.get("wrapper_variant"),
            projection_keys=[str(item) for item in payload.get("projection_keys", []) if str(item).strip()],
            roundtrip_payload_hash=payload.get("roundtrip_payload_hash"),
            dialect_order=[str(item) for item in payload.get("dialect_order", []) if str(item).strip()],
        )


@dataclass
class ReplayCase:
    case_id: str
    case_type: str
    signature: str
    endpoint: str
    dialect: str
    request_body: dict[str, Any]
    response_status: int
    response_body_text: str
    response_headers: dict[str, Any]
    metadata: dict[str, Any]
    expected: ReplayExpected
    source_run_id: str | None = None
    source_snapshot: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    synthetic: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["expected"] = self.expected.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReplayCase:
        return cls(
            case_id=str(payload.get("case_id") or ""),
            case_type=str(payload.get("case_type") or ""),
            signature=str(payload.get("signature") or ""),
            endpoint=str(payload.get("endpoint") or ""),
            dialect=str(payload.get("dialect") or ""),
            request_body=dict(payload.get("request_body") or {}),
            response_status=int(payload.get("response_status") or 0),
            response_body_text=str(payload.get("response_body_text") or ""),
            response_headers=dict(payload.get("response_headers") or {}),
            metadata=dict(payload.get("metadata") or {}),
            expected=ReplayExpected.from_dict(dict(payload.get("expected") or {})),
            source_run_id=(str(payload.get("source_run_id")) if payload.get("source_run_id") is not None else None),
            source_snapshot=(str(payload.get("source_snapshot")) if payload.get("source_snapshot") is not None else None),
            evidence_refs=[str(item) for item in payload.get("evidence_refs", []) if str(item).strip()],
            synthetic=bool(payload.get("synthetic", False)),
        )


@dataclass
class ReplayCorpusIndex:
    schema_version: int
    tool_version: str
    source_roots: list[str]
    source_run_ids: list[str]
    case_count: int
    case_files: list[str]
    case_checksums: dict[str, str]
    source_fingerprint: str
    coverage: dict[str, int]
    generated_at: str | None = None
    source_manifest_count: int = 0
    diff_summary_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReplayCorpusIndex:
        return cls(
            schema_version=int(payload.get("schema_version") or 0),
            tool_version=str(payload.get("tool_version") or ""),
            source_roots=[str(item) for item in payload.get("source_roots", []) if str(item).strip()],
            source_run_ids=[str(item) for item in payload.get("source_run_ids", []) if str(item).strip()],
            case_count=int(payload.get("case_count") or 0),
            case_files=[str(item) for item in payload.get("case_files", []) if str(item).strip()],
            case_checksums={str(k): str(v) for k, v in dict(payload.get("case_checksums") or {}).items()},
            source_fingerprint=str(payload.get("source_fingerprint") or ""),
            coverage={str(k): int(v) for k, v in dict(payload.get("coverage") or {}).items()},
            generated_at=(str(payload.get("generated_at")) if payload.get("generated_at") is not None else None),
            source_manifest_count=int(payload.get("source_manifest_count") or 0),
            diff_summary_file=(str(payload.get("diff_summary_file")) if payload.get("diff_summary_file") is not None else None),
        )


@dataclass
class ReplayRunReport:
    schema_version: int
    corpus_path: str
    passed: bool
    total_cases: int
    failed_cases: int
    warning_count: int
    failures: list[dict[str, Any]]
    warnings: list[str]
    generated_at: str | None = None
    overrides_applied: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
