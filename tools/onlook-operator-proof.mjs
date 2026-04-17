import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium, expect } from '@playwright/test';

const BROWSER_ARGS = [
  '--disable-features=LocalNetworkAccessChecks,BlockInsecurePrivateNetworkRequests',
];

function parseArgs(argv) {
  const args = {
    baseUrl: 'http://127.0.0.1:3011',
    appDir: '',
    canonicalDir: '',
    browserChannel: 'msedge',
    timeoutMs: 180000,
    documentTracePath: '/document-trace',
    workbenchPath: '/workbench-compare',
    candidateBPath: '/candidate-b-trace',
    proofFile: 'app/page.tsx',
    proofMarker: 'onlook-operator-proof',
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--base-url') {
      args.baseUrl = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--app-dir') {
      args.appDir = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--canonical-dir') {
      args.canonicalDir = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--browser-channel') {
      args.browserChannel = argv[index + 1];
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
      continue;
    }
    if (token === '--proof-file') {
      args.proofFile = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--proof-marker') {
      args.proofMarker = argv[index + 1];
      index += 1;
    }
  }

  if (!args.appDir) {
    throw new Error('Missing --app-dir');
  }

  if (!args.canonicalDir) {
    throw new Error('Missing --canonical-dir');
  }

  if (!Number.isFinite(args.timeoutMs) || args.timeoutMs <= 0) {
    throw new Error(`Invalid timeout: ${args.timeoutMs}`);
  }

  args.documentTracePath = remapLiveReviewPath(args.documentTracePath);
  args.workbenchPath = remapLiveReviewPath(args.workbenchPath);
  args.candidateBPath = remapLiveReviewPath(args.candidateBPath);

  return args;
}

function absoluteUrl(baseUrl, pathname) {
  return new URL(pathname, `${baseUrl.replace(/\/+$/, '')}/`).toString();
}

function remapLiveReviewPath(rawPath) {
  if (!rawPath) {
    return rawPath;
  }

  const parsed = safeParseUrl(rawPath);
  if (!parsed) {
    return rawPath;
  }

  const currentPath = parsed.pathname;
  if (currentPath === '/review/nrc-aps') {
    return parsed.search ? `/${parsed.search}` : '/';
  }
  if (currentPath === '/review/nrc-aps/document-trace') {
    return `/document-trace${parsed.search}`;
  }
  if (currentPath === '/review/nrc-aps/workbench-compare') {
    return `/workbench-compare${parsed.search}`;
  }
  if (currentPath === '/review/nrc-aps/candidate-b-trace') {
    return `/candidate-b-trace${parsed.search}`;
  }
  if (currentPath === '/review/analyst-insight') {
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

function buildRoutePath(pathname, params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) {
      search.set(key, value);
    }
  }

  const query = search.toString();
  return query ? `${pathname}?${query}` : pathname;
}

function getQueryValue(rawPath, key) {
  const parsed = safeParseUrl(rawPath);
  return parsed?.searchParams.get(key) ?? null;
}

function hasExpectedPreviewRoute(frameUrl, pathname, expectedParams = {}) {
  const parsed = safeParseUrl(frameUrl);
  if (!parsed) {
    return false;
  }

  if (parsed.pathname !== pathname) {
    return false;
  }

  for (const [key, value] of Object.entries(expectedParams)) {
    if (value === null || value === undefined) {
      continue;
    }
    if (parsed.searchParams.get(key) !== value) {
      return false;
    }
  }

  return true;
}

async function waitForEnabled(locator, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await locator.isEnabled().catch(() => false)) {
      return;
    }

    await locator.page().waitForTimeout(1000);
  }

  throw new Error('Timed out waiting for an enabled control.');
}

async function loginWithDevUser(page, baseUrl, timeoutMs) {
  await page.goto(absoluteUrl(baseUrl, '/login'), { waitUntil: 'domcontentloaded' });
  const devButton = page.getByRole('button', { name: 'DEV MODE: Sign in as demo user' });
  if (await devButton.isVisible().catch(() => false)) {
    await devButton.click();
    await page.waitForURL((url) => !url.pathname.endsWith('/login'), {
      timeout: timeoutMs,
    });
  }
}

async function importLocalProject(page, baseUrl, appDir, timeoutMs) {
  await page.goto(absoluteUrl(baseUrl, '/projects/import/local'), {
    waitUntil: 'domcontentloaded',
  });

  const picker = page.locator('input[type="file"][webkitdirectory]');
  await picker.setInputFiles(appDir, { timeout: timeoutMs });

  const finish = page.getByRole('button', { name: 'Finish setup' });
  await finish.waitFor({ state: 'visible', timeout: timeoutMs });
  await waitForEnabled(finish, timeoutMs);
  await finish.click();

  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (/\/project\//.test(page.url())) {
      return page.url();
    }

    const bodyText = await page.locator('body').innerText().catch(() => '');
    if (bodyText.includes('Failed to create project')) {
      throw new Error('Onlook reported a project finalization failure during import.');
    }

    await page.waitForTimeout(2000);
  }

  throw new Error('Timed out waiting for a project URL after import.');
}

function findPreviewFrame(page) {
  return page.frames().find((item) => item.url().includes('csb.app'));
}

async function waitForPreviewFrame(page, timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const previewFrame = findPreviewFrame(page);
    if (previewFrame) {
      return previewFrame;
    }

    await page.waitForTimeout(1000);
  }

  throw new Error('Timed out waiting for the preview frame.');
}

async function getPreviewLocation(frame) {
  try {
    return await frame.evaluate(() => window.location.href);
  } catch {
    return frame.url();
  }
}

async function waitForPreviewRoute(page, pathname, expectedParams, timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const previewFrame = findPreviewFrame(page);
    if (
      previewFrame &&
      hasExpectedPreviewRoute(await getPreviewLocation(previewFrame), pathname, expectedParams)
    ) {
      return previewFrame;
    }

    await page.waitForTimeout(1000);
  }

  throw new Error(`Timed out waiting for preview route ${pathname}`);
}

async function ensureTrustedPreview(page, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let previewFrame = null;

  while (Date.now() < deadline) {
    previewFrame = findPreviewFrame(page);
    if (!previewFrame) {
      await page.waitForTimeout(1500);
      continue;
    }

    const trustLink = previewFrame.locator('#btn-answer-yes');
    if (await trustLink.isVisible().catch(() => false)) {
      await trustLink.evaluate((node) => node.click());
      await page.waitForTimeout(1500);
      continue;
    }

    const bodyText = await previewFrame.locator('body').innerText().catch(() => '');
    if (bodyText.includes('Review Overview')) {
      return previewFrame;
    }

    await page.waitForTimeout(1500);
  }

  throw new Error('Timed out waiting for the trusted preview to load.');
}

async function assertRootPreview(page, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let bodyText = '';
  let previewFrame = null;
  const runResponses = [];
  let processedRunResponseCount = 0;
  const onResponse = (response) => {
    if (isReviewRunsResponse(response)) {
      runResponses.push(response);
    }
  };

  page.on('response', onResponse);

  try {
    while (Date.now() < deadline) {
      previewFrame = findPreviewFrame(page);
      if (!previewFrame) {
        await page.waitForTimeout(1500);
        continue;
      }

      await waitForHydratedFrameMain(
        previewFrame,
        Math.max(1000, Math.min(5000, deadline - Date.now())),
      ).catch(() => null);

      bodyText = await previewFrame.locator('body').innerText().catch(() => '');
      if (/Runs loaded:\s*[1-9]/.test(bodyText)) {
        break;
      }
      if (
        bodyText.includes('Failed to fetch')
        || bodyText.includes('Review API request failed')
        || bodyText.includes('NEXT_PUBLIC_REVIEW_API_BASE is not set')
      ) {
        throw new Error(`Preview failed to reach or configure the local review API:\n${bodyText.slice(0, 1200)}`);
      }

      if (runResponses.length > processedRunResponseCount) {
        const latestResponse = runResponses[runResponses.length - 1];
        ensureOk(latestResponse, 'review runs response');
        processedRunResponseCount = runResponses.length;
      }

      await page.waitForTimeout(1500);
    }

    if (!/Runs loaded:\s*[1-9]/.test(bodyText)) {
      if (runResponses.length < 1) {
        throw new Error(`Preview did not request review runs within timeout:\n${bodyText.slice(0, 1200)}`);
      }

      throw new Error(`Preview did not render populated review runs within timeout:\n${bodyText.slice(0, 1200)}`);
    }

    if (!previewFrame) {
      throw new Error('Preview frame disappeared before the populated review shell could be asserted.');
    }

    await expect(previewFrame.getByRole('heading', { name: 'Review Overview' })).toBeVisible({
      timeout: timeoutMs,
    });

    return previewFrame;
  } finally {
    page.off('response', onResponse);
  }
}

async function waitForHydratedFrameMain(frame, timeoutMs) {
  await frame.waitForFunction(() => {
    const main = document.querySelector('main');
    if (!main) {
      return false;
    }

    return Object.keys(main).some((key) =>
      key.startsWith('__reactFiber$') || key.startsWith('__reactProps$'),
    );
  }, { timeout: timeoutMs });
}

async function waitForPreviewState(page, description, timeoutMs, predicate) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const frame = findPreviewFrame(page);
    if (!frame) {
      await page.waitForTimeout(1000);
      continue;
    }

    if (await predicate(frame).catch(() => false)) {
      return frame;
    }

    await page.waitForTimeout(1000);
  }

  throw new Error(`Timed out waiting for ${description}`);
}

async function navigateWithinPreview(page, path, description, isReady, timeoutMs) {
  const frame = await waitForPreviewFrame(page, timeoutMs);
  await frame.evaluate((nextPath) => {
    window.location.assign(nextPath);
  }, path);
  return waitForPreviewState(page, description, timeoutMs, isReady);
}

function getSelectLocator(frame, label) {
  return frame
    .locator('label')
    .filter({ hasText: label })
    .locator('select')
    .first();
}

async function waitForSelectOption(page, label, value, timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const frame = findPreviewFrame(page);
    if (!frame) {
      await page.waitForTimeout(1000);
      continue;
    }

    const select = getSelectLocator(frame, label);
    const isVisible = await select.isVisible().catch(() => false);
    if (!isVisible) {
      await page.waitForTimeout(1000);
      continue;
    }

    const hasOption = await select
      .evaluate(
        (node, optionValue) =>
          Array.from(node.options).some((option) => option.value === optionValue),
        value,
      )
      .catch(() => false);
    if (hasOption) {
      return { frame, select };
    }

    await page.waitForTimeout(1000);
  }

  throw new Error(`Timed out waiting for ${label} option ${value}`);
}

async function waitForSelectValue(page, label, value, timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const frame = findPreviewFrame(page);
    if (!frame) {
      await page.waitForTimeout(1000);
      continue;
    }

    const select = getSelectLocator(frame, label);
    const isVisible = await select.isVisible().catch(() => false);
    if (!isVisible) {
      await page.waitForTimeout(1000);
      continue;
    }

    const currentValue = await select.inputValue().catch(() => '');
    if (currentValue === value) {
      return frame;
    }

    await page.waitForTimeout(1000);
  }

  throw new Error(`Timed out waiting for ${label} to select ${value}`);
}

async function selectFieldValue(page, frame, label, value, timeoutMs) {
  const current = await waitForSelectOption(page, label, value, timeoutMs);
  frame = current.frame;
  const select = current.select;
  if ((await select.inputValue()) !== value) {
    await select.selectOption(value);
  }

  return waitForSelectValue(page, label, value, timeoutMs);
}

async function clickRoute(page, frame, label, description, isReady, timeoutMs) {
  await waitForHydratedFrameMain(frame, timeoutMs);
  let currentFrame = frame;
  let link = currentFrame.getByRole('link', { name: label, exact: true }).first();
  await link.waitFor({ state: 'visible', timeout: timeoutMs });

  try {
    await link.click({ timeout: Math.min(timeoutMs, 10000) });
    return await waitForPreviewState(
      page,
      description,
      Math.min(timeoutMs, 15000),
      isReady,
    );
  } catch {
    currentFrame = await waitForPreviewFrame(page, timeoutMs);
    await waitForHydratedFrameMain(currentFrame, timeoutMs);
    link = currentFrame.getByRole('link', { name: label, exact: true }).first();
    await link.waitFor({ state: 'visible', timeout: timeoutMs });
    await link.evaluate((node) => node.click());
    return waitForPreviewState(page, description, timeoutMs, isReady);
  }
}

async function assertDocumentTrace(page, frame, selection, timeoutMs) {
  frame = await clickRoute(
    page,
    frame,
    'Document Trace',
    'Document Trace route',
    async (currentFrame) => {
      await waitForHydratedFrameMain(currentFrame, Math.min(timeoutMs, 10000));
      return currentFrame.getByRole('heading', { name: 'Document Trace' }).isVisible();
    },
    timeoutMs,
  );
  await waitForHydratedFrameMain(frame, timeoutMs);
  if (selection.runId) {
    frame = await selectFieldValue(
      page,
      frame,
      'Run',
      selection.runId,
      timeoutMs,
    );
    await waitForHydratedFrameMain(frame, timeoutMs);
  }
  if (selection.targetId) {
    frame = await selectFieldValue(
      page,
      frame,
      'Document',
      selection.targetId,
      timeoutMs,
    );
    await waitForHydratedFrameMain(frame, timeoutMs);
  }

  await waitForHydratedFrameMain(frame, timeoutMs);
  await expect(frame.getByRole('heading', { name: 'Document Trace' })).toBeVisible({
    timeout: timeoutMs,
  });
  await expect(frame.getByRole('button', { name: 'Extracted Units' })).toBeVisible({
    timeout: timeoutMs,
  });

  return frame;
}

async function isWorkbenchComparePopulated(frame, timeoutMs) {
  await waitForHydratedFrameMain(frame, Math.min(timeoutMs, 10000));
  const bodyText = await frame.locator('body').innerText().catch(() => '');
  const hasHeading = await frame
    .getByRole('heading', { name: 'Workbench Compare' })
    .isVisible()
    .catch(() => false);
  return (
    hasHeading &&
    bodyText.includes('Selection Context') &&
    bodyText.includes('Summary') &&
    !bodyText.includes('Choose a complete compare selection')
  );
}

async function assertWorkbenchCompare(page, frame, selection, directPath, timeoutMs) {
  frame = await clickRoute(
    page,
    frame,
    'Workbench Compare',
    'Workbench Compare route',
    async (currentFrame) => {
      await waitForHydratedFrameMain(currentFrame, Math.min(timeoutMs, 10000));
      return getSelectLocator(currentFrame, 'Baseline').isVisible();
    },
    timeoutMs,
  );
  await waitForHydratedFrameMain(frame, timeoutMs);
  try {
    if (selection.baselineRunId) {
      frame = await selectFieldValue(
        page,
        frame,
        'Baseline',
        selection.baselineRunId,
        timeoutMs,
      );
    }
    if (selection.candidateARunId) {
      frame = await selectFieldValue(
        page,
        frame,
        'Candidate A',
        selection.candidateARunId,
        timeoutMs,
      );
    }
    if (selection.candidateBBundleId) {
      frame = await selectFieldValue(
        page,
        frame,
        'Candidate B',
        selection.candidateBBundleId,
        timeoutMs,
      );
    }
    if (selection.fixtureId) {
      frame = await selectFieldValue(
        page,
        frame,
        'Fixture',
        selection.fixtureId,
        timeoutMs,
      );
    }
    frame = await waitForPreviewState(
      page,
      'populated Workbench Compare route',
      Math.min(timeoutMs, 15000),
      (currentFrame) => isWorkbenchComparePopulated(currentFrame, timeoutMs),
    );
  } catch {
    frame = await navigateWithinPreview(
      page,
      directPath,
      'populated Workbench Compare route',
      (currentFrame) => isWorkbenchComparePopulated(currentFrame, timeoutMs),
      timeoutMs,
    );
  }

  await waitForHydratedFrameMain(frame, timeoutMs);
  await expect(frame.getByRole('heading', { name: 'Workbench Compare' })).toBeVisible({
    timeout: timeoutMs,
  });
  await expect(frame.getByText('Selection Context')).toBeVisible({ timeout: timeoutMs });
  await expect(frame.getByRole('button', { name: 'Summary' })).toBeVisible({
    timeout: timeoutMs,
  });
  await expect(frame.getByText('Choose a complete compare selection')).toHaveCount(0);

  return frame;
}

async function isCandidateBTraceReady(frame, timeoutMs) {
  await waitForHydratedFrameMain(frame, Math.min(timeoutMs, 10000));
  const hasHeading = await frame
    .getByRole('heading', { name: 'Candidate B Trace' })
    .isVisible()
    .catch(() => false);
  const hasAnnotatedPdf = await frame
    .getByRole('button', { name: 'Annotated PDF' })
    .isVisible()
    .catch(() => false);
  return hasHeading && hasAnnotatedPdf;
}

async function assertCandidateBTrace(page, frame, selection, directPath, timeoutMs) {
  frame = await clickRoute(
    page,
    frame,
    'Candidate B Trace',
    'Candidate B Trace route',
    async (currentFrame) => {
      await waitForHydratedFrameMain(currentFrame, Math.min(timeoutMs, 10000));
      return getSelectLocator(currentFrame, 'Baseline').isVisible();
    },
    timeoutMs,
  );
  await waitForHydratedFrameMain(frame, timeoutMs);
  try {
    if (selection.baselineRunId) {
      frame = await selectFieldValue(
        page,
        frame,
        'Baseline',
        selection.baselineRunId,
        timeoutMs,
      );
    }
    if (selection.candidateARunId) {
      frame = await selectFieldValue(
        page,
        frame,
        'Candidate A',
        selection.candidateARunId,
        timeoutMs,
      );
    }
    if (selection.candidateBBundleId) {
      frame = await selectFieldValue(
        page,
        frame,
        'Candidate B',
        selection.candidateBBundleId,
        timeoutMs,
      );
    }
    if (selection.fixtureId) {
      frame = await selectFieldValue(
        page,
        frame,
        'Fixture',
        selection.fixtureId,
        timeoutMs,
      );
    }
    frame = await waitForPreviewState(
      page,
      'Candidate B Trace route',
      Math.min(timeoutMs, 15000),
      (currentFrame) => isCandidateBTraceReady(currentFrame, timeoutMs),
    );
  } catch {
    frame = await navigateWithinPreview(
      page,
      directPath,
      'Candidate B Trace route',
      (currentFrame) => isCandidateBTraceReady(currentFrame, timeoutMs),
      timeoutMs,
    );
  }

  await waitForHydratedFrameMain(frame, timeoutMs);
  await expect(frame.getByRole('heading', { name: 'Candidate B Trace' })).toBeVisible({
    timeout: timeoutMs,
  });
  await expect(frame.getByRole('button', { name: 'Annotated PDF' })).toBeVisible({
    timeout: timeoutMs,
  });
  await expect(frame.getByRole('button', { name: 'Raw JSON' })).toBeVisible({
    timeout: timeoutMs,
  });
  await expect(frame.getByRole('button', { name: 'Raw Markdown' })).toBeVisible({
    timeout: timeoutMs,
  });

  return frame;
}

function ensureOk(response, label) {
  if (!response.ok()) {
    throw new Error(`${label} failed with status ${response.status()} at ${response.url()}`);
  }
}

function isReviewRunsResponse(response) {
  return (
    response.url().includes('/api/v1/review/nrc-aps/runs')
    && response.request().method() === 'GET'
  );
}

async function assertAnalystInsight(page, frame, timeoutMs) {
  await waitForHydratedFrameMain(frame, timeoutMs);
  await expect(frame.getByRole('heading', { name: 'Analyst Insight' })).toBeVisible({
    timeout: timeoutMs,
  });

  const runFlow = frame.getByRole('button', { name: 'Run full analyst flow' });
  await runFlow.waitFor({ state: 'visible', timeout: timeoutMs });
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
  await runFlow.click();
  const responses = await Promise.all(flowResponses);
  responses.forEach((response, index) => ensureOk(response, `analyst flow response ${index + 1}`));
  await expect(frame.locator('pre').last()).toContainText('stage3_insights', {
    timeout: timeoutMs,
  });
}

async function assertCodeWriteback(page, duplicateFilePath, canonicalFilePath, proofMarker, timeoutMs) {
  const originalDuplicate = await fs.readFile(duplicateFilePath, 'utf8');
  const originalCanonical = await fs.readFile(canonicalFilePath, 'utf8');

  if (originalDuplicate !== originalCanonical) {
    throw new Error(
      'Duplicate proof file already diverges from canonical source. Review the duplicate before running the operator proof.',
    );
  }

  const markerLine = `// ${proofMarker}`;

  try {
    await page.getByText('Code', { exact: true }).click();
    await page.getByRole('button', { name: /View Files/i }).click();
    await page.getByText('app', { exact: true }).click();
    await page.waitForTimeout(1000);
    await page.getByText('page.tsx', { exact: true }).click();

    const editor = page.locator('.cm-content').first();
    await editor.waitFor({ state: 'visible', timeout: timeoutMs });
    const currentText = await editor.innerText();
    if (!currentText.includes('ReviewShell')) {
      throw new Error('Code editor did not load app/page.tsx as expected.');
    }

    await editor.click();
    await page.keyboard.press('Control+End');
    await page.keyboard.type(`\n${markerLine}`);

    const saveButton = page.getByRole('button', { name: 'Save' });
    await waitForEnabled(saveButton, timeoutMs);
    await saveButton.click();

    const deadline = Date.now() + timeoutMs;
    let updatedDuplicate = originalDuplicate;
    while (Date.now() < deadline) {
      updatedDuplicate = await fs.readFile(duplicateFilePath, 'utf8');
      if (updatedDuplicate.includes(markerLine)) {
        break;
      }

      await page.waitForTimeout(1000);
    }

    if (!updatedDuplicate.includes(markerLine)) {
      throw new Error('Timed out waiting for duplicate-target writeback on disk.');
    }

    const canonicalAfterSave = await fs.readFile(canonicalFilePath, 'utf8');
    if (canonicalAfterSave !== originalCanonical) {
      throw new Error('Canonical sandbox source changed during duplicate-target writeback proof.');
    }
  } finally {
    await fs.writeFile(duplicateFilePath, originalDuplicate, 'utf8');
  }

  const restoredDuplicate = await fs.readFile(duplicateFilePath, 'utf8');
  const restoredCanonical = await fs.readFile(canonicalFilePath, 'utf8');
  if (restoredDuplicate !== originalDuplicate) {
    throw new Error('Failed to restore the duplicate proof file after writeback validation.');
  }
  if (restoredCanonical !== originalCanonical) {
    throw new Error('Canonical sandbox source drifted during duplicate-target writeback validation.');
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const duplicateFilePath = path.join(args.appDir, ...args.proofFile.split('/'));
  const canonicalFilePath = path.join(args.canonicalDir, ...args.proofFile.split('/'));
  const documentTraceSelection = {
    runId: getQueryValue(args.documentTracePath, 'run_id'),
    targetId: getQueryValue(args.documentTracePath, 'target_id'),
  };
  const workbenchSelection = {
    baselineRunId: getQueryValue(args.workbenchPath, 'baseline_run_id'),
    candidateARunId: getQueryValue(args.workbenchPath, 'candidate_a_run_id'),
    candidateBBundleId: getQueryValue(args.workbenchPath, 'candidate_b_bundle_id'),
    fixtureId: getQueryValue(args.workbenchPath, 'fixture_id'),
  };
  const candidateBSelection = {
    baselineRunId: getQueryValue(args.candidateBPath, 'baseline_run_id'),
    candidateARunId: getQueryValue(args.candidateBPath, 'candidate_a_run_id'),
    candidateBBundleId: getQueryValue(args.candidateBPath, 'candidate_b_bundle_id'),
    fixtureId: getQueryValue(args.candidateBPath, 'fixture_id'),
  };
  const workbenchDirectPath = buildRoutePath('/workbench-compare', {
    baseline_run_id: workbenchSelection.baselineRunId,
    candidate_a_run_id: workbenchSelection.candidateARunId,
    candidate_b_bundle_id: workbenchSelection.candidateBBundleId,
    fixture_id: workbenchSelection.fixtureId,
  });
  const candidateBDirectPath = buildRoutePath('/candidate-b-trace', {
    baseline_run_id: candidateBSelection.baselineRunId ?? workbenchSelection.baselineRunId,
    candidate_a_run_id: candidateBSelection.candidateARunId ?? workbenchSelection.candidateARunId,
    candidate_b_bundle_id:
      candidateBSelection.candidateBBundleId ?? workbenchSelection.candidateBBundleId,
    fixture_id: candidateBSelection.fixtureId ?? workbenchSelection.fixtureId,
  });
  const browser = await chromium.launch({
    headless: true,
    channel: args.browserChannel,
    args: BROWSER_ARGS,
  });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await loginWithDevUser(page, args.baseUrl, args.timeoutMs);
    const projectUrl = await importLocalProject(page, args.baseUrl, args.appDir, args.timeoutMs);
    await page.waitForTimeout(15000);
    await page.getByText('Preview', { exact: true }).click().catch(() => {});

    let previewFrame = await ensureTrustedPreview(page, args.timeoutMs);
    previewFrame = await assertRootPreview(page, args.timeoutMs);

    previewFrame = await assertDocumentTrace(
      page,
      previewFrame,
      documentTraceSelection,
      args.timeoutMs,
    );
    previewFrame = await clickRoute(
      page,
      previewFrame,
      'Review',
      'Review route',
      async (currentFrame) => {
        const bodyText = await currentFrame.locator('body').innerText().catch(() => '');
        return /Runs loaded:\s*[1-9]/.test(bodyText);
      },
      args.timeoutMs,
    );
    previewFrame = await assertRootPreview(page, args.timeoutMs);

    previewFrame = await assertWorkbenchCompare(
      page,
      previewFrame,
      workbenchSelection,
      workbenchDirectPath,
      args.timeoutMs,
    );
    previewFrame = await clickRoute(
      page,
      previewFrame,
      'Review',
      'Review route',
      async (currentFrame) => {
        const bodyText = await currentFrame.locator('body').innerText().catch(() => '');
        return /Runs loaded:\s*[1-9]/.test(bodyText);
      },
      args.timeoutMs,
    );
    previewFrame = await assertRootPreview(page, args.timeoutMs);

    previewFrame = await assertCandidateBTrace(
      page,
      previewFrame,
      candidateBSelection,
      candidateBDirectPath,
      args.timeoutMs,
    );
    previewFrame = await clickRoute(
      page,
      previewFrame,
      'Review',
      'Review route',
      async (currentFrame) => {
        const bodyText = await currentFrame.locator('body').innerText().catch(() => '');
        return /Runs loaded:\s*[1-9]/.test(bodyText);
      },
      args.timeoutMs,
    );
    previewFrame = await assertRootPreview(page, args.timeoutMs);

    previewFrame = await clickRoute(
      page,
      previewFrame,
      'Analyst Insight',
      'Analyst Insight route',
      async (currentFrame) => {
        await waitForHydratedFrameMain(currentFrame, Math.min(args.timeoutMs, 10000));
        return currentFrame.getByRole('heading', { name: 'Analyst Insight' }).isVisible();
      },
      args.timeoutMs,
    );
    await assertAnalystInsight(page, previewFrame, args.timeoutMs);

    await assertCodeWriteback(
      page,
      duplicateFilePath,
      canonicalFilePath,
      args.proofMarker,
      args.timeoutMs,
    );

    console.log(
      JSON.stringify(
        {
          passed: true,
          projectUrl,
          previewOrigin: new URL(previewFrame.url()).origin,
          browserChannel: args.browserChannel,
          browserArgs: BROWSER_ARGS,
          proofFile: args.proofFile,
          proofMarker: args.proofMarker,
          routes: [
            '/',
            args.documentTracePath,
            args.workbenchPath,
            args.candidateBPath,
            '/analyst-insight',
          ],
          duplicateRestored: true,
          canonicalUntouched: true,
        },
        null,
        2,
      ),
    );
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack ?? error.message : String(error));
  process.exitCode = 1;
});
