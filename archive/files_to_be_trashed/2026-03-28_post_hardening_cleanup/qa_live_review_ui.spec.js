const { test, expect } = require('playwright/test');

const BASE_URL = 'http://127.0.0.1:8010/review/nrc-aps';
const GOLDEN_RUN = 'd6be0fff-bbd7-468a-9b00-7103d5995494';

test('live review UI projections diverge by mode', async ({ page }) => {
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });

  const runSelector = page.locator('#run-selector');
  await expect(runSelector).toBeVisible();
  await expect(runSelector).toHaveValue(GOLDEN_RUN);

  const mermaidContainer = page.locator('#mermaid-container');
  await expect(mermaidContainer.locator('svg')).toBeVisible();

  await page.locator('#view-general + label').click();
  await expect(page.locator('#tree-pane .pane-header')).toHaveText('Pipeline Layout Summary');
  await expect(mermaidContainer.locator('text').filter({ hasText: 'Branch A' })).toBeVisible();
  await expect(mermaidContainer.locator('text').filter({ hasText: 'Branch B' })).toBeVisible();
  const generalNodeCount = await mermaidContainer.locator('g.node').count();

  await mermaidContainer.locator('g.node').filter({ hasText: 'Branch A' }).first().click();
  await expect(page.locator('#details-content')).toContainText('Conceptual Stage');
  await expect(page.locator('#details-content')).toContainText('Branch A');

  await page.locator('#view-run + label').click();
  await expect(page.locator('#tree-pane .pane-header')).toHaveText('Strict Filesystem Tree');
  const runNodeCount = await mermaidContainer.locator('g.node').count();
  expect(runNodeCount).toBeGreaterThan(generalNodeCount);
  await expect(mermaidContainer.locator('text').filter({ hasText: 'aps_content_index_run_v1.json' })).toBeVisible();
  await expect(mermaidContainer.locator('text').filter({ hasText: 'd6be0fff-bbd7-468a-9b00-7103d5995494' })).toBeVisible();

  await page.locator('#file-tree .tree-row').filter({ hasText: 'local_corpus_e2e_summary.json' }).click();
  await expect(page.locator('#details-content')).toContainText('local_corpus_e2e_summary.json');
  await expect(page.locator('#details-content')).toContainText('Preview');
});
