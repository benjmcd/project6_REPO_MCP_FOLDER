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

test('Layer 3 workbench keeps Layer 3-only theme preferences page-local', async ({ page }) => {
  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    localStorage.setItem('nrc_aps_review_theme', 'workbench');
    localStorage.removeItem('layer3_workbench_theme');
  });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'system');
  await expect(page.locator('#theme-selector')).toHaveValue('system');
  const sharedAfterNrc = await page.evaluate(() => localStorage.getItem('nrc_aps_review_theme'));
  expect(sharedAfterNrc).toBeNull();

  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    localStorage.setItem('nrc_aps_review_theme', 'workbench');
    localStorage.removeItem('layer3_workbench_theme');
  });

  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await expect(page.locator('#theme-selector')).toHaveValue('workbench');

  const storage = await page.evaluate(() => ({
    sharedTheme: localStorage.getItem('nrc_aps_review_theme'),
    layer3Theme: localStorage.getItem('layer3_workbench_theme'),
  }));
  expect(storage).toEqual({
    sharedTheme: null,
    layer3Theme: 'workbench',
  });

  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'system');
  await expect(page.locator('#theme-selector')).toHaveValue('system');

  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'dark');
  const storageAfterLayer3Dark = await page.evaluate(() => ({
    sharedTheme: localStorage.getItem('nrc_aps_review_theme'),
    layer3Theme: localStorage.getItem('layer3_workbench_theme'),
  }));
  expect(storageAfterLayer3Dark).toEqual({
    sharedTheme: 'dark',
    layer3Theme: null,
  });

  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('light');
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'light');
  await expect(page.locator('#theme-selector')).toHaveValue('light');
  const storageAfterNrcLight = await page.evaluate(() => ({
    sharedTheme: localStorage.getItem('nrc_aps_review_theme'),
    layer3Theme: localStorage.getItem('layer3_workbench_theme'),
  }));
  expect(storageAfterNrcLight).toEqual({
    sharedTheme: 'light',
    layer3Theme: null,
  });

  await page.locator('#theme-selector').selectOption('workbench');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await expect(page.locator('#theme-selector')).toHaveValue('workbench');
  const storageAfterWorkbenchWithSharedTheme = await page.evaluate(() => ({
    sharedTheme: localStorage.getItem('nrc_aps_review_theme'),
    layer3Theme: localStorage.getItem('layer3_workbench_theme'),
  }));
  expect(storageAfterWorkbenchWithSharedTheme).toEqual({
    sharedTheme: 'light',
    layer3Theme: 'workbench',
  });

  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'light');
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');

  await Promise.all([
    page.waitForURL('**/review/layer3/static/claude.html'),
    page.locator('#theme-selector').selectOption('claude'),
  ]);
  await expect(page).toHaveTitle(/Layer 3 Workbench.*Prototype/);
  await expect(page.locator('.app-shell')).toBeVisible();
  await expect(page.locator('.chrome-bar')).toHaveCount(0);
  await expect(page.locator('header.app-header.layer3-header')).toBeVisible();
  await expect(page.locator('a.back-link')).toHaveAttribute('href', '/review/nrc-aps');
  await expect(page.locator('.proto-badge')).toHaveText('PROTOTYPE');
  await expect(page.locator('#theme-selector')).toHaveValue('claude');
  await page.locator('[data-screen="overview"]').click();
  await expect(page.locator('#ov-sources')).toContainText('APS content document');
  await page.locator('[data-screen="3a"]').click();
  await expect(page.locator('#detail-3a-gate')).toContainText('aps-doc-operator-evidence-001');
  await expect(page.locator('#detail-3a-gate')).toContainText('ML26001A001');
  await expect(page.locator('#detail-3a-gate')).toContainText('aps_content_units_v2');
  await expect(page.locator('#detail-3a-gate')).toContainText('traceable_aps_content_document');
  await expect(page.locator('#detail-3a-status')).toContainText('21');
  const storageAfterClaude = await page.evaluate(() => ({
    sharedTheme: localStorage.getItem('nrc_aps_review_theme'),
    layer3Theme: localStorage.getItem('layer3_workbench_theme'),
  }));
  expect(storageAfterClaude).toEqual({
    sharedTheme: 'light',
    layer3Theme: 'workbench',
  });

  await Promise.all([
    page.waitForURL('**/review/layer3'),
    page.locator('#theme-selector').selectOption('workbench'),
  ]);
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await expect(page.locator('#theme-selector')).toHaveValue('workbench');

  await page.locator('#theme-selector').selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'dark');
});

test('Layer 3 workbench clears schema-id-only Gate B drafts after contract signature hardening', async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('layer3_workbench_gate_b_draft_v1', JSON.stringify({
      schema_id: 'layer3.gate_b_draft_snapshot.v1',
      schema_version: 1,
      draft_authority: 'browser_restore_only_server_revalidated_on_commit',
      client_request_id: 'stale-schema-id-only-draft',
      state_action_contract_schema_id: 'layer3.state_action_contract.v1',
      expires_at: new Date(Date.now() + (60 * 60 * 1000)).toISOString(),
      material_preview_id: 'stale-material-preview',
      material_preview_hash: 'stale-hash',
      candidate_ids: ['stale-candidate'],
      material_preview: {
        material_preview_id: 'stale-material-preview',
        material_preview_hash: 'stale-hash',
        material_candidates: [{ candidate_id: 'stale-candidate' }],
      },
    }));
  });

  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

  await expect.poll(() => page.evaluate(() => (
    sessionStorage.getItem('layer3_workbench_gate_b_draft_v1')
  ))).toBeNull();
});

test('Layer 3 workbench restores Gate B drafts and server session anchors across reloads', async ({ page }) => {
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

  const materialResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/material-preview')
  ));
  await page.locator('#layer3-intent').fill('Protect Gate B draft and recover server session.');
  await page.locator('#run-preflight').click();
  const material = await expectJson(await materialResponsePromise);
  expect(material.material_candidates.length).toBeGreaterThan(1);

  const rows = page.locator('#material-ledger-body tr[data-candidate-id]');
  await rows.nth(1).locator('.decision-select').selectOption('denied');
  await rows.nth(1).locator('.reason-input').fill('Reload recovery draft proof.');

  const draftBeforeReload = await page.evaluate(() => JSON.parse(
    sessionStorage.getItem('layer3_workbench_gate_b_draft_v1'),
  ));
  expect(draftBeforeReload.schema_id).toBe('layer3.gate_b_draft_snapshot.v1');
  expect(draftBeforeReload.draft_authority).toBe('browser_restore_only_server_revalidated_on_commit');
  expect(draftBeforeReload.state_action_contract_schema_id).toBe('layer3.state_action_contract.v1');
  expect(draftBeforeReload.state_action_contract_signature).toContain('"schema_id":"layer3.state_action_contract.v1"');
  expect(draftBeforeReload.material_preview_hash).toBe(material.material_preview_hash);
  expect(draftBeforeReload.client_request_id).toBeTruthy();

  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]')).toHaveCount(material.material_candidates.length);
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]').nth(1).locator('.decision-select')).toHaveValue('denied');
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]').nth(1).locator('.reason-input')).toHaveValue('Reload recovery draft proof.');

  const gateBRequestPromise = page.waitForRequest((request) => (
    request.url().includes('/api/v1/layer3/gate-b/decision') && request.method() === 'POST'
  ));
  const gateBResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/gate-b/decision')
  ));
  await page.locator('#gate-b-submit').click();
  const gateBRequest = await gateBRequestPromise;
  const gateBPayload = gateBRequest.postDataJSON();
  expect(gateBPayload.client_request_id).toBe(draftBeforeReload.client_request_id);
  expect(gateBPayload.material_preview_hash).toBe(material.material_preview_hash);
  const gateB = await expectJson(await gateBResponsePromise);
  expect(gateB.status).toBe('ok');

  const storageAfterCommit = await page.evaluate(() => ({
    draft: sessionStorage.getItem('layer3_workbench_gate_b_draft_v1'),
    recovery: JSON.parse(localStorage.getItem('layer3_workbench_session_recovery_v1')),
  }));
  expect(storageAfterCommit.draft).toBeNull();
  expect(storageAfterCommit.recovery.schema_id).toBe('layer3.browser_session_recovery.v1');
  expect(storageAfterCommit.recovery.session_id).toBe(gateB.session_id);
  expect(storageAfterCommit.recovery.state_action_contract_schema_id).toBe('layer3.state_action_contract.v1');
  expect(storageAfterCommit.recovery.state_action_contract_signature).toContain('"schema_id":"layer3.state_action_contract.v1"');

  const sessionResponsePromise = page.waitForResponse((response) => (
    response.url().includes(`/api/v1/layer3/session/${gateB.session_id}`)
  ));
  await page.reload({ waitUntil: 'domcontentloaded' });
  const session = await expectJson(await sessionResponsePromise);
  expect(session.session_id).toBe(gateB.session_id);
  await expect(page.locator('#authority-rail')).toContainText(gateB.session_id);
  await expect(page.locator('#gate-c-preview')).toBeEnabled();
});

test('Layer 3 workbench keeps page-level scrolling and step navigation across viewports', async ({ page }) => {
  const stepTargets = [
    ['intent', 'intent-band'],
    ['sources', 'source-fieldset'],
    ['gate_b', 'gate-b-band'],
    ['gate_c', 'gate-c-band'],
    ['plan', 'plan-band'],
    ['execution', 'result-review-band'],
    ['results', 'result-review-band'],
    ['package', 'package-review-band'],
    ['handoff', 'handoff-export-band'],
  ];

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Layer 3 Workbench' })).toBeVisible();

    const scrollState = await page.evaluate(() => {
      const bodyStyle = window.getComputedStyle(document.body);
      const contextStyle = window.getComputedStyle(document.querySelector('.context-panel'));
      return {
        bodyOverflowY: bodyStyle.overflowY,
        contextOverflow: contextStyle.overflow,
        pageCanScroll: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight) > window.innerHeight,
        pageFitsViewportWidth: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      };
    });
    expect(scrollState).toEqual({
      bodyOverflowY: 'auto',
      contextOverflow: 'visible',
      pageCanScroll: true,
      pageFitsViewportWidth: true,
    });

    for (const [step, targetId] of stepTargets) {
      const chip = page.locator(`[data-step="${step}"]`);
      await expect(chip).toBeEnabled();
      await chip.click();
      await expect(chip).toHaveAttribute('aria-current', 'step');
      await expect(page.locator(`#${targetId}`)).toBeVisible();
    }
  }
});

test('Layer 3 workbench surfaces typed and deferred APS source-family guardrails', async ({ page }) => {
  const candidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  const candidates = await expectJson(await candidatesResponsePromise);

  expect(candidates.source_family_summary.selection_shape).toBe('dataset_version');
  expect(
    candidates.source_family_summary.admitted_materialized_families.map((family) => family.parser_family),
  ).toEqual(expect.arrayContaining([
    'csv_table',
    'xlsx_workbook',
    'json_recordset',
    'sec_edgar_filing',
  ]));
  expect(
    candidates.source_family_summary.not_admitted_or_deferred_families.map((family) => family.source_family),
  ).toEqual(expect.arrayContaining([
    'xml_html_inline_xbrl',
    'broad_workbook_semantics',
    'archive_member_table_or_filing_orchestration',
    'mixed_source_package_semantics',
  ]));

  const summary = page.locator('.source-family-summary');
  await expect(summary).toContainText('Server-backed typed families');
  await expect(summary).toContainText('CSV table');
  await expect(summary).toContainText('XLSX workbook table');
  await expect(summary).toContainText('JSON recordset');
  await expect(summary).toContainText('SEC/EDGAR text table');
  await expect(summary).toContainText('Deferred / refused guardrails');
  await expect(summary).toContainText('XML/HTML/inline XBRL');
  await expect(summary).toContainText(
    'This endpoint surfaces server-backed APS-derived DatasetVersion choices only; refused/deferred families are explanatory guardrails, not selectable source classes.',
  );
});

test('Layer 3 workbench renders selected APS DatasetVersion trace detail from material preview', async ({ page, request }) => {
  const seed = await expectJson(await request.post('/__test/layer3/seed-aps-dataset'));
  const candidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  const candidates = await expectJson(await candidatesResponsePromise);
  expect(candidates.dataset_version_candidates.map((candidate) => candidate.dataset_version_id)).toContain(
    seed.dataset_version_id,
  );

  await page.locator(`input[name="dataset-version-candidate"][value="${seed.dataset_version_id}"]`).check();
  await page.locator('input[name="source-class"][value="aps_content_document"]').uncheck();
  const materialResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/material-preview')
  ));
  await page.locator('#layer3-intent').fill('Review selected APS-derived dataset trace detail.');
  await page.locator('#run-preflight').click();
  const material = await expectJson(await materialResponsePromise);
  const materialCandidate = material.material_candidates.find((candidate) => (
    candidate.payload?.dataset_version_id === seed.dataset_version_id
  ));
  expect(materialCandidate).toBeTruthy();
  expect(materialCandidate.source_trace.trace_readiness).toBe('traceable_aps_dataset_version');
  expect(materialCandidate.source_trace.aps_trace_refs.typed_content_contract_id).toBe('aps_csv_table_units_v1');

  const row = page.locator('#material-ledger-body tr[data-candidate-id]');
  await expect(row).toHaveCount(1);
  const trace = row.locator('.material-trace-card');
  await expect(trace).toContainText('CSV table');
  await expect(trace).toContainText('traceable_aps_dataset_version');
  await expect(trace).toContainText('csv_table');
  await expect(trace).toContainText('aps_csv_table_units_v1');
  await expect(trace).toContainText('ML26001A777');

  await page.locator('#material-filter').fill('aps_csv_table_units_v1');
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]')).toHaveCount(1);
});

test('Layer 3 workbench renders selected APS content document trace detail from material preview', async ({ page, request }) => {
  const seed = await expectJson(await request.post('/__test/layer3/seed-aps-document'));
  const candidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/aps-content-document-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  const candidates = await expectJson(await candidatesResponsePromise);
  expect(candidates.aps_content_document_candidates.map((candidate) => candidate.content_id)).toContain(
    seed.content_id,
  );

  await page.locator(`input[name="aps-content-document-candidate"][value="${seed.content_id}"]`).check();
  await page.locator('input[name="source-class"][value="dataset_version"]').uncheck();
  const materialResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/material-preview')
  ));
  await page.locator('#layer3-intent').fill('Review selected APS content document trace detail.');
  await page.locator('#run-preflight').click();
  const material = await expectJson(await materialResponsePromise);
  const materialCandidate = material.material_candidates.find((candidate) => (
    candidate.payload?.content_id === seed.content_id
  ));
  expect(materialCandidate).toBeTruthy();
  expect(materialCandidate.source_trace.trace_readiness).toBe('traceable_aps_content_document');
  expect(materialCandidate.source_trace.aps_trace_refs.content_units_ref).toContain('_content_units.json');

  const row = page.locator('#material-ledger-body tr[data-candidate-id]');
  await expect(row).toHaveCount(1);
  const trace = row.locator('.material-trace-card');
  await expect(trace).toContainText('APS content document');
  await expect(trace).toContainText('traceable_aps_content_document');
  await expect(trace).toContainText(seed.content_id);
  await expect(trace).toContainText('aps_content_units_v2');
  await expect(trace).toContainText('ML26001A001');

  await page.locator('#material-filter').fill(seed.content_id);
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]')).toHaveCount(1);
});

test('Layer 3 workbench exposes visible keyboard focus across themes', async ({ page }) => {
  for (const theme of ['light', 'dark', 'workbench']) {
    await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
    await page.locator('#theme-selector').selectOption(theme);
    await page.reload({ waitUntil: 'domcontentloaded' });

    await page.keyboard.press('Tab');
    await expect(page.locator('a.back-link')).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(page.locator('#theme-selector')).toBeFocused();
    await page.keyboard.press('Tab');

    const intentChip = page.locator('[data-step="intent"]');
    await expect(intentChip).toBeFocused();
    await expect(intentChip).toHaveAttribute('aria-current', 'step');
    const chipFocusStyle = await intentChip.evaluate((element) => {
      const style = window.getComputedStyle(element);
      return {
        outlineStyle: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        outlineColor: style.outlineColor,
        borderColor: style.borderColor,
      };
    });
    expect(chipFocusStyle.outlineStyle).toBe('solid');
    expect(chipFocusStyle.outlineWidth).toBe('3px');

    const gateCChip = page.locator('[data-step="gate_c"]');
    await gateCChip.focus();
    await page.keyboard.press('Enter');
    await expect(gateCChip).toHaveAttribute('aria-current', 'step');
    await expect(page.locator('#gate-c-band')).toBeFocused();
    const targetFocusStyle = await page.locator('#gate-c-band').evaluate((element) => {
      const style = window.getComputedStyle(element);
      return {
        outlineStyle: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        boxShadow: style.boxShadow,
      };
    });
    expect(targetFocusStyle.outlineStyle).toBe('solid');
    expect(targetFocusStyle.outlineWidth).toBe('3px');
    expect(targetFocusStyle.boxShadow).not.toBe('none');
  }
});

test('Layer 3 workbench requires explicit associated-cohort delivery UI server authority', async ({ page }) => {
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    const authorityRail = {
      session_id: 'session-cohort-delivery-ui',
      current_gate: 'package',
      persistence_mode: 'durable_external_export_download_prepare',
      source_authority: { source_classes: ['dataset_version'] },
      downstream_unavailable: ['public_url', 'signed_url', 'connector_dispatch'],
    };
    const packageIds = ['pkg-canonical', 'pkg-user', 'pkg-review'];
    const packageKinds = ['canonical_internal', 'user_facing', 'review_facing'];
    const payloadRefs = ['payload-canonical', 'payload-user', 'payload-review'];
    const payloadHashes = ['hash-canonical', 'hash-user', 'hash-review'];
    const external = {
      schema_id: 'layer3.external_export_download_prepare_state.v1',
      state: 'external_export_download_prepared',
      external_export_download_state: 'external_export_download_prepared',
      external_export_download_record_ref: 'readiness-ref',
      export_download_descriptor_ref: 'descriptor-ref',
      result_review_record_ref: 'review-ref',
      package_review_preview_hash: 'package-preview-hash',
      reconciliation_record_id: 'reconciliation-id',
      output_package_ids: packageIds,
      package_kinds: packageKinds,
      payload_refs: payloadRefs,
      payload_hashes: payloadHashes,
      package_review_submit_record_ref: 'submit-ref',
      package_review_state: 'package_review_approved',
      prepare_record_ref: 'prepare-ref',
      handoff_export_state: 'handoff_export_prepared',
      handoff_export_envelope_ref: 'envelope-ref',
      handoff_target: 'internal_export_envelope',
      export_mode: 'prepare_only',
      aps_handoff_record_ref: 'aps-record-ref',
      aps_handoff_state: 'aps_handoff_dispatched',
      aps_handoff_target: 'aps_evidence_bundle',
      dispatch_mode: 'server_side_aps_handoff',
      aps_output_package_id: 'aps-package-id',
      aps_output_package_kind: 'aps_evidence_bundle_handoff',
      aps_bundle_ref: 'aps-bundle-ref',
      aps_bundle_id: 'aps-bundle-id',
      aps_schema_id: 'aps.evidence_bundle.v2',
      source_artifact_hash: 'source-artifact-hash',
      source_artifact_size_bytes: 123,
      export_download_target: 'aps_evidence_bundle_download_reference',
      download_mode: 'reference_only_prepare',
      pass_type: 'associated_cohort',
      pass_scope: 'quantitative_associated_cohort_dataset_version',
      method: 'descriptive_summary',
      source_gate: '78_COHORT_FREEZE',
      source_shape: 'aligned_wide_table',
      source_dataset_version_ids: ['dv-1', 'dv-2'],
    };
    State.sessionSummary = {
      session_id: 'session-cohort-delivery-ui',
      execution_selection: {
        selected: true,
        pass_run_ids: ['pass-run-id'],
        pass_run_statuses: { 'pass-run-id': 'completed' },
        source_preview_id: 'preview-id',
        source_preview_hash: 'preview-hash',
        analysis_plan_id: 'analysis-plan-id',
      },
      analysis_execution_start: {
        analysis_run_id: 'analysis-run-id',
      },
      execution_result_review: {
        review_state: 'execution_result_review_approved',
        operator_decision: 'approved',
        review_record_ref: 'review-ref',
      },
      package_review_submit: {
        package_review_state: 'package_review_approved',
        submit_record_ref: 'submit-ref',
        output_package_ids: packageIds,
        package_kinds: packageKinds,
        payload_refs: payloadRefs,
        payload_hashes: payloadHashes,
      },
      handoff_export_prepare: {
        prepare_record_ref: 'prepare-ref',
        handoff_export_state: 'handoff_export_prepared',
        handoff_export_envelope_ref: 'envelope-ref',
        result_review_record_ref: 'review-ref',
        package_review_preview_hash: 'package-preview-hash',
        reconciliation_record_id: 'reconciliation-id',
        package_review_submit_record_ref: 'submit-ref',
        package_review_state: 'package_review_approved',
        output_package_ids: packageIds,
        package_kinds: packageKinds,
        payload_refs: payloadRefs,
        payload_hashes: payloadHashes,
      },
      aps_handoff_dispatch: {
        aps_handoff_record_ref: 'aps-record-ref',
        aps_handoff_state: 'aps_handoff_dispatched',
      },
      external_export_download: external,
      sublayer_visualization: {
        pass_runs: [{
          pass_run_id: 'pass-run-id',
          pass_type: 'associated_cohort',
          pass_scope: 'quantitative_associated_cohort_dataset_version',
          selected_method_name: 'descriptive_summary',
          requested_method_name: 'descriptive_summary',
          requested_method_source: 'analysis_set.formation_basis_json.requested_method_name',
          source_gate: '78_COHORT_FREEZE',
          cohort_shape: 'aligned_wide_table',
          source_dataset_version_ids: ['dv-1', 'dv-2'],
        }],
      },
      authority_rail: authorityRail,
    };
    State.resultStatus = {
      result_status_available: true,
      pass_run_id: 'pass-run-id',
      pass_run_status: 'completed',
      pass_type: 'associated_cohort',
      pass_scope: 'quantitative_associated_cohort_dataset_version',
      selected_method_name: 'descriptive_summary',
      analysis_plan_id: 'analysis-plan-id',
      analysis_run_id: 'analysis-run-id',
      preview_identity: { preview_id: 'preview-id', preview_hash: 'preview-hash' },
      output_payload_ref: 'output-ref',
      output_metadata_summary: {
        readable: true,
        pass_type: 'associated_cohort',
        pass_scope: 'quantitative_associated_cohort_dataset_version',
        selected_method_name: 'descriptive_summary',
        requested_method_name: 'descriptive_summary',
        requested_method_source: 'analysis_set.formation_basis_json.requested_method_name',
        source_gate: '78_COHORT_FREEZE',
        cohort_shape: 'aligned_wide_table',
        source_dataset_version_ids: ['dv-1', 'dv-2'],
        output_payload_ref: 'output-ref',
      },
    };
    renderAll();
  });

  await expect(page.locator('#external-export-download-delivery-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    'associated_cohort_external_export_download_delivery_ui_unavailable',
  );

  await page.evaluate(() => {
    State.sessionSummary.external_export_download.delivery_ui = {
      schema_id: 'layer3.external_export_download_delivery_ui.v1',
      available: true,
      state: 'associated_cohort_external_export_download_delivery_ui_ready',
      operator_decision: 'deliver_external_export_download',
      delivery_mode: 'same_origin_artifact_stream',
      server_authority: 'associated_cohort_external_export_download_delivery_ui_gate',
      browser_managed_same_origin_attachment_enabled: true,
      public_url_enabled: false,
      signed_url_enabled: false,
      connector_dispatch_enabled: false,
      destination_selection_enabled: false,
      generic_downstream_dispatch_enabled: false,
      package_mutation_enabled: false,
      schema_runtime_source_widening_enabled: false,
    };
    renderAll();
  });

  await expect(page.locator('#external-export-download-delivery-submit')).toBeEnabled();
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    'external_export_download_delivery_ui_ready',
  );
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    'associated_cohort_external_export_download_delivery_ui_gate',
  );
  await expect(page.locator('#external-export-download-signed-reference-generate')).toBeEnabled();
  await expect(page.locator('#external-export-download-signed-reference-use')).toBeDisabled();
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'external_export_download_signed_reference_ui_ready',
  );

  await page.route('**/api/v1/layer3/handoff/export/download/signed-reference/generate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        schema_id: 'layer3.external_export_download_signed_reference.v1',
        status: 'prepared',
        session_id: 'session-cohort-delivery-ui',
        analysis_plan_id: 'analysis-plan-id',
        pass_run_id: 'pass-run-id',
        preview_identity: { preview_id: 'preview-id', preview_hash: 'preview-hash' },
        reconciliation_record_id: 'reconciliation-id',
        external_export_download_record_ref: 'readiness-ref',
        export_download_descriptor_ref: 'descriptor-ref',
        signed_reference_state: 'external_export_download_signed_reference_ready',
        signed_reference_token: 'signed-token-from-server',
        signed_reference_expires_at: '2026-05-04T12:00:00+00:00',
        signed_reference_expires_in_seconds: 300,
        signed_reference_use_endpoint: '/api/v1/layer3/handoff/export/download/signed-reference/use',
        delivery_mode: 'same_origin_signed_delivery_reference',
        server_authority: 'associated_cohort_external_export_download_signed_reference_gate',
        source_artifact_ref: 'aps-bundle-ref',
        source_artifact_hash: 'source-artifact-hash',
        source_artifact_size_bytes: 123,
        pass_type: 'associated_cohort',
        pass_scope: 'quantitative_associated_cohort_dataset_version',
        method: 'descriptive_summary',
        source_gate: '78_COHORT_FREEZE',
        source_shape: 'aligned_wide_table',
        source_dataset_version_ids: ['dv-1', 'dv-2'],
        public_url_enabled: false,
        external_object_store_url_enabled: false,
        connector_dispatch_enabled: false,
        destination_selection_enabled: false,
        generic_downstream_dispatch_enabled: false,
        package_mutation_enabled: false,
        schema_runtime_source_widening_enabled: false,
        authority_rail: {
          token_authority: 'server_hmac_stateless_reference',
          artifact_authority: 'existing_external_export_download_delivery_validator',
          expires_within_seconds: 300,
          revalidated_at_generation: true,
          revalidate_at_use_required: true,
          configured_secret_present: true,
        },
      }),
    });
  });

  const signedRequestPromise = page.waitForRequest(
    '**/api/v1/layer3/handoff/export/download/signed-reference/generate',
  );
  await page.locator('#external-export-download-signed-reference-generate').click();
  const signedRequest = await signedRequestPromise;
  const signedPayload = signedRequest.postDataJSON();
  expect(signedPayload.operator_decision).toBe('deliver_external_export_download');
  expect(signedPayload.delivery_mode).toBe('same_origin_artifact_stream');
  expect(signedPayload.external_export_download_record_ref).toBe('readiness-ref');
  expect(signedPayload.client_request_id).toEqual(expect.any(String));
  for (const forbiddenKey of [
    'download_url',
    'download_token',
    'public_url',
    'signed_url',
    'local_file_path',
    'connector_run_id',
    'connector_dispatch',
    'destination',
    'destination_id',
    'generic_dispatch',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'retry',
    'recover',
    'schema_migration',
    'delivery_ui',
  ]) {
    expect(signedPayload).not.toHaveProperty(forbiddenKey);
  }
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'external_export_download_signed_reference_ready',
  );
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'same_origin_signed_delivery_reference',
  );
  await expect(page.locator('#external-export-download-signed-reference-generate')).toBeDisabled();
  await expect(page.locator('#external-export-download-signed-reference-use')).toBeEnabled();

  await page.route('**/api/v1/layer3/handoff/export/download/signed-reference/use', async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload).toEqual({ signed_reference_token: 'signed-token-from-server' });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: {
        'x-layer3-schema-id': 'layer3.external_export_download_signed_reference_use.v1',
        'x-layer3-delivery-state': 'external_export_download_delivered',
        'x-layer3-signed-reference-state': 'external_export_download_signed_reference_delivered',
        'x-layer3-signed-reference-expires-at': '2026-05-04T12:00:00+00:00',
        'x-layer3-source-artifact-hash': 'source-artifact-hash',
      },
      body: '{"delivered":true}',
    });
  });

  await Promise.all([
    page.waitForResponse('**/api/v1/layer3/handoff/export/download/signed-reference/use'),
    page.locator('#external-export-download-signed-reference-use').click(),
  ]);
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'external_export_download_signed_reference_delivered',
  );

  await page.route('**/api/v1/layer3/handoff/export/download/deliver', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/octet-stream',
      headers: {
        'content-disposition': 'attachment; filename="cohort-aps-bundle.json"',
        'x-layer3-schema-id': 'layer3.external_export_download_delivery.v1',
        'x-layer3-delivery-state': 'external_export_download_delivered',
        'x-layer3-source-artifact-hash': 'source-artifact-hash',
      },
      body: '{"delivered":true}',
    });
  });

  const [deliveryRequest, deliveryResponse] = await Promise.all([
    page.waitForRequest('**/api/v1/layer3/handoff/export/download/deliver'),
    page.waitForResponse('**/api/v1/layer3/handoff/export/download/deliver'),
    page.locator('#external-export-download-delivery-submit').click(),
  ]);
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    'external_export_download_delivery_ui_downloading',
  );
  expect(deliveryResponse.status()).toBe(200);
  expect(deliveryResponse.headers()['content-disposition']).toContain('attachment');
  const submittedPayload = formPostPayload(deliveryRequest);
  expect(submittedPayload.operator_decision).toBe('deliver_external_export_download');
  expect(submittedPayload.delivery_mode).toBe('same_origin_artifact_stream');
  expect(submittedPayload.external_export_download_record_ref).toBe('readiness-ref');
  expect(submittedPayload.client_request_id).toEqual(expect.any(String));
  expect(submittedPayload.client_request_id.length).toBeGreaterThan(0);
  for (const forbiddenKey of [
    'download_url',
    'download_token',
    'public_url',
    'signed_url',
    'local_file_path',
    'connector_run_id',
    'connector_dispatch',
    'destination',
    'destination_id',
    'generic_dispatch',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'retry',
    'recover',
    'schema_migration',
    'delivery_ui',
  ]) {
    expect(submittedPayload).not.toHaveProperty(forbiddenKey);
  }
});

test('Layer 3 workbench applies mockup-informed Workbench visual boundaries without degrading shared themes', async ({ page }) => {
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('workbench');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('.operation-dock-tab')).toHaveCount(9);
  await expect(page.locator('.operations-dock > .operation-panel-active')).toHaveCount(1);
  await expect(page.locator('.operations-dock > .operation-panel-inactive').first()).toBeAttached();
  await expect(page.locator('#operations-dock-summary')).toContainText('Intent');
  await expect(page.locator('#operations-dock-summary')).toContainText('3A intake setup');
  await expect(page.locator('#operations-dock-summary')).toContainText('Sublayer 3A intake/specification field');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-canvas', '3a');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-key', 'intent');

  const workbenchStyles = await page.evaluate(() => {
    const bodyStyle = window.getComputedStyle(document.body);
    const shell = document.querySelector('.layer3-body');
    const shellRect = shell.getBoundingClientRect();
    const stepperRect = document.querySelector('.layer3-stepper').getBoundingClientRect();
    const contextRect = document.querySelector('.context-panel').getBoundingClientRect();
    const workspaceRect = document.querySelector('.layer3-workspace').getBoundingClientRect();
    const railStyle = window.getComputedStyle(document.querySelector('.authority-rail'));
    const workbandStyle = window.getComputedStyle(document.querySelector('#gate-b-band'));
    const fieldsetStyle = window.getComputedStyle(document.querySelector('#source-fieldset'));
    const chipStyle = window.getComputedStyle(document.querySelector('[data-step="gate_b"]'));
    const dockStyle = window.getComputedStyle(document.querySelector('.operations-dock'));
    const dockNavStyle = window.getComputedStyle(document.querySelector('.operations-dock-nav'));
    const activePanelStyle = window.getComputedStyle(document.querySelector('.operations-dock > .operation-panel-active'));
    const inactivePanelStyle = window.getComputedStyle(document.querySelector('.operations-dock > .operation-panel-inactive'));
    const mapBand = document.querySelector('#sublayer-map-band');
    const mapBandStyle = window.getComputedStyle(mapBand);
    const mapPanelStyle = window.getComputedStyle(document.querySelector('#sublayer-map-panel'));
    return {
      bodyBackground: bodyStyle.backgroundColor,
      railBorderTopStyle: railStyle.borderTopStyle,
      railBorderBottomStyle: railStyle.borderBottomStyle,
      railBackground: railStyle.backgroundColor,
      workspaceBackground: window.getComputedStyle(document.querySelector('.layer3-workspace')).backgroundColor,
      workbandBorderStyle: workbandStyle.borderTopStyle,
      workbandBorderLeftWidth: workbandStyle.borderLeftWidth,
      workbandBorderLeftColor: workbandStyle.borderLeftColor,
      workbandBackground: workbandStyle.backgroundColor,
      fieldsetBorderStyle: fieldsetStyle.borderTopStyle,
      chipBackground: chipStyle.backgroundColor,
      dockDisplay: dockStyle.display,
      dockOverflowX: dockStyle.overflowX,
      dockColumnCount: dockStyle.gridTemplateColumns.split(' ').filter(Boolean).length,
      dockNavDisplay: dockNavStyle.display,
      activePanelDisplay: activePanelStyle.display,
      inactivePanelDisplay: inactivePanelStyle.display,
      shellColumnCount: window.getComputedStyle(shell).gridTemplateColumns.split(' ').filter(Boolean).length,
      stepperWidth: Math.round(stepperRect.width),
      contextWidth: Math.round(contextRect.width),
      workspaceShare: workspaceRect.width / shellRect.width,
      mapBandHasCanvasStageClass: mapBand.classList.contains('canvas-stage-band'),
      mapBandBorderLeftStyle: mapBandStyle.borderLeftStyle,
      mapBandBorderRightStyle: mapBandStyle.borderRightStyle,
      mapPanelPaddingLeft: Math.round(Number.parseFloat(mapPanelStyle.paddingLeft)),
    };
  });
  expect(workbenchStyles).toMatchObject({
    bodyBackground: 'rgb(13, 13, 13)',
    railBorderTopStyle: 'none',
    railBorderBottomStyle: 'dotted',
    workspaceBackground: 'rgba(0, 0, 0, 0)',
    workbandBorderStyle: 'dotted',
    workbandBorderLeftWidth: '0px',
    workbandBackground: 'rgba(0, 0, 0, 0)',
    fieldsetBorderStyle: 'dashed',
    dockDisplay: 'grid',
    dockOverflowX: 'hidden',
    dockColumnCount: 2,
    dockNavDisplay: 'grid',
    activePanelDisplay: 'grid',
    inactivePanelDisplay: 'none',
    shellColumnCount: 3,
    mapBandHasCanvasStageClass: true,
    mapBandBorderLeftStyle: 'none',
    mapBandBorderRightStyle: 'none',
  });
  expect(workbenchStyles.mapPanelPaddingLeft).toBeLessThanOrEqual(10);
  expect(workbenchStyles.stepperWidth).toBeLessThanOrEqual(38);
  expect(workbenchStyles.contextWidth).toBeLessThanOrEqual(62);
  expect(workbenchStyles.workspaceShare).toBeGreaterThan(0.92);
  expect(workbenchStyles.railBackground).not.toBe('rgba(0, 0, 0, 0)');
  expect(workbenchStyles.chipBackground).not.toBe('rgba(0, 0, 0, 0)');
  await expect(page.locator('.operation-dock-tab')).toHaveCount(9);
  await expect(page.locator('.operation-dock-tab').first()).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#intent-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#gate-b-band')).toHaveAttribute('data-operation-active', 'false');

  await page.locator('.operation-dock-tab').first().focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('.operation-dock-tab').nth(1)).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#gate-b-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#intent-band')).toHaveAttribute('data-operation-active', 'false');
  await expect(page.locator('#operations-dock-summary')).toContainText('Gate B Material Ledger');
  await expect(page.locator('#operations-dock-summary')).toContainText('3A material ledger');
  await expect(page.locator('#operations-dock-summary')).toContainText('Sublayer 3A session-scoped material ledger');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-canvas', '3a');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-key', 'gate_b');

  await page.keyboard.press('ArrowRight');
  await expect(page.locator('.operation-dock-tab').nth(2)).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#gate-c-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#operations-dock-summary')).toContainText('Sublayer 3B modality object banks');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-canvas', '3b');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-key', 'gate_c');

  const canvasFocusStyles = await page.evaluate(() => {
    const threeB = window.getComputedStyle(document.querySelector('.sublayer-3b'));
    const connector = window.getComputedStyle(document.querySelector('.sublayer-connector-3bc'));
    return {
      threeBBorderColor: threeB.borderTopColor,
      threeBBoxShadow: threeB.boxShadow,
      connectorFilter: connector.filter,
    };
  });
  expect(canvasFocusStyles.threeBBorderColor).not.toBe('rgb(180, 180, 180)');
  expect(canvasFocusStyles.threeBBoxShadow).not.toBe('none');
  expect(canvasFocusStyles.connectorFilter).not.toBe('none');

  await page.locator('[data-step="sources"]').click();
  await expect(page.locator('#intent-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-key', 'intent');
  await expect(page.locator('#source-fieldset')).toBeVisible();

  await page.locator('#theme-selector').selectOption('light');
  await page.reload({ waitUntil: 'domcontentloaded' });
  const lightWorkbandStyle = await page.locator('#gate-b-band').evaluate((element) => {
    const style = window.getComputedStyle(element);
    return {
      borderStyle: style.borderTopStyle,
      borderLeftWidth: style.borderLeftWidth,
    };
  });
  expect(lightWorkbandStyle).toEqual({
    borderStyle: 'solid',
    borderLeftWidth: '1px',
  });

  await page.setViewportSize({ width: 1024, height: 768 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  const lightPlaneColumnCount = await page.locator('.analysis-plane .plane-flow').first().evaluate((element) => {
    const style = window.getComputedStyle(element);
    return style.gridTemplateColumns.split(' ').filter(Boolean).length;
  });
  expect(lightPlaneColumnCount).toBeGreaterThan(1);

  await page.locator('#theme-selector').selectOption('workbench');
  await page.reload({ waitUntil: 'domcontentloaded' });
  const workbenchPlaneColumnCount = await page.locator('.analysis-plane .plane-flow').first().evaluate((element) => {
    const style = window.getComputedStyle(element);
    return style.gridTemplateColumns.split(' ').filter(Boolean).length;
  });
  expect(workbenchPlaneColumnCount).toBe(1);

  await page.locator('[data-operation-target="result-review-band"]').click();
  await expect(page.locator('#result-review-band')).toHaveAttribute('data-operation-active', 'true');
  const workbenchResultControlColumns = await page.evaluate(() => {
    const resultControls = window.getComputedStyle(document.querySelector('#result-review-band .result-review-controls'));
    return resultControls.gridTemplateColumns.split(' ').filter(Boolean).length;
  });
  expect(workbenchResultControlColumns).toBe(2);
  await page.locator('[data-operation-target="aps-handoff-band"]').click();
  await expect(page.locator('#aps-handoff-band')).toHaveAttribute('data-operation-active', 'true');
  const workbenchApsControlColumns = await page.evaluate(() => {
    const apsControls = window.getComputedStyle(document.querySelector('#aps-handoff-dispatch-form .result-review-controls'));
    return apsControls.gridTemplateColumns.split(' ').filter(Boolean).length;
  });
  expect(workbenchApsControlColumns).toBe(1);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('[data-operation-target="result-review-band"]').click();
  await expect(page.locator('#result-review-band')).toHaveAttribute('data-operation-active', 'true');
  const mobileWorkbenchControlColumns = await page.evaluate(() => {
    const resultControls = window.getComputedStyle(document.querySelector('#result-review-band .result-review-controls'));
    return {
      result: resultControls.gridTemplateColumns.split(' ').filter(Boolean).length,
    };
  });
  expect(mobileWorkbenchControlColumns).toEqual({
    result: 1,
  });
  await page.locator('[data-operation-target="aps-handoff-band"]').click();
  await expect(page.locator('#aps-handoff-band')).toHaveAttribute('data-operation-active', 'true');
  const mobileApsControlColumns = await page.evaluate(() => {
    const apsControls = window.getComputedStyle(document.querySelector('#aps-handoff-dispatch-form .result-review-controls'));
    return apsControls.gridTemplateColumns.split(' ').filter(Boolean).length;
  });
  expect(mobileApsControlColumns).toBe(1);
});

test('Layer 3 workbench opens the exact Claude prototype as a durable standalone mode', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await Promise.all([
    page.waitForURL('**/review/layer3/static/claude.html'),
    page.locator('#theme-selector').selectOption('claude'),
  ]);

  await expect(page).toHaveTitle(/Layer 3 Workbench.*Prototype/);
  await expect(page.locator('.chrome-bar')).toHaveCount(0);
  await expect(page.locator('header.app-header.layer3-header')).toBeVisible();
  await expect(page.locator('.proto-badge')).toHaveText('PROTOTYPE');
  await expect(page.locator('#theme-selector')).toHaveValue('claude');
  await expect(page.locator('.nav-tab[data-screen="overview"]')).toContainText('Overview');
  await expect(page.locator('.state-btn[data-state="loaded"]')).toHaveClass(/active/);
  await expect(page.locator('#screen-intent')).toHaveClass(/active/);

  await page.locator('.nav-tab[data-screen="overview"]').click();
  await expect(page.locator('#screen-overview')).toHaveClass(/active/);
  await page.locator('.state-btn[data-state="analyzed"]').click();
  await expect(page.locator('.state-btn[data-state="analyzed"]')).toHaveClass(/active/);
  await expect(page.locator('#ov-3c-content')).toContainText('Insights/Facts/Data Generated');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page).toHaveTitle(/Layer 3 Workbench.*Prototype/);
  const mobileState = await page.evaluate(() => ({
    screenCount: document.querySelectorAll('.screen').length,
    hasPrototypeBadge: document.querySelector('.proto-badge')?.textContent?.trim() === 'PROTOTYPE',
    themeValue: document.querySelector('#theme-selector')?.value,
  }));
  expect(mobileState).toEqual({
    screenCount: 5,
    hasPrototypeBadge: true,
    themeValue: 'claude',
  });

  await Promise.all([
    page.waitForURL('**/review/layer3'),
    page.locator('#theme-selector').selectOption('dark'),
  ]);
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'dark');
});

test('Layer 3 workbench renders a responsive live-state sublayer material and analysis map', async ({ page }) => {
  await page.setViewportSize({ width: 1626, height: 869 });
  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);
  await page.locator('#theme-selector').selectOption('workbench');

  await expect(page.locator('#sublayer-map-panel')).toContainText('Sublayer 3A');
  await expect(page.locator('#sublayer-map-panel')).toContainText('Sublayer 3B');
  await expect(page.locator('#sublayer-map-panel')).toContainText('Sublayer 3C');
  await expect(page.locator('#sublayer-map-panel')).toHaveClass(/diagram-canvas/);
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-viz-state', 'empty|empty|structural');
  await expect(page.locator('.canvas-intake-spec')).toContainText('User Natural Language Query Input');
  await expect(page.locator('.canvas-state-flow')).toContainText('3A');
  await expect(page.locator('.canvas-state-flow')).toContainText('Awaiting live state');
  await expect(page.locator('.canvas-state-flow')).toContainText('Structural only');
  await expect(page.locator('.manual-source-spec')).toContainText('Dataset version');
  await expect(page.locator('.manual-source-spec')).toContainText('APS content document');
  await expect(page.locator('.ledger-chip-field')).toBeVisible();
  await expect(page.locator('.ledger-bracket')).toContainText('Session-scoped Materials');
  await expect(page.locator('.analysis-lane-legend')).toContainText('Input object bank');
  await expect(page.locator('.analysis-lane-legend')).toContainText('Process / status');
  await expect(page.locator('.analysis-lane-legend')).toContainText('Output field');
  await expect(page.locator('.plane-arrow-process').first()).toBeVisible();
  await expect(page.locator('.plane-bracket').first()).toBeVisible();
  await expect(page.locator('.sublayer-3a .flow-empty')).toContainText('No material preview');
  await expect(page.locator('.modality-bucket.modality-quantitative')).toContainText('No quantitative objects');
  await expect(page.locator('.modality-bucket.modality-quantitative .modality-transfer-rail')).toHaveText('Awaiting objects');
  await expect(page.locator('.modality-bucket.modality-unclassified .modality-transfer-rail')).toHaveText('Held in 3B');
  await expect(page.locator('.analysis-plane.modality-quantitative')).toContainText('No live input object');

  const preflightResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/preflight'));
  const sourceResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/source-preview'));
  const materialResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/material-preview'));
  await page.locator('#run-preflight').click();
  await Promise.all([
    expectJson(await preflightResponsePromise),
    expectJson(await sourceResponsePromise),
    expectJson(await materialResponsePromise),
  ]);

  await expect(page.locator('.sublayer-3a .flow-object')).toHaveCount(2);
  await expect(page.locator('.sublayer-3a .diagram-chip')).toHaveCount(2);
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-viz-state', 'preview|empty|structural');
  await expect(page.locator('.sublayer-3a')).toContainText('Dataset Version');

  const rows = page.locator('#material-ledger-body tr[data-candidate-id]');
  await rows.nth(1).locator('.decision-select').selectOption('denied');
  await rows.nth(1).locator('.reason-input').fill('Deferred outside this visual proof.');
  await expect(page.locator('.sublayer-3a')).toContainText('denied');

  const gateBResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/gate-b/decision'));
  await page.locator('#gate-b-submit').click();
  await expectJson(await gateBResponsePromise);

  const gateCResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/gate-c/preview'));
  await page.locator('#gate-c-preview').click();
  const gateC = await expectJson(await gateCResponsePromise);
  expect(gateC.typing_records.length).toBeGreaterThan(0);

  await expect(page.locator('.modality-bucket.modality-quantitative .flow-object')).toHaveCount(gateC.typing_records.length);
  await expect(page.locator('.modality-bucket.modality-quantitative .diagram-chip')).toHaveCount(gateC.typing_records.length);
  await expect(page.locator('.modality-bucket.modality-quantitative .modality-transfer-rail')).toHaveAttribute('data-transfer-state', 'ready');
  await expect(page.locator('.modality-bucket.modality-quantitative .modality-transfer-rail')).toHaveText('Feeds 3C plane');
  await expect(page.locator('.sublayer-3a .flow-slot-ghost')).toHaveCount(4);
  await expect(page.locator('.modality-bucket.modality-quantitative .flow-slot-ghost')).toHaveCount(Math.max(0, 3 - gateC.typing_records.length));
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-viz-state', 'session|typed|inputs');
  await expect(page.locator('.state-3a')).toContainText('Session scoped');
  await expect(page.locator('.state-3b')).toContainText('Typing previewed');
  await expect(page.locator('.state-3c')).toContainText('Inputs routed');
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-input-bank')).toContainText('modality quantitative');
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-process-node')).toContainText('No live process yet');
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-output-field')).toContainText('No live output');
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-output-field h5')).toHaveText('Output / Result Field');

  const diagramStyles = await page.evaluate(() => {
    const sublayer = window.getComputedStyle(document.querySelector('.sublayer-3a'));
    const modality = window.getComputedStyle(document.querySelector('.modality-bucket.modality-quantitative'));
    const modalityObjects = window.getComputedStyle(document.querySelector('.modality-bucket.modality-quantitative .flow-object-list'));
    const transferRail = window.getComputedStyle(document.querySelector('.modality-bucket.modality-quantitative .modality-transfer-rail'));
    const heldRailElement = document.querySelector('.analysis-routing-plane .modality-bucket.modality-unclassified .modality-transfer-rail');
    const heldRail = window.getComputedStyle(heldRailElement);
    const ghostSlot = window.getComputedStyle(document.querySelector('.sublayer-3a .flow-slot-ghost'));
    const arrow = window.getComputedStyle(document.querySelector('.plane-arrow-process'));
    const chip = window.getComputedStyle(document.querySelector('.sublayer-3a .diagram-chip'));
    const laneLegend = window.getComputedStyle(document.querySelector('.analysis-lane-legend'));
    const laneLabel = window.getComputedStyle(document.querySelector('.analysis-lane-label'));
    const intake = window.getComputedStyle(document.querySelector('.canvas-intake-spec'));
    const intakeFrame = window.getComputedStyle(document.querySelector('.intake-spec-frame'));
    const stateFlow = window.getComputedStyle(document.querySelector('.canvas-state-flow'));
    const routingElement = document.querySelector('.analysis-routing-plane');
    const routing = window.getComputedStyle(routingElement);
    const connector3bc = document.querySelector('.sublayer-connector-3bc');
    const connector3bcBefore = window.getComputedStyle(connector3bc, '::before');
    const connector3bcAfter = window.getComputedStyle(connector3bc, '::after');
    const threeA = window.getComputedStyle(document.querySelector('.sublayer-3a'));
    const inputBank = document.querySelector('.plane-input-bank');
    const processNode = document.querySelector('.plane-process-node');
    const outputField = document.querySelector('.plane-output-field');
    const outputFieldStyle = window.getComputedStyle(outputField);
    const materialBankShell = document.querySelector('.material-bank-shell');
    const materialBankShellStyle = window.getComputedStyle(materialBankShell);
    const modalityBankShell = document.querySelector('.modality-bank-shell');
    const modalityBankShellStyle = window.getComputedStyle(modalityBankShell);
    const laneFrame = document.querySelector('.plane-flow-frame');
    const laneFrameStyle = window.getComputedStyle(laneFrame);
    const laneSpineStyle = window.getComputedStyle(document.querySelector('.plane-lane-spine'));
    return {
      intakeDisplay: intake.display,
      intakeGridArea: intake.gridArea,
      intakeFrameDisplay: intakeFrame.display,
      intakeFrameColumns: intakeFrame.gridTemplateColumns.split(' ').filter(Boolean).length,
      stateFlowDisplay: stateFlow.display,
      stateFlowGridArea: stateFlow.gridArea,
      routingTag: routingElement.tagName,
      routingLabel: routingElement.getAttribute('aria-label'),
      routingDisplay: routing.display,
      routingGridArea: routing.gridArea,
      routingColumns: routing.gridTemplateColumns.split(' ').filter(Boolean).length,
      connector3bcBeforeWidth: connector3bcBefore.width,
      connector3bcAfterWidth: connector3bcAfter.width,
      connector3bcAfterClip: connector3bcAfter.clipPath !== 'none',
      threeADisplay: threeA.display,
      threeAColumns: threeA.gridTemplateColumns.split(' ').filter(Boolean).length,
      sublayerBorderStyle: sublayer.borderTopStyle,
      materialBankRole: materialBankShell.getAttribute('data-diagram-role'),
      materialBankColumns: materialBankShellStyle.gridTemplateColumns.split(' ').filter(Boolean).length,
      modalityBankRole: modalityBankShell.getAttribute('data-diagram-role'),
      modalityBankColumns: modalityBankShellStyle.gridTemplateColumns.split(' ').filter(Boolean).length,
      modalityBorderStyle: modality.borderTopStyle,
      modalityColumns: modality.gridTemplateColumns.split(' ').filter(Boolean).length,
      modalityObjectGridArea: modalityObjects.gridColumnStart,
      transferRailDisplay: transferRail.display,
      transferRailGridColumnStart: transferRail.gridColumnStart,
      transferRailPosition: transferRail.position,
      transferRailWritingMode: transferRail.writingMode,
      transferRailWidth: Math.round(Number.parseFloat(transferRail.width)),
      heldRailText: heldRailElement.textContent.trim(),
      heldRailPosition: heldRail.position,
      heldRailGridColumnStart: heldRail.gridColumnStart,
      heldRailAlignSelf: heldRail.alignSelf,
      heldRailWhiteSpace: heldRail.whiteSpace,
      heldRailWritingMode: heldRail.writingMode,
      ghostSlotDisplay: ghostSlot.display,
      ghostSlotBorderStyle: ghostSlot.borderTopStyle,
      arrowDisplay: arrow.display,
      chipRadius: chip.borderTopLeftRadius,
      laneLegendDisplay: laneLegend.display,
      laneLegendColumns: laneLegend.gridTemplateColumns.split(' ').filter(Boolean).length,
      laneLabelTransform: laneLabel.textTransform,
      inputBankRole: inputBank.getAttribute('data-plane-role'),
      processNodeRole: processNode.getAttribute('data-plane-role'),
      outputFieldRole: outputField.getAttribute('data-plane-role'),
      outputFieldHeading: outputField.querySelector('h5')?.textContent?.trim(),
      outputFieldBorderStyle: outputFieldStyle.borderTopStyle,
      laneFrameRole: laneFrame.getAttribute('data-plane-role'),
      laneFrameBorderTopStyle: laneFrameStyle.borderTopStyle,
      laneSpineDisplay: laneSpineStyle.display,
    };
  });
  expect(diagramStyles).toEqual({
    intakeDisplay: 'grid',
    intakeGridArea: 'spec',
    intakeFrameDisplay: 'grid',
    intakeFrameColumns: 2,
    stateFlowDisplay: 'grid',
    stateFlowGridArea: 'stateflow',
    routingTag: 'SECTION',
    routingLabel: 'Sublayer 3B to 3C analysis routing',
    routingDisplay: 'grid',
    routingGridArea: 'routing',
    routingColumns: 3,
    connector3bcBeforeWidth: '6px',
    connector3bcAfterWidth: '52px',
    connector3bcAfterClip: true,
    threeADisplay: 'grid',
    threeAColumns: 2,
    sublayerBorderStyle: 'dotted',
    materialBankRole: 'source-plane-material-field',
    materialBankColumns: 2,
    modalityBankRole: 'modality-object-bank',
    modalityBankColumns: 2,
    modalityBorderStyle: 'solid',
    modalityColumns: 1,
    modalityObjectGridArea: '2',
    transferRailDisplay: 'flex',
    transferRailGridColumnStart: '3',
    transferRailPosition: 'absolute',
    transferRailWritingMode: 'vertical-rl',
    transferRailWidth: 64,
    heldRailText: 'Held in 3B',
    heldRailPosition: 'static',
    heldRailGridColumnStart: '1',
    heldRailAlignSelf: 'start',
    heldRailWhiteSpace: 'nowrap',
    heldRailWritingMode: 'horizontal-tb',
    ghostSlotDisplay: 'block',
    ghostSlotBorderStyle: 'dashed',
    arrowDisplay: 'block',
    chipRadius: '0px',
    laneLegendDisplay: 'grid',
    laneLegendColumns: 5,
    laneLabelTransform: 'uppercase',
    inputBankRole: 'input-bank',
    processNodeRole: 'process-status',
    outputFieldRole: 'output-field',
    outputFieldHeading: 'Output / Result Field',
    outputFieldBorderStyle: 'dotted',
    laneFrameRole: 'analysis-environment-lane',
    laneFrameBorderTopStyle: 'solid',
    laneSpineDisplay: 'block',
  });

  const desktopFit = await page.evaluate(() => {
    const panel = document.querySelector('.sublayer-map-panel');
    const band = document.querySelector('.sublayer-map-band');
    return {
      pageFitsViewport: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      panelFitsBand: panel.scrollWidth <= band.clientWidth + 1,
      mapIsPrimarySurface: band.getBoundingClientRect().height >= window.innerHeight * 0.82,
    };
  });
  expect(desktopFit).toEqual({
    pageFitsViewport: true,
    panelFitsBand: true,
    mapIsPrimarySurface: true,
  });

  await page.setViewportSize({ width: 1500, height: 820 });
  const desktopBreakpointFit = await page.evaluate(() => {
    const panel = document.querySelector('.sublayer-map-panel');
    const band = document.querySelector('.sublayer-map-band');
    const firstPlaneFlow = document.querySelector('.analysis-plane .plane-flow');
    const laneLegend = document.querySelector('.analysis-lane-legend');
    return {
      pageFitsViewport: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      panelFitsBand: panel.scrollWidth <= band.clientWidth + 1,
      planeColumnCount: window.getComputedStyle(firstPlaneFlow).gridTemplateColumns.split(' ').filter(Boolean).length,
      laneLegendColumns: window.getComputedStyle(laneLegend).gridTemplateColumns.split(' ').filter(Boolean).length,
    };
  });
  expect(desktopBreakpointFit).toEqual({
    pageFitsViewport: true,
    panelFitsBand: true,
    planeColumnCount: 5,
    laneLegendColumns: 5,
  });

  await page.setViewportSize({ width: 1440, height: 820 });
  const mediumFit = await page.evaluate(() => {
    const firstPlaneFlow = document.querySelector('.analysis-plane .plane-flow');
    const firstPlaneColumnCount = window.getComputedStyle(firstPlaneFlow).gridTemplateColumns.split(' ').filter(Boolean).length;
    const laneLegend = window.getComputedStyle(document.querySelector('.analysis-lane-legend'));
    const laneSpine = window.getComputedStyle(document.querySelector('.plane-lane-spine'));
    return {
      fitsViewport: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      planeColumnCount: firstPlaneColumnCount,
      laneLegendDisplay: laneLegend.display,
      laneSpineDisplay: laneSpine.display,
    };
  });
  expect(mediumFit).toEqual({
    fitsViewport: true,
    planeColumnCount: 5,
    laneLegendDisplay: 'grid',
    laneSpineDisplay: 'block',
  });

  await page.setViewportSize({ width: 1024, height: 768 });
  const tabletFit = await page.evaluate(() => {
    const panel = window.getComputedStyle(document.querySelector('#sublayer-map-panel'));
    const intake = window.getComputedStyle(document.querySelector('.canvas-intake-spec'));
    const routing = window.getComputedStyle(document.querySelector('.analysis-routing-plane'));
    const workflow = window.getComputedStyle(document.querySelector('.workflow-canvas-field'));
    return {
      fitsViewport: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      panelTemplateIncludesWorkflow: panel.gridTemplateAreas.includes('workflow'),
      workflowGridArea: workflow.gridArea,
      intakeColumnCount: intake.gridTemplateColumns.split(' ').filter(Boolean).length,
      routingDisplay: routing.display,
    };
  });
  expect(tabletFit).toEqual({
    fitsViewport: true,
    panelTemplateIncludesWorkflow: true,
    workflowGridArea: 'workflow',
    intakeColumnCount: 1,
    routingDisplay: 'grid',
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('#sublayer-map-panel')).toBeVisible();
  await expect(page.locator('.sublayer-3a')).toBeVisible();
  await expect(page.locator('.sublayer-3b')).toBeVisible();
  await expect(page.locator('.sublayer-3c')).toBeVisible();
  const mobileFit = await page.evaluate(() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1);
  expect(mobileFit).toBe(true);
});

test('Layer 3 workbench keeps unsupported-only Gate C material out of 3C routed-input state', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 820 });
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('workbench');

  await page.evaluate(() => {
    const authorityRail = {
      current_gate: 'gate_c',
      session_id: 'unsupported-only-session',
      persistence_status: 'not_committed',
      approved_material_count: 0,
      denied_material_count: 0,
      isolated_material_count: 0,
      flagged_material_count: 1,
      typing_status: 'previewed',
    };
    State.materialPreview = null;
    State.gateB = {
      schema_id: 'layer3.gate_b_decision_result.v1',
      session_id: 'unsupported-only-session',
      approved_candidate_ids: [],
      denied_candidate_ids: [],
      isolated_candidate_ids: [],
      flagged_candidate_ids: ['unsupported-snapshot-1'],
      authority_rail: authorityRail,
    };
    State.gateC = {
      schema_id: 'layer3.gate_c_preview_result.v1',
      session_id: 'unsupported-only-session',
      typing_records: [],
      unsupported_material: [{
        material_snapshot_id: 'unsupported-snapshot-1',
        owner_service_source_shape: 'unsupported_shape',
        reason: 'unsupported-only visual proof',
      }],
      authority_rail: authorityRail,
    };
    State.planPreview = null;
    State.planApproval = null;
    State.planRevision = null;
    State.sessionSummary = null;
    clearResultReviewState();
    renderAll();
  });

  await expect(page.locator('.modality-bucket.modality-unclassified')).toContainText('Unsupported material');
  await expect(page.locator('.modality-bucket.modality-unclassified .diagram-chip')).toHaveCount(1);
  await expect(page.locator('.analysis-plane .plane-inputs .diagram-chip')).toHaveCount(0);
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-viz-state', 'session|typed|structural');
  await expect(page.locator('.state-3c')).toContainText('Structural only');
});
