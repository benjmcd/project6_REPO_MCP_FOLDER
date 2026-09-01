"""Selection-cap regression tests for the ScienceBase connector.

Live-run-confirmed defect (2026-09-01, run f057e456…): max_files was applied
over ALL surfaced files before surface/extension/dedup filtering, so an MCS
item whose first file is metadata (.xml) consumed the only selection slot and
every CSV behind it was ignored_selection_cap — the file cap could never
yield a CSV. The cap must count QUALIFYING candidates only.
"""

from app.services.connectors_sciencebase import (
    _capped_selection_indexes,
    _duplicate_candidate_indexes,
)
from app.services.sciencebase_connector.contracts import ArtifactCandidate


def _candidate(name: str, *, key: str | None = None, surface: str = "files") -> ArtifactCandidate:
    return ArtifactCandidate(
        stable_release_key="doi:10.5066/test",
        stable_release_identifier="doi:10.5066/test",
        identifiers_json=[],
        sciencebase_item_id="item-1",
        sciencebase_item_url="https://www.sciencebase.gov/catalog/item/item-1",
        artifact_surface=surface,
        artifact_locator_type="downloadUri",
        sciencebase_file_name=name,
        sciencebase_download_uri=f"https://www.sciencebase.gov/catalog/file/get/item-1?name={name}",
        remote_checksum_type=None,
        remote_checksum_value=None,
        source_reference_json={},
        canonical_artifact_key=key or f"key::{name}",
        source_artifact_key=f"src::{name}",
        dedup_hint=key or f"key::{name}",
        permission_snapshot_json={},
        access_level_summary="public",
        public_read_confirmed=True,
    )


def _select(candidates, *, max_files, selection_mode="first_n", seed=0):
    duplicates = _duplicate_candidate_indexes(candidates)
    return _capped_selection_indexes(
        candidates,
        max_files=max_files,
        selection_mode=selection_mode,
        seed=seed,
        duplicates=duplicates,
        surface_policy="files_only",
        allowed_extensions=[".csv"],
    )


def test_leading_non_tabular_file_does_not_consume_the_file_cap() -> None:
    candidates = [_candidate("mcs2023-germa_meta.xml"), _candidate("mcs2023-germa_salient.csv")]

    selected, truncated = _select(candidates, max_files=1)

    assert selected == {1}
    assert truncated is False


def test_cap_truncates_only_qualifying_candidates() -> None:
    candidates = [
        _candidate("meta.xml"),
        _candidate("salient.csv"),
        _candidate("world.csv"),
    ]

    selected, truncated = _select(candidates, max_files=1)

    assert selected == {1}
    assert truncated is True


def test_duplicates_do_not_consume_the_cap() -> None:
    candidates = [
        _candidate("salient.csv", key="same-bytes"),
        _candidate("salient-copy.csv", key="same-bytes"),
        _candidate("world.csv"),
    ]

    selected, truncated = _select(candidates, max_files=1)

    assert selected == {0}
    assert truncated is True


def test_higher_precedence_surface_evicts_earlier_winner() -> None:
    candidates = [
        _candidate("salient.csv", key="same-bytes", surface="distributionLinks"),
        _candidate("salient.csv", key="same-bytes", surface="files"),
        _candidate("world.csv"),
    ]

    duplicates = _duplicate_candidate_indexes(candidates)
    selected, truncated = _select(candidates, max_files=1)

    assert duplicates == {0}
    assert selected == {1}
    assert truncated is True


def test_sample_mode_samples_among_qualifying() -> None:
    candidates = [
        _candidate("meta.xml"),
        _candidate("salient.csv"),
        _candidate("world.csv"),
    ]

    selected, truncated = _select(candidates, max_files=1, selection_mode="sample", seed=7)

    assert len(selected) == 1
    assert selected <= {1, 2}
    assert truncated is True


def test_uncapped_returns_all_qualifying() -> None:
    candidates = [
        _candidate("meta.xml"),
        _candidate("salient.csv"),
        _candidate("world.csv", surface="webLinks"),
    ]

    selected, truncated = _select(candidates, max_files=0)

    assert selected == {1}
    assert truncated is False
