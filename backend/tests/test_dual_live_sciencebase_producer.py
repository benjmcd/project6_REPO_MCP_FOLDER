from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, replace as dataclass_replace
from pathlib import Path

import pytest

from app.services.connector_egress_contract import ContractHold, RequestLimits
from app.services.dual_live_sciencebase_producer import (
    SCIENCEBASE_RESPONSE_CAP_BYTES,
    ProducerHold,
    ScienceBaseInput,
    ScienceBaseProducer,
)


SEARCH_URL = "https://www.sciencebase.gov/catalog/items?q=critical%20minerals&format=json"
ITEM_URL = "https://www.sciencebase.gov/catalog/item/item-7?format=json"
FILE_URL = "https://www.sciencebase.gov/catalog/file/get/item-7?f=target.csv"
REDIRECT_URL = "https://sciencebase.gov/catalog/file/get/item-7?f=target.csv"


@dataclass(frozen=True)
class StubEffectResult:
    reservation_event_id: str
    plan_digest: str
    status_code: int
    body: bytes
    response_header_names: tuple[str, ...]
    redirect_location: str | None


class FakeEffectPort:
    def __init__(self, results: list[StubEffectResult]) -> None:
        self.results = list(results)
        self.plans = []

    def execute(self, plan):
        self.plans.append(plan)
        if not self.results:
            raise AssertionError("unexpected physical request")
        return dataclass_replace(self.results.pop(0), plan_digest=plan.plan_digest)


def effect(
    status: int,
    body: bytes = b"",
    *,
    redirect: str | None = None,
    header_names: tuple[str, ...] = (),
) -> StubEffectResult:
    return StubEffectResult(
        reservation_event_id=f"event-{status}-{len(body)}",
        plan_digest="a" * 64,
        status_code=status,
        body=body,
        response_header_names=header_names,
        redirect_location=redirect,
    )


def request(
    *,
    limits: RequestLimits | None = None,
    max_total_bytes: int = 4096,
    max_redirect_hops: int = 1,
) -> ScienceBaseInput:
    return ScienceBaseInput(
        query="critical minerals",
        expected_item_id="item-7",
        expected_file_name="target.csv",
        envelope_digest="sha256:" + "e" * 64,
        campaign_id="campaign-1",
        canonical_root=str(Path.cwd().resolve()),
        connector_run_id="11111111-1111-4111-8111-111111111111",
        authorization_digest="sha256:" + "b" * 64,
        grant_digest="sha256:" + "c" * 64,
        max_total_bytes=max_total_bytes,
        limits=limits or RequestLimits(timeout_seconds=10.0),
        max_redirect_hops=max_redirect_hops,
        connector_run_target_id="target-1",
    )


def json_bytes(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def happy_results(*, file_entry: dict[str, object] | None = None) -> list[StubEffectResult]:
    entry = file_entry or {"name": "target.csv", "downloadUri": FILE_URL, "url": FILE_URL}
    return [
        effect(200, json_bytes({"items": [{"id": "item-7"}]}), header_names=("content-type",)),
        effect(200, json_bytes({"id": "item-7", "files": [entry]}), header_names=("content-type",)),
        effect(200, b"a,b\n1,2\n", header_names=("content-type",)),
    ]


def test_acquires_exact_file_only_through_effect_port() -> None:
    port = FakeEffectPort(happy_results())

    output = ScienceBaseProducer(port).acquire_exact_file(request())

    assert output.item_id == "item-7"
    assert output.file_name == "target.csv"
    assert output.content == b"a,b\n1,2\n"
    assert output.sha256 == hashlib.sha256(output.content).hexdigest()
    assert output.request_count == 3
    assert output.total_response_bytes == sum(len(result.body) for result in happy_results())
    assert "sha256:" + "b" * 64 not in repr(output)
    assert "sha256:" + "c" * 64 not in repr(output)
    assert [plan.request_ordinal for plan in port.plans] == [1, 2, 3]
    assert [plan.stage for plan in port.plans] == ["sciencebase_search", "sciencebase_hydrate", "sciencebase_download"]
    assert [plan.canonical_destination for plan in port.plans] == [SEARCH_URL, ITEM_URL, FILE_URL]
    assert all(plan.method == "GET" for plan in port.plans)
    assert all(plan.header_names == plan.header_value_sha256s == () for plan in port.plans)
    assert all(
        plan.authorization_digest == "sha256:" + "b" * 64
        and plan.grant_digest == "sha256:" + "c" * 64
        for plan in port.plans
    )


@pytest.mark.parametrize(
    ("search_items", "code"),
    [([], "sciencebase_exact_item_not_unique"), ([{"id": "item-7"}, {"id": "item-7"}], "sciencebase_exact_item_not_unique")],
)
def test_search_requires_one_exact_item(search_items: list[dict[str, str]], code: str) -> None:
    port = FakeEffectPort([effect(200, json_bytes({"items": search_items}))])

    with pytest.raises(ProducerHold, match=f"^{code}$"):
        ScienceBaseProducer(port).acquire_exact_file(request())

    assert len(port.plans) == 1


@pytest.mark.parametrize(
    "file_entry",
    [
        {"name": "target.csv", "url": FILE_URL},
        {"name": "target.csv", "downloadUri": FILE_URL, "url": "https://example.test/wrong"},
    ],
)
def test_download_uri_is_required_and_conflicting_alias_holds(file_entry: dict[str, object]) -> None:
    port = FakeEffectPort(happy_results(file_entry=file_entry)[:2])

    with pytest.raises(ProducerHold, match="^sciencebase_exact_file_locator_invalid$"):
        ScienceBaseProducer(port).acquire_exact_file(request())

    assert len(port.plans) == 2


def test_redirect_is_a_new_reserved_physical_request() -> None:
    results = happy_results()
    results[2:] = [effect(302, redirect=REDIRECT_URL, header_names=("location",)), effect(200, b"x,y\n3,4\n")]
    port = FakeEffectPort(results)

    output = ScienceBaseProducer(port).acquire_exact_file(request())

    assert output.request_count == 4
    assert [plan.request_ordinal for plan in port.plans] == [1, 2, 3, 4]
    assert port.plans[3].stage == "sciencebase_download_redirect"
    assert port.plans[3].canonical_destination == REDIRECT_URL


def test_redirect_over_ceiling_holds_without_another_effect() -> None:
    limits = RequestLimits(timeout_seconds=10.0, max_redirects=0)
    results = happy_results()
    results[2] = effect(302, redirect=REDIRECT_URL, header_names=("location",))
    port = FakeEffectPort(results)

    with pytest.raises(ProducerHold, match="^sciencebase_redirect_limit_exceeded$"):
        ScienceBaseProducer(port).acquire_exact_file(request(limits=limits, max_redirect_hops=0))

    assert len(port.plans) == 3


def test_response_and_cumulative_bounds_fail_closed() -> None:
    tiny = RequestLimits(timeout_seconds=10.0, max_response_bytes=8, max_redirects=0)
    over_response = FakeEffectPort([effect(200, b"123456789")])
    with pytest.raises(ProducerHold, match="^sciencebase_response_limit_exceeded$"):
        ScienceBaseProducer(over_response).acquire_exact_file(request(limits=tiny))

    search = effect(200, json_bytes({"items": [{"id": "item-7"}]}))
    over_total = FakeEffectPort([search])
    with pytest.raises(ProducerHold, match="^sciencebase_run_limit_exceeded$"):
        ScienceBaseProducer(over_total).acquire_exact_file(request(max_total_bytes=len(search.body) - 1))


def test_response_cap_is_exactly_64_mib_and_cannot_be_increased() -> None:
    assert SCIENCEBASE_RESPONSE_CAP_BYTES == 64 * 1024 * 1024
    with pytest.raises(ContractHold, match="^request_limits_invalid:max_response_bytes$"):
        RequestLimits(timeout_seconds=10.0, max_response_bytes=SCIENCEBASE_RESPONSE_CAP_BYTES + 1)


def test_effect_failure_is_redacted_at_producer_boundary() -> None:
    sentinel = "never-emit-secret-value"

    class FailingPort:
        def execute(self, plan):
            raise RuntimeError(sentinel)

    with pytest.raises(ProducerHold, match="^sciencebase_effect_hold$") as caught:
        ScienceBaseProducer(FailingPort()).acquire_exact_file(request())
    assert sentinel not in str(caught.value)


def _forbidden_effect_surface(source: str) -> set[str]:
    tree = ast.parse(source)
    forbidden_roots = {"requests", "socket", "ssl", "http", "urllib", "subprocess", "ctypes", "importlib"}
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attributes = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }
    return (
        imports.intersection(forbidden_roots)
        | calls.intersection({"eval", "exec", "compile", "__import__", "getattr", "setattr", "delattr", "import_module"})
        | attributes.intersection({"system", "popen", "connect", "connect_ex", "send", "sendto", "wrap_socket"})
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from requests import get\nget('https://example.test')", "requests"),
        ("import subprocess\nsubprocess.run([])", "subprocess"),
        ("from ctypes import CDLL\nCDLL('network.dll')", "ctypes"),
        ("from importlib import import_module as loader\nloader('socket')", "importlib"),
    ],
)
def test_ast_guard_rejects_import_mutations(source: str, expected: str) -> None:
    assert expected in _forbidden_effect_surface(source)


def test_producer_source_has_no_ambient_effect_or_dynamic_escape_surface() -> None:
    source_path = Path(__file__).parents[1] / "app" / "services" / "dual_live_sciencebase_producer.py"
    assert not _forbidden_effect_surface(source_path.read_text(encoding="utf-8"))
