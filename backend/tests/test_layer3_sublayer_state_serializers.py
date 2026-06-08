from __future__ import annotations

from types import SimpleNamespace

from app.services.layer3_sublayer_state import (
    serialize_output_package_product,
    serialize_reconciliation_record,
)


def test_serialize_reconciliation_record_exposes_only_status_and_package_status() -> None:
    record = SimpleNamespace(
        reconciliation_record_id="recon-1",
        status="reconciled_with_warnings",
        summary_json={
            "package_status": "package_complete_with_warnings",
            "workbench_package_commit": {
                "result_review_record_ref": "/secret/review/ref",
                "output_payload_ref": "/secret/payload/path",
                "output_payload_hash": "deadbeef",
                "authority_basis_hash": "cafebabe",
            },
        },
    )

    serialized = serialize_reconciliation_record(record)

    assert serialized == {
        "reconciliation_record_id": "recon-1",
        "status": "reconciled_with_warnings",
        "package_status": "package_complete_with_warnings",
    }
    # The nested workbench_package_commit raw refs must never surface.
    leaked = repr(serialized)
    for secret in (
        "/secret/review/ref",
        "/secret/payload/path",
        "result_review_record_ref",
        "output_payload_ref",
        "workbench_package_commit",
        "authority_basis_hash",
    ):
        assert secret not in leaked


def test_serialize_reconciliation_record_guards_non_dict_summary() -> None:
    record = SimpleNamespace(
        reconciliation_record_id="recon-2",
        status="review_only",
        summary_json=None,
    )

    assert serialize_reconciliation_record(record) == {
        "reconciliation_record_id": "recon-2",
        "status": "review_only",
        "package_status": None,
    }


def test_serialize_output_package_product_never_exposes_payload_ref() -> None:
    package = SimpleNamespace(
        output_package_id="pkg-1",
        reconciliation_record_id="recon-1",
        package_kind="canonical_internal",
        status="package_complete",
        payload_hash="hash-1",
        payload_ref="/secret/package/path",
        summary_json={
            "finding_count": 3,
            "contradiction_count": 1,
            "caveat_count": 0,
            "output_payload_ref": "/secret/payload/path",
        },
    )

    serialized = serialize_output_package_product(package)

    assert serialized == {
        "output_package_id": "pkg-1",
        "reconciliation_record_id": "recon-1",
        "package_kind": "canonical_internal",
        "status": "package_complete",
        "payload_hash": "hash-1",
        "content": {
            "finding_count": 3,
            "contradiction_count": 1,
            "caveat_count": 0,
        },
    }
    assert "payload_ref" not in serialized
    assert "/secret/package/path" not in repr(serialized)
    assert "/secret/payload/path" not in repr(serialized)


def test_serialize_output_package_product_content_guards_non_int_counts() -> None:
    package = SimpleNamespace(
        output_package_id="pkg-2",
        reconciliation_record_id="recon-1",
        package_kind="user_facing",
        status="package_complete",
        payload_hash="hash-2",
        payload_ref="/secret/path",
        summary_json={"finding_count": "lots", "contradiction_count": -1, "caveat_count": True},
    )

    content = serialize_output_package_product(package)["content"]

    # non-int, negative, and bool counts all degrade to None rather than rendering junk
    assert content == {
        "finding_count": None,
        "contradiction_count": None,
        "caveat_count": None,
    }
