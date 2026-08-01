from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import pytest

from app.services import dual_live_dependencies as dependencies


@dataclass(frozen=True, slots=True)
class _RecordPath:
    value: str
    hash: dependencies._RecordHash | None

    @property
    def suffix(self) -> str:
        return Path(self.value).suffix

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class _Distribution:
    name: str
    version: str
    root: Path
    files: tuple[_RecordPath, ...]

    @property
    def metadata(self) -> dict[str, str]:
        return {"Name": self.name}

    def locate_file(self, path: object) -> Path:
        return self.root / str(path)


def _record_hash(content: bytes) -> dependencies._RecordHash:
    value = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=")
    return SimpleNamespace(mode="sha256", value=value.decode("ascii"))


def _exact_stack(tmp_path: Path) -> dict[str, list[_Distribution]]:
    result: dict[str, list[_Distribution]] = {}
    root = tmp_path / "site-packages"
    root.mkdir()
    for name, version in dependencies._EXPECTED_DEPENDENCY_VERSIONS.items():
        import_root = dependencies._DEPENDENCY_IMPORT_ROOTS[name]
        relative = f"{import_root}/__init__.py"
        content = f"__version__ = {version!r}\n".encode("utf-8")
        path = root / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(content)
        result[name] = [
            _Distribution(
                name=name,
                version=version,
                root=root,
                files=(_RecordPath(relative, _record_hash(content)),),
            )
        ]
    return result


def _provider(
    stack: dict[str, list[_Distribution]],
) -> Callable[[str], tuple[_Distribution, ...]]:
    return lambda name: tuple(stack.get(name, ()))


def _verify(
    stack: dict[str, list[_Distribution]],
    *,
    lock_path: Path | None = None,
    approved_root: Path | None = None,
) -> str:
    distribution_root = next(iter(stack.values()))[0].root
    return dependencies._verify_dependency_set(
        lock_path=dependencies._LOCK_PATH if lock_path is None else lock_path,
        distribution_provider=_provider(stack),
        approved_distribution_roots=(
            distribution_root if approved_root is None else approved_root,
        ),
        python_version=(3, 12),
        dont_write_bytecode=True,
        pycache_prefix="NUL",
    )


def test_exact_locked_dependency_set_returns_stable_content_digest(
    tmp_path: Path,
) -> None:
    stack = _exact_stack(tmp_path)

    first = _verify(stack)
    second = _verify(stack)

    assert len(first) == 64
    assert first == second
    assert first == first.lower()


@pytest.mark.parametrize("mode", ("missing", "multiple", "version-mismatch"))
def test_dependency_set_refuses_missing_multiple_or_stale_distribution(
    tmp_path: Path,
    mode: str,
) -> None:
    stack = _exact_stack(tmp_path)
    name = "requests"
    if mode == "missing":
        stack[name] = []
    elif mode == "multiple":
        stack[name].append(stack[name][0])
    else:
        stack[name] = [
            _Distribution(
                name=name,
                version="0.0.0",
                root=stack[name][0].root,
                files=stack[name][0].files,
            )
        ]

    with pytest.raises(dependencies.DualLiveDependencyError) as exc:
        _verify(stack)

    assert exc.value.code == "dual_live_dependency_provenance_invalid"


def test_dependency_set_refuses_tampered_installed_source(
    tmp_path: Path,
) -> None:
    stack = _exact_stack(tmp_path)
    distribution = stack["requests"][0]
    distribution.locate_file(distribution.files[0]).write_bytes(b"tampered\n")

    with pytest.raises(dependencies.DualLiveDependencyError) as exc:
        _verify(stack)

    assert exc.value.code == "dual_live_dependency_provenance_invalid"


def test_dependency_set_refuses_unrecorded_importable_source(
    tmp_path: Path,
) -> None:
    stack = _exact_stack(tmp_path)
    distribution = stack["requests"][0]
    injected = distribution.root / "requests" / "injected.py"
    injected.write_text("raise RuntimeError\n", encoding="utf-8")

    with pytest.raises(dependencies.DualLiveDependencyError) as exc:
        _verify(stack)

    assert exc.value.code == "dual_live_dependency_provenance_invalid"


def test_dependency_set_refuses_distribution_outside_runtime_site_packages(
    tmp_path: Path,
) -> None:
    stack = _exact_stack(tmp_path)
    unrelated_root = tmp_path / "other-site-packages"
    unrelated_root.mkdir()

    with pytest.raises(dependencies.DualLiveDependencyError) as exc:
        _verify(stack, approved_root=unrelated_root)

    assert exc.value.code == "dual_live_dependency_provenance_invalid"


def test_bytes_and_record_rewrite_is_explicit_trusted_install_nonclaim(
    tmp_path: Path,
) -> None:
    stack = _exact_stack(tmp_path)
    original_digest = _verify(stack)
    original = stack["requests"][0]
    content = b"owning-account-rewrite\n"
    original.locate_file(original.files[0]).write_bytes(content)
    stack["requests"] = [
        _Distribution(
            name=original.name,
            version=original.version,
            root=original.root,
            files=(
                _RecordPath(original.files[0].value, _record_hash(content)),
            ),
        )
    ]

    rewritten_digest = _verify(stack)

    assert rewritten_digest != original_digest
    assert dependencies.DEPENDENCY_PROVENANCE_NONCLAIM == (
        "same-version package bytes and RECORD rewritten by the owning account "
        "are not independently authenticated"
    )


def test_dependency_set_refuses_changed_canonical_lock(
    tmp_path: Path,
) -> None:
    stack = _exact_stack(tmp_path)
    changed_lock = tmp_path / "requirements.lock.txt"
    changed_lock.write_bytes(dependencies._LOCK_PATH.read_bytes() + b"\n")

    with pytest.raises(dependencies.DualLiveDependencyError) as exc:
        _verify(stack, lock_path=changed_lock)

    assert exc.value.code == "dual_live_dependency_provenance_invalid"


@pytest.mark.parametrize(
    ("python_version", "dont_write_bytecode", "pycache_prefix"),
    (
        ((3, 11), True, "NUL"),
        ((3, 12), False, "NUL"),
        ((3, 12), True, None),
    ),
)
def test_dependency_set_requires_exact_isolated_runtime_posture(
    tmp_path: Path,
    python_version: tuple[int, int],
    dont_write_bytecode: bool,
    pycache_prefix: str | None,
) -> None:
    stack = _exact_stack(tmp_path)

    with pytest.raises(dependencies.DualLiveDependencyError) as exc:
        dependencies._verify_dependency_set(
            lock_path=dependencies._LOCK_PATH,
            distribution_provider=_provider(stack),
            approved_distribution_roots=(
                next(iter(stack.values()))[0].root,
            ),
            python_version=python_version,
            dont_write_bytecode=dont_write_bytecode,
            pycache_prefix=pycache_prefix,
        )

    assert exc.value.code == "dual_live_dependency_provenance_invalid"
