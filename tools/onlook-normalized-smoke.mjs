import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const execFileAsync = promisify(execFile);
const DEFAULT_ACTIVE_PAIR_FILE = path.join(__dirname, 'onlook-active-pair.json');
const LANE_HELPER_FILES = [
  'tools/run-onlook-normalized-smoke.ps1',
  'tools/onlook-normalized-smoke.mjs',
  'tools/start-onlook-web.ps1',
];
const RUNTIME_GENERATED_PATHS = [
  'apps/web/client/messages/en.d.json.ts',
  'apps/web/client/public/onlook-preload-script.js',
];
const ROUTE_PLAN = [
  ['Workbench Compare', '/workbench-compare'],
  ['Document Trace', '/document-trace'],
];
const MAX_BREADCRUMBS = 80;
const MAX_CHECKPOINTS = 20;
const MAX_FRAME_EVENTS = 120;
const MAX_CONSOLE_ENTRIES = 80;
const MAX_NETWORK_ENTRIES = 80;
const PREVIEW_QUIET_MS = 1500;
const ROOT_REVIEW_LOADING_MARKERS = [
  'Loading review runs from the sandbox fixture API...',
  'Loading overview payload for the selected run...',
];
const ROOT_REVIEW_DEGRADED_MARKERS = [
  'No reviewable runs found',
  'Runs loaded: 0',
];

function isoNow() {
  return new Date().toISOString();
}

function pushBounded(list, value, maxEntries) {
  list.push(value);
  if (list.length > maxEntries) {
    list.splice(0, list.length - maxEntries);
  }
}

function truncateText(value, maxLength = 1200) {
  return String(value ?? '').slice(0, maxLength);
}

function safeFrameUrl(frame) {
  try {
    return frame?.url?.() ?? '';
  } catch {
    return '';
  }
}

function safeFrameName(frame) {
  try {
    return frame?.name?.() ?? '';
  } catch {
    return '';
  }
}

function nextOrder(observability) {
  observability.sequence += 1;
  return observability.sequence;
}

function createObservability(previewOrigin, hostOrigin) {
  return {
    previewOrigin,
    hostOrigin,
    sequence: 0,
    targetPreviewFrame: null,
    lastKnownTargetFrameUrl: null,
    lastPreviewInstabilityAtMs: 0,
    data: {
      breadcrumbs: [],
      checkpoints: [],
      frameLifecycleEvents: [],
      consoleEntries: [],
      networkEntries: [],
    },
  };
}

function rememberPreviewFrame(observability, frame) {
  if (!frame) {
    return frame;
  }

  observability.targetPreviewFrame = frame;
  const frameUrl = safeFrameUrl(frame);
  if (frameUrl.startsWith(observability.previewOrigin)) {
    observability.lastKnownTargetFrameUrl = frameUrl;
  }
  return frame;
}

function recordBreadcrumb(observability, phase, details = {}) {
  pushBounded(
    observability.data.breadcrumbs,
    {
      order: nextOrder(observability),
      at: isoNow(),
      phase,
      ...details,
    },
    MAX_BREADCRUMBS,
  );
}

function markPreviewInstability(observability) {
  observability.lastPreviewInstabilityAtMs = Date.now();
}

function isPreviewRelevantFrame(observability, frame) {
  if (!frame) {
    return false;
  }

  const url = safeFrameUrl(frame);
  if (url.startsWith(observability.previewOrigin)) {
    return true;
  }

  if (observability.targetPreviewFrame && frame === observability.targetPreviewFrame) {
    return true;
  }

  if (observability.lastKnownTargetFrameUrl && url === observability.lastKnownTargetFrameUrl) {
    return true;
  }

  const parentFrame = frame.parentFrame?.();
  if (!parentFrame) {
    return false;
  }

  return isPreviewRelevantFrame(observability, parentFrame);
}

function attachObservability(page, observability) {
  page.on('frameattached', (frame) => {
    if (isPreviewRelevantFrame(observability, frame)) {
      markPreviewInstability(observability);
    }
    pushBounded(
      observability.data.frameLifecycleEvents,
      {
        order: nextOrder(observability),
        at: isoNow(),
        event: 'frameattached',
        relevantToPreview: isPreviewRelevantFrame(observability, frame),
        url: safeFrameUrl(frame),
        name: safeFrameName(frame),
        parentUrl: safeFrameUrl(frame.parentFrame?.()),
      },
      MAX_FRAME_EVENTS,
    );
  });

  page.on('framedetached', (frame) => {
    if (isPreviewRelevantFrame(observability, frame)) {
      markPreviewInstability(observability);
    }
    pushBounded(
      observability.data.frameLifecycleEvents,
      {
        order: nextOrder(observability),
        at: isoNow(),
        event: 'framedetached',
        relevantToPreview: isPreviewRelevantFrame(observability, frame),
        url: safeFrameUrl(frame) || observability.lastKnownTargetFrameUrl || '',
        name: safeFrameName(frame),
        parentUrl: safeFrameUrl(frame.parentFrame?.()),
      },
      MAX_FRAME_EVENTS,
    );
  });

  page.on('framenavigated', (frame) => {
    const frameUrl = safeFrameUrl(frame);
    if (frameUrl.startsWith(observability.previewOrigin)) {
      observability.lastKnownTargetFrameUrl = frameUrl;
      observability.targetPreviewFrame = frame;
      markPreviewInstability(observability);
    }

    pushBounded(
      observability.data.frameLifecycleEvents,
      {
        order: nextOrder(observability),
        at: isoNow(),
        event: 'framenavigated',
        relevantToPreview: isPreviewRelevantFrame(observability, frame),
        url: frameUrl,
        name: safeFrameName(frame),
        parentUrl: safeFrameUrl(frame.parentFrame?.()),
      },
      MAX_FRAME_EVENTS,
    );
  });

  page.on('console', (message) => {
    const type = message.type();
    if (!['error', 'warning'].includes(type)) {
      return;
    }

    const location = message.location();
    const url = location?.url ?? '';
    const surface = url.startsWith(observability.previewOrigin)
      ? 'preview'
      : url.startsWith(observability.hostOrigin)
        ? 'host'
        : 'other';

    pushBounded(
      observability.data.consoleEntries,
      {
        order: nextOrder(observability),
        at: isoNow(),
        type,
        surface,
        url,
        text: truncateText(message.text(), 500),
      },
      MAX_CONSOLE_ENTRIES,
    );

    if (
      surface === 'preview'
      && (
        url.includes('/_next/static/webpack/')
        || type === 'error'
      )
    ) {
      markPreviewInstability(observability);
    }
  });

  page.on('response', (response) => {
    const url = response.url();
    if (!url.startsWith(observability.previewOrigin) && !url.startsWith(observability.hostOrigin)) {
      return;
    }

    let frameUrl = '';
    try {
      frameUrl = safeFrameUrl(response.frame());
    } catch {
      frameUrl = '';
    }

    if (
      url.startsWith(observability.previewOrigin)
      && (
        response.request().resourceType() === 'document'
        || url.includes('/_next/static/webpack/')
        || url.includes('hot-update')
      )
    ) {
      markPreviewInstability(observability);
    }

    pushBounded(
      observability.data.networkEntries,
      {
        order: nextOrder(observability),
        at: isoNow(),
        surface: url.startsWith(observability.previewOrigin) ? 'preview' : 'host',
        url,
        status: response.status(),
        resourceType: response.request().resourceType(),
        frameUrl,
      },
      MAX_NETWORK_ENTRIES,
    );
  });
}

async function collectHostSnapshot(page) {
  let url = null;
  let bodyTextSnippet = null;
  let editorMode = null;
  let overlay = null;
  let readError = null;

  try {
    const state = await page.evaluate(() => ({
      url: window.location.href,
      bodyText: (document.body?.innerText ?? '').slice(0, 1200),
    }));
    url = state.url;
    bodyTextSnippet = state.bodyText;
  } catch (error) {
    readError = error instanceof Error ? error.message : String(error);
  }

  try {
    editorMode = await getEditorMode(page);
  } catch {
    editorMode = null;
  }

  try {
    overlay = await getLoadingOverlay(page);
  } catch {
    overlay = null;
  }

  return {
    url,
    bodyTextSnippet,
    editorMode,
    overlay,
    readError,
  };
}

async function collectPreviewSnapshot(page, observability, frame = null) {
  if (frame) {
    rememberPreviewFrame(observability, frame);
  }

  const allFrames = page.frames();
  const previewFrames = allFrames.filter((item) => safeFrameUrl(item).startsWith(observability.previewOrigin));

  let activeTargetFrame = null;
  if (observability.targetPreviewFrame && allFrames.includes(observability.targetPreviewFrame)) {
    activeTargetFrame = observability.targetPreviewFrame;
  } else if (previewFrames.length > 0) {
    activeTargetFrame = previewFrames[0];
    rememberPreviewFrame(observability, activeTargetFrame);
  }

  const targetFrameStillExists = Boolean(
    observability.targetPreviewFrame && allFrames.includes(observability.targetPreviewFrame),
  );
  const replacementState = observability.targetPreviewFrame && !targetFrameStillExists
    ? (previewFrames.length > 0 ? 'replaced' : 'vanished')
    : 'same';

  let previewBodySnippet = null;
  let readError = null;
  if (activeTargetFrame) {
    try {
      const previewState = await activeTargetFrame.evaluate(() => ({
        url: window.location.href,
        bodyText: (document.body?.innerText ?? '').slice(0, 1200),
      }));
      observability.lastKnownTargetFrameUrl = previewState.url;
      previewBodySnippet = previewState.bodyText;
    } catch (error) {
      readError = error instanceof Error ? error.message : String(error);
    }
  }

  return {
    frameList: allFrames.map((item) => ({
      url: safeFrameUrl(item),
      name: safeFrameName(item),
      parentUrl: safeFrameUrl(item.parentFrame?.()),
    })),
    lastKnownTargetFrameUrl: observability.lastKnownTargetFrameUrl,
    targetFrameStillExists,
    replacementState,
    previewBodySnippet,
    readError,
  };
}

async function captureCheckpoint(page, observability, phase, frame = null) {
  recordBreadcrumb(observability, phase);
  const host = await collectHostSnapshot(page);
  const preview = await collectPreviewSnapshot(page, observability, frame);
  pushBounded(
    observability.data.checkpoints,
    {
      order: nextOrder(observability),
      at: isoNow(),
      phase,
      host,
      preview,
    },
    MAX_CHECKPOINTS,
  );
}

function classifyRootReviewBody(bodyText) {
  const text = String(bodyText ?? '');
  const loadingMarkers = ROOT_REVIEW_LOADING_MARKERS.filter((marker) => text.includes(marker));
  const degradedMarkers = ROOT_REVIEW_DEGRADED_MARKERS.filter((marker) => text.includes(marker));

  return {
    ready: loadingMarkers.length === 0 && degradedMarkers.length === 0,
    loadingMarkers,
    degradedMarkers,
    text,
  };
}

async function readPreviewBody(frame) {
  return frame.evaluate(() => (document.body?.innerText ?? '').slice(0, 1200));
}

async function waitForPreviewQuiet(page, observability, previewOrigin, timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const frame = page.frames().find((item) => item.url().startsWith(previewOrigin));
    if (!frame) {
      await page.waitForTimeout(500);
      continue;
    }

    rememberPreviewFrame(observability, frame);
    const quietForMs = Date.now() - observability.lastPreviewInstabilityAtMs;
    if (quietForMs < PREVIEW_QUIET_MS) {
      await page.waitForTimeout(500);
      continue;
    }

    try {
      const readyState = await frame.evaluate(() => document.readyState);
      if (readyState === 'interactive' || readyState === 'complete') {
        return frame;
      }
    } catch (error) {
      if (
        !(error instanceof Error)
        || (
          !error.message.includes('Execution context was destroyed')
          && !error.message.includes('Frame was detached')
        )
      ) {
        throw error;
      }
    }

    await page.waitForTimeout(500);
  }

  const pageState = await page.evaluate(() => ({
    url: window.location.href,
    bodyText: (document.body?.innerText ?? '').slice(0, 1200),
  }));
  throw new Error(`Preview did not settle at ${previewOrigin}; host url=${pageState.url}; host body=${JSON.stringify(pageState.bodyText)}`);
}

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

async function getFileSha256(filePath) {
  const text = await fs.readFile(filePath, 'utf8');
  const normalized = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  return crypto.createHash('sha256').update(normalized, 'utf8').digest('hex');
}

async function readLaneHelperHashes() {
  const laneRoot = path.join(__dirname, '..');
  const helperHashes = {};

  for (const repoPath of LANE_HELPER_FILES) {
    const fullPath = path.join(laneRoot, ...repoPath.split('/'));
    helperHashes[repoPath] = await getFileSha256(fullPath);
  }

  return helperHashes;
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

async function isLineEndingOnlyDrift(repoRoot, repoPaths) {
  for (const repoPath of repoPaths) {
    const fullPath = path.join(repoRoot, ...repoPath.split('/'));
    try {
      await fs.access(fullPath);
    } catch {
      return false;
    }
  }

  for (const diffMode of [[], ['--cached']]) {
    try {
      await execFileAsync('git', ['-C', repoRoot, 'diff', ...diffMode, '--ignore-space-at-eol', '--exit-code', '--', ...repoPaths], {
        cwd: repoRoot,
      });
    } catch {
      return false;
    }
  }

  return true;
}

async function readCurrentProvenance(runtimeDir) {
  const laneRoot = path.join(__dirname, '..');
  const runtimeRoot = path.join(laneRoot, runtimeDir);
  const laneHead = await execText('git', ['-C', laneRoot, 'rev-parse', 'HEAD'], laneRoot);
  const runtimeHead = await execText('git', ['-C', runtimeRoot, 'rev-parse', 'HEAD'], laneRoot);
  const runtimeTree = await execText('git', ['-C', runtimeRoot, 'rev-parse', 'HEAD^{tree}'], laneRoot);
  const runtimeStatus = await execText('git', ['-C', runtimeRoot, 'status', '--short'], laneRoot);
  let runtimeCloneDirtyPaths = parseStatusPaths(runtimeStatus);
  if (runtimeCloneDirtyPaths.length > 0) {
    const onlyRuntimeGenerated = runtimeCloneDirtyPaths.every((repoPath) => RUNTIME_GENERATED_PATHS.includes(repoPath));
    if (onlyRuntimeGenerated && await isLineEndingOnlyDrift(runtimeRoot, RUNTIME_GENERATED_PATHS)) {
      runtimeCloneDirtyPaths = [];
    }
  }

  return {
    laneHead,
    runtimeHead,
    runtimeTree,
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
    'runtimeCloneTree',
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
    activePairState.runtimeCloneTree !== current.runtimeTree
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
    || ledger.scope?.runtimeClone?.tree !== activePairState.runtimeCloneTree
  ) {
    throw new Error(`Active pair source ledger does not match ${activePairPath}; provide --project-url and --preview-origin explicitly.`);
  }

  const helperFiles = ledger.scope?.lane?.helperFiles;
  if (helperFiles && Object.keys(helperFiles).length > 0) {
    const currentHelperFiles = await readLaneHelperHashes();
    const mismatches = [];
    for (const [repoPath, expectedHash] of Object.entries(helperFiles)) {
      const currentHash = currentHelperFiles[repoPath];
      if (!currentHash) {
        mismatches.push(`${repoPath} (missing locally)`);
        continue;
      }

      if (currentHash !== String(expectedHash).toLowerCase()) {
        mismatches.push(`${repoPath} (${currentHash} != ${expectedHash})`);
      }
    }

    if (mismatches.length > 0) {
      throw new Error(`Active pair helper provenance does not match current lane helper state in ${activePairPath}; provide --project-url and --preview-origin explicitly. Mismatches: ${mismatches.join('; ')}`);
    }
  } else if (activePairState.laneHead !== current.laneHead) {
    throw new Error(`Active pair provenance does not match current lane/runtime state in ${activePairPath}; provide --project-url and --preview-origin explicitly.`);
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
  const runtimeTree = await execText('git', ['-C', runtimeRoot, 'rev-parse', 'HEAD^{tree}'], laneRoot);
  const runtimeStatus = await execText('git', ['-C', runtimeRoot, 'status', '--short'], laneRoot);
  let runtimeCloneDirtyPaths = parseStatusPaths(runtimeStatus);
  if (runtimeCloneDirtyPaths.length > 0) {
    const onlyRuntimeGenerated = runtimeCloneDirtyPaths.every((repoPath) => RUNTIME_GENERATED_PATHS.includes(repoPath));
    if (onlyRuntimeGenerated && await isLineEndingOnlyDrift(runtimeRoot, RUNTIME_GENERATED_PATHS)) {
      runtimeCloneDirtyPaths = [];
    }
  }
  const helperFiles = await readLaneHelperHashes();

  return {
    lane: {
      worktreePath: path.relative(repoRoot, laneRoot).replace(/\\/g, '/'),
      head: laneHead,
      helperFiles,
    },
    runtimeClone: {
      dir: args.runtimeDir,
      head: runtimeHead,
      tree: runtimeTree,
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

function isRecoverablePreviewError(error) {
  return error instanceof Error && (
    error.message.includes('Execution context was destroyed')
    || error.message.includes('Frame was detached')
  );
}

async function waitForRootReview(page, observability, previewOrigin, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastFrame = null;

  while (Date.now() < deadline) {
    try {
      const remainingMs = deadline - Date.now();
      let frame = await waitForPreviewFrame(page, previewOrigin, Math.max(1000, remainingMs));
      rememberPreviewFrame(observability, frame);
      frame = await waitForPreviewQuiet(page, observability, previewOrigin, Math.min(remainingMs, timeoutMs));
      lastFrame = frame;

      const currentPath = await frame.evaluate(() => window.location.pathname).catch(() => (
        getPathnameFromUrl(safeFrameUrl(frame))
        ?? getPathnameFromUrl(observability.lastKnownTargetFrameUrl)
      ));
      if (currentPath && currentPath !== '/') {
        await frame.goto(previewOrigin, { waitUntil: 'domcontentloaded', timeout: Math.max(1000, remainingMs) });
        frame = await waitForPreviewFrame(page, previewOrigin, Math.max(1000, deadline - Date.now()));
        rememberPreviewFrame(observability, frame);
        frame = await waitForPreviewQuiet(page, observability, previewOrigin, Math.max(1000, deadline - Date.now()));
        lastFrame = frame;
      }

      const overview = frame.getByText('Review Overview').first();
      const workbench = frame.getByRole('link', { name: 'Workbench Compare' }).first();
      const documentTrace = frame.getByRole('link', { name: 'Document Trace' }).first();
      await overview.waitFor({ state: 'visible', timeout: Math.max(1000, deadline - Date.now()) });
      await workbench.waitFor({ state: 'visible', timeout: Math.max(1000, deadline - Date.now()) });
      await documentTrace.waitFor({ state: 'visible', timeout: Math.max(1000, deadline - Date.now()) });

      const previewBody = await readPreviewBody(frame);
      const rootReview = classifyRootReviewBody(previewBody);
      if (rootReview.ready) {
        await page.waitForTimeout(500);
        return frame;
      }
    } catch (error) {
      if (!isRecoverablePreviewError(error)) {
        break;
      }
    }

    await page.waitForTimeout(1000);
  }

  const targetFrame = lastFrame ?? page.frames().find((item) => item.url().startsWith(previewOrigin));
  const previewState = targetFrame
    ? await targetFrame.evaluate(() => ({
        url: window.location.href,
        bodyText: (document.body?.innerText ?? '').slice(0, 1200),
      })).catch(() => ({
        url: targetFrame.url(),
        bodyText: '<preview body unavailable>',
      }))
    : {
        url: previewOrigin,
        bodyText: '<preview body unavailable>',
      };
  const hostState = await page.evaluate(() => ({
    url: window.location.href,
    bodyText: (document.body?.innerText ?? '').slice(0, 1200),
  }));
  throw new Error(`Root review shell did not become visible; preview url=${previewState.url}; preview body=${JSON.stringify(previewState.bodyText)}; host url=${hostState.url}; host body=${JSON.stringify(hostState.bodyText)}`);
}

async function normalizeSession(page, args, observability) {
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
    recordBreadcrumb(observability, 'host-opened', {
      hostUrl: page.url(),
    });

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

      recordBreadcrumb(observability, 'post-login', {
        hostUrl: page.url(),
      });
    }

    let frame = await waitForPreviewFrame(page, args.previewOrigin, args.timeoutMs);
    rememberPreviewFrame(observability, frame);
    recordBreadcrumb(observability, 'preview-frame-found', {
      previewUrl: safeFrameUrl(frame),
    });
    normalization.trustCleared = await clearTrustIfNeeded(frame, page, args.previewOrigin, args.timeoutMs);
    recordBreadcrumb(observability, 'trust-cleared', {
      cleared: normalization.trustCleared,
    });

    frame = await waitForPreviewFrame(page, args.previewOrigin, args.timeoutMs);
    rememberPreviewFrame(observability, frame);
    const previewMode = await switchToPreviewMode(page, args.timeoutMs);
    normalization.initialEditorMode = previewMode.initialEditorMode;
    normalization.finalEditorModeBeforeSmoke = previewMode.finalEditorMode;
    recordBreadcrumb(observability, 'preview-mode-set', {
      editorMode: previewMode.finalEditorMode,
    });

    normalization.overlayAtSmokeTime = await getLoadingOverlay(page);
    if (normalization.overlayAtSmokeTime.present) {
      normalization.overlayAtSmokeTime = await waitForOverlayToClear(page, args.timeoutMs);
    }

    frame = await waitForRootReview(page, observability, args.previewOrigin, args.timeoutMs);
    frame = await waitForPreviewQuiet(page, observability, args.previewOrigin, args.timeoutMs);
    rememberPreviewFrame(observability, frame);
    normalization.rootReviewVisible = true;
    await captureCheckpoint(page, observability, 'root-review-visible', frame);

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

async function restoreRootReview(page, args, observability) {
  let frame = await waitForRootReview(page, observability, args.previewOrigin, args.timeoutMs);
  frame = await waitForPreviewQuiet(page, observability, args.previewOrigin, args.timeoutMs);
  rememberPreviewFrame(observability, frame);
  await captureCheckpoint(page, observability, 'root-review-visible', frame);
  return frame;
}

async function getPathState(frame) {
  return frame.evaluate(() => ({
    pathname: window.location.pathname,
    historyLength: window.history.length,
  }));
}

async function waitForRouteNavigation(page, observability, previewOrigin, beforePathname, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastFrame = null;
  let lastState = null;

  while (Date.now() < deadline) {
    try {
      const frame = await waitForPreviewQuiet(
        page,
        observability,
        previewOrigin,
        Math.max(1000, deadline - Date.now()),
      );
      rememberPreviewFrame(observability, frame);
      lastFrame = frame;
      lastState = await getPathState(frame);
      if (lastState.pathname !== beforePathname) {
        return {
          frame,
          after: lastState,
        };
      }
    } catch (error) {
      if (!isRecoverablePreviewError(error)) {
        throw error;
      }
    }

    await page.waitForTimeout(250);
  }

  if (!lastFrame) {
    try {
      lastFrame = await waitForPreviewFrame(page, previewOrigin, 1000);
      rememberPreviewFrame(observability, lastFrame);
    } catch {
      lastFrame = null;
    }
  }

  if (lastFrame) {
    try {
      lastState = await getPathState(lastFrame);
    } catch (error) {
      if (!isRecoverablePreviewError(error)) {
        throw error;
      }
    }
  }

  if (!lastFrame) {
    throw new Error(`Preview frame vanished after route click and did not recover within ${timeoutMs}ms`);
  }

  return {
    frame: lastFrame,
    after: lastState ?? {
      pathname: beforePathname,
      historyLength: 0,
    },
  };
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

function getPathnameFromUrl(urlValue) {
  if (!urlValue) {
    return null;
  }

  try {
    return new URL(urlValue).pathname;
  } catch {
    return null;
  }
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

function classifyFailurePhase(message, routes = [], stage = null) {
  const text = String(message ?? '');

  if (text.includes('Frame was detached') || text.includes('Execution context was destroyed')) {
    return 'frame-detach / preview loss';
  }

  if (routes.some((route) => route.pass === false) || stage === 'route verdict') {
    return 'route verdict';
  }

  if (text.includes('Root review shell did not become visible')) {
    return 'root-review restoration';
  }

  if (
    text.includes('Timed out waiting for preview frame')
    || text.includes('Timed out clearing the CodeSandbox trust interstitial')
    || text.includes('Timed out switching the host editor mode to Preview')
  ) {
    return 'trust/frame entry';
  }

  return 'other';
}

async function writeArtifacts(args, ledger, observability) {
  const output = JSON.stringify(ledger, null, 2);
  if (args.jsonOut) {
    await fs.writeFile(args.jsonOut, `${output}\n`, 'utf8');
    const observabilityPath = path.join(path.dirname(args.jsonOut), 'observability.json');
    await fs.writeFile(
      observabilityPath,
      `${JSON.stringify(observability.data, null, 2)}\n`,
      'utf8',
    );
    ledger.artifacts = {
      observability: observabilityPath,
    };
    await fs.writeFile(args.jsonOut, `${JSON.stringify(ledger, null, 2)}\n`, 'utf8');
  }
  console.log(JSON.stringify(ledger, null, 2));
}

async function smokeRoute(page, args, observability, routeName, expectedPath, prepared = null) {
  const preparedState = prepared ?? await normalizeSession(page, args, observability);
  let frame = preparedState.frame;
  const { normalization } = preparedState;
  frame = await waitForPreviewQuiet(page, observability, args.previewOrigin, Math.min(args.timeoutMs, 5000));
  rememberPreviewFrame(observability, frame);
  await captureCheckpoint(page, observability, `route-start:${routeName}`, frame);

  let routeStage = 'route-start';
  let before = null;
  let stacks = null;

  try {
    const chip = frame.getByRole('link', { name: routeName }).first();
    await chip.waitFor({ state: 'visible', timeout: args.timeoutMs });
    routeStage = 'route-link-visible';
    recordBreadcrumb(observability, `route-link-visible:${routeName}`, {
      route: routeName,
      locatorVisible: true,
    });

    before = await getPathState(frame);
    stacks = await collectStacks(page, frame, chip);
    await page.mouse.click(stacks.center.x, stacks.center.y);
    routeStage = 'route-clicked';
    recordBreadcrumb(observability, `route-clicked:${routeName}`, {
      route: routeName,
    });

    const routeOutcome = await waitForRouteNavigation(
      page,
      observability,
      args.previewOrigin,
      before.pathname,
      5000,
    );
    frame = routeOutcome.frame ?? frame;
    const after = routeOutcome.after ?? before;
    const pass = after.pathname === expectedPath && after.historyLength > before.historyLength;

    return {
      route: routeName,
      expectedPath,
      overlayAtSmokeTime: normalization.overlayAtSmokeTime,
      locatorVisible: true,
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
  } catch (error) {
    if (error instanceof Error) {
      error.routeName = routeName;
      error.routeStage = routeStage;
      error.routeBefore = before;
      error.routeStacks = stacks;
      error.normalization = error.normalization ?? normalization;
    }
    await captureCheckpoint(page, observability, 'failure', frame).catch(() => {});
    if (error instanceof Error) {
      error.failureCheckpointRecorded = true;
    }
    throw error;
  }
}

async function main() {
  const args = await resolvePairArgs(parseArgs(process.argv.slice(2)));
  args.previewOrigin = normalizePreviewOrigin(args.previewOrigin);
  const scope = await buildScope(args);
  const observability = createObservability(args.previewOrigin, new URL(args.projectUrl).origin);

  const chromium = await loadChromium();
  const browser = await chromium.launch({
    channel: args.browserChannel,
    headless: false,
    slowMo: 150,
  });

  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  attachObservability(page, observability);
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
    failurePhase: null,
    failureRoute: null,
    failureStage: null,
    failureReason: null,
    artifacts: null,
  };

  try {
    const firstNormalization = await normalizeSession(page, args, observability);
    ledger.normalization = firstNormalization.normalization;

    let prepared = firstNormalization;
    for (let index = 0; index < ROUTE_PLAN.length; index += 1) {
      const [routeName, expectedPath] = ROUTE_PLAN[index];
      const result = await smokeRoute(page, args, observability, routeName, expectedPath, prepared);
      ledger.routes.push(result);
      if (!result.pass && !ledger.failureReason) {
        ledger.failureReason = `${routeName}: ${result.failureReason}`;
        ledger.failureRoute = routeName;
        ledger.failureStage = 'route verdict';
        await captureCheckpoint(page, observability, 'failure').catch(() => {});
        break;
      }

      if (index < ROUTE_PLAN.length - 1) {
        prepared = {
          frame: await restoreRootReview(page, args, observability),
          normalization: firstNormalization.normalization,
        };
        continue;
      }

      prepared = null;
    }

    ledger.status = ledger.routes.every((route) => route.pass) ? 'pass' : 'fail';
    ledger.classification = ledger.status === 'fail'
      ? classifyFailure(ledger.failureReason, ledger.routes)
      : null;
    ledger.failurePhase = ledger.status === 'fail'
      ? classifyFailurePhase(ledger.failureReason, ledger.routes, ledger.failureStage)
      : null;
    await writeArtifacts(args, ledger, observability);

    if (ledger.status !== 'pass') {
      process.exitCode = 1;
    }
  } catch (error) {
    ledger.status = 'fail';
    ledger.normalization = error?.normalization ?? ledger.normalization;
    ledger.failureReason = error instanceof Error ? error.message : String(error);
    ledger.failureRoute = error?.routeName ?? ledger.failureRoute;
    ledger.failureStage = error?.routeStage ?? ledger.failureStage;
    ledger.classification = classifyFailure(ledger.failureReason, ledger.routes);
    ledger.failurePhase = classifyFailurePhase(ledger.failureReason, ledger.routes, ledger.failureStage);
    if (!error?.failureCheckpointRecorded) {
      await captureCheckpoint(page, observability, 'failure').catch(() => {});
    }
    await writeArtifacts(args, ledger, observability);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

await main();
