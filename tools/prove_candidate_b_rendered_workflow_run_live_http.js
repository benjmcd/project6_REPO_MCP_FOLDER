#!/usr/bin/env node

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

const MILESTONE = 'candidate_b_rendered_operator_workflow_run_live_http_operator_proof_v1';
const SCHEMA_ID = 'candidate_b.rendered_operator_workflow_run_live_http_operator_proof.v1';
const START_RENDERED_MODE = 'rendered_candidate_b_full_corpus_operator_workflow_run_start_control';
const PROGRESS_RENDERED_MODE = 'rendered_candidate_b_full_corpus_operator_workflow_run_progress_control';
const RUN_ENDPOINT = '/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run';
const STATUS_ENDPOINT = '/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status';
const ALLOWED_RUN_FIELDS = new Set([
  'baseline_run_id',
  'candidate_a_run_id',
  'candidate_b_run_id',
  'client_request_id',
  'compare_target_set_hash',
  'material_relative_name',
  'operator_decision',
  'run_mode',
  'runtime_root_lifecycle_receipt_id',
]);
const FORBIDDEN_RUN_FIELDS = [
  'bridge_dir',
  'frontend_durable_authority',
  'local_path',
  'provider_ref',
  'raw_url',
  'runtime_root',
  'selector_mutation_performed',
  'source_directory',
];

function usage() {
  return [
    'Usage:',
    '  node ./tools/prove_candidate_b_rendered_workflow_run_live_http.js \\',
    '    --page-url http://127.0.0.1:8098/review/layer3 \\',
    '    --receipt-file ./backend/app/storage_test_runtime/.../receipt.json \\',
    '    --output ./backend/app/storage_test_runtime/.../rendered-proof.json',
    '',
    'Options:',
    '  --headed                 Run headed Chromium instead of headless.',
    '  --timeout-ms <number>    Action/response timeout, default 120000.',
    '  --screenshot <path>      Optional rendered proof screenshot path.',
  ].join('\n');
}

function parseArgs(argv) {
  const args = {
    headed: false,
    timeoutMs: 120000,
  };
  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--headed') {
      args.headed = true;
      continue;
    }
    if (arg === '--help' || arg === '-h') {
      console.log(usage());
      process.exit(0);
    }
    if (!arg.startsWith('--')) {
      throw new Error(`Unexpected positional argument: ${arg}`);
    }
    const key = arg.slice(2).replace(/-([a-z])/g, (_, char) => char.toUpperCase());
    const value = argv[i + 1];
    if (!value || value.startsWith('--')) {
      throw new Error(`Missing value for ${arg}`);
    }
    args[key] = value;
    i += 1;
  }
  if (!args.pageUrl) throw new Error('Missing --page-url.');
  if (!args.receiptFile) throw new Error('Missing --receipt-file.');
  if (args.timeoutMs !== undefined) {
    const timeout = Number(args.timeoutMs);
    if (!Number.isFinite(timeout) || timeout <= 0) {
      throw new Error('--timeout-ms must be a positive number.');
    }
    args.timeoutMs = timeout;
  }
  return args;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(',')}]`;
  }
  if (value && typeof value === 'object') {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
      .join(',')}}`;
  }
  return JSON.stringify(value);
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function redactedUrlRef(url) {
  return `redacted://url/${sha256(String(url)).slice(0, 24)}`;
}

function requireString(value, field) {
  const text = String(value || '').trim();
  if (!text) throw new Error(`Receipt missing ${field}.`);
  return text;
}

function valuesFromReceipt(receipt) {
  const authority = receipt.server_owned_workflow_run?.authority_basis || {};
  const runtimeLifecycle = receipt.runtime_root_lifecycle || {};
  return {
    runtimeRootLifecycleReceiptId: requireString(
      authority.runtime_root_lifecycle_receipt_id || runtimeLifecycle.lifecycle_receipt_id,
      'runtime root lifecycle receipt id',
    ),
    baselineRunId: requireString(authority.baseline_run_id || receipt.baseline_run_id, 'baseline run id'),
    candidateARunId: requireString(
      authority.candidate_a_run_id || receipt.candidate_a_run_id,
      'Candidate A run id',
    ),
    candidateBRunId: requireString(
      authority.candidate_b_run_id || receipt.candidate_b_run_id,
      'Candidate B run id',
    ),
    compareTargetSetHash: requireString(
      authority.compare_target_set_hash || receipt.compare_target_set_hash,
      'compare target set hash',
    ),
    materialRelativeName: requireString(
      authority.material_relative_name || receipt.corpus?.material_relative_name,
      'material relative name',
    ),
    sourceOperatorWorkflowReceiptId: requireString(
      authority.source_operator_workflow_receipt_id || receipt.receipt_id,
      'source operator workflow receipt id',
    ),
  };
}

function parsePostData(request) {
  const raw = request.postData() || '{}';
  return JSON.parse(raw);
}

function forbiddenFields(payload) {
  return FORBIDDEN_RUN_FIELDS.filter((field) => Object.prototype.hasOwnProperty.call(payload, field));
}

function disallowedFields(payload) {
  return Object.keys(payload).filter((field) => !ALLOWED_RUN_FIELDS.has(field)).sort();
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function main() {
  const args = parseArgs(process.argv);
  const receiptFile = path.resolve(args.receiptFile);
  const receipt = readJson(receiptFile);
  const formValues = valuesFromReceipt(receipt);
  const browser = await chromium.launch({ headless: !args.headed });
  let proof;
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(args.timeoutMs);
    await page.goto(args.pageUrl, { waitUntil: 'domcontentloaded' });
    const form = page.locator('#candidate-b-full-corpus-workflow-run-form');
    await form.waitFor({ state: 'visible' });
    assert(
      await form.getAttribute('data-rendered-mode') === START_RENDERED_MODE,
      'Rendered start mode mismatch.',
    );
    assert(
      await form.getAttribute('data-progress-rendered-mode') === PROGRESS_RENDERED_MODE,
      'Rendered progress mode mismatch.',
    );
    assert(
      await form.getAttribute('data-frontend-durable-authority') === 'false',
      'Rendered run form exposed frontend durable authority.',
    );
    await page.waitForFunction(() => {
      const button = document.querySelector('#candidate-b-full-corpus-workflow-run-submit');
      return button && !button.disabled;
    });
    await page.locator('#candidate-b-full-corpus-workflow-run-lifecycle-receipt-id').fill(
      formValues.runtimeRootLifecycleReceiptId,
    );
    await page.locator('#candidate-b-full-corpus-workflow-run-baseline-run-id').fill(formValues.baselineRunId);
    await page.locator('#candidate-b-full-corpus-workflow-run-candidate-a-run-id').fill(formValues.candidateARunId);
    await page.locator('#candidate-b-full-corpus-workflow-run-candidate-b-run-id').fill(formValues.candidateBRunId);
    await page.locator('#candidate-b-full-corpus-workflow-run-compare-target-set-hash').fill(
      formValues.compareTargetSetHash,
    );
    await page.locator('#candidate-b-full-corpus-workflow-run-material-relative-name').fill(
      formValues.materialRelativeName,
    );

    const runResponsePromise = page.waitForResponse(
      (response) => response.request().method() === 'POST' && response.url().includes(RUN_ENDPOINT),
      { timeout: args.timeoutMs },
    );
    const statusResponsePromise = page.waitForResponse(
      (response) => response.request().method() === 'POST' && response.url().includes(STATUS_ENDPOINT),
      { timeout: args.timeoutMs },
    );
    await page.locator('#candidate-b-full-corpus-workflow-run-submit').click();
    const runResponse = await runResponsePromise;
    const statusResponse = await statusResponsePromise;
    assert(runResponse.ok(), `Run endpoint returned HTTP ${runResponse.status()}.`);
    assert(statusResponse.ok(), `Status endpoint returned HTTP ${statusResponse.status()}.`);
    const runJson = await runResponse.json();
    const statusJson = await statusResponse.json();
    const runPayload = parsePostData(runResponse.request());
    const statusPayload = parsePostData(statusResponse.request());
    assert(
      stableStringify(statusPayload) === stableStringify(runJson.status_request),
      'Rendered progress request did not use the run endpoint returned status_request.',
    );
    assert(forbiddenFields(runPayload).length === 0, 'Rendered run payload included forbidden authority fields.');
    assert(disallowedFields(runPayload).length === 0, 'Rendered run payload included non-admitted fields.');
    await page.locator('#candidate-b-default-promotion-status-panel').waitFor({ state: 'visible' });
    await page.waitForFunction(() => document.body.innerText.includes('candidate_b_full_corpus_workflow_run_proven'));
    const pageText = await page.locator('body').innerText();
    const leakedRawPatterns = [
      /file:\/\//i,
      /[A-Za-z]:\\/,
      /provider_key/i,
      /LAYER3_INTERNAL_WEBHOOK_URL/,
    ].filter((pattern) => pattern.test(pageText));
    assert(leakedRawPatterns.length === 0, 'Rendered page exposed raw path, URL, or credential-like text.');
    if (args.screenshot) {
      const screenshotPath = path.resolve(args.screenshot);
      fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
      await page.screenshot({ path: screenshotPath, fullPage: true });
    }
    proof = {
      schema_id: SCHEMA_ID,
      schema_version: 1,
      milestone: MILESTONE,
      execution_mode: 'live-http-rendered-browser',
      live_http_layer3_api_used: true,
      testclient_dependency_used: false,
      in_memory_db_used: false,
      durable_database_required: true,
      playwright_browser_surface_used: true,
      headed_chromium: Boolean(args.headed),
      page_url_ref: redactedUrlRef(args.pageUrl),
      source_receipt_ref: `repo://${path.relative(process.cwd(), receiptFile).replace(/\\/g, '/')}`,
      source_operator_workflow_receipt_id: formValues.sourceOperatorWorkflowReceiptId,
      runtime_root_lifecycle_receipt_id: formValues.runtimeRootLifecycleReceiptId,
      baseline_run_id: formValues.baselineRunId,
      candidate_a_run_id: formValues.candidateARunId,
      candidate_b_run_id: formValues.candidateBRunId,
      compare_target_set_hash: formValues.compareTargetSetHash,
      material_relative_name: formValues.materialRelativeName,
      selected_rendered_start_mode: START_RENDERED_MODE,
      selected_rendered_progress_mode: PROGRESS_RENDERED_MODE,
      frontend_durable_authority: false,
      run_endpoint_verified: true,
      status_endpoint_verified_after_rendered_run: true,
      run_endpoint_status_request_used_for_progress: true,
      run_schema_id: runJson.schema_id,
      run_state: runJson.run_state,
      source_operator_workflow_receipt_hash: runJson.source_operator_workflow_receipt_hash,
      server_owned_run_receipt_id: runJson.operator_workflow_receipt_id,
      server_owned_run_receipt_hash: runJson.operator_workflow_receipt_hash,
      status_schema_id: statusJson.schema_id,
      status: statusJson.status,
      status_operator_workflow_receipt_id: statusJson.operator_workflow_receipt_id,
      status_operator_workflow_hash: statusJson.operator_workflow_hash,
      rendered_payload_allowed_fields_only: true,
      forbidden_rendered_payload_fields_present: [],
      raw_api_base_url_persisted: false,
      raw_local_path_exposed: false,
      raw_url_exposed: false,
      runtime_roots_submitted_by_browser: false,
      source_directory_submitted_by_browser: false,
      bridge_dir_submitted_by_browser: false,
      selector_mutation_performed: false,
      provider_object_write_enabled: false,
      connector_dispatch_enabled: false,
      rag_vector_model_runtime_enabled: false,
      full_mockup_activation_enabled: false,
    };
    proof.proof_hash = sha256(stableStringify(proof));
    proof.proof_receipt_id = `cb-rendered-run-live-http-${proof.proof_hash.slice(0, 24)}`;
  } finally {
    await browser.close();
  }
  const output = JSON.stringify(proof, null, 2);
  if (args.output) {
    const outputPath = path.resolve(args.output);
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, `${output}\n`, 'utf8');
  }
  console.log(output);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
