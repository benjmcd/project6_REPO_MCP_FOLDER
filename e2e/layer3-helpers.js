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

export async function attachSessionToWorkbench(page, sessionId, sourceClasses = ['dataset_version']) {
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
  }, { session_id: sessionId, source_classes: sourceClasses });
}
