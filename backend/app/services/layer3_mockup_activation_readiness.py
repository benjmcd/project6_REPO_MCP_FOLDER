from __future__ import annotations

from typing import Any


MOCKUP_ACTIVATION_READINESS_SCHEMA_ID = "layer3.mockup_activation_readiness.v1"
MOCKUP_ACTIVATION_READINESS_PHASE = "next_phase_activation_readiness"
MOCKUP_FIRST_ADMITTED_SLICE = "query_source_setup_interactive_live_classification"

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
        "server_authority": "session summary pdf_location_projection",
        "rendered_surface": "#mockup-pdf-location-projection",
        "evidence": (
            "server PDF-location projection renders bounded location items when available",
            "projection remains unavailable without session summary authority",
        ),
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
        "classification": "read_only",
        "activation_slice": None,
        "server_authority": "session summary result-review, package, handoff, delivery, and webhook state",
        "rendered_surface": "#mockup-output-review-package-handoff-projection",
        "evidence": (
            "output review package handoff projection reads server session state",
            "projection has no controls",
        ),
        "next_allowed_action": "select_exact_server_owned_review_or_handoff_control_before_activation",
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


def mockup_activation_readiness_contract() -> dict[str, Any]:
    journeys = [dict(row, evidence=list(row["evidence"])) for row in _JOURNEYS]
    return {
        "schema_id": MOCKUP_ACTIVATION_READINESS_SCHEMA_ID,
        "phase": MOCKUP_ACTIVATION_READINESS_PHASE,
        "selected_first_slice": MOCKUP_FIRST_ADMITTED_SLICE,
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
        "next_posture": "land_first_activation_readiness_slice_without_full_mockup_activation",
    }
