from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "tools" / "sec-xbrl-arelle.py"


def _helper_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_arelle_helper", HELPER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_arelle_helper_skips_invalid_taxonomy_zips_when_valid_packages_exist(tmp_path: Path) -> None:
    module = _helper_module()
    valid = tmp_path / "valid.zip"
    invalid = tmp_path / "invalid.zip"
    valid.write_bytes(b"valid-taxonomy")
    invalid.write_bytes(b"invalid-taxonomy")
    missing = tmp_path / "missing.zip"
    manager = _FakePackageManager(valid_name=valid.name)

    status = module._load_packages(object(), manager, [str(invalid), str(missing), str(valid)])

    assert status["loaded_hashes"] == [_sha256_bytes(b"valid-taxonomy")]
    assert status["invalid_hashes"] == [
        _sha256_bytes(b"invalid-taxonomy"),
        _sha256_text(str(missing)),
    ]
    assert manager.rebuilt is True


def test_sec_xbrl_arelle_helper_fails_closed_when_no_valid_taxonomy_package_exists(tmp_path: Path) -> None:
    module = _helper_module()
    invalid = tmp_path / "invalid.zip"
    invalid.write_bytes(b"invalid-taxonomy")

    try:
        module._load_packages(object(), _FakePackageManager(valid_name="none.zip"), [str(invalid)])
    except RuntimeError as exc:
        assert str(exc) == "taxonomy_package_valid_package_missing"
    else:
        raise AssertionError("expected taxonomy package load to fail closed")


class _FakePackageManager:
    def __init__(self, *, valid_name: str) -> None:
        self.valid_name = valid_name
        self.rebuilt = False

    def init(self, _cntlr, *, loadPackagesConfig: bool) -> None:
        assert loadPackagesConfig is False

    def addPackage(self, _cntlr, path: str):
        return {"name": "valid"} if Path(path).name == self.valid_name else None

    def rebuildRemappings(self, _cntlr) -> None:
        self.rebuilt = True


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
