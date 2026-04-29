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

function formPostPayload(request) {
  const payload = {};
  const params = new URLSearchParams(request.postData() || '');
  for (const [key, value] of params.entries()) {
    payload[key] = JSON.parse(value);
  }
  return payload;
}

async function expectStepAvailable(page, step) {
  const chip = page.locator(`[data-step="${step}"]`);
  await expect(chip).toBeEnabled();
  await expect(chip).toHaveAttribute('data-available', 'true');
  await expect(chip).not.toHaveClass(/unavailable/);
}

async function expectStepUnavailable(page, step) {
  const chip = page.locator(`[data-step="${step}"]`);
  await expect(chip).toBeEnabled();
  await expect(chip).toHaveAttribute('data-available', 'false');
  await expect(chip).toHaveClass(/unavailable/);
}

test('Layer 3 workbench keeps the Workbench theme preference page-local', async ({ page }) => {
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

test('Layer 3 workbench applies mockup-informed Workbench visual boundaries without degrading shared themes', async ({ page }) => {
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('workbench');
  await page.reload({ waitUntil: 'domcontentloaded' });

  const workbenchStyles = await page.evaluate(() => {
    const bodyStyle = window.getComputedStyle(document.body);
    const railStyle = window.getComputedStyle(document.querySelector('.authority-rail'));
    const workbandStyle = window.getComputedStyle(document.querySelector('#gate-b-band'));
    const fieldsetStyle = window.getComputedStyle(document.querySelector('#source-fieldset'));
    const chipStyle = window.getComputedStyle(document.querySelector('[data-step="gate_b"]'));
    return {
      bodyBackground: bodyStyle.backgroundColor,
      railBorderStyle: railStyle.borderTopStyle,
      railBackground: railStyle.backgroundColor,
      workbandBorderStyle: workbandStyle.borderTopStyle,
      workbandBorderLeftWidth: workbandStyle.borderLeftWidth,
      workbandBorderLeftColor: workbandStyle.borderLeftColor,
      fieldsetBorderStyle: fieldsetStyle.borderTopStyle,
      chipBackground: chipStyle.backgroundColor,
    };
  });
  expect(workbenchStyles).toMatchObject({
    bodyBackground: 'rgb(13, 13, 13)',
    railBorderStyle: 'solid',
    workbandBorderStyle: 'dotted',
    workbandBorderLeftWidth: '2px',
    workbandBorderLeftColor: 'rgb(204, 255, 153)',
    fieldsetBorderStyle: 'dashed',
  });
  expect(workbenchStyles.railBackground).not.toBe('rgba(0, 0, 0, 0)');
  expect(workbenchStyles.chipBackground).not.toBe('rgba(0, 0, 0, 0)');

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
  await expect(page.locator('.canvas-intake-spec')).toContainText('User Natural Language Query Input');
  await expect(page.locator('.manual-source-spec')).toContainText('Dataset version');
  await expect(page.locator('.manual-source-spec')).toContainText('APS content document');
  await expect(page.locator('.ledger-chip-field')).toBeVisible();
  await expect(page.locator('.ledger-bracket')).toContainText('Session-scoped Materials');
  await expect(page.locator('.plane-arrow-process').first()).toBeVisible();
  await expect(page.locator('.plane-bracket').first()).toBeVisible();
  await expect(page.locator('.sublayer-3a .flow-empty')).toContainText('No material preview');
  await expect(page.locator('.modality-bucket.modality-quantitative')).toContainText('No quantitative objects');
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
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-column').first()).toContainText('modality quantitative');
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-process')).toContainText('No live process yet');
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-column').last()).toContainText('No live output');

  const diagramStyles = await page.evaluate(() => {
    const sublayer = window.getComputedStyle(document.querySelector('.sublayer-3a'));
    const modality = window.getComputedStyle(document.querySelector('.modality-bucket.modality-quantitative'));
    const arrow = window.getComputedStyle(document.querySelector('.plane-arrow-process'));
    const chip = window.getComputedStyle(document.querySelector('.sublayer-3a .diagram-chip'));
    const intake = window.getComputedStyle(document.querySelector('.canvas-intake-spec'));
    return {
      intakeDisplay: intake.display,
      intakeGridArea: intake.gridArea,
      sublayerBorderStyle: sublayer.borderTopStyle,
      modalityBorderStyle: modality.borderTopStyle,
      arrowDisplay: arrow.display,
      chipRadius: chip.borderTopLeftRadius,
    };
  });
  expect(diagramStyles).toEqual({
    intakeDisplay: 'grid',
    intakeGridArea: 'spec',
    sublayerBorderStyle: 'dotted',
    modalityBorderStyle: 'solid',
    arrowDisplay: 'block',
    chipRadius: '0px',
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

  await page.setViewportSize({ width: 1024, height: 768 });
  const tabletFit = await page.evaluate(() => {
    const intake = window.getComputedStyle(document.querySelector('.canvas-intake-spec'));
    return {
      fitsViewport: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      intakeColumnCount: intake.gridTemplateColumns.split(' ').filter(Boolean).length,
    };
  });
  expect(tabletFit).toEqual({
    fitsViewport: true,
    intakeColumnCount: 1,
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('#sublayer-map-panel')).toBeVisible();
  await expect(page.locator('.sublayer-3a')).toBeVisible();
  await expect(page.locator('.sublayer-3b')).toBeVisible();
  await expect(page.locator('.sublayer-3c')).toBeVisible();
  const mobileFit = await page.evaluate(() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1);
  expect(mobileFit).toBe(true);
});

async function prepareExecutedLayer3Session(request, seedPath = '/__test/layer3/seed-quant') {
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
  await expectStepUnavailable(page, 'plan');
  await expectStepUnavailable(page, 'execution');
  await expectStepUnavailable(page, 'results');
  await expectStepUnavailable(page, 'package');
  await expect(page.locator('#result-review-refresh')).toBeDisabled();
  await expect(page.locator('#result-status-inspect')).toBeDisabled();
  await expect(page.locator('#result-review-submit')).toBeDisabled();
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-delivery-submit')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Start Execution' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Rerun' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Export' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Download' })).toHaveCount(0);
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
  await expectStepUnavailable(page, 'plan');

  const gateCCommitResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/gate-c/preview'));
  await page.locator('#gate-c-commit').click();
  const gateCCommit = await expectJson(await gateCCommitResponsePromise);
  expect(gateCCommit.next_state).toBe('plan_preview_ready');
  expect(gateCCommit.typing_records[0].authoritative).toBe(true);

  await expect(page.locator('#gate-c-panel')).toContainText('Authoritative: yes');
  await expect(page.locator('#gate-c-preview')).toBeDisabled();
  await expectStepAvailable(page, 'plan');
  await expect(page.locator('#plan-preview')).toBeEnabled();

  const planPreviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/plan/preview'));
  await page.locator('#plan-preview').click();
  const planPreview = await expectJsonStatus(await planPreviewResponsePromise, 409);
  expect(planPreview.error_code).toBe('no_admissible_plan');

  await expect(page.locator('#plan-panel')).toContainText('Plan Preview Blocked');
  await expect(page.locator('#plan-panel')).toContainText('no_admissible_plan');
  await expect(page.locator('#unavailable-list')).toContainText('package');
  await expectStepUnavailable(page, 'execution');
  await expectStepUnavailable(page, 'package');
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
  await expectStepUnavailable(page, 'execution');
  await expectStepUnavailable(page, 'results');
  await expectStepUnavailable(page, 'package');
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();
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
  await expectStepAvailable(page, 'execution');
  await expectStepAvailable(page, 'results');
  await expectStepUnavailable(page, 'package');

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
  await expectStepUnavailable(page, 'package');
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();
});

test('Layer 3 workbench prepares handoff and dispatches bounded APS handoff after approved package review', async ({ page, request }) => {
  const setup = await prepareExecutedLayer3Session(request, '/__test/layer3/seed-aps-handoff');

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
  await expectStepAvailable(page, 'package');

  const postCommitSummaryPattern = `**/api/v1/layer3/session/${setup.seed.session_id}`;
  const blockPostCommitSummary = async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({
        schema_id: 'layer3.workbench_error.v1',
        error_code: 'forced_post_commit_session_refresh_failure',
        message: 'Forced post-commit session refresh failure for UI fallback proof.',
      }),
    });
    await page.unroute(postCommitSummaryPattern, blockPostCommitSummary);
  };
  await page.route(postCommitSummaryPattern, blockPostCommitSummary);

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
  expect((await postCommitSummaryPromise).status()).toBe(503);

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
  expect(submit.downstream_unavailable).toEqual(['aps_handoff', 'external_export', 'downstream_dispatch']);
  await expectJson(await postSubmitSummaryPromise);

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_approved');
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('handoff_export_ready');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('internal_export_envelope');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('prepare_only');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeEnabled();

  await page.locator('#handoff-export-prepare-decision').selectOption('hold');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await page.locator('#handoff-export-prepare-notes').fill('Holding the preparation requires notes.');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeEnabled();
  await page.locator('#handoff-export-prepare-decision').selectOption('authorize_prepare');
  await page.locator('#handoff-export-prepare-notes').fill('');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeEnabled();

  const prepareRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/export/prepare'));
  const prepareResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/export/prepare'));
  const postPrepareSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#handoff-export-prepare-submit').click();
  const prepareRequest = await prepareRequestPromise;
  const preparePayload = prepareRequest.postDataJSON();
  const committedPackageIds = commit.output_packages.map((item) => item.output_package_id);
  const expectedPrepareKeys = [
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
    'handoff_target',
    'export_mode',
    'operator_decision',
    'expected_package_kinds',
  ];
  if (preparePayload.analysis_run_id) expectedPrepareKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(preparePayload, expectedPrepareKeys);
  expect(preparePayload.session_id).toBe(setup.seed.session_id);
  expect(preparePayload.analysis_plan_id).toBe(setup.approval.analysis_plan_id);
  expect(preparePayload.pass_run_id).toBe(setup.passRunId);
  expect(preparePayload.preview_id).toBe(setup.planPreview.preview_id);
  expect(preparePayload.preview_hash).toBe(setup.planPreview.preview_hash);
  expect(preparePayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(preparePayload.package_review_preview_hash).toBe(preview.package_review_preview_hash);
  expect(preparePayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(preparePayload.package_review_submit_record_ref).toBe(submit.submit_record_ref);
  expect(preparePayload.package_review_state).toBe('package_review_approved');
  expect(preparePayload.handoff_target).toBe('internal_export_envelope');
  expect(preparePayload.export_mode).toBe('prepare_only');
  expect(preparePayload.operator_decision).toBe('authorize_prepare');
  expect([...preparePayload.output_package_ids].sort()).toEqual([...committedPackageIds].sort());
  expect(preparePayload.payload_refs).toEqual(commit.payload_refs);
  expect(preparePayload.payload_hashes).toEqual(commit.payload_hashes);
  expect(preparePayload.expected_package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
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
    expect(preparePayload).not.toHaveProperty(forbidden);
  }

  const prepare = await expectJson(await prepareResponsePromise);
  expect(prepare.schema_id).toBe('layer3.handoff_export_prepare.v1');
  expect(prepare.status).toBe('prepared');
  expect(prepare.handoff_export_state).toBe('handoff_export_prepared');
  expect(prepare.handoff_target).toBe('internal_export_envelope');
  expect(prepare.export_mode).toBe('prepare_only');
  expect(prepare.external_handoff_enabled).toBe(false);
  expect(prepare.external_export_enabled).toBe(false);
  expect(prepare.dispatch_enabled).toBe(false);
  expect(prepare.downstream_unavailable).toEqual(['aps_handoff', 'external_export', 'downstream_dispatch']);
  expect([...prepare.handoff_export_envelope.output_package_ids].sort()).toEqual([...committedPackageIds].sort());
  expect(prepare.handoff_export_envelope.payload_refs).toEqual(commit.payload_refs);
  expect(prepare.handoff_export_envelope.payload_hashes).toEqual(commit.payload_hashes);
  await expectJson(await postPrepareSummaryPromise);

  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('handoff_export_prepared');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('aps handoff');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('external export');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('downstream dispatch');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_handoff_ready');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_evidence_bundle');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('server_side_aps_handoff');
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeEnabled();
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();

  const dispatchRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/aps/dispatch'));
  const dispatchResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/aps/dispatch'));
  const postDispatchSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#aps-handoff-dispatch-submit').click();
  const dispatchRequest = await dispatchRequestPromise;
  const dispatchPayload = dispatchRequest.postDataJSON();
  const expectedDispatchKeys = [
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
    'package_kinds',
    'payload_refs',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
    'prepare_record_ref',
    'handoff_export_state',
    'handoff_export_envelope_ref',
    'handoff_target',
    'export_mode',
    'aps_handoff_target',
    'dispatch_mode',
    'operator_decision',
  ];
  if (dispatchPayload.analysis_run_id) expectedDispatchKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(dispatchPayload, expectedDispatchKeys);
  expect(dispatchPayload.session_id).toBe(setup.seed.session_id);
  expect(dispatchPayload.analysis_plan_id).toBe(setup.approval.analysis_plan_id);
  expect(dispatchPayload.pass_run_id).toBe(setup.passRunId);
  expect(dispatchPayload.preview_id).toBe(setup.planPreview.preview_id);
  expect(dispatchPayload.preview_hash).toBe(setup.planPreview.preview_hash);
  expect(dispatchPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(dispatchPayload.package_review_preview_hash).toBe(preview.package_review_preview_hash);
  expect(dispatchPayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(dispatchPayload.package_review_submit_record_ref).toBe(submit.submit_record_ref);
  expect(dispatchPayload.package_review_state).toBe('package_review_approved');
  expect(dispatchPayload.prepare_record_ref).toBe(prepare.prepare_record_ref);
  expect(dispatchPayload.handoff_export_state).toBe('handoff_export_prepared');
  expect(dispatchPayload.handoff_export_envelope_ref).toBe(prepare.handoff_export_envelope.envelope_ref);
  expect(dispatchPayload.handoff_target).toBe('internal_export_envelope');
  expect(dispatchPayload.export_mode).toBe('prepare_only');
  expect(dispatchPayload.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(dispatchPayload.dispatch_mode).toBe('server_side_aps_handoff');
  expect(dispatchPayload.operator_decision).toBe('dispatch_aps_handoff');
  expect([...dispatchPayload.output_package_ids].sort()).toEqual([...committedPackageIds].sort());
  expect(dispatchPayload.package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
  expect(dispatchPayload.payload_refs).toEqual(commit.payload_refs);
  expect(dispatchPayload.payload_hashes).toEqual(commit.payload_hashes);
  for (const forbidden of [
    'external_export',
    'external_target',
    'download',
    'download_url',
    'destination',
    'destination_selector',
    'connector_run_id',
    'connector_dispatch',
    'dispatch',
    'send',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'package_variant_content',
    'rewrite_output',
    'edited_findings',
    'result_review_amendment',
    'package_review_amendment',
    'rerun',
    'retry',
    'recover',
    'cancel',
    'selected_pass_ids',
    'pass_run_ids',
    'new_analysis_plan',
    'plan_revision',
    'source_expansion',
    'local_upload',
    'local_directory',
    'schema_migration',
    'expected_package_kinds',
  ]) {
    expect(dispatchPayload).not.toHaveProperty(forbidden);
  }

  const dispatch = await expectJson(await dispatchResponsePromise);
  expect(dispatch.schema_id).toBe('layer3.aps_handoff_dispatch.v1');
  expect(dispatch.status).toBe('dispatched');
  expect(dispatch.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(dispatch.aps_output_package_kind).toBe('aps_evidence_bundle_handoff');
  expect(dispatch.external_export_enabled).toBe(false);
  expect(dispatch.download_enabled).toBe(false);
  expect(dispatch.connector_dispatch_enabled).toBe(false);
  expect(dispatch.downstream_unavailable).toEqual(['external_export', 'download', 'connector_dispatch', 'non_aps_dispatch']);
  const postDispatchSummary = await expectJson(await postDispatchSummaryPromise);
  expect(postDispatchSummary.external_export_download.state).toBe('external_export_download_ready');
  expect(postDispatchSummary.external_export_download.available).toBe(true);

  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_handoff_dispatched');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_evidence_bundle_handoff');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('external export');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('download');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('connector dispatch');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('non aps dispatch');
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('external_export_download_ready');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('aps_evidence_bundle_download_reference');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('reference_only_prepare');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('browser download');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('download url');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('connector dispatch');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('destination selection');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('generic downstream dispatch');
  await expect(page.locator('#external-export-download-prepare-submit')).toBeEnabled();

  const externalRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/export/download/prepare'));
  const externalResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/export/download/prepare'));
  const postExternalSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#external-export-download-prepare-submit').click();
  const externalRequest = await externalRequestPromise;
  const externalPayload = externalRequest.postDataJSON();
  const expectedExternalKeys = [
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
    'package_kinds',
    'payload_refs',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
    'prepare_record_ref',
    'handoff_export_state',
    'handoff_export_envelope_ref',
    'handoff_target',
    'export_mode',
    'aps_handoff_record_ref',
    'aps_handoff_state',
    'aps_handoff_target',
    'dispatch_mode',
    'aps_output_package_id',
    'aps_output_package_kind',
    'aps_bundle_ref',
    'aps_bundle_id',
    'aps_schema_id',
    'export_download_target',
    'download_mode',
    'operator_decision',
    'aps_bundle_hash',
    'aps_bundle_size_bytes',
  ];
  if (externalPayload.analysis_run_id) expectedExternalKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(externalPayload, expectedExternalKeys);
  expect(externalPayload.session_id).toBe(setup.seed.session_id);
  expect(externalPayload.analysis_plan_id).toBe(setup.approval.analysis_plan_id);
  expect(externalPayload.pass_run_id).toBe(setup.passRunId);
  expect(externalPayload.preview_id).toBe(setup.planPreview.preview_id);
  expect(externalPayload.preview_hash).toBe(setup.planPreview.preview_hash);
  expect(externalPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(externalPayload.package_review_preview_hash).toBe(preview.package_review_preview_hash);
  expect(externalPayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(externalPayload.package_review_submit_record_ref).toBe(submit.submit_record_ref);
  expect(externalPayload.package_review_state).toBe('package_review_approved');
  expect(externalPayload.prepare_record_ref).toBe(prepare.prepare_record_ref);
  expect(externalPayload.handoff_export_state).toBe('handoff_export_prepared');
  expect(externalPayload.handoff_export_envelope_ref).toBe(prepare.handoff_export_envelope.envelope_ref);
  expect(externalPayload.handoff_target).toBe('internal_export_envelope');
  expect(externalPayload.export_mode).toBe('prepare_only');
  expect(externalPayload.aps_handoff_record_ref).toBe(dispatch.aps_handoff_record_ref);
  expect(externalPayload.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(externalPayload.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(externalPayload.dispatch_mode).toBe('server_side_aps_handoff');
  expect(externalPayload.aps_output_package_id).toBe(dispatch.aps_output_package_id);
  expect(externalPayload.aps_output_package_kind).toBe('aps_evidence_bundle_handoff');
  expect(externalPayload.aps_bundle_ref).toBe(dispatch.aps_bundle_ref);
  expect(externalPayload.aps_bundle_id).toBe(dispatch.aps_bundle_id);
  expect(externalPayload.aps_schema_id).toBe(dispatch.aps_schema_id);
  expect(externalPayload.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(externalPayload.download_mode).toBe('reference_only_prepare');
  expect(externalPayload.operator_decision).toBe('prepare_external_export_download');
  expect(externalPayload.aps_bundle_hash).toBe(postDispatchSummary.external_export_download.source_artifact_hash);
  expect(externalPayload.aps_bundle_size_bytes).toBe(postDispatchSummary.external_export_download.source_artifact_size_bytes);
  expect([...externalPayload.output_package_ids].sort()).toEqual([...committedPackageIds].sort());
  expect(externalPayload.package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
  expect(externalPayload.payload_refs).toEqual(commit.payload_refs);
  expect(externalPayload.payload_hashes).toEqual(commit.payload_hashes);
  for (const forbidden of [
    'download_url',
    'public_url',
    'signed_url',
    'stream_file',
    'browser_download',
    'external_export',
    'send',
    'dispatch',
    'generic_dispatch',
    'connector_run_id',
    'connector_dispatch',
    'destination',
    'destination_id',
    'external_target',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'package_variant_content',
    'rewrite_output',
    'edited_findings',
    'result_review_amendment',
    'package_review_amendment',
    'handoff_export_amendment',
    'aps_handoff_amendment',
    'rerun',
    'retry',
    'recover',
    'cancel',
    'selected_pass_ids',
    'pass_run_ids',
    'new_analysis_plan',
    'plan_revision',
    'source_expansion',
    'local_upload',
    'local_directory',
    'schema_migration',
  ]) {
    expect(externalPayload).not.toHaveProperty(forbidden);
  }

  const external = await expectJson(await externalResponsePromise);
  expect(external.schema_id).toBe('layer3.external_export_download_prepare.v1');
  expect(external.status).toBe('prepared');
  expect(external.external_export_download_state).toBe('external_export_download_prepared');
  expect(external.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(external.download_mode).toBe('reference_only_prepare');
  expect(external.operator_decision).toBe('prepare_external_export_download');
  expect(external.browser_download_enabled).toBe(false);
  expect(external.download_url_enabled).toBe(false);
  expect(external.connector_dispatch_enabled).toBe(false);
  expect(external.destination_selection_enabled).toBe(false);
  expect(external.generic_downstream_dispatch_enabled).toBe(false);
  expect(external.downstream_unavailable).toEqual([
    'browser_download',
    'download_url',
    'connector_dispatch',
    'destination_selection',
    'generic_downstream_dispatch',
  ]);
  expect(external.external_export_download_descriptor.browser_download_enabled).toBe(false);
  expect(external.external_export_download_descriptor.download_url_enabled).toBe(false);
  const postExternalSummary = await expectJson(await postExternalSummaryPromise);
  expect(postExternalSummary.external_export_download.state).toBe('external_export_download_prepared');
  expect(postExternalSummary.external_export_download.available).toBe(false);

  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('external_export_download_prepared');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText(external.export_download_descriptor_ref);
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('browser download');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('download url');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('connector dispatch');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('destination selection');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('generic downstream dispatch');
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('external_export_download_delivery_ui_ready');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(external.external_export_download_record_ref);
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('same_origin_artifact_stream');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('public url');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('signed url');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('connector dispatch');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('destination selection');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('generic downstream dispatch');
  await expect(page.locator('#external-export-download-delivery-submit')).toBeEnabled();

  const deliveryRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/export/download/deliver'));
  const deliveryResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/export/download/deliver'));
  const downloadPromise = page.waitForEvent('download');
  const postDeliverySummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#external-export-download-delivery-submit').click();
  const deliveryRequest = await deliveryRequestPromise;
  expect(deliveryRequest.headers()['content-type']).toContain('application/x-www-form-urlencoded');
  const deliveryPayload = formPostPayload(deliveryRequest);
  const expectedDeliveryKeys = [
    ...expectedExternalKeys.filter((key) => key !== 'operator_decision'),
    'operator_decision',
    'external_export_download_record_ref',
    'export_download_descriptor_ref',
    'external_export_download_state',
    'delivery_mode',
  ];
  expectOnlyPayloadKeys(deliveryPayload, expectedDeliveryKeys);
  expect(deliveryPayload.operator_decision).toBe('deliver_external_export_download');
  expect(deliveryPayload.external_export_download_record_ref).toBe(external.external_export_download_record_ref);
  expect(deliveryPayload.export_download_descriptor_ref).toBe(external.export_download_descriptor_ref);
  expect(deliveryPayload.external_export_download_state).toBe('external_export_download_prepared');
  expect(deliveryPayload.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(deliveryPayload.download_mode).toBe('reference_only_prepare');
  expect(deliveryPayload.delivery_mode).toBe('same_origin_artifact_stream');
  for (const forbidden of [
    'download_url',
    'download_token',
    'public_url',
    'signed_url',
    'local_file_path',
    'external_target',
    'destination',
    'destination_selector',
    'destination_id',
    'connector_run_id',
    'connector_dispatch',
    'generic_dispatch',
    'dispatch',
    'send',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'package_variant_content',
    'rewrite_output',
    'edited_findings',
    'result_review_amendment',
    'package_review_amendment',
    'handoff_export_amendment',
    'aps_handoff_amendment',
    'rerun',
    'retry',
    'recover',
    'cancel',
    'selected_pass_ids',
    'pass_run_ids',
    'new_analysis_plan',
    'plan_revision',
    'source_expansion',
    'local_upload',
    'local_directory',
    'schema_migration',
  ]) {
    expect(deliveryPayload).not.toHaveProperty(forbidden);
  }

  const deliveryResponse = await deliveryResponsePromise;
  expect(deliveryResponse.status()).toBe(200);
  const deliveryHeaders = deliveryResponse.headers();
  expect(deliveryHeaders['x-layer3-schema-id']).toBe('layer3.external_export_download_delivery.v1');
  expect(deliveryHeaders['x-layer3-delivery-state']).toBe('external_export_download_delivered');
  expect(deliveryHeaders['x-layer3-external-export-download-record-ref']).toBe(external.external_export_download_record_ref);
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain('layer3-');
  const postDeliverySummary = await expectJson(await postDeliverySummaryPromise);
  expect(postDeliverySummary.external_export_download.state).toBe('external_export_download_prepared');

  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('external_export_download_delivery_submitted');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(deliveryHeaders['x-layer3-source-artifact-hash']);
  await expect(page.locator('#external-export-download-delivery-submit')).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Create Package' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Export' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Download' })).toHaveCount(0);
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
  await expectStepUnavailable(page, 'execution');
  await expectStepUnavailable(page, 'results');
  await expectStepUnavailable(page, 'package');
  await expect(page.locator('#unavailable-list')).toContainText('execution');
  await expect(page.locator('#unavailable-list')).toContainText('package');
});
