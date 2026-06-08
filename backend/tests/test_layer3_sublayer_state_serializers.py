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
        summary_json={"finding_count": 3},
    )

    serialized = serialize_output_package_product(package)

    assert serialized == {
        "output_package_id": "pkg-1",
        "reconciliation_record_id": "recon-1",
        "package_kind": "canonical_internal",
        "status": "package_complete",
        "payload_hash": "hash-1",
    }
    assert "payload_ref" not in serialized
    assert "/secret/package/path" not in repr(serialized)
