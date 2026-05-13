import { test, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import {
  expectJson,
  requestId,
  expectOnlyPayloadKeys,
  formPostPayload,
  expectStepAvailable,
  expectStepUnavailable,
  prepareExecutedLayer3Session,
  attachSessionToWorkbench,
} from './layer3-helpers.js';

const MOCKUP_FRAME_MANIFEST_PATH = path.resolve('next_milestone_plans/layer3-mockups/frames/manifest.json');
const MOCKUP_VISUAL_DIFF_LIMITS = {
  compareWidth: 360,
  compareHeight: 220,
  normalizedMeanDeltaMax: 0.19,
  highDeltaRatioMax: 0.305,
};

function pngDimensions(buffer) {
  return {
    width: buffer.readUInt32BE(16),
    height: buffer.readUInt32BE(20),
  };
}

function loadMockupFrameManifest() {
  const manifest = JSON.parse(readFileSync(MOCKUP_FRAME_MANIFEST_PATH, 'utf8').replace(/^\uFEFF/, ''));
  expect(manifest.schema_id).toBe('layer3.mockup_visual_acceptance_frames.v1');
  expect(manifest.selected_theme_target).toBe('layer3_mockup_workbench_theme');
  expect(manifest.selected_first_slice).toBe('mockup_theme_shell_and_fixture_projection');
  expect(manifest.frames).toHaveLength(8);
  return manifest.frames.map((frame) => {
    const buffer = readFileSync(path.resolve(frame.repo_path));
    expect(createHash('sha256').update(buffer).digest('hex')).toBe(frame.sha256);
    expect(buffer.length).toBe(frame.size_bytes);
    expect(frame.rendered_projection?.acceptance_mode).toBe('static_theme_region_projection');
    expect(frame.rendered_projection?.selector).toMatch(/^#/);
    expect(frame.rendered_projection?.projection_id).toBeTruthy();
    expect(frame.rendered_projection?.screenshot_attachment).toBeTruthy();
    return { ...frame, dimensions: pngDimensions(buffer) };
  });
}

function frameDataUrl(frame) {
  const buffer = readFileSync(path.resolve(frame.repo_path));
  return `data:image/png;base64,${buffer.toString('base64')}`;
}

async function compareMockupFrameImages(page, referenceDataUrl, actualDataUrl) {
  return page.evaluate(async ({ referenceDataUrl, actualDataUrl, limits }) => {
    const loadImage = (src) => new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error(`Unable to decode visual-diff image: ${src.slice(0, 32)}`));
      image.src = src;
    });
    const [reference, actual] = await Promise.all([
      loadImage(referenceDataUrl),
      loadImage(actualDataUrl),
    ]);
    const canvas = document.createElement('canvas');
    canvas.width = limits.compareWidth;
    canvas.height = limits.compareHeight;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    context.drawImage(reference, 0, 0, limits.compareWidth, limits.compareHeight);
    const referencePixels = context.getImageData(0, 0, limits.compareWidth, limits.compareHeight).data;
    context.clearRect(0, 0, limits.compareWidth, limits.compareHeight);
    context.drawImage(actual, 0, 0, limits.compareWidth, limits.compareHeight);
    const actualPixels = context.getImageData(0, 0, limits.compareWidth, limits.compareHeight).data;
    let totalDelta = 0;
    let highDeltaPixels = 0;
    const pixelCount = limits.compareWidth * limits.compareHeight;
    for (let index = 0; index < referencePixels.length; index += 4) {
      const redDelta = Math.abs(referencePixels[index] - actualPixels[index]);
      const greenDelta = Math.abs(referencePixels[index + 1] - actualPixels[index + 1]);
      const blueDelta = Math.abs(referencePixels[index + 2] - actualPixels[index + 2]);
      const normalizedPixelDelta = (redDelta + greenDelta + blueDelta) / (255 * 3);
      totalDelta += normalizedPixelDelta;
      if (normalizedPixelDelta > 0.32) highDeltaPixels += 1;
    }
    return {
      referenceWidth: reference.naturalWidth,
      referenceHeight: reference.naturalHeight,
      actualWidth: actual.naturalWidth,
      actualHeight: actual.naturalHeight,
      compareWidth: limits.compareWidth,
      compareHeight: limits.compareHeight,
      normalizedMeanDelta: Number((totalDelta / pixelCount).toFixed(6)),
      highDeltaRatio: Number((highDeltaPixels / pixelCount).toFixed(6)),
    };
  }, { referenceDataUrl, actualDataUrl, limits: MOCKUP_VISUAL_DIFF_LIMITS });
}

async function seedRawMixedBridgeSetup(request) {
  const setup = await expectJson(await request.post('/__test/layer3/seed-raw-mixed'));
  expect(setup.schema_id).toBe('project6.review_browser_raw_mixed_seed_setup.v1');

  const seed = await expectJson(await request.post('/api/v1/layer3/source/mixed-corpus/seed', {
    data: setup.seed_request,
  }));
  expect(seed.schema_id).toBe('layer3.raw_mixed_corpus_seed_result.v1');
  expect(seed.seed_mode).toBe('raw_mixed_corpus_bridge_seed_only');
  expect(seed.source_seed_state).toBe('seeded');
  expect(seed.source_classes).toEqual(['dataset_version', 'aps_content_document']);
  expect(seed.layer3_flow_started).toBe(false);
  expect(seed.next_allowed_actions).toEqual(['run_layer3_preflight_with_seeded_source_ids']);
  expect(seed.dataset_version_ids).toHaveLength(2);
  expect(seed.aps_content_document_ids).toHaveLength(1);
  expect(seed).not.toHaveProperty('local_upload');
  expect(seed).not.toHaveProperty('local_directory');
  expect(seed).not.toHaveProperty('rag_plan');
  expect(seed).not.toHaveProperty('provider_url');
  expect(seed).not.toHaveProperty('public_url');
  expect(seed).not.toHaveProperty('connector_run_id');
  return seed;
}

async function materializeRawMixedSetup(request) {
  const setup = await expectJson(await request.post('/__test/layer3/materialize-raw-mixed'));
  expect(setup.schema_id).toBe('project6.review_browser_raw_mixed_materialization_setup.v1');

  const materialization = await expectJson(await request.post('/api/v1/layer3/source/mixed-corpus/materialize', {
    data: setup.materialize_request,
  }));
  expect(materialization.schema_id).toBe('layer3.raw_mixed_corpus_materialize_result.v1');
  expect(materialization.materialization_mode).toBe('raw_mixed_existing_source_materialization_entry');
  expect(materialization.source_materialization_state).toBe('materialized');
  expect(materialization.source_classes).toEqual(['dataset_version', 'aps_content_document']);
  expect(materialization.layer3_flow_started).toBe(false);
  expect(materialization.files_written).toEqual([]);
  expect(materialization.next_allowed_actions).toEqual(['run_layer3_preflight_with_materialized_source_ids']);
  expect(materialization.dataset_version_ids).toHaveLength(2);
  expect(materialization.aps_content_document_ids).toHaveLength(1);
  expect(materialization.database_rows_written).toEqual({
    datasets: 2,
    dataset_versions: 2,
    variables: 4,
    dataset_rows: 48,
    variable_profiles: 2,
    dataset_source_provenance: 2,
    connector_runs: 1,
    connector_run_targets: 1,
    aps_content_documents: 1,
    aps_content_chunks: 2,
    aps_content_linkages: 1,
  });
  expect(materialization).not.toHaveProperty('local_upload');
  expect(materialization).not.toHaveProperty('local_directory');
  expect(materialization).not.toHaveProperty('rag_plan');
  expect(materialization).not.toHaveProperty('provider_url');
  expect(materialization).not.toHaveProperty('public_url');
  expect(materialization).not.toHaveProperty('connector_dispatch');
  return materialization;
}

async function expectNoDeferredRawMixedControls(page) {
  const sourceClassValues = await page.locator('input[name="source-class"]').evaluateAll((inputs) => (
    inputs.map((input) => input.value).sort()
  ));
  expect(sourceClassValues).toEqual(['aps_content_document', 'dataset_version']);
  await expect(page.locator('input[type="file"]')).toHaveCount(0);
  await expect(page.locator([
    'input[name*="upload"]',
    'input[name*="directory"]',
    'input[name*="provider"]',
    'input[name*="public"]',
    'input[name*="rag"]',
    'input[name*="vector"]',
    'textarea[name*="upload"]',
    'textarea[name*="directory"]',
    'textarea[name*="provider"]',
    'textarea[name*="public"]',
    'textarea[name*="rag"]',
    'textarea[name*="vector"]',
  ].join(','))).toHaveCount(0);
  await expect(page.getByRole('button', {
    name: /upload|ingest|local directory|web connector|rag|vector|provider url|public url|connector dispatch|destination|mockup|auth/i,
  })).toHaveCount(0);
}

async function selectSeededSources(page, seed) {
  for (const datasetVersionId of seed.dataset_version_ids) {
    const input = page.locator(`input[name="dataset-version-candidate"][value="${datasetVersionId}"]`);
    await expect(input).toBeVisible();
    await input.check();
    await expect(input).toBeChecked();
  }
  for (const contentId of seed.aps_content_document_ids) {
    const input = page.locator(`input[name="aps-content-document-candidate"][value="${contentId}"]`);
    await expect(input).toBeVisible();
    await input.check();
    await expect(input).toBeChecked();
  }
}

function expectMaterialPreviewContainsSeededSources(material, seed) {
  const candidates = material.material_candidates || [];
  expect(candidates).toHaveLength(3);
  const datasetVersionIds = candidates
    .filter((candidate) => candidate.source_class === 'dataset_version')
    .map((candidate) => candidate.source_identity?.dataset_version_id)
    .sort();
  const apsContentIds = candidates
    .filter((candidate) => candidate.source_class === 'aps_content_document')
    .map((candidate) => candidate.source_identity?.content_id)
    .sort();
  expect(datasetVersionIds).toEqual([...seed.dataset_version_ids].sort());
  expect(apsContentIds).toEqual([...seed.aps_content_document_ids].sort());
}

const DEFERRED_RAW_MIXED_PAYLOAD_FIELDS = [
  'artifact_manifest',
  'auth_context',
  'connector_dispatch',
  'connector_run_id',
  'destination',
  'destination_id',
  'directory',
  'local_directory',
  'local_upload',
  'llm_plan',
  'model_name',
  'mockup',
  'package_payload',
  'provider_url',
  'public_url',
  'rag_plan',
  'rebuild_package',
  'source_adapter_registry',
  'upload',
  'vector_query',
  'web_connector',
];

const EXPECTED_PACKAGE_REVIEW_KINDS = ['canonical_internal', 'user_facing', 'review_facing'];
const LIVE_LAYER3_THEMES = ['system', 'light', 'dark', 'workbench'];

function expectNoDeferredRawMixedPayloadFields(payload) {
  for (const field of DEFERRED_RAW_MIXED_PAYLOAD_FIELDS) {
    expect(payload).not.toHaveProperty(field);
  }
}

function valuesByPackageKind(keyedValues) {
  return EXPECTED_PACKAGE_REVIEW_KINDS.map((packageKind) => keyedValues[packageKind]);
}

function trackLayer3ApiRequests(page) {
  const requests = [];
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith('/api/v1/layer3/')) {
      requests.push({ method: request.method(), path: url.pathname });
    }
  });
  return requests;
}

function expectNoRequestsToLayer3Paths(requests, pathFragments) {
  for (const fragment of pathFragments) {
    expect(requests.filter((request) => request.path.includes(fragment))).toEqual([]);
  }
}

async function expectLiveThemeParityCheckpoint(page, checkpointLabel, visibleSurfaceSelector) {
  expect(checkpointLabel).toBeTruthy();
  expect(visibleSurfaceSelector).toBeTruthy();
  const entryTheme = await page.locator('#theme-selector').inputValue();
  for (const theme of LIVE_LAYER3_THEMES) {
    await page.locator('#theme-selector').selectOption(theme);
    await expect(page.locator('#theme-selector')).toHaveValue(theme);
    await expect(page.locator('html')).toHaveAttribute('data-theme-preference', theme);
    await expect(page.locator(visibleSurfaceSelector)).toBeVisible();
    await expect(page.locator('#source-fieldset')).toHaveCount(1);
    await expect(page.locator('#material-ledger-body')).toHaveCount(1);
    await expect(page.locator('#gate-b-band')).toHaveCount(1);
    await expect(page.locator('#gate-c-panel')).toHaveCount(1);
    await expect(page.locator('#external-export-download-band')).toHaveCount(1);
    await expect(page.locator('#external-export-download-signed-reference-panel')).toHaveCount(1);
    await expect(page.locator('#provider-private-signed-url-panel')).toHaveCount(1);
    await expect(page.locator('#provider-private-signed-url-use')).toHaveCount(0);
    await expect(page.locator('#connector-destination-panel')).toHaveCount(0);
    await expect(page.locator('#package-mutation-panel')).toHaveCount(0);
  }
  await page.locator('#theme-selector').selectOption(entryTheme);
  await expect(page.locator('#theme-selector')).toHaveValue(entryTheme);
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', entryTheme);
}

async function openRawMixedSeededWorkbench(page, request) {
  const seed = await seedRawMixedBridgeSetup(request);
  const datasetCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  const apsCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/aps-content-document-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  const datasetCandidates = await expectJson(await datasetCandidatesResponsePromise);
  const apsCandidates = await expectJson(await apsCandidatesResponsePromise);

  expect(datasetCandidates.dataset_version_candidates.map((candidate) => candidate.dataset_version_id)).toEqual(
    expect.arrayContaining(seed.dataset_version_ids),
  );
  expect(apsCandidates.aps_content_document_candidates.map((candidate) => candidate.content_id)).toEqual(
    expect.arrayContaining(seed.aps_content_document_ids),
  );
  await expectNoDeferredRawMixedControls(page);
  await selectSeededSources(page, seed);
  return seed;
}

async function openRawMixedMaterializedWorkbench(page, request) {
  const materialization = await materializeRawMixedSetup(request);
  const datasetCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  const apsCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/aps-content-document-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  const datasetCandidates = await expectJson(await datasetCandidatesResponsePromise);
  const apsCandidates = await expectJson(await apsCandidatesResponsePromise);

  expect(datasetCandidates.dataset_version_candidates.map((candidate) => candidate.dataset_version_id)).toEqual(
    expect.arrayContaining(materialization.dataset_version_ids),
  );
  expect(apsCandidates.aps_content_document_candidates.map((candidate) => candidate.content_id)).toEqual(
    expect.arrayContaining(materialization.aps_content_document_ids),
  );
  await expectNoDeferredRawMixedControls(page);
  await selectSeededSources(page, materialization);
  return materialization;
}

async function materializeRawMixedThroughRenderedControls(page, request) {
  const setup = await expectJson(await request.post('/__test/layer3/materialize-raw-mixed'));
  expect(setup.schema_id).toBe('project6.review_browser_raw_mixed_materialization_setup.v1');
  const materializeRequest = setup.materialize_request;
  const materializeRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/source/mixed-corpus/materialize')
    && apiRequest.method() === 'POST'
  ));
  const materializeResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/source/mixed-corpus/materialize')
    && response.request().method() === 'POST'
  ));
  const datasetCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  const apsCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/aps-content-document-candidates')
  ));

  await page.locator('#raw-mixed-corpus-batch-id').fill(materializeRequest.corpus_batch_id);
  await page.locator('#raw-mixed-manifest-ref').fill(materializeRequest.artifact_manifest_ref);
  await page.locator('#raw-mixed-manifest-hash').fill(materializeRequest.artifact_manifest_hash);
  await page.locator('#raw-mixed-operator-confirmation').check();
  await expect(page.locator('#raw-mixed-materialize')).toBeEnabled();
  await page.locator('#raw-mixed-materialize').click();

  const requestPayload = (await materializeRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(requestPayload, [
    'artifact_manifest_hash',
    'artifact_manifest_ref',
    'client_request_id',
    'corpus_batch_id',
    'materialization_mode',
    'operator_confirmation',
    'requested_source_classes',
    'schema_id',
    'schema_version',
  ]);
  expect(requestPayload).toMatchObject({
    artifact_manifest_hash: materializeRequest.artifact_manifest_hash,
    artifact_manifest_ref: materializeRequest.artifact_manifest_ref,
    corpus_batch_id: materializeRequest.corpus_batch_id,
    materialization_mode: 'raw_mixed_existing_source_materialization_entry',
    operator_confirmation: true,
    requested_source_classes: ['dataset_version', 'aps_content_document'],
    schema_id: 'layer3.raw_mixed_corpus_materialize_request.v1',
    schema_version: 1,
  });
  for (const forbidden of [
    'local_upload',
    'local_directory',
    'web_connector',
    'rag_plan',
    'provider_url',
    'public_url',
    'connector_dispatch',
    'destination_id',
    'package_mutation',
    'auth_override',
  ]) {
    expect(requestPayload).not.toHaveProperty(forbidden);
  }

  const materialization = await expectJson(await materializeResponsePromise);
  const datasetCandidates = await expectJson(await datasetCandidatesResponsePromise);
  const apsCandidates = await expectJson(await apsCandidatesResponsePromise);
  expect(materialization.schema_id).toBe('layer3.raw_mixed_corpus_materialize_result.v1');
  expect(materialization.layer3_flow_started).toBe(false);
  expect(materialization.files_written).toEqual([]);
  expect(datasetCandidates.dataset_version_candidates.map((candidate) => candidate.dataset_version_id)).toEqual(
    expect.arrayContaining(materialization.dataset_version_ids),
  );
  expect(apsCandidates.aps_content_document_candidates.map((candidate) => candidate.content_id)).toEqual(
    expect.arrayContaining(materialization.aps_content_document_ids),
  );
  await expect(page.locator('#raw-mixed-materialization-state')).toHaveText('Materialized');
  await expect(page.locator('#raw-mixed-materialization-status')).toContainText('selected after candidate refresh');
  await expect(page.locator('#dataset-version-ids')).toHaveValue(materialization.dataset_version_ids.join('\n'));
  await expect(page.locator('#aps-content-document-ids')).toHaveValue(materialization.aps_content_document_ids.join('\n'));
  await expectNoDeferredRawMixedControls(page);
  return materialization;
}

async function runRawMixedRenderedMaterialPreview(page, seed) {
  const preflightResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/preflight')
  ));
  const sourceResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/source-preview')
  ));
  const materialResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/material-preview')
  ));
  await page.locator('#layer3-intent').fill('Drive raw mixed source IDs through rendered Gate C and plan approval.');
  await page.locator('#run-preflight').click();
  const preflight = await expectJson(await preflightResponsePromise);
  const source = await expectJson(await sourceResponsePromise);
  const material = await expectJson(await materialResponsePromise);

  expect(preflight.preflight_id).toBeTruthy();
  expect(source.source_candidates.map((candidate) => candidate.source_class).sort()).toEqual([
    'aps_content_document',
    'dataset_version',
  ]);
  expectMaterialPreviewContainsSeededSources(material, seed);
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]')).toHaveCount(3);
  await expectNoDeferredRawMixedControls(page);
  return { preflight, source, material };
}

async function submitRenderedGateB(page, material) {
  const gateBRequestPromise = page.waitForRequest((gateBRequest) => (
    gateBRequest.url().includes('/api/v1/layer3/gate-b/decision') && gateBRequest.method() === 'POST'
  ));
  const gateBResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/gate-b/decision')
  ));
  await page.locator('#gate-b-submit').click();
  const gateBPayload = (await gateBRequestPromise).postDataJSON();
  expect(gateBPayload.material_preview_hash).toBe(material.material_preview_hash);
  expect(gateBPayload.candidate_decisions).toHaveLength(3);
  const submittedDatasetVersionIds = gateBPayload.candidate_decisions
    .filter((decision) => decision.decision_basis?.source_identity?.source_class === 'dataset_version')
    .map((decision) => decision.decision_basis.source_identity.dataset_version_id)
    .sort();
  const materialDatasetVersionIds = material.material_candidates
    .filter((candidate) => candidate.source_class === 'dataset_version')
    .map((candidate) => candidate.source_identity.dataset_version_id)
    .sort();
  expect(submittedDatasetVersionIds).toEqual(materialDatasetVersionIds);
  for (const decision of gateBPayload.candidate_decisions) {
    expect(decision.decision_basis.source_identity).toBeTruthy();
    expect(decision.decision_basis.source_provenance).toBeTruthy();
    expect(decision.decision_basis.payload).toBeTruthy();
    expect(decision.decision_basis.load_summary).toBeTruthy();
  }
  expectNoDeferredRawMixedPayloadFields(gateBPayload);
  const gateB = await expectJson(await gateBResponsePromise);
  expect(gateB.status).toBe('ok');
  expect(gateB.approved_candidate_ids).toHaveLength(3);
  await expect(page.locator('#gate-c-preview')).toBeEnabled();
  await expect(page.locator('#gate-c-commit')).toBeEnabled();
  await expect(page.locator('#plan-preview')).toBeDisabled();
  return gateB;
}

async function previewRenderedGateC(page, sessionId) {
  const gateCRequestPromise = page.waitForRequest((gateCRequest) => (
    gateCRequest.url().includes('/api/v1/layer3/gate-c/preview') && gateCRequest.method() === 'POST'
  ));
  const gateCResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/gate-c/preview')
  ));
  await page.locator('#gate-c-preview').click();
  const payload = (await gateCRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(payload, ['client_request_id', 'commit_typing', 'schema_id', 'session_id']);
  expect(payload.session_id).toBe(sessionId);
  expect(payload.commit_typing).toBe(false);
  expectNoDeferredRawMixedPayloadFields(payload);
  const gateC = await expectJson(await gateCResponsePromise);
  expect(gateC.schema_id).toBe('layer3.gate_c_preview_result.v1');
  expect(gateC.next_state).toBe('first_slice_complete');
  expect(gateC.typing_records.length).toBeGreaterThan(0);
  await expect(page.locator('#gate-c-panel')).toContainText('document_chunks');
  await expect(page.locator('#gate-c-panel')).toContainText('tabular_numeric');
  await expect(page.locator('#plan-preview')).toBeDisabled();
  return gateC;
}

async function commitRenderedGateC(page, sessionId) {
  const gateCRequestPromise = page.waitForRequest((gateCRequest) => (
    gateCRequest.url().includes('/api/v1/layer3/gate-c/preview') && gateCRequest.method() === 'POST'
  ));
  const gateCResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/gate-c/preview')
  ));
  await page.locator('#gate-c-commit').click();
  const payload = (await gateCRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(payload, ['client_request_id', 'commit_typing', 'schema_id', 'session_id']);
  expect(payload.session_id).toBe(sessionId);
  expect(payload.commit_typing).toBe(true);
  expectNoDeferredRawMixedPayloadFields(payload);
  const gateC = await expectJson(await gateCResponsePromise);
  expect(gateC.schema_id).toBe('layer3.gate_c_preview_result.v1');
  expect(gateC.next_state).toBe('plan_preview_ready');
  expect(gateC.authority_rail.typing_status).toBe('committed');
  await expect(page.locator('#gate-c-preview')).toBeDisabled();
  await expect(page.locator('#gate-c-commit')).toBeDisabled();
  await expect(page.locator('#plan-preview')).toBeEnabled();
  await expectStepAvailable(page, 'plan');
  return gateC;
}

async function previewRenderedPlan(page, sessionId, seed) {
  const planRequestPromise = page.waitForRequest((planRequest) => (
    planRequest.url().includes('/api/v1/layer3/plan/preview') && planRequest.method() === 'POST'
  ));
  const planResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/plan/preview')
  ));
  await page.locator('#plan-preview').click();
  const payload = (await planRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(payload, ['client_request_id', 'include_exclusions', 'preview_scope', 'schema_id', 'session_id']);
  expect(payload.session_id).toBe(sessionId);
  expect(payload.include_exclusions).toBe(true);
  expect(payload.preview_scope).toBe('owner_service_default');
  expectNoDeferredRawMixedPayloadFields(payload);
  const planPreview = await expectJson(await planResponsePromise);
  expect(planPreview.schema_id).toBe('layer3.plan_preview_result.v1');
  expect(planPreview.preview_only).toBe(true);
  expect(planPreview.plan_preview.approval_ready).toBe(true);
  expect(planPreview.plan_preview.admitted_sets).toHaveLength(1);
  expect(planPreview.plan_preview.excluded_sets).toHaveLength(1);
  expect(planPreview.plan_preview.excluded_sets[0].reason_code).toBe(
    'qualitative_aps_companion_provenance_not_pass_candidate',
  );
  expect(planPreview.plan_preview.planned_passes).toHaveLength(1);
  const plannedPass = planPreview.plan_preview.planned_passes[0];
  expect(plannedPass.pass_type).toBe('associated_cohort');
  expect(plannedPass.pass_scope).toBe('quantitative_associated_cohort_dataset_version');
  expect(plannedPass.selected_method_name).toBe('descriptive_summary');
  expect([...plannedPass.source_dataset_version_ids].sort()).toEqual([...seed.dataset_version_ids].sort());
  await expect(page.locator('#plan-panel')).toContainText('Planned Passes');
  await expect(page.locator('#plan-panel')).toContainText('associated_cohort');
  await expect(page.locator('#plan-approve')).toBeEnabled();
  return planPreview;
}

async function approveRenderedPlan(page, sessionId, planPreview) {
  const approvalRequestPromise = page.waitForRequest((approvalRequest) => (
    approvalRequest.url().includes('/api/v1/layer3/plan/approve') && approvalRequest.method() === 'POST'
  ));
  const approvalResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/plan/approve')
  ));
  await page.locator('#plan-approve').click();
  const payload = (await approvalRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(payload, [
    'approval_scope',
    'client_request_id',
    'operator_confirmation',
    'preview_hash',
    'preview_id',
    'schema_id',
    'session_id',
  ]);
  expect(payload.session_id).toBe(sessionId);
  expect(payload.preview_id).toBe(planPreview.preview_id);
  expect(payload.preview_hash).toBe(planPreview.preview_hash);
  expect(payload.operator_confirmation).toBe(true);
  expect(payload.approval_scope).toBe('owner_service_default');
  expectNoDeferredRawMixedPayloadFields(payload);
  const approval = await expectJson(await approvalResponsePromise);
  expect(approval.schema_id).toBe('layer3.plan_approval_result.v1');
  expect(approval.next_state).toBe('plan_approved');
  expect(approval.execution_started).toBe(false);
  expect(approval.approval_only).toBe(true);
  expect(approval.analysis_plan_id).toBeTruthy();
  await expect(page.locator('#plan-approve')).toBeDisabled();
  return approval;
}

async function assertRenderedPlanApprovalStopsBeforeExecution(page, sessionId, layer3ApiRequests) {
  await expect(page.locator('#plan-approve')).toBeDisabled();
  await expect(page.locator('#execution-selection-start-panel')).toContainText('execution_selection_ready');
  await expect(page.locator('#execution-select')).toBeEnabled();
  await expect(page.locator('#execution-start')).toBeDisabled();
  await expect(page.locator('#result-status-inspect')).toBeDisabled();
  await expect(page.locator('#result-review-submit')).toBeDisabled();
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();
  await expectStepUnavailable(page, 'execution');
  await expectStepUnavailable(page, 'results');
  await expectStepUnavailable(page, 'package');

  const sessionSummaryResponsePromise = page.waitForResponse((response) => (
    response.url().includes(`/api/v1/layer3/session/${sessionId}`)
  ));
  await page.locator('#result-review-refresh').click();
  const sessionSummary = await expectJson(await sessionSummaryResponsePromise);
  expect(sessionSummary.plan_approval.approved).toBe(true);
  expect(sessionSummary.plan_approval.pass_run_count).toBe(0);
  expect(sessionSummary.execution_selection.selected).toBe(false);
  expect(sessionSummary.analysis_execution_start.available).toBe(false);
  await expect(page.locator('#execution-select')).toBeEnabled();
  await expect(page.locator('#execution-start')).toBeDisabled();
  await expect(page.locator('#result-status-inspect')).toBeDisabled();
  await expect(page.locator('#result-review-submit')).toBeDisabled();
  await expectNoDeferredRawMixedControls(page);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, [
    '/execution/select',
    '/execution/start',
    '/execution/result/status',
    '/execution/result/review',
    '/package/review/',
    '/handoff/',
  ]);
}

async function reloadRecoveredExecutionSession(page, sessionId) {
  const sessionSummaryResponsePromise = page.waitForResponse((response) => (
    response.url().includes(`/api/v1/layer3/session/${sessionId}`)
  ));
  await page.reload({ waitUntil: 'domcontentloaded' });
  const sessionSummary = await expectJson(await sessionSummaryResponsePromise);
  expect(sessionSummary.session_id).toBe(sessionId);
  await page.locator('#execution-step-chip').click();
  await expect(page.locator('#execution-selection-start-panel')).toBeVisible();
  return sessionSummary;
}

async function selectAndStartRenderedExecution(page, sessionId, approval, planPreview) {
  await expect(page.locator('#execution-selection-start-panel')).toContainText('execution_selection_ready');
  await page.locator('#theme-selector').selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'dark');
  await expect(page.locator('#execution-selection-start-panel')).toBeVisible();
  const recoveredBeforeSelection = await reloadRecoveredExecutionSession(page, sessionId);
  expect(recoveredBeforeSelection.execution_selection.available).toBe(true);
  expect(recoveredBeforeSelection.execution_selection.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(recoveredBeforeSelection.execution_selection.source_preview_id).toBe(planPreview.preview_id);
  expect(recoveredBeforeSelection.execution_selection.source_preview_hash).toBe(planPreview.preview_hash);
  await expect(page.locator('#execution-selection-start-panel')).toContainText('execution_selection_ready');
  await expect(page.locator('#execution-select')).toBeEnabled();
  await expect(page.locator('#execution-start')).toBeDisabled();

  const selectionRequestPromise = page.waitForRequest((selectionRequest) => (
    selectionRequest.url().includes('/api/v1/layer3/execution/select') && selectionRequest.method() === 'POST'
  ));
  const selectionResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/execution/select')
  ));
  await page.locator('#execution-select').click();
  const selectionPayload = (await selectionRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(selectionPayload, [
    'analysis_plan_id',
    'client_request_id',
    'preview_hash',
    'preview_id',
    'session_id',
  ]);
  expect(selectionPayload.session_id).toBe(sessionId);
  expect(selectionPayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(selectionPayload.preview_id).toBe(planPreview.preview_id);
  expect(selectionPayload.preview_hash).toBe(planPreview.preview_hash);
  expectNoDeferredRawMixedPayloadFields(selectionPayload);

  const selection = await expectJson(await selectionResponsePromise);
  expect(selection.schema_id).toBe('layer3.execution_selection.v1');
  expect(selection.session_id).toBe(sessionId);
  expect(selection.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(selection.preview_identity.preview_id).toBe(planPreview.preview_id);
  expect(selection.preview_identity.preview_hash).toBe(planPreview.preview_hash);
  expect(selection.pass_run_ids).toHaveLength(1);
  expect(selection.pass_run_count).toBe(1);
  expect(selection.execution_started).toBe(false);
  expect(selection.analysis_run_ids).toEqual([]);
  await expect(page.locator('#execution-selection-start-panel')).toContainText('execution_selected');
  await expect(page.locator('#execution-select')).toBeDisabled();
  await expect(page.locator('#execution-start')).toBeEnabled();
  await expectStepAvailable(page, 'execution');
  await expect(page.locator('#result-status-inspect')).toBeDisabled();

  const recoveredAfterSelection = await reloadRecoveredExecutionSession(page, sessionId);
  expect(recoveredAfterSelection.execution_selection.selected).toBe(true);
  expect(recoveredAfterSelection.execution_selection.pass_run_ids).toEqual(selection.pass_run_ids);
  expect(recoveredAfterSelection.execution_selection.source_preview_id).toBe(planPreview.preview_id);
  await expect(page.locator('#execution-selection-start-panel')).toContainText('execution_selected');
  await expect(page.locator('#execution-select')).toBeDisabled();
  await expect(page.locator('#execution-start')).toBeEnabled();

  await page.locator('#theme-selector').selectOption('workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await page.locator('#execution-step-chip').click();
  await expect(page.locator('#execution-selection-start-panel')).toBeVisible();

  const startRequestPromise = page.waitForRequest((startRequest) => (
    startRequest.url().includes('/api/v1/layer3/execution/start') && startRequest.method() === 'POST'
  ));
  const startResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/execution/start')
  ));
  await page.locator('#execution-start').click();
  const startPayload = (await startRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(startPayload, [
    'analysis_plan_id',
    'client_request_id',
    'execution_mode',
    'pass_run_id',
    'preview_hash',
    'preview_id',
    'session_id',
  ]);
  expect(startPayload.session_id).toBe(sessionId);
  expect(startPayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(startPayload.pass_run_id).toBe(selection.pass_run_ids[0]);
  expect(startPayload.preview_id).toBe(planPreview.preview_id);
  expect(startPayload.preview_hash).toBe(planPreview.preview_hash);
  expect(startPayload.execution_mode).toBe('synchronous_single_pass');
  expectNoDeferredRawMixedPayloadFields(startPayload);

  const start = await expectJson(await startResponsePromise);
  expect(start.schema_id).toBe('layer3.analysis_execution_start.v1');
  expect(start.session_id).toBe(sessionId);
  expect(start.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(start.pass_run_id).toBe(selection.pass_run_ids[0]);
  expect(start.preview_identity.preview_id).toBe(planPreview.preview_id);
  expect(start.preview_identity.preview_hash).toBe(planPreview.preview_hash);
  expect(start.execution_started).toBe(true);
  await expect(page.locator('#execution-selection-start-panel')).toContainText('execution_started');
  await expect(page.locator('#execution-start')).toBeDisabled();
  await expect(page.locator('#result-status-inspect')).toBeEnabled();
  await expect(page.locator('#result-review-submit')).toBeDisabled();
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();

  return { selection, start };
}

async function inspectRenderedResultStatus(page, sessionId, approval, planPreview, execution) {
  await page.locator('#theme-selector').selectOption('light');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'light');
  await page.locator('#execution-step-chip').click();
  const statusRequestPromise = page.waitForRequest((statusRequest) => (
    statusRequest.url().includes('/api/v1/layer3/execution/result/status') && statusRequest.method() === 'POST'
  ));
  const statusResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/execution/result/status')
  ));
  await page.locator('#result-status-inspect').click();
  const statusPayload = (await statusRequestPromise).postDataJSON();
  const expectedStatusKeys = [
    'analysis_plan_id',
    'client_request_id',
    'operator_view_mode',
    'pass_run_id',
    'preview_hash',
    'preview_id',
    'session_id',
  ];
  if (statusPayload.analysis_run_id) {
    expectedStatusKeys.push('analysis_run_id');
    expect(statusPayload.analysis_run_id).toBe(execution.start.analysis_run_id);
  }
  expectOnlyPayloadKeys(statusPayload, expectedStatusKeys);
  expect(statusPayload.session_id).toBe(sessionId);
  expect(statusPayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(statusPayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(statusPayload.preview_id).toBe(planPreview.preview_id);
  expect(statusPayload.preview_hash).toBe(planPreview.preview_hash);
  expect(statusPayload.operator_view_mode).toBe('status_only');
  expectNoDeferredRawMixedPayloadFields(statusPayload);

  const status = await expectJson(await statusResponsePromise);
  expect(status.schema_id).toBe('layer3.execution_result_status.v1');
  expect(status.session_id).toBe(sessionId);
  expect(status.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(status.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(status.preview_identity.preview_id).toBe(planPreview.preview_id);
  expect(status.preview_identity.preview_hash).toBe(planPreview.preview_hash);
  expect(status.execution_started).toBe(true);
  expect(status.result_status_available).toBe(true);
  await expect(page.locator('#result-review-panel')).toContainText('cohort_result_review_ui_review_ready');
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();
  await expectNoDeferredRawMixedControls(page);
  return status;
}

async function submitRenderedResultReview(page, sessionId, approval, planPreview, execution, status, options = {}) {
  const {
    operatorDecision = 'changes_requested',
    reviewNotes = 'Raw mixed rendered result review requires a follow-up caveat before packaging.',
    packageReviewEnabled = false,
  } = options;
  await page.locator('#theme-selector').selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'dark');
  await expect(page.locator('#result-review-panel')).toBeVisible();
  await expect(page.locator('#result-review-panel')).toContainText('cohort_result_review_ui_review_ready');
  await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();

  await page.locator('#theme-selector').selectOption('workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await expect(page.locator('#result-review-panel')).toBeVisible();
  await expect(page.locator('#result-review-submit')).toBeEnabled();
  await page.locator('#result-review-decision').selectOption(operatorDecision);
  if (operatorDecision === 'approved') {
    await expect(page.locator('#result-review-submit')).toBeEnabled();
  } else {
    await expect(page.locator('#result-review-submit')).toBeDisabled();
  }
  await page.locator('#result-review-notes').fill(reviewNotes);
  await expect(page.locator('#result-review-submit')).toBeEnabled();

  const reviewRequestPromise = page.waitForRequest((reviewRequest) => (
    reviewRequest.url().includes('/api/v1/layer3/execution/result/review') && reviewRequest.method() === 'POST'
  ));
  const reviewResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/execution/result/review')
  ));
  await page.locator('#result-review-submit').click();
  const reviewPayload = (await reviewRequestPromise).postDataJSON();
  const expectedReviewKeys = [
    'analysis_plan_id',
    'client_request_id',
    'operator_decision',
    'pass_run_id',
    'preview_hash',
    'preview_id',
    'review_notes',
    'session_id',
  ];
  if (reviewPayload.analysis_run_id) {
    expectedReviewKeys.push('analysis_run_id');
    expect(reviewPayload.analysis_run_id).toBe(execution.start.analysis_run_id);
  }
  if (reviewPayload.reviewed_output_items) {
    expectedReviewKeys.push('reviewed_output_items');
    expect(reviewPayload.reviewed_output_items).toEqual(expect.any(Array));
    expect(reviewPayload.reviewed_output_items.length).toBeGreaterThan(0);
  }
  expectOnlyPayloadKeys(reviewPayload, expectedReviewKeys);
  expect(reviewPayload.session_id).toBe(sessionId);
  expect(reviewPayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(reviewPayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(reviewPayload.preview_id).toBe(planPreview.preview_id);
  expect(reviewPayload.preview_hash).toBe(planPreview.preview_hash);
  if (operatorDecision === 'changes_requested') {
    expect(reviewPayload.operator_decision).toBe('changes_requested');
  } else {
    expect(reviewPayload.operator_decision).toBe(operatorDecision);
  }
  expect(reviewPayload.review_notes).toBe(reviewNotes);
  expectNoDeferredRawMixedPayloadFields(reviewPayload);
  expect(reviewPayload).not.toHaveProperty('package');
  expect(reviewPayload).not.toHaveProperty('handoff');
  expect(reviewPayload).not.toHaveProperty('rerun');
  expect(reviewPayload).not.toHaveProperty('pass_run_ids');
  expect(reviewPayload).not.toHaveProperty('artifact_manifest');

  const review = await expectJson(await reviewResponsePromise);
  expect(review.schema_id).toBe('layer3.execution_result_review.v1');
  expect(review.status).toBe('recorded');
  expect(review.session_id).toBe(sessionId);
  expect(review.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(review.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(review.preview_identity.preview_id).toBe(planPreview.preview_id);
  expect(review.preview_identity.preview_hash).toBe(planPreview.preview_hash);
  expect(review.analysis_run_id).toBe(status.analysis_run_id);
  expect(review.operator_decision).toBe(operatorDecision);
  expect(review.result_status_available).toBe(true);
  expect(review.result_review_enabled).toBe(true);
  expect(review.package_review_enabled).toBe(false);
  expect(review.handoff_enabled).toBe(false);
  expect(review.downstream_unavailable).toEqual(
    expect.arrayContaining(operatorDecision === 'approved' ? ['handoff'] : ['package', 'handoff']),
  );
  expect(review.review_notes_recorded).toBe(true);
  expect(review.cohort_shape).toBeTruthy();

  await expect(page.locator('#result-review-panel')).toContainText('cohort_result_review_ui_recorded');
  await expect(page.locator('#result-review-panel')).toContainText(operatorDecision);
  await expect(page.locator('#result-review-submit')).toBeDisabled();
  if (packageReviewEnabled) {
    await expect(page.locator('#package-review-preview-inspect')).toBeEnabled();
  } else {
    await expect(page.locator('#package-review-preview-inspect')).toBeDisabled();
    await expect(page.locator('#package-construction-commit')).toBeDisabled();
    await expect(page.locator('#package-review-submit')).toBeDisabled();
  }
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();
  await expectNoDeferredRawMixedControls(page);
  return review;
}

async function inspectRenderedPackagePreview(page, sessionId, approval, planPreview, execution, review) {
  await page.locator('#theme-selector').selectOption('light');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'light');
  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_preview_available');
  await expect(page.locator('#package-review-preview-inspect')).toBeEnabled();
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeDisabled();

  const previewRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/package/review/preview') && apiRequest.method() === 'POST'
  ));
  const previewResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/package/review/preview')
  ));
  await page.locator('#package-review-preview-inspect').click();
  const previewPayload = (await previewRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(previewPayload, [
    'analysis_plan_id',
    'analysis_run_id',
    'client_request_id',
    'pass_run_id',
    'preview_hash',
    'preview_id',
    'result_review_record_ref',
    'session_id',
  ]);
  expect(previewPayload.session_id).toBe(sessionId);
  expect(previewPayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(previewPayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(previewPayload.preview_id).toBe(planPreview.preview_id);
  expect(previewPayload.preview_hash).toBe(planPreview.preview_hash);
  expect(previewPayload.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(previewPayload.result_review_record_ref).toBe(review.review_record_ref);
  expectNoDeferredRawMixedPayloadFields(previewPayload);
  for (const forbiddenKey of [
    'create_package',
    'handoff',
    'export',
    'rerun',
    'rewrite_output',
    'package_payload',
  ]) {
    expect(previewPayload).not.toHaveProperty(forbiddenKey);
  }

  const packagePreview = await expectJson(await previewResponsePromise);
  expect(packagePreview.schema_id).toBe('layer3.package_review_preview.v1');
  expect(packagePreview.status).toBe('available');
  expect(packagePreview.session_id).toBe(sessionId);
  expect(packagePreview.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(packagePreview.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(packagePreview.preview_identity.preview_id).toBe(planPreview.preview_id);
  expect(packagePreview.preview_identity.preview_hash).toBe(planPreview.preview_hash);
  expect(packagePreview.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(packagePreview.result_review_record_ref).toBe(review.review_record_ref);
  expect(packagePreview.result_review_state).toBe('execution_result_review_approved');
  expect(packagePreview.package_review_preview_hash).toBeTruthy();
  expect(packagePreview.package_review_preview_enabled).toBe(true);
  expect(packagePreview.package_commit_enabled).toBe(true);
  expect(packagePreview.package_review_enabled).toBe(false);
  expect(packagePreview.downstream_unavailable).toEqual(expect.arrayContaining(['handoff', 'export']));
  expect(packagePreview.candidate_package_kinds.map((candidate) => candidate.package_kind)).toEqual(
    EXPECTED_PACKAGE_REVIEW_KINDS,
  );
  expect(packagePreview.pass_type).toBe('associated_cohort');
  expect(packagePreview.selected_method_name).toBe('descriptive_summary');

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_preview_ready');
  await expect(page.locator('#package-construction-commit')).toBeEnabled();
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expectNoDeferredRawMixedControls(page);
  return packagePreview;
}

async function commitRenderedPackageConstruction(page, sessionId, approval, planPreview, execution, review, packagePreview) {
  await page.locator('#theme-selector').selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'dark');
  await expect(page.locator('#package-construction-commit')).toBeEnabled();

  const commitRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/package/review/commit') && apiRequest.method() === 'POST'
  ));
  const commitResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/package/review/commit')
  ));
  await page.locator('#package-construction-commit').click();
  const commitPayload = (await commitRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(commitPayload, [
    'analysis_plan_id',
    'analysis_run_id',
    'client_request_id',
    'expected_package_kinds',
    'package_review_preview_hash',
    'pass_run_id',
    'preview_hash',
    'preview_id',
    'result_review_record_ref',
    'session_id',
  ]);
  expect(commitPayload.session_id).toBe(sessionId);
  expect(commitPayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(commitPayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(commitPayload.preview_id).toBe(planPreview.preview_id);
  expect(commitPayload.preview_hash).toBe(planPreview.preview_hash);
  expect(commitPayload.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(commitPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(commitPayload.package_review_preview_hash).toBe(packagePreview.package_review_preview_hash);
  expect(commitPayload.expected_package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expectNoDeferredRawMixedPayloadFields(commitPayload);
  for (const forbiddenKey of [
    'handoff',
    'export',
    'rerun',
    'rewrite_output',
    'package_payload',
    'submit_package_review',
  ]) {
    expect(commitPayload).not.toHaveProperty(forbiddenKey);
  }

  const commit = await expectJson(await commitResponsePromise);
  expect(commit.schema_id).toBe('layer3.package_construction_commit.v1');
  expect(['committed', 'already_committed']).toContain(commit.status);
  expect(commit.session_id).toBe(sessionId);
  expect(commit.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(commit.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(commit.preview_identity.preview_id).toBe(planPreview.preview_id);
  expect(commit.preview_identity.preview_hash).toBe(planPreview.preview_hash);
  expect(commit.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(commit.result_review_record_ref).toBe(review.review_record_ref);
  expect(commit.package_review_preview_hash).toBe(packagePreview.package_review_preview_hash);
  expect(commit.reconciliation_record_id).toBeTruthy();
  expect(commit.output_packages).toHaveLength(3);
  expect(commit.output_package_ids).toHaveLength(3);
  expect(commit.package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expect(commit.payload_refs).toHaveLength(3);
  expect(commit.payload_hashes).toHaveLength(3);
  expect(commit.package_review_submit_enabled).toBe(true);
  expect(commit.handoff_enabled).toBe(false);
  expect(commit.aps_handoff_enabled).toBe(false);
  expect(commit.external_export_download_enabled).toBe(false);
  expect(commit.connector_dispatch_enabled).toBe(false);
  expect(commit.provider_public_url_enabled).toBe(false);
  expect(commit.downstream_unavailable).toEqual(expect.arrayContaining(['handoff', 'export']));

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_submit_ready');
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeEnabled();
  await expectNoDeferredRawMixedControls(page);
  return commit;
}

async function submitRenderedPackageReview(page, sessionId, approval, planPreview, execution, review, commit) {
  await page.locator('#theme-selector').selectOption('workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await page.locator('[data-operation-target="package-review-band"]').click();
  await expect(page.locator('#package-review-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#package-review-submit')).toBeEnabled();
  await page.locator('#package-review-submit-decision').selectOption('changes_requested');
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await page.locator('#package-review-submit-decision').selectOption('approved');
  await page.locator('#package-review-submit-notes').fill('Raw mixed rendered package review approves the constructed package set.');
  await expect(page.locator('#package-review-submit')).toBeEnabled();

  const submitRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/package/review/submit') && apiRequest.method() === 'POST'
  ));
  const submitResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/package/review/submit')
  ));
  await page.locator('#package-review-submit').click();
  const submitPayload = (await submitRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(submitPayload, [
    'analysis_plan_id',
    'analysis_run_id',
    'client_request_id',
    'construction_basis_hash',
    'decision_notes',
    'expected_package_kinds',
    'operator_decision',
    'output_package_ids',
    'package_review_preview_hash',
    'pass_run_id',
    'payload_hashes',
    'payload_refs',
    'preview_hash',
    'preview_id',
    'reconciliation_record_id',
    'result_review_record_ref',
    'session_id',
  ]);
  expect(submitPayload.session_id).toBe(sessionId);
  expect(submitPayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(submitPayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(submitPayload.preview_id).toBe(planPreview.preview_id);
  expect(submitPayload.preview_hash).toBe(planPreview.preview_hash);
  expect(submitPayload.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(submitPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(submitPayload.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(submitPayload.construction_basis_hash).toBe(commit.construction_basis_hash);
  expect(submitPayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(submitPayload.output_package_ids).toEqual(commit.output_package_ids);
  expect(submitPayload.payload_refs).toEqual(commit.payload_refs);
  expect(submitPayload.payload_hashes).toEqual(commit.payload_hashes);
  expect(submitPayload.expected_package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expect(submitPayload.operator_decision).toBe('approved');
  expect(submitPayload.decision_notes).toContain('approves the constructed package set');
  expectNoDeferredRawMixedPayloadFields(submitPayload);
  for (const forbiddenKey of [
    'handoff',
    'export',
    'aps_handoff',
    'create_package',
    'rebuild_package',
    'package_payload',
    'rewrite_output',
    'result_review_amendment',
  ]) {
    expect(submitPayload).not.toHaveProperty(forbiddenKey);
  }

  const packageSubmit = await expectJson(await submitResponsePromise);
  expect(packageSubmit.schema_id).toBe('layer3.cohort_package_review_submit.v1');
  expect(packageSubmit.status).toBe('submitted');
  expect(packageSubmit.session_id).toBe(sessionId);
  expect(packageSubmit.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(packageSubmit.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(packageSubmit.preview_identity.preview_id).toBe(planPreview.preview_id);
  expect(packageSubmit.preview_identity.preview_hash).toBe(planPreview.preview_hash);
  expect(packageSubmit.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(packageSubmit.result_review_record_ref).toBe(review.review_record_ref);
  expect(packageSubmit.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect([commit.construction_basis_hash, null]).toContain(packageSubmit.construction_basis_hash);
  expect(packageSubmit.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(packageSubmit.output_package_ids).toEqual(commit.output_package_ids);
  expect(packageSubmit.package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expect(packageSubmit.payload_refs).toEqual(commit.payload_refs);
  expect(packageSubmit.payload_hashes).toEqual(commit.payload_hashes);
  expect(packageSubmit.operator_decision).toBe('approved');
  expect(packageSubmit.package_review_state).toBe('package_review_approved');
  expect(packageSubmit.submit_record_ref).toBeTruthy();
  expect(packageSubmit.package_review_submit_enabled).toBe(false);
  expect(packageSubmit.handoff_enabled).toBe(false);
  expect(packageSubmit.aps_handoff_enabled).toBe(false);
  expect(packageSubmit.external_export_download_enabled).toBe(false);
  expect(packageSubmit.connector_dispatch_enabled).toBe(false);
  expect(packageSubmit.provider_public_url_enabled).toBe(false);
  expect(packageSubmit.downstream_unavailable).toEqual(expect.arrayContaining(['handoff', 'export']));

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_approved');
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expectNoDeferredRawMixedControls(page);
  return packageSubmit;
}

async function submitRenderedHandoffExportPrepare(
  page,
  sessionId,
  approval,
  planPreview,
  execution,
  review,
  commit,
  packageSubmit,
) {
  await page.locator('#theme-selector').selectOption('workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await page.locator('[data-operation-target="handoff-export-band"]').click();
  await expect(page.locator('#handoff-export-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('handoff_export_ready');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeEnabled();
  await page.locator('#handoff-export-prepare-decision').selectOption('hold');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await page.locator('#handoff-export-prepare-decision').selectOption('authorize_prepare');
  await page.locator('#handoff-export-prepare-notes').fill('Raw mixed rendered handoff/export prepare authorizes the internal envelope.');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeEnabled();

  const prepareRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/handoff/export/prepare') && apiRequest.method() === 'POST'
  ));
  const prepareResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/handoff/export/prepare')
  ));
  await page.locator('#handoff-export-prepare-submit').click();
  const preparePayload = (await prepareRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(preparePayload, [
    'analysis_plan_id',
    'analysis_run_id',
    'client_request_id',
    'decision_notes',
    'expected_package_kinds',
    'export_mode',
    'handoff_target',
    'operator_decision',
    'output_package_ids',
    'package_review_preview_hash',
    'package_review_state',
    'package_review_submit_record_ref',
    'package_review_submit_schema_id',
    'pass_run_id',
    'payload_hashes',
    'payload_refs',
    'preview_hash',
    'preview_id',
    'reconciliation_record_id',
    'result_review_record_ref',
    'session_id',
  ]);
  expect(preparePayload.session_id).toBe(sessionId);
  expect(preparePayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(preparePayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(preparePayload.preview_id).toBe(planPreview.preview_id);
  expect(preparePayload.preview_hash).toBe(planPreview.preview_hash);
  expect(preparePayload.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(preparePayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(preparePayload.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(preparePayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(preparePayload.output_package_ids).toEqual(commit.output_package_ids);
  expect(preparePayload.payload_refs).toEqual(commit.payload_refs);
  expect(preparePayload.payload_hashes).toEqual(commit.payload_hashes);
  expect(preparePayload.package_review_submit_record_ref).toBe(packageSubmit.submit_record_ref);
  expect(preparePayload.package_review_state).toBe('package_review_approved');
  expect(preparePayload.package_review_submit_schema_id).toBe(packageSubmit.schema_id);
  expect(preparePayload.handoff_target).toBe('internal_export_envelope');
  expect(preparePayload.export_mode).toBe('prepare_only');
  expect(preparePayload.operator_decision).toBe('authorize_prepare');
  expect(preparePayload.decision_notes).toContain('authorizes the internal envelope');
  expect(preparePayload.expected_package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expectNoDeferredRawMixedPayloadFields(preparePayload);
  for (const forbiddenKey of [
    'aps_handoff',
    'dispatch',
    'send',
    'external_export',
    'external_target',
    'download',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'package_variant_content',
    'rewrite_output',
    'edited_findings',
    'result_review_amendment',
    'package_review_amendment',
    'rerun',
    'retry',
    'recover',
    'cancel',
    'selected_pass_ids',
    'pass_run_ids',
    'new_analysis_plan',
    'plan_revision',
    'source_expansion',
    'local_upload',
    'local_directory',
    'schema_migration',
  ]) {
    expect(preparePayload).not.toHaveProperty(forbiddenKey);
  }

  const handoffPrepare = await expectJson(await prepareResponsePromise);
  expect(handoffPrepare.schema_id).toBe('layer3.cohort_handoff_export_prepare.v1');
  expect(handoffPrepare.status).toBe('prepared');
  expect(handoffPrepare.session_id).toBe(sessionId);
  expect(handoffPrepare.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(handoffPrepare.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(handoffPrepare.preview_identity.preview_id).toBe(planPreview.preview_id);
  expect(handoffPrepare.preview_identity.preview_hash).toBe(planPreview.preview_hash);
  expect(handoffPrepare.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(handoffPrepare.result_review_record_ref).toBe(review.review_record_ref);
  expect(handoffPrepare.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(handoffPrepare.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(handoffPrepare.output_package_ids).toEqual(commit.output_package_ids);
  expect(handoffPrepare.package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expect(handoffPrepare.payload_refs).toEqual(commit.payload_refs);
  expect(handoffPrepare.payload_hashes).toEqual(commit.payload_hashes);
  expect(handoffPrepare.package_review_submit_schema_id).toBe(packageSubmit.schema_id);
  expect(handoffPrepare.package_review_submit_record_ref).toBe(packageSubmit.submit_record_ref);
  expect(handoffPrepare.package_review_state).toBe('package_review_approved');
  expect(handoffPrepare.operator_decision).toBe('authorize_prepare');
  expect(handoffPrepare.handoff_export_state).toBe('handoff_export_prepared');
  expect(handoffPrepare.handoff_target).toBe('internal_export_envelope');
  expect(handoffPrepare.export_mode).toBe('prepare_only');
  expect(handoffPrepare.external_handoff_enabled).toBe(false);
  expect(handoffPrepare.external_export_enabled).toBe(false);
  expect(handoffPrepare.dispatch_enabled).toBe(false);
  expect(handoffPrepare.aps_handoff_enabled).toBe(false);
  expect(handoffPrepare.external_export_download_enabled).toBe(false);
  expect(handoffPrepare.connector_dispatch_enabled).toBe(false);
  expect(handoffPrepare.provider_public_url_enabled).toBe(false);
  expect(handoffPrepare.downstream_unavailable).toEqual(
    expect.arrayContaining(['aps_handoff', 'external_export', 'downstream_dispatch']),
  );
  expect(handoffPrepare.next_state).toBe('handoff_export_prepared');
  expect(handoffPrepare.prepare_record_ref).toBeTruthy();
  expect(handoffPrepare.handoff_export_envelope).toBeTruthy();
  expect(handoffPrepare.handoff_export_envelope.package_review_submit_record_ref).toBe(packageSubmit.submit_record_ref);
  expect(handoffPrepare.handoff_export_envelope.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(handoffPrepare.authority_rail).toBeTruthy();

  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('handoff_export_prepared');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeEnabled();
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-delivery-submit')).toBeDisabled();
  await expectNoDeferredRawMixedControls(page);
  return handoffPrepare;
}

async function submitRenderedApsHandoffDispatch(
  page,
  sessionId,
  approval,
  planPreview,
  execution,
  review,
  commit,
  packageSubmit,
  handoffPrepare,
) {
  await page.locator('#theme-selector').selectOption('workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await page.locator('[data-operation-target="aps-handoff-band"]').click();
  await expect(page.locator('#aps-handoff-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_handoff_ready');
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeEnabled();

  const dispatchRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/handoff/aps/dispatch') && apiRequest.method() === 'POST'
  ));
  const dispatchResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/handoff/aps/dispatch')
  ));
  await page.locator('#aps-handoff-dispatch-submit').click();
  const dispatchPayload = (await dispatchRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(dispatchPayload, [
    'analysis_plan_id',
    'analysis_run_id',
    'aps_handoff_target',
    'client_request_id',
    'dispatch_mode',
    'export_mode',
    'handoff_export_envelope_ref',
    'handoff_export_state',
    'handoff_target',
    'operator_decision',
    'output_package_ids',
    'package_kinds',
    'package_review_preview_hash',
    'package_review_state',
    'package_review_submit_record_ref',
    'pass_run_id',
    'payload_hashes',
    'payload_refs',
    'prepare_record_ref',
    'preview_hash',
    'preview_id',
    'reconciliation_record_id',
    'result_review_record_ref',
    'session_id',
  ]);
  expect(dispatchPayload.session_id).toBe(sessionId);
  expect(dispatchPayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(dispatchPayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(dispatchPayload.preview_id).toBe(planPreview.preview_id);
  expect(dispatchPayload.preview_hash).toBe(planPreview.preview_hash);
  expect(dispatchPayload.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(dispatchPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(dispatchPayload.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(dispatchPayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(dispatchPayload.output_package_ids).toEqual(commit.output_package_ids);
  expect(dispatchPayload.package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expect(dispatchPayload.payload_refs).toEqual(commit.payload_refs);
  expect(dispatchPayload.payload_hashes).toEqual(commit.payload_hashes);
  expect(dispatchPayload.package_review_submit_record_ref).toBe(packageSubmit.submit_record_ref);
  expect(dispatchPayload.package_review_state).toBe('package_review_approved');
  expect(dispatchPayload.prepare_record_ref).toBe(handoffPrepare.prepare_record_ref);
  expect(dispatchPayload.handoff_export_state).toBe('handoff_export_prepared');
  expect(dispatchPayload.handoff_export_envelope_ref).toBe(handoffPrepare.handoff_export_envelope.envelope_ref);
  expect(dispatchPayload.handoff_target).toBe('internal_export_envelope');
  expect(dispatchPayload.export_mode).toBe('prepare_only');
  expect(dispatchPayload.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(dispatchPayload.dispatch_mode).toBe('server_side_aps_handoff');
  expect(dispatchPayload.operator_decision).toBe('dispatch_aps_handoff');
  expectNoDeferredRawMixedPayloadFields(dispatchPayload);
  for (const forbiddenKey of [
    'external_export',
    'external_target',
    'download',
    'download_url',
    'destination',
    'destination_selector',
    'connector_run_id',
    'connector_dispatch',
    'dispatch',
    'send',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'package_variant_content',
    'rewrite_output',
    'edited_findings',
    'result_review_amendment',
    'package_review_amendment',
    'rerun',
    'retry',
    'recover',
    'cancel',
    'selected_pass_ids',
    'pass_run_ids',
    'new_analysis_plan',
    'plan_revision',
    'source_expansion',
    'local_upload',
    'local_directory',
    'schema_migration',
  ]) {
    expect(dispatchPayload).not.toHaveProperty(forbiddenKey);
  }

  const apsDispatch = await expectJson(await dispatchResponsePromise);
  expect(apsDispatch.schema_id).toBe('layer3.aps_handoff_dispatch.v1');
  expect(apsDispatch.status).toBe('dispatched');
  expect(apsDispatch.session_id).toBe(sessionId);
  expect(apsDispatch.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(apsDispatch.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(apsDispatch.preview_identity.preview_id).toBe(planPreview.preview_id);
  expect(apsDispatch.preview_identity.preview_hash).toBe(planPreview.preview_hash);
  expect(apsDispatch.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(apsDispatch.result_review_record_ref).toBe(review.review_record_ref);
  expect(apsDispatch.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(apsDispatch.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(apsDispatch.output_package_ids).toEqual(commit.output_package_ids);
  expect(apsDispatch.package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expect(apsDispatch.payload_refs).toEqual(commit.payload_refs);
  expect(apsDispatch.payload_hashes).toEqual(commit.payload_hashes);
  expect(apsDispatch.package_review_submit_record_ref).toBe(packageSubmit.submit_record_ref);
  expect(apsDispatch.package_review_state).toBe('package_review_approved');
  expect(apsDispatch.prepare_record_ref).toBe(handoffPrepare.prepare_record_ref);
  expect(apsDispatch.handoff_export_state).toBe('handoff_export_prepared');
  expect(apsDispatch.handoff_export_envelope_ref).toBe(handoffPrepare.handoff_export_envelope.envelope_ref);
  expect(apsDispatch.handoff_target).toBe('internal_export_envelope');
  expect(apsDispatch.export_mode).toBe('prepare_only');
  expect(apsDispatch.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(apsDispatch.dispatch_mode).toBe('server_side_aps_handoff');
  expect(apsDispatch.operator_decision).toBe('dispatch_aps_handoff');
  expect(apsDispatch.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(apsDispatch.aps_handoff_record_ref).toBeTruthy();
  expect(apsDispatch.aps_output_package_id).toBeTruthy();
  expect(apsDispatch.aps_output_package_kind).toBe('aps_evidence_bundle_handoff');
  expect(apsDispatch.aps_bundle_ref).toBeTruthy();
  expect(apsDispatch.aps_bundle_id).toBeTruthy();
  expect(apsDispatch.aps_schema_id).toBeTruthy();
  expect(Object.keys(apsDispatch.source_package_refs).sort()).toEqual([...EXPECTED_PACKAGE_REVIEW_KINDS].sort());
  expect(Object.keys(apsDispatch.source_package_hashes).sort()).toEqual([...EXPECTED_PACKAGE_REVIEW_KINDS].sort());
  expect(valuesByPackageKind(apsDispatch.source_package_refs)).toEqual(commit.payload_refs);
  expect(valuesByPackageKind(apsDispatch.source_package_hashes)).toEqual(commit.payload_hashes);
  expect(apsDispatch.external_export_enabled).toBe(false);
  expect(apsDispatch.download_enabled).toBe(false);
  expect(apsDispatch.connector_dispatch_enabled).toBe(false);
  expect(apsDispatch.provider_public_url_enabled).toBe(false);
  expect(apsDispatch.downstream_unavailable).toEqual(
    expect.arrayContaining(['external_export', 'download', 'connector_dispatch', 'non_aps_dispatch']),
  );
  expect(apsDispatch.next_state).toBe('aps_handoff_dispatched');
  expect(apsDispatch.authority_rail).toBeTruthy();

  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_handoff_dispatched');
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-prepare-submit')).toBeEnabled();
  await expect(page.locator('#external-export-download-delivery-submit')).toBeDisabled();
  await expectNoDeferredRawMixedControls(page);
  return apsDispatch;
}

async function submitRenderedExternalExportDownloadPrepare(
  page,
  sessionId,
  approval,
  planPreview,
  execution,
  review,
  commit,
  packageSubmit,
  handoffPrepare,
  apsDispatch,
) {
  await page.locator('#theme-selector').selectOption('workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await page.locator('[data-operation-target="external-export-download-band"]').click();
  await expect(page.locator('#external-export-download-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('external_export_download_ready');
  await expect(page.locator('#external-export-download-prepare-submit')).toBeEnabled();

  const prepareRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/handoff/export/download/prepare') && apiRequest.method() === 'POST'
  ));
  const prepareResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/handoff/export/download/prepare')
  ));
  await page.locator('#external-export-download-prepare-submit').click();
  const preparePayload = (await prepareRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(preparePayload, [
    'analysis_plan_id',
    'analysis_run_id',
    'aps_bundle_hash',
    'aps_bundle_id',
    'aps_bundle_ref',
    'aps_bundle_size_bytes',
    'aps_handoff_record_ref',
    'aps_handoff_state',
    'aps_handoff_target',
    'aps_output_package_id',
    'aps_output_package_kind',
    'aps_schema_id',
    'client_request_id',
    'dispatch_mode',
    'download_mode',
    'export_download_target',
    'export_mode',
    'handoff_export_envelope_ref',
    'handoff_export_state',
    'handoff_target',
    'operator_decision',
    'output_package_ids',
    'package_kinds',
    'package_review_preview_hash',
    'package_review_state',
    'package_review_submit_record_ref',
    'pass_run_id',
    'payload_hashes',
    'payload_refs',
    'prepare_record_ref',
    'preview_hash',
    'preview_id',
    'reconciliation_record_id',
    'result_review_record_ref',
    'session_id',
  ]);
  expect(preparePayload.session_id).toBe(sessionId);
  expect(preparePayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(preparePayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(preparePayload.preview_id).toBe(planPreview.preview_id);
  expect(preparePayload.preview_hash).toBe(planPreview.preview_hash);
  expect(preparePayload.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(preparePayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(preparePayload.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(preparePayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(preparePayload.output_package_ids).toEqual(commit.output_package_ids);
  expect(preparePayload.package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expect(preparePayload.payload_refs).toEqual(commit.payload_refs);
  expect(preparePayload.payload_hashes).toEqual(commit.payload_hashes);
  expect(preparePayload.package_review_submit_record_ref).toBe(packageSubmit.submit_record_ref);
  expect(preparePayload.package_review_state).toBe('package_review_approved');
  expect(preparePayload.prepare_record_ref).toBe(handoffPrepare.prepare_record_ref);
  expect(preparePayload.handoff_export_state).toBe('handoff_export_prepared');
  expect(preparePayload.handoff_export_envelope_ref).toBe(handoffPrepare.handoff_export_envelope.envelope_ref);
  expect(preparePayload.handoff_target).toBe('internal_export_envelope');
  expect(preparePayload.export_mode).toBe('prepare_only');
  expect(preparePayload.aps_handoff_record_ref).toBe(apsDispatch.aps_handoff_record_ref);
  expect(preparePayload.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(preparePayload.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(preparePayload.dispatch_mode).toBe('server_side_aps_handoff');
  expect(preparePayload.aps_output_package_id).toBe(apsDispatch.aps_output_package_id);
  expect(preparePayload.aps_output_package_kind).toBe('aps_evidence_bundle_handoff');
  expect(preparePayload.aps_bundle_ref).toBe(apsDispatch.aps_bundle_ref);
  expect(preparePayload.aps_bundle_id).toBe(apsDispatch.aps_bundle_id);
  expect(preparePayload.aps_schema_id).toBe(apsDispatch.aps_schema_id);
  expect(preparePayload.aps_bundle_hash).toEqual(expect.any(String));
  expect(preparePayload.aps_bundle_hash.length).toBe(64);
  expect(preparePayload.aps_bundle_size_bytes).toBeGreaterThan(0);
  expect(preparePayload.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(preparePayload.download_mode).toBe('reference_only_prepare');
  expect(preparePayload.operator_decision).toBe('prepare_external_export_download');
  expectNoDeferredRawMixedPayloadFields(preparePayload);
  for (const forbiddenKey of [
    'external_export',
    'external_target',
    'download',
    'download_url',
    'delivery',
    'delivery_mode',
    'destination',
    'destination_selector',
    'connector_run_id',
    'connector_dispatch',
    'dispatch',
    'send',
    'public_url',
    'signed_url',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'package_variant_content',
    'rewrite_output',
    'edited_findings',
    'result_review_amendment',
    'package_review_amendment',
    'rerun',
    'retry',
    'recover',
    'cancel',
    'selected_pass_ids',
    'pass_run_ids',
    'new_analysis_plan',
    'plan_revision',
    'source_expansion',
    'local_upload',
    'local_directory',
    'schema_migration',
  ]) {
    expect(preparePayload).not.toHaveProperty(forbiddenKey);
  }

  const downloadPrepare = await expectJson(await prepareResponsePromise);
  expect(downloadPrepare.schema_id).toBe('layer3.external_export_download_prepare.v1');
  expect(downloadPrepare.status).toBe('prepared');
  expect(downloadPrepare.session_id).toBe(sessionId);
  expect(downloadPrepare.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(downloadPrepare.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(downloadPrepare.preview_identity.preview_id).toBe(planPreview.preview_id);
  expect(downloadPrepare.preview_identity.preview_hash).toBe(planPreview.preview_hash);
  expect(downloadPrepare.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(downloadPrepare.result_review_record_ref).toBe(review.review_record_ref);
  expect(downloadPrepare.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(downloadPrepare.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(downloadPrepare.output_package_ids).toEqual(commit.output_package_ids);
  expect(downloadPrepare.package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expect(downloadPrepare.payload_refs).toEqual(commit.payload_refs);
  expect(downloadPrepare.payload_hashes).toEqual(commit.payload_hashes);
  expect(downloadPrepare.package_review_submit_record_ref).toBe(packageSubmit.submit_record_ref);
  expect(downloadPrepare.package_review_state).toBe('package_review_approved');
  expect(downloadPrepare.prepare_record_ref).toBe(handoffPrepare.prepare_record_ref);
  expect(downloadPrepare.handoff_export_state).toBe('handoff_export_prepared');
  expect(downloadPrepare.handoff_export_envelope_ref).toBe(handoffPrepare.handoff_export_envelope.envelope_ref);
  expect(downloadPrepare.handoff_target).toBe('internal_export_envelope');
  expect(downloadPrepare.export_mode).toBe('prepare_only');
  expect(downloadPrepare.aps_handoff_record_ref).toBe(apsDispatch.aps_handoff_record_ref);
  expect(downloadPrepare.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(downloadPrepare.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(downloadPrepare.dispatch_mode).toBe('server_side_aps_handoff');
  expect(downloadPrepare.aps_output_package_id).toBe(apsDispatch.aps_output_package_id);
  expect(downloadPrepare.aps_output_package_kind).toBe('aps_evidence_bundle_handoff');
  expect(downloadPrepare.aps_bundle_ref).toBe(apsDispatch.aps_bundle_ref);
  expect(downloadPrepare.aps_bundle_id).toBe(apsDispatch.aps_bundle_id);
  expect(downloadPrepare.aps_schema_id).toBe(apsDispatch.aps_schema_id);
  expect(downloadPrepare.external_export_download_state).toBe('external_export_download_prepared');
  expect(downloadPrepare.external_export_download_record_ref).toBeTruthy();
  expect(downloadPrepare.export_download_descriptor_ref).toBeTruthy();
  expect(downloadPrepare.source_artifact_ref).toBe(apsDispatch.aps_bundle_ref);
  expect(downloadPrepare.source_artifact_hash).toBe(preparePayload.aps_bundle_hash);
  expect(downloadPrepare.source_artifact_size_bytes).toBe(preparePayload.aps_bundle_size_bytes);
  expect(downloadPrepare.browser_download_enabled).toBe(false);
  expect(downloadPrepare.download_url_enabled).toBe(false);
  expect(downloadPrepare.connector_dispatch_enabled).toBe(false);
  expect(downloadPrepare.destination_selection_enabled).toBe(false);
  expect(downloadPrepare.generic_downstream_dispatch_enabled).toBe(false);
  expect(downloadPrepare.downstream_unavailable).toEqual(
    expect.arrayContaining([
      'browser_download',
      'download_url',
      'connector_dispatch',
      'destination_selection',
      'generic_downstream_dispatch',
    ]),
  );
  expect(downloadPrepare.delivery_ui.state).toBe('associated_cohort_external_export_download_delivery_ui_ready');
  expect(downloadPrepare.delivery_ui.browser_managed_same_origin_attachment_enabled).toBe(true);
  expect(downloadPrepare.delivery_ui.public_url_enabled).toBe(false);
  expect(downloadPrepare.delivery_ui.signed_url_enabled).toBe(false);
  expect(downloadPrepare.delivery_ui.connector_dispatch_enabled).toBe(false);
  expect(downloadPrepare.delivery_ui.destination_selection_enabled).toBe(false);
  expect(downloadPrepare.next_state).toBe('external_export_download_prepared');
  expect(downloadPrepare.authority_rail).toBeTruthy();

  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('external_export_download_prepared');
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-delivery-submit')).toBeEnabled();
  await expectNoDeferredRawMixedControls(page);
  return downloadPrepare;
}

async function submitRenderedExternalExportDownloadDelivery(
  page,
  sessionId,
  approval,
  planPreview,
  execution,
  review,
  commit,
  packageSubmit,
  handoffPrepare,
  apsDispatch,
  downloadPrepare,
) {
  await page.locator('#theme-selector').selectOption('workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await page.locator('[data-operation-target="external-export-download-band"]').click();
  await expect(page.locator('#external-export-download-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    'external_export_download_delivery_ui_ready',
  );
  await expect(page.locator('#external-export-download-delivery-submit')).toBeEnabled();

  const deliveryRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/handoff/export/download/deliver') && apiRequest.method() === 'POST'
  ));
  const deliveryResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/handoff/export/download/deliver')
  ));
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#external-export-download-delivery-submit').click();
  const deliveryRequest = await deliveryRequestPromise;
  const deliveryPayload = formPostPayload(deliveryRequest);
  expectOnlyPayloadKeys(deliveryPayload, [
    'analysis_plan_id',
    'analysis_run_id',
    'aps_bundle_hash',
    'aps_bundle_id',
    'aps_bundle_ref',
    'aps_bundle_size_bytes',
    'aps_handoff_record_ref',
    'aps_handoff_state',
    'aps_handoff_target',
    'aps_output_package_id',
    'aps_output_package_kind',
    'aps_schema_id',
    'client_request_id',
    'delivery_mode',
    'dispatch_mode',
    'download_mode',
    'export_download_descriptor_ref',
    'export_download_target',
    'export_mode',
    'external_export_download_record_ref',
    'external_export_download_state',
    'handoff_export_envelope_ref',
    'handoff_export_state',
    'handoff_target',
    'operator_decision',
    'output_package_ids',
    'package_kinds',
    'package_review_preview_hash',
    'package_review_state',
    'package_review_submit_record_ref',
    'pass_run_id',
    'payload_hashes',
    'payload_refs',
    'prepare_record_ref',
    'preview_hash',
    'preview_id',
    'reconciliation_record_id',
    'result_review_record_ref',
    'session_id',
  ]);
  expect(deliveryPayload.session_id).toBe(sessionId);
  expect(deliveryPayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(deliveryPayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(deliveryPayload.preview_id).toBe(planPreview.preview_id);
  expect(deliveryPayload.preview_hash).toBe(planPreview.preview_hash);
  expect(deliveryPayload.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(deliveryPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(deliveryPayload.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(deliveryPayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(deliveryPayload.output_package_ids).toEqual(commit.output_package_ids);
  expect(deliveryPayload.package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expect(deliveryPayload.payload_refs).toEqual(commit.payload_refs);
  expect(deliveryPayload.payload_hashes).toEqual(commit.payload_hashes);
  expect(deliveryPayload.package_review_submit_record_ref).toBe(packageSubmit.submit_record_ref);
  expect(deliveryPayload.package_review_state).toBe('package_review_approved');
  expect(deliveryPayload.prepare_record_ref).toBe(handoffPrepare.prepare_record_ref);
  expect(deliveryPayload.handoff_export_state).toBe('handoff_export_prepared');
  expect(deliveryPayload.handoff_export_envelope_ref).toBe(handoffPrepare.handoff_export_envelope.envelope_ref);
  expect(deliveryPayload.handoff_target).toBe('internal_export_envelope');
  expect(deliveryPayload.export_mode).toBe('prepare_only');
  expect(deliveryPayload.aps_handoff_record_ref).toBe(apsDispatch.aps_handoff_record_ref);
  expect(deliveryPayload.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(deliveryPayload.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(deliveryPayload.dispatch_mode).toBe('server_side_aps_handoff');
  expect(deliveryPayload.aps_output_package_id).toBe(apsDispatch.aps_output_package_id);
  expect(deliveryPayload.aps_output_package_kind).toBe('aps_evidence_bundle_handoff');
  expect(deliveryPayload.aps_bundle_ref).toBe(apsDispatch.aps_bundle_ref);
  expect(deliveryPayload.aps_bundle_id).toBe(apsDispatch.aps_bundle_id);
  expect(deliveryPayload.aps_schema_id).toBe(apsDispatch.aps_schema_id);
  expect(deliveryPayload.aps_bundle_hash).toBe(downloadPrepare.source_artifact_hash);
  expect(deliveryPayload.aps_bundle_size_bytes).toBe(downloadPrepare.source_artifact_size_bytes);
  expect(deliveryPayload.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(deliveryPayload.download_mode).toBe('reference_only_prepare');
  expect(deliveryPayload.operator_decision).toBe('deliver_external_export_download');
  expect(deliveryPayload.external_export_download_record_ref).toBe(
    downloadPrepare.external_export_download_record_ref,
  );
  expect(deliveryPayload.export_download_descriptor_ref).toBe(downloadPrepare.export_download_descriptor_ref);
  expect(deliveryPayload.external_export_download_state).toBe('external_export_download_prepared');
  expect(deliveryPayload.delivery_mode).toBe('same_origin_artifact_stream');
  expectNoDeferredRawMixedPayloadFields(deliveryPayload);
  for (const forbiddenKey of [
    'download',
    'download_url',
    'delivery',
    'destination',
    'destination_selector',
    'connector_run_id',
    'connector_dispatch',
    'dispatch',
    'send',
    'public_url',
    'signed_url',
    'signed_reference_token',
    'provider_url',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'package_variant_content',
    'rewrite_output',
    'rerun',
    'retry',
    'recover',
    'cancel',
    'selected_pass_ids',
    'pass_run_ids',
    'new_analysis_plan',
    'plan_revision',
    'source_expansion',
    'local_upload',
    'local_directory',
    'schema_migration',
  ]) {
    expect(deliveryPayload).not.toHaveProperty(forbiddenKey);
  }

  const deliveryResponse = await deliveryResponsePromise;
  expect(deliveryResponse.ok()).toBe(true);
  const headers = deliveryResponse.headers();
  expect(headers['x-layer3-schema-id']).toBe('layer3.external_export_download_delivery.v1');
  expect(headers['x-layer3-delivery-state']).toBe('external_export_download_delivered');
  expect(headers['x-layer3-source-artifact-hash']).toBe(downloadPrepare.source_artifact_hash);
  expect(headers['x-layer3-external-export-download-record-ref']).toBe(
    downloadPrepare.external_export_download_record_ref,
  );
  expect(headers['content-disposition']).toContain('attachment');
  expect(headers).not.toHaveProperty('download_url');
  expect(headers).not.toHaveProperty('public_url');
  expect(headers).not.toHaveProperty('signed_url');
  expect(headers).not.toHaveProperty('download-url');
  expect(headers).not.toHaveProperty('public-url');
  expect(headers).not.toHaveProperty('signed-url');
  if (headers['content-length']) {
    expect(Number(headers['content-length'])).toBe(downloadPrepare.source_artifact_size_bytes);
  }
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain('layer3-');

  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    /external_export_download_delivery_(submitted|delivered)/,
    { timeout: 7000 },
  );
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    downloadPrepare.external_export_download_record_ref,
  );
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    downloadPrepare.source_artifact_hash,
  );
  await expectNoDeferredRawMixedControls(page);
  return { headers, payload: deliveryPayload };
}

async function submitRenderedExternalExportDownloadSignedReference(
  page,
  sessionId,
  approval,
  planPreview,
  execution,
  review,
  commit,
  packageSubmit,
  handoffPrepare,
  apsDispatch,
  downloadPrepare,
) {
  await page.locator('#theme-selector').selectOption('workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await page.locator('[data-operation-target="external-export-download-band"]').click();
  await expect(page.locator('#external-export-download-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'external_export_download_signed_reference_ui_ready',
  );
  await expect(page.locator('#external-export-download-signed-reference-generate')).toBeEnabled();
  await expect(page.locator('#external-export-download-signed-reference-use')).toBeDisabled();

  const signedRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/handoff/export/download/signed-reference/generate')
      && apiRequest.method() === 'POST'
  ));
  const signedResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/handoff/export/download/signed-reference/generate')
  ));
  await page.locator('#external-export-download-signed-reference-generate').click();
  const signedPayload = (await signedRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(signedPayload, [
    'analysis_plan_id',
    'analysis_run_id',
    'aps_bundle_hash',
    'aps_bundle_id',
    'aps_bundle_ref',
    'aps_bundle_size_bytes',
    'aps_handoff_record_ref',
    'aps_handoff_state',
    'aps_handoff_target',
    'aps_output_package_id',
    'aps_output_package_kind',
    'aps_schema_id',
    'client_request_id',
    'delivery_mode',
    'dispatch_mode',
    'download_mode',
    'export_download_descriptor_ref',
    'export_download_target',
    'export_mode',
    'external_export_download_record_ref',
    'external_export_download_state',
    'handoff_export_envelope_ref',
    'handoff_export_state',
    'handoff_target',
    'operator_decision',
    'output_package_ids',
    'package_kinds',
    'package_review_preview_hash',
    'package_review_state',
    'package_review_submit_record_ref',
    'pass_run_id',
    'payload_hashes',
    'payload_refs',
    'prepare_record_ref',
    'preview_hash',
    'preview_id',
    'reconciliation_record_id',
    'result_review_record_ref',
    'session_id',
  ]);
  expect(signedPayload.session_id).toBe(sessionId);
  expect(signedPayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(signedPayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(signedPayload.preview_id).toBe(planPreview.preview_id);
  expect(signedPayload.preview_hash).toBe(planPreview.preview_hash);
  expect(signedPayload.analysis_run_id).toBe(execution.start.analysis_run_id);
  expect(signedPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(signedPayload.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(signedPayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(signedPayload.output_package_ids).toEqual(commit.output_package_ids);
  expect(signedPayload.package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS);
  expect(signedPayload.payload_refs).toEqual(commit.payload_refs);
  expect(signedPayload.payload_hashes).toEqual(commit.payload_hashes);
  expect(signedPayload.package_review_submit_record_ref).toBe(packageSubmit.submit_record_ref);
  expect(signedPayload.package_review_state).toBe('package_review_approved');
  expect(signedPayload.prepare_record_ref).toBe(handoffPrepare.prepare_record_ref);
  expect(signedPayload.handoff_export_state).toBe('handoff_export_prepared');
  expect(signedPayload.handoff_export_envelope_ref).toBe(handoffPrepare.handoff_export_envelope.envelope_ref);
  expect(signedPayload.handoff_target).toBe('internal_export_envelope');
  expect(signedPayload.export_mode).toBe('prepare_only');
  expect(signedPayload.aps_handoff_record_ref).toBe(apsDispatch.aps_handoff_record_ref);
  expect(signedPayload.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(signedPayload.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(signedPayload.dispatch_mode).toBe('server_side_aps_handoff');
  expect(signedPayload.aps_output_package_id).toBe(apsDispatch.aps_output_package_id);
  expect(signedPayload.aps_output_package_kind).toBe('aps_evidence_bundle_handoff');
  expect(signedPayload.aps_bundle_ref).toBe(apsDispatch.aps_bundle_ref);
  expect(signedPayload.aps_bundle_id).toBe(apsDispatch.aps_bundle_id);
  expect(signedPayload.aps_schema_id).toBe(apsDispatch.aps_schema_id);
  expect(signedPayload.aps_bundle_hash).toBe(downloadPrepare.source_artifact_hash);
  expect(signedPayload.aps_bundle_size_bytes).toBe(downloadPrepare.source_artifact_size_bytes);
  expect(signedPayload.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(signedPayload.download_mode).toBe('reference_only_prepare');
  expect(signedPayload.operator_decision).toBe('deliver_external_export_download');
  expect(signedPayload.external_export_download_record_ref).toBe(
    downloadPrepare.external_export_download_record_ref,
  );
  expect(signedPayload.export_download_descriptor_ref).toBe(downloadPrepare.export_download_descriptor_ref);
  expect(signedPayload.external_export_download_state).toBe('external_export_download_prepared');
  expect(signedPayload.delivery_mode).toBe('same_origin_artifact_stream');
  expectNoDeferredRawMixedPayloadFields(signedPayload);
  for (const forbiddenKey of [
    'download_url',
    'destination',
    'destination_selector',
    'connector_run_id',
    'connector_dispatch',
    'public_url',
    'signed_url',
    'signed_reference_token',
    'provider_url',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'package_variant_content',
    'rewrite_output',
    'rerun',
    'retry',
    'recover',
    'cancel',
    'selected_pass_ids',
    'pass_run_ids',
    'new_analysis_plan',
    'plan_revision',
    'source_expansion',
    'local_upload',
    'local_directory',
    'schema_migration',
  ]) {
    expect(signedPayload).not.toHaveProperty(forbiddenKey);
  }

  const signedReference = await expectJson(await signedResponsePromise);
  expect(signedReference.schema_id).toBe('layer3.external_export_download_signed_reference.v1');
  expect(signedReference.status).toBe('prepared');
  expect(signedReference.signed_reference_state).toBe('external_export_download_signed_reference_ready');
  expect(signedReference.signed_reference_token).toEqual(expect.any(String));
  expect(signedReference.signed_reference_token_id).toBeTruthy();
  expect(signedReference.signed_reference_receipt_id).toBeTruthy();
  expect(signedReference.signed_reference_replay_policy).toBe('single_use');
  expect(signedReference.signed_reference_use_count).toBe(0);
  expect(signedReference.signed_reference_max_use_count).toBe(1);
  expect(signedReference.signed_reference_revoked).toBe(false);
  expect(signedReference.signed_reference_use_endpoint).toBe(
    '/api/v1/layer3/handoff/export/download/signed-reference/use',
  );
  expect(signedReference.delivery_mode).toBe('same_origin_signed_delivery_reference');
  expect(signedReference.server_authority).toBe(
    'associated_cohort_external_export_download_signed_reference_gate',
  );
  expect(signedReference.source_artifact_hash).toBe(downloadPrepare.source_artifact_hash);
  expect(signedReference.source_artifact_size_bytes).toBe(downloadPrepare.source_artifact_size_bytes);
  expect(signedReference.public_url_enabled).toBe(false);
  expect(signedReference.external_object_store_url_enabled).toBe(false);
  expect(signedReference.connector_dispatch_enabled).toBe(false);
  expect(signedReference.destination_selection_enabled).toBe(false);
  expect(signedReference.generic_downstream_dispatch_enabled).toBe(false);
  expect(signedReference.package_mutation_enabled).toBe(false);
  expect(signedReference.schema_runtime_source_widening_enabled).toBe(false);
  expect(signedReference.authority_rail.token_authority).toBe('server_hmac_with_durable_state');
  expect(signedReference.authority_rail.durable_state_required).toBe(true);
  expect(signedReference.authority_rail.configured_secret_present).toBe(true);
  for (const forbiddenKey of ['download_url', 'download_token', 'public_url', 'signed_url', 'connector_run_id']) {
    expect(signedReference).not.toHaveProperty(forbiddenKey);
  }

  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'external_export_download_signed_reference_ready',
  );
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'same_origin_signed_delivery_reference',
  );
  await expect(page.locator('#external-export-download-signed-reference-generate')).toBeDisabled();
  await expect(page.locator('#external-export-download-signed-reference-use')).toBeEnabled();

  const useRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/handoff/export/download/signed-reference/use')
      && apiRequest.method() === 'POST'
  ));
  const useResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/handoff/export/download/signed-reference/use')
  ));
  await page.locator('#external-export-download-signed-reference-use').click();
  expect((await useRequestPromise).postDataJSON()).toEqual({
    signed_reference_token: signedReference.signed_reference_token,
  });
  const useResponse = await useResponsePromise;
  expect(useResponse.ok()).toBe(true);
  const useHeaders = useResponse.headers();
  expect(useHeaders['x-layer3-schema-id']).toBe('layer3.external_export_download_signed_reference_use.v1');
  expect(useHeaders['x-layer3-delivery-state']).toBe('external_export_download_delivered');
  expect(useHeaders['x-layer3-signed-reference-state']).toBe(
    'external_export_download_signed_reference_delivered',
  );
  expect(useHeaders['x-layer3-signed-reference-token-id']).toBe(signedReference.signed_reference_token_id);
  expect(useHeaders['x-layer3-signed-reference-receipt-id']).toBeTruthy();
  expect(useHeaders['x-layer3-signed-reference-replay-policy']).toBe('single_use');
  expect(useHeaders['x-layer3-signed-reference-use-count']).toBe('1');
  expect(useHeaders['x-layer3-source-artifact-hash']).toBe(downloadPrepare.source_artifact_hash);
  expect(useHeaders).not.toHaveProperty('download_url');
  expect(useHeaders).not.toHaveProperty('public_url');
  expect(useHeaders).not.toHaveProperty('signed_url');

  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'external_export_download_signed_reference_delivered',
  );
  await expect(page.locator('#external-export-download-signed-reference-use')).toBeDisabled();
  await expectNoDeferredRawMixedControls(page);
  return { signedReference, useHeaders, payload: signedPayload };
}

async function submitRenderedProviderPrivateSignedUrl(
  page,
  sessionId,
  approval,
  planPreview,
  execution,
  review,
  commit,
  packageSubmit,
  handoffPrepare,
  apsDispatch,
  downloadPrepare,
) {
  await page.locator('#theme-selector').selectOption('workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await page.locator('[data-operation-target="external-export-download-band"]').click();
  await expect(page.locator('#external-export-download-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#provider-private-signed-url-panel')).toContainText('provider_private_signed_url_ui_ready');
  await expect(page.locator('#provider-private-signed-url-prepare')).toBeEnabled();
  await expect(page.locator('#provider-private-signed-url-status')).toBeDisabled();
  await expect(page.locator('#provider-private-signed-url-revoke')).toBeDisabled();
  await expect(page.locator('#provider-private-signed-url-use')).toHaveCount(0);

  const prepareRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/handoff/export/download/provider-private-signed-url/prepare')
    && apiRequest.method() === 'POST'
  ));
  const prepareResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/handoff/export/download/provider-private-signed-url/prepare')
  ));
  await page.locator('#provider-private-signed-url-prepare').click();
  const preparePayload = (await prepareRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(preparePayload, [
    'analysis_plan_id',
    'client_request_id',
    'decision_notes',
    'delivery_mode',
    'download_mode',
    'export_download_descriptor_ref',
    'export_download_target',
    'external_export_download_record_ref',
    'external_export_download_state',
    'operator_decision',
    'pass_run_id',
    'recipient_scope',
    'reconciliation_record_id',
    'requested_ttl_seconds',
    'session_id',
    'source_artifact_hash',
    'source_artifact_size_bytes',
  ]);
  expect(preparePayload.session_id).toBe(sessionId);
  expect(preparePayload.analysis_plan_id).toBe(approval.analysis_plan_id);
  expect(preparePayload.pass_run_id).toBe(execution.selection.pass_run_ids[0]);
  expect(preparePayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(preparePayload.external_export_download_record_ref).toBe(downloadPrepare.external_export_download_record_ref);
  expect(preparePayload.export_download_descriptor_ref).toBe(downloadPrepare.export_download_descriptor_ref);
  expect(preparePayload.external_export_download_state).toBe('external_export_download_prepared');
  expect(preparePayload.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(preparePayload.download_mode).toBe('reference_only_prepare');
  expect(preparePayload.delivery_mode).toBe('provider_private_signed_url');
  expect(preparePayload.operator_decision).toBe('prepare_provider_private_signed_url');
  expect(preparePayload.source_artifact_hash).toBe(downloadPrepare.source_artifact_hash);
  expect(preparePayload.source_artifact_size_bytes).toBe(downloadPrepare.source_artifact_size_bytes);
  expect(preparePayload.recipient_scope).toBe('external_downstream_recipient_private_artifact_delivery');
  expect(preparePayload.requested_ttl_seconds).toBe(300);
  expect(preparePayload).not.toHaveProperty('provider_private_signed_url_token');
  expect(preparePayload).not.toHaveProperty('raw_provider_private_signed_url_token');
  expect(preparePayload).not.toHaveProperty('provider_url');
  expect(preparePayload).not.toHaveProperty('public_url');
  expect(preparePayload).not.toHaveProperty('connector_dispatch');
  expect(preparePayload).not.toHaveProperty('package_mutation');
  expect(preparePayload).not.toHaveProperty('source_expansion');

  const prepare = await expectJson(await prepareResponsePromise);
  expect(prepare.schema_id).toBe('layer3.provider_private_signed_url.prepare.v1');
  expect(prepare.provider_signed_url_state).toBe('provider_private_signed_url_prepared');
  expect(prepare.provider_signed_url_receipt_id).toBeTruthy();
  expect(prepare.delivery_mode).toBe('provider_private_signed_url');
  expect(prepare.provider_url_redacted).toBe('provider-private-signed-url:redacted');
  expect(prepare.provider_url_revocation_supported).toBe(true);
  expect(prepare.provider_url_revoked).toBe(false);
  expect(prepare.source_artifact_hash).toBe(downloadPrepare.source_artifact_hash);
  expect(prepare.source_artifact_size_bytes).toBe(downloadPrepare.source_artifact_size_bytes);
  expect(prepare).not.toHaveProperty('provider_private_signed_url_token');
  expect(prepare.audit_receipt || {}).not.toHaveProperty('provider_private_signed_url_token');
  expect(JSON.stringify(prepare)).not.toContain('raw_provider_private_signed_url_token');
  await expect(page.locator('#provider-private-signed-url-panel')).toContainText(prepare.provider_signed_url_receipt_id);
  await expect(page.locator('#provider-private-signed-url-panel')).toContainText('provider-private-signed-url:redacted');
  await expect(page.locator('#provider-private-signed-url-prepare')).toBeDisabled();
  await expect(page.locator('#provider-private-signed-url-status')).toBeEnabled();
  await expect(page.locator('#provider-private-signed-url-revoke')).toBeEnabled();

  const statusResponsePromise = page.waitForResponse((response) => (
    response.url().includes(`/api/v1/layer3/handoff/export/download/provider-private-signed-url/status/${prepare.provider_signed_url_receipt_id}`)
  ));
  await page.locator('#provider-private-signed-url-status').click();
  const status = await expectJson(await statusResponsePromise);
  expect(status.schema_id).toBe('layer3.provider_private_signed_url.status.v1');
  expect(status.provider_signed_url_receipt_id).toBe(prepare.provider_signed_url_receipt_id);
  expect(status.provider_signed_url_state).toBe('provider_private_signed_url_prepared');
  expect(status.provider_url_redacted).toBe('provider-private-signed-url:redacted');
  expect(status).not.toHaveProperty('provider_private_signed_url_token');
  expect(status.audit_receipt || {}).not.toHaveProperty('provider_private_signed_url_token');
  expect(JSON.stringify(status)).not.toContain('raw_provider_private_signed_url_token');

  const revokeRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/handoff/export/download/provider-private-signed-url/revoke')
    && apiRequest.method() === 'POST'
  ));
  const revokeResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/handoff/export/download/provider-private-signed-url/revoke')
  ));
  await page.locator('#provider-private-signed-url-revoke').click();
  const revokePayload = (await revokeRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(revokePayload, [
    'client_request_id',
    'decision_notes',
    'idempotency_key',
    'operator_decision',
    'provider_signed_url_receipt_id',
    'revocation_reason',
    'revoked_by',
  ]);
  expect(revokePayload.provider_signed_url_receipt_id).toBe(prepare.provider_signed_url_receipt_id);
  expect(revokePayload.operator_decision).toBe('revoke_provider_private_signed_url');
  expect(revokePayload.idempotency_key).toBe(`provider-private-revoke:${prepare.provider_signed_url_receipt_id}`);
  expect(revokePayload.revoked_by).toBe('layer3-rendered-workbench');
  expect(revokePayload).not.toHaveProperty('provider_private_signed_url_token');
  expect(revokePayload).not.toHaveProperty('raw_provider_private_signed_url_token');
  expect(revokePayload).not.toHaveProperty('provider_url');
  expect(revokePayload).not.toHaveProperty('public_url');
  expect(revokePayload).not.toHaveProperty('connector_dispatch');
  expect(revokePayload).not.toHaveProperty('package_mutation');
  expect(revokePayload).not.toHaveProperty('source_expansion');

  const revoke = await expectJson(await revokeResponsePromise);
  expect(revoke.schema_id).toBe('layer3.provider_private_signed_url.revoke.v1');
  expect(revoke.provider_signed_url_receipt_id).toBe(prepare.provider_signed_url_receipt_id);
  expect(revoke.provider_signed_url_state).toBe('provider_private_signed_url_revoked');
  expect(revoke.provider_url_redacted).toBe('provider-private-signed-url:redacted');
  expect(revoke.provider_url_revoked).toBe(true);
  expect(revoke.revocation_recorded).toBe(true);
  expect(revoke).not.toHaveProperty('provider_private_signed_url_token');
  expect(revoke.audit_receipt || {}).not.toHaveProperty('provider_private_signed_url_token');
  expect(JSON.stringify(revoke)).not.toContain('raw_provider_private_signed_url_token');
  await expect(page.locator('#provider-private-signed-url-panel')).toContainText('provider_private_signed_url_revoked');
  await expect(page.locator('#provider-private-signed-url-revoke')).toBeDisabled();

  const revokedStatusResponsePromise = page.waitForResponse((response) => (
    response.url().includes(`/api/v1/layer3/handoff/export/download/provider-private-signed-url/status/${prepare.provider_signed_url_receipt_id}`)
  ));
  await page.locator('#provider-private-signed-url-status').click();
  const revokedStatus = await expectJson(await revokedStatusResponsePromise);
  expect(revokedStatus.provider_signed_url_receipt_id).toBe(prepare.provider_signed_url_receipt_id);
  expect(revokedStatus.provider_signed_url_state).toBe('provider_private_signed_url_revoked');
  expect(revokedStatus.provider_url_redacted).toBe('provider-private-signed-url:redacted');
  await expectNoDeferredRawMixedControls(page);
  return { prepare, status, revoke, revokedStatus, preparePayload, revokePayload };
}

function qualitativeApsPackageSubmitUiFixture() {
  const sessionId = 'session-qual-aps-submit-ui';
  const analysisPlanId = 'plan-qual-aps-submit-ui';
  const passRunId = 'pass-qual-aps-submit-ui';
  const previewId = 'preview-qual-aps-submit-ui';
  const previewHash = 'preview-hash-qual-aps-submit-ui';
  const resultReviewRef = 'result-review-qual-aps-submit-ui';
  const packagePreviewHash = 'package-preview-qual-aps-submit-ui';
  const reconciliationId = 'recon-qual-aps-submit-ui';
  const constructionBasisHash = 'd'.repeat(64);
  const outputPackages = [
    {
      output_package_id: 'pkg-qual-aps-canonical-ui',
      package_kind: 'canonical_internal',
      payload_ref: 'artifact://qual-aps-canonical-ui',
      payload_hash: 'a'.repeat(64),
    },
    {
      output_package_id: 'pkg-qual-aps-user-ui',
      package_kind: 'user_facing',
      payload_ref: 'artifact://qual-aps-user-ui',
      payload_hash: 'b'.repeat(64),
    },
    {
      output_package_id: 'pkg-qual-aps-review-ui',
      package_kind: 'review_facing',
      payload_ref: 'artifact://qual-aps-review-ui',
      payload_hash: 'c'.repeat(64),
    },
  ];
  const packageKinds = outputPackages.map((pkg) => pkg.package_kind);
  const payloadRefs = outputPackages.map((pkg) => pkg.payload_ref);
  const payloadHashes = outputPackages.map((pkg) => pkg.payload_hash);
  return {
    sessionId,
    analysisPlanId,
    passRunId,
    previewId,
    previewHash,
    resultReviewRef,
    packagePreviewHash,
    reconciliationId,
    constructionBasisHash,
    packageKinds,
    payloadRefs,
    payloadHashes,
    outputPackages,
    packageSubmitResponse: {
      schema_id: 'layer3.qual_aps_package_review_submit.v1',
      status: 'submitted',
      session_id: sessionId,
      analysis_plan_id: analysisPlanId,
      pass_run_id: passRunId,
      preview_identity: { preview_id: previewId, preview_hash: previewHash },
      analysis_run_id: null,
      result_review_record_ref: resultReviewRef,
      package_review_preview_hash: packagePreviewHash,
      reconciliation_record_id: reconciliationId,
      output_package_ids: outputPackages.map((pkg) => pkg.output_package_id),
      package_kinds: packageKinds,
      payload_refs: payloadRefs,
      payload_hashes: payloadHashes,
      construction_basis_hash: constructionBasisHash,
      operator_decision: 'approved',
      decision_notes: null,
      package_review_state: 'package_review_approved',
      submit_record_ref: 'submit-qual-aps-ui',
      pass_type: 'qualitative_aps_document',
      pass_scope: 'single_aps_doc_qualitative_pass',
      method: 'qualitative_summary',
      source_gate: '119_L3_QUAL_APS_EXEC_ENTRY_FREEZE',
      source_shape: 'aps_content_document',
      package_construction_source_gate: '140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE',
      package_review_submit_enabled: false,
      handoff_enabled: false,
      export_enabled: false,
      downstream_unavailable: ['handoff', 'export', 'aps_handoff', 'external_export_download', 'connector'],
      next_state: 'package_review_approved',
    },
  };
}

async function seedQualitativeApsPackageSubmitUiState(page, fixture) {
  await page.evaluate((state) => {
    const outputPackageIds = state.outputPackages.map((pkg) => pkg.output_package_id);
    const commonAuthority = {
      session_id: state.sessionId,
      analysis_plan_id: state.analysisPlanId,
      pass_run_id: state.passRunId,
      preview_identity: {
        preview_id: state.previewId,
        preview_hash: state.previewHash,
      },
      pass_scope: 'single_aps_doc_qualitative_pass',
      selected_method_name: 'qualitative_summary',
      source_gate: '119_L3_QUAL_APS_EXEC_ENTRY_FREEZE',
      source_shape: 'aps_content_document',
    };
    State.sessionSummary = {
      session_id: state.sessionId,
      execution_selection: {
        selected: true,
        execution_started: true,
        analysis_plan_id: state.analysisPlanId,
        pass_run_ids: [state.passRunId],
        analysis_run_ids: ['analysis-run-should-not-be-sent'],
        source_preview_id: state.previewId,
        source_preview_hash: state.previewHash,
        pass_run_statuses: { [state.passRunId]: 'completed' },
      },
      analysis_execution_start: {
        pass_run_id: state.passRunId,
        analysis_plan_id: state.analysisPlanId,
        source_preview_id: state.previewId,
        source_preview_hash: state.previewHash,
        pass_run_status: 'completed',
        analysis_run_id: 'analysis-run-should-not-be-sent',
      },
      execution_result_review: {
        ...commonAuthority,
        review_state: 'execution_result_review_approved',
        operator_decision: 'approved',
        review_record_ref: state.resultReviewRef,
      },
      package_construction: {
        schema_id: 'layer3.qual_aps_package_construction_commit.v1',
        status: 'committed',
        state: 'package_constructed',
        session_id: state.sessionId,
        analysis_plan_id: state.analysisPlanId,
        pass_run_id: state.passRunId,
        preview_identity: { preview_id: state.previewId, preview_hash: state.previewHash },
        analysis_run_id: null,
        result_review_record_ref: state.resultReviewRef,
        package_review_preview_hash: state.packagePreviewHash,
        reconciliation_record_id: state.reconciliationId,
        construction_basis_hash: state.constructionBasisHash,
        output_packages: state.outputPackages,
        output_package_ids: outputPackageIds,
        package_kinds: state.packageKinds,
        payload_refs: state.payloadRefs,
        payload_hashes: state.payloadHashes,
        pass_type: 'qualitative_aps_document',
        pass_scope: 'single_aps_doc_qualitative_pass',
        method: 'qualitative_summary',
        source_gate: '119_L3_QUAL_APS_EXEC_ENTRY_FREEZE',
        source_shape: 'aps_content_document',
        package_construction_source_gate: '140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE',
        package_review_submit_enabled: true,
        handoff_enabled: false,
        downstream_unavailable: ['handoff', 'export', 'aps_handoff', 'external_export_download', 'connector'],
      },
    };
    State.resultStatus = {
      ...commonAuthority,
      analysis_run_id: null,
      result_status_available: true,
      pass_run_status: 'completed',
      output_metadata_summary: {
        readable: true,
        output_payload_ref: 'artifact://qual-aps-output-ui',
        pass_scope: 'single_aps_doc_qualitative_pass',
        source_shape: 'aps_content_document',
      },
    };
    State.resultReview = State.sessionSummary.execution_result_review;
    State.packageReviewPreview = {
      schema_id: 'layer3.qual_aps_package_review_preview.v1',
      status: 'ok',
      session_id: state.sessionId,
      analysis_plan_id: state.analysisPlanId,
      pass_run_id: state.passRunId,
      preview_identity: { preview_id: state.previewId, preview_hash: state.previewHash },
      analysis_run_id: null,
      result_review_state: 'execution_result_review_approved',
      result_review_record_ref: state.resultReviewRef,
      package_review_preview_hash: state.packagePreviewHash,
      package_review_preview_enabled: true,
      package_commit_enabled: true,
      candidate_package_kinds: state.packageKinds.map((package_kind) => ({
        package_kind,
        preview_only: true,
        package_commit_enabled: true,
      })),
    };
    State.packageConstruction = State.sessionSummary.package_construction;
    State.packageReviewSubmit = null;
    State.packageReviewSubmitError = null;
    renderAll();
  }, fixture);
}

test('Layer 3 workbench keeps Layer 3-only theme preferences page-local', async ({ page }) => {
  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    localStorage.setItem('nrc_aps_review_theme', 'workbench');
    localStorage.removeItem('layer3_workbench_theme');
  });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'system');
  await expect(page.locator('#theme-selector')).toHaveValue('system');
  const sharedAfterNrc = await page.evaluate(() => localStorage.getItem('nrc_aps_review_theme'));
  expect(sharedAfterNrc).toBeNull();

  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    localStorage.setItem('nrc_aps_review_theme', 'workbench');
    localStorage.removeItem('layer3_workbench_theme');
  });

  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await expect(page.locator('#theme-selector')).toHaveValue('workbench');

  const storage = await page.evaluate(() => ({
    sharedTheme: localStorage.getItem('nrc_aps_review_theme'),
    layer3Theme: localStorage.getItem('layer3_workbench_theme'),
  }));
  expect(storage).toEqual({
    sharedTheme: null,
    layer3Theme: 'workbench',
  });

  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'system');
  await expect(page.locator('#theme-selector')).toHaveValue('system');

  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'dark');
  const storageAfterLayer3Dark = await page.evaluate(() => ({
    sharedTheme: localStorage.getItem('nrc_aps_review_theme'),
    layer3Theme: localStorage.getItem('layer3_workbench_theme'),
  }));
  expect(storageAfterLayer3Dark).toEqual({
    sharedTheme: 'dark',
    layer3Theme: null,
  });

  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('light');
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'light');
  await expect(page.locator('#theme-selector')).toHaveValue('light');
  const storageAfterNrcLight = await page.evaluate(() => ({
    sharedTheme: localStorage.getItem('nrc_aps_review_theme'),
    layer3Theme: localStorage.getItem('layer3_workbench_theme'),
  }));
  expect(storageAfterNrcLight).toEqual({
    sharedTheme: 'light',
    layer3Theme: null,
  });

  await page.locator('#theme-selector').selectOption('workbench');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await expect(page.locator('#theme-selector')).toHaveValue('workbench');
  const storageAfterWorkbenchWithSharedTheme = await page.evaluate(() => ({
    sharedTheme: localStorage.getItem('nrc_aps_review_theme'),
    layer3Theme: localStorage.getItem('layer3_workbench_theme'),
  }));
  expect(storageAfterWorkbenchWithSharedTheme).toEqual({
    sharedTheme: 'light',
    layer3Theme: 'workbench',
  });

  await page.goto('/review/nrc-aps', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'light');
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');

  await Promise.all([
    page.waitForURL('**/review/layer3/static/claude.html'),
    page.locator('#theme-selector').selectOption('claude'),
  ]);
  await expect(page).toHaveTitle(/Layer 3 Workbench.*Prototype/);
  await expect(page.locator('.app-shell')).toBeVisible();
  await expect(page.locator('.chrome-bar')).toHaveCount(0);
  await expect(page.locator('header.app-header.layer3-header')).toBeVisible();
  await expect(page.locator('a.back-link')).toHaveAttribute('href', '/review/nrc-aps');
  await expect(page.locator('.proto-badge')).toHaveText('PROTOTYPE');
  await expect(page.locator('#theme-selector')).toHaveValue('claude');
  await page.locator('[data-screen="overview"]').click();
  await expect(page.locator('#ov-sources')).toContainText('APS content document');
  await page.locator('[data-screen="3a"]').click();
  await expect(page.locator('#detail-3a-gate')).toContainText('aps-doc-operator-evidence-001');
  await expect(page.locator('#detail-3a-gate')).toContainText('ML26001A001');
  await expect(page.locator('#detail-3a-gate')).toContainText('aps_content_units_v2');
  await expect(page.locator('#detail-3a-gate')).toContainText('traceable_aps_content_document');
  await expect(page.locator('#detail-3a-status')).toContainText('21');
  const storageAfterClaude = await page.evaluate(() => ({
    sharedTheme: localStorage.getItem('nrc_aps_review_theme'),
    layer3Theme: localStorage.getItem('layer3_workbench_theme'),
  }));
  expect(storageAfterClaude).toEqual({
    sharedTheme: 'light',
    layer3Theme: 'workbench',
  });

  await Promise.all([
    page.waitForURL('**/review/layer3'),
    page.locator('#theme-selector').selectOption('workbench'),
  ]);
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await expect(page.locator('#theme-selector')).toHaveValue('workbench');

  await page.locator('#theme-selector').selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'dark');
});

test('Layer 3 workbench clears schema-id-only Gate B drafts after contract signature hardening', async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('layer3_workbench_gate_b_draft_v1', JSON.stringify({
      schema_id: 'layer3.gate_b_draft_snapshot.v1',
      schema_version: 1,
      draft_authority: 'browser_restore_only_server_revalidated_on_commit',
      client_request_id: 'stale-schema-id-only-draft',
      state_action_contract_schema_id: 'layer3.state_action_contract.v1',
      expires_at: new Date(Date.now() + (60 * 60 * 1000)).toISOString(),
      material_preview_id: 'stale-material-preview',
      material_preview_hash: 'stale-hash',
      candidate_ids: ['stale-candidate'],
      material_preview: {
        material_preview_id: 'stale-material-preview',
        material_preview_hash: 'stale-hash',
        material_candidates: [{ candidate_id: 'stale-candidate' }],
      },
    }));
  });

  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

  await expect.poll(() => page.evaluate(() => (
    sessionStorage.getItem('layer3_workbench_gate_b_draft_v1')
  ))).toBeNull();
});

test('Layer 3 workbench restores Gate B drafts and server session anchors across reloads', async ({ page }) => {
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });

  const materialResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/material-preview')
  ));
  await page.locator('#layer3-intent').fill('Protect Gate B draft and recover server session.');
  await page.locator('#run-preflight').click();
  const material = await expectJson(await materialResponsePromise);
  expect(material.material_candidates.length).toBeGreaterThan(1);

  const rows = page.locator('#material-ledger-body tr[data-candidate-id]');
  await rows.nth(1).locator('.decision-select').selectOption('denied');
  await rows.nth(1).locator('.reason-input').fill('Reload recovery draft proof.');

  const draftBeforeReload = await page.evaluate(() => JSON.parse(
    sessionStorage.getItem('layer3_workbench_gate_b_draft_v1'),
  ));
  expect(draftBeforeReload.schema_id).toBe('layer3.gate_b_draft_snapshot.v1');
  expect(draftBeforeReload.draft_authority).toBe('browser_restore_only_server_revalidated_on_commit');
  expect(draftBeforeReload.state_action_contract_schema_id).toBe('layer3.state_action_contract.v1');
  expect(draftBeforeReload.state_action_contract_signature).toContain('"schema_id":"layer3.state_action_contract.v1"');
  expect(draftBeforeReload.material_preview_hash).toBe(material.material_preview_hash);
  expect(draftBeforeReload.client_request_id).toBeTruthy();

  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]')).toHaveCount(material.material_candidates.length);
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]').nth(1).locator('.decision-select')).toHaveValue('denied');
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]').nth(1).locator('.reason-input')).toHaveValue('Reload recovery draft proof.');

  const gateBRequestPromise = page.waitForRequest((request) => (
    request.url().includes('/api/v1/layer3/gate-b/decision') && request.method() === 'POST'
  ));
  const gateBResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/gate-b/decision')
  ));
  await page.locator('#gate-b-submit').click();
  const gateBRequest = await gateBRequestPromise;
  const gateBPayload = gateBRequest.postDataJSON();
  expect(gateBPayload.client_request_id).toBe(draftBeforeReload.client_request_id);
  expect(gateBPayload.material_preview_hash).toBe(material.material_preview_hash);
  const gateB = await expectJson(await gateBResponsePromise);
  expect(gateB.status).toBe('ok');

  const storageAfterCommit = await page.evaluate(() => ({
    draft: sessionStorage.getItem('layer3_workbench_gate_b_draft_v1'),
    recovery: JSON.parse(localStorage.getItem('layer3_workbench_session_recovery_v1')),
  }));
  expect(storageAfterCommit.draft).toBeNull();
  expect(storageAfterCommit.recovery.schema_id).toBe('layer3.browser_session_recovery.v1');
  expect(storageAfterCommit.recovery.session_id).toBe(gateB.session_id);
  expect(storageAfterCommit.recovery.state_action_contract_schema_id).toBe('layer3.state_action_contract.v1');
  expect(storageAfterCommit.recovery.state_action_contract_signature).toContain('"schema_id":"layer3.state_action_contract.v1"');

  const sessionResponsePromise = page.waitForResponse((response) => (
    response.url().includes(`/api/v1/layer3/session/${gateB.session_id}`)
  ));
  await page.reload({ waitUntil: 'domcontentloaded' });
  const session = await expectJson(await sessionResponsePromise);
  expect(session.session_id).toBe(gateB.session_id);
  await expect(page.locator('#authority-rail')).toContainText(gateB.session_id);
  await expect(page.locator('#gate-c-preview')).toBeEnabled();
});

test('Layer 3 workbench keeps page-level scrolling and step navigation across viewports', async ({ page }) => {
  const stepTargets = [
    ['intent', 'intent-band'],
    ['sources', 'source-fieldset'],
    ['gate_b', 'gate-b-band'],
    ['gate_c', 'gate-c-band'],
    ['plan', 'plan-band'],
    ['execution', 'result-review-band'],
    ['results', 'result-review-band'],
    ['package', 'package-review-band'],
    ['handoff', 'handoff-export-band'],
  ];

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Layer 3 Workbench' })).toBeVisible();

    const scrollState = await page.evaluate(() => {
      const bodyStyle = window.getComputedStyle(document.body);
      const contextStyle = window.getComputedStyle(document.querySelector('.context-panel'));
      return {
        bodyOverflowY: bodyStyle.overflowY,
        contextOverflow: contextStyle.overflow,
        pageCanScroll: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight) > window.innerHeight,
        pageFitsViewportWidth: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      };
    });
    expect(scrollState).toEqual({
      bodyOverflowY: 'auto',
      contextOverflow: 'visible',
      pageCanScroll: true,
      pageFitsViewportWidth: true,
    });

    for (const [step, targetId] of stepTargets) {
      const chip = page.locator(`[data-step="${step}"]`);
      await expect(chip).toBeEnabled();
      await chip.click();
      await expect(chip).toHaveAttribute('aria-current', 'step');
      await expect(page.locator(`#${targetId}`)).toBeVisible();
    }
  }
});

test('Layer 3 workbench surfaces typed and deferred APS source-family guardrails', async ({ page }) => {
  const candidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  const candidates = await expectJson(await candidatesResponsePromise);

  expect(candidates.source_family_summary.selection_shape).toBe('dataset_version');
  expect(
    candidates.source_family_summary.admitted_materialized_families.map((family) => family.parser_family),
  ).toEqual(expect.arrayContaining([
    'csv_table',
    'xlsx_workbook',
    'json_recordset',
    'sec_edgar_filing',
  ]));
  expect(
    candidates.source_family_summary.not_admitted_or_deferred_families.map((family) => family.source_family),
  ).toEqual(expect.arrayContaining([
    'xml_html_inline_xbrl',
    'broad_workbook_semantics',
    'archive_member_table_or_filing_orchestration',
    'mixed_source_package_semantics',
  ]));

  const summary = page.locator('.source-family-summary');
  await expect(summary).toContainText('Server-backed typed families');
  await expect(summary).toContainText('CSV table');
  await expect(summary).toContainText('XLSX workbook table');
  await expect(summary).toContainText('JSON recordset');
  await expect(summary).toContainText('SEC/EDGAR text table');
  await expect(summary).toContainText('Deferred / refused guardrails');
  await expect(summary).toContainText('XML/HTML/inline XBRL');
  await expect(summary).toContainText(
    'This endpoint surfaces server-backed materialized DatasetVersion choices only; refused/deferred families are explanatory guardrails, not selectable source classes.',
  );
});

test('Layer 3 workbench uses raw mixed seed bridge setup for rendered material review', async ({ page, request }) => {
  const seed = await seedRawMixedBridgeSetup(request);

  const datasetCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  const apsCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/aps-content-document-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  const datasetCandidates = await expectJson(await datasetCandidatesResponsePromise);
  const apsCandidates = await expectJson(await apsCandidatesResponsePromise);

  expect(datasetCandidates.dataset_version_candidates.map((candidate) => candidate.dataset_version_id)).toEqual(
    expect.arrayContaining(seed.dataset_version_ids),
  );
  expect(apsCandidates.aps_content_document_candidates.map((candidate) => candidate.content_id)).toEqual(
    expect.arrayContaining(seed.aps_content_document_ids),
  );
  await expectNoDeferredRawMixedControls(page);
  await selectSeededSources(page, seed);

  const preflightResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/preflight')
  ));
  const sourceResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/source-preview')
  ));
  const materialResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/material-preview')
  ));
  await page.locator('#layer3-intent').fill('Review raw mixed seed bridge setup through rendered Layer 3 material preview.');
  await page.locator('#run-preflight').click();
  const preflight = await expectJson(await preflightResponsePromise);
  const source = await expectJson(await sourceResponsePromise);
  const material = await expectJson(await materialResponsePromise);

  expect(preflight.preflight_id).toBeTruthy();
  expect(source.source_candidates.map((candidate) => candidate.source_class).sort()).toEqual([
    'aps_content_document',
    'dataset_version',
  ]);
  expectMaterialPreviewContainsSeededSources(material, seed);
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]')).toHaveCount(3);
  for (const contentId of seed.aps_content_document_ids) {
    await expect(page.locator('#material-ledger-body')).toContainText(contentId);
  }
  await expectNoDeferredRawMixedControls(page);

  const gateBRequestPromise = page.waitForRequest((gateBRequest) => (
    gateBRequest.url().includes('/api/v1/layer3/gate-b/decision') && gateBRequest.method() === 'POST'
  ));
  const gateBResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/gate-b/decision')
  ));
  await page.locator('#gate-b-submit').click();
  const gateBRequest = await gateBRequestPromise;
  const gateBPayload = gateBRequest.postDataJSON();
  expect(gateBPayload.material_preview_hash).toBe(material.material_preview_hash);
  expect(gateBPayload.candidate_decisions).toHaveLength(3);
  expect(gateBPayload).not.toHaveProperty('local_upload');
  expect(gateBPayload).not.toHaveProperty('local_directory');
  expect(gateBPayload).not.toHaveProperty('rag_plan');
  expect(gateBPayload).not.toHaveProperty('provider_url');
  expect(gateBPayload).not.toHaveProperty('public_url');
  expect(gateBPayload).not.toHaveProperty('connector_dispatch');
  const gateB = await expectJson(await gateBResponsePromise);
  expect(gateB.status).toBe('ok');
  expect(gateB.approved_candidate_ids).toHaveLength(3);
  await expect(page.locator('#gate-c-preview')).toBeEnabled();
  await expectNoDeferredRawMixedControls(page);
});

test('Layer 3 workbench uses raw mixed seed bridge setup through rendered Gate C and plan approval', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const seed = await openRawMixedSeededWorkbench(page, request);
  const { material } = await runRawMixedRenderedMaterialPreview(page, seed);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, seed);
  await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
});

test('Layer 3 workbench uses raw mixed materialization setup through rendered Gate C and plan approval', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const materialization = await openRawMixedMaterializedWorkbench(page, request);
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
});

test('Layer 3 workbench materializes raw mixed manifest through rendered controls', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const initialDatasetCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  const initialApsCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/aps-content-document-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await initialDatasetCandidatesResponsePromise);
  await expectJson(await initialApsCandidatesResponsePromise);
  await page.locator('#theme-selector').selectOption('workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'workbench');
  await expect(page.locator('.raw-mixed-materialization')).toBeVisible();
  await expect(page.locator('#raw-mixed-materialization-status')).toContainText('Awaiting server-owned manifest authority');
  await page.locator('#theme-selector').selectOption('light');
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'light');
  await expect(page.locator('#raw-mixed-materialize')).toBeDisabled();

  const materialization = await materializeRawMixedThroughRenderedControls(page, request);
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
});

test('Layer 3 workbench fail-closes raw mixed rendered materialization review guards', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const preselectedSeed = await seedRawMixedBridgeSetup(request);
  const setup = await expectJson(await request.post('/__test/layer3/materialize-raw-mixed'));
  const materializeRequest = setup.materialize_request;
  const initialDatasetCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  const initialApsCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/aps-content-document-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await initialDatasetCandidatesResponsePromise);
  await expectJson(await initialApsCandidatesResponsePromise);
  await selectSeededSources(page, preselectedSeed);

  await page.locator('#raw-mixed-corpus-batch-id').fill(materializeRequest.corpus_batch_id);
  await page.locator('#raw-mixed-manifest-ref').fill(materializeRequest.artifact_manifest_ref);
  await page.locator('#raw-mixed-manifest-hash').fill(materializeRequest.artifact_manifest_hash);
  await page.locator('#raw-mixed-operator-confirmation').check();
  await expect(page.locator('#raw-mixed-materialize')).toBeEnabled();

  await page.locator('input[name="source-class"][value="aps_content_document"]').uncheck();
  await expect(page.locator('#raw-mixed-materialize')).toBeDisabled();
  await expect(page.locator('#raw-mixed-materialization-status')).toContainText(
    'Select both Dataset version and APS content document source classes.',
  );
  await page.locator('#raw-mixed-manifest-ref').press('Enter');
  await page.waitForTimeout(100);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, ['/preflight']);

  await page.locator('input[name="source-class"][value="aps_content_document"]').check();
  await expect(page.locator('#raw-mixed-materialize')).toBeEnabled();
  await page.route('**/api/v1/layer3/dataset-version-candidates', (route) => route.abort());
  const failedMaterializeResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/source/mixed-corpus/materialize')
    && response.request().method() === 'POST'
  ));
  await page.locator('#raw-mixed-materialize').click();
  await expectJson(await failedMaterializeResponsePromise);
  await expect(page.locator('#raw-mixed-materialization-state')).toHaveText('Blocked');
  await expect(page.locator('#raw-mixed-materialization-status')).toContainText('candidate refresh failed');
  await expect(page.locator('#dataset-version-ids')).toHaveValue('');
  await expect(page.locator('#aps-content-document-ids')).toHaveValue('');
  await page.unroute('**/api/v1/layer3/dataset-version-candidates');

  const materializeRequestPromise = page.waitForRequest((apiRequest) => (
    apiRequest.url().includes('/api/v1/layer3/source/mixed-corpus/materialize')
    && apiRequest.method() === 'POST'
  ));
  const materializeResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/source/mixed-corpus/materialize')
    && response.request().method() === 'POST'
  ));
  const datasetCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  const apsCandidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/aps-content-document-candidates')
  ));
  await page.locator('#raw-mixed-materialize').click();
  const requestPayload = (await materializeRequestPromise).postDataJSON();
  expect(requestPayload.requested_source_classes).toEqual(['dataset_version', 'aps_content_document']);
  const materialization = await expectJson(await materializeResponsePromise);
  await expectJson(await datasetCandidatesResponsePromise);
  await expectJson(await apsCandidatesResponsePromise);
  await expect(page.locator('#raw-mixed-materialization-state')).toHaveText('Materialized');
  await expect(page.locator('#dataset-version-ids')).toHaveValue(materialization.dataset_version_ids.join('\n'));
  await expect(page.locator('#aps-content-document-ids')).toHaveValue(materialization.aps_content_document_ids.join('\n'));
  for (const datasetVersionId of preselectedSeed.dataset_version_ids) {
    await expect(page.locator(`input[name="dataset-version-candidate"][value="${datasetVersionId}"]`)).not.toBeChecked();
  }
  for (const contentId of preselectedSeed.aps_content_document_ids) {
    await expect(page.locator(`input[name="aps-content-document-candidate"][value="${contentId}"]`)).not.toBeChecked();
  }

  await page.locator('#raw-mixed-manifest-hash').fill(`${materializeRequest.artifact_manifest_hash}0`);
  await expect(page.locator('#raw-mixed-materialization-state')).toHaveText('Ready');
  await expect(page.locator('#raw-mixed-materialization-status')).toContainText('Ready to call the server-owned materialization route.');
  await expect(page.locator('#dataset-version-ids')).toHaveValue('');
  await expect(page.locator('#aps-content-document-ids')).toHaveValue('');
  expectNoRequestsToLayer3Paths(layer3ApiRequests, ['/preflight']);
  await expectNoDeferredRawMixedControls(page);
});

test('Layer 3 workbench drives raw mixed rendered execution selection and start', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const materialization = await openRawMixedMaterializedWorkbench(page, request);
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  const approval = await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
  const execution = await selectAndStartRenderedExecution(page, gateB.session_id, approval, planPreview);
  await inspectRenderedResultStatus(page, gateB.session_id, approval, planPreview, execution);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, [
    '/execution/result/review',
    '/package/review/',
    '/handoff/',
  ]);
});

test('Layer 3 workbench drives raw mixed rendered result-review submit', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const materialization = await openRawMixedMaterializedWorkbench(page, request);
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  const approval = await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
  const execution = await selectAndStartRenderedExecution(page, gateB.session_id, approval, planPreview);
  const status = await inspectRenderedResultStatus(page, gateB.session_id, approval, planPreview, execution);
  const review = await submitRenderedResultReview(page, gateB.session_id, approval, planPreview, execution, status);
  expect(review.review_state).toContain('changes_requested');
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/execution/result/review'))).toHaveLength(1);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, [
    '/package/review/',
    '/handoff/',
  ]);
});

test('Layer 3 workbench drives raw mixed rendered package-review preview commit and submit', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const materialization = await openRawMixedMaterializedWorkbench(page, request);
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  const approval = await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
  const execution = await selectAndStartRenderedExecution(page, gateB.session_id, approval, planPreview);
  const status = await inspectRenderedResultStatus(page, gateB.session_id, approval, planPreview, execution);
  const review = await submitRenderedResultReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    status,
    {
      operatorDecision: 'approved',
      reviewNotes: 'Raw mixed rendered result review approves package-review inspection.',
      packageReviewEnabled: true,
    },
  );
  const packagePreview = await inspectRenderedPackagePreview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
  );
  const commit = await commitRenderedPackageConstruction(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    packagePreview,
  );
  const packageSubmit = await submitRenderedPackageReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
  );

  expect(review.review_state).toBe('execution_result_review_approved');
  expect(packageSubmit.package_review_state).toBe('package_review_approved');
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/execution/result/review'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/preview'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/commit'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/submit'))).toHaveLength(1);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, [
    '/handoff/',
    '/package/mutation',
    '/package/replacement',
    '/package/supersession',
  ]);
});

test('Layer 3 workbench drives raw mixed rendered handoff export prepare', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const materialization = await openRawMixedMaterializedWorkbench(page, request);
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  const approval = await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
  const execution = await selectAndStartRenderedExecution(page, gateB.session_id, approval, planPreview);
  const status = await inspectRenderedResultStatus(page, gateB.session_id, approval, planPreview, execution);
  const review = await submitRenderedResultReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    status,
    {
      operatorDecision: 'approved',
      reviewNotes: 'Raw mixed rendered result review approves handoff/export preparation.',
      packageReviewEnabled: true,
    },
  );
  const packagePreview = await inspectRenderedPackagePreview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
  );
  const commit = await commitRenderedPackageConstruction(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    packagePreview,
  );
  const packageSubmit = await submitRenderedPackageReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
  );
  const handoffPrepare = await submitRenderedHandoffExportPrepare(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
  );

  expect(review.review_state).toBe('execution_result_review_approved');
  expect(packageSubmit.package_review_state).toBe('package_review_approved');
  expect(handoffPrepare.handoff_export_state).toBe('handoff_export_prepared');
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/execution/result/review'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/preview'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/commit'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/submit'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/prepare'))).toHaveLength(1);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, [
    '/handoff/aps/dispatch',
    '/handoff/export/download',
    '/package/mutation',
    '/package/replacement',
    '/package/supersession',
  ]);
});

test('Layer 3 workbench drives raw mixed rendered APS handoff dispatch', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const materialization = await openRawMixedMaterializedWorkbench(page, request);
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  const approval = await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
  const execution = await selectAndStartRenderedExecution(page, gateB.session_id, approval, planPreview);
  const status = await inspectRenderedResultStatus(page, gateB.session_id, approval, planPreview, execution);
  const review = await submitRenderedResultReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    status,
    {
      operatorDecision: 'approved',
      reviewNotes: 'Raw mixed rendered result review approves APS handoff dispatch.',
      packageReviewEnabled: true,
    },
  );
  const packagePreview = await inspectRenderedPackagePreview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
  );
  const commit = await commitRenderedPackageConstruction(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    packagePreview,
  );
  const packageSubmit = await submitRenderedPackageReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
  );
  const handoffPrepare = await submitRenderedHandoffExportPrepare(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
  );
  const apsDispatch = await submitRenderedApsHandoffDispatch(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
  );

  expect(handoffPrepare.handoff_export_state).toBe('handoff_export_prepared');
  expect(apsDispatch.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/execution/result/review'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/preview'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/commit'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/submit'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/prepare'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/aps/dispatch'))).toHaveLength(1);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, [
    '/handoff/export/download',
    '/package/mutation',
    '/package/replacement',
    '/package/supersession',
  ]);
});

test('Layer 3 workbench drives raw mixed rendered external export download prepare', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const materialization = await openRawMixedMaterializedWorkbench(page, request);
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  const approval = await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
  const execution = await selectAndStartRenderedExecution(page, gateB.session_id, approval, planPreview);
  const status = await inspectRenderedResultStatus(page, gateB.session_id, approval, planPreview, execution);
  const review = await submitRenderedResultReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    status,
    {
      operatorDecision: 'approved',
      reviewNotes: 'Raw mixed rendered result review approves external export/download readiness.',
      packageReviewEnabled: true,
    },
  );
  const packagePreview = await inspectRenderedPackagePreview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
  );
  const commit = await commitRenderedPackageConstruction(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    packagePreview,
  );
  const packageSubmit = await submitRenderedPackageReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
  );
  const handoffPrepare = await submitRenderedHandoffExportPrepare(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
  );
  const apsDispatch = await submitRenderedApsHandoffDispatch(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
  );
  const downloadPrepare = await submitRenderedExternalExportDownloadPrepare(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
    apsDispatch,
  );

  expect(apsDispatch.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(downloadPrepare.external_export_download_state).toBe('external_export_download_prepared');
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/execution/result/review'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/preview'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/commit'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/package/review/submit'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/prepare'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/aps/dispatch'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/download/prepare'))).toHaveLength(1);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, [
    '/handoff/export/download/deliver',
    '/handoff/export/download/signed-reference',
    '/package/mutation',
    '/package/replacement',
    '/package/supersession',
  ]);
});

test('Layer 3 workbench drives raw mixed rendered external export download delivery', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const materialization = await openRawMixedMaterializedWorkbench(page, request);
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  const approval = await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
  const execution = await selectAndStartRenderedExecution(page, gateB.session_id, approval, planPreview);
  const status = await inspectRenderedResultStatus(page, gateB.session_id, approval, planPreview, execution);
  const review = await submitRenderedResultReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    status,
    {
      operatorDecision: 'approved',
      reviewNotes: 'Raw mixed rendered result review approves same-origin external delivery.',
      packageReviewEnabled: true,
    },
  );
  const packagePreview = await inspectRenderedPackagePreview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
  );
  const commit = await commitRenderedPackageConstruction(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    packagePreview,
  );
  const packageSubmit = await submitRenderedPackageReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
  );
  const handoffPrepare = await submitRenderedHandoffExportPrepare(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
  );
  const apsDispatch = await submitRenderedApsHandoffDispatch(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
  );
  const downloadPrepare = await submitRenderedExternalExportDownloadPrepare(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
    apsDispatch,
  );
  const delivery = await submitRenderedExternalExportDownloadDelivery(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
    apsDispatch,
    downloadPrepare,
  );

  expect(downloadPrepare.external_export_download_state).toBe('external_export_download_prepared');
  expect(delivery.headers['x-layer3-delivery-state']).toBe('external_export_download_delivered');
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/download/prepare'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/download/deliver'))).toHaveLength(1);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, [
    '/handoff/export/download/signed-reference',
    '/package/mutation',
    '/package/replacement',
    '/package/supersession',
    '/handoff/connector',
  ]);
});

test('Layer 3 workbench drives raw mixed rendered external export download signed reference', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const materialization = await openRawMixedMaterializedWorkbench(page, request);
  await expectLiveThemeParityCheckpoint(page, 'materialized-source-selection', '#source-fieldset');
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  const approval = await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
  const execution = await selectAndStartRenderedExecution(page, gateB.session_id, approval, planPreview);
  const status = await inspectRenderedResultStatus(page, gateB.session_id, approval, planPreview, execution);
  const review = await submitRenderedResultReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    status,
    {
      operatorDecision: 'approved',
      reviewNotes: 'Raw mixed rendered result review approves signed-reference delivery proof.',
      packageReviewEnabled: true,
    },
  );
  const packagePreview = await inspectRenderedPackagePreview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
  );
  const commit = await commitRenderedPackageConstruction(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    packagePreview,
  );
  const packageSubmit = await submitRenderedPackageReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
  );
  const handoffPrepare = await submitRenderedHandoffExportPrepare(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
  );
  const apsDispatch = await submitRenderedApsHandoffDispatch(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
  );
  const downloadPrepare = await submitRenderedExternalExportDownloadPrepare(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
    apsDispatch,
  );
  const signed = await submitRenderedExternalExportDownloadSignedReference(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
    apsDispatch,
    downloadPrepare,
  );

  expect(signed.signedReference.signed_reference_state).toBe('external_export_download_signed_reference_ready');
  expect(signed.useHeaders['x-layer3-signed-reference-state']).toBe(
    'external_export_download_signed_reference_delivered',
  );
  await expectLiveThemeParityCheckpoint(
    page,
    'signed-reference-delivered',
    '#external-export-download-signed-reference-panel',
  );
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/download/prepare'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/download/signed-reference/generate'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/download/signed-reference/use'))).toHaveLength(1);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, [
    '/handoff/export/download/deliver',
    '/package/mutation',
    '/package/replacement',
    '/package/supersession',
    '/handoff/connector',
  ]);
});

test('Layer 3 workbench drives raw mixed rendered provider-private signed URL prepare status revoke', async ({ page, request }) => {
  const layer3ApiRequests = trackLayer3ApiRequests(page);
  const materialization = await openRawMixedMaterializedWorkbench(page, request);
  await expectLiveThemeParityCheckpoint(page, 'materialized-source-selection', '#source-fieldset');
  const { material } = await runRawMixedRenderedMaterialPreview(page, materialization);
  const gateB = await submitRenderedGateB(page, material);
  await previewRenderedGateC(page, gateB.session_id);
  await commitRenderedGateC(page, gateB.session_id);
  const planPreview = await previewRenderedPlan(page, gateB.session_id, materialization);
  const approval = await approveRenderedPlan(page, gateB.session_id, planPreview);
  await assertRenderedPlanApprovalStopsBeforeExecution(page, gateB.session_id, layer3ApiRequests);
  const execution = await selectAndStartRenderedExecution(page, gateB.session_id, approval, planPreview);
  const status = await inspectRenderedResultStatus(page, gateB.session_id, approval, planPreview, execution);
  const review = await submitRenderedResultReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    status,
    {
      operatorDecision: 'approved',
      reviewNotes: 'Raw mixed rendered result review approved for provider-private signed URL proof.',
      packageReviewEnabled: true,
    },
  );
  const preview = await inspectRenderedPackagePreview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
  );
  const commit = await commitRenderedPackageConstruction(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    preview,
  );
  const packageSubmit = await submitRenderedPackageReview(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
  );
  const handoffPrepare = await submitRenderedHandoffExportPrepare(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
  );
  const apsDispatch = await submitRenderedApsHandoffDispatch(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
  );
  const downloadPrepare = await submitRenderedExternalExportDownloadPrepare(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
    apsDispatch,
  );
  const providerPrivate = await submitRenderedProviderPrivateSignedUrl(
    page,
    gateB.session_id,
    approval,
    planPreview,
    execution,
    review,
    commit,
    packageSubmit,
    handoffPrepare,
    apsDispatch,
    downloadPrepare,
  );

  expect(providerPrivate.prepare.provider_signed_url_state).toBe('provider_private_signed_url_prepared');
  expect(providerPrivate.status.provider_signed_url_state).toBe('provider_private_signed_url_prepared');
  expect(providerPrivate.revoke.provider_signed_url_state).toBe('provider_private_signed_url_revoked');
  expect(providerPrivate.revokedStatus.provider_signed_url_state).toBe('provider_private_signed_url_revoked');
  await expectLiveThemeParityCheckpoint(
    page,
    'provider-private-signed-url-revoked',
    '#provider-private-signed-url-panel',
  );
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/download/provider-private-signed-url/prepare'))).toHaveLength(1);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/download/provider-private-signed-url/status'))).toHaveLength(2);
  expect(layer3ApiRequests.filter((apiRequest) => apiRequest.path.includes('/handoff/export/download/provider-private-signed-url/revoke'))).toHaveLength(1);
  expectNoRequestsToLayer3Paths(layer3ApiRequests, [
    '/handoff/export/download/provider-private-signed-url/use',
    '/package/mutation',
    '/package/replacement',
    '/package/supersession',
    '/handoff/connector',
  ]);
});

test('Layer 3 workbench renders selected APS DatasetVersion trace detail from material preview', async ({ page, request }) => {
  const seed = await expectJson(await request.post('/__test/layer3/seed-aps-dataset'));
  const candidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/dataset-version-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  const candidates = await expectJson(await candidatesResponsePromise);
  expect(candidates.dataset_version_candidates.map((candidate) => candidate.dataset_version_id)).toContain(
    seed.dataset_version_id,
  );

  await page.locator(`input[name="dataset-version-candidate"][value="${seed.dataset_version_id}"]`).check();
  await page.locator('input[name="source-class"][value="aps_content_document"]').uncheck();
  const materialResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/material-preview')
  ));
  await page.locator('#layer3-intent').fill('Review selected APS-derived dataset trace detail.');
  await page.locator('#run-preflight').click();
  const material = await expectJson(await materialResponsePromise);
  const materialCandidate = material.material_candidates.find((candidate) => (
    candidate.payload?.dataset_version_id === seed.dataset_version_id
  ));
  expect(materialCandidate).toBeTruthy();
  expect(materialCandidate.source_trace.trace_readiness).toBe('traceable_aps_dataset_version');
  expect(materialCandidate.source_trace.aps_trace_refs.typed_content_contract_id).toBe('aps_csv_table_units_v1');

  const row = page.locator('#material-ledger-body tr[data-candidate-id]');
  await expect(row).toHaveCount(1);
  const trace = row.locator('.material-trace-card');
  await expect(trace).toContainText('CSV table');
  await expect(trace).toContainText('traceable_aps_dataset_version');
  await expect(trace).toContainText('csv_table');
  await expect(trace).toContainText('aps_csv_table_units_v1');
  await expect(trace).toContainText('ML26001A777');

  await page.locator('#material-filter').fill('aps_csv_table_units_v1');
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]')).toHaveCount(1);
});

test('Layer 3 workbench renders selected APS content document trace detail from material preview', async ({ page, request }) => {
  const seed = await expectJson(await request.post('/__test/layer3/seed-aps-document'));
  const candidatesResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/aps-content-document-candidates')
  ));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  const candidates = await expectJson(await candidatesResponsePromise);
  expect(candidates.aps_content_document_candidates.map((candidate) => candidate.content_id)).toContain(
    seed.content_id,
  );

  await page.locator(`input[name="aps-content-document-candidate"][value="${seed.content_id}"]`).check();
  await page.locator('input[name="source-class"][value="dataset_version"]').uncheck();
  const materialResponsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/material-preview')
  ));
  await page.locator('#layer3-intent').fill('Review selected APS content document trace detail.');
  await page.locator('#run-preflight').click();
  const material = await expectJson(await materialResponsePromise);
  const materialCandidate = material.material_candidates.find((candidate) => (
    candidate.payload?.content_id === seed.content_id
  ));
  expect(materialCandidate).toBeTruthy();
  expect(materialCandidate.source_trace.trace_readiness).toBe('traceable_aps_content_document');
  expect(materialCandidate.source_trace.aps_trace_refs.content_units_ref).toContain('_content_units.json');

  const row = page.locator('#material-ledger-body tr[data-candidate-id]');
  await expect(row).toHaveCount(1);
  const trace = row.locator('.material-trace-card');
  await expect(trace).toContainText('APS content document');
  await expect(trace).toContainText('traceable_aps_content_document');
  await expect(trace).toContainText(seed.content_id);
  await expect(trace).toContainText('aps_content_units_v2');
  await expect(trace).toContainText('ML26001A001');

  await page.locator('#material-filter').fill(seed.content_id);
  await expect(page.locator('#material-ledger-body tr[data-candidate-id]')).toHaveCount(1);
});

test('Layer 3 workbench exposes visible keyboard focus across themes', async ({ page }) => {
  for (const theme of ['light', 'dark', 'workbench']) {
    await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
    await page.locator('#theme-selector').selectOption(theme);
    await page.reload({ waitUntil: 'domcontentloaded' });

    await page.keyboard.press('Tab');
    await expect(page.locator('a.back-link')).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(page.locator('#theme-selector')).toBeFocused();
    await page.keyboard.press('Tab');

    const intentChip = page.locator('[data-step="intent"]');
    await expect(intentChip).toBeFocused();
    await expect(intentChip).toHaveAttribute('aria-current', 'step');
    const chipFocusStyle = await intentChip.evaluate((element) => {
      const style = window.getComputedStyle(element);
      return {
        outlineStyle: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        outlineColor: style.outlineColor,
        borderColor: style.borderColor,
      };
    });
    expect(chipFocusStyle.outlineStyle).toBe('solid');
    expect(chipFocusStyle.outlineWidth).toBe('3px');

    const gateCChip = page.locator('[data-step="gate_c"]');
    await gateCChip.focus();
    await page.keyboard.press('Enter');
    await expect(gateCChip).toHaveAttribute('aria-current', 'step');
    await expect(page.locator('#gate-c-band')).toBeFocused();
    const targetFocusStyle = await page.locator('#gate-c-band').evaluate((element) => {
      const style = window.getComputedStyle(element);
      return {
        outlineStyle: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        boxShadow: style.boxShadow,
      };
    });
    expect(targetFocusStyle.outlineStyle).toBe('solid');
    expect(targetFocusStyle.outlineWidth).toBe('3px');
    expect(targetFocusStyle.boxShadow).not.toBe('none');
  }
});

test('Layer 3 workbench requires explicit associated-cohort delivery UI server authority', async ({ page }) => {
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    const authorityRail = {
      session_id: 'session-cohort-delivery-ui',
      current_gate: 'package',
      persistence_mode: 'durable_external_export_download_prepare',
      source_authority: { source_classes: ['dataset_version'] },
      downstream_unavailable: ['public_url', 'signed_url', 'connector_dispatch'],
    };
    const packageIds = ['pkg-canonical', 'pkg-user', 'pkg-review'];
    const packageKinds = ['canonical_internal', 'user_facing', 'review_facing'];
    const payloadRefs = ['payload-canonical', 'payload-user', 'payload-review'];
    const payloadHashes = ['hash-canonical', 'hash-user', 'hash-review'];
    const external = {
      schema_id: 'layer3.external_export_download_prepare_state.v1',
      state: 'external_export_download_prepared',
      external_export_download_state: 'external_export_download_prepared',
      external_export_download_record_ref: 'readiness-ref',
      export_download_descriptor_ref: 'descriptor-ref',
      result_review_record_ref: 'review-ref',
      package_review_preview_hash: 'package-preview-hash',
      reconciliation_record_id: 'reconciliation-id',
      output_package_ids: packageIds,
      package_kinds: packageKinds,
      payload_refs: payloadRefs,
      payload_hashes: payloadHashes,
      package_review_submit_record_ref: 'submit-ref',
      package_review_state: 'package_review_approved',
      prepare_record_ref: 'prepare-ref',
      handoff_export_state: 'handoff_export_prepared',
      handoff_export_envelope_ref: 'envelope-ref',
      handoff_target: 'internal_export_envelope',
      export_mode: 'prepare_only',
      aps_handoff_record_ref: 'aps-record-ref',
      aps_handoff_state: 'aps_handoff_dispatched',
      aps_handoff_target: 'aps_evidence_bundle',
      dispatch_mode: 'server_side_aps_handoff',
      aps_output_package_id: 'aps-package-id',
      aps_output_package_kind: 'aps_evidence_bundle_handoff',
      aps_bundle_ref: 'aps-bundle-ref',
      aps_bundle_id: 'aps-bundle-id',
      aps_schema_id: 'aps.evidence_bundle.v2',
      source_artifact_hash: 'source-artifact-hash',
      source_artifact_size_bytes: 123,
      export_download_target: 'aps_evidence_bundle_download_reference',
      download_mode: 'reference_only_prepare',
      pass_type: 'associated_cohort',
      pass_scope: 'quantitative_associated_cohort_dataset_version',
      method: 'descriptive_summary',
      source_gate: '78_COHORT_FREEZE',
      source_shape: 'aligned_wide_table',
      source_dataset_version_ids: ['dv-1', 'dv-2'],
    };
    State.sessionSummary = {
      session_id: 'session-cohort-delivery-ui',
      execution_selection: {
        selected: true,
        pass_run_ids: ['pass-run-id'],
        pass_run_statuses: { 'pass-run-id': 'completed' },
        source_preview_id: 'preview-id',
        source_preview_hash: 'preview-hash',
        analysis_plan_id: 'analysis-plan-id',
      },
      analysis_execution_start: {
        analysis_run_id: 'analysis-run-id',
      },
      execution_result_review: {
        review_state: 'execution_result_review_approved',
        operator_decision: 'approved',
        review_record_ref: 'review-ref',
      },
      package_review_submit: {
        package_review_state: 'package_review_approved',
        submit_record_ref: 'submit-ref',
        output_package_ids: packageIds,
        package_kinds: packageKinds,
        payload_refs: payloadRefs,
        payload_hashes: payloadHashes,
      },
      handoff_export_prepare: {
        prepare_record_ref: 'prepare-ref',
        handoff_export_state: 'handoff_export_prepared',
        handoff_export_envelope_ref: 'envelope-ref',
        result_review_record_ref: 'review-ref',
        package_review_preview_hash: 'package-preview-hash',
        reconciliation_record_id: 'reconciliation-id',
        package_review_submit_record_ref: 'submit-ref',
        package_review_state: 'package_review_approved',
        output_package_ids: packageIds,
        package_kinds: packageKinds,
        payload_refs: payloadRefs,
        payload_hashes: payloadHashes,
      },
      aps_handoff_dispatch: {
        aps_handoff_record_ref: 'aps-record-ref',
        aps_handoff_state: 'aps_handoff_dispatched',
      },
      external_export_download: external,
      sublayer_visualization: {
        pass_runs: [{
          pass_run_id: 'pass-run-id',
          pass_type: 'associated_cohort',
          pass_scope: 'quantitative_associated_cohort_dataset_version',
          selected_method_name: 'descriptive_summary',
          requested_method_name: 'descriptive_summary',
          requested_method_source: 'analysis_set.formation_basis_json.requested_method_name',
          source_gate: '78_COHORT_FREEZE',
          cohort_shape: 'aligned_wide_table',
          source_dataset_version_ids: ['dv-1', 'dv-2'],
        }],
      },
      authority_rail: authorityRail,
    };
    State.resultStatus = {
      result_status_available: true,
      pass_run_id: 'pass-run-id',
      pass_run_status: 'completed',
      pass_type: 'associated_cohort',
      pass_scope: 'quantitative_associated_cohort_dataset_version',
      selected_method_name: 'descriptive_summary',
      analysis_plan_id: 'analysis-plan-id',
      analysis_run_id: 'analysis-run-id',
      preview_identity: { preview_id: 'preview-id', preview_hash: 'preview-hash' },
      output_payload_ref: 'output-ref',
      output_metadata_summary: {
        readable: true,
        pass_type: 'associated_cohort',
        pass_scope: 'quantitative_associated_cohort_dataset_version',
        selected_method_name: 'descriptive_summary',
        requested_method_name: 'descriptive_summary',
        requested_method_source: 'analysis_set.formation_basis_json.requested_method_name',
        source_gate: '78_COHORT_FREEZE',
        cohort_shape: 'aligned_wide_table',
        source_dataset_version_ids: ['dv-1', 'dv-2'],
        output_payload_ref: 'output-ref',
      },
    };
    renderAll();
  });

  await expect(page.locator('#external-export-download-delivery-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    'associated_cohort_external_export_download_delivery_ui_unavailable',
  );

  await page.evaluate(() => {
    State.sessionSummary.external_export_download.delivery_ui = {
      schema_id: 'layer3.external_export_download_delivery_ui.v1',
      available: true,
      state: 'associated_cohort_external_export_download_delivery_ui_ready',
      operator_decision: 'deliver_external_export_download',
      delivery_mode: 'same_origin_artifact_stream',
      server_authority: 'associated_cohort_external_export_download_delivery_ui_gate',
      browser_managed_same_origin_attachment_enabled: true,
      public_url_enabled: false,
      signed_url_enabled: false,
      connector_dispatch_enabled: false,
      destination_selection_enabled: false,
      generic_downstream_dispatch_enabled: false,
      package_mutation_enabled: false,
      schema_runtime_source_widening_enabled: false,
    };
    renderAll();
  });

  await expect(page.locator('#external-export-download-delivery-submit')).toBeEnabled();
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    'external_export_download_delivery_ui_ready',
  );
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    'associated_cohort_external_export_download_delivery_ui_gate',
  );
  await expect(page.locator('#external-export-download-signed-reference-generate')).toBeEnabled();
  await expect(page.locator('#external-export-download-signed-reference-use')).toBeDisabled();
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'external_export_download_signed_reference_ui_ready',
  );

  await page.route('**/api/v1/layer3/handoff/export/download/signed-reference/generate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        schema_id: 'layer3.external_export_download_signed_reference.v1',
        status: 'prepared',
        session_id: 'session-cohort-delivery-ui',
        analysis_plan_id: 'analysis-plan-id',
        pass_run_id: 'pass-run-id',
        preview_identity: { preview_id: 'preview-id', preview_hash: 'preview-hash' },
        reconciliation_record_id: 'reconciliation-id',
        external_export_download_record_ref: 'readiness-ref',
        export_download_descriptor_ref: 'descriptor-ref',
        signed_reference_state: 'external_export_download_signed_reference_ready',
        signed_reference_token: 'signed-token-from-server',
        signed_reference_expires_at: '2026-05-04T12:00:00+00:00',
        signed_reference_expires_in_seconds: 300,
        signed_reference_use_endpoint: '/api/v1/layer3/handoff/export/download/signed-reference/use',
        delivery_mode: 'same_origin_signed_delivery_reference',
        server_authority: 'associated_cohort_external_export_download_signed_reference_gate',
        source_artifact_ref: 'aps-bundle-ref',
        source_artifact_hash: 'source-artifact-hash',
        source_artifact_size_bytes: 123,
        pass_type: 'associated_cohort',
        pass_scope: 'quantitative_associated_cohort_dataset_version',
        method: 'descriptive_summary',
        source_gate: '78_COHORT_FREEZE',
        source_shape: 'aligned_wide_table',
        source_dataset_version_ids: ['dv-1', 'dv-2'],
        public_url_enabled: false,
        external_object_store_url_enabled: false,
        connector_dispatch_enabled: false,
        destination_selection_enabled: false,
        generic_downstream_dispatch_enabled: false,
        package_mutation_enabled: false,
        schema_runtime_source_widening_enabled: false,
        authority_rail: {
          token_authority: 'server_hmac_stateless_reference',
          artifact_authority: 'existing_external_export_download_delivery_validator',
          expires_within_seconds: 300,
          revalidated_at_generation: true,
          revalidate_at_use_required: true,
          configured_secret_present: true,
        },
      }),
    });
  });

  const signedRequestPromise = page.waitForRequest(
    '**/api/v1/layer3/handoff/export/download/signed-reference/generate',
  );
  await page.locator('#external-export-download-signed-reference-generate').click();
  const signedRequest = await signedRequestPromise;
  const signedPayload = signedRequest.postDataJSON();
  expect(signedPayload.operator_decision).toBe('deliver_external_export_download');
  expect(signedPayload.delivery_mode).toBe('same_origin_artifact_stream');
  expect(signedPayload.external_export_download_record_ref).toBe('readiness-ref');
  expect(signedPayload.client_request_id).toEqual(expect.any(String));
  for (const forbiddenKey of [
    'download_url',
    'download_token',
    'public_url',
    'signed_url',
    'local_file_path',
    'connector_run_id',
    'connector_dispatch',
    'destination',
    'destination_id',
    'generic_dispatch',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'retry',
    'recover',
    'schema_migration',
    'delivery_ui',
  ]) {
    expect(signedPayload).not.toHaveProperty(forbiddenKey);
  }
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'external_export_download_signed_reference_ready',
  );
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'same_origin_signed_delivery_reference',
  );
  await expect(page.locator('#external-export-download-signed-reference-generate')).toBeDisabled();
  await expect(page.locator('#external-export-download-signed-reference-use')).toBeEnabled();

  await page.route('**/api/v1/layer3/handoff/export/download/signed-reference/use', async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload).toEqual({ signed_reference_token: 'signed-token-from-server' });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: {
        'x-layer3-schema-id': 'layer3.external_export_download_signed_reference_use.v1',
        'x-layer3-delivery-state': 'external_export_download_delivered',
        'x-layer3-signed-reference-state': 'external_export_download_signed_reference_delivered',
        'x-layer3-signed-reference-expires-at': '2026-05-04T12:00:00+00:00',
        'x-layer3-source-artifact-hash': 'source-artifact-hash',
      },
      body: '{"delivered":true}',
    });
  });

  await Promise.all([
    page.waitForResponse('**/api/v1/layer3/handoff/export/download/signed-reference/use'),
    page.locator('#external-export-download-signed-reference-use').click(),
  ]);
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText(
    'external_export_download_signed_reference_delivered',
  );

  await page.route('**/api/v1/layer3/handoff/export/download/deliver', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/octet-stream',
      headers: {
        'content-disposition': 'attachment; filename="cohort-aps-bundle.json"',
        'x-layer3-schema-id': 'layer3.external_export_download_delivery.v1',
        'x-layer3-delivery-state': 'external_export_download_delivered',
        'x-layer3-source-artifact-hash': 'source-artifact-hash',
      },
      body: '{"delivered":true}',
    });
  });

  const [deliveryRequest, deliveryResponse] = await Promise.all([
    page.waitForRequest('**/api/v1/layer3/handoff/export/download/deliver'),
    page.waitForResponse('**/api/v1/layer3/handoff/export/download/deliver'),
    page.locator('#external-export-download-delivery-submit').click(),
  ]);
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(
    'external_export_download_delivery_ui_downloading',
  );
  expect(deliveryResponse.status()).toBe(200);
  expect(deliveryResponse.headers()['content-disposition']).toContain('attachment');
  const submittedPayload = formPostPayload(deliveryRequest);
  expect(submittedPayload.operator_decision).toBe('deliver_external_export_download');
  expect(submittedPayload.delivery_mode).toBe('same_origin_artifact_stream');
  expect(submittedPayload.external_export_download_record_ref).toBe('readiness-ref');
  expect(submittedPayload.client_request_id).toEqual(expect.any(String));
  expect(submittedPayload.client_request_id.length).toBeGreaterThan(0);
  for (const forbiddenKey of [
    'download_url',
    'download_token',
    'public_url',
    'signed_url',
    'local_file_path',
    'connector_run_id',
    'connector_dispatch',
    'destination',
    'destination_id',
    'generic_dispatch',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'retry',
    'recover',
    'schema_migration',
    'delivery_ui',
  ]) {
    expect(submittedPayload).not.toHaveProperty(forbiddenKey);
  }
});

test('Layer 3 workbench submits qualitative APS package review without analysis-run authority', async ({ page }) => {
  const fixture = qualitativeApsPackageSubmitUiFixture();
  let packageSubmitPayload = null;
  await page.route('**/api/v1/layer3/package/review/submit', async (route) => {
    packageSubmitPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(fixture.packageSubmitResponse),
    });
  });
  await page.route(`**/api/v1/layer3/session/${fixture.sessionId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        session_id: fixture.sessionId,
        execution_selection: {
          selected: true,
          pass_run_ids: [fixture.passRunId],
          pass_run_statuses: { [fixture.passRunId]: 'completed' },
          source_preview_id: fixture.previewId,
          source_preview_hash: fixture.previewHash,
          analysis_plan_id: fixture.analysisPlanId,
        },
        package_review_submit: fixture.packageSubmitResponse,
        handoff_export_prepare: {
          schema_id: 'layer3.handoff_export_prepare_state.v1',
          available: false,
          state: 'handoff_export_unavailable',
          blocked_reason: 'qualitative_aps_handoff_export_prepare_not_admitted_by_ui_fixture',
        },
      }),
    });
  });

  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await seedQualitativeApsPackageSubmitUiState(page, fixture);
  await expectNoDeferredRawMixedControls(page);
  await expect(page.locator('#package-review-submit')).toBeEnabled();
  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_submit_ready');

  const responsePromise = page.waitForResponse((response) => (
    response.url().includes('/api/v1/layer3/package/review/submit')
  ));
  await page.locator('#package-review-submit').click();
  const packageSubmit = await expectJson(await responsePromise);
  expect(packageSubmit.schema_id).toBe('layer3.qual_aps_package_review_submit.v1');
  expect(packageSubmitPayload).toBeTruthy();
  expectOnlyPayloadKeys(packageSubmitPayload, [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'result_review_record_ref',
    'package_review_preview_hash',
    'reconciliation_record_id',
    'output_package_ids',
    'payload_refs',
    'payload_hashes',
    'construction_basis_hash',
    'operator_decision',
    'decision_notes',
    'expected_package_kinds',
  ]);
  expect(packageSubmitPayload.session_id).toBe(fixture.sessionId);
  expect(packageSubmitPayload.analysis_plan_id).toBe(fixture.analysisPlanId);
  expect(packageSubmitPayload.pass_run_id).toBe(fixture.passRunId);
  expect(packageSubmitPayload.preview_id).toBe(fixture.previewId);
  expect(packageSubmitPayload.preview_hash).toBe(fixture.previewHash);
  expect(packageSubmitPayload.result_review_record_ref).toBe(fixture.resultReviewRef);
  expect(packageSubmitPayload.package_review_preview_hash).toBe(fixture.packagePreviewHash);
  expect(packageSubmitPayload.reconciliation_record_id).toBe(fixture.reconciliationId);
  expect(packageSubmitPayload.output_package_ids).toEqual(fixture.outputPackages.map((pkg) => pkg.output_package_id));
  expect(packageSubmitPayload.payload_refs).toEqual(fixture.payloadRefs);
  expect(packageSubmitPayload.payload_hashes).toEqual(fixture.payloadHashes);
  expect(packageSubmitPayload.construction_basis_hash).toBe(fixture.constructionBasisHash);
  expect(packageSubmitPayload.operator_decision).toBe('approved');
  expect(packageSubmitPayload).not.toHaveProperty('analysis_run_id');
  for (const forbiddenKey of [
    'handoff',
    'export',
    'package_payload',
    'provider_url',
    'public_url',
    'connector_run_id',
    'connector_dispatch',
    'destination',
    'rag_plan',
    'vector_query',
    'local_upload',
    'local_directory',
    'web_connector',
    'source_adapter_registry',
    'llm_plan',
    'mockup',
    'auth_context',
  ]) {
    expect(packageSubmitPayload).not.toHaveProperty(forbiddenKey);
  }
  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_approved');
});

test('Layer 3 workbench applies mockup-informed Workbench visual boundaries without degrading shared themes', async ({ page }) => {
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('workbench');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('.operation-dock-tab')).toHaveCount(9);
  await expect(page.locator('.operations-dock > .operation-panel-active')).toHaveCount(1);
  await expect(page.locator('.operations-dock > .operation-panel-inactive').first()).toBeAttached();
  await expect(page.locator('#operations-dock-summary')).toContainText('Intent');
  await expect(page.locator('#operations-dock-summary')).toContainText('3A intake setup');
  await expect(page.locator('#operations-dock-summary')).toContainText('Sublayer 3A intake/specification field');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-canvas', '3a');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-key', 'intent');

  const workbenchStyles = await page.evaluate(() => {
    const bodyStyle = window.getComputedStyle(document.body);
    const shell = document.querySelector('.layer3-body');
    const shellRect = shell.getBoundingClientRect();
    const stepperRect = document.querySelector('.layer3-stepper').getBoundingClientRect();
    const contextRect = document.querySelector('.context-panel').getBoundingClientRect();
    const workspaceRect = document.querySelector('.layer3-workspace').getBoundingClientRect();
    const railStyle = window.getComputedStyle(document.querySelector('.authority-rail'));
    const workbandStyle = window.getComputedStyle(document.querySelector('#gate-b-band'));
    const fieldsetStyle = window.getComputedStyle(document.querySelector('#source-fieldset'));
    const chipStyle = window.getComputedStyle(document.querySelector('[data-step="gate_b"]'));
    const dockStyle = window.getComputedStyle(document.querySelector('.operations-dock'));
    const dockNavStyle = window.getComputedStyle(document.querySelector('.operations-dock-nav'));
    const activePanelStyle = window.getComputedStyle(document.querySelector('.operations-dock > .operation-panel-active'));
    const inactivePanelStyle = window.getComputedStyle(document.querySelector('.operations-dock > .operation-panel-inactive'));
    const mapBand = document.querySelector('#sublayer-map-band');
    const mapBandStyle = window.getComputedStyle(mapBand);
    const mapPanelStyle = window.getComputedStyle(document.querySelector('#sublayer-map-panel'));
    return {
      bodyBackground: bodyStyle.backgroundColor,
      railBorderTopStyle: railStyle.borderTopStyle,
      railBorderBottomStyle: railStyle.borderBottomStyle,
      railBackground: railStyle.backgroundColor,
      workspaceBackground: window.getComputedStyle(document.querySelector('.layer3-workspace')).backgroundColor,
      workbandBorderStyle: workbandStyle.borderTopStyle,
      workbandBorderLeftWidth: workbandStyle.borderLeftWidth,
      workbandBorderLeftColor: workbandStyle.borderLeftColor,
      workbandBackground: workbandStyle.backgroundColor,
      fieldsetBorderStyle: fieldsetStyle.borderTopStyle,
      chipBackground: chipStyle.backgroundColor,
      dockDisplay: dockStyle.display,
      dockOverflowX: dockStyle.overflowX,
      dockColumnCount: dockStyle.gridTemplateColumns.split(' ').filter(Boolean).length,
      dockNavDisplay: dockNavStyle.display,
      activePanelDisplay: activePanelStyle.display,
      inactivePanelDisplay: inactivePanelStyle.display,
      shellColumnCount: window.getComputedStyle(shell).gridTemplateColumns.split(' ').filter(Boolean).length,
      stepperWidth: Math.round(stepperRect.width),
      contextWidth: Math.round(contextRect.width),
      workspaceShare: workspaceRect.width / shellRect.width,
      mapBandHasCanvasStageClass: mapBand.classList.contains('canvas-stage-band'),
      mapBandBorderLeftStyle: mapBandStyle.borderLeftStyle,
      mapBandBorderRightStyle: mapBandStyle.borderRightStyle,
      mapPanelPaddingLeft: Math.round(Number.parseFloat(mapPanelStyle.paddingLeft)),
    };
  });
  expect(workbenchStyles).toMatchObject({
    bodyBackground: 'rgb(13, 13, 13)',
    railBorderTopStyle: 'none',
    railBorderBottomStyle: 'dotted',
    workspaceBackground: 'rgba(0, 0, 0, 0)',
    workbandBorderStyle: 'dotted',
    workbandBorderLeftWidth: '0px',
    workbandBackground: 'rgba(0, 0, 0, 0)',
    fieldsetBorderStyle: 'dashed',
    dockDisplay: 'grid',
    dockOverflowX: 'hidden',
    dockColumnCount: 2,
    dockNavDisplay: 'grid',
    activePanelDisplay: 'grid',
    inactivePanelDisplay: 'none',
    shellColumnCount: 3,
    mapBandHasCanvasStageClass: true,
    mapBandBorderLeftStyle: 'none',
    mapBandBorderRightStyle: 'none',
  });
  expect(workbenchStyles.mapPanelPaddingLeft).toBeLessThanOrEqual(10);
  expect(workbenchStyles.stepperWidth).toBeLessThanOrEqual(38);
  expect(workbenchStyles.contextWidth).toBeLessThanOrEqual(62);
  expect(workbenchStyles.workspaceShare).toBeGreaterThan(0.92);
  expect(workbenchStyles.railBackground).not.toBe('rgba(0, 0, 0, 0)');
  expect(workbenchStyles.chipBackground).not.toBe('rgba(0, 0, 0, 0)');
  await expect(page.locator('.operation-dock-tab')).toHaveCount(9);
  await expect(page.locator('.operation-dock-tab').first()).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#intent-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#gate-b-band')).toHaveAttribute('data-operation-active', 'false');

  await page.locator('.operation-dock-tab').first().focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('.operation-dock-tab').nth(1)).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#gate-b-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#intent-band')).toHaveAttribute('data-operation-active', 'false');
  await expect(page.locator('#operations-dock-summary')).toContainText('Gate B Material Ledger');
  await expect(page.locator('#operations-dock-summary')).toContainText('3A material ledger');
  await expect(page.locator('#operations-dock-summary')).toContainText('Sublayer 3A session-scoped material ledger');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-canvas', '3a');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-key', 'gate_b');

  await page.keyboard.press('ArrowRight');
  await expect(page.locator('.operation-dock-tab').nth(2)).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#gate-c-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#operations-dock-summary')).toContainText('Sublayer 3B modality object banks');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-canvas', '3b');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-key', 'gate_c');

  const canvasFocusStyles = await page.evaluate(() => {
    const threeB = window.getComputedStyle(document.querySelector('.sublayer-3b'));
    const connector = window.getComputedStyle(document.querySelector('.sublayer-connector-3bc'));
    return {
      threeBBorderColor: threeB.borderTopColor,
      threeBBoxShadow: threeB.boxShadow,
      connectorFilter: connector.filter,
    };
  });
  expect(canvasFocusStyles.threeBBorderColor).not.toBe('rgb(180, 180, 180)');
  expect(canvasFocusStyles.threeBBoxShadow).not.toBe('none');
  expect(canvasFocusStyles.connectorFilter).not.toBe('none');

  await page.locator('[data-step="sources"]').click();
  await expect(page.locator('#intent-band')).toHaveAttribute('data-operation-active', 'true');
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-active-operation-key', 'intent');
  await expect(page.locator('#source-fieldset')).toBeVisible();

  await page.locator('#theme-selector').selectOption('light');
  await page.reload({ waitUntil: 'domcontentloaded' });
  const lightWorkbandStyle = await page.locator('#gate-b-band').evaluate((element) => {
    const style = window.getComputedStyle(element);
    return {
      borderStyle: style.borderTopStyle,
      borderLeftWidth: style.borderLeftWidth,
    };
  });
  expect(lightWorkbandStyle).toEqual({
    borderStyle: 'solid',
    borderLeftWidth: '1px',
  });

  await page.setViewportSize({ width: 1024, height: 768 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  const lightPlaneColumnCount = await page.locator('.analysis-plane .plane-flow').first().evaluate((element) => {
    const style = window.getComputedStyle(element);
    return style.gridTemplateColumns.split(' ').filter(Boolean).length;
  });
  expect(lightPlaneColumnCount).toBeGreaterThan(1);

  await page.locator('#theme-selector').selectOption('workbench');
  await page.reload({ waitUntil: 'domcontentloaded' });
  const workbenchPlaneColumnCount = await page.locator('.analysis-plane .plane-flow').first().evaluate((element) => {
    const style = window.getComputedStyle(element);
    return style.gridTemplateColumns.split(' ').filter(Boolean).length;
  });
  expect(workbenchPlaneColumnCount).toBe(1);

  await page.locator('[data-operation-target="result-review-band"]').click();
  await expect(page.locator('#result-review-band')).toHaveAttribute('data-operation-active', 'true');
  const workbenchResultControlColumns = await page.evaluate(() => {
    const resultControls = window.getComputedStyle(document.querySelector('#result-review-band .result-review-controls'));
    return resultControls.gridTemplateColumns.split(' ').filter(Boolean).length;
  });
  expect(workbenchResultControlColumns).toBe(2);
  await page.locator('[data-operation-target="aps-handoff-band"]').click();
  await expect(page.locator('#aps-handoff-band')).toHaveAttribute('data-operation-active', 'true');
  const workbenchApsControlColumns = await page.evaluate(() => {
    const apsControls = window.getComputedStyle(document.querySelector('#aps-handoff-dispatch-form .result-review-controls'));
    return apsControls.gridTemplateColumns.split(' ').filter(Boolean).length;
  });
  expect(workbenchApsControlColumns).toBe(1);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('[data-operation-target="result-review-band"]').click();
  await expect(page.locator('#result-review-band')).toHaveAttribute('data-operation-active', 'true');
  const mobileWorkbenchControlColumns = await page.evaluate(() => {
    const resultControls = window.getComputedStyle(document.querySelector('#result-review-band .result-review-controls'));
    return {
      result: resultControls.gridTemplateColumns.split(' ').filter(Boolean).length,
    };
  });
  expect(mobileWorkbenchControlColumns).toEqual({
    result: 1,
  });
  await page.locator('[data-operation-target="aps-handoff-band"]').click();
  await expect(page.locator('#aps-handoff-band')).toHaveAttribute('data-operation-active', 'true');
  const mobileApsControlColumns = await page.evaluate(() => {
    const apsControls = window.getComputedStyle(document.querySelector('#aps-handoff-dispatch-form .result-review-controls'));
    return apsControls.gridTemplateColumns.split(' ').filter(Boolean).length;
  });
  expect(mobileApsControlColumns).toBe(1);
});

test('Layer 3 workbench opens the exact Claude prototype as a durable standalone mode', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await Promise.all([
    page.waitForURL('**/review/layer3/static/claude.html'),
    page.locator('#theme-selector').selectOption('claude'),
  ]);

  await expect(page).toHaveTitle(/Layer 3 Workbench.*Prototype/);
  await expect(page.locator('.chrome-bar')).toHaveCount(0);
  await expect(page.locator('header.app-header.layer3-header')).toBeVisible();
  await expect(page.locator('.proto-badge')).toHaveText('PROTOTYPE');
  await expect(page.locator('#theme-selector')).toHaveValue('claude');
  await expect(page.locator('.nav-tab[data-screen="overview"]')).toContainText('Overview');
  await expect(page.locator('.state-btn[data-state="loaded"]')).toHaveClass(/active/);
  await expect(page.locator('#screen-intent')).toHaveClass(/active/);
  await expect(page.locator('#screen-intent')).toContainText('No corpus-backed manual/custom specification loaded.');
  await expect(page.locator('#spec-chips-grid .spec-chip')).toHaveCount(0);

  await page.locator('.nav-tab[data-screen="overview"]').click();
  await expect(page.locator('#screen-overview')).toHaveClass(/active/);
  await page.locator('.state-btn[data-state="analyzed"]').click();
  await expect(page.locator('.state-btn[data-state="analyzed"]')).toHaveClass(/active/);
  await expect(page.locator('#ov-3c-content')).toContainText('Insights/Facts/Data Generated');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page).toHaveTitle(/Layer 3 Workbench.*Prototype/);
  const mobileState = await page.evaluate(() => ({
    screenCount: document.querySelectorAll('.screen').length,
    hasPrototypeBadge: document.querySelector('.proto-badge')?.textContent?.trim() === 'PROTOTYPE',
    themeValue: document.querySelector('#theme-selector')?.value,
  }));
  expect(mobileState).toEqual({
    screenCount: 5,
    hasPrototypeBadge: true,
    themeValue: 'claude',
  });

  await Promise.all([
    page.waitForURL('**/review/layer3'),
    page.locator('#theme-selector').selectOption('dark'),
  ]);
  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'dark');
});

test('Layer 3 workbench renders a responsive live-state sublayer material and analysis map', async ({ page }) => {
  await page.setViewportSize({ width: 1626, height: 869 });
  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);
  await page.locator('#theme-selector').selectOption('workbench');

  await expect(page.locator('#sublayer-map-panel')).toContainText('Sublayer 3A');
  await expect(page.locator('#sublayer-map-panel')).toContainText('Sublayer 3B');
  await expect(page.locator('#sublayer-map-panel')).toContainText('Sublayer 3C');
  await expect(page.locator('#sublayer-map-panel')).toHaveClass(/diagram-canvas/);
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-viz-state', 'empty|empty|structural');
  await expect(page.locator('.canvas-intake-spec')).toContainText('User Natural Language Query Input');
  await expect(page.locator('.canvas-state-flow')).toContainText('3A');
  await expect(page.locator('.canvas-state-flow')).toContainText('Awaiting live state');
  await expect(page.locator('.canvas-state-flow')).toContainText('Structural only');
  await expect(page.locator('.manual-source-spec')).toContainText('Dataset version');
  await expect(page.locator('.manual-source-spec')).toContainText('APS content document');
  await expect(page.locator('.ledger-chip-field')).toBeVisible();
  await expect(page.locator('.ledger-bracket')).toContainText('Session-scoped Materials');
  await expect(page.locator('.analysis-lane-legend')).toContainText('Input object bank');
  await expect(page.locator('.analysis-lane-legend')).toContainText('Process / status');
  await expect(page.locator('.analysis-lane-legend')).toContainText('Output field');
  await expect(page.locator('.plane-arrow-process').first()).toBeVisible();
  await expect(page.locator('.plane-bracket').first()).toBeVisible();
  await expect(page.locator('.sublayer-3a .flow-empty')).toContainText('No material preview');
  await expect(page.locator('.modality-bucket.modality-quantitative')).toContainText('No quantitative objects');
  await expect(page.locator('.modality-bucket.modality-quantitative .modality-transfer-rail')).toHaveText('Awaiting objects');
  await expect(page.locator('.modality-bucket.modality-unclassified .modality-transfer-rail')).toHaveText('Held in 3B');
  await expect(page.locator('.analysis-plane.modality-quantitative')).toContainText('No live input object');

  const preflightResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/preflight'));
  const sourceResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/source-preview'));
  const materialResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/material-preview'));
  await page.locator('#run-preflight').click();
  await Promise.all([
    expectJson(await preflightResponsePromise),
    expectJson(await sourceResponsePromise),
    expectJson(await materialResponsePromise),
  ]);

  await expect(page.locator('.sublayer-3a .flow-object')).toHaveCount(2);
  await expect(page.locator('.sublayer-3a .diagram-chip')).toHaveCount(2);
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-viz-state', 'preview|empty|structural');
  await expect(page.locator('.sublayer-3a')).toContainText('Dataset Version');

  const rows = page.locator('#material-ledger-body tr[data-candidate-id]');
  await rows.nth(1).locator('.decision-select').selectOption('denied');
  await rows.nth(1).locator('.reason-input').fill('Deferred outside this visual proof.');
  await expect(page.locator('.sublayer-3a')).toContainText('denied');

  const gateBResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/gate-b/decision'));
  await page.locator('#gate-b-submit').click();
  await expectJson(await gateBResponsePromise);

  const gateCResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/gate-c/preview'));
  await page.locator('#gate-c-preview').click();
  const gateC = await expectJson(await gateCResponsePromise);
  expect(gateC.typing_records.length).toBeGreaterThan(0);

  await expect(page.locator('.modality-bucket.modality-quantitative .flow-object')).toHaveCount(gateC.typing_records.length);
  await expect(page.locator('.modality-bucket.modality-quantitative .diagram-chip')).toHaveCount(gateC.typing_records.length);
  await expect(page.locator('.modality-bucket.modality-quantitative .modality-transfer-rail')).toHaveAttribute('data-transfer-state', 'ready');
  await expect(page.locator('.modality-bucket.modality-quantitative .modality-transfer-rail')).toHaveText('Feeds 3C plane');
  await expect(page.locator('.sublayer-3a .flow-slot-ghost')).toHaveCount(4);
  await expect(page.locator('.modality-bucket.modality-quantitative .flow-slot-ghost')).toHaveCount(Math.max(0, 3 - gateC.typing_records.length));
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-viz-state', 'session|typed|inputs');
  await expect(page.locator('.state-3a')).toContainText('Session scoped');
  await expect(page.locator('.state-3b')).toContainText('Typing previewed');
  await expect(page.locator('.state-3c')).toContainText('Inputs routed');
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-input-bank')).toContainText('modality quantitative');
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-process-node')).toContainText('No live process yet');
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-output-field')).toContainText('No live output');
  await expect(page.locator('.analysis-plane.modality-quantitative .plane-output-field h5')).toHaveText('Output / Result Field');

  const diagramStyles = await page.evaluate(() => {
    const sublayer = window.getComputedStyle(document.querySelector('.sublayer-3a'));
    const modality = window.getComputedStyle(document.querySelector('.modality-bucket.modality-quantitative'));
    const modalityObjects = window.getComputedStyle(document.querySelector('.modality-bucket.modality-quantitative .flow-object-list'));
    const transferRail = window.getComputedStyle(document.querySelector('.modality-bucket.modality-quantitative .modality-transfer-rail'));
    const heldRailElement = document.querySelector('.analysis-routing-plane .modality-bucket.modality-unclassified .modality-transfer-rail');
    const heldRail = window.getComputedStyle(heldRailElement);
    const ghostSlot = window.getComputedStyle(document.querySelector('.sublayer-3a .flow-slot-ghost'));
    const arrow = window.getComputedStyle(document.querySelector('.plane-arrow-process'));
    const chip = window.getComputedStyle(document.querySelector('.sublayer-3a .diagram-chip'));
    const laneLegend = window.getComputedStyle(document.querySelector('.analysis-lane-legend'));
    const laneLabel = window.getComputedStyle(document.querySelector('.analysis-lane-label'));
    const intake = window.getComputedStyle(document.querySelector('.canvas-intake-spec'));
    const intakeFrame = window.getComputedStyle(document.querySelector('.intake-spec-frame'));
    const stateFlow = window.getComputedStyle(document.querySelector('.canvas-state-flow'));
    const routingElement = document.querySelector('.analysis-routing-plane');
    const routing = window.getComputedStyle(routingElement);
    const connector3bc = document.querySelector('.sublayer-connector-3bc');
    const connector3bcBefore = window.getComputedStyle(connector3bc, '::before');
    const connector3bcAfter = window.getComputedStyle(connector3bc, '::after');
    const threeA = window.getComputedStyle(document.querySelector('.sublayer-3a'));
    const inputBank = document.querySelector('.plane-input-bank');
    const processNode = document.querySelector('.plane-process-node');
    const outputField = document.querySelector('.plane-output-field');
    const outputFieldStyle = window.getComputedStyle(outputField);
    const materialBankShell = document.querySelector('.material-bank-shell');
    const materialBankShellStyle = window.getComputedStyle(materialBankShell);
    const modalityBankShell = document.querySelector('.modality-bank-shell');
    const modalityBankShellStyle = window.getComputedStyle(modalityBankShell);
    const laneFrame = document.querySelector('.plane-flow-frame');
    const laneFrameStyle = window.getComputedStyle(laneFrame);
    const laneSpineStyle = window.getComputedStyle(document.querySelector('.plane-lane-spine'));
    return {
      intakeDisplay: intake.display,
      intakeGridArea: intake.gridArea,
      intakeFrameDisplay: intakeFrame.display,
      intakeFrameColumns: intakeFrame.gridTemplateColumns.split(' ').filter(Boolean).length,
      stateFlowDisplay: stateFlow.display,
      stateFlowGridArea: stateFlow.gridArea,
      routingTag: routingElement.tagName,
      routingLabel: routingElement.getAttribute('aria-label'),
      routingDisplay: routing.display,
      routingGridArea: routing.gridArea,
      routingColumns: routing.gridTemplateColumns.split(' ').filter(Boolean).length,
      connector3bcBeforeWidth: connector3bcBefore.width,
      connector3bcAfterWidth: connector3bcAfter.width,
      connector3bcAfterClip: connector3bcAfter.clipPath !== 'none',
      threeADisplay: threeA.display,
      threeAColumns: threeA.gridTemplateColumns.split(' ').filter(Boolean).length,
      sublayerBorderStyle: sublayer.borderTopStyle,
      materialBankRole: materialBankShell.getAttribute('data-diagram-role'),
      materialBankColumns: materialBankShellStyle.gridTemplateColumns.split(' ').filter(Boolean).length,
      modalityBankRole: modalityBankShell.getAttribute('data-diagram-role'),
      modalityBankColumns: modalityBankShellStyle.gridTemplateColumns.split(' ').filter(Boolean).length,
      modalityBorderStyle: modality.borderTopStyle,
      modalityColumns: modality.gridTemplateColumns.split(' ').filter(Boolean).length,
      modalityObjectGridArea: modalityObjects.gridColumnStart,
      transferRailDisplay: transferRail.display,
      transferRailGridColumnStart: transferRail.gridColumnStart,
      transferRailPosition: transferRail.position,
      transferRailWritingMode: transferRail.writingMode,
      transferRailWidth: Math.round(Number.parseFloat(transferRail.width)),
      heldRailText: heldRailElement.textContent.trim(),
      heldRailPosition: heldRail.position,
      heldRailGridColumnStart: heldRail.gridColumnStart,
      heldRailAlignSelf: heldRail.alignSelf,
      heldRailWhiteSpace: heldRail.whiteSpace,
      heldRailWritingMode: heldRail.writingMode,
      ghostSlotDisplay: ghostSlot.display,
      ghostSlotBorderStyle: ghostSlot.borderTopStyle,
      arrowDisplay: arrow.display,
      chipRadius: chip.borderTopLeftRadius,
      laneLegendDisplay: laneLegend.display,
      laneLegendColumns: laneLegend.gridTemplateColumns.split(' ').filter(Boolean).length,
      laneLabelTransform: laneLabel.textTransform,
      inputBankRole: inputBank.getAttribute('data-plane-role'),
      processNodeRole: processNode.getAttribute('data-plane-role'),
      outputFieldRole: outputField.getAttribute('data-plane-role'),
      outputFieldHeading: outputField.querySelector('h5')?.textContent?.trim(),
      outputFieldBorderStyle: outputFieldStyle.borderTopStyle,
      laneFrameRole: laneFrame.getAttribute('data-plane-role'),
      laneFrameBorderTopStyle: laneFrameStyle.borderTopStyle,
      laneSpineDisplay: laneSpineStyle.display,
    };
  });
  expect(diagramStyles).toEqual({
    intakeDisplay: 'grid',
    intakeGridArea: 'spec',
    intakeFrameDisplay: 'grid',
    intakeFrameColumns: 2,
    stateFlowDisplay: 'grid',
    stateFlowGridArea: 'stateflow',
    routingTag: 'SECTION',
    routingLabel: 'Sublayer 3B to 3C analysis routing',
    routingDisplay: 'grid',
    routingGridArea: 'routing',
    routingColumns: 3,
    connector3bcBeforeWidth: '6px',
    connector3bcAfterWidth: '52px',
    connector3bcAfterClip: true,
    threeADisplay: 'grid',
    threeAColumns: 2,
    sublayerBorderStyle: 'dotted',
    materialBankRole: 'source-plane-material-field',
    materialBankColumns: 2,
    modalityBankRole: 'modality-object-bank',
    modalityBankColumns: 2,
    modalityBorderStyle: 'solid',
    modalityColumns: 1,
    modalityObjectGridArea: '2',
    transferRailDisplay: 'flex',
    transferRailGridColumnStart: '3',
    transferRailPosition: 'absolute',
    transferRailWritingMode: 'vertical-rl',
    transferRailWidth: 64,
    heldRailText: 'Held in 3B',
    heldRailPosition: 'static',
    heldRailGridColumnStart: '1',
    heldRailAlignSelf: 'start',
    heldRailWhiteSpace: 'nowrap',
    heldRailWritingMode: 'horizontal-tb',
    ghostSlotDisplay: 'block',
    ghostSlotBorderStyle: 'dashed',
    arrowDisplay: 'block',
    chipRadius: '0px',
    laneLegendDisplay: 'grid',
    laneLegendColumns: 5,
    laneLabelTransform: 'uppercase',
    inputBankRole: 'input-bank',
    processNodeRole: 'process-status',
    outputFieldRole: 'output-field',
    outputFieldHeading: 'Output / Result Field',
    outputFieldBorderStyle: 'dotted',
    laneFrameRole: 'analysis-environment-lane',
    laneFrameBorderTopStyle: 'solid',
    laneSpineDisplay: 'block',
  });

  const desktopFit = await page.evaluate(() => {
    const panel = document.querySelector('.sublayer-map-panel');
    const band = document.querySelector('.sublayer-map-band');
    return {
      pageFitsViewport: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      panelFitsBand: panel.scrollWidth <= band.clientWidth + 1,
      mapIsPrimarySurface: band.getBoundingClientRect().height >= window.innerHeight * 0.82,
    };
  });
  expect(desktopFit).toEqual({
    pageFitsViewport: true,
    panelFitsBand: true,
    mapIsPrimarySurface: true,
  });

  await page.setViewportSize({ width: 1500, height: 820 });
  const desktopBreakpointFit = await page.evaluate(() => {
    const panel = document.querySelector('.sublayer-map-panel');
    const band = document.querySelector('.sublayer-map-band');
    const firstPlaneFlow = document.querySelector('.analysis-plane .plane-flow');
    const laneLegend = document.querySelector('.analysis-lane-legend');
    return {
      pageFitsViewport: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      panelFitsBand: panel.scrollWidth <= band.clientWidth + 1,
      planeColumnCount: window.getComputedStyle(firstPlaneFlow).gridTemplateColumns.split(' ').filter(Boolean).length,
      laneLegendColumns: window.getComputedStyle(laneLegend).gridTemplateColumns.split(' ').filter(Boolean).length,
    };
  });
  expect(desktopBreakpointFit).toEqual({
    pageFitsViewport: true,
    panelFitsBand: true,
    planeColumnCount: 5,
    laneLegendColumns: 5,
  });

  await page.setViewportSize({ width: 1440, height: 820 });
  const mediumFit = await page.evaluate(() => {
    const firstPlaneFlow = document.querySelector('.analysis-plane .plane-flow');
    const firstPlaneColumnCount = window.getComputedStyle(firstPlaneFlow).gridTemplateColumns.split(' ').filter(Boolean).length;
    const laneLegend = window.getComputedStyle(document.querySelector('.analysis-lane-legend'));
    const laneSpine = window.getComputedStyle(document.querySelector('.plane-lane-spine'));
    return {
      fitsViewport: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      planeColumnCount: firstPlaneColumnCount,
      laneLegendDisplay: laneLegend.display,
      laneSpineDisplay: laneSpine.display,
    };
  });
  expect(mediumFit).toEqual({
    fitsViewport: true,
    planeColumnCount: 5,
    laneLegendDisplay: 'grid',
    laneSpineDisplay: 'block',
  });

  await page.setViewportSize({ width: 1024, height: 768 });
  const tabletFit = await page.evaluate(() => {
    const panel = window.getComputedStyle(document.querySelector('#sublayer-map-panel'));
    const intake = window.getComputedStyle(document.querySelector('.canvas-intake-spec'));
    const routing = window.getComputedStyle(document.querySelector('.analysis-routing-plane'));
    const workflow = window.getComputedStyle(document.querySelector('.workflow-canvas-field'));
    return {
      fitsViewport: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      panelTemplateIncludesWorkflow: panel.gridTemplateAreas.includes('workflow'),
      workflowGridArea: workflow.gridArea,
      intakeColumnCount: intake.gridTemplateColumns.split(' ').filter(Boolean).length,
      routingDisplay: routing.display,
    };
  });
  expect(tabletFit).toEqual({
    fitsViewport: true,
    panelTemplateIncludesWorkflow: true,
    workflowGridArea: 'workflow',
    intakeColumnCount: 1,
    routingDisplay: 'grid',
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('#sublayer-map-panel')).toBeVisible();
  await expect(page.locator('.sublayer-3a')).toBeVisible();
  await expect(page.locator('.sublayer-3b')).toBeVisible();
  await expect(page.locator('.sublayer-3c')).toBeVisible();
  const mobileFit = await page.evaluate(() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1);
  expect(mobileFit).toBe(true);
});

test('Layer 3 workbench keeps unsupported-only Gate C material out of 3C routed-input state', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 820 });
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('workbench');

  await page.evaluate(() => {
    const authorityRail = {
      current_gate: 'gate_c',
      session_id: 'unsupported-only-session',
      persistence_status: 'not_committed',
      approved_material_count: 0,
      denied_material_count: 0,
      isolated_material_count: 0,
      flagged_material_count: 1,
      typing_status: 'previewed',
    };
    State.materialPreview = null;
    State.gateB = {
      schema_id: 'layer3.gate_b_decision_result.v1',
      session_id: 'unsupported-only-session',
      approved_candidate_ids: [],
      denied_candidate_ids: [],
      isolated_candidate_ids: [],
      flagged_candidate_ids: ['unsupported-snapshot-1'],
      authority_rail: authorityRail,
    };
    State.gateC = {
      schema_id: 'layer3.gate_c_preview_result.v1',
      session_id: 'unsupported-only-session',
      typing_records: [],
      unsupported_material: [{
        material_snapshot_id: 'unsupported-snapshot-1',
        owner_service_source_shape: 'unsupported_shape',
        reason: 'unsupported-only visual proof',
      }],
      authority_rail: authorityRail,
    };
    State.planPreview = null;
    State.planApproval = null;
    State.planRevision = null;
    State.sessionSummary = null;
    clearResultReviewState();
    renderAll();
  });

  await expect(page.locator('.modality-bucket.modality-unclassified')).toContainText('Unsupported material');
  await expect(page.locator('.modality-bucket.modality-unclassified .diagram-chip')).toHaveCount(1);
  await expect(page.locator('.analysis-plane .plane-inputs .diagram-chip')).toHaveCount(0);
  await expect(page.locator('#sublayer-map-panel')).toHaveAttribute('data-viz-state', 'session|typed|structural');
  await expect(page.locator('.state-3c')).toContainText('Structural only');
});

test('Layer 3 mockup workbench theme exposes fixture projection without backend widening', async ({ page }, testInfo) => {
  const frames = loadMockupFrameManifest();
  const sublayerCFrame = frames.find((frame) => frame.repo_path.endsWith('sublayer-c.png'));
  const pdfLocationFrame = frames.find((frame) => frame.repo_path.endsWith('pdf-location.png'));
  expect(sublayerCFrame).toBeTruthy();
  expect(pdfLocationFrame).toBeTruthy();
  expect(sublayerCFrame.dimensions).toEqual({ width: 1022, height: 903 });
  expect(pdfLocationFrame.dimensions).toEqual({ width: 1610, height: 446 });

  const apiRequests = trackLayer3ApiRequests(page);
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('layer3_mockup_workbench_theme');

  await expect(page.locator('html')).toHaveAttribute('data-theme-preference', 'layer3_mockup_workbench_theme');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'workbench');
  await expect(page.locator('html')).toHaveAttribute('data-theme-variant', 'layer3_mockup_workbench_theme');
  await expect(page.locator('#mockup-theme-shell')).toBeVisible();
  await expect(page.locator('#mockup-theme-shell')).toHaveAttribute('data-theme-target', 'layer3_mockup_workbench_theme');
  await expect(page.locator('#mockup-theme-shell')).toHaveAttribute('data-first-slice', 'mockup_theme_shell_and_fixture_projection');
  await expect(page.locator('#mockup-fixture-scenario')).toHaveAttribute('data-fixture-scenario', 'semiconductor_infrastructure_auto_supply_chain');
  await expect(page.locator('#mockup-theme-shell')).toContainText('server state mapping required');
  await expect(page.locator('#mockup-theme-shell')).toContainText('browser storage presentation only');
  await expect(page.locator('#mockup-theme-shell')).toContainText('New source family unavailable');
  await expect(page.locator('#mockup-sublayers-ab-board')).toBeVisible();
  await expect(page.locator('#mockup-sublayers-ab-board')).toHaveAttribute('data-visual-source', 'focus_on_these/sublayer3A_and_sublayer3B.png');
  await expect(page.locator('#mockup-sublayers-ab-board')).toContainText('Gate B / Session Entry / Material Ledger');
  await expect(page.locator('#mockup-sublayers-ab-board')).toContainText('Hybrid/Mixed Data');
  await expect(page.locator('.mockup-ab-ledger .mockup-ab-object')).toHaveCount(20);
  await expect(page.locator('.mockup-ab-quant .mockup-ab-object')).toHaveCount(7);
  await expect(page.locator('.mockup-ab-qual .mockup-ab-object')).toHaveCount(7);
  await expect(page.locator('.mockup-ab-hybrid .mockup-ab-object')).toHaveCount(6);
  await expect(page.locator('#mockup-userflow-board')).toBeVisible();
  await expect(page.locator('#mockup-userflow-board')).toHaveAttribute('data-visual-source', 'userflow/layer3_user-flow-overview1.png');
  await expect(page.locator('#mockup-userflow-board')).toHaveAttribute('data-usecase-source', 'clear-screenshots/userflow_slide1_specific_usecase-example_zoomed-in.png');
  await expect(page.locator('#mockup-userflow-board')).toHaveAttribute('data-pdf-location-source', 'example-use-case-location-in-pdf.png');
  await expect(page.locator('#mockup-userflow-board')).toContainText('User Natural Language Query Input');
  await expect(page.locator('#mockup-userflow-board')).toContainText('PDF evidence location');
  await expect(page.locator('#mockup-userflow-board')).toContainText('Layer manually chooses the specific, relevant');
  await expect(page.locator('#mockup-pdf-location-projection')).toBeVisible();
  await expect(page.locator('#mockup-pdf-location-projection')).toHaveAttribute('data-projection-state', 'unavailable');
  await expect(page.locator('#mockup-pdf-location-projection')).toContainText('Server PDF-location projection');
  await expect(page.locator('#mockup-pdf-location-projection')).toContainText('Read-only server projection pending');
  await expect(page.locator('.mockup-userflow-node')).toHaveCount(5);
  await expect(page.locator('#mockup-execution-lanes')).toBeVisible();
  await expect(page.locator('#mockup-execution-lanes')).toHaveAttribute('data-visual-source', 'focus_on_these/sublayer3C.png');
  await expect(page.locator('#mockup-execution-lanes')).toContainText('Analysis Execution Environments');
  await expect(page.locator('#mockup-execution-lanes')).toContainText("Quantitative (and/or/AKA 'Deterministic') Environment/Container/Plane");
  await expect(page.locator('#mockup-execution-lanes')).toContainText('Qualitative Data Analysis Environment/Container/Plane');
  await expect(page.locator('.mockup-process-note')).toHaveCount(2);
  await expect(page.locator('.mockup-output-card')).toHaveCount(20);
  await expect(page.locator('#mockup-execution-lanes')).toContainText('Gate B Ingress Object #17 -> Generated insight #10');
  await expect(page.locator('#mockup-execution-lanes')).toContainText('Gate B Ingress Object #20 -> Generated finding #10');
  await expect(page.locator('#mockup-frame-list li')).toHaveCount(8);
  await expect(page.locator('#mockup-frame-list')).toContainText('userflow/layer3_user-flow-overview1.png');
  await expect(page.locator('#mockup-frame-list')).toContainText('focus_on_these/sublayer3C.png');
  await expect(page.locator('#mockup-frame-list')).toContainText('focus_on_these/sublayer3A_and_sublayer3B.png');
  await expect(page.locator('#mockup-frame-list')).toContainText('example-use-case-location-in-pdf.png');

  const frameProjectionCoverage = await page.locator('#mockup-theme-shell').evaluate((shell, frameSummaries) => frameSummaries.map((frame) => {
    const projection = frame.rendered_projection;
    const element = projection
      ? (projection.selector === '#mockup-theme-shell' ? shell : shell.querySelector(projection.selector))
      : null;
    const rect = element?.getBoundingClientRect();
    return {
      repoPath: frame.repo_path,
      projectionId: projection?.projection_id || null,
      selector: projection?.selector || null,
      screenshotAttachment: projection?.screenshot_attachment || null,
      visible: Boolean(rect && rect.width > 0 && rect.height > 0),
      width: rect ? Math.round(rect.width) : 0,
      height: rect ? Math.round(rect.height) : 0,
    };
  }), frames.map((frame) => ({
    repo_path: frame.repo_path,
    rendered_projection: frame.rendered_projection,
  })));
  expect(frameProjectionCoverage.map((entry) => entry.projectionId)).toEqual([
    'userflow_overview_1_projection',
    'userflow_overview_2_projection',
    'slide_1_projection',
    'slide_general_projection',
    'slide_usecase_projection',
    'pdf_location_projection',
    'sublayers_ab_projection',
    'sublayer_c_projection',
  ]);
  expect(new Set(frameProjectionCoverage.map((entry) => entry.selector))).toEqual(new Set([
    '#mockup-theme-shell',
    '#mockup-fixture-scenario',
    '#mockup-pdf-location-card',
    '#mockup-sublayers-ab-board',
    '#mockup-execution-lanes',
  ]));
  for (const coverage of frameProjectionCoverage) {
    expect(coverage.visible).toBe(true);
    expect(coverage.width).toBeGreaterThan(100);
    expect(coverage.height).toBeGreaterThan(80);
  }
  await testInfo.attach('layer3-mockup-frame-map.json', {
    body: JSON.stringify(frameProjectionCoverage, null, 2),
    contentType: 'application/json',
  });
  await expect(page.locator('#mockup-theme-shell button')).toHaveCount(0);
  await expect(page.locator('#mockup-execution-lanes button')).toHaveCount(0);
  const mockupShellScreenshot = await page.locator('#mockup-theme-shell').screenshot();
  expect(mockupShellScreenshot.length).toBeGreaterThan(10000);
  await testInfo.attach('layer3-mockup-theme-shell.png', {
    body: mockupShellScreenshot,
    contentType: 'image/png',
  });
  const sublayersAbScreenshot = await page.locator('#mockup-sublayers-ab-board').screenshot();
  expect(sublayersAbScreenshot.length).toBeGreaterThan(9000);
  await testInfo.attach('layer3-mockup-sublayers-ab-board.png', {
    body: sublayersAbScreenshot,
    contentType: 'image/png',
  });
  const userflowScreenshot = await page.locator('#mockup-userflow-board').screenshot();
  expect(userflowScreenshot.length).toBeGreaterThan(7000);
  await testInfo.attach('layer3-mockup-userflow-board.png', {
    body: userflowScreenshot,
    contentType: 'image/png',
  });
  const fixtureScenarioScreenshot = await page.locator('#mockup-fixture-scenario').screenshot();
  expect(fixtureScenarioScreenshot.length).toBeGreaterThan(7000);
  await testInfo.attach('layer3-mockup-fixture-scenario.png', {
    body: fixtureScenarioScreenshot,
    contentType: 'image/png',
  });

  const sublayersAbAcceptance = await page.locator('#mockup-sublayers-ab-board').evaluate((board) => ({
    visualSource: board.getAttribute('data-visual-source'),
    boardColumns: window.getComputedStyle(board).gridTemplateColumns.split(' ').filter(Boolean).length,
    ledgerObjects: board.querySelectorAll('.mockup-ab-ledger .mockup-ab-object').length,
    groupCount: board.querySelectorAll('.mockup-ab-group').length,
    quantitativeObjects: board.querySelectorAll('.mockup-ab-quant .mockup-ab-object').length,
    qualitativeObjects: board.querySelectorAll('.mockup-ab-qual .mockup-ab-object').length,
    hybridObjects: board.querySelectorAll('.mockup-ab-hybrid .mockup-ab-object').length,
  }));
  expect(sublayersAbAcceptance).toEqual({
    visualSource: 'focus_on_these/sublayer3A_and_sublayer3B.png',
    boardColumns: 3,
    ledgerObjects: 20,
    groupCount: 3,
    quantitativeObjects: 7,
    qualitativeObjects: 7,
    hybridObjects: 6,
  });

  const userflowAcceptance = await page.locator('#mockup-userflow-board').evaluate((board) => ({
    visualSource: board.getAttribute('data-visual-source'),
    usecaseSource: board.getAttribute('data-usecase-source'),
    pdfLocationSource: board.getAttribute('data-pdf-location-source'),
    promptCount: board.querySelectorAll('.mockup-userflow-prompt').length,
    specCount: board.querySelectorAll('.mockup-userflow-spec').length,
    pdfIntentCards: board.querySelectorAll('.mockup-pdf-intent-card').length,
    evidenceSheets: board.querySelectorAll('.mockup-evidence-sheet').length,
    summaryCards: board.querySelectorAll('.mockup-pdf-summary-card').length,
    serverProjectionState: board.querySelector('#mockup-pdf-location-projection')?.getAttribute('data-projection-state'),
    serverProjectionCards: board.querySelectorAll('.mockup-pdf-location-item').length,
    stageCount: board.querySelectorAll('.mockup-userflow-node').length,
    stageColumns: window.getComputedStyle(board.querySelector('.mockup-userflow-stage')).gridTemplateColumns.split(' ').filter(Boolean).length,
  }));
  expect(userflowAcceptance).toEqual({
    visualSource: 'userflow/layer3_user-flow-overview1.png',
    usecaseSource: 'clear-screenshots/userflow_slide1_specific_usecase-example_zoomed-in.png',
    pdfLocationSource: 'example-use-case-location-in-pdf.png',
    promptCount: 1,
    specCount: 1,
    pdfIntentCards: 1,
    evidenceSheets: 4,
    summaryCards: 3,
    serverProjectionState: 'unavailable',
    serverProjectionCards: 0,
    stageCount: 5,
    stageColumns: 5,
  });

  const visualAcceptance = await page.locator('#mockup-execution-lanes').evaluate((lanes) => {
    const laneBodies = Array.from(lanes.querySelectorAll('.mockup-lane-body'));
    return {
      visualSource: lanes.getAttribute('data-visual-source'),
      laneCount: lanes.querySelectorAll('.mockup-exec-lane').length,
      processNotes: lanes.querySelectorAll('.mockup-process-note').length,
      outputCards: lanes.querySelectorAll('.mockup-output-card').length,
      arrowCount: lanes.querySelectorAll('.mockup-flow-arrow').length,
      canvasTitle: lanes.querySelector('.mockup-canvas-title')?.textContent.replace(/\s+/g, ' ').trim(),
      laneColumns: laneBodies.map((body) => window.getComputedStyle(body).gridTemplateColumns.split(' ').filter(Boolean).length),
    };
  });
  expect(visualAcceptance).toEqual({
    visualSource: 'focus_on_these/sublayer3C.png',
    laneCount: 2,
    processNotes: 2,
    outputCards: 20,
    arrowCount: 4,
    canvasTitle: 'Sublayer 3C Analysis Execution Environments',
    laneColumns: [5, 5],
  });
  await page.setViewportSize({ width: 390, height: 900 });
  await expect(page.locator('#mockup-theme-shell')).toBeVisible();
  await expect(page.locator('#mockup-userflow-board')).toBeVisible();
  await expect(page.locator('#mockup-sublayers-ab-board')).toBeVisible();
  await expect(page.locator('#mockup-execution-lanes')).toBeVisible();
  const responsiveAcceptance = await page.locator('#mockup-theme-shell').evaluate((shell) => {
    const columnCount = (element) => window.getComputedStyle(element).gridTemplateColumns.split(' ').filter(Boolean).length;
    return {
      fitsViewport: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth + 1,
      shellDisplay: window.getComputedStyle(shell).display,
      userflowColumns: columnCount(shell.querySelector('#mockup-userflow-board')),
      sublayersColumns: columnCount(shell.querySelector('#mockup-sublayers-ab-board')),
      userflowStageColumns: columnCount(shell.querySelector('.mockup-userflow-stage')),
      laneColumns: Array.from(shell.querySelectorAll('.mockup-lane-body')).map(columnCount),
    };
  });
  expect(responsiveAcceptance).toEqual({
    fitsViewport: true,
    shellDisplay: 'grid',
    userflowColumns: 1,
    sublayersColumns: 1,
    userflowStageColumns: 1,
    laneColumns: [1, 1],
  });

  expectNoRequestsToLayer3Paths(apiRequests, [
    'source/mixed-corpus/materialize',
    'package/mutation',
    'handoff/connector',
    'provider-private-signed-url/prepare',
    'execution/start',
  ]);
});

test('Layer 3 mockup workbench visual diff harness compares repo-local frames', async ({ page }, testInfo) => {
  const frames = loadMockupFrameManifest();
  const apiRequests = trackLayer3ApiRequests(page);
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.locator('#theme-selector').selectOption('layer3_mockup_workbench_theme');
  await page.evaluate(() => document.fonts?.ready);

  const comparisons = [];
  for (const frame of frames) {
    const projection = frame.rendered_projection;
    const renderedSurface = page.locator(projection.selector).first();
    await expect(renderedSurface).toBeVisible();
    const screenshot = await renderedSurface.screenshot();
    expect(screenshot.length).toBeGreaterThan(7000);
    const metrics = await compareMockupFrameImages(
      page,
      frameDataUrl(frame),
      `data:image/png;base64,${screenshot.toString('base64')}`,
    );
    expect(metrics.referenceWidth).toBe(frame.dimensions.width);
    expect(metrics.referenceHeight).toBe(frame.dimensions.height);
    expect(metrics.actualWidth).toBeGreaterThan(100);
    expect(metrics.actualHeight).toBeGreaterThan(80);
    expect(metrics.normalizedMeanDelta, projection.projection_id).toBeLessThanOrEqual(
      MOCKUP_VISUAL_DIFF_LIMITS.normalizedMeanDeltaMax,
    );
    expect(metrics.highDeltaRatio, projection.projection_id).toBeLessThanOrEqual(
      MOCKUP_VISUAL_DIFF_LIMITS.highDeltaRatioMax,
    );
    comparisons.push({
      projectionId: projection.projection_id,
      selector: projection.selector,
      repoPath: frame.repo_path,
      renderedSurface: projection.rendered_surface,
      acceptanceMode: projection.acceptance_mode,
      limits: MOCKUP_VISUAL_DIFF_LIMITS,
      metrics,
    });
  }

  await testInfo.attach('layer3-mockup-visual-diff-metrics.json', {
    body: JSON.stringify(comparisons, null, 2),
    contentType: 'application/json',
  });
  expect(comparisons).toHaveLength(8);
  expect(new Set(comparisons.map((comparison) => comparison.selector))).toEqual(new Set([
    '#mockup-theme-shell',
    '#mockup-fixture-scenario',
    '#mockup-pdf-location-card',
    '#mockup-sublayers-ab-board',
    '#mockup-execution-lanes',
  ]));
  expectNoRequestsToLayer3Paths(apiRequests, [
    'source/mixed-corpus/materialize',
    'package/mutation',
    'handoff/connector',
    'provider-private-signed-url/prepare',
    'execution/start',
  ]);
});
