from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "onlook-ui" / "data"
FIXTURE_PATH = DATA_ROOT / "fixture.json"

ANALYST_INTEGRATION_SAMPLE = {
    "sources": {
        "shipping": [
            {
                "vessel_id": "MV1",
                "region": "USW",
                "date": "2026-01-15",
                "tons": 1200,
            }
        ],
        "bonds": [{"region": "USW", "date": "2026-01-15", "spread_bps": 45}],
        "regulatory": [{"region": "USW", "date": "2026-01-15", "rule_id": "R-9"}],
    },
    "link_keys": ["region", "date"],
}

ANALYST_VALIDATION_SAMPLE = {
    "rows": [
        {"entity": "A", "price": 10.0},
        {"entity": "B", "price": 11.0},
        {"entity": "C", "price": 99.0},
    ],
    "options": {
        "required_fields": ["entity", "price"],
        "numeric_columns": ["price"],
        "outlier_method": "zscore",
        "zscore_threshold": 2.0,
        "normalize_columns": ["price"],
    },
}

ANALYST_INSIGHT_SAMPLE = {
    "validation_summary": {
        "valid_count": 100,
        "invalid_count": 4,
        "failed_count": 0,
        "pass_rate": 0.92,
    },
    "integrated": {
        "signals_by_category": {"shipping": 50, "bonds": 45, "regulatory": 5},
        "signal_trajectory": [1.0, 1.05, 1.1, 1.4, 1.9],
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a committed same-origin fixture snapshot for the Onlook sandbox lanes."
    )
    parser.add_argument(
        "--review-api-base",
        default="http://127.0.0.1:8000/api/v1/review/nrc-aps",
        help="Source review API base to snapshot.",
    )
    parser.add_argument(
        "--api-v1-base",
        default="http://127.0.0.1:8000/api/v1",
        help="Source API v1 base for analyst alias samples.",
    )
    parser.add_argument(
        "--output",
        default=str(FIXTURE_PATH),
        help="Destination fixture JSON path.",
    )
    return parser


def selection_key(
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_bundle_id: str,
) -> str:
    return "::".join([baseline_run_id, candidate_a_run_id, candidate_b_bundle_id])


def target_key(run_id: str, target_id: str) -> str:
    return "::".join([run_id, target_id])


def units_key(run_id: str, target_id: str, page_number: int | None) -> str:
    page = "all" if page_number is None else str(page_number)
    return "::".join([run_id, target_id, page])


def bundle_key(bundle_id: str, fixture_id: str) -> str:
    return "::".join([bundle_id, fixture_id])


def workbench_key(selection: str, fixture_id: str) -> str:
    return "::".join([selection, fixture_id])


def workbench_tab_key(selection: str, fixture_id: str, tab_id: str) -> str:
    return "::".join([selection, fixture_id, tab_id])


def fetch_bytes(url: str, *, method: str = "GET", body: bytes | None = None) -> tuple[bytes, str]:
    request = Request(
        url,
        method=method,
        data=body,
        headers={
            "Accept": "application/json, text/plain;q=0.9, application/pdf;q=0.8, */*;q=0.1"
        },
    )
    if body is not None:
        request.add_header("Content-Type", "application/json")

    with urlopen(request) as response:
        payload = response.read()
        content_type = response.headers.get("Content-Type", "application/octet-stream")
    return payload, content_type


def fetch_json(url: str, *, method: str = "GET", body: dict | None = None) -> dict:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    raw, _ = fetch_bytes(url, method=method, body=payload)
    return json.loads(raw)


def fetch_text(url: str) -> str:
    raw, _ = fetch_bytes(url)
    return raw.decode("utf-8")


def binary_extension(content_type: str) -> str:
    lowered = content_type.lower()
    if "pdf" in lowered:
        return ".pdf"
    if "json" in lowered:
        return ".json"
    if "markdown" in lowered or "text/plain" in lowered:
        return ".txt"
    return ".bin"


def store_binary(data_root: Path, bucket: str, key: str, url: str) -> dict[str, str]:
    raw, content_type = fetch_bytes(url)
    digest = hashlib.sha1(raw).hexdigest()[:16]
    relative_path = Path(bucket) / f"{digest}{binary_extension(content_type)}"
    absolute_path = data_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(raw)
    return {
        "content_type": content_type,
        "relative_path": relative_path.as_posix(),
    }


def parse_prep_summary() -> dict:
    raw = subprocess.check_output(
        [sys.executable, str(ROOT / "tools" / "validate_wb_prep.py")],
        text=True,
    )
    summary = json.loads(raw)
    if not summary.get("passed"):
        raise RuntimeError("validate_wb_prep.py did not return a passing summary.")
    return summary


def build_document_fixture(
    data_root: Path,
    review_api_base: str,
    api_origin: str,
    run_id: str,
    target_id: str,
) -> dict:
    trace = fetch_json(
        f"{review_api_base}/runs/{quote(run_id)}/documents/{quote(target_id)}/trace"
    )
    diagnostics = fetch_json(
        f"{review_api_base}/runs/{quote(run_id)}/documents/{quote(target_id)}/diagnostics"
    )
    normalized_text = fetch_json(
        f"{review_api_base}/runs/{quote(run_id)}/documents/{quote(target_id)}/normalized-text"
    )
    indexed_chunks = fetch_json(
        f"{review_api_base}/runs/{quote(run_id)}/documents/{quote(target_id)}/indexed-chunks"
    )
    extracted_all = fetch_json(
        f"{review_api_base}/runs/{quote(run_id)}/documents/{quote(target_id)}/extracted-units"
    )

    extracted_units: dict[str, dict] = {
        units_key(run_id, target_id, None): extracted_all,
    }
    for geometry in trace.get("source", {}).get("page_geometries", []) or []:
        page_number = geometry.get("page_number")
        if page_number is None:
            continue
        extracted_units[units_key(run_id, target_id, int(page_number))] = fetch_json(
            f"{review_api_base}/runs/{quote(run_id)}/documents/{quote(target_id)}/extracted-units?page_number={int(page_number)}"
        )

    source_endpoint = trace.get("source", {}).get("source_endpoint")
    binary_source = (
        store_binary(data_root, "review-src", target_key(run_id, target_id), f"{api_origin}{source_endpoint}")
        if isinstance(source_endpoint, str) and source_endpoint
        else None
    )

    return {
        "trace": trace,
        "diagnostics": diagnostics,
        "normalized_text": normalized_text,
        "indexed_chunks": indexed_chunks,
        "extracted_units": extracted_units,
        "source_blob": binary_source,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    prep = parse_prep_summary()
    review_api_base = args.review_api_base.rstrip("/")
    api_v1_base = args.api_v1_base.rstrip("/")
    api_origin = api_v1_base.rsplit("/api/v1", 1)[0]
    output_path = Path(args.output).resolve()
    data_root = output_path.parent

    runs = fetch_json(f"{review_api_base}/runs")
    reviewable_runs = [item for item in runs.get("runs", []) if item.get("reviewable")]

    review_payload = {
        "runs": runs,
        "overviews": {},
        "documents": {},
        "traces": {},
        "diagnostics": {},
        "normalized_text": {},
        "indexed_chunks": {},
        "extracted_units": {},
        "source_blobs": {},
    }

    for run in reviewable_runs:
        run_id = str(run["run_id"])
        review_payload["overviews"][run_id] = fetch_json(
            f"{review_api_base}/runs/{quote(run_id)}/overview"
        )
        documents = fetch_json(f"{review_api_base}/runs/{quote(run_id)}/documents")
        review_payload["documents"][run_id] = documents

        for document in documents.get("documents", []):
            target_id = str(document["target_id"])
            document_key = target_key(run_id, target_id)
            exported = build_document_fixture(
                data_root,
                review_api_base,
                api_origin,
                run_id,
                target_id,
            )
            review_payload["traces"][document_key] = exported["trace"]
            review_payload["diagnostics"][document_key] = exported["diagnostics"]
            review_payload["normalized_text"][document_key] = exported["normalized_text"]
            review_payload["indexed_chunks"][document_key] = exported["indexed_chunks"]
            review_payload["source_blobs"][document_key] = exported["source_blob"]
            for key, value in exported["extracted_units"].items():
                review_payload["extracted_units"][key] = value

    baseline_run_id = str(prep["selection"]["baseline_run_id"])
    candidate_a_run_id = str(prep["selection"]["candidate_a_run_id"])
    candidate_b_bundle_id = str(prep["selection"]["candidate_b_bundle_id"])
    selection = selection_key(
        baseline_run_id, candidate_a_run_id, candidate_b_bundle_id
    )

    workbench_sources = fetch_json(f"{review_api_base}/workbench-compare/sources")
    workbench_targets = fetch_json(
        f"{review_api_base}/workbench-compare/targets?baseline_run_id={quote(baseline_run_id)}&candidate_a_run_id={quote(candidate_a_run_id)}&candidate_b_bundle_id={quote(candidate_b_bundle_id)}"
    )

    workbench_payload = {
        "selection_key": selection,
        "sources": workbench_sources,
        "targets": {selection: workbench_targets},
        "manifests": {},
        "tabs": {},
    }

    candidate_b_payload = {
        "manifests": {},
        "raw_json": {},
        "raw_markdown": {},
        "annotated_pdf": {},
    }

    for target in workbench_targets.get("targets", []):
        fixture_id = str(target["fixture_id"])
        wb_key = workbench_key(selection, fixture_id)
        manifest = fetch_json(
            f"{review_api_base}/workbench-compare/targets/{quote(fixture_id)}/manifest?baseline_run_id={quote(baseline_run_id)}&candidate_a_run_id={quote(candidate_a_run_id)}&candidate_b_bundle_id={quote(candidate_b_bundle_id)}"
        )
        workbench_payload["manifests"][wb_key] = manifest

        for tab in manifest.get("tabs", []):
            if not tab.get("available"):
                continue
            tab_id = str(tab["tab_id"])
            workbench_payload["tabs"][workbench_tab_key(selection, fixture_id, tab_id)] = fetch_json(
                f"{review_api_base}/workbench-compare/targets/{quote(fixture_id)}/tabs/{quote(tab_id)}?baseline_run_id={quote(baseline_run_id)}&candidate_a_run_id={quote(candidate_a_run_id)}&candidate_b_bundle_id={quote(candidate_b_bundle_id)}"
            )

        bundle_fixture = bundle_key(candidate_b_bundle_id, fixture_id)
        candidate_manifest = fetch_json(
            f"{review_api_base}/candidate-b-trace/manifest?candidate_b_bundle_id={quote(candidate_b_bundle_id)}&fixture_id={quote(fixture_id)}"
        )
        candidate_b_payload["manifests"][bundle_fixture] = candidate_manifest

        raw_json_url = candidate_manifest.get("artifacts", {}).get("raw_json")
        raw_markdown_url = candidate_manifest.get("artifacts", {}).get("raw_markdown")
        annotated_pdf_url = candidate_manifest.get("artifacts", {}).get("annotated_pdf")

        if raw_json_url:
            candidate_b_payload["raw_json"][bundle_fixture] = fetch_json(
                f"{api_origin}{raw_json_url}"
            )
        if raw_markdown_url:
            candidate_b_payload["raw_markdown"][bundle_fixture] = fetch_text(
                f"{api_origin}{raw_markdown_url}"
            )
        if annotated_pdf_url:
            candidate_b_payload["annotated_pdf"][bundle_fixture] = store_binary(
                data_root,
                "candidate-pdf",
                bundle_fixture,
                f"{api_origin}{annotated_pdf_url}",
            )

    analyst_payload = {
        "integration": fetch_json(
            f"{api_v1_base}/analyst-insight/integration/cross-reference",
            method="POST",
            body=ANALYST_INTEGRATION_SAMPLE,
        ),
        "validation": fetch_json(
            f"{api_v1_base}/analyst-insight/validation/run",
            method="POST",
            body=ANALYST_VALIDATION_SAMPLE,
        ),
        "insight": fetch_json(
            f"{api_v1_base}/analyst-insight/insights/process",
            method="POST",
            body=ANALYST_INSIGHT_SAMPLE,
        ),
    }

    snapshot = {
        "schema_id": "onlook.fixture.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "review_api_base": review_api_base,
            "api_v1_base": api_v1_base,
            "prep": prep,
        },
        "routes": {
            "review": "/",
            "document_trace": prep["recommended_urls"]["baseline_trace"].replace(
                "/review/nrc-aps/document-trace", "/document-trace"
            ),
            "workbench_compare": prep["recommended_urls"][
                "workbench_compare"
            ].replace("/review/nrc-aps/workbench-compare", "/workbench-compare"),
            "candidate_b_trace": prep["recommended_urls"][
                "candidate_b_trace"
            ].replace("/review/nrc-aps/candidate-b-trace", "/candidate-b-trace"),
            "analyst_insight": "/analyst-insight",
        },
        "review": review_payload,
        "workbench": workbench_payload,
        "candidate_b": candidate_b_payload,
        "analyst": analyst_payload,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
