import { test, expect } from '@playwright/test';
import {
  expectJson,
  expectJsonStatus,
  requestId,
  expectOnlyPayloadKeys,
  formPostPayload,
  expectStepAvailable,
  expectStepUnavailable,
  prepareExecutedLayer3Session,
  attachSessionToWorkbench,
} from './layer3-helpers.js';

test('Layer 3 workbench records bounded associated-cohort result review from server provenance', async ({ page }) => {
  const sessionId = 'session-cohort-ui';
  const analysisPlanId = 'plan-cohort-ui';
  const passRunId = 'pass-cohort-ui';
  const previewId = 'preview-cohort-ui';
  const previewHash = 'preview-hash-cohort-ui';
  const analysisRunId = 'analysis-run-cohort-ui';
  const outputPayloadRef = 'artifact://cohort-output-ui';
  const summary = {
    session_id: sessionId,
    execution_selection: {
      selected: true,
      execution_started: true,
      analysis_plan_id: analysisPlanId,
      pass_run_ids: [passRunId],
      analysis_run_ids: [analysisRunId],
      source_preview_id: previewId,
      source_preview_hash: previewHash,
      pass_run_statuses: {
        [passRunId]: 'completed',
      },
    },
    analysis_execution_start: {
      pass_run_id: passRunId,
      analysis_plan_id: analysisPlanId,
      analysis_run_id: analysisRunId,
      source_preview_id: previewId,
      source_preview_hash: previewHash,
      pass_run_status: 'completed',
      output_payload_ref: outputPayloadRef,
    },
    sublayer_visualization: {
      pass_runs: [
        {
          pass_run_id: passRunId,
          pass_type: 'associated_cohort',
          pass_scope: 'quantitative_associated_cohort_dataset_version',
          selected_method_name: 'descriptive_summary',
          requested_method_name: 'descriptive_summary',
          requested_method_source: 'analysis_set.formation_basis_json.requested_method_name',
          source_gate: '78_COHORT_FREEZE',
          source_dataset_version_ids: ['dv-cohort-001', 'dv-cohort-002'],
          cohort_shape: 'aligned_wide_table',
        },
      ],
    },
    downstream_unavailable: ['package', 'handoff', 'package_review'],
  };
  const status = {
    schema_id: 'layer3.execution_result_status.v1',
    status: 'available',
    session_id: sessionId,
    analysis_plan_id: analysisPlanId,
    pass_run_id: passRunId,
    preview_identity: {
      preview_id: previewId,
      preview_hash: previewHash,
    },
    execution_started: true,
    analysis_run_id: analysisRunId,
    pass_run_status: 'completed',
    output_payload_ref: outputPayloadRef,
    output_metadata_summary: {
      readable: true,
      artifact_count: 1,
      output_payload_ref: outputPayloadRef,
      pass_scope: 'quantitative_associated_cohort_dataset_version',
      selected_method_name: 'descriptive_summary',
      requested_method_name: 'descriptive_summary',
      requested_method_source: 'analysis_set.formation_basis_json.requested_method_name',
      source_gate: '78_COHORT_FREEZE',
      source_dataset_version_ids: ['dv-cohort-001', 'dv-cohort-002'],
      cohort_shape: 'aligned_wide_table',
    },
    result_status_available: true,
    result_review_enabled: false,
    package_review_enabled: false,
    handoff_enabled: false,
    downstream_unavailable: ['package', 'handoff', 'package_review'],
    pass_type: 'associated_cohort',
    pass_scope: 'quantitative_associated_cohort_dataset_version',
    selected_method_name: 'descriptive_summary',
  };
  const reviewResponse = {
    schema_id: 'layer3.execution_result_review.v1',
    status: 'recorded',
    session_id: sessionId,
    analysis_plan_id: analysisPlanId,
    pass_run_id: passRunId,
    preview_identity: {
      preview_id: previewId,
      preview_hash: previewHash,
    },
    analysis_run_id: analysisRunId,
    result_status_available: true,
    result_review_enabled: true,
    review_state: 'execution_result_review_approved',
    operator_decision: 'approved',
    review_record_ref: 'l3-result-review-cohort-ui',
    trace_summary: {
      session_id: sessionId,
      analysis_plan_id: analysisPlanId,
      pass_run_id: passRunId,
      analysis_run_id: analysisRunId,
      output_payload_ref: outputPayloadRef,
      selected_method_name: 'descriptive_summary',
      pass_scope: 'quantitative_associated_cohort_dataset_version',
      source_dataset_version_ids: ['dv-cohort-001', 'dv-cohort-002'],
      cohort_shape: 'aligned_wide_table',
      requested_method_name: 'descriptive_summary',
      requested_method_source: 'analysis_set.formation_basis_json.requested_method_name',
      source_gate: '78_COHORT_FREEZE',
      reviewed_item_count: 1,
      unresolved_trace_count: 0,
    },
    reviewed_output_items: [
      {
        index: 0,
        item_ref: outputPayloadRef,
        item_type: 'finding',
        trace_status: 'resolved',
        missing_trace_fields: [],
      },
    ],
    unresolved_trace_count: 0,
    package_review_enabled: false,
    handoff_enabled: false,
    downstream_unavailable: ['package', 'handoff', 'package_review'],
    review_notes_recorded: false,
    engine_family: 'layer3',
    pass_type: 'associated_cohort',
    pass_scope: 'quantitative_associated_cohort_dataset_version',
    selected_method_name: 'descriptive_summary',
    source_gate: '78_COHORT_FREEZE',
    source_dataset_version_ids: ['dv-cohort-001', 'dv-cohort-002'],
    cohort_shape: 'aligned_wide_table',
  };
  const packagePreviewResponse = {
    schema_id: 'layer3.package_review_preview.v1',
    status: 'available',
    session_id: sessionId,
    analysis_plan_id: analysisPlanId,
    pass_run_id: passRunId,
    preview_identity: {
      preview_id: previewId,
      preview_hash: previewHash,
    },
    package_review_preview_hash: 'l3-package-preview-cohort-ui',
    analysis_run_id: analysisRunId,
    result_status_available: true,
    result_review_state: 'execution_result_review_approved',
    result_review_record_ref: reviewResponse.review_record_ref,
    package_review_preview_enabled: true,
    package_commit_enabled: true,
    package_review_enabled: false,
    candidate_package_kinds: [
      {
        package_kind: 'canonical_internal',
        preview_only: true,
        package_commit_enabled: true,
        package_review_submit_enabled: false,
        handoff_enabled: false,
        readiness_reason: 'candidate family is eligible for bounded package construction commit',
      },
      {
        package_kind: 'user_facing',
        preview_only: true,
        package_commit_enabled: true,
        package_review_submit_enabled: false,
        handoff_enabled: false,
        readiness_reason: 'candidate family is eligible for bounded package construction commit',
      },
      {
        package_kind: 'review_facing',
        preview_only: true,
        package_commit_enabled: true,
        package_review_submit_enabled: false,
        handoff_enabled: false,
        readiness_reason: 'candidate family is eligible for bounded package construction commit',
      },
    ],
    package_owner_compatibility: {
      status: 'associated_cohort_construction_preconditions_satisfied',
      preview_candidate_projection_compatible: true,
      construction_compatible_with_current_workbench_state: true,
    },
    blocked_reasons: [],
    downstream_unavailable: [
      'package_review_submit',
      'handoff',
      'export',
      'aps_handoff',
      'external_export_download',
      'connector',
    ],
    next_state: 'package_review_preview_ready',
    output_metadata_summary: status.output_metadata_summary,
    trace_summary: reviewResponse.trace_summary,
    reviewed_output_item_summary: {
      reviewed_item_count: 1,
      unresolved_trace_count: 0,
    },
    unresolved_trace_count: 0,
    pass_type: 'associated_cohort',
    pass_scope: 'quantitative_associated_cohort_dataset_version',
    selected_method_name: 'descriptive_summary',
    source_gate: '78_COHORT_FREEZE',
    source_dataset_version_ids: ['dv-cohort-001', 'dv-cohort-002'],
    cohort_shape: 'aligned_wide_table',
    authority_rail: {
      current_gate: 'package',
      persistence_mode: 'read_only_package_review_preview',
      downstream_unavailable: [
        'package_review_submit',
        'handoff',
        'export',
        'aps_handoff',
        'external_export_download',
        'connector',
      ],
    },
  };
  const packageCommitResponse = {
    schema_id: 'layer3.package_construction_commit.v1',
    status: 'committed',
    session_id: sessionId,
    analysis_plan_id: analysisPlanId,
    pass_run_id: passRunId,
    preview_identity: {
      preview_id: previewId,
      preview_hash: previewHash,
    },
    analysis_run_id: analysisRunId,
    result_review_record_ref: reviewResponse.review_record_ref,
    package_review_preview_hash: packagePreviewResponse.package_review_preview_hash,
    reconciliation_record_id: 'recon-cohort-ui',
    output_packages: [
      {
        output_package_id: 'pkg-cohort-canonical',
        package_kind: 'canonical_internal',
        status: 'package_complete',
        payload_ref: 'artifact://cohort-canonical-package',
        payload_hash: 'a'.repeat(64),
      },
      {
        output_package_id: 'pkg-cohort-user',
        package_kind: 'user_facing',
        status: 'package_complete',
        payload_ref: 'artifact://cohort-user-package',
        payload_hash: 'b'.repeat(64),
      },
      {
        output_package_id: 'pkg-cohort-review',
        package_kind: 'review_facing',
        status: 'package_complete',
        payload_ref: 'artifact://cohort-review-package',
        payload_hash: 'c'.repeat(64),
      },
    ],
    package_kinds: ['canonical_internal', 'user_facing', 'review_facing'],
    payload_refs: [
      'artifact://cohort-canonical-package',
      'artifact://cohort-user-package',
      'artifact://cohort-review-package',
    ],
    payload_hashes: ['a'.repeat(64), 'b'.repeat(64), 'c'.repeat(64)],
    pass_scope: 'quantitative_associated_cohort_dataset_version',
    method: 'descriptive_summary',
    source_gate: '78_COHORT_FREEZE',
    package_construction_source_gate: '88_COHORT_PACKAGE_CONSTRUCTION_FREEZE',
    source_shape: 'aligned_wide_table',
    source_dataset_version_ids: ['dv-cohort-001', 'dv-cohort-002'],
    reviewed_output_item_summary: {
      reviewed_item_count: 1,
      unresolved_trace_count: 0,
    },
    package_review_submit_enabled: true,
    handoff_enabled: false,
    downstream_unavailable: [
      'handoff',
      'export',
      'aps_handoff',
      'external_export_download',
      'connector',
    ],
    next_state: 'package_constructed',
    authority_rail: {
      current_gate: 'package',
      persistence_mode: 'durable_package_construction',
      downstream_unavailable: [
        'handoff',
        'export',
        'aps_handoff',
        'external_export_download',
        'connector',
      ],
    },
  };
  const packageSubmitResponse = {
    schema_id: 'layer3.cohort_package_review_submit.v1',
    status: 'submitted',
    session_id: sessionId,
    analysis_plan_id: analysisPlanId,
    pass_run_id: passRunId,
    preview_identity: {
      preview_id: previewId,
      preview_hash: previewHash,
    },
    analysis_run_id: analysisRunId,
    result_review_record_ref: reviewResponse.review_record_ref,
    package_review_preview_hash: packagePreviewResponse.package_review_preview_hash,
    reconciliation_record_id: packageCommitResponse.reconciliation_record_id,
    output_package_ids: packageCommitResponse.output_packages.map((pkg) => pkg.output_package_id),
    package_kinds: packageCommitResponse.package_kinds,
    payload_hashes: packageCommitResponse.payload_hashes,
    operator_decision: 'approved',
    decision_notes: null,
    package_review_state: 'package_review_approved',
    submit_record_ref: 'submit-cohort-ui',
    pass_type: 'associated_cohort',
    pass_scope: 'quantitative_associated_cohort_dataset_version',
    method: 'descriptive_summary',
    source_gate: '78_COHORT_FREEZE',
    package_construction_source_gate: '88_COHORT_PACKAGE_CONSTRUCTION_FREEZE',
    source_shape: 'aligned_wide_table',
    source_dataset_version_ids: ['dv-cohort-001', 'dv-cohort-002'],
    package_review_submit_enabled: false,
    handoff_enabled: false,
    export_enabled: false,
    downstream_unavailable: [
      'handoff',
      'export',
      'aps_handoff',
      'external_export_download',
      'connector',
    ],
    next_state: 'package_review_approved',
  };
  const handoffReadyState = {
    schema_id: 'layer3.handoff_export_prepare_state.v1',
    available: true,
    state: 'handoff_export_ready',
    blocked_reason: null,
    analysis_run_id: analysisRunId,
    result_review_record_ref: reviewResponse.review_record_ref,
    package_review_preview_hash: packagePreviewResponse.package_review_preview_hash,
    reconciliation_record_id: packageCommitResponse.reconciliation_record_id,
    output_package_ids: packageCommitResponse.output_packages.map((pkg) => pkg.output_package_id),
    package_kinds: packageCommitResponse.package_kinds,
    payload_refs: packageCommitResponse.payload_refs,
    payload_hashes: packageCommitResponse.payload_hashes,
    package_review_submit_record_ref: packageSubmitResponse.submit_record_ref,
    package_review_state: 'package_review_approved',
    pass_type: 'associated_cohort',
    pass_scope: 'quantitative_associated_cohort_dataset_version',
    method: 'descriptive_summary',
    source_gate: '78_COHORT_FREEZE',
    package_construction_source_gate: '88_COHORT_PACKAGE_CONSTRUCTION_FREEZE',
    source_shape: 'aligned_wide_table',
    source_dataset_version_ids: ['dv-cohort-001', 'dv-cohort-002'],
    handoff_export_prepare_enabled: true,
    external_handoff_enabled: false,
    external_export_enabled: false,
    dispatch_enabled: false,
    downstream_unavailable: ['aps_handoff', 'external_export', 'downstream_dispatch'],
  };
  const handoffPrepareResponse = {
    schema_id: 'layer3.cohort_handoff_export_prepare.v1',
    status: 'prepared',
    session_id: sessionId,
    analysis_plan_id: analysisPlanId,
    pass_run_id: passRunId,
    preview_identity: {
      preview_id: previewId,
      preview_hash: previewHash,
    },
    analysis_run_id: analysisRunId,
    result_review_record_ref: reviewResponse.review_record_ref,
    package_review_preview_hash: packagePreviewResponse.package_review_preview_hash,
    reconciliation_record_id: packageCommitResponse.reconciliation_record_id,
    output_package_ids: packageCommitResponse.output_packages.map((pkg) => pkg.output_package_id),
    package_kinds: packageCommitResponse.package_kinds,
    payload_refs: packageCommitResponse.payload_refs,
    payload_hashes: packageCommitResponse.payload_hashes,
    package_review_submit_record_ref: packageSubmitResponse.submit_record_ref,
    package_review_state: 'package_review_approved',
    operator_decision: 'authorize_prepare',
    decision_notes: null,
    handoff_export_state: 'handoff_export_prepared',
    handoff_target: 'internal_export_envelope',
    export_mode: 'prepare_only',
    external_handoff_enabled: false,
    external_export_enabled: false,
    dispatch_enabled: false,
    downstream_unavailable: ['aps_handoff', 'external_export', 'downstream_dispatch'],
    next_state: 'handoff_export_prepared',
    prepare_record_ref: 'prepare-cohort-ui',
    pass_type: 'associated_cohort',
    pass_scope: 'quantitative_associated_cohort_dataset_version',
    method: 'descriptive_summary',
    source_gate: '78_COHORT_FREEZE',
    package_construction_source_gate: '88_COHORT_PACKAGE_CONSTRUCTION_FREEZE',
    source_shape: 'aligned_wide_table',
    source_dataset_version_ids: ['dv-cohort-001', 'dv-cohort-002'],
    package_review_submit_schema_id: 'layer3.cohort_package_review_submit.v1',
    handoff_export_envelope: {
      schema_id: 'layer3.handoff_export_envelope.v1',
      envelope_ref: 'envelope-cohort-ui',
      package_review_submit_record_ref: packageSubmitResponse.submit_record_ref,
      reconciliation_record_id: packageCommitResponse.reconciliation_record_id,
      output_package_ids: packageCommitResponse.output_packages.map((pkg) => pkg.output_package_id),
      payload_refs: packageCommitResponse.payload_refs,
      payload_hashes: packageCommitResponse.payload_hashes,
    },
  };
  let reviewPayload;
  let packagePreviewPayload;
  let packageCommitPayload;
  let packageSubmitPayload;
  let handoffPreparePayload;
  let packageCommitted = false;
  let packageSubmitted = false;
  let handoffPrepared = false;
  await page.route('**/api/v1/layer3/execution/result/review', async (route) => {
    reviewPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(reviewResponse),
    });
  });
  await page.route('**/api/v1/layer3/package/review/preview', async (route) => {
    packagePreviewPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(packagePreviewResponse),
    });
  });
  await page.route('**/api/v1/layer3/package/review/commit', async (route) => {
    packageCommitPayload = route.request().postDataJSON();
    packageCommitted = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(packageCommitResponse),
    });
  });
  await page.route('**/api/v1/layer3/package/review/submit', async (route) => {
    packageSubmitPayload = route.request().postDataJSON();
    packageSubmitted = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(packageSubmitResponse),
    });
  });
  await page.route('**/api/v1/layer3/handoff/export/prepare', async (route) => {
    handoffPreparePayload = route.request().postDataJSON();
    handoffPrepared = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(handoffPrepareResponse),
    });
  });
  await page.route(`**/api/v1/layer3/session/${sessionId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ...summary,
        current_gate: 'package',
        package_review_preview: packagePreviewResponse,
        package_construction: packageCommitted
          ? {
              schema_id: 'layer3.package_construction_commit_state.v1',
              available: false,
              state: 'package_constructed',
              reconciliation_record_id: packageCommitResponse.reconciliation_record_id,
              output_package_ids: packageCommitResponse.output_packages.map((pkg) => pkg.output_package_id),
              package_kinds: packageCommitResponse.package_kinds,
              package_commit_enabled: false,
              package_review_submit_enabled: !packageSubmitted,
              handoff_enabled: false,
              downstream_unavailable: packageSubmitted
                ? packageSubmitResponse.downstream_unavailable
                : packageCommitResponse.downstream_unavailable,
            }
          : {
              schema_id: 'layer3.package_construction_commit_state.v1',
              available: true,
              state: 'package_commit_ready',
              reconciliation_record_id: null,
              output_package_ids: [],
              package_kinds: ['canonical_internal', 'user_facing', 'review_facing'],
              package_commit_enabled: true,
              package_review_submit_enabled: false,
              handoff_enabled: false,
              downstream_unavailable: ['package_review_submit', 'handoff', 'export'],
            },
        package_review_submit: packageCommitted
          ? packageSubmitted
            ? {
              schema_id: 'layer3.package_review_submit_state.v1',
              available: false,
              state: 'package_review_approved',
              submit_record_ref: packageSubmitResponse.submit_record_ref,
              operator_decision: 'approved',
              analysis_run_id: analysisRunId,
              result_review_record_ref: reviewResponse.review_record_ref,
              package_review_preview_hash: packagePreviewResponse.package_review_preview_hash,
              reconciliation_record_id: packageCommitResponse.reconciliation_record_id,
              output_package_ids: packageCommitResponse.output_packages.map((pkg) => pkg.output_package_id),
              package_kinds: packageCommitResponse.package_kinds,
              payload_hashes: packageCommitResponse.payload_hashes,
              package_construction_source_gate: '88_COHORT_PACKAGE_CONSTRUCTION_FREEZE',
              package_review_submit_enabled: false,
              handoff_enabled: false,
              export_enabled: false,
              downstream_unavailable: packageSubmitResponse.downstream_unavailable,
            }
            : {
              schema_id: 'layer3.package_review_submit_state.v1',
              available: true,
              state: 'package_review_submit_ready',
              blocked_reason: null,
              reconciliation_record_id: packageCommitResponse.reconciliation_record_id,
              output_package_ids: packageCommitResponse.output_packages.map((pkg) => pkg.output_package_id),
              package_kinds: packageCommitResponse.package_kinds,
              payload_hashes: packageCommitResponse.payload_hashes,
              package_construction_source_gate: '88_COHORT_PACKAGE_CONSTRUCTION_FREEZE',
              package_review_submit_enabled: true,
              handoff_enabled: false,
              export_enabled: false,
              downstream_unavailable: packageCommitResponse.downstream_unavailable,
            }
          : {
              schema_id: 'layer3.package_review_submit_state.v1',
              available: false,
              state: 'package_review_submit_unavailable',
              blocked_reason: 'package_not_constructed',
              package_review_submit_enabled: false,
              handoff_enabled: false,
              export_enabled: false,
              downstream_unavailable: ['package_review_submit', 'handoff', 'export'],
            },
        downstream_unavailable: packageCommitted
          ? packageSubmitted
            ? ['aps_handoff', 'external_export', 'downstream_dispatch']
            : packageCommitResponse.downstream_unavailable
          : ['package_review_submit', 'handoff', 'export'],
        handoff_export_prepare: packageSubmitted
          ? handoffPrepared
            ? handoffPrepareResponse
            : handoffReadyState
          : {
              schema_id: 'layer3.handoff_export_prepare_state.v1',
              available: false,
              state: 'handoff_export_unavailable',
              blocked_reason: 'approved_package_review_submit_required',
              handoff_export_prepare_enabled: false,
              external_handoff_enabled: false,
              external_export_enabled: false,
              dispatch_enabled: false,
              downstream_unavailable: ['handoff', 'export'],
            },
        aps_handoff_dispatch: {
          schema_id: 'layer3.aps_handoff_dispatch_state.v1',
          available: false,
          state: 'aps_handoff_unavailable',
          blocked_reason: handoffPrepared
            ? 'associated_cohort_aps_handoff_dispatch_not_admitted'
            : 'handoff_export_prepared_required',
          aps_handoff_enabled: false,
          external_export_enabled: false,
          download_enabled: false,
          connector_dispatch_enabled: false,
          downstream_unavailable: ['aps_handoff', 'external_export', 'downstream_dispatch'],
        },
        execution_result_review: {
          schema_id: 'layer3.execution_result_review_state.v1',
          review_record_ref: reviewResponse.review_record_ref,
          review_state: reviewResponse.review_state,
          operator_decision: reviewResponse.operator_decision,
          pass_run_id: passRunId,
          analysis_plan_id: analysisPlanId,
          analysis_run_id: analysisRunId,
          pass_type: 'associated_cohort',
          pass_scope: 'quantitative_associated_cohort_dataset_version',
          selected_method_name: 'descriptive_summary',
          source_gate: '78_COHORT_FREEZE',
          source_dataset_version_ids: ['dv-cohort-001', 'dv-cohort-002'],
          cohort_shape: 'aligned_wide_table',
          unresolved_trace_count: 0,
          package_review_enabled: false,
          handoff_enabled: false,
          downstream_unavailable: ['package', 'handoff', 'package_review'],
        },
      }),
    });
  });

  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.evaluate(({ summaryState, statusState }) => {
    State.sessionSummary = summaryState;
    State.resultStatus = statusState;
    State.resultReview = null;
    State.resultReviewError = null;
    State.resultStatusError = null;
    renderAll();
  }, { summaryState: summary, statusState: status });

  await expect(page.locator('#result-review-panel')).toContainText('cohort_result_review_ui_review_ready');
  await expect(page.locator('#result-review-panel')).toContainText('associated_cohort');
  await expect(page.locator('#result-review-panel')).toContainText('descriptive_summary');
  await expect(page.locator('#result-review-panel')).toContainText('78_COHORT_FREEZE');
  await expect(page.locator('#result-review-panel')).toContainText('dv-cohort-001');
  await expect(page.locator('#result-review-submit')).toBeEnabled();

  const reviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/execution/result/review'));
  await page.locator('#result-review-submit').click();
  await expectJson(await reviewResponsePromise);
  expectOnlyPayloadKeys(reviewPayload, [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'operator_decision',
    'review_notes',
    'analysis_run_id',
    'reviewed_output_items',
  ]);
  expect(reviewPayload.session_id).toBe(sessionId);
  expect(reviewPayload.analysis_plan_id).toBe(analysisPlanId);
  expect(reviewPayload.pass_run_id).toBe(passRunId);
  expect(reviewPayload.operator_decision).toBe('approved');
  expect(reviewPayload.reviewed_output_items).toEqual([
    {
      item_ref: outputPayloadRef,
      item_type: 'finding',
      trace: {
        session_id: sessionId,
        analysis_plan_id: analysisPlanId,
        pass_run_id: passRunId,
        output_payload_ref: outputPayloadRef,
        analysis_run_id: analysisRunId,
      },
    },
  ]);
  expect(reviewPayload).not.toHaveProperty('package');
  expect(reviewPayload).not.toHaveProperty('handoff');
  expect(reviewPayload).not.toHaveProperty('rerun');
  expect(reviewPayload).not.toHaveProperty('pass_run_ids');
  expect(reviewPayload).not.toHaveProperty('artifact_manifest');

  await expect(page.locator('#result-review-panel')).toContainText('cohort_result_review_ui_recorded');
  await expect(page.locator('#package-review-preview-inspect')).toBeEnabled();
  const packagePreviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/preview'));
  await page.locator('#package-review-preview-inspect').click();
  await expectJson(await packagePreviewResponsePromise);
  expectOnlyPayloadKeys(packagePreviewPayload, [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'analysis_run_id',
    'result_review_record_ref',
  ]);
  expect(packagePreviewPayload.session_id).toBe(sessionId);
  expect(packagePreviewPayload.result_review_record_ref).toBe(reviewResponse.review_record_ref);
  expect(packagePreviewPayload).not.toHaveProperty('reviewed_output_items');
  expect(packagePreviewPayload).not.toHaveProperty('package');
  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_preview_ready');
  await expect(page.locator('#package-review-preview-panel')).toContainText('commit ready');
  await expect(page.locator('#package-construction-commit')).toBeEnabled();

  const packageCommitResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/commit'));
  await page.locator('#package-construction-commit').click();
  const packageCommit = await expectJson(await packageCommitResponsePromise);
  expect(packageCommit.schema_id).toBe('layer3.package_construction_commit.v1');
  expect(packageCommit.package_review_submit_enabled).toBe(true);
  expect(packageCommit.package_construction_source_gate).toBe('88_COHORT_PACKAGE_CONSTRUCTION_FREEZE');
  expect(packageCommit.downstream_unavailable).toEqual([
    'handoff',
    'export',
    'aps_handoff',
    'external_export_download',
    'connector',
  ]);
  expectOnlyPayloadKeys(packageCommitPayload, [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'analysis_run_id',
    'result_review_record_ref',
    'package_review_preview_hash',
    'expected_package_kinds',
  ]);
  expect(packageCommitPayload.result_review_record_ref).toBe(reviewResponse.review_record_ref);
  expect(packageCommitPayload.package_review_preview_hash).toBe(packagePreviewResponse.package_review_preview_hash);
  expect(packageCommitPayload.expected_package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
  expect(packageCommitPayload).not.toHaveProperty('package_review_submit');
  expect(packageCommitPayload).not.toHaveProperty('handoff');
  expect(packageCommitPayload).not.toHaveProperty('export');

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_constructed');
  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_submit_ready');
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeEnabled();

  const packageSubmitResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/submit'));
  await page.locator('#package-review-submit').click();
  const packageSubmit = await expectJson(await packageSubmitResponsePromise);
  expect(packageSubmit.schema_id).toBe('layer3.cohort_package_review_submit.v1');
  expect(packageSubmit.package_review_state).toBe('package_review_approved');
  expect(packageSubmit.pass_type).toBe('associated_cohort');
  expect(packageSubmit.package_construction_source_gate).toBe('88_COHORT_PACKAGE_CONSTRUCTION_FREEZE');
  expect(packageSubmit.downstream_unavailable).toEqual([
    'handoff',
    'export',
    'aps_handoff',
    'external_export_download',
    'connector',
  ]);
  expectOnlyPayloadKeys(packageSubmitPayload, [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'analysis_run_id',
    'result_review_record_ref',
    'package_review_preview_hash',
    'reconciliation_record_id',
    'output_package_ids',
    'payload_hashes',
    'operator_decision',
    'decision_notes',
    'expected_package_kinds',
  ]);
  expect(packageSubmitPayload.operator_decision).toBe('approved');
  expect(packageSubmitPayload.reconciliation_record_id).toBe(packageCommit.reconciliation_record_id);
  expect(packageSubmitPayload.output_package_ids.sort()).toEqual(packageCommit.output_packages.map((pkg) => pkg.output_package_id).sort());
  expect(packageSubmitPayload.payload_hashes).toEqual(packageCommit.payload_hashes);
  expect(packageSubmitPayload).not.toHaveProperty('handoff');
  expect(packageSubmitPayload).not.toHaveProperty('export');
  expect(packageSubmitPayload).not.toHaveProperty('package_payload');

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_approved');
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('handoff_export_ready');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('associated_cohort');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('descriptive_summary');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('internal_export_envelope');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeEnabled();

  const handoffPrepareResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/export/prepare'));
  const postHandoffSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${sessionId}`));
  await page.locator('#handoff-export-prepare-submit').click();
  const handoffPrepare = await expectJson(await handoffPrepareResponsePromise);
  expect(handoffPrepare.schema_id).toBe('layer3.cohort_handoff_export_prepare.v1');
  expect(handoffPrepare.handoff_export_state).toBe('handoff_export_prepared');
  expect(handoffPrepare.pass_type).toBe('associated_cohort');
  expect(handoffPrepare.package_construction_source_gate).toBe('88_COHORT_PACKAGE_CONSTRUCTION_FREEZE');
  expect(handoffPrepare.downstream_unavailable).toEqual(['aps_handoff', 'external_export', 'downstream_dispatch']);
  expectOnlyPayloadKeys(handoffPreparePayload, [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'result_review_record_ref',
    'package_review_preview_hash',
    'reconciliation_record_id',
    'output_package_ids',
    'payload_refs',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
    'package_review_submit_schema_id',
    'handoff_target',
    'export_mode',
    'operator_decision',
    'expected_package_kinds',
    'analysis_run_id',
  ]);
  expect(handoffPreparePayload.package_review_state).toBe('package_review_approved');
  expect(handoffPreparePayload.package_review_submit_schema_id).toBe(packageSubmit.schema_id);
  expect(handoffPreparePayload.handoff_target).toBe('internal_export_envelope');
  expect(handoffPreparePayload.export_mode).toBe('prepare_only');
  expect(handoffPreparePayload.operator_decision).toBe('authorize_prepare');
  expect(handoffPreparePayload.output_package_ids.sort()).toEqual(packageCommit.output_packages.map((pkg) => pkg.output_package_id).sort());
  expect(handoffPreparePayload.payload_refs).toEqual(packageCommit.payload_refs);
  expect(handoffPreparePayload.payload_hashes).toEqual(packageCommit.payload_hashes);
  for (const forbidden of [
    'aps_handoff',
    'dispatch',
    'send',
    'external_export',
    'download',
    'connector_run_id',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'rewrite_output',
  ]) {
    expect(handoffPreparePayload).not.toHaveProperty(forbidden);
  }
  await expectJson(await postHandoffSummaryPromise);

  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('handoff_export_prepared');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('prepare-cohort-ui');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('aps handoff');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('external export');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();
  await expectStepAvailable(page, 'handoff');
});

test('Layer 3 workbench blocks associated-cohort result review when provenance is incomplete', async ({ page }) => {
  const sessionId = 'session-cohort-ui-blocked';
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.evaluate((id) => {
    State.sessionSummary = {
      session_id: id,
      execution_selection: {
        selected: true,
        execution_started: true,
        analysis_plan_id: 'plan-cohort-ui-blocked',
        pass_run_ids: ['pass-cohort-ui-blocked'],
        analysis_run_ids: ['analysis-run-cohort-ui-blocked'],
        source_preview_id: 'preview-cohort-ui-blocked',
        source_preview_hash: 'preview-hash-cohort-ui-blocked',
        pass_run_statuses: {
          'pass-cohort-ui-blocked': 'completed',
        },
      },
      downstream_unavailable: ['package', 'handoff', 'package_review'],
      sublayer_visualization: {
        pass_runs: [
          {
            pass_run_id: 'pass-cohort-ui-blocked',
            pass_type: 'associated_cohort',
            pass_scope: 'quantitative_associated_cohort_dataset_version',
            selected_method_name: 'descriptive_summary',
            requested_method_name: 'descriptive_summary',
            requested_method_source: 'analysis_set.formation_basis_json.requested_method_name',
            source_gate: '78_COHORT_FREEZE',
            cohort_shape: 'aligned_wide_table',
          },
        ],
      },
    };
    State.resultStatus = {
      schema_id: 'layer3.execution_result_status.v1',
      status: 'available',
      session_id: id,
      analysis_plan_id: 'plan-cohort-ui-blocked',
      pass_run_id: 'pass-cohort-ui-blocked',
      preview_identity: {
        preview_id: 'preview-cohort-ui-blocked',
        preview_hash: 'preview-hash-cohort-ui-blocked',
      },
      analysis_run_id: 'analysis-run-cohort-ui-blocked',
      pass_run_status: 'completed',
      output_payload_ref: 'artifact://cohort-output-ui-blocked',
      output_metadata_summary: {
        readable: true,
        artifact_count: 1,
        output_payload_ref: 'artifact://cohort-output-ui-blocked',
        pass_scope: 'quantitative_associated_cohort_dataset_version',
        selected_method_name: 'descriptive_summary',
        requested_method_name: 'descriptive_summary',
        requested_method_source: 'analysis_set.formation_basis_json.requested_method_name',
        source_gate: '78_COHORT_FREEZE',
        cohort_shape: 'aligned_wide_table',
      },
      result_status_available: true,
      downstream_unavailable: ['package', 'handoff', 'package_review'],
      pass_type: 'associated_cohort',
      pass_scope: 'quantitative_associated_cohort_dataset_version',
      selected_method_name: 'descriptive_summary',
    };
    State.resultReview = null;
    State.resultReviewError = null;
    State.resultStatusError = null;
    renderAll();
  }, sessionId);

  await expect(page.locator('#result-review-panel')).toContainText('cohort_result_review_ui_blocked');
  await expect(page.locator('#result-review-panel')).toContainText('source dataset versions: unknown');
  await expect(page.locator('#result-review-submit')).toBeDisabled();
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
});
