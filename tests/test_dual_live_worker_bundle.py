from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
import traceback

import pytest


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")


class MemoryProbe:
    def __init__(self, root: Path, manifest: bytes, files: dict[str, bytes], security: object) -> None:
        self.root = root
        self.manifest = manifest
        self.files = files
        self.security = security
        self.ancestor_security = security
        self.volume_id = "vol-7"
        self.fixed = True
        self.local = True
        self.identity_overrides: dict[str, object] = {}
        self.inventory_override: tuple[str, ...] | None = None
        self.runtime_override: object | None = None
        self.stream_overrides: dict[str, tuple[str, ...]] = {}

    def canonicalize(self, path: Path) -> Path:
        return path

    def volume(self, path: Path) -> object:
        from app.services.dual_live_worker_bundle import VolumeIdentity

        return VolumeIdentity(self.volume_id, fixed=self.fixed, local=self.local)

    def identity(self, path: Path) -> object:
        from app.services.dual_live_worker_bundle import FileIdentity

        try:
            relative = "." if path == self.root else path.relative_to(self.root).as_posix()
            directory = relative == "." or relative.endswith("/")
        except ValueError:
            relative, directory = "@" + path.as_posix(), True
        return self.identity_overrides.get(relative, FileIdentity(self.volume_id, f"id:{relative}", 1, False, directory))

    def inventory(self, root: Path, max_entries: int) -> tuple[str, ...]:
        assert max_entries > 0
        return self.inventory_override or tuple(sorted(("worker-bundle.json", *self.files)))

    def read_bytes(self, path: Path, max_bytes: int) -> bytes:
        relative = path.relative_to(self.root).as_posix()
        value = self.manifest if relative == "worker-bundle.json" else self.files[relative]
        if len(value) > max_bytes:
            raise ValueError("bounded read exceeded")
        return value

    def security_descriptor(self, path: Path) -> object:
        try:
            path.relative_to(self.root)
        except ValueError:
            return self.ancestor_security
        return self.security

    def runtime_context(self, profile_moniker: str) -> object:
        assert profile_moniker
        assert self.runtime_override is not None
        return self.runtime_override

    def streams(self, path: Path, max_streams: int) -> tuple[str, ...]:
        try:
            relative = "." if path == self.root else path.relative_to(self.root).as_posix()
        except ValueError:
            relative = "@" + path.as_posix()
        value = self.stream_overrides.get(relative, () if relative.startswith("@") else ("::$DATA",))
        assert len(value) <= max_streams
        return value


def _valid_case() -> tuple[object, MemoryProbe]:
    from app.services.dual_live_worker_bundle import (
        AccessEntry,
        BundleBinding,
        RuntimeContext,
        SecurityDescriptor,
    )

    files = {"python.exe": b"python", "worker.py": b"worker"}
    principals = {
        "package": "S-1-15-2-42",
        "owner": "S-1-5-21-owner",
        "provisioner": "S-1-5-21-provisioner",
        "broker": "S-1-5-21-broker",
    }
    control = frozenset({"read", "execute", "traverse", "write", "create", "delete", "rename", "owner", "dacl"})
    rx = frozenset({"read", "execute", "traverse"})
    entries = (
        AccessEntry("S-1-5-18", control, access_mask=0x001F01FF),
        AccessEntry("S-1-5-32-544", control, access_mask=0x001F01FF),
        AccessEntry(principals["owner"], control, access_mask=0x001F01FF),
        AccessEntry(principals["provisioner"], control, access_mask=0x001F01FF),
        AccessEntry(principals["broker"], rx, access_mask=0x001200A9),
        AccessEntry(principals["package"], rx, access_mask=0x001200A9),
    )
    security = SecurityDescriptor(principals["owner"], True, entries, (entries[-2], entries[-1]))
    manifest = {
        "architecture": "amd64",
        "entrypoint": "worker.py",
        "files": [
            {"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
            for name, data in sorted(files.items())
        ],
        "interpreter": "python.exe",
        "principals": principals,
        "profile_moniker": "Project6.B0.ZeroCapability.v1",
        "python_version": "3.11.9",
        "schema_version": "project6.worker-bundle.v1",
        "source_commit": "a" * 40,
    }
    raw = _canonical(manifest)
    manifest_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    root = Path("C:/ProgramData/Project6/Bundles") / manifest_digest.replace(":", "-")
    binding = BundleBinding(
        root=root,
        provisioning_root=root.parent,
        profile_moniker="Project6.B0.ZeroCapability.v1",
        manifest_digest=manifest_digest,
        source_commit="a" * 40,
        entrypoint="worker.py",
        interpreter="python.exe",
        python_version="3.11.9",
        architecture="amd64",
        package_sid=principals["package"],
        owner_sid=principals["owner"],
        provisioner_sid=principals["provisioner"],
        broker_sid=principals["broker"],
        ambient_interpreter_root=Path("C:/Python311"),
        repository_root=Path("C:/repo"),
        campaign_root=Path("C:/campaign"),
        appcontainer_profile_root=Path("C:/profile"),
        broker_profile_root=Path("C:/Users/benny"),
        user_data_root=Path("C:/Users/benny/AppData/Local"),
    )
    probe = MemoryProbe(root, raw, files, security)
    probe.runtime_override = RuntimeContext(
        binding.broker_sid, binding.package_sid, binding.appcontainer_profile_root,
        binding.ambient_interpreter_root, binding.broker_profile_root, binding.user_data_root,
    )
    return binding, probe


def _rewrite_manifest(binding: object, probe: MemoryProbe, edit: object) -> object:
    document = json.loads(probe.manifest)
    edit(document)
    probe.manifest = _canonical(document)
    digest = "sha256:" + hashlib.sha256(probe.manifest).hexdigest()
    root = binding.root.parent / digest.replace(":", "-")
    probe.root = root
    return replace(binding, root=root, manifest_digest=digest)


def test_validates_exact_content_addressed_read_only_bundle() -> None:
    from app.services.dual_live_worker_bundle import validate_worker_bundle

    binding, probe = _valid_case()
    validated = validate_worker_bundle(binding, probe)

    assert validated.interpreter == binding.root / "python.exe"
    assert validated.entrypoint == binding.root / "worker.py"
    assert validated.manifest_digest == binding.manifest_digest


def test_holds_when_root_is_not_bound_to_manifest_digest() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    binding = replace(binding, root=binding.root.parent / "unbound")
    probe.root = binding.root
    with pytest.raises(BundleHold, match="bundle_root_unbound"):
        validate_worker_bundle(binding, probe)


def test_holds_when_bundle_is_under_broker_documents_tree() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    provisioning_root = binding.broker_profile_root / "Documents" / "Bundles"
    root = provisioning_root / binding.manifest_digest.replace(":", "-")
    binding = replace(binding, root=root, provisioning_root=provisioning_root)
    probe.root = root
    with pytest.raises(BundleHold, match="bundle_root_forbidden"):
        validate_worker_bundle(binding, probe)


def test_holds_when_derived_runtime_principals_do_not_match_binding() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    probe.runtime_override = replace(probe.runtime_override, package_sid="S-1-15-2-other")
    with pytest.raises(BundleHold, match="bundle_runtime_principal_mismatch"):
        validate_worker_bundle(binding, probe)


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda b, p: setattr(p, "manifest", p.manifest + b"\n"), "bundle_manifest_digest_mismatch"),
        (lambda b, p: p.files.__setitem__("worker.py", b"drift"), "bundle_file_drift"),
        (lambda b, p: setattr(p, "inventory_override", ("python.exe", "worker-bundle.json")), "bundle_inventory_mismatch"),
        (lambda b, p: setattr(p, "inventory_override", ("extra.dll", "python.exe", "worker-bundle.json", "worker.py")), "bundle_inventory_mismatch"),
        (lambda b, p: setattr(p, "fixed", False), "bundle_volume_invalid"),
    ],
)
def test_holds_on_content_inventory_or_volume_drift(mutate: object, code: str) -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    mutate(binding, probe)
    with pytest.raises(BundleHold, match=code):
        validate_worker_bundle(binding, probe)


@pytest.mark.parametrize(("attribute", "value"), [("source_commit", "b" * 40), ("interpreter", "worker.py")])
def test_holds_on_envelope_binding_drift(attribute: str, value: str) -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    with pytest.raises(BundleHold, match="bundle_binding_mismatch"):
        validate_worker_bundle(replace(binding, **{attribute: value}), probe)


@pytest.mark.parametrize(("attribute", "value"), [("architecture", "mystery"), ("python_version", "3")])
def test_holds_when_envelope_and_manifest_share_invalid_runtime_identity(attribute: str, value: str) -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    binding = replace(binding, **{attribute: value})
    binding = _rewrite_manifest(binding, probe, lambda m: m.__setitem__(attribute, value))
    with pytest.raises(BundleHold, match="bundle_binding_invalid"):
        validate_worker_bundle(binding, probe)


@pytest.mark.parametrize(("relative", "link_count", "reparse"), [("worker.py", 2, False), ("worker.py", 1, True)])
def test_holds_on_hardlink_or_reparse(relative: str, link_count: int, reparse: bool) -> None:
    from app.services.dual_live_worker_bundle import BundleHold, FileIdentity, validate_worker_bundle

    binding, probe = _valid_case()
    probe.identity_overrides[relative] = FileIdentity("vol-7", "changed", link_count, reparse)
    with pytest.raises(BundleHold, match="bundle_file_drift"):
        validate_worker_bundle(binding, probe)


def test_holds_on_alternate_data_stream() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    probe.stream_overrides["worker.py"] = ("::$DATA", ":poison:$DATA")
    with pytest.raises(BundleHold, match="bundle_stream_invalid"):
        validate_worker_bundle(binding, probe)


def test_holds_on_manifest_traversal() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    binding = _rewrite_manifest(binding, probe, lambda m: m["files"][0].__setitem__("path", "../python.exe"))
    with pytest.raises(BundleHold, match="bundle_path_invalid"):
        validate_worker_bundle(binding, probe)


def test_holds_on_noncanonical_file_order() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    binding = _rewrite_manifest(binding, probe, lambda m: m["files"].reverse())
    with pytest.raises(BundleHold, match="bundle_manifest_contract_mismatch"):
        validate_worker_bundle(binding, probe)


def test_holds_when_manifest_size_is_boolean() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    binding = _rewrite_manifest(binding, probe, lambda m: m["files"][0].__setitem__("size", True))
    with pytest.raises(BundleHold, match="bundle_file_record_invalid"):
        validate_worker_bundle(binding, probe)


@pytest.mark.parametrize(("principal", "rights", "inherited"), [("package", frozenset({"read", "execute", "traverse", right}), False) for right in ("write", "create", "delete", "rename", "owner", "dacl")] + [("broker", frozenset({"read", "execute", "traverse"}), True), ("unexpected", frozenset({"read"}), False)])
def test_holds_on_broad_inherited_or_unexpected_acl(principal: str, rights: frozenset[str], inherited: bool) -> None:
    from app.services.dual_live_worker_bundle import AccessEntry, BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    sid = getattr(binding, f"{principal}_sid", "S-1-1-0")
    entries = tuple(entry for entry in probe.security.entries if entry.principal != sid) + (AccessEntry(sid, rights, inherited=inherited),)
    probe.security = replace(probe.security, entries=entries)
    with pytest.raises(BundleHold, match="bundle_dacl_mismatch"):
        validate_worker_bundle(binding, probe)


# Windows canonicalizes explicit-ACE order when a descriptor is written: the
# stored order is ascending SID -- sub-authority count first, then identifier
# authority, then sub-authorities -- regardless of the order the grants were
# issued in.  Measured on Windows 10.0.26100 / PowerShell 5.1 against disposable
# NTFS trees, and identical for a single icacls call in grant order, a single
# call in reversed order, one call per principal, and a pure .NET Set-Acl.  DACL
# order is therefore not a property any provisioner can establish, so the
# validator must not depend on it.
_PRODUCTION_SIDS_BY_ROLE = {
    "system": "S-1-5-18",
    "administrators": "S-1-5-32-544",
    "owner": "S-1-5-19",
    "provisioner": "S-1-5-20",
    "broker": "S-1-15-2-3624051433-2125758914-1423191267-1740899205-1073925389-3782572162-737981194",
    "package": "S-1-15-2-1861897761-1695161497-2927542615-642690995-327840285-2659745135-2630312742",
}
_GRANT_ROLE_ORDER = ("system", "administrators", "owner", "provisioner", "broker", "package")


def _sid_sort_key(sid: str) -> tuple[int, int, tuple[int, ...]]:
    """The ordering Windows imposes on explicit ACEs, as measured."""

    _, _, identifier_authority, *sub_authorities = sid.split("-")
    return (
        len(sub_authorities),
        int(identifier_authority),
        tuple(int(part) for part in sub_authorities),
    )


_CANONICAL_ROLE_ORDER = tuple(
    sorted(_GRANT_ROLE_ORDER, key=lambda role: _sid_sort_key(_PRODUCTION_SIDS_BY_ROLE[role]))
)


def test_canonical_windows_dacl_order_differs_from_the_grant_order() -> None:
    """Pins the measured ordering law, and that it is not the grant order.

    If these two ever coincided the acceptance test below would prove nothing.
    """

    assert _CANONICAL_ROLE_ORDER == (
        "system", "owner", "provisioner", "administrators", "package", "broker",
    )
    assert _CANONICAL_ROLE_ORDER != _GRANT_ROLE_ORDER


def test_validates_bundle_whose_dacl_is_in_canonical_windows_order() -> None:
    """A correctly provisioned bundle validates in the order Windows stores.

    The six ACEs are exactly the contract's -- same principals, masks, types,
    inheritance and propagation -- and only their DACL positions differ, which
    is the only arrangement a real provisioned bundle can ever present.
    """

    from app.services.dual_live_worker_bundle import validate_worker_bundle

    binding, probe = _valid_case()
    role_to_sid = {
        "system": "S-1-5-18",
        "administrators": "S-1-5-32-544",
        "owner": binding.owner_sid,
        "provisioner": binding.provisioner_sid,
        "broker": binding.broker_sid,
        "package": binding.package_sid,
    }
    by_principal = {entry.principal: entry for entry in probe.security.entries}
    reordered = tuple(by_principal[role_to_sid[role]] for role in _CANONICAL_ROLE_ORDER)
    assert set(reordered) == set(probe.security.entries), "reordering must not change content"
    assert reordered != probe.security.entries, "reordering must actually reorder"
    probe.security = replace(probe.security, entries=reordered)

    validated = validate_worker_bundle(binding, probe)

    assert validated.root == binding.root
    assert validated.manifest_digest == binding.manifest_digest


def test_holds_when_actual_broker_token_can_mutate_bundle() -> None:
    from app.services.dual_live_worker_bundle import AccessEntry, BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    control = frozenset({"read", "execute", "traverse", "write", "create", "delete", "rename", "owner", "dacl"})
    broker = AccessEntry(binding.broker_sid, control, access_mask=0x001F01FF)
    probe.security = replace(probe.security, effective_entries=(broker, probe.security.effective_entries[1]))
    with pytest.raises(BundleHold, match="bundle_dacl_mismatch"):
        validate_worker_bundle(binding, probe)


def test_holds_when_actual_broker_token_can_mutate_ancestor() -> None:
    from app.services.dual_live_worker_bundle import AccessEntry, BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    control = frozenset({"read", "execute", "traverse", "write", "create", "delete", "rename", "owner", "dacl"})
    broker = AccessEntry(binding.broker_sid, control, access_mask=0x001F01FF)
    probe.ancestor_security = replace(probe.security, effective_entries=(broker, probe.security.effective_entries[1]))
    with pytest.raises(BundleHold, match="bundle_ancestor_invalid"):
        validate_worker_bundle(binding, probe)


def test_suspended_rebind_holds_on_file_identity_drift() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, FileIdentity, revalidate_worker_bundle, validate_worker_bundle

    binding, probe = _valid_case()
    expected = validate_worker_bundle(binding, probe)
    probe.identity_overrides["worker.py"] = FileIdentity("vol-7", "id:replacement", 1, False)
    with pytest.raises(BundleHold, match="bundle_rebind_drift"):
        revalidate_worker_bundle(binding, probe, expected)


def test_windows_probe_preserves_exact_acl_masks() -> None:
    from app.services.dual_live_worker_bundle import _access_entry

    entry = _access_entry("S-1-15-2-42", 0x001200A9, True, 0)

    assert entry.access_mask == 0x001200A9
    assert entry.rights == frozenset({"read", "execute", "traverse"})


def test_windows_runtime_observation_holds_with_fixed_secret_free_phase() -> None:
    from types import SimpleNamespace
    from app.services.dual_live_worker_bundle import BundleHold, WindowsBundleProbe

    probe = object.__new__(WindowsBundleProbe)
    probe._kernel = SimpleNamespace(GetCurrentProcess=lambda: 1, CloseHandle=lambda handle: None)
    probe._advapi = SimpleNamespace(OpenProcessToken=lambda process, access, token: False)

    with pytest.raises(BundleHold, match="^bundle_runtime_ambiguous_token$") as caught:
        probe.runtime_context("Project6.B0.CI.test")
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


def test_hold_suppresses_sensitive_observation_exception() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    probe.read_bytes = lambda path, limit: (_ for _ in ()).throw(RuntimeError("C:/sentinel-secret"))

    with pytest.raises(BundleHold) as caught:
        validate_worker_bundle(binding, probe)

    rendered = "".join(traceback.format_exception(caught.value))
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert str(caught.value) == "bundle_observation_ambiguous_manifest"
    assert "sentinel-secret" not in rendered


def test_hold_identifies_only_the_ambiguous_canonicalization_category() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    original = probe.canonicalize
    probe.canonicalize = lambda path: (_ for _ in ()).throw(RuntimeError("sentinel")) if path == binding.repository_root else original(path)

    with pytest.raises(BundleHold, match="^bundle_observation_ambiguous_canonicalize_repository$"):
        validate_worker_bundle(binding, probe)


def test_hold_suppresses_malformed_manifest_bytes() -> None:
    from app.services.dual_live_worker_bundle import BundleHold, validate_worker_bundle

    binding, probe = _valid_case()
    probe.manifest = b"\xffsentinel-malformed"
    digest = "sha256:" + hashlib.sha256(probe.manifest).hexdigest()
    root = binding.root.parent / digest.replace(":", "-")
    binding, probe.root = replace(binding, root=root, manifest_digest=digest), root
    with pytest.raises(BundleHold) as caught:
        validate_worker_bundle(binding, probe)
    rendered = "".join(traceback.format_exception(caught.value))
    assert caught.value.__cause__ is None and caught.value.__suppress_context__
    assert "sentinel-malformed" not in rendered


@pytest.mark.skipif(os.name != "nt", reason="Win32 probe")
def test_windows_probe_validates_preprovisioned_fixture() -> None:
    from app.services.dual_live_worker_bundle import (
        BundleBinding,
        WindowsBundleProbe,
        validate_worker_bundle,
    )

    binding_file = os.environ.get("PROJECT6_B0_BUNDLE_BINDING")
    if not binding_file:
        pytest.skip("externally pre-provisioned PROJECT6_B0_BUNDLE_BINDING required")
    document = json.loads(Path(binding_file).resolve(strict=True).read_text(encoding="utf-8"))
    path_fields = {
        "root", "provisioning_root", "ambient_interpreter_root", "repository_root",
        "campaign_root", "appcontainer_profile_root", "broker_profile_root", "user_data_root",
    }
    binding = BundleBinding(**{
        key: Path(value) if key in path_fields else value
        for key, value in document.items()
    })

    validated = validate_worker_bundle(binding, WindowsBundleProbe(binding))

    assert validated.root == binding.root
    assert validated.manifest_digest == binding.manifest_digest
