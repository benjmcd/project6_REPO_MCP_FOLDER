from __future__ import annotations

from typing import Any, Iterable

from app.models.models import L3OutputPackage


def state_downstream_unavailable(
    state: Any,
    *,
    fallback: tuple[str, ...],
) -> tuple[str, ...]:
    values = state.get("downstream_unavailable") if isinstance(state, dict) else None
    if isinstance(values, (list, tuple)) and values:
        return tuple(str(item) for item in values)
    return fallback


def active_downstream_unavailable(
    *,
    transitions: Iterable[tuple[Any, str, Any, tuple[str, ...]]],
    default_state: Any,
    default_fallback: tuple[str, ...],
) -> tuple[str, ...]:
    for completed_state, completed_value, next_state, next_fallback in transitions:
        if isinstance(completed_state, dict) and completed_state.get("state") == completed_value:
            return state_downstream_unavailable(next_state, fallback=next_fallback)
    return state_downstream_unavailable(default_state, fallback=default_fallback)


def packages_in_kind_order(
    packages: list[L3OutputPackage],
    *,
    package_kinds: Iterable[str],
) -> list[L3OutputPackage]:
    packages_by_kind = {package.package_kind: package for package in packages}
    return [packages_by_kind[package_kind] for package_kind in package_kinds]


def packages_with_kinds(
    packages: list[L3OutputPackage],
    *,
    package_kinds: Iterable[str],
) -> list[L3OutputPackage]:
    source_kinds = set(package_kinds)
    return [package for package in packages if package.package_kind in source_kinds]


def dispatched_package_id(
    dispatch_state: dict[str, Any] | None,
    *,
    dispatched_state: str,
    expected_package_kind: str,
) -> str | None:
    if not isinstance(dispatch_state, dict):
        return None
    if dispatch_state.get("aps_handoff_state") != dispatched_state:
        return None
    if dispatch_state.get("aps_output_package_kind") != expected_package_kind:
        return None
    output_package_id = str(dispatch_state.get("aps_output_package_id") or "").strip()
    return output_package_id or None


def unexpected_package_kinds(
    packages: list[L3OutputPackage],
    *,
    source_kinds: Iterable[str],
    aps_handoff_dispatch_state: dict[str, Any] | None,
    aps_dispatched_state: str,
    aps_package_kind: str,
) -> list[str]:
    allowed_source_kinds = set(source_kinds)
    allowed_aps_package_id = dispatched_package_id(
        aps_handoff_dispatch_state,
        dispatched_state=aps_dispatched_state,
        expected_package_kind=aps_package_kind,
    )
    unexpected_kinds = set()
    for package in packages:
        if package.package_kind in allowed_source_kinds:
            continue
        if package.package_kind == aps_package_kind and package.output_package_id == allowed_aps_package_id:
            continue
        unexpected_kinds.add(package.package_kind)
    return sorted(unexpected_kinds)


def canonical_payload_values(
    *,
    values: Any,
    packages: list[L3OutputPackage],
    package_kinds: Iterable[str],
    package_attr: str,
) -> list[str] | None:
    ordered_packages = packages_in_kind_order(packages, package_kinds=package_kinds)
    expected_values = [str(getattr(package, package_attr)) for package in ordered_packages]
    if isinstance(values, list):
        normalized_values = [str(item or "").strip() for item in values]
        if len(normalized_values) == len(ordered_packages) and set(normalized_values) == set(expected_values):
            return expected_values
        return None
    if isinstance(values, dict):
        by_kind = {package.package_kind: str(getattr(package, package_attr)) for package in ordered_packages}
        by_id = {package.output_package_id: str(getattr(package, package_attr)) for package in ordered_packages}
        normalized = {str(key or "").strip(): str(value or "").strip() for key, value in values.items()}
        if normalized == by_kind:
            return expected_values
        if normalized == by_id:
            return expected_values
    return None
