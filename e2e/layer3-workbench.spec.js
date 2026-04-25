import { test, expect } from '@playwright/test';

async function expectJson(response) {
  expect(response.status()).toBe(200);
  return response.json();
}

async function expectJsonStatus(response, status) {
  expect(response.status()).toBe(status);
  return response.json();
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
