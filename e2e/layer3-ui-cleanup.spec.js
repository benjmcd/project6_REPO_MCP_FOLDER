import { test, expect } from '@playwright/test';

async function openLayer3(page) {
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => typeof State === 'object' && typeof renderAll === 'function');
}

test('Layer 3 approved plan panel posts admitted cancel request and renders 409 guidance', async ({ page }) => {
  await openLayer3(page);

  await page.evaluate(() => {
    State.sessionSummary = { session_id: 'cancel-session' };
    State.planPreview = null;
    State.planRevision = null;
    State.planApprovalError = null;
    State.planApproval = {
      schema_id: 'layer3.plan_approval_result.v1',
      session_id: 'cancel-session',
      analysis_plan_id: 'analysis-plan-cancel',
      approved_at: '2026-06-26T17:00:00Z',
      execution_started: false,
      approved_plan: {
        source_preview_id: 'source-preview-cancel',
        source_preview_hash: 'b'.repeat(64),
        approved_sets: [],
        excluded_sets: [],
        planned_passes: [],
        warnings: [],
        owner_service_basis: { mode: 'owner_service_default' },
      },
    };
    renderAll();
  });

  let cancelPayload = null;
  await page.route('**/api/v1/layer3/plan/approved/cancel', async (route) => {
    cancelPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({
        schema_id: 'layer3.workbench_error.v1',
        error_code: 'approved_plan_cancel_downstream_state_exists',
        message: 'Downstream state already exists for this approved plan.',
        next_allowed_actions: ['start_new_session_for_replacement_plan'],
      }),
    });
  });

  const button = page.getByRole('button', { name: 'Cancel approved plan (no replacement)' });
  await expect(button).toBeEnabled();
  await button.click();

  expect(cancelPayload.client_request_id).toBeTruthy();
  expect(cancelPayload.session_id).toBe('cancel-session');
  expect(cancelPayload.analysis_plan_id).toBe('analysis-plan-cancel');
  expect(cancelPayload.source_preview_id).toBe('source-preview-cancel');
  expect(cancelPayload.source_preview_hash).toBe('b'.repeat(64));
  expect(cancelPayload.operator_decision).toBe('cancel_approved_plan_without_replacement');
  expect(cancelPayload.approved_plan_supersession).toBeUndefined();
  expect(cancelPayload.replacement_plan).toBeUndefined();

  const panel = page.locator('#plan-panel');
  await expect(panel).toContainText('approved_plan_cancel_downstream_state_exists');
  await expect(panel).toContainText('start_new_session_for_replacement_plan');
});

test('Layer 3 SEC XBRL controls are disabled until controlled value reveal posture is enabled', async ({ page }) => {
  await openLayer3(page);

  await page.evaluate(() => {
    State.secXbrlRuntimePosture = {
      posture_state: 'sec_xbrl_runtime_posture_default_off',
      runtime_flags: { controlled_value_reveal_submit_enabled: false },
    };
    State.secXbrlOperatorReviewDecisionSubmitInput = {
      workflowId: 'sec-xbrl-operator-review-workflow-test',
      workflowBasisHash: '',
      reviewDecision: 'approved',
      decisionReasonCode: 'ready_for_next_freeze',
      decisionNotes: '',
    };
    State.secXbrlValueRevealAuthorityPrepareInput = {
      decisionId: 'sec-xbrl-operator-review-decision-test',
      decisionBasisHash: 'a'.repeat(64),
      operatorAttestation: '',
    };
    State.secXbrlControlledValueRevealSubmitInput = {
      authorityReceiptId: 'sec-xbrl-value-reveal-authority-test',
      authorityBasisHash: 'b'.repeat(64),
      operatorRevealConfirmation: true,
      maxRecords: '1',
    };
    renderSecXbrlOperatorReviewDecisionSubmitPanel();
    renderSecXbrlControlledValueRevealPanel();
  });

  await expect(page.locator('#sec-xbrl-operator-review-decision-submit')).toBeDisabled();
  await expect(page.locator('#sec-xbrl-value-reveal-authority-prepare-submit')).toBeDisabled();
  await expect(page.locator('#sec-xbrl-controlled-value-reveal-submit')).toBeDisabled();
  await expect(page.locator('#sec-xbrl-controlled-value-reveal-panel')).toContainText(
    'controlled_value_reveal_submit_enabled is not enabled',
  );
});
