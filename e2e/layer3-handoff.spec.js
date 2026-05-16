import { test, expect } from '@playwright/test';
import {
  expectJson,
  expectJsonStatus,
  requestId,
  expectOnlyPayloadKeys,
  formPostPayload,
  expectStepAvailable,
  expectStepUnavailable,
  prepareExecutedLayer3Session,
  prepareQualitativeApsResultReviewSession,
  attachSessionToWorkbench,
} from './layer3-helpers.js';

async function expectRenderedDownstreamAccessLifecycleDashboard(page, stateLabel, expectedTexts = []) {
  const dashboard = page.locator('#downstream-access-lifecycle-dashboard-panel');
  await expect(dashboard).toBeVisible();
  await expect(dashboard).toHaveAttribute('data-rendered-mode', 'rendered_downstream_access_lifecycle_read_only_dashboard');
  await expect(dashboard).toHaveAttribute('data-lifecycle-state', stateLabel);
  await expect(dashboard).toContainText('operator_inspects_downstream_access_lifecycle_without_dispatch_or_raw_url_use');
  await expect(dashboard).toContainText('existing_server_response_authority');
  await expect(dashboard).toContainText('connector invocation');
  await expect(dashboard).toContainText('raw public URL display/use');
  await expect(dashboard.locator('button,input,select,textarea')).toHaveCount(0);
  for (const text of expectedTexts) {
    await expect(dashboard).toContainText(text);
  }
}

async function expectRenderedLayer3E2EGovernanceLifecycleDashboard(page, stateLabel, expectedTexts = []) {
  const dashboard = page.locator('#layer3-e2e-governance-lifecycle-dashboard-panel');
  await expect(dashboard).toBeVisible();
  await expect(dashboard).toHaveAttribute('data-rendered-mode', 'rendered_layer3_end_to_end_governance_lifecycle_read_only_dashboard');
  await expect(dashboard).toHaveAttribute('data-lifecycle-state', stateLabel);
  await expect(dashboard).toContainText('operator_inspects_layer3_end_to_end_governance_lifecycle_without_mutation_or_dispatch');
  await expect(dashboard).toContainText('existing_server_response_authority');
  await expect(dashboard).toContainText('package mutation');
  await expect(dashboard).toContainText('connector/destination dispatch');
  await expect(dashboard).toContainText('raw public URL display/use');
  await expect(dashboard.locator('button,input,select,textarea')).toHaveCount(0);
  for (const text of expectedTexts) {
    await expect(dashboard).toContainText(text);
  }
}

const LOCAL_OUTBOX_EXPECTED_PACKAGE_KINDS = ['canonical_internal', 'user_facing', 'review_facing'];

function maybeAnalysisRun(start) {
  return start.analysis_run_id ? { analysis_run_id: start.analysis_run_id } : {};
}

function outputPackageIds(commit) {
  return commit.output_packages.map((item) => item.output_package_id);
}

async function postLayer3Json(request, path, data) {
  const response = await request.post(path, { data });
  if (response.status() !== 200) {
    throw new Error(`${path} returned ${response.status()}: ${await response.text()}`);
  }
  return response.json();
}

async function prepareServerOwnedLocalOutboxWriteViaApi(request) {
  const setup = await prepareExecutedLayer3Session(request, '/__test/layer3/seed-cohort-aps-handoff');
  const sessionId = setup.seed.session_id;
  const common = {
    session_id: sessionId,
    analysis_plan_id: setup.approval.analysis_plan_id,
    pass_run_id: setup.passRunId,
    preview_id: setup.planPreview.preview_id,
    preview_hash: setup.planPreview.preview_hash,
    ...maybeAnalysisRun(setup.start),
  };
  const status = await postLayer3Json(request, '/api/v1/layer3/execution/result/status', {
    client_request_id: requestId('api-local-outbox-status'),
    ...common,
    operator_view_mode: 'status_only',
  });
  expect(status.result_status_available).toBe(true);

  const review = await postLayer3Json(request, '/api/v1/layer3/execution/result/review', {
    client_request_id: requestId('api-local-outbox-review'),
    ...common,
    operator_decision: 'approved',
    review_notes: 'Request-backed local outbox lifecycle proof.',
  });
  const packagePreview = await postLayer3Json(request, '/api/v1/layer3/package/review/preview', {
    client_request_id: requestId('api-local-outbox-package-preview'),
    ...common,
    result_review_record_ref: review.review_record_ref,
  });
  const commit = await postLayer3Json(request, '/api/v1/layer3/package/review/commit', {
    client_request_id: requestId('api-local-outbox-package-commit'),
    ...common,
    result_review_record_ref: review.review_record_ref,
    package_review_preview_hash: packagePreview.package_review_preview_hash,
    expected_package_kinds: LOCAL_OUTBOX_EXPECTED_PACKAGE_KINDS,
  });
  const submit = await postLayer3Json(request, '/api/v1/layer3/package/review/submit', {
    client_request_id: requestId('api-local-outbox-package-submit'),
    ...common,
    result_review_record_ref: review.review_record_ref,
    package_review_preview_hash: commit.package_review_preview_hash,
    reconciliation_record_id: commit.reconciliation_record_id,
    output_package_ids: outputPackageIds(commit),
    payload_refs: commit.payload_refs,
    payload_hashes: commit.payload_hashes,
    ...(commit.construction_basis_hash ? { construction_basis_hash: commit.construction_basis_hash } : {}),
    operator_decision: 'approved',
    decision_notes: 'Approve package for request-backed local outbox lifecycle proof.',
    expected_package_kinds: LOCAL_OUTBOX_EXPECTED_PACKAGE_KINDS,
  });
  const prepare = await postLayer3Json(request, '/api/v1/layer3/handoff/export/prepare', {
    client_request_id: requestId('api-local-outbox-handoff-prepare'),
    ...common,
    result_review_record_ref: review.review_record_ref,
    package_review_preview_hash: commit.package_review_preview_hash,
    reconciliation_record_id: commit.reconciliation_record_id,
    output_package_ids: outputPackageIds(commit),
    payload_refs: commit.payload_refs,
    payload_hashes: commit.payload_hashes,
    package_review_submit_record_ref: submit.submit_record_ref,
    package_review_state: submit.package_review_state,
    package_review_submit_schema_id: submit.schema_id,
    ...(commit.construction_basis_hash ? { construction_basis_hash: commit.construction_basis_hash } : {}),
    handoff_target: 'internal_export_envelope',
    export_mode: 'prepare_only',
    operator_decision: 'authorize_prepare',
    expected_package_kinds: LOCAL_OUTBOX_EXPECTED_PACKAGE_KINDS,
  });
  const dispatch = await postLayer3Json(request, '/api/v1/layer3/handoff/aps/dispatch', {
    client_request_id: requestId('api-local-outbox-aps-dispatch'),
    ...common,
    result_review_record_ref: review.review_record_ref,
    package_review_preview_hash: commit.package_review_preview_hash,
    reconciliation_record_id: commit.reconciliation_record_id,
    output_package_ids: outputPackageIds(commit),
    package_kinds: commit.package_kinds,
    payload_refs: commit.payload_refs,
    payload_hashes: commit.payload_hashes,
    package_review_submit_record_ref: submit.submit_record_ref,
    package_review_state: submit.package_review_state,
    prepare_record_ref: prepare.prepare_record_ref,
    handoff_export_state: prepare.handoff_export_state,
    handoff_export_envelope_ref: prepare.handoff_export_envelope.envelope_ref,
    handoff_target: 'internal_export_envelope',
    export_mode: 'prepare_only',
    aps_handoff_target: 'aps_evidence_bundle',
    dispatch_mode: 'server_side_aps_handoff',
    operator_decision: 'dispatch_aps_handoff',
  });
  const postDispatchSummary = await expectJson(await request.get(`/api/v1/layer3/session/${sessionId}`));
  const external = await postLayer3Json(request, '/api/v1/layer3/handoff/export/download/prepare', {
    client_request_id: requestId('api-local-outbox-export-download'),
    ...common,
    result_review_record_ref: review.review_record_ref,
    package_review_preview_hash: commit.package_review_preview_hash,
    reconciliation_record_id: commit.reconciliation_record_id,
    output_package_ids: outputPackageIds(commit),
    package_kinds: commit.package_kinds,
    payload_refs: commit.payload_refs,
    payload_hashes: commit.payload_hashes,
    package_review_submit_record_ref: submit.submit_record_ref,
    package_review_state: submit.package_review_state,
    prepare_record_ref: prepare.prepare_record_ref,
    handoff_export_state: prepare.handoff_export_state,
    handoff_export_envelope_ref: prepare.handoff_export_envelope.envelope_ref,
    handoff_target: 'internal_export_envelope',
    export_mode: 'prepare_only',
    aps_handoff_record_ref: dispatch.aps_handoff_record_ref,
    aps_handoff_state: dispatch.aps_handoff_state,
    aps_handoff_target: dispatch.aps_handoff_target,
    dispatch_mode: dispatch.dispatch_mode,
    aps_output_package_id: dispatch.aps_output_package_id,
    aps_output_package_kind: dispatch.aps_output_package_kind,
    aps_bundle_ref: dispatch.aps_bundle_ref,
    aps_bundle_id: dispatch.aps_bundle_id,
    aps_schema_id: dispatch.aps_schema_id,
    aps_bundle_hash: postDispatchSummary.external_export_download.source_artifact_hash,
    aps_bundle_size_bytes: postDispatchSummary.external_export_download.source_artifact_size_bytes,
    export_download_target: 'aps_evidence_bundle_download_reference',
    download_mode: 'reference_only_prepare',
    operator_decision: 'prepare_external_export_download',
  });
  const connector = await postLayer3Json(request, '/api/v1/layer3/handoff/connector/record', {
    client_request_id: requestId('api-local-outbox-connector'),
    session_id: sessionId,
    analysis_plan_id: setup.approval.analysis_plan_id,
    pass_run_id: setup.passRunId,
    ...maybeAnalysisRun(setup.start),
    result_review_record_ref: review.review_record_ref,
    package_review_preview_hash: commit.package_review_preview_hash,
    reconciliation_record_id: commit.reconciliation_record_id,
    output_package_ids: outputPackageIds(commit),
    package_kinds: commit.package_kinds,
    payload_refs: commit.payload_refs,
    payload_hashes: commit.payload_hashes,
    package_review_submit_record_ref: submit.submit_record_ref,
    prepare_record_ref: prepare.prepare_record_ref,
    handoff_export_state: prepare.handoff_export_state,
    aps_handoff_record_ref: dispatch.aps_handoff_record_ref,
    aps_handoff_state: dispatch.aps_handoff_state,
    aps_handoff_target: dispatch.aps_handoff_target,
    aps_output_package_id: dispatch.aps_output_package_id,
    aps_output_package_kind: dispatch.aps_output_package_kind,
    aps_bundle_ref: dispatch.aps_bundle_ref,
    source_artifact_hash: external.source_artifact_hash,
    source_artifact_size_bytes: external.source_artifact_size_bytes,
    source_artifact_ref: external.source_artifact_ref,
    source_artifact_schema_id: external.source_artifact_schema_id,
    external_export_download_record_ref: external.external_export_download_record_ref,
    external_export_download_state: external.external_export_download_state,
    external_export_download_descriptor_ref: external.export_download_descriptor_ref,
    delivery_mode: 'same_origin_artifact_stream',
    operator_decision: 'record_internal_connector_dispatch',
  });
  const localReceipt = await postLayer3Json(request, '/api/v1/layer3/handoff/connector/local-destination/receipt', {
    client_request_id: requestId('api-local-outbox-local-receipt'),
    session_id: sessionId,
    analysis_plan_id: setup.approval.analysis_plan_id,
    pass_run_id: setup.passRunId,
    reconciliation_record_id: commit.reconciliation_record_id,
    connector_dispatch_record_ref: connector.connector_dispatch_record_ref,
    external_export_download_record_ref: external.external_export_download_record_ref,
    external_export_download_state: external.external_export_download_state,
    destination_target: 'layer3_internal_fake_local_destination_receipt',
    dispatch_mode: 'internal_fake_local_destination_receipt_only',
    operator_decision: 'record_internal_fake_local_destination_receipt',
  });
  const target = await postLayer3Json(request, '/api/v1/layer3/handoff/connector/local-outbox/fake-target', {
    client_request_id: requestId('api-local-outbox-fake-target'),
    session_id: sessionId,
    analysis_plan_id: setup.approval.analysis_plan_id,
    pass_run_id: setup.passRunId,
    reconciliation_record_id: commit.reconciliation_record_id,
    connector_dispatch_record_ref: connector.connector_dispatch_record_ref,
    connector_local_destination_receipt_id: localReceipt.connector_local_destination_receipt_id,
    connector_local_destination_receipt_state: localReceipt.connector_local_destination_receipt_state,
    external_export_download_record_ref: external.external_export_download_record_ref,
    target_identity: 'server_owned_local_delivery_outbox_destination',
    dispatch_mode: 'single_named_destination_dispatch_fake_target_first',
    operator_decision: 'record_server_owned_local_outbox_fake_target',
  });
  const write = await postLayer3Json(request, '/api/v1/layer3/handoff/connector/local-outbox/write', {
    client_request_id: requestId('api-local-outbox-write'),
    session_id: sessionId,
    analysis_plan_id: setup.approval.analysis_plan_id,
    pass_run_id: setup.passRunId,
    reconciliation_record_id: commit.reconciliation_record_id,
    connector_dispatch_record_ref: connector.connector_dispatch_record_ref,
    connector_local_destination_receipt_id: localReceipt.connector_local_destination_receipt_id,
    server_owned_local_outbox_target_receipt_id: target.server_owned_local_outbox_target_receipt_id,
    server_owned_local_outbox_target_state: target.server_owned_local_outbox_target_state,
    external_export_download_record_ref: external.external_export_download_record_ref,
    target_identity: 'server_owned_local_delivery_outbox_destination',
    dispatch_mode: 'server_owned_local_outbox_write_via_storage_dir',
    operator_decision: 'write_server_owned_local_outbox',
  });
  expect(write.server_owned_local_outbox_write_state).toBe('server_owned_local_outbox_write_recorded');
  expect(write.server_owned_local_outbox_write_performed).toBe(true);
  expect(write.real_connector_invocation_enabled).toBe(false);
  expect(write.external_destination_write_enabled).toBe(false);
  expect(write.connector_run_created).toBe(false);
  expect(write.connector_run_target_created).toBe(false);
  expect(write.outbox_artifact_ref).toMatch(/^storage:\/\/server-owned-local-outbox\//);
  return {
    ...setup,
    sessionId,
    review,
    packagePreview,
    commit,
    submit,
    prepare,
    dispatch,
    external,
    connector,
    localReceipt,
    target,
    write,
  };
}

async function prepareLocalOutboxProviderPrivateHandoffViaApi(request) {
  const setup = await prepareServerOwnedLocalOutboxWriteViaApi(request);
  const readySummary = await expectJson(await request.get(`/api/v1/layer3/session/${setup.sessionId}`));
  const readyStatus = readySummary.local_outbox_provider_private_handoff;
  expect(readyStatus.state).toBe('local_outbox_provider_private_handoff_ready');
  expect(readyStatus.available).toBe(true);
  expect(readyStatus.server_owned_local_outbox_write_receipt_id).toBe(
    setup.write.server_owned_local_outbox_write_receipt_id,
  );

  const providerPrivate = await postLayer3Json(
    request,
    '/api/v1/layer3/handoff/connector/local-outbox/provider-private/prepare',
    {
      client_request_id: requestId('api-local-outbox-provider-private'),
      session_id: setup.sessionId,
      analysis_plan_id: setup.approval.analysis_plan_id,
      pass_run_id: setup.passRunId,
      reconciliation_record_id: setup.commit.reconciliation_record_id,
      connector_dispatch_record_ref: setup.connector.connector_dispatch_record_ref,
      connector_local_destination_receipt_id: setup.localReceipt.connector_local_destination_receipt_id,
      server_owned_local_outbox_target_receipt_id: setup.target.server_owned_local_outbox_target_receipt_id,
      server_owned_local_outbox_write_receipt_id: setup.write.server_owned_local_outbox_write_receipt_id,
      external_export_download_record_ref: setup.external.external_export_download_record_ref,
      target_identity: 'server_owned_local_outbox_provider_private_handoff_destination',
      dispatch_mode: 'provider_private_fake_provider_prepare_status_from_local_outbox_receipt',
      operator_decision: 'prepare_provider_private_handoff_from_local_outbox',
      recipient_scope: 'external_downstream_recipient_private_artifact_delivery',
      requested_ttl_seconds: 300,
      decision_notes: 'Prepare redacted provider-private handoff receipt from request-backed local outbox authority.',
    },
  );
  expect(providerPrivate.provider_private_handoff_state).toBe('local_outbox_provider_private_handoff_prepared');
  expect(providerPrivate.raw_token_exposed).toBe(false);
  expect(providerPrivate.provider_private_use_route_enabled).toBe(false);
  expect(providerPrivate.real_connector_invocation_enabled).toBe(false);
  expect(providerPrivate.external_destination_write_enabled).toBe(false);
  expect(providerPrivate.connector_run_created).toBe(false);

  const providerPrivateStatus = await expectJson(
    await request.get(
      `/api/v1/layer3/handoff/connector/local-outbox/provider-private/status/${providerPrivate.provider_private_handoff_receipt_id}`,
    ),
  );
  expect(providerPrivateStatus.provider_private_handoff_receipt_id).toBe(
    providerPrivate.provider_private_handoff_receipt_id,
  );
  expect(providerPrivateStatus.provider_private_handoff_state).toBe('local_outbox_provider_private_handoff_prepared');
  expect(JSON.stringify(providerPrivateStatus)).not.toContain('fake-provider-private-token');

  return {
    ...setup,
    providerPrivate,
    providerPrivateStatus,
  };
}

async function prepareExternalLocalExportViaApi(request) {
  const setup = await prepareLocalOutboxProviderPrivateHandoffViaApi(request);
  const readySummary = await expectJson(await request.get(`/api/v1/layer3/session/${setup.sessionId}`));
  const readyStatus = readySummary.external_local_export;
  expect(readyStatus.state).toBe('external_local_export_ready');
  expect(readyStatus.available).toBe(true);
  expect(readyStatus.server_owned_local_outbox_write_receipt_id).toBe(
    setup.write.server_owned_local_outbox_write_receipt_id,
  );
  expect(readyStatus.provider_private_handoff_receipt_id).toBe(
    setup.providerPrivate.provider_private_handoff_receipt_id,
  );

  const externalLocalExportPayload = {
    client_request_id: requestId('api-external-local-export'),
    session_id: setup.sessionId,
    analysis_plan_id: setup.approval.analysis_plan_id,
    pass_run_id: setup.passRunId,
    reconciliation_record_id: setup.commit.reconciliation_record_id,
    connector_dispatch_record_ref: setup.connector.connector_dispatch_record_ref,
    connector_local_destination_receipt_id: setup.localReceipt.connector_local_destination_receipt_id,
    server_owned_local_outbox_target_receipt_id: setup.target.server_owned_local_outbox_target_receipt_id,
    server_owned_local_outbox_write_receipt_id: setup.write.server_owned_local_outbox_write_receipt_id,
    external_export_download_record_ref: setup.external.external_export_download_record_ref,
    provider_private_handoff_receipt_id: setup.providerPrivate.provider_private_handoff_receipt_id,
    target_identity: 'server_configured_external_local_export_directory',
    dispatch_mode: 'server_configured_external_local_export_directory_write',
    operator_decision: 'write_server_configured_external_local_export_directory',
  };
  const externalLocalExport = await postLayer3Json(
    request,
    '/api/v1/layer3/handoff/connector/local-outbox/external-local-export/write',
    externalLocalExportPayload,
  );
  expect(externalLocalExport.external_local_export_state).toBe('external_local_export_written');
  expect(externalLocalExport.server_configured_external_local_export_write_performed).toBe(true);
  expect(externalLocalExport.external_artifact_ref).toMatch(/^external-local-export:\/\//);
  expect(externalLocalExport.external_manifest_ref).toMatch(/^external-local-export:\/\//);
  expect(externalLocalExport.real_connector_invocation_enabled).toBe(false);
  expect(externalLocalExport.connector_run_created).toBe(false);
  expect(externalLocalExport.connector_run_target_created).toBe(false);
  expect(externalLocalExport.credentials_enabled).toBe(false);
  expect(externalLocalExport.network_egress_enabled).toBe(false);
  expect(externalLocalExport.raw_public_url_exposed).toBe(false);
  expect(JSON.stringify(externalLocalExport)).not.toContain('LAYER3_EXTERNAL_LOCAL_EXPORT_DIR');
  expect(externalLocalExport).not.toHaveProperty('destination_path');
  expect(externalLocalExport).not.toHaveProperty('caller_supplied_destination_path');

  const replay = await postLayer3Json(
    request,
    '/api/v1/layer3/handoff/connector/local-outbox/external-local-export/write',
    externalLocalExportPayload,
  );
  expect(replay.external_local_export_receipt_id).toBe(externalLocalExport.external_local_export_receipt_id);
  expect(replay.export_operation_state).toBe('external_local_export_replay');

  const externalLocalExportStatus = await expectJson(
    await request.get(
      `/api/v1/layer3/handoff/connector/local-outbox/external-local-export/status/${externalLocalExport.external_local_export_receipt_id}`,
    ),
  );
  expect(externalLocalExportStatus.schema_id).toBe('layer3.external_local_export.status.v1');
  expect(externalLocalExportStatus.external_local_export_state).toBe('external_local_export_written');
  expect(externalLocalExportStatus.external_local_export_receipt_id).toBe(
    externalLocalExport.external_local_export_receipt_id,
  );
  expect(JSON.stringify(externalLocalExportStatus)).not.toContain('LAYER3_EXTERNAL_LOCAL_EXPORT_DIR');
  expect(externalLocalExportStatus).not.toHaveProperty('destination_path');
  expect(externalLocalExportStatus).not.toHaveProperty('caller_supplied_destination_path');

  return {
    ...setup,
    externalLocalExport,
    externalLocalExportStatus,
  };
}

test('Layer 3 workbench prepares handoff and dispatches bounded APS handoff after approved package review', async ({ page, request }) => {
  const setup = await prepareExecutedLayer3Session(request, '/__test/layer3/seed-aps-handoff');

  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);
  await attachSessionToWorkbench(page, setup.seed.session_id);

  const summaryResponsePromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#result-review-refresh').click();
  await expectJson(await summaryResponsePromise);

  const statusResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/execution/result/status'));
  await page.locator('#result-status-inspect').click();
  const status = await expectJson(await statusResponsePromise);
  expect(status.result_status_available).toBe(true);

  await expect(page.locator('#result-review-submit')).toBeEnabled();
  const reviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/execution/result/review'));
  const postReviewSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#result-review-submit').click();
  const review = await expectJson(await reviewResponsePromise);
  expect(review.review_state).toBe('execution_result_review_approved');
  await expectJson(await postReviewSummaryPromise);

  await expect(page.locator('#package-review-preview-inspect')).toBeEnabled();
  const previewRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/package/review/preview'));
  const previewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/preview'));
  await page.locator('#package-review-preview-inspect').click();
  const previewRequest = await previewRequestPromise;
  const previewPayload = previewRequest.postDataJSON();
  const expectedPreviewKeys = [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'result_review_record_ref',
  ];
  if (previewPayload.analysis_run_id) expectedPreviewKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(previewPayload, expectedPreviewKeys);
  expect(previewPayload.session_id).toBe(setup.seed.session_id);
  expect(previewPayload.analysis_plan_id).toBe(setup.approval.analysis_plan_id);
  expect(previewPayload.pass_run_id).toBe(setup.passRunId);
  expect(previewPayload.preview_id).toBe(setup.planPreview.preview_id);
  expect(previewPayload.preview_hash).toBe(setup.planPreview.preview_hash);
  expect(previewPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(previewPayload).not.toHaveProperty('package');
  expect(previewPayload).not.toHaveProperty('handoff');
  expect(previewPayload).not.toHaveProperty('rerun');
  expect(previewPayload).not.toHaveProperty('rewrite_output');

  const preview = await expectJson(await previewResponsePromise);
  expect(preview.schema_id).toBe('layer3.package_review_preview.v1');
  expect(preview.status).toBe('available');
  expect(preview.package_review_preview_enabled).toBe(true);
  expect(preview.package_commit_enabled).toBe(true);
  expect(preview.package_review_enabled).toBe(false);
  expect(preview.package_review_preview_hash).toEqual(expect.any(String));
  expect(preview.candidate_package_kinds.map((item) => item.package_kind)).toEqual([
    'canonical_internal',
    'user_facing',
    'review_facing',
  ]);
  expect(preview.downstream_unavailable).toEqual(['package_review_submit', 'handoff', 'export']);

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_preview_ready');
  await expect(page.locator('#package-review-preview-panel')).toContainText('canonical_internal');
  await expect(page.locator('#package-review-preview-panel')).toContainText('user_facing');
  await expect(page.locator('#package-review-preview-panel')).toContainText('review_facing');
  await expect(page.locator('#package-review-preview-panel')).toContainText('package review submit');
  await expect(page.locator('#package-review-preview-panel')).toContainText('handoff');
  await expect(page.locator('#package-construction-commit')).toBeEnabled();
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expectStepAvailable(page, 'package');

  const postCommitSummaryPattern = `**/api/v1/layer3/session/${setup.seed.session_id}`;
  const blockPostCommitSummary = async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({
        schema_id: 'layer3.workbench_error.v1',
        error_code: 'forced_post_commit_session_refresh_failure',
        message: 'Forced post-commit session refresh failure for UI fallback proof.',
      }),
    });
    await page.unroute(postCommitSummaryPattern, blockPostCommitSummary);
  };
  await page.route(postCommitSummaryPattern, blockPostCommitSummary);

  const commitRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/package/review/commit'));
  const commitResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/commit'));
  const postCommitSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#package-construction-commit').click();
  const commitRequest = await commitRequestPromise;
  const commitPayload = commitRequest.postDataJSON();
  const expectedCommitKeys = [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'result_review_record_ref',
    'package_review_preview_hash',
    'expected_package_kinds',
  ];
  if (commitPayload.analysis_run_id) expectedCommitKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(commitPayload, expectedCommitKeys);
  expect(commitPayload.package_review_preview_hash).toBe(preview.package_review_preview_hash);
  expect(commitPayload.expected_package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
  expect(commitPayload).not.toHaveProperty('package');
  expect(commitPayload).not.toHaveProperty('handoff');
  expect(commitPayload).not.toHaveProperty('export');
  expect(commitPayload).not.toHaveProperty('package_payload');

  const commit = await expectJson(await commitResponsePromise);
  expect(commit.schema_id).toBe('layer3.package_construction_commit.v1');
  expect(commit.status).toBe('committed');
  expect(commit.next_state).toBe('package_constructed');
  expect(commit.package_review_submit_enabled).toBe(true);
  expect(commit.handoff_enabled).toBe(false);
  expect(commit.downstream_unavailable).toEqual(['handoff', 'export']);
  expect(commit.output_packages).toHaveLength(3);
  expect((await postCommitSummaryPromise).status()).toBe(503);

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_constructed');
  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_submit_ready');
  await expect(page.locator('#package-construction-commit')).toBeDisabled();
  await expect(page.locator('#package-review-submit')).toBeEnabled();

  const submitRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/package/review/submit'));
  const submitResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/submit'));
  const postSubmitSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#package-review-submit').click();
  const submitRequest = await submitRequestPromise;
  const submitPayload = submitRequest.postDataJSON();
  const expectedSubmitKeys = [
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
  ];
  if (submitPayload.analysis_run_id) expectedSubmitKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(submitPayload, expectedSubmitKeys);
  expect(submitPayload.operator_decision).toBe('approved');
  expect(submitPayload.decision_notes).toBe('');
  expect(submitPayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect([...submitPayload.output_package_ids].sort()).toEqual([...commit.output_packages.map((item) => item.output_package_id)].sort());
  expect(submitPayload.payload_refs).toEqual(commit.payload_refs);
  expect(submitPayload.payload_hashes).toEqual(commit.payload_hashes);
  expect(submitPayload.construction_basis_hash).toBe(commit.construction_basis_hash);
  expect(submitPayload.expected_package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
  expect(submitPayload).not.toHaveProperty('package');
  expect(submitPayload).not.toHaveProperty('handoff');
  expect(submitPayload).not.toHaveProperty('export');
  expect(submitPayload).not.toHaveProperty('package_payload');
  expect(submitPayload).not.toHaveProperty('rebuild_package');

  const submit = await expectJson(await submitResponsePromise);
  expect(submit.schema_id).toBe('layer3.package_review_submit.v1');
  expect(submit.status).toBe('submitted');
  expect(submit.package_review_state).toBe('package_review_approved');
  expect(submit.operator_decision).toBe('approved');
  expect(submit.package_review_submit_enabled).toBe(false);
  expect(submit.handoff_enabled).toBe(false);
  expect(submit.export_enabled).toBe(false);
  expect(submit.downstream_unavailable).toEqual(['aps_handoff', 'external_export', 'downstream_dispatch']);
  await expectJson(await postSubmitSummaryPromise);

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_approved');
  await expect(page.locator('#package-review-submit')).toBeDisabled();
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('handoff_export_ready');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('internal_export_envelope');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('prepare_only');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeEnabled();

  await page.locator('#handoff-export-prepare-decision').selectOption('hold');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await page.locator('#handoff-export-prepare-notes').fill('Holding the preparation requires notes.');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeEnabled();
  await page.locator('#handoff-export-prepare-decision').selectOption('authorize_prepare');
  await page.locator('#handoff-export-prepare-notes').fill('');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeEnabled();

  const prepareRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/export/prepare'));
  const prepareResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/export/prepare'));
  const postPrepareSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#handoff-export-prepare-submit').click();
  const prepareRequest = await prepareRequestPromise;
  const preparePayload = prepareRequest.postDataJSON();
  const committedPackageIds = commit.output_packages.map((item) => item.output_package_id);
  const expectedPrepareKeys = [
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
    'package_review_submit_record_ref',
    'package_review_state',
    'package_review_submit_schema_id',
    'handoff_target',
    'export_mode',
    'operator_decision',
    'expected_package_kinds',
  ];
  if (preparePayload.analysis_run_id) expectedPrepareKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(preparePayload, expectedPrepareKeys);
  expect(preparePayload.session_id).toBe(setup.seed.session_id);
  expect(preparePayload.analysis_plan_id).toBe(setup.approval.analysis_plan_id);
  expect(preparePayload.pass_run_id).toBe(setup.passRunId);
  expect(preparePayload.preview_id).toBe(setup.planPreview.preview_id);
  expect(preparePayload.preview_hash).toBe(setup.planPreview.preview_hash);
  expect(preparePayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(preparePayload.package_review_preview_hash).toBe(preview.package_review_preview_hash);
  expect(preparePayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(preparePayload.package_review_submit_record_ref).toBe(submit.submit_record_ref);
  expect(preparePayload.package_review_state).toBe('package_review_approved');
  expect(preparePayload.package_review_submit_schema_id).toBe(submit.schema_id);
  expect(preparePayload.handoff_target).toBe('internal_export_envelope');
  expect(preparePayload.export_mode).toBe('prepare_only');
  expect(preparePayload.operator_decision).toBe('authorize_prepare');
  expect([...preparePayload.output_package_ids].sort()).toEqual([...committedPackageIds].sort());
  expect(preparePayload.payload_refs).toEqual(commit.payload_refs);
  expect(preparePayload.payload_hashes).toEqual(commit.payload_hashes);
  expect(preparePayload.expected_package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
  for (const forbidden of [
    'aps_handoff',
    'dispatch',
    'send',
    'external_export',
    'download',
    'connector_run_id',
    'runtime_db_write',
    'analysis_artifact',
    'artifact_manifest',
    'create_package',
    'rebuild_package',
    'package_payload',
    'rewrite_output',
  ]) {
    expect(preparePayload).not.toHaveProperty(forbidden);
  }

  const prepare = await expectJson(await prepareResponsePromise);
  expect(prepare.schema_id).toBe('layer3.handoff_export_prepare.v1');
  expect(prepare.status).toBe('prepared');
  expect(prepare.handoff_export_state).toBe('handoff_export_prepared');
  expect(prepare.handoff_target).toBe('internal_export_envelope');
  expect(prepare.export_mode).toBe('prepare_only');
  expect(prepare.external_handoff_enabled).toBe(false);
  expect(prepare.external_export_enabled).toBe(false);
  expect(prepare.dispatch_enabled).toBe(false);
  expect(prepare.downstream_unavailable).toEqual(['aps_handoff', 'external_export', 'downstream_dispatch']);
  expect([...prepare.handoff_export_envelope.output_package_ids].sort()).toEqual([...committedPackageIds].sort());
  expect(prepare.handoff_export_envelope.payload_refs).toEqual(commit.payload_refs);
  expect(prepare.handoff_export_envelope.payload_hashes).toEqual(commit.payload_hashes);
  await expectJson(await postPrepareSummaryPromise);

  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('handoff_export_prepared');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('aps handoff');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('external export');
  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('downstream dispatch');
  await expectRenderedDownstreamAccessLifecycleDashboard(page, 'aps_handoff_ready', [
    'handoff/export prepare',
    'prepare_only',
    prepare.prepare_record_ref,
  ]);
  await expectRenderedLayer3E2EGovernanceLifecycleDashboard(page, 'layer3_e2e_latest_downstream_access', [
    'package lifecycle',
    'handoff/export',
    'downstream access',
  ]);
  await expect(page.locator('#handoff-export-prepare-submit')).toBeDisabled();
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_handoff_ready');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_evidence_bundle');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('server_side_aps_handoff');
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeEnabled();
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();

  const dispatchRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/aps/dispatch'));
  const dispatchResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/aps/dispatch'));
  const postDispatchSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#aps-handoff-dispatch-submit').click();
  const dispatchRequest = await dispatchRequestPromise;
  const dispatchPayload = dispatchRequest.postDataJSON();
  const expectedDispatchKeys = [
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
    'package_kinds',
    'payload_refs',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
    'prepare_record_ref',
    'handoff_export_state',
    'handoff_export_envelope_ref',
    'handoff_target',
    'export_mode',
    'aps_handoff_target',
    'dispatch_mode',
    'operator_decision',
  ];
  if (dispatchPayload.analysis_run_id) expectedDispatchKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(dispatchPayload, expectedDispatchKeys);
  expect(dispatchPayload.session_id).toBe(setup.seed.session_id);
  expect(dispatchPayload.analysis_plan_id).toBe(setup.approval.analysis_plan_id);
  expect(dispatchPayload.pass_run_id).toBe(setup.passRunId);
  expect(dispatchPayload.preview_id).toBe(setup.planPreview.preview_id);
  expect(dispatchPayload.preview_hash).toBe(setup.planPreview.preview_hash);
  expect(dispatchPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(dispatchPayload.package_review_preview_hash).toBe(preview.package_review_preview_hash);
  expect(dispatchPayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(dispatchPayload.package_review_submit_record_ref).toBe(submit.submit_record_ref);
  expect(dispatchPayload.package_review_state).toBe('package_review_approved');
  expect(dispatchPayload.prepare_record_ref).toBe(prepare.prepare_record_ref);
  expect(dispatchPayload.handoff_export_state).toBe('handoff_export_prepared');
  expect(dispatchPayload.handoff_export_envelope_ref).toBe(prepare.handoff_export_envelope.envelope_ref);
  expect(dispatchPayload.handoff_target).toBe('internal_export_envelope');
  expect(dispatchPayload.export_mode).toBe('prepare_only');
  expect(dispatchPayload.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(dispatchPayload.dispatch_mode).toBe('server_side_aps_handoff');
  expect(dispatchPayload.operator_decision).toBe('dispatch_aps_handoff');
  expect([...dispatchPayload.output_package_ids].sort()).toEqual([...committedPackageIds].sort());
  expect(dispatchPayload.package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
  expect(dispatchPayload.payload_refs).toEqual(commit.payload_refs);
  expect(dispatchPayload.payload_hashes).toEqual(commit.payload_hashes);
  for (const forbidden of [
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
    'expected_package_kinds',
  ]) {
    expect(dispatchPayload).not.toHaveProperty(forbidden);
  }

  const dispatch = await expectJson(await dispatchResponsePromise);
  expect(dispatch.schema_id).toBe('layer3.aps_handoff_dispatch.v1');
  expect(dispatch.status).toBe('dispatched');
  expect(dispatch.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(dispatch.aps_output_package_kind).toBe('aps_evidence_bundle_handoff');
  expect(dispatch.external_export_enabled).toBe(false);
  expect(dispatch.download_enabled).toBe(false);
  expect(dispatch.connector_dispatch_enabled).toBe(false);
  expect(dispatch.downstream_unavailable).toEqual(['external_export', 'download', 'connector_dispatch', 'non_aps_dispatch']);
  const postDispatchSummary = await expectJson(await postDispatchSummaryPromise);
  expect(postDispatchSummary.external_export_download.state).toBe('external_export_download_ready');
  expect(postDispatchSummary.external_export_download.available).toBe(true);

  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_handoff_dispatched');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_evidence_bundle_handoff');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('external export');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('download');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('connector dispatch');
  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('non aps dispatch');
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('external_export_download_ready');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('aps_evidence_bundle_download_reference');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('reference_only_prepare');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('browser download');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('download url');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('connector dispatch');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('destination selection');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('generic downstream dispatch');
  await expect(page.locator('#external-export-download-prepare-submit')).toBeEnabled();

  const externalRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/export/download/prepare'));
  const externalResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/export/download/prepare'));
  const postExternalSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#external-export-download-prepare-submit').click();
  const externalRequest = await externalRequestPromise;
  const externalPayload = externalRequest.postDataJSON();
  const expectedExternalKeys = [
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
    'package_kinds',
    'payload_refs',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
    'prepare_record_ref',
    'handoff_export_state',
    'handoff_export_envelope_ref',
    'handoff_target',
    'export_mode',
    'aps_handoff_record_ref',
    'aps_handoff_state',
    'aps_handoff_target',
    'dispatch_mode',
    'aps_output_package_id',
    'aps_output_package_kind',
    'aps_bundle_ref',
    'aps_bundle_id',
    'aps_schema_id',
    'export_download_target',
    'download_mode',
    'operator_decision',
    'aps_bundle_hash',
    'aps_bundle_size_bytes',
  ];
  if (externalPayload.analysis_run_id) expectedExternalKeys.push('analysis_run_id');
  expectOnlyPayloadKeys(externalPayload, expectedExternalKeys);
  expect(externalPayload.session_id).toBe(setup.seed.session_id);
  expect(externalPayload.analysis_plan_id).toBe(setup.approval.analysis_plan_id);
  expect(externalPayload.pass_run_id).toBe(setup.passRunId);
  expect(externalPayload.preview_id).toBe(setup.planPreview.preview_id);
  expect(externalPayload.preview_hash).toBe(setup.planPreview.preview_hash);
  expect(externalPayload.result_review_record_ref).toBe(review.review_record_ref);
  expect(externalPayload.package_review_preview_hash).toBe(preview.package_review_preview_hash);
  expect(externalPayload.reconciliation_record_id).toBe(commit.reconciliation_record_id);
  expect(externalPayload.package_review_submit_record_ref).toBe(submit.submit_record_ref);
  expect(externalPayload.package_review_state).toBe('package_review_approved');
  expect(externalPayload.prepare_record_ref).toBe(prepare.prepare_record_ref);
  expect(externalPayload.handoff_export_state).toBe('handoff_export_prepared');
  expect(externalPayload.handoff_export_envelope_ref).toBe(prepare.handoff_export_envelope.envelope_ref);
  expect(externalPayload.handoff_target).toBe('internal_export_envelope');
  expect(externalPayload.export_mode).toBe('prepare_only');
  expect(externalPayload.aps_handoff_record_ref).toBe(dispatch.aps_handoff_record_ref);
  expect(externalPayload.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(externalPayload.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(externalPayload.dispatch_mode).toBe('server_side_aps_handoff');
  expect(externalPayload.aps_output_package_id).toBe(dispatch.aps_output_package_id);
  expect(externalPayload.aps_output_package_kind).toBe('aps_evidence_bundle_handoff');
  expect(externalPayload.aps_bundle_ref).toBe(dispatch.aps_bundle_ref);
  expect(externalPayload.aps_bundle_id).toBe(dispatch.aps_bundle_id);
  expect(externalPayload.aps_schema_id).toBe(dispatch.aps_schema_id);
  expect(externalPayload.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(externalPayload.download_mode).toBe('reference_only_prepare');
  expect(externalPayload.operator_decision).toBe('prepare_external_export_download');
  expect(externalPayload.aps_bundle_hash).toBe(postDispatchSummary.external_export_download.source_artifact_hash);
  expect(externalPayload.aps_bundle_size_bytes).toBe(postDispatchSummary.external_export_download.source_artifact_size_bytes);
  expect([...externalPayload.output_package_ids].sort()).toEqual([...committedPackageIds].sort());
  expect(externalPayload.package_kinds).toEqual(['canonical_internal', 'user_facing', 'review_facing']);
  expect(externalPayload.payload_refs).toEqual(commit.payload_refs);
  expect(externalPayload.payload_hashes).toEqual(commit.payload_hashes);
  for (const forbidden of [
    'download_url',
    'public_url',
    'signed_url',
    'stream_file',
    'browser_download',
    'external_export',
    'send',
    'dispatch',
    'generic_dispatch',
    'connector_run_id',
    'connector_dispatch',
    'destination',
    'destination_id',
    'external_target',
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
    'handoff_export_amendment',
    'aps_handoff_amendment',
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
    expect(externalPayload).not.toHaveProperty(forbidden);
  }

  const external = await expectJson(await externalResponsePromise);
  expect(external.schema_id).toBe('layer3.external_export_download_prepare.v1');
  expect(external.status).toBe('prepared');
  expect(external.external_export_download_state).toBe('external_export_download_prepared');
  expect(external.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(external.download_mode).toBe('reference_only_prepare');
  expect(external.operator_decision).toBe('prepare_external_export_download');
  expect(external.browser_download_enabled).toBe(false);
  expect(external.download_url_enabled).toBe(false);
  expect(external.connector_dispatch_enabled).toBe(false);
  expect(external.destination_selection_enabled).toBe(false);
  expect(external.generic_downstream_dispatch_enabled).toBe(false);
  expect(external.downstream_unavailable).toEqual([
    'browser_download',
    'download_url',
    'connector_dispatch',
    'destination_selection',
    'generic_downstream_dispatch',
  ]);
  expect(external.external_export_download_descriptor.browser_download_enabled).toBe(false);
  expect(external.external_export_download_descriptor.download_url_enabled).toBe(false);
  const postExternalSummary = await expectJson(await postExternalSummaryPromise);
  expect(postExternalSummary.external_export_download.state).toBe('external_export_download_prepared');
  expect(postExternalSummary.external_export_download.available).toBe(false);

  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('external_export_download_prepared');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText(external.export_download_descriptor_ref);
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('browser download');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('download url');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('connector dispatch');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('destination selection');
  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('generic downstream dispatch');
  await expectRenderedDownstreamAccessLifecycleDashboard(page, 'external_export_download_prepared', [
    'external export/download readiness',
    external.external_export_download_record_ref,
    'reference_only_prepare',
  ]);
  await expectRenderedLayer3E2EGovernanceLifecycleDashboard(page, 'layer3_e2e_latest_downstream_access', [
    'external export/download readiness',
    external.external_export_download_record_ref,
  ]);
  await expect(page.locator('#external-export-download-prepare-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('external_export_download_delivery_ui_ready');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(external.external_export_download_record_ref);
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('same_origin_artifact_stream');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('public url');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('signed url');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('connector dispatch');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('destination selection');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('generic downstream dispatch');
  await expect(page.locator('#external-export-download-delivery-submit')).toBeEnabled();
  await expect(page.locator('#connector-local-destination-receipt-panel')).toContainText('rendered_connector_local_destination_receipt_read_only_status_surface');
  await expect(page.locator('#connector-local-destination-receipt-panel button, #connector-local-destination-receipt-panel input, #connector-local-destination-receipt-panel select, #connector-local-destination-receipt-panel textarea')).toHaveCount(0);

  const deliveryRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/export/download/deliver'));
  const deliveryResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/export/download/deliver'));
  const downloadPromise = page.waitForEvent('download');
  const postDeliverySummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.seed.session_id}`));
  await page.locator('#external-export-download-delivery-submit').click();
  const deliveryRequest = await deliveryRequestPromise;
  expect(deliveryRequest.headers()['content-type']).toContain('application/x-www-form-urlencoded');
  const deliveryPayload = formPostPayload(deliveryRequest);
  const expectedDeliveryKeys = [
    ...expectedExternalKeys.filter((key) => key !== 'operator_decision'),
    'operator_decision',
    'external_export_download_record_ref',
    'export_download_descriptor_ref',
    'external_export_download_state',
    'delivery_mode',
  ];
  expectOnlyPayloadKeys(deliveryPayload, expectedDeliveryKeys);
  expect(deliveryPayload.operator_decision).toBe('deliver_external_export_download');
  expect(deliveryPayload.external_export_download_record_ref).toBe(external.external_export_download_record_ref);
  expect(deliveryPayload.export_download_descriptor_ref).toBe(external.export_download_descriptor_ref);
  expect(deliveryPayload.external_export_download_state).toBe('external_export_download_prepared');
  expect(deliveryPayload.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(deliveryPayload.download_mode).toBe('reference_only_prepare');
  expect(deliveryPayload.delivery_mode).toBe('same_origin_artifact_stream');
  for (const forbidden of [
    'download_url',
    'download_token',
    'public_url',
    'signed_url',
    'local_file_path',
    'external_target',
    'destination',
    'destination_selector',
    'destination_id',
    'connector_run_id',
    'connector_dispatch',
    'generic_dispatch',
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
    'handoff_export_amendment',
    'aps_handoff_amendment',
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
    expect(deliveryPayload).not.toHaveProperty(forbidden);
  }

  const deliveryResponse = await deliveryResponsePromise;
  expect(deliveryResponse.status()).toBe(200);
  const deliveryHeaders = deliveryResponse.headers();
  expect(deliveryHeaders['x-layer3-schema-id']).toBe('layer3.external_export_download_delivery.v1');
  expect(deliveryHeaders['x-layer3-delivery-state']).toBe('external_export_download_delivered');
  expect(deliveryHeaders['x-layer3-external-export-download-record-ref']).toBe(external.external_export_download_record_ref);
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain('layer3-');
  const postDeliverySummary = await expectJson(await postDeliverySummaryPromise);
  expect(postDeliverySummary.external_export_download.state).toBe('external_export_download_prepared');

  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('external_export_download_delivery_submitted');
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText(deliveryHeaders['x-layer3-source-artifact-hash']);
  await expectRenderedDownstreamAccessLifecycleDashboard(page, 'external_export_download_delivery_submitted', [
    'same-origin delivery',
    'same_origin_artifact_stream',
    external.external_export_download_record_ref,
  ]);
  await expectRenderedLayer3E2EGovernanceLifecycleDashboard(page, 'layer3_e2e_latest_downstream_access', [
    'same-origin delivery',
    'same_origin_artifact_stream',
  ]);
  await expect(page.locator('#external-export-download-delivery-submit')).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Create Package' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Export' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Download' })).toHaveCount(0);
});

test('Layer 3 workbench drives qualitative APS package handoff to external readiness with delivery UI gated', async ({ page, request }) => {
  const setup = await prepareQualitativeApsResultReviewSession(request);
  const sessionId = setup.gateB.session_id;

  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);
  await attachSessionToWorkbench(page, sessionId, ['aps_content_document']);

  const summaryResponsePromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${sessionId}`));
  await page.locator('#result-review-refresh').click();
  const initialSummary = await expectJson(await summaryResponsePromise);
  expect(initialSummary.execution_result_review.review_state).toBe('execution_result_review_approved');

  await expect(page.locator('#package-review-preview-inspect')).toBeEnabled();
  await expect(page.locator('input[type="file"]:not(#source-intake-file)')).toHaveCount(0);

  const packagePreviewRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/package/review/preview'));
  const packagePreviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/preview'));
  await page.locator('#package-review-preview-inspect').click();
  const packagePreviewPayload = (await packagePreviewRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(packagePreviewPayload, [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'result_review_record_ref',
  ]);
  expect(packagePreviewPayload.result_review_record_ref).toBe(setup.review.review_record_ref);
  expect(packagePreviewPayload).not.toHaveProperty('analysis_run_id');
  const packagePreview = await expectJson(await packagePreviewResponsePromise);
  expect(packagePreview.schema_id).toBe('layer3.qual_aps_package_review_preview.v1');
  expect(packagePreview.package_commit_enabled).toBe(true);

  await expect(page.locator('#package-construction-commit')).toBeEnabled();
  const commitRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/package/review/commit'));
  const commitResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/commit'));
  const postCommitSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${sessionId}`));
  await page.locator('#package-construction-commit').click();
  const commitPayload = (await commitRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(commitPayload, [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'result_review_record_ref',
    'package_review_preview_hash',
    'expected_package_kinds',
  ]);
  expect(commitPayload.package_review_preview_hash).toBe(packagePreview.package_review_preview_hash);
  expect(commitPayload).not.toHaveProperty('analysis_run_id');
  const commit = await expectJson(await commitResponsePromise);
  expect(commit.schema_id).toBe('layer3.qual_aps_package_construction_commit.v1');
  expect(commit.package_construction_source_gate).toBe('140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE');
  expect(commit.package_review_submit_enabled).toBe(true);
  await expectJson(await postCommitSummaryPromise);

  await page.reload({ waitUntil: 'domcontentloaded' });
  await attachSessionToWorkbench(page, sessionId, ['aps_content_document']);
  const resumedSummaryResponsePromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${sessionId}`));
  await page.locator('#result-review-refresh').click();
  const resumedSummary = await expectJson(await resumedSummaryResponsePromise);
  expect(resumedSummary.package_construction.state).toBe('package_constructed');
  expect(resumedSummary.package_review_submit.state).toBe('package_review_submit_ready');
  expect(resumedSummary.package_review_submit.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(resumedSummary.package_review_submit.construction_basis_hash).toBe(commit.construction_basis_hash);
  expect(resumedSummary.package_review_submit.payload_refs).toEqual(commit.payload_refs);
  expect(resumedSummary.package_review_submit.payload_hashes).toEqual(commit.payload_hashes);

  await expect(page.locator('#package-review-preview-panel')).toContainText('package_review_submit_ready');
  await expect(page.locator('#package-review-submit')).toBeEnabled();

  const submitRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/package/review/submit'));
  const submitResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/package/review/submit'));
  const postSubmitSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${sessionId}`));
  await page.locator('#package-review-submit').click();
  const submitPayload = (await submitRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(submitPayload, [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'result_review_record_ref',
    'package_review_preview_hash',
    'construction_basis_hash',
    'reconciliation_record_id',
    'output_package_ids',
    'payload_refs',
    'payload_hashes',
    'operator_decision',
    'decision_notes',
    'expected_package_kinds',
  ]);
  expect(submitPayload.session_id).toBe(sessionId);
  expect(submitPayload.analysis_plan_id).toBe(setup.approval.analysis_plan_id);
  expect(submitPayload.pass_run_id).toBe(setup.passRunId);
  expect(submitPayload.preview_id).toBe(setup.planPreview.preview_id);
  expect(submitPayload.preview_hash).toBe(setup.planPreview.preview_hash);
  expect(submitPayload.result_review_record_ref).toBe(setup.review.review_record_ref);
  expect(submitPayload.package_review_preview_hash).toBe(commit.package_review_preview_hash);
  expect(submitPayload.construction_basis_hash).toBe(commit.construction_basis_hash);
  expect(submitPayload.operator_decision).toBe('approved');
  expect(submitPayload).not.toHaveProperty('analysis_run_id');
  expect(submitPayload).not.toHaveProperty('provider_url');
  expect(submitPayload).not.toHaveProperty('connector_dispatch');
  expect(submitPayload).not.toHaveProperty('package_payload');

  const submit = await expectJson(await submitResponsePromise);
  expect(submit.schema_id).toBe('layer3.qual_aps_package_review_submit.v1');
  expect(submit.package_review_state).toBe('package_review_approved');
  await expectJson(await postSubmitSummaryPromise);

  await expect(page.locator('#handoff-export-prepare-panel')).toContainText('handoff_export_ready');
  await expect(page.locator('#handoff-export-prepare-submit')).toBeEnabled();

  const prepareRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/export/prepare'));
  const prepareResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/export/prepare'));
  const postPrepareSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${sessionId}`));
  await page.locator('#handoff-export-prepare-submit').click();
  const preparePayload = (await prepareRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(preparePayload, [
    'client_request_id',
    'session_id',
    'analysis_plan_id',
    'pass_run_id',
    'preview_id',
    'preview_hash',
    'result_review_record_ref',
    'package_review_preview_hash',
    'construction_basis_hash',
    'reconciliation_record_id',
    'output_package_ids',
    'payload_refs',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
    'package_review_submit_schema_id',
    'handoff_target',
    'export_mode',
    'operator_decision',
    'expected_package_kinds',
  ]);
  expect(preparePayload.package_review_submit_schema_id).toBe('layer3.qual_aps_package_review_submit.v1');
  expect(preparePayload.construction_basis_hash).toBe(commit.construction_basis_hash);
  expect(preparePayload.handoff_target).toBe('internal_export_envelope');
  expect(preparePayload.export_mode).toBe('prepare_only');
  expect(preparePayload.operator_decision).toBe('authorize_prepare');
  expect(preparePayload).not.toHaveProperty('analysis_run_id');
  expect(preparePayload).not.toHaveProperty('external_export');
  expect(preparePayload).not.toHaveProperty('connector_run_id');

  const prepare = await expectJson(await prepareResponsePromise);
  expect(prepare.schema_id).toBe('layer3.qual_aps_handoff_export_prepare.v1');
  expect(prepare.handoff_export_state).toBe('handoff_export_prepared');
  expect(prepare.analysis_run_id).toBeNull();
  await expectJson(await postPrepareSummaryPromise);

  await expect(page.locator('#aps-handoff-dispatch-panel')).toContainText('aps_handoff_ready');
  await expect(page.locator('#aps-handoff-dispatch-submit')).toBeEnabled();

  const dispatchRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/aps/dispatch'));
  const dispatchResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/aps/dispatch'));
  const postDispatchSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${sessionId}`));
  await page.locator('#aps-handoff-dispatch-submit').click();
  const dispatchPayload = (await dispatchRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(dispatchPayload, [
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
    'package_kinds',
    'payload_refs',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
    'prepare_record_ref',
    'handoff_export_state',
    'handoff_export_envelope_ref',
    'handoff_target',
    'export_mode',
    'aps_handoff_target',
    'dispatch_mode',
    'operator_decision',
  ]);
  expect(dispatchPayload.aps_handoff_target).toBe('aps_evidence_bundle');
  expect(dispatchPayload.dispatch_mode).toBe('server_side_aps_handoff');
  expect(dispatchPayload.operator_decision).toBe('dispatch_aps_handoff');
  expect(dispatchPayload).not.toHaveProperty('analysis_run_id');
  expect(dispatchPayload).not.toHaveProperty('download_url');
  expect(dispatchPayload).not.toHaveProperty('destination');

  const dispatch = await expectJson(await dispatchResponsePromise);
  expect(dispatch.schema_id).toBe('layer3.qual_aps_aps_handoff_dispatch.v1');
  expect(dispatch.aps_handoff_state).toBe('aps_handoff_dispatched');
  expect(dispatch.analysis_run_id).toBeNull();
  const postDispatchSummary = await expectJson(await postDispatchSummaryPromise);
  expect(postDispatchSummary.external_export_download.available).toBe(true);
  expect(postDispatchSummary.external_export_download.state).toBe('external_export_download_ready');

  await expect(page.locator('#external-export-download-prepare-panel')).toContainText('external_export_download_ready');
  await expect(page.locator('#external-export-download-prepare-submit')).toBeEnabled();

  const externalRequestPromise = page.waitForRequest((req) => req.url().includes('/api/v1/layer3/handoff/export/download/prepare'));
  const externalResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/handoff/export/download/prepare'));
  const postExternalSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${sessionId}`));
  await page.locator('#external-export-download-prepare-submit').click();
  const externalPayload = (await externalRequestPromise).postDataJSON();
  expectOnlyPayloadKeys(externalPayload, [
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
    'package_kinds',
    'payload_refs',
    'payload_hashes',
    'package_review_submit_record_ref',
    'package_review_state',
    'prepare_record_ref',
    'handoff_export_state',
    'handoff_export_envelope_ref',
    'handoff_target',
    'export_mode',
    'aps_handoff_record_ref',
    'aps_handoff_state',
    'aps_handoff_target',
    'dispatch_mode',
    'aps_output_package_id',
    'aps_output_package_kind',
    'aps_bundle_ref',
    'aps_bundle_id',
    'aps_schema_id',
    'export_download_target',
    'download_mode',
    'operator_decision',
    'aps_bundle_hash',
    'aps_bundle_size_bytes',
  ]);
  expect(externalPayload.export_download_target).toBe('aps_evidence_bundle_download_reference');
  expect(externalPayload.download_mode).toBe('reference_only_prepare');
  expect(externalPayload.operator_decision).toBe('prepare_external_export_download');
  expect(externalPayload.aps_bundle_hash).toBe(postDispatchSummary.external_export_download.source_artifact_hash);
  expect(externalPayload.aps_bundle_size_bytes).toBe(postDispatchSummary.external_export_download.source_artifact_size_bytes);
  expect(externalPayload).not.toHaveProperty('analysis_run_id');
  expect(externalPayload).not.toHaveProperty('public_url');
  expect(externalPayload).not.toHaveProperty('signed_url');
  expect(externalPayload).not.toHaveProperty('connector_dispatch');

  const external = await expectJson(await externalResponsePromise);
  expect(external.schema_id).toBe('layer3.qual_aps_external_export_download_prepare.v1');
  expect(external.external_export_download_state).toBe('external_export_download_prepared');
  expect(external.delivery_ui).toBeNull();
  const postExternalSummary = await expectJson(await postExternalSummaryPromise);
  expect(postExternalSummary.external_export_download.state).toBe('external_export_download_prepared');
  expect(postExternalSummary.external_export_download.delivery_ui ?? null).toBeNull();

  await expect(page.locator('#external-export-download-delivery-submit')).toBeDisabled();
  await expect(page.locator('#external-export-download-delivery-panel')).toContainText('external_export_download_delivery_ui_unavailable');
  await expect(page.locator('#external-export-download-signed-reference-generate')).toBeDisabled();
  await expect(page.locator('#external-export-download-signed-reference-panel')).toContainText('external_export_download_signed_reference_ui_blocked');
  const uploadButtonIds = await page.getByRole('button', { name: /upload/i }).evaluateAll((buttons) => (
    buttons.map((button) => button.id).sort()
  ));
  expect(uploadButtonIds.filter((id) => id !== 'source-intake-upload-submit')).toEqual([]);
  await expect(page.getByRole('button', {
    name: /ingest|local directory|web connector|rag|vector|provider url|public url|connector dispatch|destination|mockup|auth/i,
  })).toHaveCount(0);
});

test('Layer 3 workbench can request plan revision without starting execution', async ({ page, request }) => {
  const seed = await expectJson(await request.post('/__test/layer3/seed-quant'));

  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);

  await page.evaluate((sessionId) => {
    State.gateB = {
      session_id: sessionId,
      authority_rail: {
        session_id: sessionId,
        current_gate: 'plan',
        persistence_mode: 'durable_layer3_control',
        source_authority: { source_classes: ['dataset_version'] },
        approved_material_count: 1,
        denied_material_count: 0,
        isolated_material_count: 0,
        flagged_material_count: 0,
        typing_status: 'committed',
        execution_enabled: false,
        package_review_enabled: false,
        downstream_unavailable: ['execution', 'results', 'package'],
      },
    };
    State.gateC = {
      authority_rail: {
        session_id: sessionId,
        current_gate: 'plan',
        persistence_mode: 'durable_layer3_control',
        source_authority: { source_classes: ['dataset_version'] },
        approved_material_count: 1,
        denied_material_count: 0,
        isolated_material_count: 0,
        flagged_material_count: 0,
        typing_status: 'committed',
        execution_enabled: false,
        package_review_enabled: false,
        downstream_unavailable: ['execution', 'results', 'package'],
      },
    };
    State.planPreview = null;
    State.planApproval = null;
    State.planRevision = null;
    renderAll();
  }, seed.session_id);

  await expect(page.locator('#plan-preview')).toBeEnabled();
  await expect(page.locator('#plan-reject')).toBeDisabled();
  await expect(page.locator('#plan-request-revision')).toBeDisabled();

  const planPreviewResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/plan/preview'));
  await page.locator('#plan-preview').click();
  const planPreview = await expectJson(await planPreviewResponsePromise);
  expect(planPreview.preview_hash).toBeTruthy();

  await expect(page.locator('#plan-reject')).toBeEnabled();
  await expect(page.locator('#plan-request-revision')).toBeEnabled();
  await expect(page.locator('#plan-approve')).toBeEnabled();

  let releaseRevisionRequest;
  await page.route('**/api/v1/layer3/plan/revise', async (route) => {
    await new Promise((resolve) => {
      releaseRevisionRequest = resolve;
    });
    await route.continue();
  });

  const revisionResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/plan/revise'));
  await page.locator('#plan-request-revision').click();
  await expect(page.locator('#plan-reject')).toBeDisabled();
  await expect(page.locator('#plan-request-revision')).toBeDisabled();
  await expect.poll(() => Boolean(releaseRevisionRequest)).toBe(true);
  releaseRevisionRequest();
  const revision = await expectJson(await revisionResponsePromise);
  expect(revision.next_state).toBe('plan_revision_requested');
  expect(revision.revision_control_only).toBe(true);
  expect(revision.execution_started).toBe(false);
  expect(revision.downstream_unavailable).toEqual(['execution', 'results', 'package']);

  await expect(page.locator('#plan-panel')).toContainText('revision requested');
  await expect(page.locator('#plan-panel')).toContainText('not started');
  await expect(page.locator('#plan-preview')).toBeDisabled();
  await expect(page.locator('#plan-reject')).toBeDisabled();
  await expect(page.locator('#plan-request-revision')).toBeDisabled();
  await expect(page.locator('#plan-approve')).toBeDisabled();
  await expectStepUnavailable(page, 'execution');
  await expectStepUnavailable(page, 'results');
  await expectStepUnavailable(page, 'package');
  await expect(page.locator('#unavailable-list')).toContainText('execution');
  await expect(page.locator('#unavailable-list')).toContainText('package');
});

test('Layer 3 renders request-backed local receipt to server-owned outbox write lifecycle', async ({ page, request }) => {
  const setup = await prepareServerOwnedLocalOutboxWriteViaApi(request);
  const summary = await expectJson(await request.get(`/api/v1/layer3/session/${setup.sessionId}`));
  const writeStatus = summary.server_owned_local_outbox_write;

  expect(writeStatus.state).toBe('server_owned_local_outbox_write_recorded');
  expect(writeStatus.server_owned_local_outbox_write_receipt_id).toBe(
    setup.write.server_owned_local_outbox_write_receipt_id,
  );
  expect(writeStatus.outbox_artifact_ref).toBe(setup.write.outbox_artifact_ref);
  expect(writeStatus.write_receipt_history_count).toBe(1);
  expect(writeStatus.latest_write_receipt.server_owned_local_outbox_write_receipt_id).toBe(
    setup.write.server_owned_local_outbox_write_receipt_id,
  );
  expect(writeStatus.lifecycle_status_surface.history_listing_authority).toBe(
    'durable_server_owned_local_outbox_write_receipt_rows',
  );
  expect(writeStatus.idempotency_policy.same_key_same_payload_replay).toBe('already_recorded');
  expect(writeStatus.idempotency_policy.same_key_different_payload_conflict).toBe(
    'server_owned_local_outbox_write_client_request_conflict',
  );
  expect(writeStatus.failure_state_projection.map((entry) => entry.case)).toContain('stale_authority');
  expect(writeStatus.real_connector_invocation_enabled).toBe(false);
  expect(writeStatus.external_destination_write_enabled).toBe(false);
  expect(writeStatus.connector_run_created).toBe(false);
  expect(writeStatus.connector_run_target_created).toBe(false);

  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);
  await attachSessionToWorkbench(page, setup.sessionId);

  const renderedSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.sessionId}`));
  await page.locator('#result-review-refresh').click();
  const renderedSummary = await expectJson(await renderedSummaryPromise);
  expect(renderedSummary.server_owned_local_outbox_write.server_owned_local_outbox_write_receipt_id).toBe(
    setup.write.server_owned_local_outbox_write_receipt_id,
  );

  await expect(page.locator('#connector-local-destination-receipt-panel')).toContainText(
    setup.localReceipt.connector_local_destination_receipt_id,
  );
  await expect(page.locator('#server-owned-local-outbox-target-panel')).toContainText(
    setup.target.server_owned_local_outbox_target_receipt_id,
  );
  const writePanel = page.locator('#server-owned-local-outbox-write-panel');
  await expect(writePanel).toContainText('rendered_server_owned_local_outbox_write_read_only_status_surface');
  await expect(writePanel).toContainText('server_owned_local_outbox_write_recorded');
  await expect(writePanel).toContainText(setup.write.server_owned_local_outbox_write_receipt_id);
  await expect(writePanel).toContainText(setup.write.outbox_artifact_ref);
  await expect(writePanel).toContainText('durable_server_owned_local_outbox_write_receipt_rows');
  await expect(writePanel).toContainText('server_owned_local_outbox_write_stale_authority');
  await expect(writePanel).toContainText('real connector invocation');
  await expect(writePanel).toContainText('external destination write');
  await expect(writePanel.locator('button,input,select,textarea')).toHaveCount(0);
  await expect(writePanel).not.toContainText('C:\\');
  await expect(writePanel).not.toContainText('source_artifact_ref');
  await expect(writePanel).not.toContainText('destination_path');
});

test('Layer 3 renders local outbox provider-private handoff lifecycle as read-only status history', async ({ page, request }) => {
  const setup = await prepareLocalOutboxProviderPrivateHandoffViaApi(request);
  const summary = await expectJson(await request.get(`/api/v1/layer3/session/${setup.sessionId}`));
  const handoffStatus = summary.local_outbox_provider_private_handoff;

  expect(handoffStatus.state).toBe('local_outbox_provider_private_handoff_prepared');
  expect(handoffStatus.provider_private_handoff_receipt_id).toBe(
    setup.providerPrivate.provider_private_handoff_receipt_id,
  );
  expect(handoffStatus.provider_private_handoff_history_count).toBe(1);
  expect(handoffStatus.latest_provider_private_handoff_receipt.provider_private_handoff_receipt_id).toBe(
    setup.providerPrivate.provider_private_handoff_receipt_id,
  );
  expect(handoffStatus.audit_event_history_count).toBe(1);
  expect(handoffStatus.lifecycle_status_surface.history_listing_authority).toBe(
    'durable_local_outbox_provider_private_handoff_receipt_rows',
  );
  expect(handoffStatus.lifecycle_status_surface.audit_trail_authority).toBe(
    'durable_local_outbox_provider_private_handoff_audit_event_rows',
  );
  expect(handoffStatus.idempotency_policy.same_key_same_payload_replay).toBe('already_recorded');
  expect(handoffStatus.idempotency_policy.same_key_different_payload_conflict).toBe(
    'local_outbox_provider_private_handoff_client_request_conflict',
  );
  expect(handoffStatus.failure_state_projection.map((entry) => entry.case)).toEqual(
    expect.arrayContaining(['stale_authority', 'expired', 'fake_provider_failed']),
  );
  expect(handoffStatus.raw_token_exposed).toBe(false);
  expect(handoffStatus.provider_private_use_route_enabled).toBe(false);
  expect(handoffStatus.real_connector_invocation_enabled).toBe(false);
  expect(handoffStatus.external_destination_write_enabled).toBe(false);
  expect(handoffStatus.connector_run_created).toBe(false);
  expect(JSON.stringify(handoffStatus)).not.toContain('fake-provider-private-token');

  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);
  await attachSessionToWorkbench(page, setup.sessionId);

  const renderedSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.sessionId}`));
  await page.locator('#result-review-refresh').click();
  const renderedSummary = await expectJson(await renderedSummaryPromise);
  expect(renderedSummary.local_outbox_provider_private_handoff.provider_private_handoff_receipt_id).toBe(
    setup.providerPrivate.provider_private_handoff_receipt_id,
  );

  const handoffPanel = page.locator('#local-outbox-provider-private-handoff-panel');
  await expect(handoffPanel).toContainText('rendered_local_outbox_provider_private_handoff_read_only_status_surface');
  await expect(handoffPanel).toContainText('local_outbox_provider_private_handoff_prepared');
  await expect(handoffPanel).toContainText(setup.providerPrivate.provider_private_handoff_receipt_id);
  await expect(handoffPanel).toContainText(setup.providerPrivate.provider_private_marker);
  await expect(handoffPanel).toContainText(setup.providerPrivate.outbox_artifact_ref);
  await expect(handoffPanel).toContainText('durable_local_outbox_provider_private_handoff_receipt_rows');
  await expect(handoffPanel).toContainText('durable_local_outbox_provider_private_handoff_audit_event_rows');
  await expect(handoffPanel).toContainText('local_outbox_provider_private_handoff_client_request_conflict');
  await expect(handoffPanel).toContainText('local_outbox_provider_private_handoff_failed');
  await expect(handoffPanel).toContainText('real connector invocation');
  await expect(handoffPanel).toContainText('external provider network write');
  await expect(handoffPanel).toContainText('raw token exposed');
  await expect(handoffPanel.locator('button,input,select,textarea')).toHaveCount(0);
  await expect(handoffPanel).not.toContainText('fake-provider-private-token');
  await expect(handoffPanel).not.toContainText('provider_private_signed_url_token');
  await expect(handoffPanel).not.toContainText('C:\\');
  await expect(handoffPanel).not.toContainText('destination_path');
});

test('Layer 3 renders external local export lifecycle as read-only status history', async ({ page, request }) => {
  const setup = await prepareExternalLocalExportViaApi(request);
  const summary = await expectJson(await request.get(`/api/v1/layer3/session/${setup.sessionId}`));
  const exportStatus = summary.external_local_export;

  expect(exportStatus.state).toBe('external_local_export_written');
  expect(exportStatus.external_local_export_receipt_id).toBe(
    setup.externalLocalExport.external_local_export_receipt_id,
  );
  expect(exportStatus.external_local_export_history_count).toBe(1);
  expect(exportStatus.latest_external_local_export_receipt.external_local_export_receipt_id).toBe(
    setup.externalLocalExport.external_local_export_receipt_id,
  );
  expect(exportStatus.audit_event_history_count).toBe(1);
  expect(exportStatus.lifecycle_status_surface.history_listing_authority).toBe(
    'durable_external_local_export_receipt_rows',
  );
  expect(exportStatus.lifecycle_status_surface.audit_trail_authority).toBe(
    'durable_external_local_export_audit_event_rows',
  );
  expect(exportStatus.idempotency_policy.same_key_same_payload_replay).toBe('already_recorded');
  expect(exportStatus.idempotency_policy.same_key_different_payload_conflict).toBe(
    'external_local_export_client_request_conflict',
  );
  expect(exportStatus.idempotency_policy.same_basis_different_client_request_id).toBe('return_existing_status');
  expect(exportStatus.idempotency_policy.duplicate_target_conflicting_output).toBe(
    'external_local_export_existing_output_conflict',
  );
  expect(exportStatus.failure_state_projection.map((entry) => entry.case)).toEqual(
    expect.arrayContaining(['stale_authority', 'same_key_different_payload_conflict', 'target_write_conflict']),
  );
  expect(exportStatus.real_connector_invocation_enabled).toBe(false);
  expect(exportStatus.connector_run_created).toBe(false);
  expect(exportStatus.connector_run_target_created).toBe(false);
  expect(exportStatus.credentials_enabled).toBe(false);
  expect(exportStatus.network_egress_enabled).toBe(false);
  expect(exportStatus.provider_public_delivery_enabled).toBe(false);
  expect(exportStatus.raw_public_url_exposed).toBe(false);
  expect(exportStatus.raw_token_exposed).toBe(false);
  expect(exportStatus.package_mutation_enabled).toBe(false);
  expect(exportStatus.source_expansion_enabled).toBe(false);
  expect(exportStatus.rag_vector_enabled).toBe(false);
  expect(JSON.stringify(exportStatus)).not.toContain('LAYER3_EXTERNAL_LOCAL_EXPORT_DIR');
  expect(exportStatus).not.toHaveProperty('destination_path');
  expect(exportStatus).not.toHaveProperty('caller_supplied_destination_path');

  const bootstrapResponsePromise = page.waitForResponse((response) => response.url().includes('/api/v1/layer3/bootstrap'));
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await expectJson(await bootstrapResponsePromise);
  await attachSessionToWorkbench(page, setup.sessionId);

  const renderedSummaryPromise = page.waitForResponse((response) => response.url().includes(`/api/v1/layer3/session/${setup.sessionId}`));
  await page.locator('#result-review-refresh').click();
  const renderedSummary = await expectJson(await renderedSummaryPromise);
  expect(renderedSummary.external_local_export.external_local_export_receipt_id).toBe(
    setup.externalLocalExport.external_local_export_receipt_id,
  );

  const exportPanel = page.locator('#external-local-export-panel');
  await expect(exportPanel).toContainText('rendered_external_local_export_read_only_status_surface');
  await expect(exportPanel).toContainText('external_local_export_written');
  await expect(exportPanel).toContainText(setup.externalLocalExport.external_local_export_receipt_id);
  await expect(exportPanel).toContainText(setup.externalLocalExport.external_artifact_ref);
  await expect(exportPanel).toContainText(setup.externalLocalExport.external_manifest_ref);
  await expect(exportPanel).toContainText('durable_external_local_export_receipt_rows');
  await expect(exportPanel).toContainText('durable_external_local_export_audit_event_rows');
  await expect(exportPanel).toContainText('external_local_export_client_request_conflict');
  await expect(exportPanel).toContainText('external_local_export_existing_output_conflict');
  await expect(exportPanel).toContainText('operator path authority');
  await expect(exportPanel).toContainText('real connector invocation');
  await expect(exportPanel).toContainText('network egress');
  await expect(exportPanel).toContainText('provider public delivery/use');
  await expect(exportPanel).toContainText('raw public URL');
  await expect(exportPanel).toContainText('package mutation');
  await expect(exportPanel).toContainText('source expansion');
  await expect(exportPanel).toContainText('RAG/vector');
  await expect(exportPanel.locator('button,input,select,textarea')).toHaveCount(0);
  await expect(exportPanel).not.toContainText('C:\\');
  await expect(exportPanel).not.toContainText('LAYER3_EXTERNAL_LOCAL_EXPORT_DIR');
  await expect(exportPanel).not.toContainText('destination_path');
  await expect(exportPanel).not.toContainText('raw_public_url_exposed: true');
  await expect(exportPanel).not.toContainText('connector_run_created: true');
});

test('Layer 3 renders local receipt to server-owned outbox write status as read-only redacted state', async ({ page }) => {
  await page.goto('/review/layer3', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    const sessionId = 'session-local-outbox-ui';
    const passRunId = 'pass-local-outbox-ui';
    const reconciliationId = 'reconciliation-local-outbox-ui';
    const connectorRecordRef = 'connector-dispatch-local-outbox-ui';
    const localReceiptId = 'local-receipt-local-outbox-ui';
    const targetReceiptId = 'target-receipt-local-outbox-ui';
    const writeReceiptId = 'write-receipt-local-outbox-ui';
    const externalRecordRef = 'external-export-local-outbox-ui';
    const authorityHash = 'authority-hash-local-outbox-ui';
    const lifecycleBase = {
      idempotency_policy: {
        client_request_id_unique: true,
        authority_basis_hash_unique: true,
        same_key_same_payload_replay: 'already_recorded',
        same_key_different_payload_conflict: 'server_owned_local_outbox_write_client_request_conflict',
        same_basis_different_client_request_id: 'server_owned_local_outbox_write_already_recorded',
      },
      retry_policy: {
        retry_fields_admitted: false,
        rerun_fields_admitted: false,
        cancel_fields_admitted: false,
        replay_semantics: 'status_only_for_same_client_request_and_same_authority_basis',
      },
      failure_state_projection: [
        {
          case: 'stale_authority',
          operator_status: 'conflict',
          projected_error_code: 'server_owned_local_outbox_write_stale_authority',
        },
        {
          case: 'same_key_different_payload_conflict',
          operator_status: 'conflict',
          projected_error_code: 'server_owned_local_outbox_write_client_request_conflict',
        },
      ],
    };
    State.sessionSummary = {
      session_id: sessionId,
      execution_selection: {
        selected: true,
        execution_started: true,
        analysis_plan_id: 'plan-local-outbox-ui',
        pass_run_ids: [passRunId],
        pass_run_statuses: { [passRunId]: 'completed' },
      },
      connector_local_destination_receipt: {
        schema_id: 'layer3.connector_local_destination_receipt_status.v1',
        state: 'connector_local_destination_receipt_recorded',
        connector_local_destination_receipt_state: 'connector_local_destination_receipt_recorded',
        session_id: sessionId,
        pass_run_id: passRunId,
        reconciliation_record_id: reconciliationId,
        connector_dispatch_record_ref: connectorRecordRef,
        external_export_download_record_ref: externalRecordRef,
        connector_local_destination_receipt_id: localReceiptId,
        destination_target: 'layer3_internal_fake_local_destination_receipt',
        dispatch_mode: 'internal_fake_local_destination_receipt_only',
        accepted_artifact_ref: 'artifact://layer3-internal-fake-local-destination-redacted',
        authority_basis_hash: 'local-receipt-authority-hash',
        receipt_history_count: 1,
        lifecycle_status_surface: {
          schema_id: 'layer3.connector_local_destination_receipt_lifecycle.v1',
          surface_mode: 'read_only_connector_local_receipt_lifecycle_status_history',
          history_listing_authority: 'durable_connector_local_destination_receipt_rows',
          audit_trail_authority: 'durable_connector_local_destination_receipt_row',
          history_count: 1,
          receipt_history: [
            {
              connector_local_destination_receipt_id: localReceiptId,
              connector_local_destination_receipt_state: 'connector_local_destination_receipt_recorded',
              authority_basis_hash: 'local-receipt-authority-hash',
            },
          ],
          ...lifecycleBase,
        },
        external_connector_invocation_enabled: false,
        destination_write_enabled: false,
        connector_run_created: false,
      },
      server_owned_local_outbox_target: {
        schema_id: 'layer3.server_owned_local_outbox_fake_target_status.v1',
        state: 'server_owned_local_outbox_fake_target_recorded',
        server_owned_local_outbox_target_state: 'server_owned_local_outbox_fake_target_recorded',
        session_id: sessionId,
        pass_run_id: passRunId,
        reconciliation_record_id: reconciliationId,
        connector_dispatch_record_ref: connectorRecordRef,
        connector_local_destination_receipt_id: localReceiptId,
        external_export_download_record_ref: externalRecordRef,
        server_owned_local_outbox_target_receipt_id: targetReceiptId,
        target_identity: 'server_owned_local_delivery_outbox_destination',
        dispatch_mode: 'single_named_destination_dispatch_fake_target_first',
        accepted_artifact_ref: 'artifact://server-owned-local-outbox-fake-target-redacted',
        authority_basis_hash: 'fake-target-authority-hash',
        target_receipt_history_count: 1,
        lifecycle_status_surface: {
          schema_id: 'layer3.server_owned_local_outbox_fake_target_lifecycle.v1',
          surface_mode: 'read_only_server_owned_local_outbox_fake_target_status_history',
          history_listing_authority: 'durable_server_owned_local_outbox_fake_target_receipt_rows',
          audit_trail_authority: 'durable_server_owned_local_outbox_fake_target_receipt_row',
          history_count: 1,
          target_receipt_history: [
            {
              server_owned_local_outbox_target_receipt_id: targetReceiptId,
              server_owned_local_outbox_target_state: 'server_owned_local_outbox_fake_target_recorded',
              authority_basis_hash: 'fake-target-authority-hash',
            },
          ],
          ...lifecycleBase,
        },
        real_connector_invocation_enabled: false,
        destination_write_enabled: false,
        connector_run_created: false,
        connector_run_target_created: false,
        credentials_enabled: false,
      },
      server_owned_local_outbox_write: {
        schema_id: 'layer3.server_owned_local_outbox_write_status.v1',
        state: 'server_owned_local_outbox_write_recorded',
        server_owned_local_outbox_write_state: 'server_owned_local_outbox_write_recorded',
        session_id: sessionId,
        pass_run_id: passRunId,
        reconciliation_record_id: reconciliationId,
        connector_dispatch_record_ref: connectorRecordRef,
        connector_local_destination_receipt_id: localReceiptId,
        external_export_download_record_ref: externalRecordRef,
        server_owned_local_outbox_target_receipt_id: targetReceiptId,
        server_owned_local_outbox_write_receipt_id: writeReceiptId,
        target_identity: 'server_owned_local_delivery_outbox_destination',
        dispatch_mode: 'server_owned_local_outbox_write_via_storage_dir',
        operator_decision: 'write_server_owned_local_outbox',
        outbox_artifact_ref: 'storage://server-owned-local-outbox/write-receipt-local-outbox-ui/artifact.json',
        outbox_manifest_ref: 'storage://server-owned-local-outbox/write-receipt-local-outbox-ui/receipt.json',
        outbox_artifact_hash: 'artifact-hash-local-outbox-ui',
        outbox_artifact_size_bytes: 1234,
        accepted_artifact_ref: 'artifact://server-owned-local-outbox-source-redacted',
        authority_basis_hash: authorityHash,
        write_receipt_history_count: 1,
        lifecycle_status_surface: {
          schema_id: 'layer3.server_owned_local_outbox_write_lifecycle.v1',
          surface_mode: 'read_only_server_owned_local_outbox_write_status_history',
          history_listing_authority: 'durable_server_owned_local_outbox_write_receipt_rows',
          audit_trail_authority: 'durable_local_outbox_write_receipt_row_and_manifest_projection',
          history_count: 1,
          write_receipt_history: [
            {
              server_owned_local_outbox_write_receipt_id: writeReceiptId,
              server_owned_local_outbox_write_state: 'server_owned_local_outbox_write_recorded',
              authority_basis_hash: authorityHash,
            },
          ],
          ...lifecycleBase,
        },
        server_owned_local_outbox_write_enabled: true,
        server_owned_local_outbox_write_performed: true,
        real_connector_invocation_enabled: false,
        external_destination_write_enabled: false,
        operator_destination_path_enabled: false,
        connector_run_created: false,
        connector_run_target_created: false,
        credentials_enabled: false,
        network_write_enabled: false,
        provider_public_url_enabled: false,
        package_mutation_enabled: false,
        source_expansion_enabled: false,
        rag_vector_enabled: false,
        frontend_durable_authority_enabled: false,
        downstream_unavailable: [
          'real_connector_invocation',
          'external_destination_write',
          'connector_run_creation',
          'credentials',
          'provider_public_delivery_use',
          'package_mutation_reconstruction',
          'source_expansion',
          'rag_vector',
          'auth_security_implementation',
          'full_mockup_activation',
          'frontend_durable_authority',
          'generic_downstream_dispatch',
        ],
      },
    };
    renderAll();
  });

  await expect(page.locator('#connector-local-destination-receipt-panel')).toContainText('connector_local_destination_receipt_recorded');
  await expect(page.locator('#server-owned-local-outbox-target-panel')).toContainText('server_owned_local_outbox_fake_target_recorded');
  const writePanel = page.locator('#server-owned-local-outbox-write-panel');
  await expect(writePanel).toContainText('rendered_server_owned_local_outbox_write_read_only_status_surface');
  await expect(writePanel).toContainText('server_owned_local_outbox_write_recorded');
  await expect(writePanel).toContainText('storage://server-owned-local-outbox/write-receipt-local-outbox-ui/artifact.json');
  await expect(writePanel).toContainText('durable_server_owned_local_outbox_write_receipt_rows');
  await expect(writePanel).toContainText('server_owned_local_outbox_write_stale_authority');
  await expect(writePanel).toContainText('real connector invocation');
  await expect(writePanel).toContainText('external destination write');
  await expect(writePanel.locator('button,input,select,textarea')).toHaveCount(0);
  await expect(writePanel).not.toContainText('C:\\');
  await expect(writePanel).not.toContainText('source_artifact_ref');
  await expect(writePanel).not.toContainText('destination_path');
});
