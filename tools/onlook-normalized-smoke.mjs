import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const execFileAsync = promisify(execFile);
const DEFAULT_ACTIVE_PAIR_FILE = path.join(__dirname, 'onlook-active-pair.json');
const ROUTE_PLAN = [
  ['Workbench Compare', '/workbench-compare'],
  ['Document Trace', '/document-trace'],
];

async function loadChromium() {
  const moduleUrl = pathToFileURL(
    path.join(__dirname, '..', 'ext-onlook-fix', 'node_modules', 'playwright', 'index.mjs'),
  ).href;
  const module = await import(moduleUrl);
  const chromium = module.chromium ?? module.default?.chromium;
  if (!chromium) {
    throw new Error('Unable to load Playwright chromium from ext-onlook-fix/node_modules/playwright');
  }

  return chromium;
}

function parseArgs(argv) {
  const args = {
    projectUrl: null,
    projectUrlSource: null,
    previewOrigin: null,
    previewOriginSource: null,
    activePairFile: DEFAULT_ACTIVE_PAIR_FILE,
    browserChannel: 'chrome',
    runtimeDir: 'ext-onlook-fix',
    hostStartMode: 'unknown',
    timeoutMs: 120000,
    jsonOut: '',
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--project-url') {
      args.projectUrl = argv[index + 1];
      args.projectUrlSource = 'explicit';
      index += 1;
      continue;
    }
    if (token === '--project-url-source') {
      args.projectUrlSource = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--preview-origin') {
      args.previewOrigin = argv[index + 1];
      args.previewOriginSource = 'explicit';
      index += 1;
      continue;
    }
    if (token === '--preview-origin-source') {
      args.previewOriginSource = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--active-pair-file') {
      args.activePairFile = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--browser-channel') {
      args.browserChannel = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--runtime-dir') {
      args.runtimeDir = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--host-start-mode') {
      args.hostStartMode = argv[index + 1];
      index += 1;
      continue;
    }
    if (token === '--timeout-ms') {
      args.timeoutMs = Number(argv[index + 1]);
      index += 1;
      continue;
    }
    if (token === '--json-out') {
      args.jsonOut = argv[index + 1];
      index += 1;
    }
  }

  if (!Number.isFinite(args.timeoutMs) || args.timeoutMs <= 0) {
    throw new Error(`Invalid timeout: ${args.timeoutMs}`);
  }

  return args;
}

function normalizePreviewOrigin(value) {
  const url = new URL(value);
  url.pathname = '/';
  url.search = '';
  url.hash = '';
  return url.toString();
}

async function execText(command, commandArgs, cwd) {
  try {
    const { stdout } = await execFileAsync(command, commandArgs, {
      cwd,
      windowsHide: true,
      maxBuffer: 1024 * 1024,
    });
    return stdout.trim();
  } catch {
    return null;
  }
}

async function readJsonFile(filePath, label) {
  let text;
  try {
    text = await fs.readFile(filePath, 'utf8');
  } catch (error) {
    throw new Error(`Missing ${label}: ${filePath}`);
  }

  try {
    return JSON.parse(text);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new Error(`Invalid ${label} JSON at ${filePath}: ${detail}`);
  }
}

function parseStatusPaths(statusText) {
  if (!statusText) {
    return [];
  }

  return statusText
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter(Boolean)
    .map((line) => line.replace(/^[\sA-Z?!]{1,3}/, '').trim())
    .filter(Boolean);
}

async function readCurrentProvenance(runtimeDir) {
  const laneRoot = path.join(__dirname, '..');
  const runtimeRoot = path.join(laneRoot, runtimeDir);
  const laneHead = await execText('git', ['-C', laneRoot, 'rev-parse', 'HEAD'], laneRoot);
  const runtimeHead = await execText('git', ['-C', runtimeRoot, 'rev-parse', 'HEAD'], laneRoot);
  const runtimeStatus = await execText('git', ['-C', runtimeRoot, 'status', '--short'], laneRoot);
  const runtimeCloneDirtyPaths = parseStatusPaths(runtimeStatus);

  return {
    laneHead,
    runtimeHead,
    runtimeCloneHasLocalDiffPaths: runtimeCloneDirtyPaths.length > 0,
    runtimeCloneLocalDiffSummary: runtimeCloneDirtyPaths.length > 0
      ? `${runtimeCloneDirtyPaths.length} local diff path(s)`
      : 'clean',
  };
}

function assertActivePairState(state, filePath) {
  const requiredFields = [
    'projectUrl',
    'previewOrigin',
    'sourceLedgerPath',
    'verifiedAt',
    'laneHead',
    'runtimeCloneHead',
    'runtimeCloneHasLocalDiffPaths',
    'runtimeCloneLocalDiffSummary',
    'status',
    'statusReason',
  ];

  for (const field of requiredFields) {
    if (!(field in state)) {
      throw new Error(`Invalid active pair state in ${filePath}: missing ${field}`);
    }
  }

  if (!['verified-live', 'stale/unhealthy', 'no-active-default'].includes(state.status)) {
    throw new Error(`Invalid active pair state in ${filePath}: unsupported status ${state.status}`);
  }
}

async function resolvePairArgs(args) {
  const hasProjectUrl = Boolean(args.projectUrl);
  const hasPreviewOrigin = Boolean(args.previewOrigin);
  if (hasProjectUrl !== hasPreviewOrigin) {
    throw new Error('Default invocation requires either both --project-url and --preview-origin, or an active verified pair file.');
  }

  if (hasProjectUrl && hasPreviewOrigin) {
    return args;
  }

  const activePairPath = path.resolve(args.activePairFile);
  const activePairState = await readJsonFile(activePairPath, 'active pair state');
  assertActivePairState(activePairState, activePairPath);

  if (activePairState.status !== 'verified-live') {
    throw new Error(`No active verified pair available in ${activePairPath}; status=${activePairState.status}; reason=${activePairState.statusReason}; provide --project-url and --preview-origin explicitly.`);
  }

  const current = await readCurrentProvenance(args.runtimeDir);
  if (
    activePairState.laneHead !== current.laneHead
    || activePairState.runtimeCloneHead !== current.runtimeHead
    || Boolean(activePairState.runtimeCloneHasLocalDiffPaths) !== current.runtimeCloneHasLocalDiffPaths
    || activePairState.runtimeCloneLocalDiffSummary !== current.runtimeCloneLocalDiffSummary
  ) {
    throw new Error(`Active pair provenance does not match current lane/runtime state in ${activePairPath}; provide --project-url and --preview-origin explicitly.`);
  }

  const laneRoot = path.join(__dirname, '..');
  const ledgerPath = path.isAbsolute(activePairState.sourceLedgerPath)
    ? activePairState.sourceLedgerPath
    : path.join(laneRoot, activePairState.sourceLedgerPath);
  const ledger = await readJsonFile(ledgerPath, 'active pair source ledger');
  if (ledger.status !== 'pass') {
    throw new Error(`Active pair source ledger is not a passing normalized-smoke artifact: ${ledgerPath}`);
  }

  const activePreviewOrigin = normalizePreviewOrigin(activePairState.previewOrigin);
  const ledgerPreviewOrigin = normalizePreviewOrigin(ledger.previewOrigin);
  if (
    ledger.projectUrl !== activePairState.projectUrl
    || ledgerPreviewOrigin !== activePreviewOrigin
    || ledger.scope?.lane?.head !== activePairState.laneHead
    || ledger.scope?.runtimeClone?.head !== activePairState.runtimeCloneHead
  ) {
    throw new Error(`Active pair source ledger does not match ${activePairPath}; provide --project-url and --preview-origin explicitly.`);
  }

  args.projectUrl = activePairState.projectUrl;
  args.previewOrigin = activePairState.previewOrigin;
  args.projectUrlSource = 'active-verified-pair';
  args.previewOriginSource = 'active-verified-pair';
  return args;
}

async function buildScope(args) {
  const laneRoot = path.join(__dirname, '..');
  const repoRoot = path.join(laneRoot, '..', '..');
  const runtimeRoot = path.join(laneRoot, args.runtimeDir);
  const laneHead = await execText('git', ['-C', laneRoot, 'rev-parse', 'HEAD'], laneRoot);
  const runtimeHead = await execText('git', ['-C', runtimeRoot, 'rev-parse', 'HEAD'], laneRoot);
  const runtimeStatus = await execText('git', ['-C', runtimeRoot, 'status', '--short'], laneRoot);
  const runtimeCloneDirtyPaths = parseStatusPaths(runtimeStatus);

  return {
    lane: {
      worktreePath: path.relative(repoRoot, laneRoot).replace(/\\/g, '/'),
      head: laneHead,
    },
    runtimeClone: {
      dir: args.runtimeDir,
      head: runtimeHead,
      hasLocalDiffPaths: runtimeCloneDirtyPaths.length > 0,
      localDiffPaths: runtimeCloneDirtyPaths,
      localDiffSummary: runtimeCloneDirtyPaths.length > 0
        ? `${runtimeCloneDirtyPaths.length} local diff path(s)`
        : 'clean',
    },
    currentPair: {
      projectUrl: args.projectUrl,
      previewOrigin: args.previewOrigin,
      projectUrlSource: args.projectUrlSource,
      previewOriginSource: args.previewOriginSource,
    },
    browser: {
      channel: args.browserChannel,
      headed: true,
      freshContext: true,
    },
    hostStartMode: args.hostStartMode,
    routesCovered: ROUTE_PLAN.map(([route, expectedPath]) => ({
      route,
      expectedPath,
    })),
  };
}

async function getEditorMode(page) {
  return page.evaluate(() => {
    const radios = Array.from(document.querySelectorAll('button[role="radio"]'));
    const active = radios.find((radio) =>
      radio.getAttribute('aria-checked') === 'true' || radio.getAttribute('data-state') === 'on',
    );

    return active ? active.textContent.trim().toLowerCase() : null;
  });
}

async function getLoadingOverlay(page) {
  return page.evaluate(() => {
    const overlay = Array.from(document.querySelectorAll('div')).find((element) => {
      const className = typeof element.className === 'string' ? element.className : '';
      return className.includes('absolute inset-0 bg-background/80 backdrop-blur-sm');
    });

    if (!overlay) {
      return {
        present: false,
        className: null,
        text: null,
      };
    }

    const textElement = overlay.querySelector('.text-foreground');
    return {
      present: true,
      className: overlay.className,
      text: textElement ? textElement.textContent.trim() : overlay.textContent.trim(),
    };
  });
}

async function waitForOverlayToClear(page, timeoutMs) {
  const initialOverlay = await getLoadingOverlay(page);
  if (!initialOverlay.present) {
    return initialOverlay;
  }

  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const currentOverlay = await getLoadingOverlay(page);
    if (!currentOverlay.present) {
      return currentOverlay;
    }

    await page.waitForTimeout(1000);
  }

  const hostState = await page.evaluate(() => ({
    url: window.location.href,
    bodyText: (document.body?.innerText ?? '').slice(0, 1200),
  }));
  throw new Error(`Loading overlay remained active after preview-mode normalization: ${initialOverlay.text ?? initialOverlay.className ?? 'unknown overlay'}; host url=${hostState.url}; host body=${JSON.stringify(hostState.bodyText)}`);
}

async function waitForPreviewFrame(page, previewOrigin, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const frame = page.frames().find((item) => item.url().startsWith(previewOrigin));
    if (frame) {
      return frame;
    }

    await page.waitForTimeout(1000);
  }

  const pageState = await page.evaluate(() => ({
    url: window.location.href,
    bodyText: (document.body?.innerText ?? '').slice(0, 1200),
  }));
  throw new Error(`Timed out waiting for preview frame at ${previewOrigin}; host url=${pageState.url}; host body=${JSON.stringify(pageState.bodyText)}`);
}

async function clearTrustIfNeeded(frame, page, previewOrigin, timeoutMs) {
  const bodyText = await frame.evaluate(() => document.body?.innerText ?? '');
  if (!bodyText.includes('You are opening a CodeSandbox preview')) {
    return false;
  }

  await frame.evaluate(() => {
    const link = document.querySelector('a.btn-answer');
    if (link instanceof HTMLElement) {
      link.click();
    }
  });

  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const currentFrame = page.frames().find((item) => item.url().startsWith(previewOrigin));
    if (currentFrame) {
      try {
        const updatedText = await currentFrame.evaluate(() => document.body?.innerText ?? '');
        if (!updatedText.includes('You are opening a CodeSandbox preview')) {
          return true;
        }
      } catch (error) {
        if (!(error instanceof Error) || !error.message.includes('Execution context was destroyed')) {
          throw error;
        }
      }
    }

    await page.waitForTimeout(1000);
  }

  throw new Error('Timed out clearing the CodeSandbox trust interstitial');
}

async function switchToPreviewMode(page, timeoutMs) {
  const initialEditorMode = await getEditorMode(page);
  if (initialEditorMode === 'preview') {
    return {
      initialEditorMode,
      finalEditorMode: initialEditorMode,
      switched: false,
    };
  }

  const previewToggle = page.getByRole('radio', { name: 'Preview' }).first();
  await previewToggle.click({ timeout: timeoutMs });

  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const finalEditorMode = await getEditorMode(page);
    if (finalEditorMode === 'preview') {
      return {
        initialEditorMode,
        finalEditorMode,
        switched: true,
      };
    }

    await page.waitForTimeout(500);
  }

  throw new Error('Timed out switching the host editor mode to Preview');
}

async function waitForRootReview(frame, page, previewOrigin, timeoutMs) {
  try {
    const currentPath = await frame.evaluate(() => window.location.pathname).catch(() => null);
    if (currentPath && currentPath !== '/') {
      await frame.goto(previewOrigin, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
      frame = await waitForPreviewFrame(page, previewOrigin, timeoutMs);
    }

    const overview = frame.getByText('Review Overview').first();
    const workbench = frame.getByRole('link', { name: 'Workbench Compare' }).first();
    const documentTrace = frame.getByRole('link', { name: 'Document Trace' }).first();
    await overview.waitFor({ state: 'visible', timeout: timeoutMs });
    await workbench.waitFor({ state: 'visible', timeout: timeoutMs });
    await documentTrace.waitFor({ state: 'visible', timeout: timeoutMs });
    await page.waitForTimeout(1000);
  } catch {
    const previewState = await frame.evaluate(() => ({
      url: window.location.href,
      bodyText: (document.body?.innerText ?? '').slice(0, 1200),
    })).catch(() => ({
      url: frame.url(),
      bodyText: '<preview body unavailable>',
    }));
    const hostState = await page.evaluate(() => ({
      url: window.location.href,
      bodyText: (document.body?.innerText ?? '').slice(0, 1200),
    }));
    throw new Error(`Root review shell did not become visible; preview url=${previewState.url}; preview body=${JSON.stringify(previewState.bodyText)}; host url=${hostState.url}; host body=${JSON.stringify(hostState.bodyText)}`);
  }
}

async function normalizeSession(page, args) {
  const normalization = {
    loginNeeded: false,
    trustCleared: false,
    initialEditorMode: null,
    finalEditorModeBeforeSmoke: null,
    rootReviewVisible: false,
    overlayAtSmokeTime: null,
  };

  try {
    await page.goto(args.projectUrl, { waitUntil: 'domcontentloaded', timeout: args.timeoutMs });
    await page.waitForTimeout(2000);

    if (page.url().includes('/login')) {
      normalization.loginNeeded = true;
      await page.getByText('DEV MODE: Sign in as demo user').first().click({ timeout: args.timeoutMs });
      try {
        await page.waitForURL((url) => !url.pathname.endsWith('/login'), {
          timeout: 30000,
        });
      } catch {
        const loginState = await page.evaluate(() => ({
          url: window.location.href,
          bodyText: (document.body?.innerText ?? '').slice(0, 1200),
        }));
        throw new Error(`Dev-mode login did not complete; host url=${loginState.url}; host body=${JSON.stringify(loginState.bodyText)}`);
      }

      await page.goto(args.projectUrl, { waitUntil: 'domcontentloaded', timeout: args.timeoutMs });
      await page.waitForTimeout(4000);
      if (page.url().includes('/login')) {
        const loginState = await page.evaluate(() => ({
          url: window.location.href,
          bodyText: (document.body?.innerText ?? '').slice(0, 1200),
        }));
        throw new Error(`Dev-mode login did not persist to the project page; host url=${loginState.url}; host body=${JSON.stringify(loginState.bodyText)}`);
      }
    }

    let frame = await waitForPreviewFrame(page, args.previewOrigin, args.timeoutMs);
    normalization.trustCleared = await clearTrustIfNeeded(frame, page, args.previewOrigin, args.timeoutMs);

    frame = await waitForPreviewFrame(page, args.previewOrigin, args.timeoutMs);
    const previewMode = await switchToPreviewMode(page, args.timeoutMs);
    normalization.initialEditorMode = previewMode.initialEditorMode;
    normalization.finalEditorModeBeforeSmoke = previewMode.finalEditorMode;

    normalization.overlayAtSmokeTime = await getLoadingOverlay(page);
    if (normalization.overlayAtSmokeTime.present) {
      normalization.overlayAtSmokeTime = await waitForOverlayToClear(page, args.timeoutMs);
    }

    frame = await waitForPreviewFrame(page, args.previewOrigin, args.timeoutMs);
    await waitForRootReview(frame, page, args.previewOrigin, args.timeoutMs);
    frame = await waitForPreviewFrame(page, args.previewOrigin, args.timeoutMs);
    normalization.rootReviewVisible = true;

    return {
      frame,
      normalization,
    };
  } catch (error) {
    if (error instanceof Error) {
      error.normalization = normalization;
    }
    throw error;
  }
}

async function getPathState(frame) {
  return frame.evaluate(() => ({
    pathname: window.location.pathname,
    historyLength: window.history.length,
  }));
}

async function collectStacks(page, frame, chip) {
  const box = await chip.boundingBox();
  if (!box) {
    throw new Error('Route chip bounding box was unavailable');
  }

  const center = {
    x: box.x + (box.width / 2),
    y: box.y + (box.height / 2),
  };

  const iframeBox = await page.locator('iframe').boundingBox();
  if (!iframeBox) {
    throw new Error('Iframe bounding box was unavailable');
  }

  const previewCenter = {
    x: center.x - iframeBox.x,
    y: center.y - iframeBox.y,
  };

  const hostStack = await page.evaluate(({ x, y }) => {
    return document.elementsFromPoint(x, y).slice(0, 5).map((element) => {
      const rect = element.getBoundingClientRect();
      return {
        tag: element.tagName,
        className: element.className || '',
        text: (element.textContent || '').trim().slice(0, 120),
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
      };
    });
  }, center);

  const previewStack = await frame.evaluate(({ x, y }) => {
    return document.elementsFromPoint(x, y).slice(0, 5).map((element) => {
      const rect = element.getBoundingClientRect();
      return {
        tag: element.tagName,
        className: element.className || '',
        text: (element.textContent || '').trim().slice(0, 120),
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
      };
    });
  }, previewCenter);

  return {
    center,
    hostStack,
    previewStack,
  };
}

function describeElement(element) {
  if (!element) {
    return 'none';
  }

  const parts = [element.tag];
  if (element.className) {
    parts.push(element.className);
  }
  if (element.text) {
    parts.push(`"${element.text}"`);
  }
  return parts.join(' ');
}

function routeFailureReason(routeName, before, after, overlay, hostStack, previewStack) {
  if (overlay?.present) {
    return `loading overlay present at smoke time: ${overlay.text ?? overlay.className ?? 'unknown overlay'}`;
  }

  const hostTop = hostStack[0];
  if (hostTop?.tag !== 'IFRAME') {
    return `host topmost element intercepted the click: ${describeElement(hostTop)}`;
  }

  const previewTop = previewStack[0];
  if (previewTop?.tag !== 'A') {
    return `preview topmost element was not the route chip: ${describeElement(previewTop)}`;
  }

  return `${routeName} did not navigate after a real mouse route-chip click (${before.pathname} -> ${after.pathname})`;
}

function classifyFailure(message, routes = []) {
  const text = String(message ?? '');

  if (routes.some((route) => route.pass === false)) {
    return {
      bucket: 8,
      label: 'route-chip mouse verdict failed after normalization',
    };
  }

  if (text.includes('Dev-mode login')) {
    return {
      bucket: 2,
      label: 'auth / dev-login failure',
    };
  }

  if (text.includes('Timed out waiting for preview frame')) {
    return {
      bucket: 3,
      label: 'preview frame missing',
    };
  }

  if (text.includes('Timed out clearing the CodeSandbox trust interstitial')) {
    return {
      bucket: 4,
      label: 'CodeSandbox trust interstitial not cleared',
    };
  }

  if (text.includes('Timed out switching the host editor mode to Preview')) {
    return {
      bucket: 5,
      label: 'preview mode not reached',
    };
  }

  if (text.includes('Root review shell did not become visible')) {
    return {
      bucket: 6,
      label: 'root review not restored',
    };
  }

  if (text.includes('Loading overlay remained active after preview-mode normalization')) {
    return {
      bucket: 7,
      label: 'loading overlay never cleared',
    };
  }

  if (text.includes('Timed out waiting for HTTP readiness')) {
    return {
      bucket: 1,
      label: 'host startup / 3011 unavailable',
    };
  }

  return {
    bucket: 9,
    label: 'unclassified normalization/tooling failure',
  };
}

async function smokeRoute(page, args, routeName, expectedPath, prepared = null) {
  const { frame, normalization } = prepared ?? await normalizeSession(page, args);
  const chip = frame.getByRole('link', { name: routeName }).first();
  await chip.waitFor({ state: 'visible', timeout: args.timeoutMs });

  const before = await getPathState(frame);
  const stacks = await collectStacks(page, frame, chip);
  await page.mouse.click(stacks.center.x, stacks.center.y);

  try {
    await frame.waitForFunction((pathname) => window.location.pathname !== pathname, before.pathname, {
      timeout: 5000,
    });
  } catch {
    // Fail closed below using the final pathname/history snapshot.
  }

  const after = await getPathState(frame);
  const pass = after.pathname === expectedPath && after.historyLength > before.historyLength;

  return {
    route: routeName,
    expectedPath,
    overlayAtSmokeTime: normalization.overlayAtSmokeTime,
    before,
    after,
    pass,
    failureReason: pass
      ? null
      : routeFailureReason(
          routeName,
          before,
          after,
          normalization.overlayAtSmokeTime,
          stacks.hostStack,
          stacks.previewStack,
        ),
    hostHitStack: stacks.hostStack,
    previewHitStack: stacks.previewStack,
  };
}

async function main() {
  const args = await resolvePairArgs(parseArgs(process.argv.slice(2)));
  args.previewOrigin = normalizePreviewOrigin(args.previewOrigin);
  const scope = await buildScope(args);

  const chromium = await loadChromium();
  const browser = await chromium.launch({
    channel: args.browserChannel,
    headless: false,
    slowMo: 150,
  });

  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  const ledger = {
    status: 'fail',
    browser: {
      channel: args.browserChannel,
      headed: true,
    },
    projectUrl: args.projectUrl,
    previewOrigin: args.previewOrigin,
    scope,
    normalization: null,
    routes: [],
    classification: null,
    failureReason: null,
  };

  try {
    const firstNormalization = await normalizeSession(page, args);
    ledger.normalization = firstNormalization.normalization;

    let prepared = firstNormalization;
    for (const [routeName, expectedPath] of ROUTE_PLAN) {
      const result = await smokeRoute(page, args, routeName, expectedPath, prepared);
      ledger.routes.push(result);
      if (!result.pass && !ledger.failureReason) {
        ledger.failureReason = `${routeName}: ${result.failureReason}`;
      }
      prepared = null;
    }

    ledger.status = ledger.routes.every((route) => route.pass) ? 'pass' : 'fail';
    ledger.classification = ledger.status === 'fail'
      ? classifyFailure(ledger.failureReason, ledger.routes)
      : null;

    const output = JSON.stringify(ledger, null, 2);
    if (args.jsonOut) {
      await fs.writeFile(args.jsonOut, `${output}\n`, 'utf8');
    }
    console.log(output);

    if (ledger.status !== 'pass') {
      process.exitCode = 1;
    }
  } catch (error) {
    ledger.status = 'fail';
    ledger.normalization = error?.normalization ?? ledger.normalization;
    ledger.failureReason = error instanceof Error ? error.message : String(error);
    ledger.classification = classifyFailure(ledger.failureReason, ledger.routes);
    const output = JSON.stringify(ledger, null, 2);
    if (args.jsonOut) {
      await fs.writeFile(args.jsonOut, `${output}\n`, 'utf8');
    }
    console.log(output);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await main();
