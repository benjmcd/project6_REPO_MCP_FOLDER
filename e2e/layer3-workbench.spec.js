import { test, expect } from '@playwright/test';

async function expectJson(response) {
  expect(response.status()).toBe(200);
  return response.json();
}

async function expectJsonStatus(response, status) {
  expect(response.status()).toBe(status);
  return response.json();
}

function requestId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function expectOnlyPayloadKeys(payload, allowedKeys) {
  expect(Object.keys(payload).sort()).toEqual([...allowedKeys].sort());
}

async function prepareExecutedLayer3Session(request) {
  const seed = await expectJson(await request.post('/__test/layer3/seed-quant'));
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

async function attachSessionToWorkbench(page, sessionId) {
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

test('Layer 3 workbench completes the first-slice operator path without enabling downstream gates', async ({ page }) => {
  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  const bootstrap = await expectJson(await bootstrapResponsePromise);

  expect(bootstrap.features.analysis_execution).toBe(false);
  expect(bootstrap.features.plan_preview).toBe(true);
  expect(bootstrap.features.rag_vector_retrieval).toBe(false);
  expect(bootstrap.features.typing_override_enabled).toBe(false);

  await expect(page.getByRole('heading', { name: 'Layer 3 Workbench' })).toBeVisible();
  await expect(page.locator('#authority-rail')).toContainText('not_committed');
  await expect(page.locator('[data-step="plan"]')).toBeDisabled();
  await expect(page.locator('[data-step="execution"]')).toBeDisabled();
  await expect(page.locator('[data-step="results"]')).toBeDisabled();
  await expect(page.locator('[data-step="package"]')).toBeDisabled();
  await expect(page.locator('#result-review-refresh')).toBeDisabled();
  await expect(page.locator('#result-status-inspect')).toBeDisabled();
  await expect(page.locator('#result-review-submit')).toBeDisabled();
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Start Execution' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Rerun' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Export' })).toHaveCount(0);
  await expect(page.locator('#unavailable-list')).toContainText('plan');
  await expect(page.locator('#unavailable-list')).toContainText('execution');

  const preflightResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/preflight'));
  const sourceResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/source-preview'));
  const materialResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/material-preview'));

  await page.locator('#layer3-intent').fill('Review deterministic dataset and APS document material for bounded typing.');
  await page.locator('#run-preflight').click();

  const [preflight, source, material] = await Promise.all([
    expectJson(await preflightResponsePromise),
    expectJson(await sourceResponsePromise),
    expectJson(await materialResponsePromise),
  ]);
  expect(preflight.eligible_for_source_selection).toBe(true);
  expect(source.source_candidates).toHaveLength(2);
  expect(material.material_candidates).toHaveLength(2);

  const rows = page.locator('#material-ledger-body tr[data-candidate-id]');
  await expect(rows).toHaveCount(2);
  await rows.nth(1).locator('.decision-select').selectOption('denied');
  await rows.nth(1).locator('.reason-input').fill('Deferred outside the first slice.');

  const gateBResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/gate-b/decision'));
  await page.locator('#gate-b-submit').click();
  const gateB = await expectJson(await gateBResponsePromise);
  expect(gateB.authority_rail.approved_material_count).toBe(1);
  expect(gateB.authority_rail.denied_material_count).toBe(1);

  await expect(page.locator('#authority-rail')).toContainText('durable_layer3_control');
  await expect(page.locator('#context-list')).toContainText(gateB.session_id);
  await expect(page.locator('#gate-c-preview')).toBeEnabled();

  const gateCResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/gate-c/preview'));
  await page.locator('#gate-c-preview').click();
  const gateC = await expectJson(await gateCResponsePromise);
  expect(gateC.override_allowed).toBe(false);
  expect(gateC.typing_records).toHaveLength(1);
  expect(gateC.typing_records[0].authoritative).toBe(false);

  await expect(page.locator('#gate-c-panel .typing-card')).toHaveCount(1);
  await expect(page.locator('#gate-c-panel')).toContainText('Authoritative: no');
  await expect(page.locator('[data-step="plan"]')).toBeDisabled();

  const gateCCommitResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/gate-c/preview'));
  await page.locator('#gate-c-commit').click();
  const gateCCommit = await expectJson(await gateCCommitResponsePromise);
  expect(gateCCommit.next_state).toBe('plan_preview_ready');
  expect(gateCCommit.typing_records[0].authoritative).toBe(true);

  await expect(page.locator('#gate-c-panel')).toContainText('Authoritative: yes');
  await expect(page.locator('#gate-c-preview')).toBeDisabled();
  await expect(page.locator('[data-step="plan"]')).toBeEnabled();
  await expect(page.locator('#plan-preview')).toBeEnabled();

  const planPreviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/plan/preview'));
  await page.locator('#plan-preview').click();
  const planPreview = await expectJsonStatus(await planPreviewResponsePromise, 409);
  expect(planPreview.error_code).toBe('no_admissible_plan');

  await expect(page.locator('#plan-panel')).toContainText('Plan Preview Blocked');
  await expect(page.locator('#plan-panel')).toContainText('no_admissible_plan');
  await expect(page.locator('#unavailable-list')).toContainText('package');
  await expect(page.locator('[data-step="execution"]')).toBeDisabled();
  await expect(page.locator('[data-step="package"]')).toBeDisabled();
});

test('Layer 3 workbench approves an admissible plan without starting execution', async ({ page, request }) => {
  const seed = await expectJson(await request.post('/__test/layer3/seed-quant'));

  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);

  await page.evaluate((sessionId) => {
    State.gateB = {
      session_id: sessionId,
      authority_rail: {
        session_id: sessionId,
        current_gate: 'plan',
        persistence_mode: 'durable_layer3_control',
        source_authority: { source_classes: ['dataset_version'] },
        approved_material_count: 1,
        denied_material_count: 0,
        isolated_material_count: 0,
        flagged_material_count: 0,
        typing_status: 'committed',
        execution_enabled: false,
        package_review_enabled: false,
        downstream_unavailable: ['execution', 'results', 'package'],
      },
    };
    State.gateC = {
      authority_rail: {
        session_id: sessionId,
        current_gate: 'plan',
        persistence_mode: 'durable_layer3_control',
        source_authority: { source_classes: ['dataset_version'] },
        approved_material_count: 1,
        denied_material_count: 0,
        isolated_material_count: 0,
        flagged_material_count: 0,
        typing_status: 'committed',
        execution_enabled: false,
        package_review_enabled: false,
        downstream_unavailable: ['execution', 'results', 'package'],
      },
    };
    State.planPreview = null;
    State.planApproval = null;
    State.planRevision = null;
    renderAll();
  }, seed.session_id);

  await expect(page.locator('#plan-preview')).toBeEnabled();
  await expect(page.locator('#plan-approve')).toBeDisabled();

  const planPreviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/plan/preview'));
  await page.locator('#plan-preview').click();
  const planPreview = await expectJson(await planPreviewResponsePromise);
  expect(planPreview.preview_hash).toBeTruthy();
  await expect(page.locator('#plan-approve')).toBeEnabled();

  const approvalResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/plan/approve'));
  await page.locator('#plan-approve').click();
  const approval = await expectJson(await approvalResponsePromise);
  expect(approval.next_state).toBe('plan_approved');
  expect(approval.approval_only).toBe(true);
  expect(approval.execution_started).toBe(false);
  expect(approval.approved_plan.would_create_pass_runs).toBe(false);
  expect(approval.approved_plan.would_execute_passes).toBe(false);

  await expect(page.locator('#plan-panel')).toContainText('approved');
  await expect(page.locator('#plan-panel')).toContainText('not started');
  await expect(page.locator('#plan-approve')).toBeDisabled();
  await expect(page.locator('[data-step="execution"]')).toBeDisabled();
  await expect(page.locator('[data-step="results"]')).toBeDisabled();
  await expect(page.locator('[data-step="package"]')).toBeDisabled();
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expect(page.locator('#unavailable-list')).toContainText('execution');
  await expect(page.locator('#unavailable-list')).toContainText('package');
});

test('Layer 3 workbench records selected-pass result review only after status authority', async ({ page, request }) => {
  const setup = await prepareExecutedLayer3Session(request);

  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);
  await attachSessionToWorkbench(page, setup.seed.session_id);

  await expect(page.locator('#result-review-refresh')).toBeEnabled();
  await expect(page.locator('#result-status-inspect')).toBeDisabled();
  await expect(page.locator('#result-review-submit')).toBeDisabled();

  const summaryResponsePromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#result-review-refresh').click();
  const summary = await expectJson(await summaryResponsePromise);
  expect(summary.execution_selection.selected).toBe(true);
  expect(summary.execution_selection.pass_run_ids).toEqual([setup.passRunId]);
  expect(summary.execution_selection.analysis_plan_id).toBe(setup.approval.analysis_plan_id);

  await expect(page.locator('#result-status-inspect')).toBeEnabled();
  await expect(page.locator('#result-review-submit')).toBeDisabled();
  await expect(page.locator('[data-step="execution"]')).toBeEnabled();
  await expect(page.locator('[data-step="results"]')).toBeEnabled();
  await expect(page.locator('[data-step="package"]')).toBeDisabled();

  const statusRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/execution/result/status'));
  const statusResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/execution/result/status'));
  await page.locator('#result-status-inspect').click();
  const statusRequest = await statusRequestPromise;
  const statusPayload = statusRequest.postDataJSON();
  const expectedStatusKeys = [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'operator_view_mode',
  ];
  if (statusPayload.analysis_run_id) expectedStatusKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(statusPayload, expectedStatusKeys);
  expect(statusPayload.session_id).toBe(setup.seed.session_id);
  expect(statusPayload.analysis_plan_id).toBe(setup.approval.analysis_plan_id);
  expect(statusPayload.pass_run_id).toBe(setup.passRunId);
  expect(statusPayload.preview_id).toBe(setup.planPreview.preview_id);
  expect(statusPayload.preview_hash).toBe(setup.planPreview.preview_hash);
  expect(statusPayload.operator_view_mode).toBe('status_only');
  expect(statusPayload).not.toHaveProperty('package');
  expect(statusPayload).not.toHaveProperty('handoff');
  expect(statusPayload).not.toHaveProperty('rerun');
  expect(statusPayload).not.toHaveProperty('pass_run_ids');

  const status = await expectJson(await statusResponsePromise);
  expect(status.result_status_available).toBe(true);
  await expect(page.locator('#result-review-panel')).toContainText('result_review_ui_review_ready');

  await page.locator('#result-review-decision').selectOption('changes_requested');
  await expect(page.locator('#result-review-submit')).toBeDisabled();
  await page.locator('#result-review-notes').fill('Operator requires a follow-up caveat before packaging.');
  await expect(page.locator('#result-review-submit')).toBeEnabled();

  const reviewRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/execution/result/review'));
  const reviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/execution/result/review'));
  await page.locator('#result-review-submit').click();
  const reviewRequest = await reviewRequestPromise;
  const reviewPayload = reviewRequest.postDataJSON();
  const expectedReviewKeys = [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'operator_decision',
    'review_notes',
  ];
  if (reviewPayload.analysis_run_id) expectedReviewKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(reviewPayload, expectedReviewKeys);
  expect(reviewPayload.operator_decision).toBe('changes_requested');
  expect(reviewPayload.review_notes).toContain('follow-up caveat');
  expect(reviewPayload).not.toHaveProperty('package');
  expect(reviewPayload).not.toHaveProperty('handoff');
  expect(reviewPayload).not.toHaveProperty('rerun');
  expect(reviewPayload).not.toHaveProperty('pass_run_ids');
  expect(reviewPayload).not.toHaveProperty('artifact_manifest');

  const review = await expectJson(await reviewResponsePromise);
  expect(review.status).toBe('recorded');
  expect(review.operator_decision).toBe('changes_requested');
  expect(review.package_review_enabled).toBe(false);
  expect(review.handoff_enabled).toBe(false);
  expect(review.downstream_unavailable).toEqual(['package', 'handoff', 'package_review']);

  await expect(page.locator('#result-review-panel')).toContainText('result_review_ui_recorded');
  await expect(page.locator('#result-review-panel')).toContainText('changes_requested');
  await expect(page.locator('#result-review-panel')).toContainText('package');
  await expect(page.locator('#result-review-panel')).toContainText('handoff');
  await expect(page.locator('#result-review-submit')).toBeDisabled();
  await expect(page.locator('[data-step="package"]')).toBeDisabled();
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeDisabled();
});

test('Layer 3 workbench commits a package set and submits bounded package review after approved result review', async ({ page, request }) => {
  const setup = await prepareExecutedLayer3Session(request);

  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);
  await attachSessionToWorkbench(page, setup.seed.session_id);

  const summaryResponsePromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#result-review-refresh').click();
  await expectJson(await summaryResponsePromise);

  const statusResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/execution/result/status'));
  await page.locator('#result-status-inspect').click();
  const status = await expectJson(await statusResponsePromise);
  expect(status.result_status_available).toBe(true);

  await expect(page.locator('#result-review-submit')).toBeEnabled();
  const reviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/execution/result/review'));
  const postReviewSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#result-review-submit').click();
  const review = await expectJson(await reviewResponsePromise);
  expect(review.review_state).toBe('execution_result_review_approved');
  await expectJson(await postReviewSummaryPromise);

  await expect(page.locator('#package-review-preview-inspect')).toBeEnabled();
  const previewRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/package/review/preview'));
  const previewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/preview'));
  await page.locator('#package-review-preview-inspect').click();
  const previewRequest = await previewRequestPromise;
  const previewPayload = previewRequest.postDataJSON();
  const expectedPreviewKeys = [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'result_review_record_ref',
  ];
  if (previewPayload.analysis_run_id) expectedPreviewKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(previewPayload, expectedPreviewKeys);
  expect(previewPayload.session_id).toBe(setup.seed.session_id);
  expect(previewPayload.analysis_plan_id).toBe(setup.approval.analysis_plan_id);
  expect(previewPayload.pass_run_id).toBe(setup.passRunId);
  expect(previewPayload.preview_id).toBe(setup.planPreview.preview_id);
  expect(previewPayload.preview_hash).toBe(setup.planPreview.preview_hash);
  expect(previewPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(previewPayload).not.toHaveProperty('package');
  expect(previewPayload).not.toHaveProperty('handoff');
  expect(previewPayload).not.toHaveProperty('rerun');
  expect(previewPayload).not.toHaveProperty('rewrite_output');

  const preview = await expectJson(await previewResponsePromise);
  expect(preview.schema_id).toBe('layer3.package_review_preview.v1');
  expect(preview.status).toBe('available');
  expect(preview.package_review_preview_enabled).toBe(true);
  expect(preview.package_commit_enabled).toBe(true);
  expect(preview.package_review_enabled).toBe(false);
  expect(preview.package_review_preview_hash).toEqual(expect.any(String));
  expect(preview.candidate_package_kinds.map((item) => item.package_kind)).toEqual([
    'canonical_internal',
    'user_facing',
    'review_facing',
  ]);
  expect(preview.downstream_unavailable).toEqual(['package_review_submit', 'handoff', 'export']);

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_preview_ready');
  await expect(page.locator('#package-review-preview-panel')).toContainText('canonical_internal');
  await expect(page.locator('#package-review-preview-panel')).toContainText('user_facing');
  await expect(page.locator('#package-review-preview-panel')).toContainText('review_facing');
  await expect(page.locator('#package-review-preview-panel')).toContainText('package review submit');
  await expect(page.locator('#package-review-preview-panel')).toContainText('handoff');
  await expect(page.locator('#package-construction-commit')).toBeEnabled();
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expect(page.locator('[data-step="package"]')).toBeEnabled();

  const commitRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/package/review/commit'));
  const commitResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/commit'));
  const postCommitSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#package-construction-commit').click();
  const commitRequest = await commitRequestPromise;
  const commitPayload = commitRequest.postDataJSON();
  const expectedCommitKeys = [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'result_review_record_ref',
    'package_review_preview_hash',
    'expected_package_kinds',
  ];
  if (commitPayload.analysis_run_id) expectedCommitKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(commitPayload, expectedCommitKeys);
  expect(commitPayload.package_review_preview_hash).toBe(preview.package_review_preview_hash);
  expect(commitPayload.expected_package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
  expect(commitPayload).not.toHaveProperty('package');
  expect(commitPayload).not.toHaveProperty('handoff');
  expect(commitPayload).not.toHaveProperty('export');
  expect(commitPayload).not.toHaveProperty('package_payload');

  const commit = await expectJson(await commitResponsePromise);
  expect(commit.schema_id).toBe('layer3.package_construction_commit.v1');
  expect(commit.status).toBe('committed');
  expect(commit.next_state).toBe('package_constructed');
  expect(commit.package_review_submit_enabled).toBe(true);
  expect(commit.handoff_enabled).toBe(false);
  expect(commit.downstream_unavailable).toEqual(['handoff', 'export']);
  expect(commit.output_packages).toHaveLength(3);
  await expectJson(await postCommitSummaryPromise);

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_constructed');
  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_submit_ready');
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeEnabled();

  const submitRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/package/review/submit'));
  const submitResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/submit'));
  const postSubmitSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#package-review-submit').click();
  const submitRequest = await submitRequestPromise;
  const submitPayload = submitRequest.postDataJSON();
  const expectedSubmitKeys = [
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
    'payload_hashes',
    'operator_decision',
    'decision_notes',
    'expected_package_kinds',
  ];
  if (submitPayload.analysis_run_id) expectedSubmitKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(submitPayload, expectedSubmitKeys);
  expect(submitPayload.operator_decision).toBe('approved');
  expect(submitPayload.decision_notes).toBe('');
  expect(submitPayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect([...submitPayload.output_package_ids].sort()).toEqual([...commit.output_packages.map((item) => item.output_package_id)].sort());
  expect(submitPayload.payload_hashes).toEqual(commit.payload_hashes);
  expect(submitPayload.expected_package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
  expect(submitPayload).not.toHaveProperty('package');
  expect(submitPayload).not.toHaveProperty('handoff');
  expect(submitPayload).not.toHaveProperty('export');
  expect(submitPayload).not.toHaveProperty('package_payload');
  expect(submitPayload).not.toHaveProperty('rebuild_package');

  const submit = await expectJson(await submitResponsePromise);
  expect(submit.schema_id).toBe('layer3.package_review_submit.v1');
  expect(submit.status).toBe('submitted');
  expect(submit.package_review_state).toBe('package_review_approved');
  expect(submit.operator_decision).toBe('approved');
  expect(submit.package_review_submit_enabled).toBe(false);
  expect(submit.handoff_enabled).toBe(false);
  expect(submit.export_enabled).toBe(false);
  expect(submit.downstream_unavailable).toEqual(['handoff', 'export']);
  await expectJson(await postSubmitSummaryPromise);

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_approved');
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Create Package' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Export' })).toHaveCount(0);
});

test('Layer 3 workbench can request plan revision without starting execution', async ({ page, request }) => {
  const seed = await expectJson(await request.post('/__test/layer3/seed-quant'));

  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);

  await page.evaluate((sessionId) => {
    State.gateB = {
      session_id: sessionId,
      authority_rail: {
        session_id: sessionId,
        current_gate: 'plan',
        persistence_mode: 'durable_layer3_control',
        source_authority: { source_classes: ['dataset_version'] },
        approved_material_count: 1,
        denied_material_count: 0,
        isolated_material_count: 0,
        flagged_material_count: 0,
        typing_status: 'committed',
        execution_enabled: false,
        package_review_enabled: false,
        downstream_unavailable: ['execution', 'results', 'package'],
      },
    };
    State.gateC = {
      authority_rail: {
        session_id: sessionId,
        current_gate: 'plan',
        persistence_mode: 'durable_layer3_control',
        source_authority: { source_classes: ['dataset_version'] },
        approved_material_count: 1,
        denied_material_count: 0,
        isolated_material_count: 0,
        flagged_material_count: 0,
        typing_status: 'committed',
        execution_enabled: false,
        package_review_enabled: false,
        downstream_unavailable: ['execution', 'results', 'package'],
      },
    };
    State.planPreview = null;
    State.planApproval = null;
    State.planRevision = null;
    renderAll();
  }, seed.session_id);

  await expect(page.locator('#plan-preview')).toBeEnabled();
  await expect(page.locator('#plan-reject')).toBeDisabled();
  await expect(page.locator('#plan-request-revision')).toBeDisabled();

  const planPreviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/plan/preview'));
  await page.locator('#plan-preview').click();
  const planPreview = await expectJson(await planPreviewResponsePromise);
  expect(planPreview.preview_hash).toBeTruthy();

  await expect(page.locator('#plan-reject')).toBeEnabled();
  await expect(page.locator('#plan-request-revision')).toBeEnabled();
  await expect(page.locator('#plan-approve')).toBeEnabled();

  let releaseRevisionRequest;
  await page.route('**/api/v1/layer3/plan/revise', async (route) => {
    await new Promise((resolve) => {
      releaseRevisionRequest = resolve;
    });
    await route.continue();
  });

  const revisionResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/plan/revise'));
  await page.locator('#plan-request-revision').click();
  await expect(page.locator('#plan-reject')).toBeDisabled();
  await expect(page.locator('#plan-request-revision')).toBeDisabled();
  await expect.poll(() => Boolean(releaseRevisionRequest)).toBe(true);
  releaseRevisionRequest();
  const revision = await expectJson(await revisionResponsePromise);
  expect(revision.next_state).toBe('plan_revision_requested');
  expect(revision.revision_control_only).toBe(true);
  expect(revision.execution_started).toBe(false);
  expect(revision.downstream_unavailable).toEqual(['execution', 'results', 'package']);

  await expect(page.locator('#plan-panel')).toContainText('revision requested');
  await expect(page.locator('#plan-panel')).toContainText('not started');
  await expect(page.locator('#plan-preview')).toBeDisabled();
  await expect(page.locator('#plan-reject')).toBeDisabled();
  await expect(page.locator('#plan-request-revision')).toBeDisabled();
  await expect(page.locator('#plan-approve')).toBeDisabled();
  await expect(page.locator('[data-step="execution"]')).toBeDisabled();
  await expect(page.locator('[data-step="results"]')).toBeDisabled();
  await expect(page.locator('[data-step="package"]')).toBeDisabled();
  await expect(page.locator('#unavailable-list')).toContainText('execution');
  await expect(page.locator('#unavailable-list')).toContainText('package');
});
