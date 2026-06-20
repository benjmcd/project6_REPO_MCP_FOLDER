from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_TESTS_ROOT = REPO_ROOT / "backend" / "tests"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "playwright.yml"

BACKEND_SHARD_PATTERNS = (
    "test_admission_evaluator_*.py",
    "test_aps_retrieval_*.py",
    "test_backend_config.py",
    "test_ci_coverage_completeness.py",
    "test_deployment_profile_*.py",
    "test_diagnostics_ref_*.py",
    "test_legacy_api_*.py",
    "test_layer3_*.py",
    "test_market_*.py",
    "test_analyst_*.py",
    "test_nrc_aps_*.py",
    "test_pre_body_*.py",
    "test_review_browser_*.py",
    "test_review_nrc_aps_candidate_b_trace_*.py",
    "test_review_nrc_aps_document_trace_page.py",
    "test_review_nrc_aps_gate_reports.py",
    "test_review_nrc_aps_operator_identity*.py",
    "test_review_nrc_aps_page.py",
    "test_review_nrc_aps_workbench_compare_*.py",
    "test_release_*.py",
    "test_sec_refs.py",
    "test_sec_xbrl_*.py",
    "test_visual_artifact_*.py",
)

RUNTIME_REQUIRED_REASON = (
    "requires-prebuilt-nrc-aps-local-corpus-runtime: tests depend on an existing "
    "storage_test_runtime/lc_e2e run database and storage tree; fresh CI does "
    "not generate runtime artifacts in validate-only backend shards"
)

EXCLUDED_BACKEND_TESTS = {
    "test_review_nrc_aps_api.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_catalog.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_details.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_document_trace_api.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_document_trace_service.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_graph.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_runtime_db.py": RUNTIME_REQUIRED_REASON,
    "test_review_nrc_aps_tree.py": RUNTIME_REQUIRED_REASON,
}


def _backend_test_files() -> list[str]:
    return sorted(path.name for path in BACKEND_TESTS_ROOT.glob("test_*.py") if path.is_file())


def _covered_by_backend_shard(file_name: str) -> bool:
    return any(fnmatch(file_name, pattern) for pattern in BACKEND_SHARD_PATTERNS)


def _workflow_backend_patterns() -> tuple[str, ...]:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"patterns = \(\s*(?P<body>.*?)\s*\)\s*files = sorted",
        workflow_text,
        flags=re.DOTALL,
    )
    assert match is not None, "Could not locate backend shard patterns tuple in playwright.yml"
    return tuple(re.findall(r'"([^"]+\.py)"', match.group("body")))


def test_backend_test_files_are_ci_covered_or_allowlisted() -> None:
    all_files = _backend_test_files()
    assert all_files, "backend/tests/test_*.py inventory is empty"

    missing_allowlist_entries = [
        file_name for file_name in EXCLUDED_BACKEND_TESTS if file_name not in all_files
    ]
    assert missing_allowlist_entries == []

    covered = {file_name for file_name in all_files if _covered_by_backend_shard(file_name)}
    excluded = set(EXCLUDED_BACKEND_TESTS)
    uncovered = sorted(set(all_files) - covered - excluded)
    assert uncovered == []


def test_backend_test_allowlist_is_concrete_and_not_shadow_covered() -> None:
    for file_name, reason in EXCLUDED_BACKEND_TESTS.items():
        assert reason.startswith("requires-"), file_name
        assert "runtime" in reason, file_name
        assert not _covered_by_backend_shard(file_name), file_name


def test_backend_shard_pattern_mirror_matches_workflow() -> None:
    workflow_patterns = _workflow_backend_patterns()
    assert workflow_patterns == BACKEND_SHARD_PATTERNS
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    for pattern in BACKEND_SHARD_PATTERNS:
        assert f'"{pattern}"' in workflow_text
