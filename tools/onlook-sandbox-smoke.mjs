import { chromium, expect } from '@playwright/test';

function parseArgs(argv) {
  const args = {
    baseUrl: 'http://127.0.0.1:3007',
    profile: 'full',
    timeoutMs: 90000,
    documentTracePath: '/document-trace',
    workbenchPath: '/workbench-compare',
    candidateBPath: '/candidate-b-trace',
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--base-url') {
      args.baseUrl = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--profile') {
      args.profile = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--timeout-ms') {
      args.timeoutMs = Number(argv[index + 1]);
      index += 1;
      continue;
    }
    if (token === '--document-trace-path') {
      args.documentTracePath = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--workbench-path') {
      args.workbenchPath = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--candidate-b-path') {
      args.candidateBPath = argv[index + 1];
      index += 1;
    }
  }

  if (!['core', 'full'].includes(args.profile)) {
    throw new Error(`Unsupported profile: ${args.profile}`);
  }

  if (!Number.isFinite(args.timeoutMs) || args.timeoutMs <= 0) {
    throw new Error(`Invalid timeout: ${args.timeoutMs}`);
  }

  args.documentTracePath = remapLiveReviewPath(args.documentTracePath);
  args.workbenchPath = remapLiveReviewPath(args.workbenchPath);
  args.candidateBPath = remapLiveReviewPath(args.candidateBPath);

  return args;
}

function absoluteUrl(baseUrl, path) {
  return new URL(path, `${baseUrl.replace(/\/+$/, '')}/`).toString();
}

function remapLiveReviewPath(rawPath) {
  if (!rawPath) {
    return rawPath;
  }

  const parsed = safeParseUrl(rawPath);
  if (!parsed) {
    return rawPath;
  }

  const path = parsed.pathname;
  if (path === '/review/nrc-aps') {
    return parsed.search ? `/${parsed.search}` : '/';
  }
  if (path === '/review/nrc-aps/document-trace') {
    return `/document-trace${parsed.search}`;
  }
  if (path === '/review/nrc-aps/workbench-compare') {
    return `/workbench-compare${parsed.search}`;
  }
  if (path === '/review/nrc-aps/candidate-b-trace') {
    return `/candidate-b-trace${parsed.search}`;
  }
  if (path === '/review/analyst-insight') {
    return `/analyst-insight${parsed.search}`;
  }

  return rawPath;
}

function safeParseUrl(value) {
  try {
    if (/^https?:\/\//i.test(value)) {
      return new URL(value);
    }

    return new URL(value, 'https://sandbox.local');
  } catch {
    return null;
  }
}

function isIgnorableRuntimeUrl(url) {
  return (
    url.includes('favicon.ico')
    || url.includes('/_next/webpack-hmr')
    || url.includes('/_next/static/webpack/webpack.')
    || url.includes('.webpack.hot-update.json')
    || url.includes('/__nextjs_original-stack-frame')
  );
}

function isIgnorableAbort(url, failureText) {
  if (failureText !== 'net::ERR_ABORTED') {
    return false;
  }

  return (
    url.includes('/_next/static/webpack/webpack.')
    || url.includes('.webpack.hot-update.json')
    || url.includes('_rsc=')
    || url.includes('/api/v1/review/nrc-aps/')
    || url.includes('/api/v1/analyst-insight/')
    || url.includes('/documents/') && url.includes('/source')
    || url.includes('/candidate-b-trace/annotated-pdf')
  );
}

function pathnameOf(response) {
  return new URL(response.url()).pathname;
}

function ensureOk(response, label) {
  if (!response.ok()) {
    throw new Error(`${label} failed with status ${response.status()} at ${response.url()}`);
  }
}

function createProblemCollector(page) {
  const pageErrors = [];
  const consoleErrors = [];
  const requestFailures = [];
  const serverErrors = [];

  page.on('pageerror', (error) => {
    pageErrors.push(error.message);
  });

  page.on('console', (message) => {
    if (message.type() !== 'error') {
      return;
    }
    const text = message.text();
    if (text.includes('favicon.ico') || text.includes('/_next/webpack-hmr')) {
      return;
    }
    consoleErrors.push(text);
  });

  page.on('requestfailed', (request) => {
    const url = request.url();
    if (isIgnorableRuntimeUrl(url)) {
      return;
    }
    const failure = request.failure();
    if (isIgnorableAbort(url, failure?.errorText ?? '')) {
      return;
    }
    requestFailures.push(`${request.method()} ${url} :: ${failure?.errorText ?? 'unknown failure'}`);
  });

  page.on('response', (response) => {
    const url = response.url();
    if (isIgnorableRuntimeUrl(url)) {
      return;
    }
    if (response.status() >= 500) {
      serverErrors.push(`${response.status()} ${url}`);
    }
  });

  return () => {
    const problems = [
      ...pageErrors.map((item) => `pageerror: ${item}`),
      ...consoleErrors.map((item) => `console: ${item}`),
      ...requestFailures.map((item) => `requestfailed: ${item}`),
      ...serverErrors.map((item) => `server: ${item}`),
    ];

    if (problems.length > 0) {
      throw new Error(`Browser smoke recorded unexpected problems:\n- ${problems.join('\n- ')}`);
    }
  };
}

async function openRoute(page, baseUrl, path, responsePredicates) {
  const seenResponses = [];
  const onResponse = (response) => {
    seenResponses.push(response);
  };

  page.on('response', onResponse);
  try {
    await page.goto(absoluteUrl(baseUrl, path), { waitUntil: 'domcontentloaded' });

    const deadline = Date.now() + Math.max(...responsePredicates.map(({ timeoutMs }) => timeoutMs));
    const matches = new Map();

    while (Date.now() < deadline) {
      for (const response of seenResponses) {
        for (const entry of responsePredicates) {
          if (!matches.has(entry.label) && entry.predicate(response)) {
            matches.set(entry.label, response);
          }
        }
      }

      if (matches.size === responsePredicates.length) {
        break;
      }

      await page.waitForTimeout(250);
    }

    for (const entry of responsePredicates) {
      const response = matches.get(entry.label);
      if (!response) {
        throw new Error(`Timed out waiting for ${entry.label} on ${path}`);
      }
      ensureOk(response, entry.label);
    }
  } finally {
    page.off('response', onResponse);
  }
}

async function waitForHydratedMain(page, timeoutMs) {
  await page.waitForFunction(() => {
    const main = document.querySelector('main');
    if (!main) {
      return false;
    }

    return Object.keys(main).some((key) =>
      key.startsWith('__reactFiber$') || key.startsWith('__reactProps$'),
    );
  }, { timeout: timeoutMs });
}

async function assertReviewRoute(page, baseUrl, timeoutMs) {
  await openRoute(page, baseUrl, '/', [
    {
      label: 'review runs response',
      timeoutMs,
      predicate: (response) =>
        pathnameOf(response) === '/api/v1/review/nrc-aps/runs' &&
        response.request().method() === 'GET',
    },
    {
      label: 'review overview response',
      timeoutMs,
      predicate: (response) =>
        response.url().includes('/api/v1/review/nrc-aps/runs/') &&
        response.url().includes('/overview') &&
        response.request().method() === 'GET',
    },
  ]);

  await waitForHydratedMain(page, timeoutMs);
  await expect(page.getByRole('heading', { name: 'Review Overview' })).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByText('Projection nodes')).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByText('Layout sections')).toBeVisible({ timeout: timeoutMs });
}

async function assertDocumentTraceRoute(page, baseUrl, routePath, timeoutMs) {
  await openRoute(page, baseUrl, routePath, [
    {
      label: 'document trace runs response',
      timeoutMs,
      predicate: (response) =>
        pathnameOf(response) === '/api/v1/review/nrc-aps/runs' &&
        response.request().method() === 'GET',
    },
    {
      label: 'document trace selector response',
      timeoutMs,
      predicate: (response) =>
        response.url().includes('/api/v1/review/nrc-aps/runs/') &&
        response.url().includes('/documents') &&
        !response.url().includes('/trace') &&
        response.request().method() === 'GET',
    },
    {
      label: 'document trace manifest response',
      timeoutMs,
      predicate: (response) =>
        response.url().includes('/api/v1/review/nrc-aps/runs/') &&
        response.url().includes('/trace') &&
        response.request().method() === 'GET',
    },
  ]);

  await waitForHydratedMain(page, timeoutMs);
  await expect(page.getByRole('heading', { name: 'Document Trace' })).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByRole('button', { name: 'Extracted Units' })).toBeVisible({ timeout: timeoutMs });

  const extractedUnitsPromise = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/review/nrc-aps/runs/') &&
      response.url().includes('/extracted-units') &&
      response.request().method() === 'GET',
    { timeout: timeoutMs },
  );
  await page.getByRole('button', { name: 'Extracted Units' }).click();
  ensureOk(await extractedUnitsPromise, 'document trace extracted-units response');
}

async function assertWorkbenchCompareRoute(page, baseUrl, routePath, timeoutMs) {
  await openRoute(page, baseUrl, routePath, [
    {
      label: 'workbench sources response',
      timeoutMs,
      predicate: (response) =>
        response.url().includes('/api/v1/review/nrc-aps/workbench-compare/sources') &&
        response.request().method() === 'GET',
    },
    {
      label: 'workbench targets response',
      timeoutMs,
      predicate: (response) =>
        response.url().includes('/api/v1/review/nrc-aps/workbench-compare/targets?') &&
        response.request().method() === 'GET',
    },
    {
      label: 'workbench manifest response',
      timeoutMs,
      predicate: (response) =>
        response.url().includes('/api/v1/review/nrc-aps/workbench-compare/targets/') &&
        response.url().includes('/manifest') &&
        response.request().method() === 'GET',
    },
  ]);

  await waitForHydratedMain(page, timeoutMs);
  await expect(page.getByRole('heading', { name: 'Workbench Compare' })).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByText('Selection Context')).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByRole('button', { name: 'Summary' })).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByText('Choose a complete compare selection')).toHaveCount(0);
}

async function assertCandidateBTraceRoute(page, baseUrl, routePath, timeoutMs) {
  const manifestPromise = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/review/nrc-aps/candidate-b-trace/manifest') &&
      response.request().method() === 'GET',
    { timeout: timeoutMs },
  );

  await page.goto(absoluteUrl(baseUrl, routePath), { waitUntil: 'domcontentloaded' });
  ensureOk(await manifestPromise, 'candidate-b trace manifest response');

  await waitForHydratedMain(page, timeoutMs);
  await expect(page.getByRole('heading', { name: 'Candidate B Trace' })).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByRole('button', { name: 'Annotated PDF' })).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByRole('button', { name: 'Raw JSON' })).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByRole('button', { name: 'Raw Markdown' })).toBeVisible({ timeout: timeoutMs });
  await page.getByRole('button', { name: 'Annotated PDF' }).click();
  await expect(page.getByRole('link', { name: 'Open annotated PDF' })).toBeVisible({ timeout: timeoutMs });
  const pdfFrame = page.locator('iframe[title="Candidate B Annotated PDF"]');
  await expect(pdfFrame).toBeVisible({ timeout: timeoutMs });
  await expect(pdfFrame).toHaveAttribute('src', /\/api\/v1\/review\/nrc-aps\/candidate-b-trace\/annotated-pdf\?/);

  const rawJsonPromise = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/review/nrc-aps/candidate-b-trace/raw-json') &&
      response.request().method() === 'GET',
    { timeout: timeoutMs },
  );
  await page.getByRole('button', { name: 'Raw JSON' }).click();
  const rawJsonResponse = await rawJsonPromise;
  ensureOk(rawJsonResponse, 'candidate-b raw-json response');
  const rawJsonPre = page.locator('pre').first();
  await expect(rawJsonPre).toBeVisible({ timeout: timeoutMs });
  const rawJsonBody = await rawJsonPre.innerText();
  if (!rawJsonBody.includes('"file name"') && !rawJsonBody.includes('"fixture_id"')) {
    throw new Error('candidate-b raw-json response did not include an expected structured payload marker');
  }

  const rawMarkdownPromise = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/review/nrc-aps/candidate-b-trace/raw-markdown') &&
      response.request().method() === 'GET',
    { timeout: timeoutMs },
  );
  await page.getByRole('button', { name: 'Raw Markdown' }).click();
  const rawMarkdownResponse = await rawMarkdownPromise;
  ensureOk(rawMarkdownResponse, 'candidate-b raw-markdown response');
  const rawMarkdownPre = page.locator('pre').first();
  await expect(rawMarkdownPre).toBeVisible({ timeout: timeoutMs });
  const rawMarkdownBody = await rawMarkdownPre.innerText();
  if (rawMarkdownBody.trim().length < 20) {
    throw new Error('candidate-b raw-markdown response was unexpectedly short');
  }
}

async function assertAnalystInsightRoute(page, baseUrl, timeoutMs) {
  await page.goto(absoluteUrl(baseUrl, '/analyst-insight'), { waitUntil: 'domcontentloaded' });

  await waitForHydratedMain(page, timeoutMs);
  await expect(page.getByRole('heading', { name: 'Analyst Insight' })).toBeVisible({ timeout: timeoutMs });
  await expect(page.getByRole('button', { name: 'Run full analyst flow' })).toBeVisible({ timeout: timeoutMs });

  const flowResponses = [
    page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/analyst-insight/integration/cross-reference') &&
        response.request().method() === 'POST',
      { timeout: timeoutMs },
    ),
    page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/analyst-insight/validation/run') &&
        response.request().method() === 'POST',
      { timeout: timeoutMs },
    ),
    page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/analyst-insight/insights/process') &&
        response.request().method() === 'POST',
      { timeout: timeoutMs },
    ),
  ];

  await page.getByRole('button', { name: 'Run full analyst flow' }).click();
  const responses = await Promise.all(flowResponses);
  responses.forEach((response, index) => ensureOk(response, `analyst flow response ${index + 1}`));
  await expect(page.locator('pre').last()).toContainText('stage3_insights', { timeout: timeoutMs });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  const assertNoProblems = createProblemCollector(page);

  try {
    await assertReviewRoute(page, args.baseUrl, args.timeoutMs);
    await assertDocumentTraceRoute(page, args.baseUrl, args.documentTracePath, args.timeoutMs);

    if (args.profile === 'full') {
      await assertWorkbenchCompareRoute(page, args.baseUrl, args.workbenchPath, args.timeoutMs);
      await assertCandidateBTraceRoute(page, args.baseUrl, args.candidateBPath, args.timeoutMs);
    }

    await assertAnalystInsightRoute(page, args.baseUrl, args.timeoutMs);
    assertNoProblems();
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack ?? error.message : String(error));
  process.exitCode = 1;
});
