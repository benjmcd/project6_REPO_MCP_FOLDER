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

export async function attachSessionToWorkbench(page, sessionId) {
  await page.evaluate((session_id) => {
    State.gateB = {
      session_id,
      authority_rail: {
        session_id,
        current_gate: 'execution',
        persistence_mode: 'durable_layer3_control',
        source_authority: { source_classes: ['dataset_version'] },
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
  }, sessionId);
}
