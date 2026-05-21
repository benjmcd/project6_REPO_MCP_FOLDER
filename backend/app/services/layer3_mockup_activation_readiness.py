from __future__ import annotations

from typing import Any


MOCKUP_ACTIVATION_READINESS_SCHEMA_ID = "layer3.mockup_activation_readiness.v1"
MOCKUP_ACTIVATION_READINESS_PHASE = "next_phase_activation_readiness"
MOCKUP_FIRST_ADMITTED_SLICE = "query_source_setup_interactive_live_classification"
MOCKUP_NEXT_ADMITTED_SLICE = "output_review_package_handoff_interactive_live_contract"
MOCKUP_PDF_LOCATION_PROJECTION_SLICE = "pdf_location_read_only_live_projection_contract"

_NO_GO_BOUNDARIES = (
    "frontend_only_durable_authority",
    "raw_provider_url_or_token_exposure",
    "unapproved_connector_destination_write",
    "unapproved_provider_object_or_network_write",
    "broad_source_family_expansion",
    "broad_model_provider_rag_expansion",
    "full_mockup_program_activation",
)

_REQUIRED_EVIDENCE = (
    "live_source_owner",
    "route_api_contract",
    "server_authority_contract",
    "negative_invariant_proof",
    "headed_browser_proof",
    "headless_browser_proof",
    "progress_check_guard",
)

_JOURNEYS = (
    {
        "journey_id": "query_source_setup",
        "label": "Query/source setup",
        "classification": "interactive_live",
        "activation_slice": MOCKUP_FIRST_ADMITTED_SLICE,
        "server_authority": "existing intent, source-intake, server-configured source-directory, material-preview, and Gate B APIs",
        "rendered_surface": "#mockup-query-source-setup-projection",
        "evidence": (
            "source-directory scan/status rendered controls",
            "material preview and Gate B rendered controls",
            "query/source setup projection has no frontend durable state",
        ),
        "next_allowed_action": "keep_projection_mapped_to_existing_server_controls",
    },
    {
        "journey_id": "pdf_location",
        "label": "PDF-location evidence",
        "classification": "read_only",
        "activation_slice": None,
        "projection_slice": MOCKUP_PDF_LOCATION_PROJECTION_SLICE,
        "server_authority": "session summary pdf_location_projection",
        "rendered_surface": "#mockup-pdf-location-projection",
        "evidence": (
            "server PDF-location projection renders bounded location items when available",
            "projection remains unavailable without session summary authority",
            "projection exposes no browser-owned PDF-location authority or raw PDF/provider URL surface",
        ),
        "projection_contract": {
            "contract_id": MOCKUP_PDF_LOCATION_PROJECTION_SLICE,
            "schema_id": "layer3.pdf_location_projection.v1",
            "server_authority_contract": "aps_content_document_chunk_page_refs_and_citation_highlight_spans",
            "status_projection": (
                "State.sessionSummary.pdf_location_projection",
            ),
            "rendered_surface": "#mockup-pdf-location-projection",
            "read_only_controls_absent": (
                "button",
                "input",
                "select",
                "textarea",
                "a[href]",
            ),
            "negative_boundaries": (
                "browser_owned_authoritative_pdf_location",
                "raw_pdf_blob_streaming",
                "pdf_byte_download",
                "provider_or_object_store_url_exposure",
                "frontend_only_durable_authority",
                "full_mockup_program_activation",
            ),
        },
        "next_allowed_action": "select_a_write_or_navigation_authority_before_interactive_activation",
    },
    {
        "journey_id": "sublayers_3a_3b",
        "label": "Sublayers 3A/3B",
        "classification": "read_only",
        "activation_slice": None,
        "server_authority": "session summary sublayer_visualization",
        "rendered_surface": "#mockup-sublayers-ab-projection",
        "evidence": (
            "server sublayer visualization projection",
            "mockup fixture remains target-state only",
        ),
        "next_allowed_action": "select_exact_server_owned_edit_or_drilldown_before_activation",
    },
    {
        "journey_id": "sublayer_3c_execution_lanes",
        "label": "Sublayer 3C execution lanes",
        "classification": "read_only",
        "activation_slice": None,
        "server_authority": "session summary analysis_environment_projection and execution state",
        "rendered_surface": "#mockup-execution-lanes-projection",
        "evidence": (
            "analysis environment projection is read-only",
            "execution lane projection has no controls",
        ),
        "next_allowed_action": "select_exact_execution_lane_control_before_interactive_activation",
    },
    {
        "journey_id": "output_review_package_handoff",
        "label": "Output review/package/handoff",
        "classification": "interactive_live",
        "activation_slice": MOCKUP_NEXT_ADMITTED_SLICE,
        "server_authority": "existing result-review, package lifecycle, handoff/export, delivery/use, local outbox, provider-private, external-local export, and internal webhook APIs",
        "rendered_surface": "#mockup-output-review-package-handoff-projection",
        "evidence": (
            "output review package handoff projection reads server session state",
            "existing rendered controls submit only server-owned route contracts",
            "status projections read session-summary receipt state without exposing package bytes, raw provider tokens, or destination credentials",
        ),
        "interaction_contract": {
            "contract_id": MOCKUP_NEXT_ADMITTED_SLICE,
            "route_authority": (
                "/api/v1/layer3/execution/result/review",
                "/api/v1/layer3/package/review/preview",
                "/api/v1/layer3/package/review/commit",
                "/api/v1/layer3/package/review/submit",
                "/api/v1/layer3/handoff/export/prepare",
                "/api/v1/layer3/handoff/export/download/prepare",
                "/api/v1/layer3/handoff/export/download/deliver",
                "/api/v1/layer3/handoff/connector/local-outbox/write",
                "/api/v1/layer3/handoff/connector/local-outbox/provider-private/prepare",
                "/api/v1/layer3/handoff/connector/local-outbox/external-local-export/write",
                "/api/v1/layer3/handoff/export/internal-webhook/dispatch",
            ),
            "rendered_controls": (
                "#result-review-submit",
                "#package-review-preview-inspect",
                "#package-construction-commit",
                "#package-review-submit",
                "#handoff-export-prepare-submit",
                "#external-export-download-prepare-submit",
                "#external-export-download-delivery-submit",
                "#server-owned-local-outbox-write-panel",
                "#local-outbox-provider-private-handoff-panel",
                "#external-local-export-panel",
                "#internal-webhook-dispatch-panel",
            ),
            "status_projection": (
                "State.sessionSummary.execution_result_review",
                "State.sessionSummary.package_construction",
                "State.sessionSummary.package_review_submit",
                "State.sessionSummary.handoff_export_prepare",
                "State.sessionSummary.external_export_download",
                "State.sessionSummary.server_owned_local_outbox_write",
                "State.sessionSummary.local_outbox_provider_private_handoff",
                "State.sessionSummary.external_local_export",
                "State.sessionSummary.internal_webhook_dispatch",
            ),
            "negative_boundaries": (
                "raw_package_payload_exposure",
                "raw_provider_token_exposure",
                "unapproved_connector_destination_write",
                "frontend_only_durable_authority",
                "full_mockup_program_activation",
            ),
        },
        "next_allowed_action": "prove_existing_controls_from_current_main_before_any_new_output_review_package_handoff_runtime",
    },
    {
        "journey_id": "full_mockup_program",
        "label": "Full mockup program",
        "classification": "blocked",
        "activation_slice": None,
        "server_authority": "layer3.mockup_truth_state_contract.v1",
        "rendered_surface": "#mockup-theme-shell",
        "evidence": (
            "full mockup activation remains explicitly blocked",
            "frontend-only durable authority remains explicitly blocked",
        ),
        "next_allowed_action": "create_later_freeze_and_full_readiness_audit_before_activation",
    },
)


def _journey_response(row: dict[str, Any]) -> dict[str, Any]:
    response = dict(row)
    response["evidence"] = list(row["evidence"])
    for contract_key in ("interaction_contract", "projection_contract"):
        if isinstance(row.get(contract_key), dict):
            response[contract_key] = {
                key: list(value) if isinstance(value, tuple) else value
                for key, value in row[contract_key].items()
            }
    return response


def mockup_activation_readiness_contract() -> dict[str, Any]:
    journeys = [_journey_response(row) for row in _JOURNEYS]
    return {
        "schema_id": MOCKUP_ACTIVATION_READINESS_SCHEMA_ID,
        "phase": MOCKUP_ACTIVATION_READINESS_PHASE,
        "selected_first_slice": MOCKUP_FIRST_ADMITTED_SLICE,
        "selected_next_slice": MOCKUP_NEXT_ADMITTED_SLICE,
        "selected_projection_slice": MOCKUP_PDF_LOCATION_PROJECTION_SLICE,
        "classification_mode": "server_owned_next_phase_activation_readiness",
        "journeys": journeys,
        "journey_counts": {
            "interactive_live": sum(row["classification"] == "interactive_live" for row in journeys),
            "read_only": sum(row["classification"] == "read_only" for row in journeys),
            "intentionally_excluded": sum(row["classification"] == "intentionally_excluded" for row in journeys),
            "blocked": sum(row["classification"] == "blocked" for row in journeys),
        },
        "required_activation_evidence": list(_REQUIRED_EVIDENCE),
        "no_go_boundaries": list(_NO_GO_BOUNDARIES),
        "full_mockup_activation_enabled": False,
        "frontend_only_durable_authority_enabled": False,
        "raw_provider_exposure_enabled": False,
        "connector_provider_write_enabled": False,
        "broad_source_model_rag_expansion_enabled": False,
        "mutates_runtime_state": False,
        "next_posture": "prove_pdf_location_read_only_projection_contract_before_selecting_next_projection_journey",
    }
