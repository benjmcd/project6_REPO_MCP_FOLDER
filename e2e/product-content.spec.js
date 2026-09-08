import { test, expect } from '@playwright/test';

const CONTENT_PATH = '**/api/v1/layer3/analysis-product/*/content?*';

function productSummary(sessionId = 'reader-session', productIds = ['product-a', 'product-b']) {
  return {
    schema_id: 'layer3.workbench_session_summary.v1',
    session_id: sessionId,
    analysis_product_inventory_projection: {
      schema_id: 'layer3.analysis_product_inventory_projection.v1',
      no_side_effects: true,
      inventory_state: 'available',
      analyst_products: productIds.map((id) => ({
        product_id: `layer3_analyst_product:${id}`,
        product_kind: 'analyst_note',
        lifecycle_status: 'draft',
        title: `Stored ${id}`,
        evidence_count: 2,
      })),
    },
  };
}

function productContent(productId = 'product-a', sessionId = 'reader-session') {
  return {
    schema_id: 'layer3.analysis_product_content.v1',
    session_id: sessionId,
    analysis_product: {
      analysis_product_id: productId,
      title: `Stored ${productId}`,
      body: `Full body for ${productId} in ${sessionId}.`,
      product_kind: 'analyst_note',
      executor_type: 'human',
      lifecycle_status: 'draft',
      is_non_evidentiary: false,
      basis_hash: 'a'.repeat(64),
      spec_hash: 'b'.repeat(64),
      created_at: '2026-09-07T12:00:00+00:00',
    },
    evidence_refs: [
      { ref_kind: 'material_snapshot', ref_id: 'snapshot-identity', evidence_role: 'observation' },
      { ref_kind: 'pass_run', ref_id: 'pass-identity', evidence_role: 'measurement' },
    ],
    evidence_refs_total: 2,
    evidence_refs_truncated: false,
  };
}

async function openProducts(page, summary = productSummary()) {
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#event-list')).toContainText('Workbench bootstrap loaded.');
  await page.evaluate((session) => {
    State.sessionSummary = session;
    State.activeOperationId = 'analysis-product-workspace-band';
    State.operationDockManual = true;
    renderAll();
  }, summary);
  await expect(page.locator('#analysis-product-workspace-band')).toBeVisible();
}

async function readProduct(page, id = 'product-a') {
  await page.locator('#apw-read-product').selectOption(id);
  await page.locator('#apw-read-submit').click();
}

async function finishResponse(page, response) {
  await (await response).finished();
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

test('Product content requires an explicit read and renders full literal wrapped text', async ({ page }) => {
  const content = productContent();
  content.analysis_product.title = '<img src=x onerror="window.contentExecuted=true"> Literal <title> & "quotes"';
  content.analysis_product.body = 'Conclusion: descriptive only.\n\nLimitations: no causal or seasonal inference.\n'
    + '<script>window.contentExecuted=true</script> <svg onload="window.contentExecuted=true"></svg>\n'
    + `Long token: ${'retained-evidence-'.repeat(500)}\nEnd of stored body.`;
  const reads = [];
  const mutations = [];
  await page.route(CONTENT_PATH, async (route) => {
    reads.push(route.request().url());
    expect(route.request().method()).toBe('GET');
    await route.fulfill({ json: content });
  });
  await openProducts(page);
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/layer3/') && request.method() !== 'GET') mutations.push(request.url());
  });
  await expect(page.locator('#apw-read-submit')).toBeDisabled();
  await expect(page.locator('#apw-content-view')).toBeHidden();
  await page.locator('#apw-read-product').selectOption('product-a');
  expect(reads).toEqual([]);
  await page.locator('#apw-read-submit').click();
  await expect(page.locator('#apw-content-title')).toHaveText(content.analysis_product.title);
  expect(await page.locator('#apw-content-body').textContent()).toBe(content.analysis_product.body);
  await expect(page.locator('#apw-content-metadata')).toContainText('reader-session');
  await expect(page.locator('#apw-content-metadata')).toContainText('product-a');
  await expect(page.locator('#apw-content-metadata')).toContainText('draft');
  await expect(page.locator('#apw-content-metadata')).toContainText('human');
  await expect(page.locator('#apw-content-metadata')).toContainText('technical authoring mode');
  await expect(page.locator('#apw-content-metadata')).toContainText(content.analysis_product.basis_hash);
  await expect(page.locator('#apw-content-evidence')).toContainText('snapshot-identity');
  await expect(page.locator('#apw-content-evidence')).toContainText('pass-identity');
  await expect(page.locator('#apw-content-evidence')).toContainText('2 of 2');
  await expect(page.locator('#apw-content-view script, #apw-content-view img, #apw-content-view svg, #apw-content-view a')).toHaveCount(0);
  expect(await page.evaluate(() => window.contentExecuted)).toBeUndefined();
  for (const width of [1280, 620]) {
    await page.setViewportSize({ width, height: 850 });
    const layout = await page.locator('#apw-content-body').evaluate((body) => ({
      whiteSpace: getComputedStyle(body).whiteSpace,
      overflowWrap: getComputedStyle(body).overflowWrap,
      width: body.clientWidth,
      scrollWidth: body.scrollWidth,
      height: body.clientHeight,
      lineHeight: parseFloat(getComputedStyle(body).lineHeight),
    }));
    expect(layout.whiteSpace).toBe('pre-wrap');
    expect(layout.overflowWrap).toBe('anywhere');
    expect(layout.scrollWidth).toBeLessThanOrEqual(layout.width + 1);
    expect(layout.height).toBeGreaterThan(layout.lineHeight * 5);
  }
  expect(reads).toHaveLength(1);
  expect(new URL(reads[0]).pathname).toBe('/api/v1/layer3/analysis-product/product-a/content');
  expect(new URL(reads[0]).searchParams.get('session_id')).toBe('reader-session');
  expect(mutations).toEqual([]);
});

test('Product selection and removed inventory entries clear prior content without fetching', async ({ page }) => {
  let reads = 0;
  await page.route(CONTENT_PATH, (route) => {
    reads += 1;
    return route.fulfill({ json: productContent() });
  });
  await openProducts(page);
  await readProduct(page);
  await expect(page.locator('#apw-content-body')).toContainText('Full body for product-a');
  await page.locator('#apw-read-product').selectOption('product-b');
  await expect(page.locator('#apw-content-view')).toBeHidden();
  await expect(page.locator('#apw-content-view')).toBeEmpty();
  expect(reads).toBe(1);
  await page.evaluate((summary) => { State.sessionSummary = summary; renderAll(); }, productSummary('reader-session', []));
  await expect(page.locator('#apw-read-product')).toHaveValue('');
  await expect(page.locator('#apw-read-submit')).toBeDisabled();
  expect(reads).toBe(1);
});

test('Product reader preserves stored carriage returns and tabs exactly', async ({ page }) => {
  const content = productContent();
  content.analysis_product.title = 'Stored\r\ntitle';
  content.analysis_product.body = 'Observation\r\n\tIndented limitation\rConclusion';
  await page.route(CONTENT_PATH, (route) => route.fulfill({ json: content }));
  await openProducts(page);
  await readProduct(page);
  await expect(page.locator('#apw-content-view')).toBeVisible();
  expect(await page.locator('#apw-content-title').textContent()).toBe(content.analysis_product.title);
  expect(await page.locator('#apw-content-body').textContent()).toBe(content.analysis_product.body);
});

for (const selectionChange of ['product', 'session', 'refresh']) {
  for (const outcome of ['success', 'failure']) {
    test(`Product reader ignores stale ${outcome} after ${selectionChange} change and retains newer busy state`, async ({ page }) => {
      let releaseOld;
      let releaseNew;
      const oldGate = new Promise((resolve) => { releaseOld = resolve; });
      const newGate = new Promise((resolve) => { releaseNew = resolve; });
      let readCount = 0;
      const newProductId = selectionChange === 'refresh' ? 'product-a' : 'product-b';
      const newSessionId = selectionChange === 'session' ? 'new-reader-session' : 'reader-session';
      await page.route(CONTENT_PATH, async (route) => {
        const first = ++readCount === 1;
        await (first ? oldGate : newGate);
        await route.fulfill(first && outcome === 'failure'
          ? { status: 503, json: { message: 'Obsolete content error' } }
          : { json: productContent(first ? 'product-a' : newProductId, first ? 'reader-session' : newSessionId) });
      });
      await openProducts(page);
      const firstRequest = page.waitForRequest(CONTENT_PATH);
      await readProduct(page);
      await firstRequest;
      await expect(page.locator('#apw-read-submit')).toBeDisabled();
      if (selectionChange !== 'product') {
        await page.route(`**/api/v1/layer3/session/${newSessionId}`, (route) => route.fulfill({ json: productSummary(newSessionId) }));
        if (selectionChange === 'session') {
          await page.locator('#result-session-reopen-id').fill(newSessionId);
          await page.locator('#result-session-reopen').click();
        } else {
          await page.locator('#result-review-refresh').click();
        }
        await expect.poll(() => page.evaluate(() => State.sessionSummary?.session_id)).toBe(newSessionId);
        await expect(page.locator('#apw-read-product')).toBeEnabled();
      }
      await page.locator('#apw-read-product').selectOption(newProductId);
      await expect(page.locator('#apw-content-view')).toBeHidden();
      await expect(page.locator('#apw-read-submit')).toBeEnabled();
      const secondRequest = page.waitForRequest(CONTENT_PATH);
      await page.locator('#apw-read-submit').click();
      await secondRequest;
      const oldResponse = page.waitForResponse(CONTENT_PATH);
      releaseOld();
      await finishResponse(page, oldResponse);
      await expect(page.locator('#apw-read-submit')).toBeDisabled();
      await expect(page.locator('#apw-read-status')).toContainText('Reading product');
      await expect(page.locator('#apw-read-status')).not.toContainText('Obsolete');
      await expect(page.locator('#apw-content-view')).toBeHidden();
      const newResponse = page.waitForResponse(CONTENT_PATH);
      releaseNew();
      await finishResponse(page, newResponse);
      await expect(page.locator('#apw-content-body')).toHaveText(`Full body for ${newProductId} in ${newSessionId}.`);
      await expect(page.locator('#apw-read-submit')).toBeEnabled();
      await expect(page.locator('#apw-read-status')).not.toContainText('Obsolete');
    });
  }
}

for (const invalidField of ['session', 'product', 'schema', 'body', 'evidence']) {
  test(`Product reader rejects a mismatched or incomplete ${invalidField} response`, async ({ page }) => {
    const content = productContent();
    if (invalidField === 'session') content.session_id = 'another-session';
    if (invalidField === 'product') content.analysis_product.analysis_product_id = 'another-product';
    if (invalidField === 'schema') content.schema_id = 'layer3.analysis_product.v1';
    if (invalidField === 'body') delete content.analysis_product.body;
    if (invalidField === 'evidence') content.evidence_refs_total = 0;
    await page.route(CONTENT_PATH, (route) => route.fulfill({ json: content }));
    await openProducts(page);
    await readProduct(page);
    await expect(page.locator('#apw-read-status')).toContainText('Unable to read product');
    await expect(page.locator('#apw-content-view')).toBeHidden();
    await expect(page.locator('#apw-content-view')).toBeEmpty();
    await expect(page.locator('#apw-read-submit')).toBeEnabled();
  });
}

test('Product reader reports missing content and clears errors when selection changes', async ({ page }) => {
  await page.route(CONTENT_PATH, (route) => route.fulfill({ status: 404, json: { message: 'Analysis product not found.' } }));
  await openProducts(page);
  await readProduct(page);
  await expect(page.locator('#apw-read-status')).toContainText('Analysis product not found.');
  await expect(page.locator('#apw-content-view')).toBeHidden();
  await expect(page.locator('#apw-read-submit')).toBeEnabled();
  await page.locator('#apw-read-product').selectOption('product-b');
  await expect(page.locator('#apw-read-status')).not.toContainText('not found');
});

test('Product reader labels truncated evidence identities without inventing approval', async ({ page }) => {
  const content = productContent();
  content.evidence_refs_total = 240;
  content.evidence_refs_truncated = true;
  content.analysis_product.lifecycle_status = 'challenged';
  content.analysis_product.executor_type = 'deterministic';
  await page.route(CONTENT_PATH, (route) => route.fulfill({ json: content }));
  await openProducts(page);
  await readProduct(page);
  await expect(page.locator('#apw-content-evidence')).toContainText('2 of 240');
  await expect(page.locator('#apw-content-evidence')).toContainText('truncated');
  await expect(page.locator('#apw-content-metadata')).toContainText('challenged');
  await expect(page.locator('#apw-content-metadata')).toContainText('deterministic');
  await expect(page.locator('#apw-content-metadata')).not.toContainText('approved');
});
