from types import SimpleNamespace

from app.services.layer3_workbench_package_state import (
    active_downstream_unavailable,
    canonical_payload_values,
    dispatched_package_id,
    packages_in_kind_order,
    packages_with_kinds,
    state_downstream_unavailable,
    unexpected_package_kinds,
)


def _package(package_kind: str, output_package_id: str, *, payload_ref: str, payload_hash: str):
    return SimpleNamespace(
        package_kind=package_kind,
        output_package_id=output_package_id,
        payload_ref=payload_ref,
        payload_hash=payload_hash,
    )


def test_state_downstream_unavailable_prefers_explicit_non_empty_state() -> None:
    assert state_downstream_unavailable(
        {"downstream_unavailable": ["next", 7]},
        fallback=("fallback",),
    ) == ("next", "7")


def test_state_downstream_unavailable_uses_fallback_for_missing_or_empty_state() -> None:
    assert state_downstream_unavailable({}, fallback=("fallback",)) == ("fallback",)
    assert state_downstream_unavailable(None, fallback=("fallback",)) == ("fallback",)
    assert state_downstream_unavailable({"downstream_unavailable": []}, fallback=("fallback",)) == ("fallback",)


def test_active_downstream_unavailable_returns_first_completed_stage_next_state() -> None:
    assert active_downstream_unavailable(
        transitions=(
            ({"state": "later_done"}, "later_done", {"downstream_unavailable": ["later_next"]}, ("later",)),
            ({"state": "earlier_done"}, "earlier_done", {"downstream_unavailable": ["earlier_next"]}, ("earlier",)),
        ),
        default_state={"downstream_unavailable": ["default_next"]},
        default_fallback=("default",),
    ) == ("later_next",)


def test_active_downstream_unavailable_falls_back_to_default_stage() -> None:
    assert active_downstream_unavailable(
        transitions=(
            (None, "done", {"downstream_unavailable": ["bad"]}, ("bad",)),
            ({"state": "pending"}, "done", {"downstream_unavailable": ["next"]}, ("next_fallback",)),
        ),
        default_state={},
        default_fallback=("default",),
    ) == ("default",)


def test_packages_in_kind_order_returns_canonical_order() -> None:
    packages = [
        _package("user", "pkg-user", payload_ref="ref-user", payload_hash="hash-user"),
        _package("internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
        _package("review", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
    ]

    ordered = packages_in_kind_order(packages, package_kinds=("internal", "review", "user"))

    assert [package.output_package_id for package in ordered] == ["pkg-internal", "pkg-review", "pkg-user"]


def test_packages_with_kinds_filters_without_mutating_order() -> None:
    packages = [
        _package("internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
        _package("debug", "pkg-debug", payload_ref="ref-debug", payload_hash="hash-debug"),
        _package("review", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
    ]

    filtered = packages_with_kinds(packages, package_kinds=("review", "internal"))

    assert [package.output_package_id for package in filtered] == ["pkg-internal", "pkg-review"]


def test_dispatched_package_id_requires_dispatched_state_and_expected_kind() -> None:
    dispatch_state = {
        "aps_handoff_state": "aps_handoff_dispatched",
        "aps_output_package_kind": "aps_bundle",
        "aps_output_package_id": "pkg-aps",
    }

    assert (
        dispatched_package_id(
            dispatch_state,
            dispatched_state="aps_handoff_dispatched",
            expected_package_kind="aps_bundle",
        )
        == "pkg-aps"
    )
    assert (
        dispatched_package_id(
            {**dispatch_state, "aps_handoff_state": "aps_handoff_ready"},
            dispatched_state="aps_handoff_dispatched",
            expected_package_kind="aps_bundle",
        )
        is None
    )
    assert (
        dispatched_package_id(
            {**dispatch_state, "aps_output_package_kind": "unexpected"},
            dispatched_state="aps_handoff_dispatched",
            expected_package_kind="aps_bundle",
        )
        is None
    )


def test_unexpected_package_kinds_allows_source_kinds_and_exact_dispatched_aps_package() -> None:
    packages = [
        _package("internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
        _package("review", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
        _package("aps_bundle", "pkg-aps-good", payload_ref="ref-aps", payload_hash="hash-aps"),
        _package("aps_bundle", "pkg-aps-extra", payload_ref="ref-aps-extra", payload_hash="hash-aps-extra"),
        _package("debug", "pkg-debug", payload_ref="ref-debug", payload_hash="hash-debug"),
    ]

    unexpected = unexpected_package_kinds(
        packages,
        source_kinds=("internal", "review"),
        aps_handoff_dispatch_state={
            "aps_handoff_state": "aps_handoff_dispatched",
            "aps_output_package_kind": "aps_bundle",
            "aps_output_package_id": "pkg-aps-good",
        },
        aps_dispatched_state="aps_handoff_dispatched",
        aps_package_kind="aps_bundle",
    )

    assert unexpected == ["aps_bundle", "debug"]


def test_canonical_payload_values_accepts_list_and_dict_identity_forms() -> None:
    packages = [
        _package("internal", "pkg-internal", payload_ref="ref-internal", payload_hash="hash-internal"),
        _package("review", "pkg-review", payload_ref="ref-review", payload_hash="hash-review"),
        _package("user", "pkg-user", payload_ref="ref-user", payload_hash="hash-user"),
    ]
    package_kinds = ("internal", "review", "user")

    assert canonical_payload_values(
        values=["ref-user", "ref-internal", "ref-review"],
        packages=packages,
        package_kinds=package_kinds,
        package_attr="payload_ref",
    ) == ["ref-internal", "ref-review", "ref-user"]
    assert canonical_payload_values(
        values={"internal": "hash-internal", "review": "hash-review", "user": "hash-user"},
        packages=packages,
        package_kinds=package_kinds,
        package_attr="payload_hash",
    ) == ["hash-internal", "hash-review", "hash-user"]
    assert canonical_payload_values(
        values={"pkg-internal": "hash-internal", "pkg-review": "hash-review", "pkg-user": "hash-user"},
        packages=packages,
        package_kinds=package_kinds,
        package_attr="payload_hash",
    ) == ["hash-internal", "hash-review", "hash-user"]
    assert (
        canonical_payload_values(
            values={"internal": "hash-internal", "review": "wrong", "user": "hash-user"},
            packages=packages,
            package_kinds=package_kinds,
            package_attr="payload_hash",
        )
        is None
    )
