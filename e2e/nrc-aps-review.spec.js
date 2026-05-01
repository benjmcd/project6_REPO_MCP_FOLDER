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
  expect(sources.candidate_b_runtime_runs).toHaveLength(1);
  expect(targets.targets).toHaveLength(1);
  expect(manifest.deep_links.candidate_b_trace).toContain('/review/nrc-aps/candidate-b-trace?');
  expectNoLocalPath(manifest.deep_links.candidate_b_trace);

  await expect(page.locator('#compare-workspace')).toBeVisible();
  await expect(page.locator('#trace-link-cluster')).toContainText('Candidate B Trace');

  const candidateBTraceLink = page.locator('#trace-link-cluster a').filter({ hasText: 'Candidate B Trace' });
  await expect(candidateBTraceLink).toHaveCount(1);
  const traceHref = await candidateBTraceLink.getAttribute('href');
  expectNoLocalPath(traceHref);
  const manifestTraceUrl = new URL(manifest.deep_links.candidate_b_trace, 'http://127.0.0.1:8098');
  const traceUrl = new URL(traceHref, 'http://127.0.0.1:8098');
  expect(traceUrl.searchParams.get('baseline_run_id')).toBe(sources.baseline_runs[0].run_id);
  expect(traceUrl.searchParams.get('candidate_a_run_id')).toBe(sources.candidate_a_runs[0].run_id);
  expect(traceUrl.searchParams.get('candidate_b_source_kind')).toBe('bundle');
  expect(traceUrl.searchParams.get('candidate_b_bundle_id')).toBe(manifestTraceUrl.searchParams.get('candidate_b_bundle_id'));
  expect(traceUrl.searchParams.get('fixture_id')).toBe(manifestTraceUrl.searchParams.get('fixture_id'));
  expect(traceUrl.searchParams.get('candidate_b_run_id')).toBeNull();

  const traceManifestResponsePromise = page.waitForResponse((response) => response.url().includes('/candidate-b-trace/manifest'));
  const traceTargetsResponsePromise = page.waitForResponse(
    (response) => response.url().includes('/workbench-compare/targets?')
      && response.url().includes('candidate_b_source_kind=bundle'),
  );
  const annotatedPdfResponsePromise = page.waitForResponse((response) => response.url().includes('/candidate-b-trace/annotated-pdf'));
  await Promise.all([
    page.waitForURL(/\/review\/nrc-aps\/candidate-b-trace\?/),
    candidateBTraceLink.click(),
  ]);
  const tracePageUrl = new URL(page.url());
  expect(tracePageUrl.searchParams.get('baseline_run_id')).toBe(sources.baseline_runs[0].run_id);
  expect(tracePageUrl.searchParams.get('candidate_a_run_id')).toBe(sources.candidate_a_runs[0].run_id);
  expect(tracePageUrl.searchParams.get('candidate_b_source_kind')).toBe('bundle');
  expect(tracePageUrl.searchParams.get('candidate_b_run_id')).toBeNull();

  const traceManifest = await expectJsonResponse(await traceManifestResponsePromise);
  expect(traceManifest.default_tab).toBe('annotated_pdf');
  expect(traceManifest.artifacts.annotated_pdf).toContain('/api/v1/review/nrc-aps/candidate-b-trace/annotated-pdf?');
  const traceTargets = await expectJsonResponse(await traceTargetsResponsePromise);
  expect(traceTargets.candidate_b_source_kind).toBe('bundle');
  expect(traceTargets.candidate_b_run_id).toBeNull();
  expect(traceTargets.targets).toHaveLength(1);
  const fixtureNavigation = page.locator('#fixture-navigation');
  await expect(fixtureNavigation).toContainText('Comparable fixtures');
  await expect(fixtureNavigation).toContainText('Fixture 1 of 1');
  await expect(fixtureNavigation).toContainText(targets.targets[0].display_label);
  await expect(fixtureNavigation).toContainText('Only one comparable fixture is available');
  await expect(fixtureNavigation.locator('.fixture-nav-link.disabled')).toHaveCount(2);
  await expect(fixtureNavigation.locator('a.fixture-nav-link')).toHaveCount(0);
  const artifactStatusStrip = page.locator('#artifact-status-strip');
  await expect(artifactStatusStrip).toContainText('Annotated PDF');
  await expect(artifactStatusStrip).toContainText('Raw JSON');
  await expect(artifactStatusStrip).toContainText('Raw Markdown');
  await expect(artifactStatusStrip.locator('.artifact-status-card.available')).toHaveCount(3);
  await expect(artifactStatusStrip).not.toContainText('No artifact was retained');

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

  const returnLink = page.locator('#workbench-return-link');
  await expect(returnLink).toHaveCount(1);
  const returnHref = await returnLink.getAttribute('href');
  expect(returnHref).toContain('/review/nrc-aps/workbench-compare?');
  expectNoLocalPath(returnHref);
  const returnUrl = new URL(returnHref, 'http://127.0.0.1:8098');
  expect(returnUrl.searchParams.get('baseline_run_id')).toBe(sources.baseline_runs[0].run_id);
  expect(returnUrl.searchParams.get('candidate_a_run_id')).toBe(sources.candidate_a_runs[0].run_id);
  expect(returnUrl.searchParams.get('candidate_b_source_kind')).toBe('bundle');
  expect(returnUrl.searchParams.get('candidate_b_bundle_id')).toBe(traceManifest.candidate_b_bundle_id);
  expect(returnUrl.searchParams.get('fixture_id')).toBe(traceManifest.fixture_id);
  expect(returnUrl.searchParams.get('candidate_b_run_id')).toBeNull();

  await Promise.all([
    page.waitForURL(/\/review\/nrc-aps\/workbench-compare\?/),
    returnLink.click(),
  ]);
  const returnedUrl = new URL(page.url());
  expect(returnedUrl.searchParams.get('baseline_run_id')).toBe(sources.baseline_runs[0].run_id);
  expect(returnedUrl.searchParams.get('candidate_a_run_id')).toBe(sources.candidate_a_runs[0].run_id);
  expect(returnedUrl.searchParams.get('candidate_b_source_kind')).toBe('bundle');
  expect(returnedUrl.searchParams.get('candidate_b_bundle_id')).toBe(traceManifest.candidate_b_bundle_id);
  expect(returnedUrl.searchParams.get('fixture_id')).toBe(traceManifest.fixture_id);
  expect(returnedUrl.searchParams.get('candidate_b_run_id')).toBeNull();
});

test('Workbench Compare can switch Candidate B from bundle source to admitted runtime source', async ({ page }) => {
  await openWorkbenchCompare(page);

  const runtimeOption = page.locator('#candidate-b-bundle-selector option')
    .filter({ hasText: 'Runtime | Candidate B / OpenDataLoader PDF' });
  await expect(runtimeOption).toHaveCount(1);
  const runtimeOptionValue = await runtimeOption.getAttribute('value');
  expect(runtimeOptionValue).toContain('runtime:candidate-b-runtime-001');

  const targetsResponsePromise = page.waitForResponse(
    (response) => response.url().includes('/workbench-compare/targets?')
      && response.url().includes('candidate_b_source_kind=runtime'),
  );
  const manifestResponsePromise = page.waitForResponse(
    (response) => response.url().includes('/workbench-compare/targets/')
      && response.url().includes('/manifest')
      && response.url().includes('candidate_b_source_kind=runtime'),
  );
  await page.selectOption('#candidate-b-bundle-selector', runtimeOptionValue);

  const targets = await expectJsonResponse(await targetsResponsePromise);
  const manifest = await expectJsonResponse(await manifestResponsePromise);

  expect(targets.candidate_b_source_kind).toBe('runtime');
  expect(targets.candidate_b_run_id).toBe('candidate-b-runtime-001');
  expect(targets.candidate_b_bundle_id).toBeNull();
  expect(targets.targets).toHaveLength(1);
  expect(targets.targets[0].candidate_b_target_id).toBeTruthy();
  expect(manifest.variant_bindings.candidate_b.source_kind).toBe('runtime');
  expect(manifest.deep_links.candidate_b_trace).toBeNull();
  expect(manifest.deep_links.candidate_b_runtime_trace).toContain('/review/nrc-aps/document-trace?');
  expectNoLocalPath(JSON.stringify(manifest));

  const currentUrl = new URL(page.url());
  expect(currentUrl.searchParams.get('candidate_b_source_kind')).toBe('runtime');
  expect(currentUrl.searchParams.get('candidate_b_run_id')).toBe('candidate-b-runtime-001');
  expect(currentUrl.searchParams.get('candidate_b_bundle_id')).toBeNull();

  await expect(page.locator('#compare-workspace')).toBeVisible();
  await expect(page.locator('#trace-link-cluster')).toContainText('Candidate B Runtime Trace');
  await expect(page.locator('#compare-identity-summary')).toContainText('Runtime | Candidate B Runtime');
  await expect(page.locator('.compare-column h3').filter({ hasText: 'Candidate B / OpenDataLoader PDF' })).toHaveCount(1);
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
