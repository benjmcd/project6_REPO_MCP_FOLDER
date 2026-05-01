import { test, expect } from '@playwright/test';

const NO_PATH_TOKENS = ['C:\\\\', 'C:/Users/', 'C:\\Users\\'];

function expectNoLocalPath(value) {
  for (const token of NO_PATH_TOKENS) {
    expect(String(value)).not.toContain(token);
  }
}

async function expectJsonResponse(response) {
  expect(response.status()).toBe(200);
  const text = await response.text();
  expectNoLocalPath(text);
  return JSON.parse(text);
}

async function openWorkbenchCompare(page) {
  const sourcesResponsePromise = page.waitForResponse((response) => response.url().includes('/workbench-compare/sources'));
  const targetsResponsePromise = page.waitForResponse((response) => response.url().includes('/workbench-compare/targets?'));
  const manifestResponsePromise = page.waitForResponse(
    (response) => response.url().includes('/workbench-compare/targets/') && response.url().includes('/manifest'),
  );
  await page.goto('/review/nrc-aps/workbench-compare', { waitUntil: 'domcontentloaded' });
  const [sourcesResponse, targetsResponse, manifestResponse] = await Promise.all([
    sourcesResponsePromise,
    targetsResponsePromise,
    manifestResponsePromise,
  ]);
  return {
    sources: await expectJsonResponse(sourcesResponse),
    targets: await expectJsonResponse(targetsResponse),
    manifest: await expectJsonResponse(manifestResponse),
  };
}

test('NRC APS header exposes Layer3 workbench navigation', async ({ page }) => {
  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });
  const layer3Link = page.locator('header.app-header a.nav-link[href="/review/layer3"]');
  await expect(layer3Link).toHaveCount(1);
  await expect(layer3Link).toHaveText('Layer3');

  await Promise.all([
    page.waitForURL('**/review/layer3'),
    layer3Link.click(),
  ]);
  await expect(page.getByRole('heading', { name: 'Layer 3 Workbench' })).toBeVisible();
});

test('NRC APS run selectors label admitted Candidate B runtime distinctly', async ({ page }) => {
  const reviewRunsResponsePromise = page.waitForResponse((response) => response.url().endsWith('/api/v1/review/nrc-aps/runs'));
  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });
  const reviewRunsPayload = await expectJsonResponse(await reviewRunsResponsePromise);
  const candidateB = reviewRunsPayload.runs.find(
    (run) => run.runtime_binding?.document_processing_engine === 'candidate_b_opendataloader_pdf',
  );
  expect(candidateB).toBeTruthy();

  await expect(page.locator('#run-selector option').filter({ hasText: 'Baseline Run' })).toHaveCount(1);
  await expect(page.locator('#run-selector option').filter({ hasText: 'Candidate A Run' })).toHaveCount(1);
  await expect(page.locator('#run-selector option').filter({ hasText: 'Candidate B / OpenDataLoader PDF' })).toHaveCount(1);

  await page.selectOption('#run-selector', candidateB.run_id);
  await expect(page.locator('#current-run-info')).toContainText('Candidate B / OpenDataLoader PDF');
  await expect(page.locator('#current-run-info')).toContainText('Variant:');

  const documentTraceRunsResponsePromise = page.waitForResponse(
    (response) => response.url().endsWith('/api/v1/review/nrc-aps/runs'),
  );
  await page.goto(`/review/nrc-aps/document-trace?run_id=${encodeURIComponent(candidateB.run_id)}`, { waitUntil: 'domcontentloaded' });
  await expectJsonResponse(await documentTraceRunsResponsePromise);
  await expect(page.locator('#trace-workspace')).toBeVisible();
  await expect(page.locator('#run-selector')).toHaveValue(candidateB.run_id);
  await expect(page.locator('#run-selector option:checked')).toContainText('Candidate B / OpenDataLoader PDF');
  await expect(page.locator('#identity-summary')).toContainText('VARIANT');
  await expect(page.locator('#identity-summary')).toContainText('Candidate B / OpenDataLoader PDF');
});

test('workbench compare deep-links into Candidate B Trace and Candidate B Trace defaults to annotated PDF', async ({ page }) => {
  const { sources, targets, manifest } = await openWorkbenchCompare(page);

  expect(sources.baseline_runs).toHaveLength(1);
  expect(sources.candidate_a_runs).toHaveLength(1);
  expect(sources.candidate_b_bundles).toHaveLength(1);
  expect(targets.targets).toHaveLength(1);
  expect(manifest.deep_links.candidate_b_trace).toContain('/review/nrc-aps/candidate-b-trace?');
  expectNoLocalPath(manifest.deep_links.candidate_b_trace);

  await expect(page.locator('#compare-workspace')).toBeVisible();
  await expect(page.locator('#trace-link-cluster')).toContainText('Candidate B Trace');

  const candidateBTraceLink = page.locator('#trace-link-cluster a').filter({ hasText: 'Candidate B Trace' });
  await expect(candidateBTraceLink).toHaveCount(1);

  const traceManifestResponsePromise = page.waitForResponse((response) => response.url().includes('/candidate-b-trace/manifest'));
  const annotatedPdfResponsePromise = page.waitForResponse((response) => response.url().includes('/candidate-b-trace/annotated-pdf'));
  await Promise.all([
    page.waitForURL(/\/review\/nrc-aps\/candidate-b-trace\?/),
    candidateBTraceLink.click(),
  ]);

  const traceManifest = await expectJsonResponse(await traceManifestResponsePromise);
  expect(traceManifest.default_tab).toBe('annotated_pdf');
  expect(traceManifest.artifacts.annotated_pdf).toContain('/api/v1/review/nrc-aps/candidate-b-trace/annotated-pdf?');

  const annotatedPdfResponse = await annotatedPdfResponsePromise;
  expect(annotatedPdfResponse.status()).toBe(200);
  expect(await annotatedPdfResponse.headerValue('content-type')).toContain('application/pdf');
  expect(await annotatedPdfResponse.headerValue('content-disposition')).toMatch(/^inline;/i);

  await expect(page.locator('#tabs-header .tab-btn.active')).toHaveText('Annotated PDF');
  const artifactFrame = page.locator('.artifact-frame');
  await expect(artifactFrame).toBeVisible();
  const artifactSrc = await artifactFrame.getAttribute('src');
  expect(artifactSrc).toContain('/api/v1/review/nrc-aps/candidate-b-trace/annotated-pdf?');
  expectNoLocalPath(artifactSrc);

  await page.getByRole('button', { name: 'Summary' }).click();
  await expect(page.locator('#tabs-header .tab-btn.active')).toHaveText('Summary');
  await expect(page.locator('.detail-grid')).toBeVisible();

  const rawJsonResponsePromise = page.waitForResponse((response) => response.url().includes('/candidate-b-trace/raw-json'));
  await page.getByRole('button', { name: 'Raw JSON' }).click();
  const rawJsonResponse = await rawJsonResponsePromise;
  expect(rawJsonResponse.status()).toBe(200);
  expectNoLocalPath(await rawJsonResponse.text());
  await expect(page.locator('.artifact-pre')).toContainText('"fixture_id"');

  const rawMarkdownResponsePromise = page.waitForResponse((response) => response.url().includes('/candidate-b-trace/raw-markdown'));
  await page.getByRole('button', { name: 'Raw Markdown' }).click();
  const rawMarkdownResponse = await rawMarkdownResponsePromise;
  expect(rawMarkdownResponse.status()).toBe(200);
  expectNoLocalPath(await rawMarkdownResponse.text());
  await expect(page.locator('.artifact-pre')).toContainText('# Candidate B');

  expectNoLocalPath(await page.content());
  expectNoLocalPath(page.url());
});

test('Workbench Compare keeps baseline and Candidate A trace links on Document Trace', async ({ page }) => {
  await openWorkbenchCompare(page);

  const traceLinks = {
    baseline: page.locator('#trace-link-cluster a').filter({ hasText: 'Baseline Trace' }),
    candidateA: page.locator('#trace-link-cluster a').filter({ hasText: 'Candidate A Trace' }),
  };

  for (const [key, link] of Object.entries(traceLinks)) {
    await expect(link).toHaveCount(1);
    const href = await link.getAttribute('href');
    expect(href).toContain('/review/nrc-aps/document-trace?');
    expectNoLocalPath(href);

    const expectedUrl = new URL(href, 'http://127.0.0.1:8031');
    const expectedRunId = expectedUrl.searchParams.get('run_id');
    const expectedTargetId = expectedUrl.searchParams.get('target_id');
    expect(expectedRunId).toBeTruthy();
    expect(expectedTargetId).toBeTruthy();

    await Promise.all([
      page.waitForURL(/\/review\/nrc-aps\/document-trace\?/),
      link.click(),
    ]);

    await expect(page.locator('#trace-workspace')).toBeVisible();
    await expect(page.locator('#run-selector')).toHaveValue(expectedRunId);
    await expect(page.locator('#doc-selector')).toHaveValue(expectedTargetId);
    expect(new URL(page.url()).pathname).toBe('/review/nrc-aps/document-trace');
    expectNoLocalPath(page.url());

    if (key !== 'candidateA') {
      await openWorkbenchCompare(page);
    }
  }
});
