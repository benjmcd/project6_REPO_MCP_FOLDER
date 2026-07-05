from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


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


def test_sec_xbrl_arelle_helper_builds_single_document_load_uri(tmp_path: Path) -> None:
    module = _helper_module()
    entry = tmp_path / "filing.htm"

    assert module._entry_document_load_uri([entry], ixds_surrogate="IXDS", ixds_doc_separator="|") == str(entry)


def test_sec_xbrl_arelle_helper_builds_inline_document_set_load_uri(tmp_path: Path) -> None:
    module = _helper_module()
    first = tmp_path / "primary.htm"
    second = tmp_path / "financials.htm"

    assert module._entry_document_load_uri([first, second], ixds_surrogate="IXDS", ixds_doc_separator="|") == (
        os.path.join(str(tmp_path), "IXDS") + f"{first}|{second}"
    )


def test_sec_xbrl_arelle_helper_reports_unresolved_semantic_references() -> None:
    module = _helper_module()
    diagnostics = module._diagnostics(
        model_error_count=0,
        facts=[
            _fact(context_id="ctx-1", period_resolved=False, unit_id="", unit_resolved=False),
            _fact(context_id="", period_resolved=False, unit_id="usd", unit_resolved=False),
            _fact(context_id="ctx-2", period_resolved=True, unit_id="shares", unit_resolved=True),
        ],
    )

    assert diagnostics["period_unresolved_count"] == 2
    assert diagnostics["period_unresolved_with_context_ref_count"] == 1
    assert diagnostics["unit_unresolved_count"] == 2
    assert diagnostics["unit_unresolved_with_unit_ref_count"] == 1


def test_sec_xbrl_arelle_helper_fails_closed_when_sec_transform_plugin_cannot_load(tmp_path: Path) -> None:
    module = _helper_module()
    cntlr = _FakeCntlr()
    plugin_path = tmp_path / "missing-sec-transforms"

    with pytest.raises(RuntimeError, match="sec_transform_plugin_load_failed"):
        module._load_sec_transform_plugin(cntlr, _FakePluginManager(plugin_info=None), plugin_path=plugin_path)


def test_sec_xbrl_arelle_helper_loads_sec_transform_plugin_before_model_load(tmp_path: Path) -> None:
    module = _helper_module()
    plugin_path = tmp_path / "arelle_sec_transforms"
    plugin_path.mkdir()
    (plugin_path / "__init__.py").write_text("", encoding="utf-8")
    cntlr = _FakeCntlr()
    plugin_manager = _FakePluginManager(
        plugin_info={
            "name": "SEC Inline Transforms",
            "classMethods": ["ModelManager.LoadCustomTransforms"],
        }
    )

    module._load_sec_transform_plugin(cntlr, plugin_manager, plugin_path=plugin_path)

    assert plugin_manager.init_load_plugin_config is False
    assert plugin_manager.added_module == str(plugin_path.resolve())
    assert cntlr.modelManager.custom_transforms_loaded is True


def test_sec_xbrl_arelle_helper_reports_bounded_model_error_codes_without_messages() -> None:
    module = _helper_module()
    codes = ["ix11.11.1.2:invalidTransformation", "IOerror", "IOerror", "x" * 90]

    diagnostics = module._diagnostics(model_error_count=4, model_error_codes=codes, facts=[])

    assert diagnostics["model_error_codes"] == ["ix11.11.1.2:invalidTransformation", "IOerror"]
    assert diagnostics["model_error_code_count"] == 2
    assert "invalidTransformation namespace" not in json.dumps(diagnostics)


def test_sec_xbrl_arelle_helper_resolves_sec_inline_transforms_offline(tmp_path: Path) -> None:
    if not _arelle_pinned():
        pytest.skip("requires pinned Arelle helper runtime")
    schema_path = tmp_path / "sec-transform-test.xsd"
    filing_path = tmp_path / "sec-transform-test.htm"
    schema_path.write_text(_SEC_TRANSFORM_SCHEMA, encoding="utf-8")
    filing_path.write_text(_SEC_TRANSFORM_INLINE_DOCUMENT.format(schema_path=schema_path.name), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(HELPER_PATH),
            "--input",
            str(filing_path),
            "--internet-connectivity",
            "offline",
            "--max-facts",
            "100000",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads(result.stdout.strip().splitlines()[-1])
    diagnostics = report["diagnostics"]
    facts = {fact["concept"]["qname"]: fact for fact in report["facts"]}

    assert diagnostics["model_error_count"] == 0
    assert diagnostics["model_error_codes"] == []
    assert report["fact_count"] == 3
    assert facts["tsec:BallotBoxFlag"]["effective_value"] == "true"
    assert facts["tsec:StateCode"]["effective_value"] == "CA"
    assert facts["tsec:ReportingDuration"]["effective_value"] == "P1Y"


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


class _FakeCntlr:
    def __init__(self) -> None:
        self.modelManager = _FakeModelManager()


class _FakeModelManager:
    def __init__(self) -> None:
        self.custom_transforms_loaded = False

    def loadCustomTransforms(self) -> None:
        self.custom_transforms_loaded = True


class _FakePluginManager:
    def __init__(self, *, plugin_info) -> None:
        self.plugin_info = plugin_info
        self.init_load_plugin_config = None
        self.added_module = None

    def init(self, _cntlr, *, loadPluginConfig: bool) -> None:
        self.init_load_plugin_config = loadPluginConfig

    def addPluginModule(self, path: str):
        self.added_module = path
        return self.plugin_info


def _arelle_pinned() -> bool:
    try:
        import importlib.metadata as metadata

        return metadata.version("arelle-release") == "2.41.3"
    except Exception:
        return False


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fact(*, context_id: str, period_resolved: bool, unit_id: str, unit_resolved: bool) -> dict:
    return {
        "context_id": context_id,
        "unit_id": unit_id,
        "concept": {"resolved_from_dts": True},
        "period": {"resolved": period_resolved},
        "unit": {"resolved": unit_resolved},
        "dimensions": {"typed": [], "explicit": []},
        "hidden": False,
        "continued": False,
    }


_SEC_TRANSFORM_SCHEMA = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xbrli="http://www.xbrl.org/2003/instance"
           xmlns:tsec="http://example.com/sec-transform-test"
           targetNamespace="http://example.com/sec-transform-test"
           elementFormDefault="qualified">
  <xs:import namespace="http://www.xbrl.org/2003/instance"
             schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>
  <xs:element name="BallotBoxFlag" id="tsec_BallotBoxFlag" type="xbrli:booleanItemType"
              substitutionGroup="xbrli:item" xbrli:periodType="duration"/>
  <xs:element name="StateCode" id="tsec_StateCode" type="xbrli:normalizedStringItemType"
              substitutionGroup="xbrli:item" xbrli:periodType="duration"/>
  <xs:element name="ReportingDuration" id="tsec_ReportingDuration" type="xbrli:durationItemType"
              substitutionGroup="xbrli:item" xbrli:periodType="duration"/>
</xs:schema>
"""


_SEC_TRANSFORM_INLINE_DOCUMENT = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
      xmlns:xbrli="http://www.xbrl.org/2003/instance"
      xmlns:link="http://www.xbrl.org/2003/linkbase"
      xmlns:xlink="http://www.w3.org/1999/xlink"
      xmlns:tsec="http://example.com/sec-transform-test"
      xmlns:ixt-sec="http://www.sec.gov/inlineXBRL/transformation/2015-08-31">
<head><title>SEC transform synthetic fixture</title></head>
<body>
<div style="display:none">
<ix:header>
  <ix:references>
    <link:schemaRef xlink:type="simple" xlink:href="{schema_path}"/>
  </ix:references>
  <ix:resources>
    <xbrli:context id="c1">
      <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000000000</xbrli:identifier></xbrli:entity>
      <xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate><xbrli:endDate>2026-12-31</xbrli:endDate></xbrli:period>
    </xbrli:context>
  </ix:resources>
</ix:header>
</div>
<p>Ballot: <ix:nonNumeric name="tsec:BallotBoxFlag" contextRef="c1" format="ixt-sec:boolballotbox">&#x2611;</ix:nonNumeric></p>
<p>State: <ix:nonNumeric name="tsec:StateCode" contextRef="c1" format="ixt-sec:stateprovnameen">California</ix:nonNumeric></p>
<p>Duration: <ix:nonNumeric name="tsec:ReportingDuration" contextRef="c1" format="ixt-sec:duryear">1</ix:nonNumeric></p>
</body>
</html>
"""
