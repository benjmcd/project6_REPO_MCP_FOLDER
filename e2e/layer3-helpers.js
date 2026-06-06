import { expect } from '@playwright/test';

export async function expectJson(response) {
  expect(response.status()).toBe(200);
  return response.json();
}

export async function expectJsonStatus(response, status) {
  expect(response.status()).toBe(status);
  return response.json();
}

export function requestId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function expectOnlyPayloadKeys(payload, allowedKeys) {
  expect(Object.keys(payload).sort()).toEqual([...allowedKeys].sort());
}

export function formPostPayload(request) {
  const payload = {};
  const params = new URLSearchParams(request.postData() || '');
  for (const [key, value] of params.entries()) {
    payload[key] = JSON.parse(value);
  }
  return payload;
}

export async function expectStepAvailable(page, step) {
  const chip = page.locator(`[data-step="${step}"]`);
  await expect(chip).toBeEnabled();
  await expect(chip).toHaveAttribute('data-available', 'true');
  await expect(chip).not.toHaveClass(/unavailable/);
}

export async function expectStepUnavailable(page, step) {
  const chip = page.locator(`[data-step="${step}"]`);
  await expect(chip).toBeEnabled();
  await expect(chip).toHaveAttribute('data-available', 'false');
  await expect(chip).toHaveClass(/unavailable/);
}

export async function prepareExecutedLayer3Session(request, seedPath = '/__test/layer3/seed-quant') {
  const seed = await expectJson(await request.post(seedPath));
  const planPreview = await expectJson(await request.post('/api/v1/layer3/plan/preview', {
    data: {
      schema_id: 'layer3.plan_preview_request.v1',
      client_request_id: requestId('plan-preview'),
      session_id: seed.session_id,
      include_exclusions: true,
      preview_scope: 'owner_service_default',
    },
  }));
  const approval = await expectJson(await request.post('/api/v1/layer3/plan/approve', {
    data: {
      schema_id: 'layer3.plan_approval_request.v1',
      client_request_id: requestId('plan-approve'),
      session_id: seed.session_id,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      operator_confirmation: true,
      approval_scope: 'owner_service_default',
    },
  }));
  const selection = await expectJson(await request.post('/api/v1/layer3/execution/select', {
    data: {
      client_request_id: requestId('execution-select'),
      session_id: seed.session_id,
      analysis_plan_id: approval.analysis_plan_id,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      operator_reason: 'browser harness selected pass setup',
    },
  }));
  const passRunId = selection.pass_run_ids[0];
  const start = await expectJson(await request.post('/api/v1/layer3/execution/start', {
    data: {
      client_request_id: requestId('execution-start'),
      session_id: seed.session_id,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      execution_mode: 'synchronous_single_pass',
      operator_reason: 'browser harness terminal pass setup',
    },
  }));

  expect(selection.pass_run_ids).toHaveLength(1);
  expect(['completed', 'completed_with_warnings', 'failed']).toContain(start.pass_run_status);
  return { seed, planPreview, approval, selection, start, passRunId };
}

function layer3DecisionBasis(candidate) {
  return {
    source_ref: candidate.source_ref,
    query_basis: candidate.query_basis,
    provenance_ref: candidate.provenance_ref,
    source_identity: candidate.source_identity,
    source_provenance: candidate.source_provenance,
    payload: candidate.payload,
    load_summary: candidate.load_summary,
  };
}

function approvedLayer3CandidateDecision(candidate) {
  return {
    candidate_id: candidate.candidate_id,
    decision: 'approved',
    decision_basis: layer3DecisionBasis(candidate),
  };
}

export async function prepareQualitativeApsResultReviewSession(request) {
  const seed = await expectJson(await request.post('/__test/layer3/seed-aps-document'));
  const preflight = await expectJson(await request.post('/api/v1/layer3/preflight', {
    data: {
      client_request_id: requestId('qual-aps-ui-preflight'),
      natural_language_intent: 'Review one indexed APS content document as qualitative source material.',
      manual_constraints: { source_classes: ['aps_content_document'] },
    },
  }));
  const source = await expectJson(await request.post('/api/v1/layer3/source-preview', {
    data: {
      client_request_id: requestId('qual-aps-ui-source-preview'),
      preflight_id: preflight.preflight_id,
      selected_source_classes: ['aps_content_document'],
    },
  }));
  expect(source.source_candidates.map((candidate) => candidate.source_class)).toEqual(['aps_content_document']);

  const material = await expectJson(await request.post('/api/v1/layer3/material-preview', {
    data: {
      client_request_id: requestId('qual-aps-ui-material-preview'),
      preflight_id: preflight.preflight_id,
      source_set_id: source.source_set_id,
      source_candidate_ids: source.source_candidates.map((candidate) => candidate.source_candidate_id),
      aps_content_document_ids: [seed.content_id],
      query_basis: {
        terms: ['aps', 'qualitative', 'single-document'],
        filters: { aps_content_document_ids: [seed.content_id] },
      },
    },
  }));
  expect(material.material_candidates).toHaveLength(1);
  expect(material.material_candidates[0].source_identity.content_id).toBe(seed.content_id);

  const gateB = await expectJson(await request.post('/api/v1/layer3/gate-b/decision', {
    data: {
      client_request_id: requestId('qual-aps-ui-gate-b'),
      preflight_id: preflight.preflight_id,
      source_set_id: source.source_set_id,
      material_preview_id: material.material_preview_id,
      material_preview_hash: material.material_preview_hash,
      candidate_decisions: material.material_candidates.map(approvedLayer3CandidateDecision),
    },
  }));
  const gateC = await expectJson(await request.post('/api/v1/layer3/gate-c/preview', {
    data: {
      client_request_id: requestId('qual-aps-ui-gate-c'),
      session_id: gateB.session_id,
      commit_typing: true,
    },
  }));
  const planPreview = await expectJson(await request.post('/api/v1/layer3/plan/preview', {
    data: {
      schema_id: 'layer3.plan_preview_request.v1',
      client_request_id: requestId('qual-aps-ui-plan-preview'),
      session_id: gateB.session_id,
      include_exclusions: true,
      preview_scope: 'owner_service_default',
    },
  }));
  const approval = await expectJson(await request.post('/api/v1/layer3/plan/approve', {
    data: {
      schema_id: 'layer3.plan_approval_request.v1',
      client_request_id: requestId('qual-aps-ui-plan-approve'),
      session_id: gateB.session_id,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      operator_confirmation: true,
      approval_scope: 'owner_service_default',
    },
  }));
  const selection = await expectJson(await request.post('/api/v1/layer3/execution/select', {
    data: {
      client_request_id: requestId('qual-aps-ui-execution-select'),
      session_id: gateB.session_id,
      analysis_plan_id: approval.analysis_plan_id,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      operator_reason: 'browser harness selected qualitative APS setup',
    },
  }));
  expect(selection.pass_run_ids).toHaveLength(1);
  const passRunId = selection.pass_run_ids[0];
  const start = await expectJson(await request.post('/api/v1/layer3/execution/start', {
    data: {
      client_request_id: requestId('qual-aps-ui-execution-start'),
      session_id: gateB.session_id,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      execution_mode: 'synchronous_single_pass',
      operator_reason: 'browser harness terminal qualitative APS setup',
    },
  }));
  expect(start.analysis_run_id).toBeNull();

  const status = await expectJson(await request.post('/api/v1/layer3/execution/result/status', {
    data: {
      client_request_id: requestId('qual-aps-ui-result-status'),
      session_id: gateB.session_id,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id,
      operator_view_mode: 'status_only',
    },
  }));
  const review = await expectJson(await request.post('/api/v1/layer3/execution/result/review', {
    data: {
      client_request_id: requestId('qual-aps-ui-result-review'),
      session_id: gateB.session_id,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id,
      operator_decision: 'approved',
      review_notes: 'Qualitative APS output is traceable for rendered downstream proof.',
    },
  }));
  return {
    seed,
    preflight,
    source,
    material,
    gateB,
    gateC,
    planPreview,
    approval,
    selection,
    start,
    status,
    review,
    passRunId,
  };
}

export async function prepareFailedLayer3Session(request) {
  const result = await prepareExecutedLayer3Session(request, '/__test/layer3/seed-failed-pass');
  expect(result.start.pass_run_status).toBe('failed');
  return result;
}

export async function prepareMissingOutputLayer3Session(request) {
  const result = await prepareExecutedLayer3Session(request, '/__test/layer3/seed-quant');
  expect(['completed', 'completed_with_warnings']).toContain(result.start.pass_run_status);
  const deleteResult = await expectJson(await request.post('/__test/layer3/delete-pass-output-manifest', {
    data: { pass_run_id: result.passRunId },
  }));
  expect(deleteResult.deleted).toBe(true);
  return result;
}

export async function prepareApprovedResultReviewQuantSession(request) {
  const result = await prepareExecutedLayer3Session(request);
  expect(['completed', 'completed_with_warnings']).toContain(result.start.pass_run_status);
  const { seed, planPreview, approval, start, passRunId } = result;

  const status = await expectJson(await request.post('/api/v1/layer3/execution/result/status', {
    data: {
      client_request_id: requestId('approved-review-result-status'),
      session_id: seed.session_id,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id ?? null,
      operator_view_mode: 'status_only',
    },
  }));
  expect(status.result_status_available).toBe(true);

  const review = await expectJson(await request.post('/api/v1/layer3/execution/result/review', {
    data: {
      client_request_id: requestId('approved-review-result-review'),
      session_id: seed.session_id,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id ?? null,
      operator_decision: 'approved',
      review_notes: 'Approved for server-backed restore test.',
    },
  }));
  expect(review.operator_decision).toBe('approved');

  return { ...result, status, review };
}

export async function prepareApprovedPackageReviewQuantSession(request) {
  const base = await prepareApprovedResultReviewQuantSession(request);
  const { seed, planPreview, approval, start, passRunId, review } = base;
  const sessionId = seed.session_id;

  const packagePreview = await expectJson(await request.post('/api/v1/layer3/package/review/preview', {
    data: {
      client_request_id: requestId('pkg-review-preview'),
      session_id: sessionId,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id ?? null,
      result_review_record_ref: review.review_record_ref,
    },
  }));
  expect(packagePreview.status).toBe('available');

  const packageKinds = packagePreview.candidate_package_kinds.map((c) => c.package_kind);

  const commit = await expectJson(await request.post('/api/v1/layer3/package/review/commit', {
    data: {
      client_request_id: requestId('pkg-review-commit'),
      session_id: sessionId,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id ?? null,
      result_review_record_ref: review.review_record_ref,
      package_review_preview_hash: packagePreview.package_review_preview_hash,
      expected_package_kinds: packageKinds,
    },
  }));
  expect(['committed', 'already_committed']).toContain(commit.status);

  const packageSubmit = await expectJson(await request.post('/api/v1/layer3/package/review/submit', {
    data: {
      client_request_id: requestId('pkg-review-submit'),
      session_id: sessionId,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id ?? null,
      result_review_record_ref: review.review_record_ref,
      package_review_preview_hash: commit.package_review_preview_hash,
      construction_basis_hash: commit.construction_basis_hash ?? null,
      reconciliation_record_id: commit.reconciliation_record_id,
      output_package_ids: commit.output_package_ids,
      payload_refs: commit.payload_refs,
      payload_hashes: commit.payload_hashes,
      expected_package_kinds: packageKinds,
      operator_decision: 'approved',
      decision_notes: 'Approved for server-backed package-review restore test.',
    },
  }));
  expect(packageSubmit.operator_decision).toBe('approved');
  expect(packageSubmit.package_review_state).toBe('package_review_approved');

  return { ...base, packagePreview, commit, packageSubmit };
}

export async function prepareApprovedPackageReviewRawMixedSession(request) {
  // Step 0: seed raw-mixed corpus authority
  const setup = await expectJson(await request.post('/__test/layer3/seed-raw-mixed'));
  expect(setup.schema_id).toBe('project6.review_browser_raw_mixed_seed_setup.v1');

  // Step 1: seed the mixed-corpus source
  const seed = await expectJson(await request.post('/api/v1/layer3/source/mixed-corpus/seed', {
    data: setup.seed_request,
  }));
  expect(seed.source_seed_state).toBe('seeded');
  expect(seed.dataset_version_ids).toHaveLength(2);
  expect(seed.aps_content_document_ids).toHaveLength(1);

  const dvids = seed.dataset_version_ids;
  const apsids = seed.aps_content_document_ids;

  // Step 2: preflight
  const preflight = await expectJson(await request.post('/api/v1/layer3/preflight', {
    data: {
      client_request_id: requestId('raw-mixed-preflight'),
      natural_language_intent: 'Review raw-mixed corpus dataset versions with APS content companion.',
      manual_constraints: {
        source_classes: ['dataset_version', 'aps_content_document'],
        dataset_version_ids: dvids,
        aps_content_document_ids: apsids,
      },
    },
  }));

  // Step 3: source-preview (dataset/aps ids FORBIDDEN here per spec)
  const source = await expectJson(await request.post('/api/v1/layer3/source-preview', {
    data: {
      client_request_id: requestId('raw-mixed-source-preview'),
      preflight_id: preflight.preflight_id,
      selected_source_classes: ['dataset_version', 'aps_content_document'],
    },
  }));

  // Step 4: material-preview
  const material = await expectJson(await request.post('/api/v1/layer3/material-preview', {
    data: {
      client_request_id: requestId('raw-mixed-material-preview'),
      preflight_id: preflight.preflight_id,
      source_set_id: source.source_set_id,
      source_candidate_ids: source.source_candidates.map((c) => c.source_candidate_id),
      dataset_version_ids: dvids,
      aps_content_document_ids: apsids,
      query_basis: {
        terms: ['raw', 'mixed', 'corpus'],
        filters: {
          dataset_version_ids: dvids,
          aps_content_document_ids: apsids,
        },
      },
    },
  }));
  expect(material.material_candidates).toHaveLength(3);

  // Step 5: gate-b/decision
  const gateB = await expectJson(await request.post('/api/v1/layer3/gate-b/decision', {
    data: {
      client_request_id: requestId('raw-mixed-gate-b'),
      preflight_id: preflight.preflight_id,
      source_set_id: source.source_set_id,
      material_preview_id: material.material_preview_id,
      material_preview_hash: material.material_preview_hash,
      candidate_decisions: material.material_candidates.map((c) => ({
        candidate_id: c.candidate_id,
        decision: 'approved',
        decision_basis: {
          source_ref: c.source_ref,
          query_basis: c.query_basis,
          provenance_ref: c.provenance_ref,
          source_identity: c.source_identity,
          source_provenance: c.source_provenance,
          payload: c.payload,
          load_summary: c.load_summary,
        },
      })),
    },
  }));
  const sessionId = gateB.session_id;
  // Attach session_id onto seed object so callers can use seed.session_id like other helpers
  seed.session_id = sessionId;

  // Step 6: gate-c/preview (dry run)
  await expectJson(await request.post('/api/v1/layer3/gate-c/preview', {
    data: {
      schema_id: 'layer3.gate_c_preview_request.v1',
      client_request_id: requestId('raw-mixed-gate-c-dry'),
      session_id: sessionId,
      commit_typing: false,
    },
  }));

  // Step 7: gate-c/preview (commit_typing=true)
  const gateC = await expectJson(await request.post('/api/v1/layer3/gate-c/preview', {
    data: {
      schema_id: 'layer3.gate_c_preview_request.v1',
      client_request_id: requestId('raw-mixed-gate-c'),
      session_id: sessionId,
      commit_typing: true,
    },
  }));
  expect(gateC.next_state).toBe('plan_preview_ready');

  // Step 8: plan/preview
  const planPreview = await expectJson(await request.post('/api/v1/layer3/plan/preview', {
    data: {
      schema_id: 'layer3.plan_preview_request.v1',
      client_request_id: requestId('raw-mixed-plan-preview'),
      session_id: sessionId,
      include_exclusions: true,
      preview_scope: 'owner_service_default',
    },
  }));

  // Step 9: plan/approve
  const approval = await expectJson(await request.post('/api/v1/layer3/plan/approve', {
    data: {
      schema_id: 'layer3.plan_approval_request.v1',
      client_request_id: requestId('raw-mixed-plan-approve'),
      session_id: sessionId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      operator_confirmation: true,
      approval_scope: 'owner_service_default',
    },
  }));

  // Step 10: execution/select
  const selection = await expectJson(await request.post('/api/v1/layer3/execution/select', {
    data: {
      client_request_id: requestId('raw-mixed-exec-select'),
      session_id: sessionId,
      analysis_plan_id: approval.analysis_plan_id,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      operator_reason: 'browser harness raw-mixed setup',
    },
  }));
  expect(selection.pass_run_ids).toHaveLength(1);
  const passRunId = selection.pass_run_ids[0];

  // Step 11: execution/start
  const start = await expectJson(await request.post('/api/v1/layer3/execution/start', {
    data: {
      client_request_id: requestId('raw-mixed-exec-start'),
      session_id: sessionId,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      execution_mode: 'synchronous_single_pass',
      operator_reason: 'browser harness raw-mixed terminal setup',
    },
  }));
  expect(['completed', 'completed_with_warnings']).toContain(start.pass_run_status);

  // Step 12: execution/result/status
  const resultStatus = await expectJson(await request.post('/api/v1/layer3/execution/result/status', {
    data: {
      client_request_id: requestId('raw-mixed-result-status'),
      session_id: sessionId,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id ?? null,
      operator_view_mode: 'status_only',
    },
  }));
  expect(resultStatus.result_status_available).toBe(true);

  // Step 13: execution/result/review
  const review = await expectJson(await request.post('/api/v1/layer3/execution/result/review', {
    data: {
      client_request_id: requestId('raw-mixed-result-review'),
      session_id: sessionId,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id ?? null,
      operator_decision: 'approved',
      review_notes: 'Approved for raw-mixed handoff delivery server-backed test.',
    },
  }));

  // Step 14: package/review/preview
  const packagePreview = await expectJson(await request.post('/api/v1/layer3/package/review/preview', {
    data: {
      client_request_id: requestId('raw-mixed-pkg-preview'),
      session_id: sessionId,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id ?? null,
      result_review_record_ref: review.review_record_ref,
    },
  }));
  expect(packagePreview.status).toBe('available');
  const packageKinds = packagePreview.candidate_package_kinds.map((c) => c.package_kind);

  // Step 15: package/review/commit
  const commit = await expectJson(await request.post('/api/v1/layer3/package/review/commit', {
    data: {
      client_request_id: requestId('raw-mixed-pkg-commit'),
      session_id: sessionId,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id ?? null,
      result_review_record_ref: review.review_record_ref,
      package_review_preview_hash: packagePreview.package_review_preview_hash,
      expected_package_kinds: packageKinds,
    },
  }));
  expect(['committed', 'already_committed']).toContain(commit.status);

  // Step 16: package/review/submit
  const packageSubmit = await expectJson(await request.post('/api/v1/layer3/package/review/submit', {
    data: {
      client_request_id: requestId('raw-mixed-pkg-submit'),
      session_id: sessionId,
      analysis_plan_id: approval.analysis_plan_id,
      pass_run_id: passRunId,
      preview_id: planPreview.preview_id,
      preview_hash: planPreview.preview_hash,
      analysis_run_id: start.analysis_run_id ?? null,
      result_review_record_ref: review.review_record_ref,
      package_review_preview_hash: commit.package_review_preview_hash,
      construction_basis_hash: commit.construction_basis_hash ?? null,
      reconciliation_record_id: commit.reconciliation_record_id,
      output_package_ids: commit.output_package_ids,
      payload_refs: commit.payload_refs,
      payload_hashes: commit.payload_hashes,
      expected_package_kinds: packageKinds,
      operator_decision: 'approved',
      decision_notes: 'Approved for raw-mixed handoff delivery server-backed test.',
    },
  }));
  expect(packageSubmit.package_review_state).toBe('package_review_approved');

  return {
    seed,
    planPreview,
    approval,
    passRunId,
    start,
    review,
    packagePreview,
    commit,
    packageSubmit,
    sessionId,
    packageKinds,
  };
}

export async function prepareRawMixedHandoffDeliverySession(request) {
  const base = await prepareApprovedPackageReviewRawMixedSession(request);
  const { seed, planPreview, approval, passRunId, start, review, commit, packageSubmit, sessionId, packageKinds } = base;

  // Step A: handoff/export/prepare
  const handoffPrepareData = {
    client_request_id: requestId('raw-mixed-handoff-prepare'),
    session_id: sessionId,
    analysis_plan_id: approval.analysis_plan_id,
    pass_run_id: passRunId,
    preview_id: planPreview.preview_id,
    preview_hash: planPreview.preview_hash,
    analysis_run_id: start.analysis_run_id ?? null,
    result_review_record_ref: review.review_record_ref,
    package_review_preview_hash: commit.package_review_preview_hash,
    reconciliation_record_id: commit.reconciliation_record_id,
    output_package_ids: commit.output_package_ids,
    payload_refs: commit.payload_refs,
    payload_hashes: commit.payload_hashes,
    package_review_submit_record_ref: packageSubmit.submit_record_ref,
    package_review_state: 'package_review_approved',
    package_review_submit_schema_id: packageSubmit.schema_id ?? 'layer3.package_review_submit.v1',
    handoff_target: 'internal_export_envelope',
    export_mode: 'prepare_only',
    operator_decision: 'authorize_prepare',
    decision_notes: 'Approved for raw-mixed handoff delivery server-backed test.',
    expected_package_kinds: packageKinds,
  };
  if (commit.construction_basis_hash != null) {
    handoffPrepareData.construction_basis_hash = commit.construction_basis_hash;
  }
  const handoffPrepare = await expectJson(await request.post('/api/v1/layer3/handoff/export/prepare', {
    data: handoffPrepareData,
  }));
  expect(handoffPrepare.handoff_export_state).toBe('handoff_export_prepared');
  // Safety rail: aps_handoff_enabled must NOT be true
  expect(handoffPrepare.aps_handoff_enabled).not.toBe(true);

  const envelopeRef = handoffPrepare.handoff_export_envelope.envelope_ref;

  // Step B: handoff/aps/dispatch
  const apsDispatchData = {
    client_request_id: requestId('raw-mixed-aps-dispatch'),
    session_id: sessionId,
    analysis_plan_id: approval.analysis_plan_id,
    pass_run_id: passRunId,
    preview_id: planPreview.preview_id,
    preview_hash: planPreview.preview_hash,
    analysis_run_id: start.analysis_run_id ?? null,
    result_review_record_ref: review.review_record_ref,
    package_review_preview_hash: commit.package_review_preview_hash,
    reconciliation_record_id: commit.reconciliation_record_id,
    output_package_ids: commit.output_package_ids,
    package_kinds: packageKinds,
    payload_refs: commit.payload_refs,
    payload_hashes: commit.payload_hashes,
    package_review_submit_record_ref: packageSubmit.submit_record_ref,
    package_review_state: 'package_review_approved',
    prepare_record_ref: handoffPrepare.prepare_record_ref,
    handoff_export_state: 'handoff_export_prepared',
    handoff_export_envelope_ref: envelopeRef,
    handoff_target: 'internal_export_envelope',
    export_mode: 'prepare_only',
    aps_handoff_target: 'aps_evidence_bundle',
    dispatch_mode: 'server_side_aps_handoff',
    operator_decision: 'dispatch_aps_handoff',
  };
  const apsDispatch = await expectJson(await request.post('/api/v1/layer3/handoff/aps/dispatch', {
    data: apsDispatchData,
  }));
  expect(apsDispatch.aps_handoff_state).toBe('aps_handoff_dispatched');

  // Step C: handoff/export/download/prepare (ALL fields from B's request + aps handoff fields)
  const downloadPrepareData = {
    ...apsDispatchData,
    client_request_id: requestId('raw-mixed-download-prepare'),
    aps_handoff_record_ref: apsDispatch.aps_handoff_record_ref,
    aps_handoff_state: 'aps_handoff_dispatched',
    aps_output_package_id: apsDispatch.aps_output_package_id,
    aps_output_package_kind: apsDispatch.aps_output_package_kind,
    aps_bundle_ref: apsDispatch.aps_bundle_ref,
    aps_bundle_id: apsDispatch.aps_bundle_id,
    aps_schema_id: apsDispatch.aps_schema_id,
    export_download_target: 'aps_evidence_bundle_download_reference',
    download_mode: 'reference_only_prepare',
    operator_decision: 'prepare_external_export_download',
  };
  const downloadPrepare = await expectJson(await request.post('/api/v1/layer3/handoff/export/download/prepare', {
    data: downloadPrepareData,
  }));
  expect(downloadPrepare.external_export_download_state).toBe('external_export_download_prepared');

  // Step D: handoff/export/download/signed-reference/generate
  // ALL fields from C's request PLUS aps_bundle_hash/size (from downloadPrepare response),
  // external_export_download_record_ref, export_download_descriptor_ref, delivery_mode, operator_decision
  const signedReferenceData = {
    ...downloadPrepareData,
    client_request_id: requestId('raw-mixed-signed-ref'),
    aps_bundle_hash: downloadPrepare.source_artifact_hash,
    aps_bundle_size_bytes: downloadPrepare.source_artifact_size_bytes,
    external_export_download_record_ref: downloadPrepare.external_export_download_record_ref,
    export_download_descriptor_ref: downloadPrepare.export_download_descriptor_ref,
    external_export_download_state: 'external_export_download_prepared',
    delivery_mode: 'same_origin_artifact_stream',
    operator_decision: 'deliver_external_export_download',
  };
  const signedReference = await expectJson(
    await request.post('/api/v1/layer3/handoff/export/download/signed-reference/generate', {
      data: signedReferenceData,
    }),
  );
  expect(signedReference.signed_reference_state).toBe('external_export_download_signed_reference_ready');

  return {
    ...base,
    handoffPrepare,
    apsDispatch,
    downloadPrepare,
    signedReference,
  };
}

export async function attachSessionToWorkbench(page, sessionId, sourceClasses = ['dataset_version']) {
  // init() loads /bootstrap asynchronously and page.goto resolves on `load`,
  // before that fetch settles. The session-recovery anchor embeds the
  // state-action contract signature derived from State.bootstrap; if we persist
  // it while bootstrap is still null, the anchor gets a null signature and is
  // rejected on reload (no session recovery fetch fires). Wait for bootstrap so
  // the anchor carries the real contract signature, matching the reloaded page.
  await page.waitForFunction(() => typeof State !== 'undefined' && !!State.bootstrap);
  await page.evaluate(({ session_id, source_classes }) => {
    State.gateB = {
      session_id,
      authority_rail: {
        session_id,
        current_gate: 'execution',
        persistence_mode: 'durable_layer3_control',
        source_authority: { source_classes },
        approved_material_count: 1,
        denied_material_count: 0,
        isolated_material_count: 0,
        flagged_material_count: 0,
        typing_status: 'committed',
        execution_enabled: false,
        package_review_enabled: false,
        downstream_unavailable: ['results', 'package', 'handoff'],
      },
    };
    State.gateC = {
      authority_rail: State.gateB.authority_rail,
    };
    State.planPreview = null;
    State.planApproval = null;
    State.planRevision = null;
    clearResultReviewState();
    renderAll();
    persistSessionRecoveryAnchor('test-harness');
  }, { session_id: sessionId, source_classes: sourceClasses });
}
