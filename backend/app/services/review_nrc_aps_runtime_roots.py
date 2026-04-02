from __future__ import annotations

from pathlib import Path


def _normalize_runtime_root(candidate: str | Path | None) -> Path | None:
    raw = str(candidate or "").strip()
    if not raw:
        return None

    root = Path(raw)
    if not root.is_absolute():
        root = root.resolve()

    if root.name in {"storage", "storage_test_runtime"}:
        root = root / "lc_e2e"

    try:
        return root.resolve()
    except OSError:
        return None


def candidate_review_runtime_roots(
    *,
    app_root: Path,
    backend_root: Path,
    storage_dir: str | Path | None = None,
) -> list[Path]:
    roots = [
        app_root / "storage_test_runtime" / "lc_e2e",
        backend_root / "storage_test_runtime" / "lc_e2e",
    ]

    configured_root = _normalize_runtime_root(storage_dir)
    if configured_root is not None:
        roots.append(configured_root)

    deduped: dict[str, Path] = {}
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        deduped[str(resolved)] = resolved
    return list(deduped.values())
