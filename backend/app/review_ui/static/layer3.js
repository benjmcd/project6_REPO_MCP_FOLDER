const API_ROOT = '/api/v1/layer3';
const THEME_STORAGE_KEY = 'nrc_aps_review_theme';
const LAYER3_THEME_STORAGE_KEY = 'layer3_workbench_theme';
const LAYER3_MOCKUP_WORKBENCH_THEME = 'layer3_mockup_workbench_theme';
const LAYER3_MOCKUP_THEME_FIRST_SLICE = 'mockup_theme_shell_and_fixture_projection';
const LAYER3_MOCKUP_THEME_FIXTURE = Object.freeze({
    scenario: 'semiconductor_infrastructure_auto_supply_chain',
    frames: Object.freeze([
        'userflow/layer3_user-flow-overview1.png',
        'userflow/layer3_user-flow-overview2.png',
        'clear-screenshots/userflow_slide1.png',
        'clear-screenshots/userflow_slide1_general-example.png',
        'clear-screenshots/userflow_slide1_specific_usecase-example_zoomed-in.png',
        'example-use-case-location-in-pdf.png',
        'focus_on_these/sublayer3A_and_sublayer3B.png',
        'focus_on_these/sublayer3C.png',
    ]),
});
const LAYER3_SESSION_RECOVERY_STORAGE_KEY = 'layer3_workbench_session_recovery_v1';
const LAYER3_GATE_B_DRAFT_STORAGE_KEY = 'layer3_workbench_gate_b_draft_v1';
const LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY = 'layer3_provider_private_receipt_v1';
const LAYER3_SESSION_RECOVERY_SCHEMA_ID = 'layer3.browser_session_recovery.v1';
const LAYER3_GATE_B_DRAFT_SCHEMA_ID = 'layer3.gate_b_draft_snapshot.v1';
const LAYER3_PROVIDER_PRIVATE_RECEIPT_SCHEMA_ID = 'layer3.provider_private_receipt_recovery.v1';
const PROVIDER_PRIVATE_SIGNED_URL_REPLACEABLE_STATES = new Set([
    'provider_private_signed_url_expired',
    'provider_private_signed_url_revoked',
]);
const PROVIDER_PUBLIC_URL_REPLACEABLE_STATES = new Set([
    'provider_public_url_expired',
    'provider_public_url_revoked',
]);
const GATE_B_DRAFT_TTL_MS = 12 * 60 * 60 * 1000;
const QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE = '140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE';
const QUAL_APS_PASS_SCOPE = 'single_aps_doc_qualitative_pass';
const QUAL_APS_SOURCE_GATE = '119_L3_QUAL_APS_EXEC_ENTRY_FREEZE';
const QUAL_APS_SOURCE_SHAPE = 'aps_content_document';
const SOURCE_INTAKE_PASS_SCOPE = 'qualitative_single_item_operator_uploaded_source';
const SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = 'layer3.source_intake_external_export_download_prepare.v1';
const SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = 'layer3.source_intake_external_export_download_delivery.v1';
const RAW_MIXED_MATERIALIZE_REQUEST_SCHEMA_ID = 'layer3.raw_mixed_corpus_materialize_request.v1';
const RAW_MIXED_MATERIALIZE_MODE = 'raw_mixed_existing_source_materialization_entry';
const RAW_MIXED_MATERIALIZE_ALLOWED_SOURCE_CLASSES = new Set(['dataset_version', 'aps_content_document']);
const PACKAGE_LIFECYCLE_DASHBOARD_MODE = 'rendered_package_lifecycle_read_only_dashboard';
const PACKAGE_LIFECYCLE_USE_CASE = 'operator_inspects_package_lifecycle_without_mutation';
const PACKAGE_LIFECYCLE_RESPONSE_AUTHORITY = 'existing_server_response_authority';
const DOWNSTREAM_ACCESS_LIFECYCLE_DASHBOARD_MODE = 'rendered_downstream_access_lifecycle_read_only_dashboard';
const DOWNSTREAM_ACCESS_LIFECYCLE_USE_CASE = 'operator_inspects_downstream_access_lifecycle_without_dispatch_or_raw_url_use';
const DOWNSTREAM_ACCESS_LIFECYCLE_RESPONSE_AUTHORITY = 'existing_server_response_authority';
const LAYER3_E2E_GOVERNANCE_LIFECYCLE_DASHBOARD_MODE = 'rendered_layer3_end_to_end_governance_lifecycle_read_only_dashboard';
const LAYER3_E2E_GOVERNANCE_LIFECYCLE_USE_CASE = 'operator_inspects_layer3_end_to_end_governance_lifecycle_without_mutation_or_dispatch';
const LAYER3_E2E_GOVERNANCE_LIFECYCLE_RESPONSE_AUTHORITY = 'existing_server_response_authority';
const AUTHORITY_MATRIX_REVIEW_RENDERED_MODE = 'rendered_authority_matrix_read_only_review_surface';
const AUTHORITY_MATRIX_REVIEW_USE_CASE = 'operator_reviews_exposed_layer3_authority_matrix_in_rendered_review_surface_without_mutation_or_dispatch';
const AUTHORITY_MATRIX_REVIEW_RESPONSE_AUTHORITY = 'State.bootstrap.authority_matrix_contract';

const State = {
    bootstrap: null,
    datasetVersionCandidates: null,
    datasetVersionCandidateError: null,
    apsContentDocumentCandidates: null,
    apsContentDocumentCandidateError: null,
    rawMixedMaterialization: null,
    rawMixedMaterializationError: null,
    rawMixedMaterializationPending: false,
    preflight: null,
    sourcePreview: null,
    materialPreview: null,
    gateB: null,
    gateC: null,
    planPreview: null,
    planApproval: null,
    planRevision: null,
    planRevisionPending: false,
    sessionSummary: null,
    executionSelection: null,
    executionSelectionError: null,
    executionSelectionPending: false,
    executionStart: null,
    executionStartError: null,
    executionStartPending: false,
    resultStatus: null,
    resultStatusError: null,
    resultReview: null,
    resultReviewError: null,
    resultReviewPending: false,
    packageReviewPreview: null,
    packageReviewPreviewError: null,
    packageReviewPreviewPending: false,
    packageConstruction: null,
    packageConstructionError: null,
    packageConstructionPending: false,
    packageReviewSubmit: null,
    packageReviewSubmitError: null,
    packageReviewSubmitPending: false,
    handoffExportPrepare: null,
    handoffExportPrepareError: null,
    handoffExportPreparePending: false,
    apsHandoffDispatch: null,
    apsHandoffDispatchError: null,
    apsHandoffDispatchPending: false,
    externalExportDownloadPrepare: null,
    externalExportDownloadPrepareError: null,
    externalExportDownloadPreparePending: false,
    externalExportDownloadDelivery: null,
    externalExportDownloadDeliveryError: null,
    externalExportDownloadDeliveryPending: false,
    externalExportDownloadSignedReference: null,
    externalExportDownloadSignedReferenceError: null,
    externalExportDownloadSignedReferencePending: false,
    externalExportDownloadSignedReferenceUse: null,
    externalExportDownloadSignedReferenceUsePending: false,
    providerPrivateSignedUrlPrepare: null,
    providerPrivateSignedUrlStatus: null,
    providerPrivateSignedUrlRevoke: null,
    providerPrivateSignedUrlReceiptRecovery: null,
    providerPrivateSignedUrlPrepareClientRequestId: null,
    providerPrivateSignedUrlError: null,
    providerPrivateSignedUrlPending: false,
    providerPublicUrlPrepare: null,
    providerPublicUrlStatus: null,
    providerPublicUrlRevoke: null,
    providerPublicUrlPrepareClientRequestId: null,
    providerPublicUrlError: null,
    providerPublicUrlPending: false,
    gateBDecisions: {},
    gateBClientRequestId: null,
    materialFilter: '',
    events: [],
    themePreference: document.documentElement.dataset.themePreference || 'system',
    activeOperationId: 'intent-band',
    operationDockManual: false,
};

const elements = {
    themeSelector: document.getElementById('theme-selector'),
    authorityRail: document.getElementById('authority-rail'),
    authorityMatrixReviewPanel: document.getElementById('authority-matrix-review-panel'),
    layer3E2EGovernanceLifecycleDashboardPanel: document.getElementById('layer3-e2e-governance-lifecycle-dashboard-panel'),
    sublayerMapPanel: document.getElementById('sublayer-map-panel'),
    intentForm: document.getElementById('intent-form'),
    intentInput: document.getElementById('layer3-intent'),
    sourceFieldset: document.getElementById('source-fieldset'),
    rawMixedCorpusBatchId: document.getElementById('raw-mixed-corpus-batch-id'),
    rawMixedManifestRef: document.getElementById('raw-mixed-manifest-ref'),
    rawMixedManifestHash: document.getElementById('raw-mixed-manifest-hash'),
    rawMixedOperatorConfirmation: document.getElementById('raw-mixed-operator-confirmation'),
    rawMixedMaterialize: document.getElementById('raw-mixed-materialize'),
    rawMixedMaterializationState: document.getElementById('raw-mixed-materialization-state'),
    rawMixedMaterializationStatus: document.getElementById('raw-mixed-materialization-status'),
    datasetVersionCandidates: document.getElementById('dataset-version-candidates'),
    datasetVersionIds: document.getElementById('dataset-version-ids'),
    apsContentDocumentCandidates: document.getElementById('aps-content-document-candidates'),
    apsContentDocumentIds: document.getElementById('aps-content-document-ids'),
    runPreflight: document.getElementById('run-preflight'),
    materialLedgerBody: document.getElementById('material-ledger-body'),
    materialFilter: document.getElementById('material-filter'),
    gateBSubmit: document.getElementById('gate-b-submit'),
    gateCPreview: document.getElementById('gate-c-preview'),
    gateCCommit: document.getElementById('gate-c-commit'),
    gateCPanel: document.getElementById('gate-c-panel'),
    planStep: document.getElementById('plan-step-chip'),
    executionStep: document.getElementById('execution-step-chip'),
    resultsStep: document.getElementById('results-step-chip'),
    packageStep: document.getElementById('package-step-chip'),
    handoffStep: document.getElementById('handoff-step-chip'),
    planPreview: document.getElementById('plan-preview'),
    planReject: document.getElementById('plan-reject'),
    planRequestRevision: document.getElementById('plan-request-revision'),
    planApprove: document.getElementById('plan-approve'),
    planPanel: document.getElementById('plan-panel'),
    executionSelect: document.getElementById('execution-select'),
    executionStart: document.getElementById('execution-start'),
    executionSelectionStartPanel: document.getElementById('execution-selection-start-panel'),
    resultReviewRefresh: document.getElementById('result-review-refresh'),
    resultStatusInspect: document.getElementById('result-status-inspect'),
    resultReviewForm: document.getElementById('result-review-form'),
    resultReviewPanel: document.getElementById('result-review-panel'),
    resultReviewDecision: document.getElementById('result-review-decision'),
    resultReviewNotes: document.getElementById('result-review-notes'),
    resultReviewSubmit: document.getElementById('result-review-submit'),
    packageReviewPreviewInspect: document.getElementById('package-review-preview-inspect'),
    packageConstructionCommit: document.getElementById('package-construction-commit'),
    packageReviewSubmitForm: document.getElementById('package-review-submit-form'),
    packageReviewSubmitDecision: document.getElementById('package-review-submit-decision'),
    packageReviewSubmitNotes: document.getElementById('package-review-submit-notes'),
    packageReviewSubmit: document.getElementById('package-review-submit'),
    packageReviewPreviewPanel: document.getElementById('package-review-preview-panel'),
    packageLifecycleDashboardPanel: document.getElementById('package-lifecycle-dashboard-panel'),
    handoffExportPrepareForm: document.getElementById('handoff-export-prepare-form'),
    handoffExportPreparePanel: document.getElementById('handoff-export-prepare-panel'),
    handoffExportPrepareDecision: document.getElementById('handoff-export-prepare-decision'),
    handoffExportPrepareNotes: document.getElementById('handoff-export-prepare-notes'),
    handoffExportPrepareSubmit: document.getElementById('handoff-export-prepare-submit'),
    apsHandoffDispatchForm: document.getElementById('aps-handoff-dispatch-form'),
    apsHandoffDispatchPanel: document.getElementById('aps-handoff-dispatch-panel'),
    apsHandoffDispatchSubmit: document.getElementById('aps-handoff-dispatch-submit'),
    externalExportDownloadPrepareForm: document.getElementById('external-export-download-prepare-form'),
    downstreamAccessLifecycleDashboardPanel: document.getElementById('downstream-access-lifecycle-dashboard-panel'),
    externalExportDownloadPreparePanel: document.getElementById('external-export-download-prepare-panel'),
    externalExportDownloadPrepareSubmit: document.getElementById('external-export-download-prepare-submit'),
    externalExportDownloadDeliveryForm: document.getElementById('external-export-download-delivery-form'),
    externalExportDownloadDeliveryPanel: document.getElementById('external-export-download-delivery-panel'),
    externalExportDownloadDeliverySubmit: document.getElementById('external-export-download-delivery-submit'),
    externalExportDownloadSignedReferenceForm: document.getElementById('external-export-download-signed-reference-form'),
    externalExportDownloadSignedReferencePanel: document.getElementById('external-export-download-signed-reference-panel'),
    externalExportDownloadSignedReferenceGenerate: document.getElementById('external-export-download-signed-reference-generate'),
    externalExportDownloadSignedReferenceUse: document.getElementById('external-export-download-signed-reference-use'),
    providerPrivateSignedUrlForm: document.getElementById('provider-private-signed-url-form'),
    providerPrivateSignedUrlPanel: document.getElementById('provider-private-signed-url-panel'),
    providerPrivateSignedUrlPrepare: document.getElementById('provider-private-signed-url-prepare'),
    providerPrivateSignedUrlStatus: document.getElementById('provider-private-signed-url-status'),
    providerPrivateSignedUrlRevoke: document.getElementById('provider-private-signed-url-revoke'),
    providerPublicUrlForm: document.getElementById('provider-public-url-form'),
    providerPublicUrlPanel: document.getElementById('provider-public-url-panel'),
    providerPublicUrlPrepare: document.getElementById('provider-public-url-prepare'),
    providerPublicUrlStatus: document.getElementById('provider-public-url-status'),
    providerPublicUrlRevoke: document.getElementById('provider-public-url-revoke'),
    contextList: document.getElementById('context-list'),
    eventList: document.getElementById('event-list'),
    unavailableList: document.getElementById('unavailable-list'),
    stepChips: Array.from(document.querySelectorAll('.step-chip[data-step-target]')),
    operationsDock: document.querySelector('.operations-dock'),
    operationsDockNav: document.getElementById('operations-dock-nav'),
    operationsDockSummary: document.getElementById('operations-dock-summary'),
    mockupThemeShell: document.getElementById('mockup-theme-shell'),
    mockupThemeFrameList: document.getElementById('mockup-frame-list'),
    mockupFixtureScenario: document.getElementById('mockup-fixture-scenario'),
    mockupPdfLocationProjection: document.getElementById('mockup-pdf-location-projection'),
};

const systemThemeQuery = typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-color-scheme: dark)')
    : null;
const TERMINAL_PASS_STATUSES = new Set(['completed', 'completed_with_warnings', 'failed']);
const RESULT_REVIEW_DECISIONS_REQUIRING_NOTES = new Set(['changes_requested', 'rejected', 'blocked']);
const PACKAGE_REVIEW_DECISIONS_REQUIRING_NOTES = new Set(['changes_requested', 'rejected', 'blocked']);
const HANDOFF_EXPORT_PREPARE_DECISIONS_REQUIRING_NOTES = new Set(['hold', 'decline', 'blocked']);
const ASSOCIATED_COHORT_PASS_TYPE = 'associated_cohort';
const ASSOCIATED_COHORT_PASS_SCOPE = 'quantitative_associated_cohort_dataset_version';
const ASSOCIATED_COHORT_METHOD = 'descriptive_summary';
const ASSOCIATED_COHORT_METHOD_SOURCE = 'analysis_set.formation_basis_json.requested_method_name';
const ASSOCIATED_COHORT_SOURCE_GATE = '78_COHORT_FREEZE';
const ASSOCIATED_COHORT_SHAPE = 'aligned_wide_table';
const HANDOFF_EXPORT_PREPARE_RECORDED_STATES = new Set([
    'handoff_export_prepared',
    'handoff_export_held',
    'handoff_export_declined',
    'handoff_export_blocked',
]);
const APS_HANDOFF_DISPATCH_RECORDED_STATES = new Set(['aps_handoff_dispatched']);
const EXTERNAL_EXPORT_DOWNLOAD_RECORDED_STATES = new Set(['external_export_download_prepared']);
const EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RECORDED_STATES = new Set(['external_export_download_delivered']);
const PACKAGE_REVIEW_PACKAGE_KINDS = ['canonical_internal', 'user_facing', 'review_facing'];
const SUBLAYER_MODALITIES = ['quantitative', 'qualitative', 'hybrid', 'unclassified'];
const SUBLAYER_MODALITY_META = {
    quantitative: {
        label: 'Quantitative Data',
        plane: 'Quantitative / Deterministic Environment',
        accent: 'green',
        empty: 'No quantitative objects are live in the current session state.',
    },
    qualitative: {
        label: 'Qualitative Data',
        plane: 'Qualitative Data Analysis Environment',
        accent: 'purple',
        empty: 'No qualitative objects are live in the current session state.',
    },
    hybrid: {
        label: 'Hybrid / Mixed Data',
        plane: 'Hybrid / Mixed Environment',
        accent: 'amber',
        empty: 'No hybrid or mixed objects are live in the current session state.',
    },
    unclassified: {
        label: 'Unclassified / Unsupported',
        plane: 'Unclassified Holding Area',
        accent: 'cyan',
        empty: 'No unclassified objects are currently reported.',
    },
};
const OPERATION_DOCK_STEPS = [
    { id: 'intent-band', key: 'intent', label: 'Intent', shortLabel: 'Intent', canvasLink: '3A intake setup', canvasTarget: '3a', canvasRole: 'Sublayer 3A intake/specification field' },
    { id: 'source-intake-rendered-controls', key: 'source_intake', label: 'Source Intake Controls', shortLabel: 'Source Intake', canvasLink: '3A source intake', canvasTarget: '3a', canvasRole: 'Sublayer 3A source intake upload/inventory/preview controls' },
    { id: 'gate-b-band', key: 'gate_b', label: 'Gate B Material Ledger', shortLabel: 'Gate B', canvasLink: '3A material ledger', canvasTarget: '3a', canvasRole: 'Sublayer 3A session-scoped material ledger' },
    { id: 'gate-c-band', key: 'gate_c', label: 'Gate C Typing Review', shortLabel: 'Gate C', canvasLink: '3B modality grouping', canvasTarget: '3b', canvasRole: 'Sublayer 3B modality object banks' },
    { id: 'plan-band', key: 'plan', label: 'Plan Preview And Approval', shortLabel: 'Plan', canvasLink: '3C process planning', canvasTarget: '3c-process', canvasRole: 'Sublayer 3C process/status planes' },
    { id: 'result-review-band', key: 'results', label: 'Result Review', shortLabel: 'Results', canvasLink: '3C output authority', canvasTarget: '3c-output', canvasRole: 'Sublayer 3C output/result fields' },
    { id: 'package-review-band', key: 'package', label: 'Package Review', shortLabel: 'Package', canvasLink: 'post-3C package controls', canvasTarget: 'post-3c', canvasRole: 'Post-3C package review control plane' },
    { id: 'handoff-export-band', key: 'handoff', label: 'Handoff / Export Preparation', shortLabel: 'Handoff', canvasLink: 'post-3C handoff controls', canvasTarget: 'post-3c', canvasRole: 'Post-3C handoff/export control plane' },
    { id: 'aps-handoff-band', key: 'aps', label: 'APS Handoff Dispatch', shortLabel: 'APS', canvasLink: 'post-3C APS bridge', canvasTarget: 'post-3c', canvasRole: 'Post-3C APS dispatch bridge' },
    { id: 'external-export-download-band', key: 'external', label: 'External Export / Download', shortLabel: 'External', canvasLink: 'post-3C delivery controls', canvasTarget: 'post-3c', canvasRole: 'Post-3C delivery readiness controls' },
];

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function isSharedThemePreference(value) {
    return value === 'system' || value === 'light' || value === 'dark';
}

function isLayer3ThemePreference(value) {
    return value === 'workbench' || value === LAYER3_MOCKUP_WORKBENCH_THEME;
}

function isClaudePrototypePreference(value) {
    return value === 'claude';
}

function isValidThemePreference(value) {
    return isSharedThemePreference(value) || isLayer3ThemePreference(value) || isClaudePrototypePreference(value);
}

function resolveTheme(preference) {
    if (preference === LAYER3_MOCKUP_WORKBENCH_THEME) return 'workbench';
    if (preference === 'light' || preference === 'dark' || preference === 'workbench') return preference;
    return systemThemeQuery?.matches ? 'dark' : 'light';
}

function applyThemePreference(preference, { persist = true } = {}) {
    const normalized = isValidThemePreference(preference) ? preference : 'system';
    if (isClaudePrototypePreference(normalized)) {
        if (persist) {
            window.location.assign('/review/layer3/static/claude.html');
        }
        return;
    }
    document.documentElement.dataset.themePreference = normalized;
    document.documentElement.dataset.theme = resolveTheme(normalized);
    if (normalized === LAYER3_MOCKUP_WORKBENCH_THEME) {
        document.documentElement.dataset.themeVariant = LAYER3_MOCKUP_WORKBENCH_THEME;
    } else {
        delete document.documentElement.dataset.themeVariant;
    }
    State.themePreference = normalized;
    if (elements.themeSelector) {
        elements.themeSelector.value = normalized;
    }
    renderMockupThemeShell();
    if (persist) {
        try {
            if (isSharedThemePreference(normalized)) {
                localStorage.removeItem(LAYER3_THEME_STORAGE_KEY);
                localStorage.setItem(THEME_STORAGE_KEY, normalized);
            } else {
                localStorage.setItem(LAYER3_THEME_STORAGE_KEY, normalized);
                if (localStorage.getItem(THEME_STORAGE_KEY) === normalized) {
                    localStorage.removeItem(THEME_STORAGE_KEY);
                }
            }
        } catch (error) {
            addEvent('Theme preference kept in browser memory only.');
        }
    }
}

function renderMockupThemeShell() {
    if (!elements.mockupThemeShell) return;
    const active = State.themePreference === LAYER3_MOCKUP_WORKBENCH_THEME;
    elements.mockupThemeShell.dataset.active = active ? 'true' : 'false';
    elements.mockupThemeShell.setAttribute('aria-hidden', active ? 'false' : 'true');
    elements.mockupThemeShell.dataset.firstSlice = LAYER3_MOCKUP_THEME_FIRST_SLICE;
    if (elements.mockupFixtureScenario) {
        elements.mockupFixtureScenario.dataset.fixtureScenario = LAYER3_MOCKUP_THEME_FIXTURE.scenario;
    }
    if (elements.mockupThemeFrameList && elements.mockupThemeFrameList.childElementCount === 0) {
        LAYER3_MOCKUP_THEME_FIXTURE.frames.forEach((frame) => {
            const item = document.createElement('li');
            item.textContent = frame;
            elements.mockupThemeFrameList.appendChild(item);
        });
    }
    renderMockupPdfLocationProjection(active);
}

function renderMockupPdfLocationProjection(active = State.themePreference === LAYER3_MOCKUP_WORKBENCH_THEME) {
    const panel = elements.mockupPdfLocationProjection;
    if (!panel) return;
    if (!active) {
        panel.dataset.projectionState = 'inactive';
        panel.innerHTML = '';
        return;
    }

    const projection = State.sessionSummary?.pdf_location_projection || null;
    const locationItems = Array.isArray(projection?.location_items) ? projection.location_items : [];
    const available = projection?.available === true;
    const blockedReason = projection?.blocked_reason || projection?.reason || 'session summary not loaded';
    const status = available
        ? `${locationItems.length} server-authoritative PDF location item${locationItems.length === 1 ? '' : 's'} available.`
        : `Server PDF-location projection unavailable: ${blockedReason}.`;
    const body = locationItems.length
        ? locationItems.map((item) => `
            <article class="mockup-pdf-location-item">
                <strong>${escapeHtml(item.page_label || item.page || 'Located page')}</strong>
                <span>${escapeHtml(item.chunk_id || item.content_id || 'chunk unavailable')}</span>
                <p>${escapeHtml(item.bounded_text_preview || item.preview || 'No bounded preview supplied.')}</p>
            </article>
        `).join('')
        : '<span class="mockup-disabled-control" aria-disabled="true">Read-only server projection pending</span>';

    panel.dataset.projectionState = available ? 'available' : 'unavailable';
    panel.innerHTML = `
        <span class="mockup-frame-label">Server PDF-location projection</span>
        <p class="mockup-pdf-location-status">${escapeHtml(status)}</p>
        <div class="mockup-pdf-location-items" aria-label="Server-authoritative PDF location items">
            ${body}
        </div>
    `;
}

async function parseResponse(res) {
    const text = await res.text();
    let data = null;
    try {
        data = text ? JSON.parse(text) : null;
    } catch (error) {
        data = { message: text };
    }
    if (!res.ok) {
        const err = new Error(data?.message || `HTTP ${res.status}`);
        err.status = res.status;
        err.payload = data;
        throw err;
    }
    return data;
}

async function getJson(path) {
    const res = await fetch(`${API_ROOT}${path}`);
    return parseResponse(res);
}

async function postJson(path, body) {
    const res = await fetch(`${API_ROOT}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return parseResponse(res);
}

function submitAttachmentForm(path, body) {
    return new Promise((resolve, reject) => {
        const frameName = `layer3-download-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const frame = document.createElement('iframe');
        frame.name = frameName;
        frame.hidden = true;

        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `${API_ROOT}${path}`;
        form.enctype = 'application/x-www-form-urlencoded';
        form.target = frameName;
        form.hidden = true;

        Object.entries(body).forEach(([key, value]) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = key;
            input.value = JSON.stringify(value);
            form.appendChild(input);
        });

        let submitted = false;
        let settled = false;
        const cleanup = () => {
            window.setTimeout(() => {
                form.remove();
                frame.remove();
            }, 15000);
        };
        const settle = (handler, value) => {
            if (settled) return;
            settled = true;
            window.clearTimeout(timer);
            cleanup();
            handler(value);
        };
        const submittedResult = {
            state: 'external_export_download_delivery_submitted',
            schemaId: 'layer3.external_export_download_delivery.v1',
            filename: 'browser-managed attachment',
            sourceArtifactHash: body.source_artifact_hash || null,
            externalExportDownloadRecordRef: body.external_export_download_record_ref || null,
        };
        const timer = window.setTimeout(() => {
            settle(resolve, submittedResult);
        }, 5000);

        frame.addEventListener('load', () => {
            if (!submitted || settled) return;
            const text = frame.contentDocument?.body?.textContent?.trim();
            if (!text) {
                settle(resolve, submittedResult);
                return;
            }
            try {
                const payload = JSON.parse(text);
                settle(reject, Object.assign(new Error(payload.message || 'External delivery request failed.'), { payload }));
            } catch (_error) {
                settle(reject, new Error(text));
            }
        });

        document.body.appendChild(frame);
        document.body.appendChild(form);
        submitted = true;
        form.submit();
    });
}

function addEvent(message) {
    State.events.unshift({
        at: new Date().toLocaleTimeString(),
        message,
    });
    State.events = State.events.slice(0, 10);
    renderEvents();
}

function renderEvents() {
    elements.eventList.innerHTML = State.events
        .map((event) => `<li><strong>${escapeHtml(event.at)}</strong> ${escapeHtml(event.message)}</li>`)
        .join('');
}

function renderUnavailable(labels) {
    const values = labels?.length ? labels : ['plan', 'execution', 'results', 'package'];
    elements.unavailableList.innerHTML = values
        .map((label) => `<li>${escapeHtml(label.replace(/_/g, ' '))}</li>`)
        .join('');
}

function currentAuthorityRail() {
    return State.externalExportDownloadPrepare?.authority_rail || State.apsHandoffDispatch?.authority_rail || State.handoffExportPrepare?.authority_rail || State.packageReviewSubmit?.authority_rail || State.packageConstruction?.authority_rail || State.packageReviewPreview?.authority_rail
        || State.sessionSummary?.authority_rail || State.resultReview?.authority_rail || State.resultStatus?.authority_rail
        || State.executionStart?.authority_rail || State.executionSelection?.authority_rail
        || State.planApproval?.authority_rail || State.planRevision?.authority_rail || State.planPreview?.authority_rail || State.gateC?.authority_rail || State.gateB?.authority_rail
        || State.materialPreview?.authority_rail || State.sourcePreview?.authority_rail || State.preflight?.authority_rail
        || State.bootstrap?.authority_rail;
}

function currentDownstreamUnavailable() {
    const external = externalExportDownloadPrepareState();
    if (
        external?.downstream_unavailable
        && (
            State.externalExportDownloadPrepare
            || external.available === true
            || externalExportDownloadStateName(external) === 'external_export_download_ready'
            || recordedExternalExportDownloadPrepare()
        )
    ) {
        return external.downstream_unavailable;
    }
    return State.apsHandoffDispatch?.downstream_unavailable
        || State.sessionSummary?.aps_handoff_dispatch?.downstream_unavailable
        || State.handoffExportPrepare?.downstream_unavailable
        || State.packageReviewSubmit?.downstream_unavailable
        || State.packageConstruction?.downstream_unavailable
        || State.packageReviewPreview?.downstream_unavailable
        || State.resultReview?.downstream_unavailable
        || State.resultStatus?.downstream_unavailable
        || State.executionStart?.downstream_unavailable
        || State.executionSelection?.downstream_unavailable
        || State.sessionSummary?.downstream_unavailable
        || State.sessionSummary?.handoff_export_prepare?.downstream_unavailable
        || State.sessionSummary?.package_review_submit?.downstream_unavailable
        || State.sessionSummary?.package_construction?.downstream_unavailable
        || State.sessionSummary?.package_review_preview?.downstream_unavailable
        || State.sessionSummary?.execution_result_review?.downstream_unavailable
        || State.sessionSummary?.analysis_execution_start?.downstream_unavailable
        || currentAuthorityRail()?.downstream_unavailable
        || State.bootstrap?.unavailable_gate_labels;
}

function renderContext() {
    const context = {
        route: State.bootstrap?.route || '/review/layer3',
        api_root: State.bootstrap?.api_root || API_ROOT,
        preflight_id: State.preflight?.preflight_id || 'none',
        source_set_id: State.sourcePreview?.source_set_id || 'none',
        material_preview_id: State.materialPreview?.material_preview_id || 'none',
        session_id: currentSessionId() || 'none',
        plan_preview_id: State.sessionSummary?.execution_selection?.source_preview_id || State.planPreview?.preview_id || 'none',
        analysis_plan_id: State.sessionSummary?.execution_selection?.analysis_plan_id || State.planApproval?.analysis_plan_id || 'none',
        plan_revision: State.planRevision?.next_state || 'none',
        pass_run_id: selectedResultAuthority()?.passRunId || State.resultStatus?.pass_run_id || 'none',
        result_status: State.resultStatus?.status || State.resultStatusError?.error_code || 'none',
        result_review: recordedResultReview()?.review_state || State.resultReview?.review_state || State.resultReviewError?.error_code || 'none',
        package_preview: State.packageReviewPreview?.next_state || State.packageReviewPreviewError?.error_code || State.sessionSummary?.package_review_preview?.state || 'none',
        package_construction: State.packageConstruction?.next_state || State.packageConstructionError?.error_code || State.sessionSummary?.package_construction?.state || 'none',
        package_review_submit: State.packageReviewSubmit?.next_state || State.packageReviewSubmitError?.error_code || State.sessionSummary?.package_review_submit?.state || 'none',
        handoff_export_prepare: State.handoffExportPrepare?.next_state || State.handoffExportPrepareError?.error_code || State.sessionSummary?.handoff_export_prepare?.state || 'none',
        aps_handoff_dispatch: State.apsHandoffDispatch?.next_state || State.apsHandoffDispatchError?.error_code || State.sessionSummary?.aps_handoff_dispatch?.state || 'none',
        external_export_download: State.externalExportDownloadPrepare?.next_state || State.externalExportDownloadPrepareError?.error_code || State.sessionSummary?.external_export_download?.state || 'none',
        external_export_download_delivery: State.externalExportDownloadDelivery?.state || State.externalExportDownloadDeliveryError?.error_code || 'none',
        signed_reference: State.externalExportDownloadSignedReferenceUse?.state || State.externalExportDownloadSignedReference?.signed_reference_state || State.externalExportDownloadSignedReferenceError?.error_code || 'none',
        provider_private_signed_url: State.providerPrivateSignedUrlRevoke?.provider_signed_url_state || State.providerPrivateSignedUrlStatus?.provider_signed_url_state || State.providerPrivateSignedUrlPrepare?.provider_signed_url_state || State.providerPrivateSignedUrlError?.error_code || 'none',
    };
    elements.contextList.innerHTML = Object.entries(context)
        .map(([key, value]) => `
            <div>
                <dt>${escapeHtml(key.replace(/_/g, ' '))}</dt>
                <dd>${escapeHtml(value)}</dd>
            </div>
        `)
        .join('');
}

function renderAuthority(rail) {
    const current = rail || currentAuthorityRail();
    if (!current) return;

    const items = {
        gate: current.current_gate,
        persistence: current.persistence_mode,
        session: current.session_id,
        sources: (current.source_authority?.source_classes || []).join(', ') || 'none',
        approved: current.approved_material_count,
        denied: current.denied_material_count,
        isolated: current.isolated_material_count,
        flagged: current.flagged_material_count,
        typing: current.typing_status,
    };
    elements.authorityRail.innerHTML = Object.entries(items)
        .map(([label, value]) => `
            <div class="rail-item">
                <span class="rail-label">${escapeHtml(label)}</span>
                <span class="rail-value">${escapeHtml(value)}</span>
            </div>
        `)
        .join('');
}

function selectedSourceClasses() {
    return Array.from(document.querySelectorAll('input[name="source-class"]:checked'))
        .map((input) => input.value);
}

function parseDatasetVersionIds(value) {
    const result = [];
    String(value || '')
        .split(/[\s,;]+/)
        .map((item) => item.trim())
        .filter(Boolean)
        .forEach((item) => {
            if (!result.includes(item)) result.push(item);
        });
    return result;
}

function parseApsContentDocumentIds(value) {
    return parseDatasetVersionIds(value);
}

function checkedDatasetVersionCandidateIds() {
    return Array.from(document.querySelectorAll('input[name="dataset-version-candidate"]:checked'))
        .map((input) => input.value)
        .filter(Boolean);
}

function checkedApsContentDocumentCandidateIds() {
    return Array.from(document.querySelectorAll('input[name="aps-content-document-candidate"]:checked'))
        .map((input) => input.value)
        .filter(Boolean);
}

function selectedDatasetVersionIds() {
    const result = [];
    [...checkedDatasetVersionCandidateIds(), ...parseDatasetVersionIds(elements.datasetVersionIds?.value)]
        .forEach((item) => {
            if (!result.includes(item)) result.push(item);
        });
    return result;
}

function selectedApsContentDocumentIds() {
    const result = [];
    [...checkedApsContentDocumentCandidateIds(), ...parseApsContentDocumentIds(elements.apsContentDocumentIds?.value)]
        .forEach((item) => {
            if (!result.includes(item)) result.push(item);
        });
    return result;
}

function selectedRawMixedSourceClasses() {
    return selectedSourceClasses()
        .filter((sourceClass) => RAW_MIXED_MATERIALIZE_ALLOWED_SOURCE_CLASSES.has(sourceClass));
}

function rawMixedMaterializationFormState() {
    return {
        corpusBatchId: elements.rawMixedCorpusBatchId?.value?.trim() || '',
        manifestRef: elements.rawMixedManifestRef?.value?.trim() || '',
        manifestHash: elements.rawMixedManifestHash?.value?.trim() || '',
        operatorConfirmed: Boolean(elements.rawMixedOperatorConfirmation?.checked),
        requestedSourceClasses: selectedRawMixedSourceClasses(),
    };
}

function canMaterializeRawMixed() {
    const form = rawMixedMaterializationFormState();
    return Boolean(
        form.corpusBatchId
        && form.manifestRef
        && form.manifestHash
        && form.operatorConfirmed
        && form.requestedSourceClasses.length === RAW_MIXED_MATERIALIZE_ALLOWED_SOURCE_CLASSES.size
        && !State.rawMixedMaterializationPending
    );
}

function rawMixedMaterializationPayload() {
    const form = rawMixedMaterializationFormState();
    return {
        schema_id: RAW_MIXED_MATERIALIZE_REQUEST_SCHEMA_ID,
        schema_version: 1,
        client_request_id: requestId(),
        materialization_mode: RAW_MIXED_MATERIALIZE_MODE,
        corpus_batch_id: form.corpusBatchId,
        artifact_manifest_ref: form.manifestRef,
        artifact_manifest_hash: form.manifestHash,
        requested_source_classes: form.requestedSourceClasses,
        operator_confirmation: true,
    };
}

function candidateIdsForMaterialization(kind) {
    if (kind === 'dataset_version') {
        return new Set((State.datasetVersionCandidates?.dataset_version_candidates || [])
            .map((candidate) => String(candidate.dataset_version_id || ''))
            .filter(Boolean));
    }
    return new Set((State.apsContentDocumentCandidates?.aps_content_document_candidates || [])
        .map((candidate) => String(candidate.content_id || ''))
        .filter(Boolean));
}

function materializedSourceIdsVisible(materialization) {
    const datasetIds = materialization?.dataset_version_ids || [];
    const contentIds = materialization?.aps_content_document_ids || [];
    const datasetCandidates = candidateIdsForMaterialization('dataset_version');
    const contentCandidates = candidateIdsForMaterialization('aps_content_document');
    return datasetIds.every((id) => datasetCandidates.has(String(id)))
        && contentIds.every((id) => contentCandidates.has(String(id)));
}

function applyMaterializedSourceIds(materialization) {
    const datasetIds = materialization?.dataset_version_ids || [];
    const contentIds = materialization?.aps_content_document_ids || [];
    clearMaterializedSourceSelection();
    if (elements.datasetVersionIds) {
        elements.datasetVersionIds.value = datasetIds.join('\n');
    }
    if (elements.apsContentDocumentIds) {
        elements.apsContentDocumentIds.value = contentIds.join('\n');
    }
}

function clearMaterializedSourceSelection() {
    document.querySelectorAll('input[name="dataset-version-candidate"]:checked')
        .forEach((input) => { input.checked = false; });
    document.querySelectorAll('input[name="aps-content-document-candidate"]:checked')
        .forEach((input) => { input.checked = false; });
    if (elements.datasetVersionIds) {
        elements.datasetVersionIds.value = '';
    }
    if (elements.apsContentDocumentIds) {
        elements.apsContentDocumentIds.value = '';
    }
}

function clearRawMixedMaterializationState({ clearAppliedSources = false } = {}) {
    const hadMaterialization = Boolean(State.rawMixedMaterialization);
    State.rawMixedMaterialization = null;
    State.rawMixedMaterializationError = null;
    if (clearAppliedSources && hadMaterialization) {
        clearMaterializedSourceSelection();
        clearLayer3FlowStateForSourceChange();
    }
}

function handleRawMixedMaterializationInputChange() {
    clearRawMixedMaterializationState({ clearAppliedSources: true });
    renderAll();
}

function preventRawMixedManifestEnterSubmit(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
    }
}

function clearLayer3FlowStateForSourceChange() {
    State.preflight = null;
    State.sourcePreview = null;
    State.materialPreview = null;
    State.gateB = null;
    State.gateC = null;
    State.planPreview = null;
    State.planApproval = null;
    State.planRevision = null;
    clearGateBDraftSnapshot();
    clearResultReviewState();
    clearSessionRecoveryAnchor();
}

function selectedSourceClassLabels() {
    const labels = Array.from(document.querySelectorAll('input[name="source-class"]'))
        .filter((input) => input.checked)
        .map((input) => input.closest('label')?.textContent || input.value)
        .map((label) => label.replace(/\s+/g, ' ').trim())
        .filter(Boolean);
    const datasetVersionIds = selectedDatasetVersionIds();
    if (datasetVersionIds.length) {
        labels.push(`${datasetVersionIds.length} APS-derived DatasetVersion ID${datasetVersionIds.length === 1 ? '' : 's'}`);
    }
    const apsContentDocumentIds = selectedApsContentDocumentIds();
    if (apsContentDocumentIds.length) {
        labels.push(`${apsContentDocumentIds.length} APS content document ID${apsContentDocumentIds.length === 1 ? '' : 's'}`);
    }
    return labels;
}

function currentIntentText() {
    const intent = elements.intentInput?.value?.trim();
    return intent || 'No operator intent has been entered yet.';
}

function requestId() {
    if (window.crypto?.randomUUID) {
        return window.crypto.randomUUID();
    }
    return `browser-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function currentSessionId() {
    return State.sessionSummary?.session_id
        || State.gateB?.session_id
        || State.planApproval?.session_id
        || State.planPreview?.session_id
        || State.gateC?.session_id
        || null;
}

function storageGet(storage, key) {
    try {
        const raw = storage?.getItem(key);
        return raw ? JSON.parse(raw) : null;
    } catch (_error) {
        return null;
    }
}

function storageSet(storage, key, value) {
    try {
        storage?.setItem(key, JSON.stringify(value));
        return true;
    } catch (_error) {
        return false;
    }
}

function storageRemove(storage, key) {
    try {
        storage?.removeItem(key);
    } catch (_error) {
        // Browser storage can be unavailable in private or locked-down contexts.
    }
}

function stateActionContractSchemaId(source = null) {
    return source?.state_action_contract?.schema_id || State.bootstrap?.state_action_contract?.schema_id || null;
}

function sortedStringList(values) {
    return Array.isArray(values) ? values.map(String).sort() : [];
}

function stableStringify(value) {
    if (Array.isArray(value)) {
        return `[${value.map((item) => stableStringify(item)).join(',')}]`;
    }
    if (value && typeof value === 'object') {
        return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
    }
    return JSON.stringify(value ?? null);
}

function capabilitySignatureItems(values) {
    return (Array.isArray(values) ? values : [])
        .map((item) => ({
            admitted: item?.admitted ?? null,
            blocked_downstream: sortedStringList(item?.blocked_downstream),
            capability: item?.capability || null,
            owner_service: item?.owner_service || null,
            reason: item?.reason || null,
            source_gate: item?.source_gate || null,
        }))
        .sort((left, right) => String(left.capability).localeCompare(String(right.capability)));
}

function stateActionMatrixSignatureItems(values) {
    return (Array.isArray(values) ? values : [])
        .map((item) => ({
            allowed_next_actions: sortedStringList(item?.allowed_next_actions),
            authority_source: item?.authority_source || null,
            forbidden_downstream_actions: sortedStringList(item?.forbidden_downstream_actions),
            state: item?.state || null,
        }))
        .sort((left, right) => String(left.state).localeCompare(String(right.state)));
}

function decisionSetSignatureItems(value) {
    const decisions = value && typeof value === 'object' ? value : {};
    return Object.fromEntries(
        Object.keys(decisions).sort().map((key) => [key, sortedStringList(decisions[key])]),
    );
}

function stateActionContractSignature(source = null) {
    const contract = source?.state_action_contract || State.bootstrap?.state_action_contract || null;
    if (!contract?.schema_id) return null;
    return stableStringify({
        action_ids: sortedStringList(contract.action_ids),
        admitted_capabilities: capabilitySignatureItems(contract.admitted_capabilities),
        decision_sets: decisionSetSignatureItems(contract.decision_sets),
        deferred_capabilities: capabilitySignatureItems(contract.deferred_capabilities),
        schema_id: contract.schema_id,
        schema_version: contract.schema_version ?? null,
        state_action_matrix: stateActionMatrixSignatureItems(contract.state_action_matrix),
        state_count: contract.state_count ?? null,
        state_model_schema_id: contract.state_model_schema_id || null,
        states: sortedStringList(contract.states),
    });
}

function authorityMatrixContract() {
    const contract = State.bootstrap?.authority_matrix_contract;
    if (!contract || typeof contract !== 'object') return null;
    if (contract.schema_id !== 'layer3.authority_matrix_contract.v1') return null;
    if (!Array.isArray(contract.authority_matrix)) return null;
    return contract;
}

function authorityMatrixReviewState(contract) {
    if (!State.bootstrap) return { label: 'authority_matrix_bootstrap_pending', pill: 'preview' };
    if (!contract) return { label: 'authority_matrix_bootstrap_contract_unavailable', pill: 'blocked' };
    if (contract.fail_closed_result === 'blocked_no_runtime_authority') {
        return { label: 'authority_matrix_fail_closed_read_only', pill: 'ok' };
    }
    return { label: 'authority_matrix_read_only_contract_loaded', pill: 'preview' };
}

function authorityMatrixRowCards(rows) {
    return rows.length
        ? rows.map((row) => `
            <li>
                <code>${escapeHtml(row.row || 'unknown_authority_row')}</code>
                ${row.admission_result ? `<span>${escapeHtml(row.admission_result)}</span>` : ''}
                ${row.next_allowed_action ? `<span>${escapeHtml(row.next_allowed_action)}</span>` : ''}
                ${Array.isArray(row.blocked_scope) && row.blocked_scope.length ? `<span>${escapeHtml(row.blocked_scope.join(', '))}</span>` : ''}
            </li>
        `).join('')
        : '<li>No authority matrix rows are exposed by bootstrap.</li>';
}

function sameStringList(left, right) {
    const leftValues = [...(left || [])].map(String).sort();
    const rightValues = [...(right || [])].map(String).sort();
    return leftValues.length === rightValues.length && leftValues.every((value, index) => value === rightValues[index]);
}

function materialPreviewCandidateIds(preview = State.materialPreview) {
    return (preview?.material_candidates || [])
        .map((candidate) => candidate.candidate_id)
        .filter(Boolean)
        .sort();
}

function isTypingCommitted() {
    return Boolean(
        State.gateC?.authority_rail?.typing_status === 'committed'
        || State.sessionSummary?.gate_c_summary?.typing_committed === true
    );
}

function persistSessionRecoveryAnchor(source) {
    const sessionId = currentSessionId();
    if (!sessionId) return;
    const anchor = {
        schema_id: LAYER3_SESSION_RECOVERY_SCHEMA_ID,
        schema_version: 1,
        session_id: sessionId,
        selection_manifest_id: State.sessionSummary?.selection_manifest_id || State.gateB?.selection_manifest_id || null,
        current_gate: State.sessionSummary?.current_gate || currentAuthorityRail()?.current_gate || null,
        state_action_contract_schema_id: stateActionContractSchemaId(State.sessionSummary),
        state_action_contract_signature: stateActionContractSignature(State.sessionSummary),
        source,
        updated_at: new Date().toISOString(),
    };
    storageSet(localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY, anchor);
}

function clearSessionRecoveryAnchor() {
    storageRemove(localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY);
}

function loadSessionRecoveryAnchor() {
    const anchor = storageGet(localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY);
    if (!anchor || anchor.schema_id !== LAYER3_SESSION_RECOVERY_SCHEMA_ID || !anchor.session_id) {
        storageRemove(localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY);
        return null;
    }
    const currentContract = stateActionContractSignature();
    if (
        currentContract
        && anchor.state_action_contract_signature !== currentContract
    ) {
        storageRemove(localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY);
        addEvent('Stored session recovery anchor skipped after contract change.');
        return null;
    }
    return anchor;
}

async function recoverSessionFromStorage() {
    const anchor = loadSessionRecoveryAnchor();
    if (!anchor) return false;
    try {
        const summary = await getJson(`/session/${encodeURIComponent(anchor.session_id)}`);
        const currentContract = stateActionContractSignature();
        const summaryContract = stateActionContractSignature(summary);
        if (currentContract && summaryContract && currentContract !== summaryContract) {
            clearSessionRecoveryAnchor();
            addEvent('Stored session recovery anchor no longer matches the server contract.');
            return false;
        }
        State.sessionSummary = summary;
        State.resultStatusError = null;
        State.resultReviewError = null;
        State.packageReviewPreviewError = null;
        State.packageConstructionError = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        State.externalExportDownloadSignedReferenceError = null;
        clearGateBDraftSnapshot();
        persistSessionRecoveryAnchor('session_recovery');
        addEvent(`Session ${summary.session_id} restored from server state.`);
        return true;
    } catch (error) {
        clearSessionRecoveryAnchor();
        addEvent(`Stored session recovery anchor cleared: ${error.message}`);
        return false;
    }
}

function gateBDraftExpiresAt() {
    return new Date(Date.now() + GATE_B_DRAFT_TTL_MS).toISOString();
}

function gateBDraftExpired(draft) {
    const expiresAt = Date.parse(draft?.expires_at || '');
    return Number.isFinite(expiresAt) && expiresAt <= Date.now();
}

function currentGateBDraftIdentity() {
    return {
        preflight_id: State.preflight?.preflight_id || null,
        source_set_id: State.sourcePreview?.source_set_id || null,
        material_preview_id: State.materialPreview?.material_preview_id || null,
        material_preview_hash: State.materialPreview?.material_preview_hash || null,
        candidate_ids: materialPreviewCandidateIds(),
    };
}

function gateBDraftMatchesCurrentPreview(draft) {
    const current = currentGateBDraftIdentity();
    return Boolean(
        draft?.material_preview_id
        && current.material_preview_id
        && draft.material_preview_id === current.material_preview_id
        && draft.material_preview_hash === current.material_preview_hash
        && sameStringList(draft.candidate_ids, current.candidate_ids)
    );
}

function buildGateBDraftSnapshot() {
    if (!(State.materialPreview?.material_candidates || []).length) return null;
    const clientRequestId = State.gateBClientRequestId || requestId();
    State.gateBClientRequestId = clientRequestId;
    return {
        schema_id: LAYER3_GATE_B_DRAFT_SCHEMA_ID,
        schema_version: 1,
        draft_authority: 'browser_restore_only_server_revalidated_on_commit',
        client_request_id: clientRequestId,
        state_action_contract_schema_id: stateActionContractSchemaId(),
        state_action_contract_signature: stateActionContractSignature(),
        expires_at: gateBDraftExpiresAt(),
        ...currentGateBDraftIdentity(),
        preflight: State.preflight,
        source_preview: State.sourcePreview,
        material_preview: State.materialPreview,
        gate_b_decisions: State.gateBDecisions,
    };
}

function persistGateBDraftSnapshot() {
    const snapshot = buildGateBDraftSnapshot();
    if (!snapshot) return;
    storageSet(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY, snapshot);
}

function clearGateBDraftSnapshot() {
    State.gateBClientRequestId = null;
    storageRemove(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
}

function restoreGateBDraftSnapshot() {
    if (currentSessionId()) return false;
    const draft = storageGet(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
    if (!draft || draft.schema_id !== LAYER3_GATE_B_DRAFT_SCHEMA_ID || gateBDraftExpired(draft)) {
        storageRemove(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
        return false;
    }
    const currentContract = stateActionContractSignature();
    if (
        currentContract
        && draft.state_action_contract_signature !== currentContract
    ) {
        storageRemove(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
        addEvent('Gate B draft skipped after contract change.');
        return false;
    }
    if (!draft.material_preview?.material_preview_id || !draft.material_preview?.material_preview_hash) {
        storageRemove(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
        return false;
    }
    if (State.materialPreview?.material_preview_id && !gateBDraftMatchesCurrentPreview(draft)) {
        storageRemove(sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY);
        addEvent('Gate B draft skipped after material preview mismatch.');
        return false;
    }
    State.preflight = draft.preflight || null;
    State.sourcePreview = draft.source_preview || null;
    State.materialPreview = draft.material_preview;
    State.gateBDecisions = draft.gate_b_decisions || {};
    State.gateBClientRequestId = draft.client_request_id || requestId();
    addEvent('Gate B draft restored for server revalidation.');
    return true;
}

function gateBRequestId() {
    if (!State.gateBClientRequestId) {
        State.gateBClientRequestId = requestId();
        persistGateBDraftSnapshot();
    }
    return State.gateBClientRequestId;
}

function providerPrivateReceiptSnapshot(provider) {
    if (!provider?.provider_signed_url_receipt_id) return null;
    return {
        schema_id: LAYER3_PROVIDER_PRIVATE_RECEIPT_SCHEMA_ID,
        schema_version: 1,
        recovery_authority: 'browser_receipt_handle_only_server_revalidated_on_status_or_revoke',
        provider_signed_url_receipt_id: provider.provider_signed_url_receipt_id,
        provider_signed_url_state: provider.provider_signed_url_state || null,
        source_artifact_hash: provider.source_artifact_hash || null,
        source_artifact_size_bytes: provider.source_artifact_size_bytes ?? null,
        updated_at: new Date().toISOString(),
    };
}

function persistProviderPrivateReceiptSnapshot(provider) {
    const snapshot = providerPrivateReceiptSnapshot(provider);
    if (!snapshot) return;
    State.providerPrivateSignedUrlReceiptRecovery = snapshot;
    storageSet(sessionStorage, LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY, snapshot);
}

function restoreProviderPrivateReceiptSnapshot() {
    const snapshot = storageGet(sessionStorage, LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY);
    if (!snapshot || snapshot.schema_id !== LAYER3_PROVIDER_PRIVATE_RECEIPT_SCHEMA_ID || !snapshot.provider_signed_url_receipt_id) {
        storageRemove(sessionStorage, LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY);
        return false;
    }
    State.providerPrivateSignedUrlReceiptRecovery = snapshot;
    addEvent('Provider-private signed URL receipt handle restored for server revalidation.');
    return true;
}

function providerPrivateSignedUrlPrepareRequestId() {
    if (!State.providerPrivateSignedUrlPrepareClientRequestId) {
        State.providerPrivateSignedUrlPrepareClientRequestId = requestId();
    }
    return State.providerPrivateSignedUrlPrepareClientRequestId;
}

function clearExternalExportDownloadPrepareState() {
    State.externalExportDownloadPrepare = null;
    State.externalExportDownloadPrepareError = null;
    State.externalExportDownloadPreparePending = false;
    clearExternalExportDownloadDeliveryState();
}

function clearExternalExportDownloadDeliveryState() {
    State.externalExportDownloadDelivery = null;
    State.externalExportDownloadDeliveryError = null;
    State.externalExportDownloadDeliveryPending = false;
    clearExternalExportDownloadSignedReferenceState();
}

function clearExternalExportDownloadSignedReferenceState() {
    State.externalExportDownloadSignedReference = null;
    State.externalExportDownloadSignedReferenceError = null;
    State.externalExportDownloadSignedReferencePending = false;
    State.externalExportDownloadSignedReferenceUse = null;
    State.externalExportDownloadSignedReferenceUsePending = false;
    clearProviderPrivateSignedUrlState();
}

function clearProviderPrivateSignedUrlState() {
    State.providerPrivateSignedUrlPrepare = null;
    State.providerPrivateSignedUrlStatus = null;
    State.providerPrivateSignedUrlRevoke = null;
    State.providerPrivateSignedUrlReceiptRecovery = null;
    State.providerPrivateSignedUrlPrepareClientRequestId = null;
    State.providerPrivateSignedUrlError = null;
    State.providerPrivateSignedUrlPending = false;
    clearProviderPublicUrlState();
    storageRemove(sessionStorage, LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY);
}

function clearProviderPublicUrlState() {
    State.providerPublicUrlPrepare = null;
    State.providerPublicUrlStatus = null;
    State.providerPublicUrlRevoke = null;
    State.providerPublicUrlPrepareClientRequestId = null;
    State.providerPublicUrlError = null;
    State.providerPublicUrlPending = false;
}

function clearResultReviewState({ keepSummary = false } = {}) {
    if (!keepSummary) {
        State.sessionSummary = null;
    }
    State.executionSelection = null;
    State.executionSelectionError = null;
    State.executionSelectionPending = false;
    State.executionStart = null;
    State.executionStartError = null;
    State.executionStartPending = false;
    State.resultStatus = null;
    State.resultStatusError = null;
    State.resultReview = null;
    State.resultReviewError = null;
    State.resultReviewPending = false;
    State.packageReviewPreview = null;
    State.packageReviewPreviewError = null;
    State.packageReviewPreviewPending = false;
    State.packageConstruction = null;
    State.packageConstructionError = null;
    State.packageConstructionPending = false;
    State.packageReviewSubmit = null;
    State.packageReviewSubmitError = null;
    State.packageReviewSubmitPending = false;
    State.handoffExportPrepare = null;
    State.handoffExportPrepareError = null;
    State.handoffExportPreparePending = false;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    State.apsHandoffDispatchPending = false;
    clearExternalExportDownloadPrepareState();
}

function selectedResultAuthority() {
    const summary = State.sessionSummary || {};
    const selection = State.executionSelection || summary.execution_selection || {};
    const startState = State.executionStart || summary.analysis_execution_start || {};
    const statusBody = State.resultStatus || {};
    const reviewBody = State.resultReview || {};
    const passRunIds = Array.isArray(selection.pass_run_ids) ? selection.pass_run_ids : [];
    const firstPassRunId = passRunIds[0] || startState.pass_run_id || statusBody.pass_run_id || reviewBody.pass_run_id || null;
    const passRunStatuses = selection.pass_run_statuses || {};
    const passStatus = statusBody.pass_run_status || startState.pass_run_status || passRunStatuses[firstPassRunId] || null;
    const analysisRunIds = Array.isArray(selection.analysis_run_ids) ? selection.analysis_run_ids : [];
    const analysisRunId = statusBody.analysis_run_id || startState.analysis_run_id || analysisRunIds[0] || reviewBody.analysis_run_id || null;
    const previewIdentity = statusBody.preview_identity || startState.preview_identity || selection.preview_identity || reviewBody.preview_identity || {};
    const previewId = selection.source_preview_id || startState.source_preview_id || previewIdentity.preview_id || State.planPreview?.preview_id || null;
    const previewHash = selection.source_preview_hash || startState.source_preview_hash || previewIdentity.preview_hash || State.planPreview?.preview_hash || null;
    const analysisPlanId = selection.analysis_plan_id || startState.analysis_plan_id || statusBody.analysis_plan_id || reviewBody.analysis_plan_id || State.planApproval?.analysis_plan_id || null;
    return {
        sessionId: summary.session_id || currentSessionId(),
        analysisPlanId,
        passRunId: firstPassRunId,
        previewId,
        previewHash,
        analysisRunId,
        passStatus,
        selected: Boolean((selection.selected === true || State.executionSelection?.schema_id) && firstPassRunId),
        terminal: TERMINAL_PASS_STATUSES.has(passStatus),
        executionStarted: Boolean(selection.execution_started || startState.execution_started || startState.pass_run_id || statusBody.execution_started),
    };
}

function executionSelectionState() {
    return State.executionSelection || State.sessionSummary?.execution_selection || {};
}

function executionStartState() {
    return State.executionStart || State.sessionSummary?.analysis_execution_start || {};
}

function executionPlanAuthority() {
    const selection = executionSelectionState();
    const previewIdentity = selection.preview_identity || State.executionStart?.preview_identity || {};
    return {
        analysisPlanId: State.planApproval?.analysis_plan_id
            || selection.analysis_plan_id
            || State.sessionSummary?.plan_approval?.analysis_plan_id
            || null,
        previewId: State.planPreview?.preview_id
            || selection.source_preview_id
            || previewIdentity.preview_id
            || null,
        previewHash: State.planPreview?.preview_hash
            || selection.source_preview_hash
            || previewIdentity.preview_hash
            || null,
    };
}

function hasResultAuthorityIdentity(authority = selectedResultAuthority()) {
    return Boolean(
        authority.sessionId
        && authority.analysisPlanId
        && authority.passRunId
        && authority.previewId
        && authority.previewHash
    );
}

function recordedResultReview() {
    if (State.resultReview?.review_record_ref || State.resultReview?.review_state) {
        return State.resultReview;
    }
    const sessionReview = State.sessionSummary?.execution_result_review;
    if (sessionReview?.review_record_ref || sessionReview?.state) {
        return sessionReview;
    }
    return null;
}

function recordedApprovedResultReview() {
    const review = recordedResultReview();
    return review && review.review_state === 'execution_result_review_approved' && review.operator_decision === 'approved'
        ? review
        : null;
}

function arrayFromServer(value) {
    return Array.isArray(value) ? value.filter((item) => item !== null && item !== undefined && String(item).trim()) : [];
}

function nullIfBlank(value) {
    const normalized = String(value ?? '').trim();
    return normalized || null;
}

function selectedPassRunSummary(authority = selectedResultAuthority()) {
    const passRuns = Array.isArray(State.sessionSummary?.sublayer_visualization?.pass_runs)
        ? State.sessionSummary.sublayer_visualization.pass_runs
        : [];
    return passRuns.find((passRun) => passRun?.pass_run_id === authority.passRunId) || {};
}

function associatedCohortProjection(authority = selectedResultAuthority()) {
    const statusBody = State.resultStatus || {};
    const metadata = statusBody.output_metadata_summary || {};
    const reviewState = recordedResultReview() || {};
    const passRun = selectedPassRunSummary(authority);
    const traceSummary = State.resultReview?.trace_summary || reviewState.trace_summary || {};
    const sourceDatasetVersionIds = arrayFromServer(
        metadata.source_dataset_version_ids
        || traceSummary.source_dataset_version_ids
        || passRun.source_dataset_version_ids
        || passRun.source_dataset_version_ids_json
    );
    const passType = nullIfBlank(statusBody.pass_type || passRun.pass_type || metadata.pass_type || traceSummary.pass_type);
    const passScope = nullIfBlank(statusBody.pass_scope || passRun.pass_scope || metadata.pass_scope || traceSummary.pass_scope);
    const selectedMethod = nullIfBlank(
        statusBody.selected_method_name || passRun.selected_method_name || metadata.selected_method_name || traceSummary.selected_method_name
    );
    const requestedMethod = nullIfBlank(metadata.requested_method_name || traceSummary.requested_method_name || passRun.requested_method_name);
    const requestedMethodSource = nullIfBlank(
        metadata.requested_method_source || traceSummary.requested_method_source || passRun.requested_method_source
    );
    const sourceGate = nullIfBlank(metadata.source_gate || traceSummary.source_gate || passRun.source_gate);
    const cohortShape = nullIfBlank(metadata.cohort_shape || traceSummary.cohort_shape || passRun.cohort_shape);
    const outputPayloadRef = nullIfBlank(
        statusBody.output_payload_ref || metadata.output_payload_ref || traceSummary.output_payload_ref
    );
    const unresolvedTraceCount = Number(
        State.resultReview?.unresolved_trace_count
        ?? reviewState.unresolved_trace_count
        ?? statusBody.unresolved_trace_count
        ?? 0
    );
    const isAssociated = passType === ASSOCIATED_COHORT_PASS_TYPE
        || (
            passScope === ASSOCIATED_COHORT_PASS_SCOPE
            && sourceGate === ASSOCIATED_COHORT_SOURCE_GATE
            && cohortShape === ASSOCIATED_COHORT_SHAPE
        );
    const ready = Boolean(
        isAssociated
        && hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && statusBody.result_status_available === true
        && metadata.readable === true
        && passType === ASSOCIATED_COHORT_PASS_TYPE
        && passScope === ASSOCIATED_COHORT_PASS_SCOPE
        && selectedMethod === ASSOCIATED_COHORT_METHOD
        && requestedMethod === ASSOCIATED_COHORT_METHOD
        && requestedMethodSource === ASSOCIATED_COHORT_METHOD_SOURCE
        && sourceGate === ASSOCIATED_COHORT_SOURCE_GATE
        && cohortShape === ASSOCIATED_COHORT_SHAPE
        && sourceDatasetVersionIds.length > 0
        && outputPayloadRef
        && unresolvedTraceCount === 0
    );
    return {
        isAssociated,
        ready,
        passType,
        passScope,
        selectedMethod,
        requestedMethod,
        requestedMethodSource,
        sourceGate,
        cohortShape,
        sourceDatasetVersionIds,
        outputPayloadRef,
        unresolvedTraceCount,
    };
}

function associatedCohortReviewedOutputItems(authority = selectedResultAuthority()) {
    const projection = associatedCohortProjection(authority);
    if (!projection.ready) return [];
    const trace = {
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        output_payload_ref: projection.outputPayloadRef,
    };
    if (authority.analysisRunId) {
        trace.analysis_run_id = authority.analysisRunId;
    }
    return [
        {
            item_ref: projection.outputPayloadRef,
            item_type: 'finding',
            trace,
        },
    ];
}

function associatedCohortReviewContext() {
    return associatedCohortProjection().isAssociated;
}

function canRefreshSessionSummary() {
    return Boolean(
        currentSessionId()
        && !State.executionSelectionPending
        && !State.executionStartPending
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canInspectResultStatus() {
    const authority = selectedResultAuthority();
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && !State.executionSelectionPending
        && !State.executionStartPending
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function reviewDecisionNeedsNotes() {
    return RESULT_REVIEW_DECISIONS_REQUIRING_NOTES.has(elements.resultReviewDecision.value);
}

function canSubmitResultReview() {
    const authority = selectedResultAuthority();
    const notes = elements.resultReviewNotes.value.trim();
    const cohort = associatedCohortProjection(authority);
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && State.resultStatus?.result_status_available === true
        && !recordedResultReview()
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && (!reviewDecisionNeedsNotes() || notes)
        && (!cohort.isAssociated || cohort.ready)
    );
}

function canInspectPackageReviewPreview() {
    const authority = selectedResultAuthority();
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && recordedApprovedResultReview()
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function packageConstructionState() {
    return State.packageConstruction || State.sessionSummary?.package_construction || null;
}

function packageReviewSubmitState() {
    if (State.packageReviewSubmit) {
        return State.packageReviewSubmit;
    }
    const summarySubmit = State.sessionSummary?.package_review_submit;
    if (summarySubmit?.package_review_state || summarySubmit?.submit_record_ref) {
        return summarySubmit;
    }
    const construction = State.packageConstruction;
    if (construction?.package_review_submit_enabled === true) {
        const outputPackageIds = Array.isArray(construction.output_package_ids)
            ? construction.output_package_ids
            : (Array.isArray(construction.output_packages)
                ? construction.output_packages.map((item) => item.output_package_id).filter(Boolean)
                : []);
        return {
            schema_id: 'layer3.package_review_submit_state.v1',
            available: true,
            state: 'package_review_submit_ready',
            reconciliation_record_id: construction.reconciliation_record_id,
            output_package_ids: outputPackageIds,
            package_kinds: construction.package_kinds,
            payload_refs: construction.payload_refs,
            payload_hashes: construction.payload_hashes,
            construction_basis_hash: construction.construction_basis_hash,
            package_review_preview_hash: construction.package_review_preview_hash,
            result_review_record_ref: construction.result_review_record_ref,
            package_construction_source_gate: construction.package_construction_source_gate,
            pass_type: construction.pass_type,
            pass_scope: construction.pass_scope,
            method: construction.method,
            source_gate: construction.source_gate,
            source_shape: construction.source_shape,
            package_review_submit_enabled: true,
            handoff_enabled: false,
            export_enabled: false,
            downstream_unavailable: construction.downstream_unavailable,
        };
    }
    if (summarySubmit) {
        return summarySubmit;
    }
    return null;
}

function packageReviewPreviewHash() {
    const preview = State.packageReviewPreview || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    return preview.package_review_preview_hash
        || submit.package_review_preview_hash
        || construction.package_review_preview_hash
        || null;
}

function packageConstructionBasisHash() {
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    return submit.construction_basis_hash || construction.construction_basis_hash || null;
}

function isQualitativeApsPackageSubmitState(
    submit = packageReviewSubmitState() || {},
    construction = packageConstructionState() || {},
) {
    return Boolean(
        submit.package_construction_source_gate === QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE
        || construction.package_construction_source_gate === QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE
        || submit.pass_scope === QUAL_APS_PASS_SCOPE
        || construction.pass_scope === QUAL_APS_PASS_SCOPE
        || submit.source_shape === QUAL_APS_SOURCE_SHAPE
        || construction.source_shape === QUAL_APS_SOURCE_SHAPE
    );
}

function packageOutputPackageIds() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    if (Array.isArray(handoff.output_package_ids) && handoff.output_package_ids.length) {
        return handoff.output_package_ids;
    }
    if (Array.isArray(submit.output_package_ids) && submit.output_package_ids.length) {
        return submit.output_package_ids;
    }
    if (Array.isArray(construction.output_package_ids) && construction.output_package_ids.length) {
        return construction.output_package_ids;
    }
    if (Array.isArray(construction.output_packages)) {
        return construction.output_packages.map((item) => item.output_package_id).filter(Boolean);
    }
    return [];
}

function packagePayloadHashes() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    if (Array.isArray(handoff.payload_hashes) && handoff.payload_hashes.length) {
        return handoff.payload_hashes;
    }
    if (Array.isArray(submit.payload_hashes) && submit.payload_hashes.length) {
        return submit.payload_hashes;
    }
    if (Array.isArray(construction.payload_hashes) && construction.payload_hashes.length) {
        return construction.payload_hashes;
    }
    if (Array.isArray(construction.output_packages)) {
        return construction.output_packages.map((item) => item.payload_hash).filter(Boolean);
    }
    return [];
}

function packagePayloadRefs() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    if (Array.isArray(handoff.payload_refs) && handoff.payload_refs.length) {
        return handoff.payload_refs;
    }
    if (Array.isArray(submit.payload_refs) && submit.payload_refs.length) {
        return submit.payload_refs;
    }
    if (Array.isArray(construction.payload_refs) && construction.payload_refs.length) {
        return construction.payload_refs;
    }
    if (Array.isArray(construction.output_packages)) {
        return construction.output_packages.map((item) => item.payload_ref).filter(Boolean);
    }
    return [];
}

function packageKindsFromState() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    if (Array.isArray(handoff.package_kinds) && handoff.package_kinds.length) {
        return handoff.package_kinds;
    }
    if (Array.isArray(submit.package_kinds) && submit.package_kinds.length) {
        return submit.package_kinds;
    }
    if (Array.isArray(construction.package_kinds) && construction.package_kinds.length) {
        return construction.package_kinds;
    }
    const previewKinds = Array.isArray(State.packageReviewPreview?.candidate_package_kinds)
        ? State.packageReviewPreview.candidate_package_kinds.map((item) => item.package_kind).filter(Boolean)
        : [];
    return previewKinds.length ? previewKinds : PACKAGE_REVIEW_PACKAGE_KINDS;
}

function packageLifecycleOutputRows() {
    const construction = packageConstructionState() || {};
    const outputPackages = Array.isArray(construction.output_packages) ? construction.output_packages : [];
    const packageIds = packageOutputPackageIds();
    const payloadRefs = packagePayloadRefs();
    const payloadHashes = packagePayloadHashes();
    const previewKinds = Array.isArray(State.packageReviewPreview?.candidate_package_kinds)
        ? State.packageReviewPreview.candidate_package_kinds.map((item) => item.package_kind).filter(Boolean)
        : [];
    const constructionKinds = Array.isArray(construction.package_kinds) ? construction.package_kinds : [];
    const submit = packageReviewSubmitState() || {};
    const submitKinds = Array.isArray(submit.package_kinds) ? submit.package_kinds : [];
    const packageKinds = outputPackages.length || packageIds.length || payloadRefs.length || payloadHashes.length
        ? packageKindsFromState()
        : (previewKinds.length ? previewKinds : (constructionKinds.length ? constructionKinds : submitKinds));
    const rowCount = Math.max(
        outputPackages.length,
        packageIds.length,
        packageKinds.length,
        payloadRefs.length,
        payloadHashes.length,
    );
    return Array.from({ length: rowCount }, (_value, index) => ({
        package_kind: outputPackages[index]?.package_kind || packageKinds[index],
        output_package_id: outputPackages[index]?.output_package_id || packageIds[index],
        payload_ref: outputPackages[index]?.payload_ref || payloadRefs[index],
        payload_hash: outputPackages[index]?.payload_hash || payloadHashes[index],
    })).filter((row) => row.package_kind || row.output_package_id || row.payload_ref || row.payload_hash);
}

function packageLifecycleDashboardState(preview, construction, submit) {
    if (State.packageReviewSubmitPending) return { label: 'package_lifecycle_submit_recording', pill: 'preview' };
    if (State.packageConstructionPending) return { label: 'package_lifecycle_construction_committing', pill: 'preview' };
    if (State.packageReviewPreviewPending) return { label: 'package_lifecycle_preview_inspecting', pill: 'preview' };
    const submitState = submit.package_review_state || submit.state;
    const submitRecorded = Boolean(
        submit.package_review_state
        || submit.submit_record_ref
    );
    if (submitRecorded) {
        return {
            label: submitState || 'package_review_recorded',
            pill: submitState === 'package_review_approved' ? 'ok' : 'blocked',
        };
    }
    if (State.packageReviewSubmitError || State.packageConstructionError || State.packageReviewPreviewError) {
        return { label: 'package_lifecycle_blocked', pill: 'blocked' };
    }
    if (submit.package_review_submit_enabled === true) {
        return { label: submit.state || 'package_review_submit_ready', pill: 'ok' };
    }
    if (construction.state === 'package_constructed' || construction.next_state === 'package_constructed') {
        return { label: 'package_lifecycle_constructed', pill: 'ok' };
    }
    if (preview.package_review_preview_enabled === true) {
        return { label: preview.next_state || 'package_lifecycle_preview_ready', pill: 'preview' };
    }
    return { label: 'package_lifecycle_waiting_for_server_state', pill: 'blocked' };
}

function renderPackageLifecycleRows(rows) {
    return rows.length
        ? rows.map((row) => `
            <li>
                <code>${escapeHtml(row.package_kind || 'unknown_package_kind')}</code>
                ${row.output_package_id ? `<code>${escapeHtml(row.output_package_id)}</code>` : ''}
                ${row.payload_ref ? `<code>${escapeHtml(row.payload_ref)}</code>` : ''}
                ${row.payload_hash ? `<code>${escapeHtml(row.payload_hash)}</code>` : ''}
            </li>
        `).join('')
        : '<li>No package lifecycle rows are available.</li>';
}

function packageReviewSubmitDecisionNeedsNotes() {
    return PACKAGE_REVIEW_DECISIONS_REQUIRING_NOTES.has(elements.packageReviewSubmitDecision.value);
}

function handoffExportPrepareDecisionNeedsNotes() {
    return HANDOFF_EXPORT_PREPARE_DECISIONS_REQUIRING_NOTES.has(elements.handoffExportPrepareDecision.value);
}

function handoffExportPrepareState() {
    return State.handoffExportPrepare || State.sessionSummary?.handoff_export_prepare || null;
}

function recordedHandoffExportPrepare() {
    const state = handoffExportPrepareState();
    if (!state) return null;
    const recordedState = state.handoff_export_state || state.next_state || state.state;
    return state.prepare_record_ref || HANDOFF_EXPORT_PREPARE_RECORDED_STATES.has(recordedState)
        ? state
        : null;
}

function apsHandoffDispatchState() {
    if (State.apsHandoffDispatch) {
        return State.apsHandoffDispatch;
    }
    const handoff = State.handoffExportPrepare;
    const handoffState = handoff?.handoff_export_state || handoff?.next_state || handoff?.state;
    const qualitativeAps = handoff?.schema_id === 'layer3.qual_aps_handoff_export_prepare.v1'
        || isQualitativeApsPackageSubmitState(packageReviewSubmitState() || {}, packageConstructionState() || {});
    if (
        qualitativeAps
        && handoffState === 'handoff_export_prepared'
        && handoff?.prepare_record_ref
        && handoffExportEnvelopeRef(handoff)
        && handoff?.package_review_submit_record_ref
    ) {
        return {
            schema_id: 'layer3.aps_handoff_dispatch_state.v1',
            available: true,
            state: 'aps_handoff_ready',
            blocked_reason: null,
            reconciliation_record_id: handoff.reconciliation_record_id,
            prepare_record_ref: handoff.prepare_record_ref,
            handoff_export_envelope_ref: handoffExportEnvelopeRef(handoff),
            aps_handoff_target: 'aps_evidence_bundle',
            dispatch_mode: 'server_side_aps_handoff',
            operator_decision: 'dispatch_aps_handoff',
            downstream_unavailable: handoff.downstream_unavailable,
        };
    }
    return State.sessionSummary?.aps_handoff_dispatch || null;
}

function apsHandoffStateName(state = apsHandoffDispatchState()) {
    return state?.aps_handoff_state || state?.next_state || state?.state || null;
}

function recordedApsHandoffDispatch() {
    const state = apsHandoffDispatchState();
    if (!state) return null;
    const recordedState = apsHandoffStateName(state);
    return state.aps_handoff_record_ref || APS_HANDOFF_DISPATCH_RECORDED_STATES.has(recordedState)
        ? state
        : null;
}

function externalExportDownloadPrepareState() {
    return State.externalExportDownloadPrepare || State.sessionSummary?.external_export_download || null;
}

function externalExportDownloadStateName(state = externalExportDownloadPrepareState()) {
    return state?.external_export_download_state || state?.next_state || state?.state || null;
}

function recordedExternalExportDownloadPrepare() {
    const state = externalExportDownloadPrepareState();
    if (!state) return null;
    const recordedState = externalExportDownloadStateName(state);
    return state.external_export_download_record_ref || EXTERNAL_EXPORT_DOWNLOAD_RECORDED_STATES.has(recordedState)
        ? state
        : null;
}

function isAssociatedCohortExternalExportDownloadState(external = externalExportDownloadPrepareState() || {}) {
    return external.pass_type === ASSOCIATED_COHORT_PASS_TYPE
        || (
            external.pass_scope === ASSOCIATED_COHORT_PASS_SCOPE
            && external.method === ASSOCIATED_COHORT_METHOD
            && external.source_gate === ASSOCIATED_COHORT_SOURCE_GATE
            && external.source_shape === ASSOCIATED_COHORT_SHAPE
        );
}

function isQualitativeApsExternalExportDownloadState(external = externalExportDownloadPrepareState() || {}) {
    if (isAssociatedCohortExternalExportDownloadState(external)) return false;
    if (isSourceIntakeExternalExportDownloadState(external)) return false;
    const summary = State.sessionSummary?.external_export_download || {};
    return external.pass_scope === QUAL_APS_PASS_SCOPE
        || summary.pass_scope === QUAL_APS_PASS_SCOPE
        || external.source_gate === QUAL_APS_SOURCE_GATE
        || summary.source_gate === QUAL_APS_SOURCE_GATE
        || external.package_construction_source_gate === QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE
        || summary.package_construction_source_gate === QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE;
}

function associatedCohortDeliveryUiState(external = externalExportDownloadPrepareState() || {}) {
    const summary = State.sessionSummary?.external_export_download || {};
    const deliveryUi = external?.delivery_ui || summary.delivery_ui || null;
    if (deliveryUi) return deliveryUi;
    return null;
}

function qualitativeApsDeliveryUiState(external = externalExportDownloadPrepareState() || {}) {
    if (!isQualitativeApsExternalExportDownloadState(external)) return null;
    const summary = State.sessionSummary?.external_export_download || {};
    const deliveryUi = external?.delivery_ui || summary.delivery_ui || null;
    if (deliveryUi) return deliveryUi;
    return null;
}

function serverExternalExportDownloadDeliveryUiState(external = externalExportDownloadPrepareState() || {}) {
    const summary = State.sessionSummary?.external_export_download || {};
    const deliveryUi = external?.delivery_ui || summary.delivery_ui || null;
    if (deliveryUi) return deliveryUi;
    return null;
}

function isSourceIntakeExternalExportDownloadState(external = externalExportDownloadPrepareState() || {}) {
    const summary = State.sessionSummary?.external_export_download || {};
    return external.schema_id === SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
        || summary.schema_id === SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
        || external.pass_scope === SOURCE_INTAKE_PASS_SCOPE
        || summary.pass_scope === SOURCE_INTAKE_PASS_SCOPE
        || Boolean(external.source_intake_record_id || summary.source_intake_record_id);
}

function sourceIntakeDeliveryUiState(external = externalExportDownloadPrepareState() || {}) {
    if (!isSourceIntakeExternalExportDownloadState(external)) return null;
    const summary = State.sessionSummary?.external_export_download || {};
    const deliveryUi = external?.delivery_ui || summary.delivery_ui || null;
    if (deliveryUi) return deliveryUi;
    const readiness = { ...summary, ...external };
    const readinessState = externalExportDownloadStateName(readiness);
    const available = Boolean(
        readiness.schema_id === SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
        && readinessState === 'external_export_download_prepared'
        && readiness.external_export_download_record_ref
        && readiness.export_download_descriptor_ref
        && readiness.source_intake_record_id
        && readiness.candidate_id
        && readiness.aps_bundle_ref
        && readiness.source_artifact_hash
    );
    return {
        available,
        state: available
            ? 'source_intake_external_export_download_delivery_ui_ready'
            : 'source_intake_external_export_download_delivery_ui_blocked',
        operator_decision: 'deliver_external_export_download',
        delivery_mode: 'same_origin_artifact_stream',
        browser_managed_same_origin_attachment_enabled: available,
        public_url_enabled: false,
        signed_url_enabled: false,
        connector_dispatch_enabled: false,
        destination_selection_enabled: false,
        generic_downstream_dispatch_enabled: false,
        package_mutation_enabled: false,
        schema_runtime_source_widening_enabled: false,
        server_authority: SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
    };
}

function deliveryUiStateAdmitted(deliveryUi, states) {
    return Boolean(
        deliveryUi
        && deliveryUi.available === true
        && states.includes(deliveryUi.state)
        && deliveryUi.operator_decision === 'deliver_external_export_download'
        && deliveryUi.delivery_mode === 'same_origin_artifact_stream'
        && deliveryUi.browser_managed_same_origin_attachment_enabled === true
        && deliveryUi.public_url_enabled === false
        && deliveryUi.signed_url_enabled === false
        && deliveryUi.connector_dispatch_enabled === false
        && deliveryUi.destination_selection_enabled === false
        && deliveryUi.generic_downstream_dispatch_enabled === false
        && deliveryUi.package_mutation_enabled === false
        && deliveryUi.schema_runtime_source_widening_enabled === false
    );
}

function externalExportDownloadDeliveryUiAdmitted(external = externalExportDownloadPrepareState() || {}) {
    const sourceIntakeDeliveryUi = sourceIntakeDeliveryUiState(external);
    if (sourceIntakeDeliveryUi) {
        return deliveryUiStateAdmitted(sourceIntakeDeliveryUi, [
            'source_intake_external_export_download_delivery_ui_ready',
        ]);
    }
    if (isQualitativeApsExternalExportDownloadState(external)) {
        return deliveryUiStateAdmitted(qualitativeApsDeliveryUiState(external), [
            'external_export_download_delivery_ui_ready',
        ]);
    }
    if (isAssociatedCohortExternalExportDownloadState(external)) {
        const deliveryUi = associatedCohortDeliveryUiState(external);
        return deliveryUiStateAdmitted(deliveryUi, [
            'associated_cohort_external_export_download_delivery_ui_ready',
            'external_export_download_delivery_ui_ready',
        ]);
    }
    return deliveryUiStateAdmitted(serverExternalExportDownloadDeliveryUiState(external), [
        'external_export_download_delivery_ui_ready',
    ]);
}

function externalExportDownloadDeliveryStateName(state = State.externalExportDownloadDelivery) {
    return state?.external_export_download_delivery_state || state?.deliveryState || state?.state || null;
}

function recordedExternalExportDownloadDelivery() {
    const state = State.externalExportDownloadDelivery;
    if (!state) return null;
    const recordedState = externalExportDownloadDeliveryStateName(state);
    return EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RECORDED_STATES.has(recordedState)
        ? state
        : null;
}

function canGenerateExternalExportDownloadSignedReference() {
    const external = externalExportDownloadPrepareState() || {};
    return Boolean(
        recordedExternalExportDownloadPrepare()
        && externalExportDownloadDeliveryUiAdmitted(external)
        && !State.externalExportDownloadSignedReference?.signed_reference_token
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.externalExportDownloadSignedReferencePending
        && !State.externalExportDownloadSignedReferenceUsePending
    );
}

function canUseExternalExportDownloadSignedReference() {
    return Boolean(
        State.externalExportDownloadSignedReference?.signed_reference_token
        && State.externalExportDownloadSignedReference?.signed_reference_state === 'external_export_download_signed_reference_ready'
        && !State.externalExportDownloadSignedReferenceUse
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.externalExportDownloadSignedReferencePending
        && !State.externalExportDownloadSignedReferenceUsePending
    );
}

function providerPrivateSignedUrlReceiptId() {
    return State.providerPrivateSignedUrlRevoke?.provider_signed_url_receipt_id
        || State.providerPrivateSignedUrlStatus?.provider_signed_url_receipt_id
        || State.providerPrivateSignedUrlPrepare?.provider_signed_url_receipt_id
        || State.providerPrivateSignedUrlReceiptRecovery?.provider_signed_url_receipt_id
        || null;
}

function providerPrivateSignedUrlLatestState() {
    return State.providerPrivateSignedUrlRevoke?.provider_signed_url_state
        || State.providerPrivateSignedUrlStatus?.provider_signed_url_state
        || State.providerPrivateSignedUrlPrepare?.provider_signed_url_state
        || State.providerPrivateSignedUrlReceiptRecovery?.provider_signed_url_state
        || null;
}

function providerPrivateSignedUrlBlocksPrepare() {
    const receiptId = providerPrivateSignedUrlReceiptId();
    if (!receiptId) return false;
    return !PROVIDER_PRIVATE_SIGNED_URL_REPLACEABLE_STATES.has(providerPrivateSignedUrlLatestState());
}

function canPrepareProviderPrivateSignedUrl() {
    const external = externalExportDownloadPrepareState() || {};
    return Boolean(
        recordedExternalExportDownloadPrepare()
        && externalExportDownloadDeliveryUiAdmitted(external)
        && (!isSourceIntakeExternalExportDownloadState(external) || State.externalExportDownloadSignedReferenceUse)
        && !providerPrivateSignedUrlBlocksPrepare()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.externalExportDownloadSignedReferencePending
        && !State.externalExportDownloadSignedReferenceUsePending
        && !State.providerPrivateSignedUrlPending
    );
}

function canInspectProviderPrivateSignedUrl() {
    return Boolean(
        providerPrivateSignedUrlReceiptId()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.providerPrivateSignedUrlPending
    );
}

function canRevokeProviderPrivateSignedUrl() {
    return Boolean(
        providerPrivateSignedUrlReceiptId()
        && providerPrivateSignedUrlLatestState() !== 'provider_private_signed_url_revoked'
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.providerPrivateSignedUrlPending
    );
}

function providerPublicUrlReceiptId() {
    return State.providerPublicUrlRevoke?.provider_public_url_receipt_id
        || State.providerPublicUrlStatus?.provider_public_url_receipt_id
        || State.providerPublicUrlPrepare?.provider_public_url_receipt_id
        || null;
}

function providerPublicUrlLatestState() {
    return State.providerPublicUrlRevoke?.provider_public_url_state
        || State.providerPublicUrlStatus?.provider_public_url_state
        || State.providerPublicUrlPrepare?.provider_public_url_state
        || null;
}

function providerPublicUrlBlocksPrepare() {
    const receiptId = providerPublicUrlReceiptId();
    if (!receiptId) return false;
    return !PROVIDER_PUBLIC_URL_REPLACEABLE_STATES.has(providerPublicUrlLatestState());
}

function canPrepareProviderPublicUrl() {
    return Boolean(
        providerPrivateSignedUrlReceiptId()
        && providerPrivateSignedUrlLatestState() === 'provider_private_signed_url_prepared'
        && !providerPublicUrlBlocksPrepare()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.providerPrivateSignedUrlPending
        && !State.providerPublicUrlPending
    );
}

function canInspectProviderPublicUrl() {
    return Boolean(
        providerPublicUrlReceiptId()
        && !State.providerPublicUrlPending
    );
}

function canRevokeProviderPublicUrl() {
    return Boolean(
        providerPublicUrlReceiptId()
        && providerPublicUrlLatestState() !== 'provider_public_url_revoked'
        && !State.providerPublicUrlPending
    );
}

function downstreamAccessLifecycleRows() {
    const handoff = handoffExportPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const external = externalExportDownloadPrepareState() || {};
    const delivery = State.externalExportDownloadDelivery || {};
    const signedReference = State.externalExportDownloadSignedReferenceUse || State.externalExportDownloadSignedReference || {};
    const providerPrivate = State.providerPrivateSignedUrlRevoke || State.providerPrivateSignedUrlStatus || State.providerPrivateSignedUrlPrepare || State.providerPrivateSignedUrlReceiptRecovery || {};
    const providerPublic = State.providerPublicUrlRevoke || State.providerPublicUrlStatus || State.providerPublicUrlPrepare || {};
    const rows = [
        {
            stage: 'handoff/export prepare',
            state: handoff.handoff_export_state || handoff.next_state || handoff.state,
            record_ref: handoff.prepare_record_ref || handoffExportEnvelopeRef(handoff),
            authority: handoff.schema_id || 'handoff_export_prepare_response',
            access_mode: handoff.export_mode || handoff.handoff_target,
        },
        {
            stage: 'APS handoff dispatch',
            state: aps.aps_handoff_state || aps.next_state || aps.state,
            record_ref: aps.aps_handoff_record_ref,
            authority: aps.schema_id || 'aps_handoff_dispatch_response',
            access_mode: aps.dispatch_mode || aps.aps_handoff_target,
        },
        {
            stage: 'external export/download readiness',
            state: externalExportDownloadStateName(external),
            record_ref: external.external_export_download_record_ref || external.export_download_descriptor_ref,
            authority: external.schema_id || 'external_export_download_prepare_response',
            access_mode: external.delivery_mode || external.download_mode || external.export_download_target,
        },
        {
            stage: 'same-origin delivery',
            state: externalExportDownloadDeliveryStateName(delivery),
            record_ref: delivery.externalExportDownloadRecordRef || delivery.external_export_download_record_ref,
            authority: delivery.schemaId || delivery.schema_id || 'external_export_download_delivery_response',
            access_mode: externalExportDownloadDeliveryStateName(delivery) || delivery.externalExportDownloadRecordRef || delivery.external_export_download_record_ref
                ? (delivery.deliveryMode || delivery.delivery_mode || 'same_origin_artifact_stream')
                : null,
        },
        {
            stage: 'signed reference',
            state: signedReference.state || signedReference.signed_reference_state,
            record_ref: signedReference.signedReferenceReceiptId || signedReference.signed_reference_receipt_id,
            authority: signedReference.schemaId || signedReference.schema_id || 'external_export_download_signed_reference_response',
            access_mode: signedReference.state || signedReference.signed_reference_state || signedReference.signedReferenceReceiptId || signedReference.signed_reference_receipt_id
                ? (signedReference.replayPolicy || signedReference.signed_reference_replay_policy || 'same_origin_signed_delivery_reference')
                : null,
        },
        {
            stage: 'provider-private receipt',
            state: providerPrivate.provider_signed_url_state,
            record_ref: providerPrivate.provider_signed_url_receipt_id,
            authority: providerPrivate.schema_id || 'provider_private_signed_url_response',
            access_mode: providerPrivate.delivery_mode || providerPrivate.provider_url_replay_policy,
        },
        {
            stage: 'provider-public receipt',
            state: providerPublic.provider_public_url_state,
            record_ref: providerPublic.provider_public_url_receipt_id,
            authority: providerPublic.schema_id || 'provider_public_url_response',
            access_mode: providerPublic.provider_public_url_redacted ? 'redacted_receipt_only' : providerPublic.delivery_mode,
        },
    ];
    return rows.filter((row) => row.state || row.record_ref || row.access_mode);
}

function downstreamAccessLifecycleDashboardState(rows) {
    const handoff = handoffExportPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const external = externalExportDownloadPrepareState() || {};
    const apsState = apsHandoffStateName(aps);
    const externalState = externalExportDownloadStateName(external);
    if (
        State.handoffExportPreparePending
        || State.apsHandoffDispatchPending
        || State.externalExportDownloadPreparePending
        || State.externalExportDownloadDeliveryPending
        || State.externalExportDownloadSignedReferencePending
        || State.externalExportDownloadSignedReferenceUsePending
        || State.providerPrivateSignedUrlPending
        || State.providerPublicUrlPending
    ) {
        return { label: 'downstream_access_lifecycle_refreshing', pill: 'preview' };
    }
    const error = State.handoffExportPrepareError
        || State.apsHandoffDispatchError
        || State.externalExportDownloadPrepareError
        || State.externalExportDownloadDeliveryError
        || State.externalExportDownloadSignedReferenceError
        || State.providerPrivateSignedUrlError
        || State.providerPublicUrlError;
    if (error) {
        return { label: error.error_code || 'downstream_access_lifecycle_blocked', pill: 'blocked' };
    }
    if (providerPublicUrlLatestState()) {
        return { label: providerPublicUrlLatestState(), pill: 'ready' };
    }
    if (providerPrivateSignedUrlLatestState()) {
        return { label: providerPrivateSignedUrlLatestState(), pill: 'ready' };
    }
    if (State.externalExportDownloadSignedReferenceUse?.state || State.externalExportDownloadSignedReference?.signed_reference_state) {
        return { label: State.externalExportDownloadSignedReferenceUse?.state || State.externalExportDownloadSignedReference?.signed_reference_state, pill: 'ready' };
    }
    if (externalExportDownloadDeliveryStateName()) {
        return { label: externalExportDownloadDeliveryStateName(), pill: 'ready' };
    }
    if (
        externalState
        && (
            State.externalExportDownloadPrepare
            || external.available === true
            || externalState === 'external_export_download_ready'
            || recordedExternalExportDownloadPrepare()
        )
    ) {
        return { label: externalState, pill: recordedExternalExportDownloadPrepare() ? 'ready' : 'preview' };
    }
    if (
        apsState
        && (
            State.apsHandoffDispatch
            || aps.available === true
            || apsState === 'aps_handoff_ready'
            || recordedApsHandoffDispatch()
        )
    ) {
        return { label: apsState, pill: recordedApsHandoffDispatch() ? 'ready' : 'preview' };
    }
    if (handoff.handoff_export_state || handoff.next_state || handoff.state) {
        return { label: handoff.handoff_export_state || handoff.next_state || handoff.state, pill: recordedHandoffExportPrepare() ? 'ready' : 'preview' };
    }
    return {
        label: rows.length ? 'downstream_access_lifecycle_partial_server_state' : 'downstream_access_lifecycle_waiting_for_server_state',
        pill: rows.length ? 'preview' : 'blocked',
    };
}

function renderDownstreamAccessLifecycleRows(rows) {
    return rows.length
        ? rows.map((row) => `
            <li>
                <code>${escapeHtml(row.stage)}</code>
                ${row.state ? `<span>${escapeHtml(row.state)}</span>` : ''}
                ${row.record_ref ? `<code>${escapeHtml(row.record_ref)}</code>` : ''}
                ${row.access_mode ? `<span>${escapeHtml(row.access_mode)}</span>` : ''}
            </li>
        `).join('')
        : '<li>No downstream access lifecycle rows are available.</li>';
}

function layer3E2EGovernanceLifecycleRows() {
    const gateB = State.gateB || {};
    const gateC = State.gateC || State.sessionSummary?.gate_c || {};
    const planPreview = State.planPreview || State.sessionSummary?.plan_preview || {};
    const planApproval = State.planApproval || State.sessionSummary?.plan_approval || {};
    const selection = executionSelectionState();
    const start = executionStartState();
    const resultReview = recordedResultReview() || {};
    const packageRows = packageLifecycleOutputRows();
    const preview = State.packageReviewPreview || {};
    const construction = packageConstructionState() || {};
    const submit = packageReviewSubmitState() || {};
    const packageState = packageLifecycleDashboardState(preview, construction, submit);
    const handoff = handoffExportPrepareState() || {};
    const downstreamRows = downstreamAccessLifecycleRows();
    const downstreamState = downstreamAccessLifecycleDashboardState(downstreamRows);
    const latestDownstreamRow = [...downstreamRows].reverse().find((row) => row.state || row.record_ref || row.access_mode) || {};
    const providerPrivate = State.providerPrivateSignedUrlRevoke || State.providerPrivateSignedUrlStatus || State.providerPrivateSignedUrlPrepare || State.providerPrivateSignedUrlReceiptRecovery || {};
    const providerPublic = State.providerPublicUrlRevoke || State.providerPublicUrlStatus || State.providerPublicUrlPrepare || {};
    return [
        {
            key: 'source_intake_gate_b',
            stage: 'source intake / Gate B',
            state: gateB.state || gateB.material_state || gateB.next_state,
            ref: gateB.source_intake_record_id || gateB.material_preview_id || gateB.session_id,
            authority: gateB.schema_id || 'gate_b_response_state',
        },
        {
            key: 'gate_c_typing',
            stage: 'Gate C typing',
            state: gateC.state || gateC.gate_c_state || gateC.next_state,
            ref: gateC.typing_record_ref || gateC.session_id || gateC.analysis_set_id,
            authority: gateC.schema_id || 'gate_c_response_state',
        },
        {
            key: 'plan_preview_approval',
            stage: 'plan preview / approval',
            state: planApproval.plan_approval_state || planApproval.state || planPreview.plan_preview_state || planPreview.state,
            ref: planApproval.analysis_plan_id || planPreview.preview_id,
            authority: planApproval.schema_id || planPreview.schema_id || 'plan_flow_response_state',
        },
        {
            key: 'execution_result_review',
            stage: 'execution / result review',
            state: resultReview.review_state || start.pass_run_status || start.state || selection.state,
            ref: selectedResultAuthority().passRunId || resultReview.review_record_ref || selection.analysis_plan_id,
            authority: resultReview.schema_id || start.schema_id || selection.schema_id || 'execution_response_state',
        },
        {
            key: 'package_lifecycle',
            stage: 'package lifecycle',
            state: packageState.label,
            ref: submit.submit_record_ref || construction.reconciliation_record_id || packageRows[0]?.output_package_id,
            authority: PACKAGE_LIFECYCLE_DASHBOARD_MODE,
        },
        {
            key: 'handoff_export',
            stage: 'handoff/export',
            state: handoff.handoff_export_state || handoff.next_state || handoff.state,
            ref: handoff.prepare_record_ref || handoffExportEnvelopeRef(handoff),
            authority: handoff.schema_id || 'handoff_export_response_state',
        },
        {
            key: 'downstream_access',
            stage: latestDownstreamRow.stage ? `downstream access / ${latestDownstreamRow.stage}` : 'downstream access',
            state: downstreamState.label,
            ref: latestDownstreamRow.record_ref,
            authority: DOWNSTREAM_ACCESS_LIFECYCLE_DASHBOARD_MODE,
            access_mode: latestDownstreamRow.access_mode,
        },
        {
            key: 'provider_connector_boundaries',
            stage: 'provider / connector boundaries',
            state: providerPublic.provider_public_url_state || providerPrivate.provider_signed_url_state,
            ref: providerPublic.provider_public_url_receipt_id || providerPrivate.provider_signed_url_receipt_id,
            authority: 'provider_receipt_and_connector_record_only_state',
        },
    ].filter((row) => row.state || row.ref);
}

function layer3E2EGovernanceLifecycleDashboardState(rows) {
    if (
        State.executionSelectionPending
        || State.executionStartPending
        || State.resultReviewPending
        || State.packageReviewPreviewPending
        || State.packageConstructionPending
        || State.packageReviewSubmitPending
        || State.handoffExportPreparePending
        || State.apsHandoffDispatchPending
        || State.externalExportDownloadPreparePending
        || State.externalExportDownloadDeliveryPending
        || State.externalExportDownloadSignedReferencePending
        || State.externalExportDownloadSignedReferenceUsePending
        || State.providerPrivateSignedUrlPending
        || State.providerPublicUrlPending
    ) {
        return { label: 'layer3_e2e_governance_lifecycle_refreshing', pill: 'preview' };
    }
    const error = State.executionSelectionError
        || State.executionStartError
        || State.resultReviewError
        || State.packageReviewPreviewError
        || State.packageConstructionError
        || State.packageReviewSubmitError
        || State.handoffExportPrepareError
        || State.apsHandoffDispatchError
        || State.externalExportDownloadPrepareError
        || State.externalExportDownloadDeliveryError
        || State.externalExportDownloadSignedReferenceError
        || State.providerPrivateSignedUrlError
        || State.providerPublicUrlError;
    if (error) {
        return { label: error.error_code || 'layer3_e2e_governance_lifecycle_blocked', pill: 'blocked' };
    }
    const furthest = [...rows].reverse().find((row) => row.state || row.ref);
    if (furthest) {
        const stateKey = furthest.key || furthest.stage.replace(/[^a-z0-9]+/gi, '_').toLowerCase();
        return { label: `layer3_e2e_latest_${stateKey}`, pill: 'ready' };
    }
    return { label: 'layer3_e2e_governance_lifecycle_waiting_for_server_state', pill: 'blocked' };
}

function renderLayer3E2EGovernanceLifecycleRows(rows) {
    return rows.length
        ? rows.map((row) => `
            <li>
                <code>${escapeHtml(row.stage)}</code>
                ${row.state ? `<span>${escapeHtml(row.state)}</span>` : ''}
                ${row.ref ? `<code>${escapeHtml(row.ref)}</code>` : ''}
                ${row.authority ? `<span>${escapeHtml(row.authority)}</span>` : ''}
                ${row.access_mode ? `<span>${escapeHtml(row.access_mode)}</span>` : ''}
            </li>
        `).join('')
        : '<li>No Layer 3 governance lifecycle rows are available.</li>';
}

function handoffExportEnvelopeRef(handoff = handoffExportPrepareState() || State.sessionSummary?.handoff_export_prepare || {}) {
    return handoff.handoff_export_envelope_ref || handoff.handoff_export_envelope?.envelope_ref || null;
}

function canCommitPackageConstruction() {
    const authority = selectedResultAuthority();
    const preview = State.packageReviewPreview || {};
    const construction = packageConstructionState() || {};
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && recordedApprovedResultReview()
        && preview.package_review_preview_enabled === true
        && preview.package_commit_enabled === true
        && preview.package_review_preview_hash
        && construction.state !== 'package_constructed'
        && construction.next_state !== 'package_constructed'
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canSubmitPackageReview() {
    const authority = selectedResultAuthority();
    const review = recordedApprovedResultReview();
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    const cohort = associatedCohortProjection(authority);
    const notes = elements.packageReviewSubmitNotes.value.trim();
    const qualitativeAps = isQualitativeApsPackageSubmitState(submit, construction);
    const previewHash = packageReviewPreviewHash();
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && review?.review_record_ref
        && (!cohort.isAssociated || cohort.ready)
        && previewHash
        && submit.package_review_submit_enabled === true
        && submit.reconciliation_record_id
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && (!qualitativeAps || submit.construction_basis_hash || construction.construction_basis_hash)
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && (!packageReviewSubmitDecisionNeedsNotes() || notes)
    );
}

function canSubmitHandoffExportPrepare() {
    const authority = selectedResultAuthority();
    const handoff = State.sessionSummary?.handoff_export_prepare || {};
    const submit = packageReviewSubmitState() || {};
    const packageReviewState = submit.package_review_state || submit.state || handoff.package_review_state;
    const notes = elements.handoffExportPrepareNotes.value.trim();
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && State.sessionSummary?.session_id
        && handoff.available === true
        && handoff.handoff_export_prepare_enabled === true
        && packageReviewState === 'package_review_approved'
        && handoff.result_review_record_ref
        && handoff.package_review_preview_hash
        && handoff.reconciliation_record_id
        && handoff.package_review_submit_record_ref
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && !recordedHandoffExportPrepare()
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && (!handoffExportPrepareDecisionNeedsNotes() || notes)
    );
}

function canSubmitApsHandoffDispatch() {
    const authority = selectedResultAuthority();
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const packageReviewState = submit.package_review_state || submit.state || handoff.package_review_state;
    const prepareState = handoff.handoff_export_state || handoff.next_state || handoff.state;
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && State.sessionSummary?.session_id
        && packageReviewState === 'package_review_approved'
        && prepareState === 'handoff_export_prepared'
        && aps.available === true
        && aps.state === 'aps_handoff_ready'
        && aps.prepare_record_ref
        && aps.handoff_export_envelope_ref
        && handoff.prepare_record_ref
        && handoffExportEnvelopeRef(handoff)
        && handoff.result_review_record_ref
        && handoff.package_review_preview_hash
        && handoff.reconciliation_record_id
        && handoff.package_review_submit_record_ref
        && packageKindsFromState().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && !recordedApsHandoffDispatch()
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canSubmitExternalExportDownloadPrepare() {
    const authority = selectedResultAuthority();
    const external = State.sessionSummary?.external_export_download || {};
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const packageReviewState = external.package_review_state || submit.package_review_state || submit.state || handoff.package_review_state;
    const prepareState = external.handoff_export_state || handoff.handoff_export_state || handoff.next_state || handoff.state;
    const apsState = external.aps_handoff_state || apsHandoffStateName(aps);
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && State.sessionSummary?.session_id
        && packageReviewState === 'package_review_approved'
        && prepareState === 'handoff_export_prepared'
        && apsState === 'aps_handoff_dispatched'
        && external.available === true
        && external.state === 'external_export_download_ready'
        && external.external_export_download_prepare_enabled === true
        && external.result_review_record_ref
        && external.package_review_preview_hash
        && external.reconciliation_record_id
        && external.package_review_submit_record_ref
        && external.prepare_record_ref
        && external.handoff_export_envelope_ref
        && external.aps_handoff_record_ref
        && external.aps_output_package_id
        && external.aps_output_package_kind
        && external.aps_bundle_ref
        && external.aps_bundle_id
        && external.aps_schema_id
        && external.source_artifact_hash
        && external.source_artifact_size_bytes != null
        && packageKindsFromState().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && !recordedExternalExportDownloadPrepare()
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function canSubmitExternalExportDownloadDelivery() {
    const authority = selectedResultAuthority();
    const external = externalExportDownloadPrepareState() || {};
    const handoff = handoffExportPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const submit = packageReviewSubmitState() || {};
    const packageReviewState = external.package_review_state || submit.package_review_state || submit.state || handoff.package_review_state;
    const prepareState = external.handoff_export_state || handoff.handoff_export_state || handoff.next_state || handoff.state;
    const apsState = external.aps_handoff_state || apsHandoffStateName(aps);
    const readinessState = externalExportDownloadStateName(external);
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && State.sessionSummary?.session_id
        && packageReviewState === 'package_review_approved'
        && prepareState === 'handoff_export_prepared'
        && apsState === 'aps_handoff_dispatched'
        && readinessState === 'external_export_download_prepared'
        && externalExportDownloadDeliveryUiAdmitted(external)
        && external.external_export_download_record_ref
        && external.export_download_descriptor_ref
        && external.result_review_record_ref
        && external.package_review_preview_hash
        && external.reconciliation_record_id
        && external.package_review_submit_record_ref
        && external.prepare_record_ref
        && external.handoff_export_envelope_ref
        && external.aps_handoff_record_ref
        && external.aps_output_package_id
        && external.aps_output_package_kind
        && external.aps_bundle_ref
        && external.aps_bundle_id
        && external.aps_schema_id
        && external.source_artifact_hash
        && external.source_artifact_size_bytes != null
        && packageKindsFromState().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadRefs().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
}

function isPackageActive() {
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    return Boolean(
        (recordedApprovedResultReview() && !associatedCohortReviewContext())
        || State.packageReviewPreview?.package_review_preview_enabled === true
        || construction.state === 'package_constructed'
        || construction.next_state === 'package_constructed'
        || submit.package_review_submit_enabled === true
        || submit.submit_record_ref
    );
}

function isHandoffActive() {
    const handoff = handoffExportPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const submit = packageReviewSubmitState() || {};
    return Boolean(
        submit.package_review_state === 'package_review_approved'
        || submit.state === 'package_review_approved'
        || handoff.available === true
        || handoff.state === 'handoff_export_ready'
        || recordedHandoffExportPrepare()
        || aps.available === true
        || recordedApsHandoffDispatch()
        || (externalExportDownloadPrepareState() || {}).available === true
        || recordedExternalExportDownloadPrepare()
    );
}

function decisionState(candidateId) {
    return State.gateBDecisions[candidateId] || { decision: 'approved', operator_reason: '' };
}

function syncDecisionStateFromRow(row) {
    const candidateId = row.dataset.candidateId;
    if (!candidateId) return;
    State.gateBDecisions[candidateId] = {
        decision: row.querySelector('.decision-select')?.value || 'approved',
        operator_reason: row.querySelector('.reason-input')?.value || '',
    };
    persistGateBDraftSnapshot();
}

function termsFromIntent(intent) {
    return Array.from(new Set(
        intent.toLowerCase()
            .split(/[^a-z0-9_]+/)
            .map((term) => term.trim())
            .filter((term) => term.length > 3)
    )).slice(0, 6);
}

function candidateSearchText(candidate) {
    const trace = candidate.source_trace || {};
    const traceRefs = trace.aps_trace_refs || {};
    return [
        candidate.candidate_id,
        candidate.source_label,
        candidate.source_class,
        candidate.owner_service_source_shape,
        candidate.planning_shape_family,
        candidate.source_family,
        candidate.source_family_label,
        candidate.source_admission_state,
        trace.trace_readiness,
        traceRefs.parser_family,
        traceRefs.parser_contract_id,
        traceRefs.typed_content_contract_id,
        traceRefs.target_id,
        traceRefs.accession_number,
        traceRefs.diagnostics_ref,
        traceRefs.content_units_ref,
        traceRefs.normalized_text_ref,
        traceRefs.blob_ref,
        trace.document_identity?.content_id,
        trace.document_identity?.content_contract_id,
        trace.document_identity?.chunking_contract_id,
        candidate.validation_status,
        candidate.duplicate_status,
    ].join(' ').toLowerCase();
}

function humanizeToken(value) {
    const text = String(value ?? '').trim();
    if (!text) return 'none';
    return text.replace(/[_-]+/g, ' ');
}

function shortText(value, maxLength = 36) {
    const text = String(value ?? '').trim();
    if (!text) return 'none';
    if (text.length <= maxLength) return text;
    return `${text.slice(0, Math.max(8, maxLength - 12))}...${text.slice(-8)}`;
}

function normalizeModality(value) {
    const text = String(value ?? '').toLowerCase();
    if (!text) return 'unclassified';
    if (text.includes('hybrid') || text.includes('mixed')) return 'hybrid';
    if (text.includes('qual')) return 'qualitative';
    if (
        text.includes('quant')
        || text.includes('deterministic')
        || text.includes('dataset')
        || text.includes('numeric')
        || text.includes('time_series')
    ) {
        return 'quantitative';
    }
    return 'unclassified';
}

function modalityMeta(modality) {
    return SUBLAYER_MODALITY_META[modality] || SUBLAYER_MODALITY_META.unclassified;
}

function groupedByModality(items) {
    return SUBLAYER_MODALITIES.reduce((groups, modality) => {
        groups[modality] = items.filter((item) => item.modality === modality);
        return groups;
    }, {});
}

function sessionSublayerState() {
    const state = State.sessionSummary?.sublayer_visualization;
    return state && typeof state === 'object' ? state : {};
}

function sourceIdentityLabel(identity = {}) {
    const candidates = [
        identity.candidate_id,
        identity.dataset_version_id,
        identity.content_id,
        identity.run_id,
        identity.target_id,
        identity.source_ref,
    ];
    return candidates.find((candidate) => candidate) || null;
}

function currentMaterialObjects() {
    const candidates = State.materialPreview?.material_candidates || [];
    if (candidates.length) {
        return candidates.map((candidate, index) => {
            const decision = decisionState(candidate.candidate_id).decision;
            return {
                id: candidate.candidate_id || `candidate-${index + 1}`,
                label: candidate.source_label || `Material candidate ${index + 1}`,
                kind: candidate.source_class || 'material candidate',
                primary: candidate.owner_service_source_shape || candidate.planning_shape_family || 'source shape unavailable',
                secondary: candidate.query_basis || candidate.duplicate_status || 'preview candidate',
                badge: decision,
                modality: normalizeModality(candidate.owner_service_source_shape || candidate.planning_shape_family || candidate.source_class),
                live: true,
            };
        });
    }

    const persistedObjects = sessionSublayerState().material_objects || [];
    if (persistedObjects.length) {
        return persistedObjects.map((item, index) => {
            const identity = item.source_identity || {};
            const identityLabel = sourceIdentityLabel(identity);
            const loadedRecords = item.load_summary?.loaded_records;
            return {
                id: item.material_snapshot_id || `material-snapshot-${index + 1}`,
                label: humanizeToken(identityLabel || item.source_shape || `Material snapshot ${index + 1}`),
                kind: item.source_shape || 'material snapshot',
                primary: identityLabel || item.source_plane || 'persisted material snapshot',
                secondary: loadedRecords !== undefined
                    ? `${loadedRecords} loaded record${loadedRecords === 1 ? '' : 's'}`
                    : (item.source_plane || 'session material ledger'),
                badge: item.state || 'loaded',
                modality: normalizeModality(item.source_shape || item.source_plane),
                live: true,
            };
        });
    }

    const gateB = State.gateB || {};
    const gateBIds = [
        ...(gateB.approved_candidate_ids || []).map((id) => ({ id, decision: 'approved' })),
        ...(gateB.denied_candidate_ids || []).map((id) => ({ id, decision: 'denied' })),
        ...(gateB.isolated_candidate_ids || []).map((id) => ({ id, decision: 'isolated' })),
        ...(gateB.flagged_candidate_ids || []).map((id) => ({ id, decision: 'flagged' })),
    ];
    if (gateBIds.length) {
        return gateBIds.map((item, index) => ({
            id: item.id || `gate-b-${index + 1}`,
            label: `Gate B ${humanizeToken(item.decision)} material`,
            kind: 'session-scoped material',
            primary: 'Gate B decision record',
            secondary: currentSessionId() ? `session ${shortText(currentSessionId(), 24)}` : 'session not reported',
            badge: item.decision,
            modality: 'unclassified',
            live: true,
        }));
    }

    const rail = currentAuthorityRail();
    const railSessionId = rail?.session_id && rail.session_id !== 'none' ? rail.session_id : null;
    const sessionId = State.gateB?.session_id || railSessionId;
    if (sessionId) {
        return [{
            id: sessionId,
            label: 'Session-scoped material posture',
            kind: 'authority rail',
            primary: `${rail?.approved_material_count ?? 0} approved / ${rail?.denied_material_count ?? 0} denied`,
            secondary: `typing ${rail?.typing_status || 'not_started'}`,
            badge: rail?.current_gate || 'session',
            modality: 'unclassified',
            live: true,
        }];
    }
    return [];
}

function currentTypingObjects() {
    const records = State.gateC?.typing_records || [];
    const persistedRecords = sessionSublayerState().typing_records || [];
    const sourceRecords = records.length ? records : persistedRecords;
    const typed = sourceRecords.map((record, index) => ({
        id: record.material_snapshot_id || `typing-${index + 1}`,
        label: record.planning_shape_family || 'Typed material',
        kind: record.owner_service_source_shape || 'source shape',
        primary: `modality ${humanizeToken(record.chosen_modality)}`,
        secondary: `confidence ${record.confidence ?? 'none'}`,
        badge: record.authoritative ? 'authoritative' : 'preview',
        modality: normalizeModality(record.chosen_modality || record.analysis_modality || record.planning_shape_family),
        live: true,
    }));
    const unsupported = (State.gateC?.unsupported_material || []).map((item, index) => ({
        id: item.material_snapshot_id || `unsupported-${index + 1}`,
        label: 'Unsupported material',
        kind: item.owner_service_source_shape || 'source shape',
        primary: item.reason || 'unsupported typing shape',
        secondary: 'held outside typed modality lanes',
        badge: 'unsupported',
        modality: 'unclassified',
        live: true,
    }));
    return [...typed, ...unsupported];
}

function currentPlanBody() {
    if (State.planApproval?.approved_plan) return State.planApproval.approved_plan;
    if (State.planPreview?.schema_id === 'layer3.plan_preview_result.v1') {
        return State.planPreview.plan_preview || State.planPreview;
    }
    if (sessionSublayerState().latest_plan) return sessionSublayerState().latest_plan;
    return null;
}

function currentPlanSetObjects() {
    const plan = currentPlanBody();
    const sets = (plan?.approved_sets || []).length
        ? (plan.approved_sets || [])
        : (plan?.admitted_sets || []);
    return sets.map((item, index) => ({
        id: item.analysis_set_id || `analysis-set-${index + 1}`,
        label: item.analysis_set_label || item.analysis_set_id || `Analysis set ${index + 1}`,
        kind: 'analysis set',
        primary: `modality ${humanizeToken(item.analysis_modality)}`,
        secondary: item.status || item.set_status || 'admitted',
        badge: plan?.approved || State.planApproval ? 'approved' : 'admitted',
        modality: normalizeModality(item.analysis_modality),
        live: true,
    }));
}

function currentPersistedAnalysisSetObjects() {
    return (sessionSublayerState().analysis_sets || []).map((item, index) => ({
        id: item.analysis_set_id || `persisted-analysis-set-${index + 1}`,
        label: item.analysis_set_id || `Analysis set ${index + 1}`,
        kind: item.set_type || 'analysis set',
        primary: `modality ${humanizeToken(item.analysis_modality)}`,
        secondary: item.unit_count !== undefined
            ? `${item.unit_count} unit${item.unit_count === 1 ? '' : 's'}`
            : 'formed Gate C set',
        badge: item.state || 'formed',
        modality: normalizeModality(item.analysis_modality),
        live: true,
    }));
}

function currentPlannedPasses() {
    const plan = currentPlanBody();
    return plan?.planned_passes || [];
}

function modalityFromPlanPass(pass) {
    const candidates = [
        pass?.analysis_modality,
        pass?.pass_scope,
        pass?.engine_family,
        pass?.method_family,
        pass?.pass_type,
        pass?.set_type,
    ];
    for (const candidate of candidates) {
        const modality = normalizeModality(candidate);
        if (modality && modality !== 'unclassified') return modality;
    }
    return 'unclassified';
}

function planPassesForModality(modality) {
    return currentPlannedPasses().filter((item) => modalityFromPlanPass(item) === modality);
}

function modalityFromEngineFamily(value) {
    const text = String(value || '').toLowerCase();
    if (text.includes('quant') || text.includes('deterministic')) return 'quantitative';
    if (text.includes('qual')) return 'qualitative';
    if (text.includes('hybrid') || text.includes('mixed')) return 'hybrid';
    return null;
}

function currentResultModality() {
    const fromStatus = modalityFromEngineFamily(State.resultStatus?.engine_family);
    if (fromStatus) return fromStatus;
    const passRunModalities = new Set(
        (sessionSublayerState().pass_runs || [])
            .map((passRun) => modalityFromEngineFamily(passRun.engine_family))
            .filter(Boolean)
    );
    if (passRunModalities.size === 1) return [...passRunModalities][0];
    const plannedModalities = new Set(
        currentPlannedPasses()
            .map((pass) => modalityFromPlanPass(pass))
            .filter((modality) => modality && modality !== 'unclassified')
    );
    return plannedModalities.size === 1 ? [...plannedModalities][0] : null;
}

function currentExecutionPipeline() {
    const summary = State.sessionSummary || {};
    const selection = summary.execution_selection || {};
    const start = summary.analysis_execution_start || {};
    const status = State.resultStatus || {};
    const review = recordedResultReview() || State.resultReview || {};
    const persistedPassRuns = sessionSublayerState().pass_runs || [];
    const cards = [];
    const outputs = [];

    if (selection.selected || selection.pass_run_count || (Array.isArray(selection.pass_run_ids) && selection.pass_run_ids.length)) {
        const passRunIds = Array.isArray(selection.pass_run_ids) ? selection.pass_run_ids : [];
        cards.push({
            label: 'Execution selection',
            primary: selection.state || (selection.selected ? 'selected' : 'available'),
            secondary: passRunIds.length ? `${passRunIds.length} pass run shell${passRunIds.length === 1 ? '' : 's'}` : 'no pass run shell reported',
            badge: selection.execution_started ? 'started' : 'selected',
            live: true,
        });
    }

    persistedPassRuns.slice(0, 4).forEach((passRun) => {
        cards.push({
            label: 'Pass run',
            primary: passRun.status || 'pass run shell',
            secondary: passRun.selected_method_name || passRun.pass_scope || passRun.pass_run_id || 'method not reported',
            badge: passRun.output_payload_available ? 'output ref' : (passRun.input_payload_available ? 'input ref' : 'run'),
            live: true,
        });
    });

    if (start.state || start.pass_run_id || status.execution_started) {
        cards.push({
            label: 'Execution start',
            primary: start.pass_run_status || status.pass_run_status || start.state || 'started',
            secondary: start.analysis_run_id || status.analysis_run_id || start.pass_run_id || 'analysis run not reported',
            badge: start.output_payload_ref || status.output_payload_ref ? 'output ref' : 'started',
            live: true,
        });
    }

    if (status.pass_run_status || status.result_status_available || status.next_state) {
        cards.push({
            label: 'Result status',
            primary: status.pass_run_status || status.status || status.next_state || 'available',
            secondary: status.next_state || status.pass_run_id || 'status loaded',
            badge: status.result_status_available ? 'available' : 'status',
            live: true,
        });
    }

    if (review.review_state || review.operator_decision || review.review_record_ref) {
        cards.push({
            label: 'Result review',
            primary: review.operator_decision || review.review_state || 'review recorded',
            secondary: review.review_record_ref || 'review ref not reported',
            badge: 'review',
            live: true,
        });
    }

    const outputRef = status.output_payload_ref || start.output_payload_ref;
    if (outputRef) {
        outputs.push({
            label: 'Output payload',
            primary: status.output_metadata_summary?.readable ? 'metadata readable' : 'payload reference reported',
            secondary: outputRef,
            badge: 'payload',
        });
    }
    if (status.output_metadata_summary?.artifact_count !== undefined) {
        outputs.push({
            label: 'Output artifacts',
            primary: `${status.output_metadata_summary.artifact_count} artifact${status.output_metadata_summary.artifact_count === 1 ? '' : 's'}`,
            secondary: status.output_metadata_summary.analysis_set_id || status.output_metadata_summary.source_gate || 'metadata summary',
            badge: 'metadata',
        });
    }
    const reviewedItems = Array.isArray(review.reviewed_output_items) ? review.reviewed_output_items : [];
    reviewedItems.slice(0, 6).forEach((item, index) => {
        outputs.push({
            label: item.item_type || `Reviewed item ${index + 1}`,
            primary: item.status || item.review_status || item.title || 'reviewed output item',
            secondary: item.item_ref || item.output_ref || item.trace_ref || review.review_record_ref || 'review item',
            badge: 'reviewed',
        });
    });

    const modality = currentResultModality();
    return {
        cards,
        outputs,
        modality,
        modalityLabel: modality ? modalityMeta(modality).label : 'modality not reported',
        state: outputs.length ? 'outputs' : (cards.length ? 'active' : 'empty'),
    };
}

function outputCardsForModality(modality) {
    const cards = [];
    const resultModality = currentResultModality();
    if (!resultModality || resultModality !== modality) {
        return cards;
    }
    const status = State.resultStatus;
    const start = State.sessionSummary?.analysis_execution_start || {};
    const outputRef = status?.output_payload_ref || start.output_payload_ref;
    if (outputRef) {
        cards.push({
            label: 'Output payload',
            primary: status?.output_metadata_summary?.readable ? 'metadata readable' : 'payload reference reported',
            secondary: outputRef,
            badge: 'payload',
        });
    }
    if (status?.result_status_available || TERMINAL_PASS_STATUSES.has(status?.pass_run_status)) {
        cards.push({
            label: 'Result status',
            primary: status.pass_run_status || status.status || 'available',
            secondary: status.pass_run_id || 'pass run id not reported',
            badge: 'status',
        });
    }
    const review = recordedResultReview() || State.resultReview;
    if (review?.review_state || review?.status) {
        cards.push({
            label: 'Result review',
            primary: review.operator_decision || review.review_state || review.status,
            secondary: review.review_record_ref || 'review ref not reported',
            badge: 'review',
        });
    }
    const reviewedItems = Array.isArray(review?.reviewed_output_items) ? review.reviewed_output_items : [];
    reviewedItems.slice(0, 6).forEach((item, index) => {
        cards.push({
            label: item.item_type || `Reviewed item ${index + 1}`,
            primary: item.status || item.review_status || item.title || 'reviewed output item',
            secondary: item.item_ref || item.output_ref || item.trace_ref || review.review_record_ref || 'review item',
            badge: 'reviewed',
        });
    });
    return modality === 'unclassified' ? [] : cards;
}

function sublayerStateLabel(state) {
    const labels = {
        empty: 'Awaiting live state',
        preview: 'Preview loaded',
        session: 'Session scoped',
        typed: 'Typing previewed',
        structural: 'Structural only',
        planned: 'Plan inputs loaded',
        inputs: 'Inputs routed',
        active: 'Execution state loaded',
        outputs: 'Outputs reported',
    };
    return labels[state] || humanizeToken(state);
}

function isRoutableAnalysisObject(item) {
    const modality = normalizeModality(item?.modality);
    return Boolean(modality && modality !== 'unclassified');
}

function currentSublayerVisualizationModel() {
    const rail = currentAuthorityRail() || {};
    const materialObjects = currentMaterialObjects();
    const typingObjects = currentTypingObjects();
    const planObjects = currentPlanSetObjects();
    const persistedAnalysisSetObjects = currentPersistedAnalysisSetObjects();
    const typedGroups = groupedByModality(typingObjects);
    const planGroups = groupedByModality(planObjects);
    const analysisSetGroups = groupedByModality(persistedAnalysisSetObjects);
    const plannedPasses = currentPlannedPasses();
    const executionPipeline = currentExecutionPipeline();
    const hasSessionScope = Boolean(State.gateB?.session_id || (rail.session_id && rail.session_id !== 'none'));
    const hasOutputs = SUBLAYER_MODALITIES.some((modality) => outputCardsForModality(modality).length > 0);
    const hasExecutionState = executionPipeline.cards.length > 0 || executionPipeline.outputs.length > 0;
    const hasRoutedInputs = typingObjects.some(isRoutableAnalysisObject)
        || persistedAnalysisSetObjects.some(isRoutableAnalysisObject);
    const threeAState = materialObjects.length ? (hasSessionScope ? 'session' : 'preview') : 'empty';
    const threeBState = typingObjects.length ? 'typed' : 'empty';
    const threeCState = hasOutputs ? 'outputs' : (planObjects.length || plannedPasses.length ? 'planned' : (hasExecutionState ? 'active' : (hasRoutedInputs ? 'inputs' : 'structural')));

    const gateBMessage = materialObjects.length
        ? (
            hasSessionScope
                ? 'Session-scoped material objects are represented from the current material preview, Gate B response, or authority rail.'
                : 'Source-plane material preview candidates are loaded; Gate B has not committed them into session state yet.'
        )
        : 'No source-plane material is loaded yet. Run Preflight to request material preview.';
    const gateCMessage = typingObjects.length
        ? 'Gate C typing objects are grouped by repo-reported modality.'
        : 'No Gate C typing state is loaded yet. Commit Gate B and preview Gate C to classify material.';
    const planeIntro = hasExecutionState
        ? '3C reflects the currently selected execution/result authority where the session summary or status endpoint reports it.'
        : (planObjects.length || plannedPasses.length
        ? '3C planes are populated from plan preview or approved-plan state where available.'
        : (hasRoutedInputs
            ? '3C planes show Gate C input objects where persisted typing or analysis-set state is available; process/output zones remain neutral until plan or execution state exists.'
            : '3C planes are structural and neutral until plan preview, approval, execution, or result status reports live data.'));

    const modalityBuckets = SUBLAYER_MODALITIES.map((modality) => {
        const objects = typedGroups[modality] || [];
        return {
            modality,
            meta: modalityMeta(modality),
            objects,
            state: objects.length ? 'loaded' : 'empty',
        };
    });

    const analysisPlanes = SUBLAYER_MODALITIES
        .filter((modality) => modality !== 'unclassified')
        .map((modality) => {
            const inputs = (planGroups[modality] || []).length
                ? planGroups[modality]
                : ((analysisSetGroups[modality] || []).length ? analysisSetGroups[modality] : (typedGroups[modality] || []));
            const passes = planPassesForModality(modality);
            const outputs = outputCardsForModality(modality);
            const processCards = executionPipeline.modality === modality ? executionPipeline.cards : [];
            return {
                modality,
                meta: modalityMeta(modality),
                inputs,
                passes,
                processCards,
                outputs,
                state: outputs.length ? 'outputs' : (passes.length || inputs.length ? 'inputs' : 'empty'),
            };
        });

    return {
        rail,
        intentText: currentIntentText(),
        sourceLabels: selectedSourceClassLabels(),
        threeA: {
            state: threeAState,
            stateLabel: sublayerStateLabel(threeAState),
            objects: materialObjects,
            message: gateBMessage,
        },
        threeB: {
            state: threeBState,
            stateLabel: sublayerStateLabel(threeBState),
            buckets: modalityBuckets,
            message: gateCMessage,
        },
        threeC: {
            state: threeCState,
            stateLabel: sublayerStateLabel(threeCState),
            planes: analysisPlanes,
            executionPipeline,
            message: planeIntro,
        },
    };
}

function renderFlowObjects(items, emptyMessage, options = {}) {
    const fieldLabel = options.fieldLabel || 'Object field';
    const slotCount = options.slotCount || 4;
    const ghostSlotCount = Math.max(0, slotCount - items.length);
    if (!items.length) {
        return `
            <div class="flow-empty diagram-empty" data-field-label="${escapeHtml(fieldLabel)}">
                <div class="empty-slot-field" aria-hidden="true">
                    ${Array.from({ length: slotCount }).map(() => '<span class="empty-slot"></span>').join('')}
                </div>
                <p>${escapeHtml(emptyMessage)}</p>
            </div>
        `;
    }
    return `
        <div class="flow-object-list diagram-chip-grid" data-field-label="${escapeHtml(fieldLabel)}" data-object-count="${items.length}" data-slot-count="${escapeHtml(slotCount)}">
            ${items.map((item) => {
                const modality = item.modality || 'unclassified';
                const meta = modalityMeta(modality);
                const label = shortText(item.label || item.id, 32);
                const primary = shortText(item.primary || 'No detail reported', 34);
                const ref = shortText(item.id, 22);
                const chipTitle = [
                    item.label || item.id,
                    item.primary,
                    item.id,
                ].filter(Boolean).join(' / ');
                return `
                    <article class="flow-object diagram-chip modality-${escapeHtml(modality)}" data-live-backed="${item.live ? 'true' : 'false'}" title="${escapeHtml(chipTitle)}">
                        <div class="flow-object-head">
                            <span>${escapeHtml(humanizeToken(item.kind || meta.label))}</span>
                            <span class="flow-object-badge">${escapeHtml(humanizeToken(item.badge || 'reported'))}</span>
                        </div>
                        <strong>${escapeHtml(label)}</strong>
                        <span>${escapeHtml(primary)}</span>
                        <code>${escapeHtml(ref)}</code>
                    </article>
                `;
            }).join('')}
            ${Array.from({ length: ghostSlotCount }).map(() => '<span class="flow-slot-ghost" aria-hidden="true"></span>').join('')}
        </div>
    `;
}

function renderModalityBucket(bucket) {
    const { modality, meta, objects, state } = bucket;
    const transferState = modality === 'unclassified' ? 'held' : (objects.length ? 'ready' : 'empty');
    const transferLabel = modality === 'unclassified'
        ? 'Held in 3B'
        : (objects.length ? 'Feeds 3C plane' : 'Awaiting objects');
    return `
        <section class="modality-bucket modality-${escapeHtml(modality)} viz-state-${escapeHtml(state)}" aria-label="${escapeHtml(meta.label)}" data-modality="${escapeHtml(modality)}" data-object-count="${objects.length}">
            <div class="modality-heading">
                <span class="modality-dot" aria-hidden="true"></span>
                <h4>${escapeHtml(meta.label)}</h4>
                <span>${objects.length} objects</span>
            </div>
            <div class="modality-route-label" aria-hidden="true">Object bank / grouping field</div>
            <span class="modality-transfer-rail" data-transfer-state="${escapeHtml(transferState)}">${escapeHtml(transferLabel)}</span>
            <div class="modality-bank-shell" data-diagram-role="modality-object-bank">
                <span class="modality-bank-bracket" aria-hidden="true"></span>
                ${renderFlowObjects(objects, meta.empty, { fieldLabel: `${meta.label} object bank`, slotCount: 3 })}
            </div>
        </section>
    `;
}

function renderExecutionPipeline(pipeline) {
    const processRows = pipeline.cards.length
        ? pipeline.cards.map((card) => `
            <li>
                <strong>${escapeHtml(card.label)}</strong>
                <span>${escapeHtml(shortText(card.primary, 54))}</span>
                <code>${escapeHtml(shortText(card.secondary, 42))}</code>
                <em>${escapeHtml(humanizeToken(card.badge || 'live'))}</em>
            </li>
        `).join('')
        : `
            <li>
                <strong>No selected execution state</strong>
                <span>Execution selection, start, result status, and review state are not loaded into this session view.</span>
            </li>
        `;
    const outputObjects = pipeline.outputs.map((item) => ({
        id: item.secondary,
        label: item.label,
        kind: 'execution output',
        primary: item.primary,
        badge: item.badge,
        modality: pipeline.modality || 'unclassified',
        live: true,
    }));
    return `
        <section class="execution-state-field viz-state-${escapeHtml(pipeline.state)}" data-execution-modality="${escapeHtml(pipeline.modality || 'unreported')}">
            <div class="execution-state-heading">
                <span>Selected execution / result authority</span>
                <strong>${escapeHtml(pipeline.modalityLabel)}</strong>
            </div>
            <div class="execution-state-flow">
                <section class="execution-state-process">
                    <h5>Process state</h5>
                    <ul>${processRows}</ul>
                </section>
                <span class="plane-arrow plane-arrow-output" aria-hidden="true"></span>
                <section class="execution-state-outputs">
                    <h5>Live output refs</h5>
                    ${renderFlowObjects(outputObjects, 'No execution output reference or reviewed output item is loaded.', { fieldLabel: 'selected execution output field', slotCount: 5 })}
                </section>
            </div>
        </section>
    `;
}

function renderAnalysisPlane(plane) {
    const { modality, meta, inputs, passes, processCards, outputs, state } = plane;
    const passRows = passes.map((pass) => `
            <li>
                <strong>${escapeHtml(humanizeToken(pass.pass_type || pass.method_family || 'planned pass'))}</strong>
                <span>${escapeHtml(shortText(pass.selected_method_name || pass.method_family || pass.pass_scope || 'method not reported', 52))}</span>
                <em>${escapeHtml(pass.approval_only ? 'approval only' : (pass.execution_mode || pass.status || 'planned'))}</em>
            </li>
        `).join('');
    const liveRows = (processCards || []).map((card) => `
                <li>
                    <strong>${escapeHtml(card.label)}</strong>
                    <span>${escapeHtml(shortText(card.primary, 52))}</span>
                    <em>${escapeHtml(humanizeToken(card.badge || 'live'))}</em>
                </li>
            `).join('');
    const processBody = passRows || liveRows
        ? `${passRows}${liveRows}`
        : '<li><strong>No live process yet</strong><span>Plan preview or approval has not reported a pass for this plane.</span></li>';
    return `
        <article class="analysis-plane modality-${escapeHtml(modality)} viz-state-${escapeHtml(state)}" data-modality="${escapeHtml(modality)}">
            <div class="analysis-plane-title">
                <span class="modality-dot" aria-hidden="true"></span>
                <h4>${escapeHtml(meta.plane)}</h4>
                <span class="plane-state-label">${escapeHtml(sublayerStateLabel(state))}</span>
            </div>
            <div class="plane-flow-frame" data-plane-role="analysis-environment-lane">
                <span class="plane-lane-spine" aria-hidden="true"></span>
                <span class="plane-lane-bracket" aria-hidden="true"></span>
                <div class="plane-flow">
                    <section class="plane-column plane-inputs plane-field-node plane-input-bank" data-plane-role="input-bank">
                        <h5>Input Object Bank</h5>
                        <div class="plane-input-group">
                            <span class="plane-bracket" aria-hidden="true"></span>
                            ${renderFlowObjects(inputs, 'No live input object is available for this plane.', { fieldLabel: `${meta.label} input objects`, slotCount: 3 })}
                        </div>
                    </section>
                    <span class="plane-arrow plane-arrow-process" aria-hidden="true"></span>
                    <section class="plane-process plane-field-node plane-process-node" data-plane-role="process-status" aria-label="${escapeHtml(meta.plane)} process status">
                        <h5>Process / Status</h5>
                        <ul>${processBody}</ul>
                    </section>
                    <span class="plane-arrow plane-arrow-output" aria-hidden="true"></span>
                    <section class="plane-column plane-outputs plane-field-node plane-output-field" data-plane-role="output-field">
                        <h5>Output / Result Field</h5>
                        ${renderFlowObjects(outputs.map((card) => ({
                            id: card.secondary,
                            label: card.label,
                            kind: 'output field',
                            primary: card.primary,
                            secondary: card.secondary,
                            badge: card.badge,
                            modality,
                            live: true,
                        })), 'No live output, insight, fact, or data item has been produced for this plane.', { fieldLabel: `${meta.label} generated output field`, slotCount: 6 })}
                    </section>
                </div>
            </div>
        </article>
    `;
}

function renderSourceFamilySummary(summary) {
    if (!summary) return '';
    const admitted = Array.isArray(summary.admitted_materialized_families)
        ? summary.admitted_materialized_families
        : [];
    const deferred = Array.isArray(summary.not_admitted_or_deferred_families)
        ? summary.not_admitted_or_deferred_families
        : [];
    const observed = summary.observed_candidate_counts || {};
    const admittedRows = admitted.map((family) => {
        const parserFamily = family.parser_family || family.source_family || 'unknown';
        const observedCount = observed[parserFamily] || 0;
        return `
            <li>
                <strong>${escapeHtml(family.source_family_label || parserFamily)}</strong>
                <span>${escapeHtml(family.scope || family.admission_state || 'server-backed dataset_version selection')}</span>
                <em>${escapeHtml(observedCount ? `${observedCount} candidate${observedCount === 1 ? '' : 's'}` : 'no candidates loaded')}</em>
            </li>
        `;
    }).join('');
    const deferredRows = deferred.map((family) => `
            <li>
                <strong>${escapeHtml(family.source_family_label || family.source_family || 'Deferred source family')}</strong>
                <span>${escapeHtml(family.scope || family.admission_state || 'not admitted')}</span>
                <em>${escapeHtml(humanizeToken(family.admission_state || 'deferred'))}</em>
            </li>
        `).join('');
    return `
        <section class="source-family-summary" aria-label="APS typed and refused source family boundary">
            <div>
                <span class="source-family-kicker">Server-backed typed families</span>
                <ul>${admittedRows || '<li><strong>No admitted table families reported</strong><span>Candidate endpoint did not report admitted families.</span></li>'}</ul>
            </div>
            <div>
                <span class="source-family-kicker">Deferred / refused guardrails</span>
                <ul>${deferredRows || '<li><strong>No deferred families reported</strong><span>Candidate endpoint did not report refusal guardrails.</span></li>'}</ul>
            </div>
            <p>${escapeHtml(summary.ui_scope || 'Only materialized APS-derived DatasetVersion records are selectable here.')}</p>
        </section>
    `;
}

function renderRawMixedMaterializationPanel() {
    if (!elements.rawMixedMaterializationStatus || !elements.rawMixedMaterializationState) return;
    const materialization = State.rawMixedMaterialization;
    if (State.rawMixedMaterializationPending) {
        elements.rawMixedMaterializationState.textContent = 'Materializing';
        elements.rawMixedMaterializationState.className = 'status-pill preview';
        elements.rawMixedMaterializationStatus.textContent = 'Materialization request is in flight.';
        return;
    }
    if (State.rawMixedMaterializationError) {
        elements.rawMixedMaterializationState.textContent = 'Blocked';
        elements.rawMixedMaterializationState.className = 'status-pill blocked';
        elements.rawMixedMaterializationStatus.textContent = State.rawMixedMaterializationError.message
            || State.rawMixedMaterializationError.error_code
            || 'Materialization failed closed.';
        return;
    }
    if (materialization) {
        const datasetCount = (materialization.dataset_version_ids || []).length;
        const contentCount = (materialization.aps_content_document_ids || []).length;
        elements.rawMixedMaterializationState.textContent = 'Materialized';
        elements.rawMixedMaterializationState.className = 'status-pill ok';
        elements.rawMixedMaterializationStatus.textContent = `${datasetCount} DatasetVersion ID${datasetCount === 1 ? '' : 's'} and ${contentCount} APS content document ID${contentCount === 1 ? '' : 's'} selected after candidate refresh.`;
        return;
    }
    const form = rawMixedMaterializationFormState();
    const ready = canMaterializeRawMixed();
    elements.rawMixedMaterializationState.textContent = ready ? 'Ready' : 'Not materialized';
    elements.rawMixedMaterializationState.className = ready ? 'status-pill ok' : 'status-pill preview';
    if (form.requestedSourceClasses.length !== RAW_MIXED_MATERIALIZE_ALLOWED_SOURCE_CLASSES.size) {
        elements.rawMixedMaterializationStatus.textContent = 'Select both Dataset version and APS content document source classes.';
    } else if (!form.corpusBatchId || !form.manifestRef || !form.manifestHash || !form.operatorConfirmed) {
        elements.rawMixedMaterializationStatus.textContent = 'Awaiting server-owned manifest authority.';
    } else {
        elements.rawMixedMaterializationStatus.textContent = 'Ready to call the server-owned materialization route.';
    }
}

function renderDatasetVersionCandidates() {
    if (!elements.datasetVersionCandidates) return;
    const summaryMarkup = renderSourceFamilySummary(State.datasetVersionCandidates?.source_family_summary);
    if (State.datasetVersionCandidateError) {
        elements.datasetVersionCandidates.innerHTML = `
            ${summaryMarkup}
            <span class="dataset-version-empty">DatasetVersion candidate lookup failed: ${escapeHtml(State.datasetVersionCandidateError)}</span>
        `;
        return;
    }
    const candidates = State.datasetVersionCandidates?.dataset_version_candidates || [];
    const selectedIds = new Set(selectedDatasetVersionIds());
    if (!candidates.length) {
        elements.datasetVersionCandidates.innerHTML = `
            ${summaryMarkup}
            <span class="dataset-version-empty">No server-backed materialized dataset versions were found in the active runtime. Paste explicit IDs if you have them from a materialization report.</span>
        `;
        return;
    }
    const candidateMarkup = candidates.map((candidate) => {
        const datasetVersionId = String(candidate.dataset_version_id || '');
        const title = candidate.dataset_name || candidate.version_label || datasetVersionId;
        const detail = [
            candidate.source_family_label,
            candidate.source_admission_state ? humanizeToken(candidate.source_admission_state) : null,
            candidate.version_type,
            candidate.parser_family,
            candidate.typed_content_contract_id,
            candidate.row_count != null ? `${candidate.row_count} rows` : null,
            candidate.variable_count != null ? `${candidate.variable_count} variables` : null,
        ].filter(Boolean).join(' / ');
        return `
            <label class="dataset-version-candidate">
                <input type="checkbox" name="dataset-version-candidate" value="${escapeHtml(datasetVersionId)}" ${selectedIds.has(datasetVersionId) ? 'checked' : ''}>
                <span>
                    <strong>${escapeHtml(title)}</strong>
                    <code>${escapeHtml(datasetVersionId)}</code>
                    <span>${escapeHtml(detail || 'APS-derived dataset version')}</span>
                    ${candidate.source_family_scope ? `<small>${escapeHtml(candidate.source_family_scope)}</small>` : ''}
                </span>
            </label>
        `;
    }).join('');
    elements.datasetVersionCandidates.innerHTML = `${summaryMarkup}${candidateMarkup}`;
}

function renderApsContentDocumentCandidates() {
    if (!elements.apsContentDocumentCandidates) return;
    if (State.apsContentDocumentCandidateError) {
        elements.apsContentDocumentCandidates.innerHTML = `
            <span class="aps-content-document-empty">APS content document lookup failed: ${escapeHtml(State.apsContentDocumentCandidateError)}</span>
        `;
        return;
    }
    const candidates = State.apsContentDocumentCandidates?.aps_content_document_candidates || [];
    const selectedIds = new Set(selectedApsContentDocumentIds());
    if (!candidates.length) {
        elements.apsContentDocumentCandidates.innerHTML = `
            <span class="aps-content-document-empty">No indexed APS content documents were found in the active runtime. Paste explicit content IDs if you have them from an APS content report.</span>
        `;
        return;
    }
    elements.apsContentDocumentCandidates.innerHTML = candidates.map((candidate) => {
        const contentId = String(candidate.content_id || '');
        const title = candidate.accession_number || candidate.document_class || contentId;
        const detail = [
            candidate.source_family_label,
            candidate.source_admission_state ? humanizeToken(candidate.source_admission_state) : null,
            candidate.media_type,
            candidate.document_class,
            candidate.content_contract_id,
            candidate.chunk_count != null ? `${candidate.chunk_count} chunks` : null,
            candidate.page_count != null ? `${candidate.page_count} pages` : null,
        ].filter(Boolean).join(' / ');
        return `
            <label class="aps-content-document-candidate">
                <input type="checkbox" name="aps-content-document-candidate" value="${escapeHtml(contentId)}" ${selectedIds.has(contentId) ? 'checked' : ''}>
                <span>
                    <strong>${escapeHtml(title)}</strong>
                    <code>${escapeHtml(contentId)}</code>
                    <span>${escapeHtml(detail || 'Indexed APS content document')}</span>
                    ${candidate.source_family_scope ? `<small>${escapeHtml(candidate.source_family_scope)}</small>` : ''}
                </span>
            </label>
        `;
    }).join('');
}

function renderSublayerMap() {
    if (!elements.sublayerMapPanel) return;
    const model = currentSublayerVisualizationModel();
    const rail = model.rail;
    const sourceLabels = model.sourceLabels;
    const activeOperation = OPERATION_DOCK_STEPS.find((step) => step.id === State.activeOperationId);

    elements.sublayerMapPanel.dataset.vizState = `${model.threeA.state}|${model.threeB.state}|${model.threeC.state}`;
    elements.sublayerMapPanel.dataset.activeOperationCanvas = activeOperation?.canvasTarget || '3a';
    elements.sublayerMapPanel.dataset.activeOperationKey = activeOperation?.key || 'intent';
    elements.sublayerMapPanel.innerHTML = `
        <section class="canvas-intake-spec" aria-label="Layer 3 intake specification">
            <div class="intake-spec-frame">
                <article class="query-spec-block">
                    <span>User Natural Language Query Input</span>
                    <p>${escapeHtml(shortText(model.intentText, 170))}</p>
                </article>
                <article class="manual-source-spec">
                    <span>User Manual / Custom Source Specification</span>
                    <div class="source-spec-chip-grid">
                        ${sourceLabels.length
                            ? sourceLabels.map((label) => `<span class="source-spec-chip">${escapeHtml(label)}</span>`).join('')
                            : '<span class="source-spec-chip muted">No source classes selected</span>'}
                    </div>
                </article>
            </div>
        </section>
        <section class="workflow-canvas-field" aria-label="Layer 3 3A to 3B to 3C workflow canvas">
            <nav class="canvas-state-flow" aria-label="Layer 3 visualization state">
                <span class="state-node state-3a viz-state-${escapeHtml(model.threeA.state)}">
                    <strong>3A</strong>
                    <span>${escapeHtml(model.threeA.stateLabel)}</span>
                </span>
                <span class="state-flow-link" aria-hidden="true"></span>
                <span class="state-node state-3b viz-state-${escapeHtml(model.threeB.state)}">
                    <strong>3B</strong>
                    <span>${escapeHtml(model.threeB.stateLabel)}</span>
                </span>
                <span class="state-flow-link" aria-hidden="true"></span>
                <span class="state-node state-3c viz-state-${escapeHtml(model.threeC.state)}">
                    <strong>3C</strong>
                    <span>${escapeHtml(model.threeC.stateLabel)}</span>
                </span>
            </nav>
            <section class="sublayer-region sublayer-3a viz-state-${escapeHtml(model.threeA.state)}" aria-label="Sublayer 3A material intake and session scoping">
                <div class="sublayer-title">
                    <span>Sublayer 3A</span>
                    <strong>Material Intake &amp; Session Scoping</strong>
                    <em>${escapeHtml(model.threeA.stateLabel)}</em>
                </div>
                <div class="gate-panel diagram-gate">
                    <h3>Gate B / Session Entry / Material Ledger</h3>
                    <p>${escapeHtml(model.threeA.message)}</p>
                    <div class="mini-rail">
                        <span>Session ${escapeHtml(shortText(rail.session_id || 'none', 24))}</span>
                        <span>Approved ${escapeHtml(rail.approved_material_count ?? 0)}</span>
                        <span>Denied ${escapeHtml(rail.denied_material_count ?? 0)}</span>
                        <span>Typing ${escapeHtml(rail.typing_status || 'not_started')}</span>
                    </div>
                </div>
                <div class="ledger-chip-field">
                    <div class="ledger-bracket"><span>Session-scoped Materials / Material Snapshots</span></div>
                    <div class="material-bank-shell" data-diagram-role="source-plane-material-field">
                        <span class="material-bank-bracket" aria-hidden="true"></span>
                        ${renderFlowObjects(model.threeA.objects, 'No material preview, session entry, or material ledger object is currently loaded.', { fieldLabel: '3A material ledger object field', slotCount: 6 })}
                    </div>
                </div>
            </section>
            <div class="sublayer-connector sublayer-connector-3ab" aria-hidden="true"><span>3A to 3B</span></div>
            <section class="analysis-routing-plane" aria-label="Sublayer 3B to 3C analysis routing">
                <section class="sublayer-region sublayer-3b viz-state-${escapeHtml(model.threeB.state)}" aria-label="Sublayer 3B typing and set formation">
                    <div class="sublayer-title">
                        <span>Sublayer 3B</span>
                        <strong>Typing, Unit/Group/Set Formation</strong>
                        <em>${escapeHtml(model.threeB.stateLabel)}</em>
                    </div>
                    <div class="gate-panel diagram-gate">
                        <h3>Gate C Typing</h3>
                        <p>${escapeHtml(model.threeB.message)}</p>
                    </div>
                    <div class="modality-bank-field">
                        <div class="field-bracket modality-field-bracket"><span>Modality Object Banks / Ingress Containers</span></div>
                        <div class="modality-buckets">
                            ${model.threeB.buckets.map((bucket) => renderModalityBucket(bucket)).join('')}
                        </div>
                    </div>
                </section>
                <div class="sublayer-connector sublayer-connector-3bc" aria-hidden="true"><span>3B to 3C</span></div>
                <section class="sublayer-region sublayer-3c viz-state-${escapeHtml(model.threeC.state)}" aria-label="Sublayer 3C analysis execution environments">
                    <div class="sublayer-title">
                        <span>Sublayer 3C</span>
                        <strong>Analysis Execution Environments / Planes</strong>
                        <em>${escapeHtml(model.threeC.stateLabel)}</em>
                    </div>
                    <div class="gate-panel diagram-gate">
                        <h3>Input To Process To Output</h3>
                        <p>${escapeHtml(model.threeC.message)}</p>
                    </div>
                    ${renderExecutionPipeline(model.threeC.executionPipeline)}
                    <div class="analysis-plane-field">
                        <div class="field-bracket analysis-field-bracket"><span>Analysis Environment Planes / Input To Output Fields</span></div>
                        <div class="analysis-lane-legend" aria-hidden="true">
                            <span class="analysis-lane-label lane-label-input">Input object bank</span>
                            <span class="analysis-lane-arrow">route</span>
                            <span class="analysis-lane-label lane-label-process">Process / status</span>
                            <span class="analysis-lane-arrow">produce</span>
                            <span class="analysis-lane-label lane-label-output">Output field</span>
                        </div>
                        <div class="analysis-planes">
                            ${model.threeC.planes.map((plane) => renderAnalysisPlane(plane)).join('')}
                        </div>
                    </div>
                </section>
            </section>
        </section>
    `;
}

function renderMaterialTrace(candidate) {
    const trace = candidate.source_trace || candidate.source_provenance?.source_trace;
    if (!trace) {
        return '<div class="material-trace-card material-trace-empty">No server trace detail.</div>';
    }
    const refs = trace.aps_trace_refs || {};
    const variables = trace.variable_summary || {};
    const storage = trace.storage_summary || {};
    const documentIdentity = trace.document_identity || {};
    const chunks = trace.chunk_summary || {};
    const numericVariables = Array.isArray(variables.numeric_variables)
        ? variables.numeric_variables
        : [];
    const timeVariables = Array.isArray(variables.time_variables)
        ? variables.time_variables
        : [];
    const detailRows = [
        ['family', trace.source_family_label || trace.source_family],
        ['readiness', trace.trace_readiness],
        ['parser', refs.parser_family],
        ['contract', refs.typed_content_contract_id || refs.parser_contract_id || documentIdentity.content_contract_id],
        ['content', documentIdentity.content_id],
        ['chunking', documentIdentity.chunking_contract_id],
        ['target', refs.target_id],
        ['accession', refs.accession_number],
        ['rows', storage.row_count],
        ['chunks', chunks.loaded_chunk_count ?? chunks.chunk_count],
        ['pages', chunks.page_count],
        ['media', documentIdentity.media_type],
        ['class', documentIdentity.document_class],
        ['variables', variables.variable_count],
        ['numeric', numericVariables.join(', ')],
        ['time', variables.time_column || timeVariables.join(', ')],
        ['units', refs.content_units_ref],
        ['blob', refs.blob_ref],
        ['diagnostics', refs.diagnostics_ref],
    ].filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== '');
    return `
        <div class="material-trace-card" data-trace-readiness="${escapeHtml(trace.trace_readiness || 'unknown')}">
            <strong>${escapeHtml(trace.source_family_label || 'DatasetVersion trace')}</strong>
            <span>${escapeHtml(trace.ui_summary || trace.source_family_scope || 'Server trace detail available.')}</span>
            <dl>
                ${detailRows.map(([label, value]) => `
                    <div>
                        <dt>${escapeHtml(label)}</dt>
                        <dd>${escapeHtml(shortText(value, 48))}</dd>
                    </div>
                `).join('')}
            </dl>
        </div>
    `;
}

function renderMaterialLedger() {
    const candidates = State.materialPreview?.material_candidates || [];
    const filter = State.materialFilter.trim().toLowerCase();
    const visible = filter
        ? candidates.filter((candidate) => candidateSearchText(candidate).includes(filter))
        : candidates;
    if (!visible.length) {
        const message = candidates.length ? 'No material candidates match the filter.' : 'No material preview loaded.';
        elements.materialLedgerBody.innerHTML = `<tr><td colspan="7" class="empty-cell">${escapeHtml(message)}</td></tr>`;
        return;
    }
    elements.materialLedgerBody.innerHTML = visible.map((candidate) => {
        const currentDecision = decisionState(candidate.candidate_id);
        const traceMarkup = renderMaterialTrace(candidate);
        return `
        <tr data-candidate-id="${escapeHtml(candidate.candidate_id)}">
            <td>
                <div class="candidate-id">${escapeHtml(candidate.candidate_id)}</div>
                <span class="source-badge">${escapeHtml(candidate.validation_status)}</span>
            </td>
            <td>${escapeHtml(candidate.source_label)}</td>
            <td>
                <div>${escapeHtml(candidate.owner_service_source_shape)}</div>
                <div class="rail-label">${escapeHtml(candidate.planning_shape_family)}</div>
            </td>
            <td>${traceMarkup}</td>
            <td>
                <div>${escapeHtml(candidate.duplicate_status)}</div>
                <div class="rail-label">${escapeHtml(candidate.query_basis)}</div>
            </td>
            <td>
                <select class="decision-select" aria-label="Decision for ${escapeHtml(candidate.candidate_id)}">
                    <option value="approved" ${currentDecision.decision === 'approved' ? 'selected' : ''}>Approved</option>
                    <option value="denied" ${currentDecision.decision === 'denied' ? 'selected' : ''}>Denied</option>
                    <option value="isolated" ${currentDecision.decision === 'isolated' ? 'selected' : ''}>Isolated</option>
                    <option value="flagged" ${currentDecision.decision === 'flagged' ? 'selected' : ''}>Flagged</option>
                </select>
            </td>
            <td>
                <input class="reason-input" type="text" value="${escapeHtml(currentDecision.operator_reason)}" placeholder="Required for denied, isolated, or flagged">
            </td>
        </tr>
    `;
    }).join('');
}

function materialCandidateById(candidateId) {
    return (State.materialPreview?.material_candidates || [])
        .find((candidate) => candidate.candidate_id === candidateId);
}

function initializeGateBDecisions() {
    State.gateBDecisions = {};
    State.gateBClientRequestId = null;
    for (const candidate of State.materialPreview?.material_candidates || []) {
        State.gateBDecisions[candidate.candidate_id] = {
            decision: 'approved',
            operator_reason: '',
        };
    }
    if (!restoreGateBDraftSnapshot()) {
        persistGateBDraftSnapshot();
    }
}

function collectGateBDecisions() {
    return (State.materialPreview?.material_candidates || []).map((candidate) => {
        const currentDecision = decisionState(candidate.candidate_id);
        return {
            candidate_id: candidate.candidate_id,
            decision: currentDecision.decision,
            operator_reason: currentDecision.operator_reason,
            decision_basis: {
                source_ref: candidate.source_ref,
                query_basis: candidate.query_basis,
                provenance_ref: candidate.provenance_ref,
                source_identity: candidate.source_identity || {},
                source_provenance: candidate.source_provenance || {},
                payload: candidate.payload || {},
                load_summary: candidate.load_summary || {},
                owner_service_source_shape: candidate.owner_service_source_shape,
                planning_shape_family: candidate.planning_shape_family,
            },
        };
    });
}

function renderGateCPanel() {
    const records = State.gateC?.typing_records || [];
    const unsupported = State.gateC?.unsupported_material || [];
    if (!records.length && !unsupported.length) {
        elements.gateCPanel.innerHTML = '<div class="empty-panel">No committed Gate B session yet.</div>';
        return;
    }
    const cards = records.map((record) => `
        <article class="typing-card">
            <h3>${escapeHtml(record.planning_shape_family)}</h3>
            <div class="typing-meta">
                <span>Snapshot: ${escapeHtml(record.material_snapshot_id)}</span>
                <span>Shape: ${escapeHtml(record.owner_service_source_shape)}</span>
                <span>Modality: ${escapeHtml(record.chosen_modality)}</span>
                <span>Confidence: ${escapeHtml(record.confidence)}</span>
                <span>Authoritative: ${record.authoritative ? 'yes' : 'no'}</span>
            </div>
        </article>
    `);
    const unsupportedRows = unsupported.map((item) => `
        <article class="typing-card">
            <h3>Unsupported Material</h3>
            <div class="typing-meta">
                <span>Snapshot: ${escapeHtml(item.material_snapshot_id)}</span>
                <span>Shape: ${escapeHtml(item.owner_service_source_shape)}</span>
                <span>Reason: ${escapeHtml(item.reason)}</span>
            </div>
        </article>
    `);
    elements.gateCPanel.innerHTML = [...cards, ...unsupportedRows].join('');
}

function canPlanPreview() {
    return Boolean(currentSessionId() && isTypingCommitted());
}

function canPlanApprove() {
    return Boolean(
        currentSessionId()
        && State.planPreview?.schema_id === 'layer3.plan_preview_result.v1'
        && State.planPreview?.preview_id
        && State.planPreview?.preview_hash
        && !State.planApproval
        && !State.planRevision
        && !State.planRevisionPending
    );
}

function canPlanRevise() {
    return Boolean(
        currentSessionId()
        && State.planPreview?.schema_id === 'layer3.plan_preview_result.v1'
        && State.planPreview?.preview_id
        && State.planPreview?.preview_hash
        && !State.planApproval
        && !State.planRevision
        && !State.planRevisionPending
    );
}

function canSelectExecution() {
    const authority = executionPlanAuthority();
    const selection = executionSelectionState();
    return Boolean(
        currentSessionId()
        && authority.analysisPlanId
        && authority.previewId
        && authority.previewHash
        && (
            State.planApproval?.analysis_plan_id
            || State.sessionSummary?.execution_selection?.available === true
        )
        && !State.planRevision
        && !State.planRevisionPending
        && !State.executionSelection
        && selection.selected !== true
        && !State.executionSelectionPending
        && !State.executionStartPending
    );
}

function canStartExecution() {
    const selection = executionSelectionState();
    const start = executionStartState();
    const authority = executionPlanAuthority();
    const passRunIds = Array.isArray(selection.pass_run_ids)
        ? selection.pass_run_ids
        : [];
    return Boolean(
        currentSessionId()
        && authority.analysisPlanId
        && authority.previewId
        && authority.previewHash
        && passRunIds[0]
        && start.execution_started !== true
        && !State.executionSelectionPending
        && !State.executionStartPending
    );
}

function renderPlanPanel() {
    if (State.planRevision) {
        const label = State.planRevision.next_state === 'plan_rejected' ? 'rejected' : 'revision requested';
        elements.planPanel.innerHTML = `
            <div class="plan-summary-grid">
                <div class="plan-summary-card"><strong>Revision Control</strong>${escapeHtml(label)}</div>
                <div class="plan-summary-card"><strong>Preview</strong><code>${escapeHtml(State.planRevision.source_preview_id)}</code></div>
                <div class="plan-summary-card"><strong>Execution</strong>${escapeHtml(State.planRevision.execution_started ? 'started' : 'not started')}</div>
            </div>
            <div class="plan-preview-grid">
                <section class="plan-list"><h3>Decision</h3><ul>
                    <li>${escapeHtml(State.planRevision.operator_decision)}</li>
                    <li>Note recorded: ${escapeHtml(State.planRevision.operator_note_recorded ? 'yes' : 'no')}</li>
                    <li>Approval blocked for this preview.</li>
                </ul></section>
                <section class="plan-list"><h3>Boundary</h3><ul>
                    <li>No execution started.</li>
                    <li>No pass runs created.</li>
                    <li>Results, package review, and handoff remain unavailable.</li>
                </ul></section>
            </div>
        `;
        return;
    }
    if (State.planApproval) {
        const approved = State.planApproval.approved_plan || {};
        const approvedSets = approved.approved_sets || [];
        const excluded = approved.excluded_sets || [];
        const planned = approved.planned_passes || [];
        const warningRows = (approved.warnings || []).length
            ? approved.warnings.map((item) => `<li>${escapeHtml(item.reason_code)}: ${escapeHtml(item.message)}</li>`).join('')
            : '<li>No warnings.</li>';
        const plannedRows = planned.length
            ? planned.map((item) => `
                <li>
                    <code>${escapeHtml(item.analysis_set_id)}</code>
                    ${escapeHtml(item.pass_type)} / ${escapeHtml(item.pass_scope)}
                    (${escapeHtml(item.selected_method_name || item.method_family)})
                </li>
            `).join('')
            : '<li>No planned passes.</li>';
        elements.planPanel.innerHTML = `
            <div class="plan-summary-grid">
                <div class="plan-summary-card"><strong>Approval</strong>approved</div>
                <div class="plan-summary-card"><strong>Plan ID</strong><code>${escapeHtml(State.planApproval.analysis_plan_id)}</code></div>
                <div class="plan-summary-card"><strong>Approved Sets</strong>${approvedSets.length}</div>
                <div class="plan-summary-card"><strong>Excluded</strong>${excluded.length}</div>
                <div class="plan-summary-card"><strong>Execution</strong>${escapeHtml(State.planApproval.execution_started ? 'started' : 'not started')}</div>
            </div>
            <div class="plan-preview-grid">
                <section class="plan-list"><h3>Approved Passes</h3><ul>${plannedRows}</ul></section>
                <section class="plan-list"><h3>Approval Basis</h3><ul>
                    <li>Approved at: ${escapeHtml(State.planApproval.approved_at)}</li>
                    <li>Preview: <code>${escapeHtml(approved.source_preview_id)}</code></li>
                    <li>Owner mode: ${escapeHtml(approved.owner_service_basis?.mode)}</li>
                </ul></section>
                <section class="plan-list"><h3>Warnings</h3><ul class="warning-list">${warningRows}</ul></section>
            </div>
        `;
        return;
    }
    const body = State.planPreview;
    if (!body) {
        elements.planPanel.innerHTML = canPlanPreview()
            ? '<div class="empty-panel">Plan preview is ready to request.</div>'
            : '<div class="empty-panel">Commit Gate C typing before plan preview.</div>';
        return;
    }
    if (body.schema_id === 'layer3.workbench_error.v1') {
        elements.planPanel.innerHTML = `
            <div class="plan-list">
                <h3>Plan Preview Blocked</h3>
                <ul>
                    <li><strong>${escapeHtml(body.error_code)}</strong>: ${escapeHtml(body.message)}</li>
                    ${(body.next_allowed_actions || []).map((action) => `<li>${escapeHtml(action)}</li>`).join('')}
                </ul>
            </div>
        `;
        return;
    }
    const preview = body.plan_preview || {};
    const admitted = preview.admitted_sets || [];
    const excluded = preview.excluded_sets || [];
    const planned = preview.planned_passes || [];
    const warnings = preview.warnings || [];
    const plannedRows = planned.length
        ? planned.map((item) => `
            <li>
                <code>${escapeHtml(item.analysis_set_id)}</code>
                ${escapeHtml(item.pass_type)} / ${escapeHtml(item.pass_scope)}
                (${escapeHtml(item.selected_method_name || item.method_family)})
            </li>
        `).join('')
        : '<li>No planned passes.</li>';
    const admittedRows = admitted.length
        ? admitted.map((item) => `<li><code>${escapeHtml(item.analysis_set_id)}</code> ${escapeHtml(item.readiness)} ${escapeHtml(item.analysis_modality)}</li>`).join('')
        : '<li>No admitted sets.</li>';
    const excludedRows = excluded.length
        ? excluded.map((item) => `<li><code>${escapeHtml(item.analysis_set_id)}</code> ${escapeHtml(item.reason_code)}</li>`).join('')
        : '<li>No excluded sets.</li>';
    const warningRows = warnings.length
        ? warnings.map((item) => `<li>${escapeHtml(item.reason_code)}: ${escapeHtml(item.message)}</li>`).join('')
        : '<li>No warnings.</li>';
    elements.planPanel.innerHTML = `
        <div class="plan-summary-grid">
            <div class="plan-summary-card"><strong>Preview</strong>${escapeHtml(body.preview_only ? 'preview only' : 'unknown')}</div>
            <div class="plan-summary-card"><strong>Admitted</strong>${admitted.length}</div>
            <div class="plan-summary-card"><strong>Excluded</strong>${excluded.length}</div>
            <div class="plan-summary-card"><strong>Passes</strong>${planned.length}</div>
        </div>
        <div class="plan-preview-grid">
            <section class="plan-list"><h3>Planned Passes</h3><ul>${plannedRows}</ul></section>
            <section class="plan-list"><h3>Admitted Sets</h3><ul>${admittedRows}</ul></section>
            <section class="plan-list"><h3>Exclusions</h3><ul>${excludedRows}</ul></section>
            <section class="plan-list"><h3>Warnings</h3><ul class="warning-list">${warningRows}</ul></section>
        </div>
    `;
}

function displayValue(value) {
    if (value === true) return 'true';
    if (value === false) return 'false';
    if (value === 0) return '0';
    return value || 'unknown';
}

function fieldItem(label, value, { code = false } = {}) {
    const escaped = escapeHtml(displayValue(value));
    const body = code ? `<code>${escaped}</code>` : escaped;
    return `<li>${escapeHtml(label)}: ${body}</li>`;
}

function summarizeTrace(value) {
    if (!value || typeof value !== 'object') return 'none';
    return Object.entries(value)
        .map(([key, item]) => `${key}=${displayValue(item)}`)
        .join(', ');
}

function resultReviewPanelState(authority) {
    const cohort = associatedCohortProjection(authority);
    if (State.resultReviewPending) {
        return {
            label: cohort.isAssociated ? 'cohort_result_review_ui_recording' : 'result_review_ui_recording',
            pill: 'preview',
            message: 'Recording one bounded operator decision.',
        };
    }
    if (recordedResultReview()) {
        return {
            label: cohort.isAssociated ? 'cohort_result_review_ui_recorded' : 'result_review_ui_recorded',
            pill: 'ok',
            message: 'Server state already contains a result-review record.',
        };
    }
    if (State.resultReviewError || State.resultStatusError) {
        return {
            label: cohort.isAssociated ? 'cohort_result_review_ui_blocked' : 'result_review_ui_blocked',
            pill: 'blocked',
            message: 'Server authority rejected or blocked the latest result-review action.',
        };
    }
    if (!authority.sessionId) {
        return { label: 'result_review_ui_unavailable', pill: 'blocked', message: 'No Layer 3 session id is available.' };
    }
    if (!State.sessionSummary && !State.executionSelection && !State.executionStart) {
        return { label: 'result_review_ui_unavailable', pill: 'blocked', message: 'Refresh session state before inspecting result status.' };
    }
    if (!hasResultAuthorityIdentity(authority) || !authority.selected) {
        return { label: 'result_review_ui_waiting_for_selection', pill: 'blocked', message: 'Server summary has no selected pass authority.' };
    }
    if (!authority.terminal) {
        return {
            label: cohort.isAssociated ? 'cohort_result_review_ui_waiting_for_execution' : 'result_review_ui_waiting_for_execution_start',
            pill: 'blocked',
            message: 'Selected pass is not terminal.',
        };
    }
    if (State.resultStatus?.result_status_available === true) {
        if (cohort.isAssociated && !cohort.ready) {
            return {
                label: 'cohort_result_review_ui_blocked',
                pill: 'blocked',
                message: 'Associated-cohort status is available, but exact method, provenance, or trace readiness is incomplete.',
            };
        }
        if (cohort.ready) {
            return {
                label: 'cohort_result_review_ui_review_ready',
                pill: 'ok',
                message: 'Exact selected-pass associated-cohort descriptive result/status authority is ready for one review.',
            };
        }
        return { label: 'result_review_ui_review_ready', pill: 'ok', message: 'Result/status authority is available for one selected terminal pass.' };
    }
    if (State.resultStatus) {
        return {
            label: cohort.isAssociated ? 'cohort_result_review_ui_blocked' : 'result_review_ui_blocked',
            pill: 'blocked',
            message: 'Result/status authority is not available for review.',
        };
    }
    return { label: 'result_review_ui_unavailable', pill: 'preview', message: 'Selected terminal pass can be inspected for result/status availability.' };
}

function renderErrorCard(error) {
    if (!error) return '';
    const actions = Array.isArray(error.next_allowed_actions) ? error.next_allowed_actions : [];
    return `
        <section class="result-review-card">
            <strong>Block Reason</strong>
            <ul>
                ${fieldItem('code', error.error_code || error.status)}
                ${fieldItem('message', error.message)}
                ${actions.map((action) => `<li>next action: ${escapeHtml(action)}</li>`).join('')}
            </ul>
        </section>
    `;
}

function renderDownstreamLocks(labels) {
    const locks = labels?.length ? labels : ['package', 'handoff', 'package_review'];
    return locks.map((label) => `<span class="status-pill blocked">${escapeHtml(label.replace(/_/g, ' '))}</span>`).join('');
}

function executionSelectionPanelState() {
    const authority = executionPlanAuthority();
    const selection = executionSelectionState();
    if (State.executionStartPending) {
        return { label: 'execution_starting', pill: 'preview', message: 'Starting the selected pass through server authority.' };
    }
    if (State.executionSelectionPending) {
        return { label: 'execution_selecting', pill: 'preview', message: 'Selecting pass runs for the approved plan.' };
    }
    if (State.executionStart?.execution_started === true) {
        return { label: 'execution_started', pill: 'ok', message: 'Execution started for the server-selected pass.' };
    }
    if (State.executionStartError || State.executionSelectionError) {
        return { label: 'execution_blocked', pill: 'blocked', message: 'Server authority rejected or blocked the latest execution action.' };
    }
    if (selection.pass_run_count) {
        return { label: 'execution_selected', pill: 'ok', message: 'Server-selected pass run is ready to start.' };
    }
    if (authority.analysisPlanId && authority.previewId && authority.previewHash) {
        return { label: 'execution_selection_ready', pill: 'preview', message: 'Approved plan is ready for execution selection.' };
    }
    return { label: 'execution_not_ready', pill: 'blocked', message: 'Approve a plan before execution selection.' };
}

function renderExecutionSelectionStartPanel() {
    const panelState = executionSelectionPanelState();
    const selection = executionSelectionState();
    const start = executionStartState();
    const error = State.executionStartError || State.executionSelectionError;
    const passRunIds = Array.isArray(selection.pass_run_ids) ? selection.pass_run_ids : [];
    const analysisRunIds = Array.isArray(selection.analysis_run_ids) ? selection.analysis_run_ids : [];
    const previewIdentity = start.preview_identity || selection.preview_identity || {};
    elements.executionSelectionStartPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Execution Selection</strong>
                <ul>
                    ${fieldItem('session', selection.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('analysis plan', selection.analysis_plan_id || State.planApproval?.analysis_plan_id || State.sessionSummary?.plan_approval?.analysis_plan_id, { code: true })}
                    ${fieldItem('preview', previewIdentity.preview_id || selection.source_preview_id || State.planPreview?.preview_id, { code: true })}
                    ${fieldItem('preview hash', previewIdentity.preview_hash || selection.source_preview_hash || State.planPreview?.preview_hash, { code: true })}
                    ${fieldItem('pass run count', selection.pass_run_count)}
                    ${fieldItem('first pass run', passRunIds[0], { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Execution Start</strong>
                <ul>
                    ${fieldItem('started', start.execution_started)}
                    ${fieldItem('pass run', start.pass_run_id || passRunIds[0], { code: true })}
                    ${fieldItem('pass status', start.pass_run_status)}
                    ${fieldItem('analysis run', start.analysis_run_id || analysisRunIds[0], { code: true })}
                    ${fieldItem('output ref', start.output_payload_ref, { code: true })}
                    ${fieldItem('next state', start.next_state || selection.next_state)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(start.downstream_unavailable || selection.downstream_unavailable || currentDownstreamUnavailable())}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function renderResultReviewPanel() {
    const authority = selectedResultAuthority();
    const statusBody = State.resultStatus || {};
    const reviewState = recordedResultReview();
    const panelState = resultReviewPanelState(authority);
    const metadata = statusBody.output_metadata_summary || {};
    const cohort = associatedCohortProjection(authority);
    const traceSummary = State.resultReview?.trace_summary || reviewState?.trace_summary;
    const error = State.resultReviewError || State.resultStatusError;
    const downstream = State.resultReview?.downstream_unavailable
        || statusBody.downstream_unavailable
        || reviewState?.downstream_unavailable
        || currentDownstreamUnavailable();

    elements.resultReviewPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Selected Authority</strong>
                <ul>
                    ${fieldItem('session', authority.sessionId, { code: true })}
                    ${fieldItem('analysis plan', authority.analysisPlanId, { code: true })}
                    ${fieldItem('pass run', authority.passRunId, { code: true })}
                    ${fieldItem('preview', authority.previewId, { code: true })}
                    ${fieldItem('preview hash', authority.previewHash, { code: true })}
                    ${fieldItem('pass status', authority.passStatus)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Result Status</strong>
                <ul>
                    ${fieldItem('status', statusBody.status)}
                    ${fieldItem('available', statusBody.result_status_available)}
                    ${fieldItem('analysis run', authority.analysisRunId, { code: true })}
                    ${fieldItem('output ref', statusBody.output_payload_ref, { code: true })}
                    ${fieldItem('metadata readable', metadata.readable)}
                    ${fieldItem('artifact count', metadata.artifact_count)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Associated Cohort Authority</strong>
                <ul>
                    ${fieldItem('pass type', cohort.passType)}
                    ${fieldItem('pass scope', cohort.passScope)}
                    ${fieldItem('selected method', cohort.selectedMethod)}
                    ${fieldItem('requested method', cohort.requestedMethod)}
                    ${fieldItem('requested method source', cohort.requestedMethodSource)}
                    ${fieldItem('source gate', cohort.sourceGate)}
                    ${fieldItem('cohort shape', cohort.cohortShape)}
                    ${fieldItem('source dataset versions', cohort.sourceDatasetVersionIds.join(', '))}
                    ${fieldItem('output ref', cohort.outputPayloadRef, { code: true })}
                    ${fieldItem('unresolved trace', cohort.unresolvedTraceCount)}
                    ${fieldItem('cohort review ready', cohort.ready)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Review State</strong>
                <ul>
                    ${fieldItem('state', reviewState?.review_state || reviewState?.state)}
                    ${fieldItem('decision', reviewState?.operator_decision)}
                    ${fieldItem('record', reviewState?.review_record_ref, { code: true })}
                    ${fieldItem('unresolved trace', reviewState?.unresolved_trace_count)}
                    ${fieldItem('trace', summarizeTrace(traceSummary))}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function packageReviewPanelState() {
    const construction = packageConstructionState() || {};
    const submit = packageReviewSubmitState() || {};
    if (State.packageReviewSubmitPending) {
        return { label: 'package_review_submit_recording', pill: 'preview', message: 'Recording one bounded package-review decision.' };
    }
    if (State.packageConstructionPending) {
        return { label: 'package_construction_committing', pill: 'preview', message: 'Committing the three package families before package-review submit.' };
    }
    if (State.packageReviewPreviewPending) {
        return { label: 'package_review_preview_inspecting', pill: 'preview', message: 'Inspecting read-only package-review readiness.' };
    }
    if (State.packageReviewSubmit?.package_review_state || submit.submit_record_ref) {
        return { label: State.packageReviewSubmit?.package_review_state || submit.state || 'package_review_recorded', pill: 'ok', message: 'Server state already contains a package-review submit record.' };
    }
    if (State.packageReviewSubmitError || State.packageConstructionError || State.packageReviewPreviewError) {
        return { label: 'package_review_blocked', pill: 'blocked', message: 'Server authority rejected or blocked the latest package action.' };
    }
    if (submit.package_review_submit_enabled === true) {
        return { label: submit.state || 'package_review_submit_ready', pill: 'ok', message: 'Constructed packages are ready for one bounded package-review decision.' };
    }
    if (construction.state === 'package_constructed') {
        return { label: 'package_constructed', pill: 'ok', message: 'Package set is constructed; inspect preview if a current preview hash is needed before submit.' };
    }
    if (State.packageReviewPreview?.package_review_preview_enabled === true) {
        if (State.packageReviewPreview?.package_commit_enabled === false) {
            return { label: State.packageReviewPreview.next_state || 'package_review_preview_ready', pill: 'preview', message: 'Associated-cohort package-review preview is available as read-only; package construction remains deferred.' };
        }
        return { label: State.packageReviewPreview.next_state || 'package_review_preview_ready', pill: 'ok', message: 'Package-review preview is available and can be committed as a package set.' };
    }
    if (recordedApprovedResultReview() && associatedCohortReviewContext()) {
        return { label: 'package_review_preview_available', pill: 'preview', message: 'Approved associated-cohort result review can be inspected for read-only package-preview readiness.' };
    }
    if (recordedApprovedResultReview()) {
        return { label: 'package_review_preview_unavailable', pill: 'preview', message: 'Approved result review can be inspected for package-preview readiness.' };
    }
    return { label: 'package_review_preview_unavailable', pill: 'blocked', message: 'Package preview requires an approved selected-pass result review.' };
}

function renderPackageReviewPreviewPanel() {
    const preview = State.packageReviewPreview || {};
    const construction = packageConstructionState() || {};
    const submit = packageReviewSubmitState() || {};
    const panelState = packageReviewPanelState();
    const review = recordedApprovedResultReview() || {};
    const compatibility = preview.package_owner_compatibility || {};
    const candidateKinds = Array.isArray(preview.candidate_package_kinds) ? preview.candidate_package_kinds : [];
    const packageIds = packageOutputPackageIds();
    const payloadHashes = packagePayloadHashes();
    const packageKinds = packageKindsFromState();
    const candidateRows = candidateKinds.length
        ? candidateKinds.map((candidate) => `
            <li>
                <code>${escapeHtml(candidate.package_kind)}</code>
                ${candidate.preview_only ? '<span class="status-pill preview">preview</span>' : ''}
                ${candidate.package_commit_enabled ? '<span class="status-pill ok">commit ready</span>' : ''}
                ${candidate.package_commit_enabled === false ? '<span class="status-pill blocked">commit deferred</span>' : ''}
            </li>
        `).join('')
        : '<li>No package candidates loaded.</li>';
    const packageRows = packageKinds.length
        ? packageKinds.map((packageKind, index) => `
            <li>
                <code>${escapeHtml(packageKind)}</code>
                ${packageIds[index] ? `<code>${escapeHtml(packageIds[index])}</code>` : ''}
            </li>
        `).join('')
        : '<li>No package set is constructed.</li>';
    const payloadRows = payloadHashes.length
        ? payloadHashes.map((payloadHash) => `<li><code>${escapeHtml(payloadHash)}</code></li>`).join('')
        : '<li>No package payload hashes are available.</li>';
    const error = State.packageReviewSubmitError || State.packageConstructionError || State.packageReviewPreviewError;
    elements.packageReviewPreviewPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Preview Authority</strong>
                <ul>
                    ${fieldItem('session', preview.session_id || currentSessionId(), { code: true })}
                    ${fieldItem('analysis plan', preview.analysis_plan_id || selectedResultAuthority().analysisPlanId, { code: true })}
                    ${fieldItem('pass run', preview.pass_run_id || selectedResultAuthority().passRunId, { code: true })}
                    ${fieldItem('result review', preview.result_review_record_ref || review.review_record_ref, { code: true })}
                    ${fieldItem('review state', preview.result_review_state || review.review_state)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Candidate Families</strong>
                <ul>${candidateRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Package Construction</strong>
                <ul>
                    ${fieldItem('state', construction.next_state || construction.state)}
                    ${fieldItem('reconciliation', construction.reconciliation_record_id, { code: true })}
                    ${fieldItem('commit enabled', construction.package_commit_enabled)}
                    ${fieldItem('submit enabled', construction.package_review_submit_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Constructed Packages</strong>
                <ul>${packageRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Hashes</strong>
                <ul>${payloadRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Package Review Submit</strong>
                <ul>
                    ${fieldItem('state', submit.next_state || submit.package_review_state || submit.state)}
                    ${fieldItem('submit ref', submit.submit_record_ref, { code: true })}
                    ${fieldItem('operator decision', submit.operator_decision)}
                    ${fieldItem('submit enabled', submit.package_review_submit_enabled)}
                    ${fieldItem('handoff enabled', submit.handoff_enabled)}
                    ${fieldItem('export enabled', submit.export_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Owner Compatibility</strong>
                <ul>
                    ${fieldItem('status', compatibility.status)}
                    ${fieldItem('preview projection', compatibility.preview_candidate_projection_compatible)}
                    ${fieldItem('construction compatible', compatibility.construction_compatible_with_current_workbench_state)}
                    ${fieldItem('materialize callable', compatibility.materialize_package_entry_callable)}
                    ${fieldItem('missing inputs', Array.isArray(compatibility.missing_owner_service_inputs) ? compatibility.missing_owner_service_inputs.join(', ') : null)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(submit.downstream_unavailable || construction.downstream_unavailable || preview.downstream_unavailable || ['package_commit', 'package_review_submit', 'handoff', 'export'])}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function renderPackageLifecycleDashboardPanel() {
    const preview = State.packageReviewPreview || {};
    const construction = packageConstructionState() || {};
    const submit = packageReviewSubmitState() || {};
    const rows = packageLifecycleOutputRows();
    const dashboardState = packageLifecycleDashboardState(preview, construction, submit);
    const sourceGate = (
        submit.source_gate
        || construction.source_gate
        || preview.source_gate
        || submit.package_construction_source_gate
        || construction.package_construction_source_gate
    );
    const downstream = [
        'package_mutation_controls_blocked',
        'package_payload_rewrite_blocked',
        'connector_dispatch_blocked',
        'provider_public_delivery_use_blocked',
        'frontend_durable_authority_blocked',
    ];
    elements.packageLifecycleDashboardPanel.dataset.lifecycleState = dashboardState.label;
    elements.packageLifecycleDashboardPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(dashboardState.pill)}">${escapeHtml(dashboardState.label)}</span>
            <span class="rail-label">${escapeHtml(PACKAGE_LIFECYCLE_DASHBOARD_MODE)}</span>
        </div>
        <div class="result-review-grid package-lifecycle-grid">
            <section class="result-review-card">
                <strong>Lifecycle Authority</strong>
                <ul>
                    ${fieldItem('use case', PACKAGE_LIFECYCLE_USE_CASE, { code: true })}
                    ${fieldItem('response authority', PACKAGE_LIFECYCLE_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('source gate', sourceGate, { code: true })}
                    ${fieldItem('session', preview.session_id || construction.session_id || submit.session_id || currentSessionId(), { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Preview Identity</strong>
                <ul>
                    ${fieldItem('preview hash', packageReviewPreviewHash(), { code: true })}
                    ${fieldItem('result review', preview.result_review_record_ref || construction.result_review_record_ref || submit.result_review_record_ref, { code: true })}
                    ${fieldItem('preview enabled', preview.package_review_preview_enabled)}
                    ${fieldItem('commit enabled', preview.package_commit_enabled)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Package Set</strong>
                <ul>
                    ${fieldItem('construction state', construction.next_state || construction.state)}
                    ${fieldItem('reconciliation', construction.reconciliation_record_id, { code: true })}
                    ${fieldItem('basis hash', packageConstructionBasisHash(), { code: true })}
                    ${fieldItem('package count', rows.length)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Review Decision</strong>
                <ul>
                    ${fieldItem('review state', submit.package_review_state || submit.next_state || submit.state)}
                    ${fieldItem('submit ref', submit.submit_record_ref, { code: true })}
                    ${fieldItem('decision', submit.operator_decision)}
                    ${fieldItem('handoff enabled', submit.handoff_enabled)}
                    ${fieldItem('export enabled', submit.export_enabled)}
                </ul>
            </section>
            <section class="result-review-card package-lifecycle-rows">
                <strong>Package Lifecycle Rows</strong>
                <ul>${renderPackageLifecycleRows(rows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function renderAuthorityMatrixReviewPanel() {
    const contract = authorityMatrixContract();
    const panelState = authorityMatrixReviewState(contract);
    const rows = contract?.authority_matrix || [];
    const blockedScope = [
        'runtime_behavior_blocked',
        'backend_route_behavior_blocked',
        'mutation_dispatch_blocked',
        'provider_public_delivery_use_blocked',
        'raw_public_url_display_use_blocked',
        'frontend_durable_authority_blocked',
    ];
    elements.authorityMatrixReviewPanel.dataset.reviewState = panelState.label;

    if (!contract) {
        elements.authorityMatrixReviewPanel.innerHTML = `
            <div class="result-review-status">
                <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
                <span class="rail-label">${escapeHtml(AUTHORITY_MATRIX_REVIEW_RENDERED_MODE)}</span>
            </div>
            <div class="result-review-grid authority-matrix-review-grid">
                <section class="result-review-card">
                    <strong>Bootstrap Contract</strong>
                    <ul>
                        ${fieldItem('response authority', AUTHORITY_MATRIX_REVIEW_RESPONSE_AUTHORITY, { code: true })}
                        ${fieldItem('schema id', State.bootstrap?.authority_matrix_contract?.schema_id, { code: true })}
                        ${fieldItem('fail closed', 'blocked_no_runtime_authority', { code: true })}
                    </ul>
                </section>
                <section class="result-review-card">
                    <strong>Unavailable Boundary</strong>
                    <div class="downstream-locks">${renderDownstreamLocks(blockedScope)}</div>
                </section>
            </div>
        `;
        return;
    }

    elements.authorityMatrixReviewPanel.innerHTML = `
        <div class="section-heading">
            <div>
                <p class="eyebrow">Authority matrix</p>
                <h2>Rendered read-only authority review</h2>
            </div>
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
        </div>
        <div class="result-review-grid authority-matrix-review-grid">
            <section class="result-review-card">
                <strong>Review Authority</strong>
                <ul>
                    ${fieldItem('use case', AUTHORITY_MATRIX_REVIEW_USE_CASE, { code: true })}
                    ${fieldItem('rendered mode', AUTHORITY_MATRIX_REVIEW_RENDERED_MODE, { code: true })}
                    ${fieldItem('response authority', AUTHORITY_MATRIX_REVIEW_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('exposure context', contract.exposure_context, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Contract Identity</strong>
                <ul>
                    ${fieldItem('schema id', contract.schema_id, { code: true })}
                    ${fieldItem('definition id', contract.contract_definition_id, { code: true })}
                    ${fieldItem('scope', contract.scope, { code: true })}
                    ${fieldItem('fail closed', contract.fail_closed_result, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Boundaries</strong>
                <ul>
                    ${fieldItem('mutation or dispatch', false)}
                    ${fieldItem('additional matrix route', false)}
                    ${fieldItem('provider-public delivery/use', false)}
                    ${fieldItem('raw public URL display/use', false)}
                    ${fieldItem('frontend durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card authority-matrix-review-rows">
                <strong>Authority Matrix Rows</strong>
                <ul>${authorityMatrixRowCards(rows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(blockedScope)}</div>
            </section>
        </div>
    `;
}

function renderDownstreamAccessLifecycleDashboardPanel() {
    const rows = downstreamAccessLifecycleRows();
    const dashboardState = downstreamAccessLifecycleDashboardState(rows);
    const external = externalExportDownloadPrepareState() || {};
    const downstream = currentDownstreamUnavailable() || [
        'external_connector_invocation_blocked',
        'destination_write_blocked',
        'provider_public_delivery_use_blocked',
        'raw_public_url_display_use_blocked',
        'frontend_durable_authority_blocked',
    ];
    elements.downstreamAccessLifecycleDashboardPanel.dataset.lifecycleState = dashboardState.label;
    elements.downstreamAccessLifecycleDashboardPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(dashboardState.pill)}">${escapeHtml(dashboardState.label)}</span>
            <span class="rail-label">${escapeHtml(DOWNSTREAM_ACCESS_LIFECYCLE_DASHBOARD_MODE)}</span>
        </div>
        <div class="result-review-grid downstream-access-lifecycle-grid">
            <section class="result-review-card">
                <strong>Lifecycle Authority</strong>
                <ul>
                    ${fieldItem('use case', DOWNSTREAM_ACCESS_LIFECYCLE_USE_CASE, { code: true })}
                    ${fieldItem('response authority', DOWNSTREAM_ACCESS_LIFECYCLE_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('session', currentSessionId(), { code: true })}
                    ${fieldItem('source gate', external.source_gate || external.package_construction_source_gate, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Access Boundaries</strong>
                <ul>
                    ${fieldItem('connector invocation', false)}
                    ${fieldItem('destination write', false)}
                    ${fieldItem('provider public delivery/use', false)}
                    ${fieldItem('raw public URL display/use', false)}
                    ${fieldItem('browser durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card downstream-access-lifecycle-rows">
                <strong>Downstream Lifecycle Rows</strong>
                <ul>${renderDownstreamAccessLifecycleRows(rows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function renderLayer3E2EGovernanceLifecycleDashboardPanel() {
    const rows = layer3E2EGovernanceLifecycleRows();
    const dashboardState = layer3E2EGovernanceLifecycleDashboardState(rows);
    const downstream = [
        'package_mutation_blocked',
        'external_connector_invocation_blocked',
        'destination_write_blocked',
        'provider_public_delivery_use_blocked',
        'raw_public_url_display_use_blocked',
        'source_expansion_blocked',
        'rag_vector_behavior_blocked',
        'auth_security_behavior_blocked',
        'frontend_durable_authority_blocked',
    ];
    elements.layer3E2EGovernanceLifecycleDashboardPanel.dataset.lifecycleState = dashboardState.label;
    elements.layer3E2EGovernanceLifecycleDashboardPanel.innerHTML = `
        <div class="section-heading">
            <div>
                <p class="eyebrow">End-to-end governance lifecycle</p>
                <h2>Layer 3 server-authoritative lifecycle</h2>
            </div>
            <span class="status-pill ${escapeHtml(dashboardState.pill)}">${escapeHtml(dashboardState.label)}</span>
        </div>
        <div class="result-review-grid layer3-e2e-governance-lifecycle-grid">
            <section class="result-review-card">
                <strong>Lifecycle Authority</strong>
                <ul>
                    ${fieldItem('use case', LAYER3_E2E_GOVERNANCE_LIFECYCLE_USE_CASE, { code: true })}
                    ${fieldItem('rendered mode', LAYER3_E2E_GOVERNANCE_LIFECYCLE_DASHBOARD_MODE, { code: true })}
                    ${fieldItem('response authority', LAYER3_E2E_GOVERNANCE_LIFECYCLE_RESPONSE_AUTHORITY, { code: true })}
                    ${fieldItem('session', currentSessionId(), { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Blocked Boundaries</strong>
                <ul>
                    ${fieldItem('package mutation', false)}
                    ${fieldItem('connector/destination dispatch', false)}
                    ${fieldItem('provider-public delivery/use', false)}
                    ${fieldItem('raw public URL display/use', false)}
                    ${fieldItem('frontend durable authority', false)}
                </ul>
            </section>
            <section class="result-review-card layer3-e2e-governance-lifecycle-rows">
                <strong>Lifecycle Rows</strong>
                <ul>${renderLayer3E2EGovernanceLifecycleRows(rows)}</ul>
            </section>
            <section class="result-review-card">
                <strong>Deferred Capabilities</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
        </div>
    `;
}

function handoffExportPanelState() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const packageReviewState = submit.package_review_state || submit.state || handoff.package_review_state;
    if (State.handoffExportPreparePending) {
        return { label: 'handoff_export_prepare_recording', pill: 'preview', message: 'Recording one prepare-only handoff/export decision.' };
    }
    if (recordedHandoffExportPrepare()) {
        return { label: handoff.handoff_export_state || handoff.next_state || handoff.state, pill: 'ok', message: 'Server state already contains a handoff/export preparation decision.' };
    }
    if (State.handoffExportPrepareError) {
        return { label: 'handoff_export_prepare_blocked', pill: 'blocked', message: 'Server authority rejected or blocked the latest preparation action.' };
    }
    if (handoff.available === true && packageReviewState === 'package_review_approved') {
        return { label: handoff.state || 'handoff_export_ready', pill: 'ok', message: 'Approved package-review submit state is ready for prepare-only recording.' };
    }
    if (packageReviewState === 'package_review_approved') {
        return { label: handoff.state || 'handoff_export_unavailable', pill: 'blocked', message: handoff.blocked_reason || 'Preparation readiness is not available from the server summary.' };
    }
    return { label: handoff.state || 'handoff_export_unavailable', pill: 'blocked', message: 'Handoff/export preparation requires approved package-review submit state.' };
}

function renderCodeList(values, emptyText) {
    return values?.length
        ? values.map((value) => `<li><code>${escapeHtml(value)}</code></li>`).join('')
        : `<li>${escapeHtml(emptyText)}</li>`;
}

function renderHandoffExportPreparePanel() {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const authority = selectedResultAuthority();
    const panelState = handoffExportPanelState();
    const packageReviewState = submit.package_review_state || submit.state || handoff.package_review_state;
    const prepareState = handoff.handoff_export_state || handoff.next_state || handoff.state;
    const packageIds = packageOutputPackageIds();
    const packageKinds = packageKindsFromState();
    const payloadRefs = packagePayloadRefs();
    const payloadHashes = packagePayloadHashes();
    const downstream = handoff.downstream_unavailable || submit.downstream_unavailable || ['aps_handoff', 'external_export', 'downstream_dispatch'];
    const envelope = handoff.handoff_export_envelope;
    const envelopeRows = envelope && typeof envelope === 'object'
        ? [
            fieldItem('schema', envelope.schema_id),
            fieldItem('package review submit ref', envelope.package_review_submit_record_ref, { code: true }),
            fieldItem('reconciliation', envelope.reconciliation_record_id, { code: true }),
            fieldItem('package count', Array.isArray(envelope.output_package_ids) ? envelope.output_package_ids.length : null),
        ].join('')
        : '<li>No preparation envelope has been recorded.</li>';

    elements.handoffExportPreparePanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Prepare Authority</strong>
                <ul>
                    ${fieldItem('session', authority.sessionId, { code: true })}
                    ${fieldItem('analysis plan', authority.analysisPlanId, { code: true })}
                    ${fieldItem('pass run', authority.passRunId, { code: true })}
                    ${fieldItem('preview', authority.previewId, { code: true })}
                    ${fieldItem('preview hash', authority.previewHash, { code: true })}
                    ${fieldItem('analysis run', handoff.analysis_run_id || authority.analysisRunId, { code: true })}
                    ${fieldItem('pass type', handoff.pass_type || submit.pass_type || authority.passType)}
                    ${fieldItem('pass scope', handoff.pass_scope || submit.pass_scope || authority.passScope)}
                    ${fieldItem('method', handoff.method || submit.method || authority.selectedMethod)}
                    ${fieldItem('source gate', handoff.source_gate || submit.source_gate || authority.sourceGate)}
                    ${fieldItem('package source gate', handoff.package_construction_source_gate || submit.package_construction_source_gate)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Package Review Submit</strong>
                <ul>
                    ${fieldItem('state', packageReviewState)}
                    ${fieldItem('submit ref', handoff.package_review_submit_record_ref || submit.submit_record_ref, { code: true })}
                    ${fieldItem('operator decision', submit.operator_decision)}
                    ${fieldItem('result review', handoff.result_review_record_ref || submit.result_review_record_ref, { code: true })}
                    ${fieldItem('package preview hash', handoff.package_review_preview_hash || submit.package_review_preview_hash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Handoff Contract</strong>
                <ul>
                    ${fieldItem('target', handoff.handoff_target || 'internal_export_envelope')}
                    ${fieldItem('mode', handoff.export_mode || 'prepare_only')}
                    ${fieldItem('state', prepareState)}
                    ${fieldItem('prepare enabled', handoff.handoff_export_prepare_enabled)}
                    ${fieldItem('prepare ref', handoff.prepare_record_ref, { code: true })}
                    ${fieldItem('operator decision', handoff.operator_decision)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Reviewed Packages</strong>
                <ul>${renderCodeList(packageKinds.map((kind, index) => `${kind}${packageIds[index] ? ` / ${packageIds[index]}` : ''}`), 'No reviewed package identities are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Refs</strong>
                <ul>${renderCodeList(payloadRefs, 'No package payload refs are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Hashes</strong>
                <ul>${renderCodeList(payloadHashes, 'No package payload hashes are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Reference Envelope</strong>
                <ul>${envelopeRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.handoffExportPrepareError)}
        </div>
    `;
}

function apsHandoffPanelState() {
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const prepareState = handoff.handoff_export_state || handoff.next_state || handoff.state;
    const stateName = apsHandoffStateName(aps);
    if (State.apsHandoffDispatchPending) {
        return { label: 'aps_handoff_ui_dispatching', pill: 'preview', message: 'Submitting one server-side APS handoff dispatch request.' };
    }
    if (recordedApsHandoffDispatch()) {
        return { label: stateName || 'aps_handoff_dispatched', pill: 'ok', message: 'Server state already contains a recorded APS handoff dispatch.' };
    }
    if (State.apsHandoffDispatchError) {
        return { label: State.apsHandoffDispatchError.error_code || 'aps_handoff_ui_error', pill: 'blocked', message: 'Server authority rejected or blocked the latest APS dispatch action.' };
    }
    if (stateName === 'aps_handoff_conflict') {
        return { label: stateName, pill: 'blocked', message: aps.blocked_reason || 'Existing APS handoff state conflicts with this workbench session.' };
    }
    if (stateName === 'aps_handoff_blocked') {
        return { label: stateName, pill: 'blocked', message: aps.blocked_reason || 'APS owner-service compatibility is blocked.' };
    }
    if (aps.available === true && stateName === 'aps_handoff_ready') {
        return { label: stateName, pill: 'ok', message: 'Prepared envelope authority is ready for server-side APS handoff dispatch.' };
    }
    if (prepareState === 'handoff_export_prepared') {
        return { label: stateName || 'aps_handoff_unavailable', pill: 'blocked', message: aps.blocked_reason || 'APS dispatch readiness is not available from the server summary.' };
    }
    return { label: stateName || 'aps_handoff_unavailable', pill: 'blocked', message: 'APS dispatch requires a recorded handoff_export_prepared envelope.' };
}

function renderApsHandoffDispatchPanel() {
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const authority = selectedResultAuthority();
    const panelState = apsHandoffPanelState();
    const packageReviewState = submit.package_review_state || submit.state || handoff.package_review_state;
    const packageKinds = packageKindsFromState();
    const packageIds = packageOutputPackageIds();
    const payloadRefs = packagePayloadRefs();
    const payloadHashes = packagePayloadHashes();
    const downstream = aps.downstream_unavailable || ['external_export', 'download', 'connector_dispatch', 'non_aps_dispatch'];

    elements.apsHandoffDispatchPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Dispatch Authority</strong>
                <ul>
                    ${fieldItem('session', authority.sessionId, { code: true })}
                    ${fieldItem('analysis plan', authority.analysisPlanId, { code: true })}
                    ${fieldItem('pass run', authority.passRunId, { code: true })}
                    ${fieldItem('preview', authority.previewId, { code: true })}
                    ${fieldItem('preview hash', authority.previewHash, { code: true })}
                    ${fieldItem('analysis run', handoff.analysis_run_id || authority.analysisRunId, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Prepared Envelope</strong>
                <ul>
                    ${fieldItem('package review state', packageReviewState)}
                    ${fieldItem('submit ref', handoff.package_review_submit_record_ref || submit.submit_record_ref, { code: true })}
                    ${fieldItem('prepare state', handoff.handoff_export_state || handoff.next_state || handoff.state)}
                    ${fieldItem('prepare ref', aps.prepare_record_ref || handoff.prepare_record_ref, { code: true })}
                    ${fieldItem('envelope ref', aps.handoff_export_envelope_ref || handoffExportEnvelopeRef(handoff), { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>APS Dispatch Contract</strong>
                <ul>
                    ${fieldItem('target', aps.aps_handoff_target || 'aps_evidence_bundle')}
                    ${fieldItem('mode', aps.dispatch_mode || 'server_side_aps_handoff')}
                    ${fieldItem('decision', aps.operator_decision || 'dispatch_aps_handoff')}
                    ${fieldItem('state', apsHandoffStateName(aps))}
                    ${fieldItem('record ref', aps.aps_handoff_record_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Source Packages</strong>
                <ul>${renderCodeList(packageKinds.map((kind, index) => `${kind}${packageIds[index] ? ` / ${packageIds[index]}` : ''}`), 'No reviewed package identities are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Refs</strong>
                <ul>${renderCodeList(payloadRefs, 'No source payload refs are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Hashes</strong>
                <ul>${renderCodeList(payloadHashes, 'No source payload hashes are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>APS Output</strong>
                <ul>
                    ${fieldItem('package id', aps.aps_output_package_id, { code: true })}
                    ${fieldItem('package kind', aps.aps_output_package_kind)}
                    ${fieldItem('bundle ref', aps.aps_bundle_ref, { code: true })}
                    ${fieldItem('bundle id', aps.aps_bundle_id, { code: true })}
                    ${fieldItem('schema', aps.aps_schema_id)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.apsHandoffDispatchError)}
        </div>
    `;
}

function externalExportDownloadPanelState() {
    const external = externalExportDownloadPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const stateName = externalExportDownloadStateName(external);
    const apsState = external.aps_handoff_state || apsHandoffStateName(aps);
    if (State.externalExportDownloadPreparePending) {
        return { label: 'external_export_download_ui_preparing', pill: 'preview', message: 'Submitting one reference-only readiness request.' };
    }
    if (recordedExternalExportDownloadPrepare()) {
        return { label: stateName || 'external_export_download_prepared', pill: 'ok', message: 'Server state already contains recorded external export/download readiness.' };
    }
    if (State.externalExportDownloadPrepareError) {
        return { label: State.externalExportDownloadPrepareError.error_code || 'external_export_download_ui_error', pill: 'blocked', message: 'Server authority rejected or blocked the latest readiness action.' };
    }
    if (stateName === 'external_export_download_conflict') {
        return { label: stateName, pill: 'blocked', message: external.blocked_reason || 'Existing external export/download readiness conflicts with this workbench session.' };
    }
    if (stateName === 'external_export_download_blocked') {
        return { label: stateName, pill: 'blocked', message: external.blocked_reason || 'External export/download readiness is blocked by server authority.' };
    }
    if (external.available === true && stateName === 'external_export_download_ready') {
        return { label: stateName, pill: 'ok', message: 'Recorded APS handoff dispatch is ready for reference-only external export/download readiness.' };
    }
    if (apsState === 'aps_handoff_dispatched') {
        return { label: stateName || 'external_export_download_unavailable', pill: 'blocked', message: external.blocked_reason || 'External export/download readiness is not available from the server summary.' };
    }
    return { label: stateName || 'external_export_download_unavailable', pill: 'blocked', message: 'External export/download readiness requires recorded APS handoff dispatch.' };
}

function renderExternalExportDownloadPreparePanel() {
    const external = externalExportDownloadPrepareState() || {};
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const authority = selectedResultAuthority();
    const panelState = externalExportDownloadPanelState();
    const packageReviewState = external.package_review_state || submit.package_review_state || submit.state || handoff.package_review_state;
    const prepareState = external.handoff_export_state || handoff.handoff_export_state || handoff.next_state || handoff.state;
    const apsState = external.aps_handoff_state || apsHandoffStateName(aps);
    const packageKinds = Array.isArray(external.package_kinds) && external.package_kinds.length ? external.package_kinds : packageKindsFromState();
    const packageIds = Array.isArray(external.output_package_ids) && external.output_package_ids.length ? external.output_package_ids : packageOutputPackageIds();
    const payloadRefs = Array.isArray(external.payload_refs) && external.payload_refs.length ? external.payload_refs : packagePayloadRefs();
    const payloadHashes = Array.isArray(external.payload_hashes) && external.payload_hashes.length ? external.payload_hashes : packagePayloadHashes();
    const downstream = external.downstream_unavailable || [
        'browser_download',
        'download_url',
        'connector_dispatch',
        'destination_selection',
        'generic_downstream_dispatch',
    ];
    const descriptor = external.external_export_download_descriptor;
    const descriptorRows = descriptor && typeof descriptor === 'object'
        ? [
            fieldItem('descriptor ref', descriptor.descriptor_ref, { code: true }),
            fieldItem('source artifact', descriptor.source_artifact_ref, { code: true }),
            fieldItem('target', descriptor.export_download_target),
            fieldItem('mode', descriptor.download_mode),
            fieldItem('browser download enabled', descriptor.browser_download_enabled),
            fieldItem('download URL enabled', descriptor.download_url_enabled),
        ].join('')
        : '<li>No readiness descriptor has been recorded.</li>';

    elements.externalExportDownloadPreparePanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Readiness Authority</strong>
                <ul>
                    ${fieldItem('session', authority.sessionId, { code: true })}
                    ${fieldItem('analysis plan', authority.analysisPlanId, { code: true })}
                    ${fieldItem('pass run', authority.passRunId, { code: true })}
                    ${fieldItem('preview', authority.previewId, { code: true })}
                    ${fieldItem('preview hash', authority.previewHash, { code: true })}
                    ${fieldItem('result review', external.result_review_record_ref || handoff.result_review_record_ref || submit.result_review_record_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Upstream State</strong>
                <ul>
                    ${fieldItem('package review state', packageReviewState)}
                    ${fieldItem('submit ref', external.package_review_submit_record_ref || handoff.package_review_submit_record_ref || submit.submit_record_ref, { code: true })}
                    ${fieldItem('prepare state', prepareState)}
                    ${fieldItem('prepare ref', external.prepare_record_ref || handoff.prepare_record_ref, { code: true })}
                    ${fieldItem('APS state', apsState)}
                    ${fieldItem('APS record ref', external.aps_handoff_record_ref || aps.aps_handoff_record_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Readiness Contract</strong>
                <ul>
                    ${fieldItem('target', external.export_download_target || 'aps_evidence_bundle_download_reference')}
                    ${fieldItem('mode', external.download_mode || 'reference_only_prepare')}
                    ${fieldItem('decision', external.operator_decision || 'prepare_external_export_download')}
                    ${fieldItem('state', externalExportDownloadStateName(external))}
                    ${fieldItem('prepare enabled', external.external_export_download_prepare_enabled)}
                    ${fieldItem('readiness ref', external.external_export_download_record_ref, { code: true })}
                    ${fieldItem('descriptor ref', external.export_download_descriptor_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Source APS Bundle</strong>
                <ul>
                    ${fieldItem('package id', external.aps_output_package_id || aps.aps_output_package_id, { code: true })}
                    ${fieldItem('package kind', external.aps_output_package_kind || aps.aps_output_package_kind)}
                    ${fieldItem('bundle ref', external.aps_bundle_ref || aps.aps_bundle_ref, { code: true })}
                    ${fieldItem('bundle id', external.aps_bundle_id || aps.aps_bundle_id, { code: true })}
                    ${fieldItem('schema', external.aps_schema_id || aps.aps_schema_id)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Source Artifact</strong>
                <ul>
                    ${fieldItem('artifact ref', external.source_artifact_ref || external.aps_bundle_ref || aps.aps_bundle_ref, { code: true })}
                    ${fieldItem('artifact schema', external.source_artifact_schema_id)}
                    ${fieldItem('artifact hash', external.source_artifact_hash, { code: true })}
                    ${fieldItem('artifact size bytes', external.source_artifact_size_bytes)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Reviewed Packages</strong>
                <ul>${renderCodeList(packageKinds.map((kind, index) => `${kind}${packageIds[index] ? ` / ${packageIds[index]}` : ''}`), 'No reviewed package identities are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Refs</strong>
                <ul>${renderCodeList(payloadRefs, 'No source payload refs are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Payload Hashes</strong>
                <ul>${renderCodeList(payloadHashes, 'No source payload hashes are available.')}</ul>
            </section>
            <section class="result-review-card">
                <strong>Readiness Descriptor</strong>
                <ul>${descriptorRows}</ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.externalExportDownloadPrepareError)}
        </div>
    `;
}

function externalExportDownloadDeliveryPanelState() {
    const external = externalExportDownloadPrepareState() || {};
    const stateName = externalExportDownloadStateName(external);
    const associatedCohort = isAssociatedCohortExternalExportDownloadState(external);
    const sourceIntake = isSourceIntakeExternalExportDownloadState(external);
    const deliveryUi = sourceIntakeDeliveryUiState(external)
        || qualitativeApsDeliveryUiState(external)
        || associatedCohortDeliveryUiState(external)
        || serverExternalExportDownloadDeliveryUiState(external);
    if (State.externalExportDownloadDeliveryPending) {
        return { label: 'external_export_download_delivery_ui_downloading', pill: 'preview', message: 'Submitting one same-origin attachment request for browser-managed download.' };
    }
    if (externalExportDownloadDeliveryStateName() === 'external_export_download_delivery_submitted') {
        return { label: 'external_export_download_delivery_submitted', pill: 'preview', message: 'The same-origin delivery request was submitted; final download handling is browser-managed.' };
    }
    if (recordedExternalExportDownloadDelivery()) {
        return { label: State.externalExportDownloadDelivery.state || 'external_export_download_delivered', pill: 'ok', message: 'The browser received the same-origin delivery request; download handling is browser-managed.' };
    }
    if (State.externalExportDownloadDeliveryError) {
        const errorCode = State.externalExportDownloadDeliveryError.error_code || 'external_export_download_delivery_ui_error';
        const isConflict = State.externalExportDownloadDeliveryError.status === 'conflict' || errorCode.includes('conflict') || errorCode.includes('mismatch');
        return { label: errorCode, pill: 'blocked', message: isConflict ? 'Server authority rejected the delivery request as stale or conflicting.' : 'Server authority rejected or blocked the delivery request.' };
    }
    if (stateName === 'external_export_download_prepared' && canSubmitExternalExportDownloadDelivery()) {
        return { label: 'external_export_download_delivery_ui_ready', pill: 'ok', message: 'Recorded readiness can be delivered as a same-origin attachment.' };
    }
    if (stateName === 'external_export_download_prepared' && sourceIntake && deliveryUi?.available !== true) {
        return { label: deliveryUi?.state || 'source_intake_external_export_download_delivery_ui_blocked', pill: 'blocked', message: 'Source-intake delivery requires complete server prepare authority before the rendered control can submit.' };
    }
    if (stateName === 'external_export_download_prepared' && associatedCohort && deliveryUi?.available !== true) {
        return { label: deliveryUi?.state || 'associated_cohort_external_export_download_delivery_ui_unavailable', pill: 'blocked', message: 'Associated-cohort delivery requires explicit server UI authority before the rendered control can submit.' };
    }
    if (stateName === 'external_export_download_prepared') {
        return { label: 'external_export_download_delivery_ui_unavailable', pill: 'blocked', message: 'Recorded readiness is present, but the server summary is missing required delivery basis.' };
    }
    return { label: 'external_export_download_delivery_ui_unavailable', pill: 'blocked', message: 'Prepare external export/download readiness before delivery.' };
}

function renderExternalExportDownloadDeliveryPanel() {
    const external = externalExportDownloadPrepareState() || {};
    const panelState = externalExportDownloadDeliveryPanelState();
    const deliveryUi = sourceIntakeDeliveryUiState(external)
        || qualitativeApsDeliveryUiState(external)
        || associatedCohortDeliveryUiState(external)
        || serverExternalExportDownloadDeliveryUiState(external)
        || {};
    const downstream = [
        'public_url',
        'signed_url',
        'connector_dispatch',
        'destination_selection',
        'generic_downstream_dispatch',
    ];
    const delivery = State.externalExportDownloadDelivery || {};
    const descriptor = external.external_export_download_descriptor || {};
    elements.externalExportDownloadDeliveryPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Delivery Gate</strong>
                <ul>
                    ${fieldItem('readiness state', externalExportDownloadStateName(external))}
                    ${fieldItem('readiness ref', external.external_export_download_record_ref, { code: true })}
                    ${fieldItem('descriptor ref', external.export_download_descriptor_ref || descriptor.descriptor_ref, { code: true })}
                    ${fieldItem('target', external.export_download_target || descriptor.export_download_target || 'aps_evidence_bundle_download_reference')}
                    ${fieldItem('download mode', external.download_mode || descriptor.download_mode || 'reference_only_prepare')}
                    ${fieldItem('delivery mode', 'same_origin_artifact_stream')}
                    ${fieldItem('decision', 'deliver_external_export_download')}
                    ${fieldItem('server UI state', deliveryUi.state)}
                    ${fieldItem('server UI available', deliveryUi.available)}
                    ${fieldItem('server UI basis', deliveryUi.server_authority)}
                    ${fieldItem('source-intake record', external.source_intake_record_id, { code: true })}
                    ${fieldItem('source-intake candidate', external.candidate_id, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Authority Basis</strong>
                <ul>
                    ${fieldItem('package review state', external.package_review_state)}
                    ${fieldItem('handoff state', external.handoff_export_state)}
                    ${fieldItem('APS state', external.aps_handoff_state)}
                    ${fieldItem('submit ref', external.package_review_submit_record_ref, { code: true })}
                    ${fieldItem('prepare ref', external.prepare_record_ref, { code: true })}
                    ${fieldItem('APS record ref', external.aps_handoff_record_ref, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Source Artifact</strong>
                <ul>
                    ${fieldItem('artifact ref', external.source_artifact_ref || external.aps_bundle_ref, { code: true })}
                    ${fieldItem('artifact schema', external.source_artifact_schema_id || external.aps_schema_id)}
                    ${fieldItem('artifact hash', external.source_artifact_hash, { code: true })}
                    ${fieldItem('artifact size bytes', external.source_artifact_size_bytes)}
                    ${fieldItem('safe filename', delivery.filename)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Completed Attempt</strong>
                <ul>
                    ${fieldItem('state', delivery.state)}
                    ${fieldItem('schema', delivery.schemaId)}
                    ${fieldItem('record ref', delivery.externalExportDownloadRecordRef, { code: true })}
                    ${fieldItem('source hash', delivery.sourceArtifactHash, { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Disabled Downstream</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.externalExportDownloadDeliveryError)}
        </div>
    `;
}

function externalExportDownloadSignedReferencePanelState() {
    const external = externalExportDownloadPrepareState() || {};
    const stateName = externalExportDownloadStateName(external);
    if (State.externalExportDownloadSignedReferenceUsePending) {
        return { label: 'external_export_download_signed_reference_using', pill: 'preview', message: 'Using one server-generated same-origin signed reference.' };
    }
    if (State.externalExportDownloadSignedReferenceUse) {
        return { label: State.externalExportDownloadSignedReferenceUse.state || 'external_export_download_signed_reference_delivered', pill: 'ok', message: 'The signed reference was accepted and used through the same-origin endpoint.' };
    }
    if (State.externalExportDownloadSignedReferencePending) {
        return { label: 'external_export_download_signed_reference_generating', pill: 'preview', message: 'Requesting one short-lived server-owned signed reference.' };
    }
    if (State.externalExportDownloadSignedReferenceError) {
        return {
            label: State.externalExportDownloadSignedReferenceError.error_code || 'external_export_download_signed_reference_ui_error',
            pill: 'blocked',
            message: 'Server authority rejected or blocked the signed-reference request.',
        };
    }
    if (State.externalExportDownloadSignedReference?.signed_reference_state === 'external_export_download_signed_reference_ready') {
        return { label: 'external_export_download_signed_reference_ready', pill: 'ok', message: 'A short-lived same-origin signed reference is ready for use.' };
    }
    if (stateName === 'external_export_download_prepared' && externalExportDownloadDeliveryUiAdmitted()) {
        return { label: 'external_export_download_signed_reference_ui_ready', pill: 'ok', message: 'Recorded readiness and explicit delivery UI authority can generate a same-origin signed reference.' };
    }
    if (stateName === 'external_export_download_prepared') {
        return { label: 'external_export_download_signed_reference_ui_blocked', pill: 'blocked', message: 'Signed-reference controls require the same server delivery UI authority used by same-origin delivery.' };
    }
    return { label: 'external_export_download_signed_reference_ui_unavailable', pill: 'blocked', message: 'Prepare external export/download readiness before signed-reference generation.' };
}

function renderExternalExportDownloadSignedReferencePanel() {
    const external = externalExportDownloadPrepareState() || {};
    const signed = State.externalExportDownloadSignedReference || {};
    const used = State.externalExportDownloadSignedReferenceUse || {};
    const panelState = externalExportDownloadSignedReferencePanelState();
    const downstream = [
        'public_url',
        'provider_signed_url',
        'connector_dispatch',
        'destination_selection',
        'durable_token_state',
        'receipt_audit_revocation_state',
    ];
    elements.externalExportDownloadSignedReferencePanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            <section class="result-review-card">
                <strong>Signed Reference Gate</strong>
                <ul>
                    ${fieldItem('readiness state', externalExportDownloadStateName(external))}
                    ${fieldItem('readiness ref', external.external_export_download_record_ref, { code: true })}
                    ${fieldItem('descriptor ref', external.export_download_descriptor_ref, { code: true })}
                    ${fieldItem('delivery UI admitted', externalExportDownloadDeliveryUiAdmitted(external))}
                    ${fieldItem('delivery mode', 'same_origin_signed_delivery_reference')}
                    ${fieldItem('server authority', signed.server_authority || 'associated_cohort_external_export_download_signed_reference_gate')}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Generated Reference</strong>
                <ul>
                    ${fieldItem('state', signed.signed_reference_state)}
                    ${fieldItem('expires at', signed.signed_reference_expires_at)}
                    ${fieldItem('expires in seconds', signed.signed_reference_expires_in_seconds)}
                    ${fieldItem('use endpoint', signed.signed_reference_use_endpoint, { code: true })}
                    ${fieldItem('token prefix', signed.signed_reference_token ? `${String(signed.signed_reference_token).slice(0, 18)}...` : 'none', { code: true })}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Artifact Basis</strong>
                <ul>
                    ${fieldItem('artifact ref', signed.source_artifact_ref || external.source_artifact_ref || external.aps_bundle_ref, { code: true })}
                    ${fieldItem('artifact hash', signed.source_artifact_hash || external.source_artifact_hash, { code: true })}
                    ${fieldItem('artifact size bytes', signed.source_artifact_size_bytes || external.source_artifact_size_bytes)}
                    ${fieldItem('pass type', signed.pass_type || external.pass_type)}
                    ${fieldItem('method', signed.method || external.method)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Use Result</strong>
                <ul>
                    ${fieldItem('state', used.state)}
                    ${fieldItem('schema', used.schemaId)}
                    ${fieldItem('source hash', used.sourceArtifactHash, { code: true })}
                    ${fieldItem('expires at', used.expiresAt)}
                    ${fieldItem('content type', used.contentType)}
                </ul>
            </section>
            <section class="result-review-card">
                <strong>Still Disabled</strong>
                <div class="downstream-locks">${renderDownstreamLocks(downstream)}</div>
            </section>
            ${renderErrorCard(State.externalExportDownloadSignedReferenceError)}
        </div>
    `;
}

function setBusy(button, busy, label) {
    button.disabled = busy;
    if (label) {
        button.textContent = busy ? 'Working...' : label;
    }
}

function setCurrentStepChip(selectedChip) {
    elements.stepChips.forEach((chip) => {
        const selected = chip === selectedChip;
        chip.classList.toggle('current', selected);
        if (selected) {
            chip.setAttribute('aria-current', 'step');
        } else {
            chip.removeAttribute('aria-current');
        }
    });
}

function navigateToStep(chip) {
    const targetId = chip.dataset.stepTarget;
    const target = targetId ? document.getElementById(targetId) : null;
    if (!target) return;
    setCurrentStepChip(chip);
    if (target.closest('.operations-dock')) {
        const operationPanel = target.closest('.workband');
        const operationId = OPERATION_DOCK_STEPS.some((step) => step.id === operationPanel?.id)
            ? operationPanel.id
            : targetId;
        setActiveOperation(operationId, { manual: true });
    }
    target.scrollIntoView({ block: 'start', behavior: 'auto' });
    if (typeof target.focus === 'function') {
        target.focus({ preventScroll: true });
    }
}

function setStepChip(element, active) {
    if (!element) return;
    element.disabled = false;
    element.classList.toggle('active', active);
    element.classList.toggle('unavailable', !active);
    element.dataset.available = active ? 'true' : 'false';
}

function operationDockStatus(step) {
    const sessionReady = Boolean(State.gateB?.session_id || currentSessionId());
    const gateCReady = Boolean(State.gateC?.typing_records?.length || sessionSublayerState().typing_records?.length);
    const authority = selectedResultAuthority();
    switch (step.key) {
    case 'intent':
        return State.preflight
            ? { state: 'live', label: 'preflight passed', detail: 'Intent and source posture are loaded.' }
            : { state: 'ready', label: 'ready', detail: 'Run preflight to load source and material previews.' };
    case 'source_intake':
        return { state: 'ready', label: 'ready', detail: 'Upload, inventory, and preview use existing server-authoritative source-intake APIs.' };
    case 'gate_b':
        if (sessionReady) return { state: 'live', label: 'session scoped', detail: 'Gate B has a session-scoped material boundary.' };
        if ((State.materialPreview?.material_candidates || []).length) return { state: 'ready', label: 'review ready', detail: 'Material preview is loaded and ready for Gate B decisions.' };
        return { state: 'blocked', label: 'waiting', detail: 'Run preflight before Gate B review.' };
    case 'gate_c':
        if (gateCReady) return { state: 'live', label: 'typing loaded', detail: 'Gate C typing is available for modality grouping.' };
        if (sessionReady) return { state: 'ready', label: 'preview ready', detail: 'Gate B is committed; Gate C preview can classify material.' };
        return { state: 'blocked', label: 'blocked', detail: 'Commit Gate B before Gate C typing.' };
    case 'plan':
        if (State.planApproval) return { state: 'live', label: 'approved', detail: 'Plan approval state is recorded.' };
        if (State.planPreview) return { state: 'live', label: 'preview loaded', detail: 'Plan preview state is loaded.' };
        if (canPlanPreview()) return { state: 'ready', label: 'preview ready', detail: 'Gate C typing allows plan preview.' };
        return { state: 'blocked', label: 'blocked', detail: 'Commit Gate C typing before plan preview.' };
    case 'results':
        if (recordedResultReview()) return { state: 'live', label: 'review recorded', detail: 'Selected-pass result review is recorded.' };
        if (State.resultStatus?.result_status_available === true) return { state: 'ready', label: 'status ready', detail: 'Selected-pass result status can be reviewed.' };
        if (authority.selected) return { state: 'ready', label: 'selected pass', detail: 'A selected pass exists; inspect terminal result status when available.' };
        return { state: 'blocked', label: 'blocked', detail: 'Execution/result authority is not available in the current session.' };
    case 'package':
        if (packageReviewSubmitState()?.package_review_state || packageReviewSubmitState()?.state) return { state: 'live', label: 'package state', detail: 'Package review state is recorded.' };
        if (canInspectPackageReviewPreview() || canCommitPackageConstruction() || canSubmitPackageReview()) return { state: 'ready', label: 'package ready', detail: 'Package preview, construction, or review controls are available.' };
        return { state: 'blocked', label: 'blocked', detail: 'Approve selected-pass result review before package review.' };
    case 'handoff':
        if (recordedHandoffExportPrepare()) return { state: 'live', label: 'prepared', detail: 'Internal handoff/export preparation is recorded.' };
        if (State.sessionSummary?.handoff_export_prepare?.available === true) return { state: 'ready', label: 'prepare ready', detail: 'Package review approval can be prepared for handoff/export.' };
        return { state: 'blocked', label: 'blocked', detail: 'Approve package review before handoff/export preparation.' };
    case 'aps':
        if (recordedApsHandoffDispatch()) return { state: 'live', label: 'dispatched', detail: 'APS handoff dispatch is recorded.' };
        if (apsHandoffDispatchState()?.available === true) return { state: 'ready', label: 'dispatch ready', detail: 'Prepared handoff/export can dispatch the APS evidence bundle.' };
        return { state: 'blocked', label: 'blocked', detail: 'Prepare handoff/export before APS dispatch.' };
    case 'external':
        if (recordedExternalExportDownloadDelivery()) return { state: 'live', label: 'delivered', detail: 'Same-origin delivery has been requested.' };
        if (recordedExternalExportDownloadPrepare()) return { state: 'ready', label: 'delivery ready', detail: 'External export/download readiness can be delivered.' };
        if (State.sessionSummary?.external_export_download?.available === true) return { state: 'ready', label: 'prepare ready', detail: 'APS dispatch can prepare external export/download readiness.' };
        return { state: 'blocked', label: 'blocked', detail: 'Dispatch APS handoff before external export/download readiness.' };
    default:
        return { state: 'blocked', label: 'unknown', detail: 'Operation state is not reported.' };
    }
}

function renderOperationDockSummary(activeStep, status) {
    if (!elements.operationsDockSummary || !activeStep || !status) return;
    const activeIndex = OPERATION_DOCK_STEPS.findIndex((step) => step.id === activeStep.id);
    const positionLabel = activeIndex >= 0
        ? `${activeIndex + 1} of ${OPERATION_DOCK_STEPS.length}`
        : 'operation';
    const stateLabel = status.state === 'live'
        ? 'Live-backed'
        : status.state === 'ready'
            ? 'Action-ready'
            : 'Unavailable';
    elements.operationsDockSummary.dataset.operationState = status.state;
    elements.operationsDockSummary.dataset.canvasTarget = activeStep.canvasTarget || '';
    elements.operationsDockSummary.innerHTML = `
        <div class="operation-summary-eyebrow">
            <span>${escapeHtml(positionLabel)}</span>
            <span>${escapeHtml(activeStep.canvasLink || 'Layer 3 operation')}</span>
        </div>
        <div class="operation-summary-main">
            <h3>${escapeHtml(activeStep.label)}</h3>
            <span class="operation-summary-state">${escapeHtml(stateLabel)}: ${escapeHtml(status.label)}</span>
        </div>
        <div class="operation-summary-canvas-role">
            <span>Canvas role</span>
            <strong>${escapeHtml(activeStep.canvasRole || activeStep.canvasLink || 'Layer 3 canvas')}</strong>
        </div>
        <p>${escapeHtml(status.detail)}</p>
    `;
}

function renderOperationsDock() {
    if (!elements.operationsDock || !elements.operationsDockNav) return;
    const availableSteps = OPERATION_DOCK_STEPS.filter((step) => document.getElementById(step.id));
    if (!availableSteps.some((step) => step.id === State.activeOperationId)) {
        State.activeOperationId = availableSteps[0]?.id || '';
        State.operationDockManual = false;
    }
    if (!State.operationDockManual) {
        const suggestedStep = [...availableSteps]
            .reverse()
            .find((step) => step.key !== 'source_intake' && operationDockStatus(step).state !== 'blocked');
        if (suggestedStep) State.activeOperationId = suggestedStep.id;
    }
    elements.operationsDock.dataset.activeOperation = State.activeOperationId;
    const activeStep = availableSteps.find((step) => step.id === State.activeOperationId);
    const activeStatus = activeStep ? operationDockStatus(activeStep) : null;
    if (elements.sublayerMapPanel) {
        elements.sublayerMapPanel.dataset.activeOperationCanvas = activeStep?.canvasTarget || '3a';
        elements.sublayerMapPanel.dataset.activeOperationKey = activeStep?.key || 'intent';
    }
    renderOperationDockSummary(activeStep, activeStatus);
    elements.operationsDockNav.innerHTML = availableSteps.map((step, index) => {
        const status = operationDockStatus(step);
        const selected = step.id === State.activeOperationId;
        return `
            <button class="operation-dock-tab ${selected ? 'active' : ''}" type="button" role="tab"
                id="operation-tab-${escapeHtml(step.key)}"
                aria-controls="${escapeHtml(step.id)}"
                aria-selected="${selected ? 'true' : 'false'}"
                tabindex="${selected ? '0' : '-1'}"
                data-operation-target="${escapeHtml(step.id)}"
                data-operation-state="${escapeHtml(status.state)}"
                data-operation-index="${index}">
                <span class="operation-dock-tab-label">${escapeHtml(step.shortLabel)}</span>
                <span class="operation-dock-tab-state">${escapeHtml(status.label)}</span>
                <span class="operation-dock-tab-detail">${escapeHtml(status.detail)}</span>
            </button>
        `;
    }).join('');
    availableSteps.forEach((step) => {
        const panel = document.getElementById(step.id);
        const status = operationDockStatus(step);
        const selected = step.id === State.activeOperationId;
        panel.classList.toggle('operation-panel-active', selected);
        panel.classList.toggle('operation-panel-inactive', !selected);
        panel.dataset.operationState = status.state;
        panel.dataset.operationActive = selected ? 'true' : 'false';
        panel.setAttribute('role', 'tabpanel');
        panel.setAttribute('aria-labelledby', `operation-tab-${step.key}`);
    });
    Array.from(elements.operationsDockNav.querySelectorAll('.operation-dock-tab')).forEach((button) => {
        button.addEventListener('click', () => setActiveOperation(button.dataset.operationTarget, { focusPanel: true, manual: true }));
        button.addEventListener('keydown', handleOperationDockKeydown);
    });
}

function setActiveOperation(operationId, { focusPanel = false, focusButton = false, manual = false } = {}) {
    if (manual) State.operationDockManual = true;
    if (!operationId || State.activeOperationId === operationId) {
        if (focusPanel) document.getElementById(operationId)?.focus({ preventScroll: true });
        return;
    }
    State.activeOperationId = operationId;
    renderOperationsDock();
    const panel = document.getElementById(operationId);
    const button = elements.operationsDockNav?.querySelector(`[data-operation-target="${CSS.escape(operationId)}"]`);
    if (focusButton && button) button.focus();
    if (focusPanel && panel) {
        panel.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'auto' });
        panel.focus({ preventScroll: true });
    }
}

function handleOperationDockKeydown(event) {
    const keys = ['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'];
    if (!keys.includes(event.key)) return;
    const buttons = Array.from(elements.operationsDockNav?.querySelectorAll('.operation-dock-tab') || []);
    const currentIndex = buttons.indexOf(event.currentTarget);
    if (currentIndex < 0) return;
    event.preventDefault();
    let nextIndex = currentIndex;
    if (event.key === 'Home') {
        nextIndex = 0;
    } else if (event.key === 'End') {
        nextIndex = buttons.length - 1;
    } else {
        const delta = event.key === 'ArrowRight' || event.key === 'ArrowDown' ? 1 : -1;
        nextIndex = (currentIndex + delta + buttons.length) % buttons.length;
    }
    setActiveOperation(buttons[nextIndex].dataset.operationTarget, { focusButton: true, manual: true });
}

function providerPrivateSignedUrlPanelState() {
    if (State.providerPrivateSignedUrlError) {
        return { label: State.providerPrivateSignedUrlError.error_code || 'provider_private_signed_url_blocked', pill: 'blocked', message: State.providerPrivateSignedUrlError.message || 'Provider-private signed URL control is blocked.' };
    }
    const stateName = providerPrivateSignedUrlLatestState();
    if (stateName === 'provider_private_signed_url_revoked') {
        return { label: stateName, pill: 'ready', message: 'Provider-private signed URL receipt has been revoked; a replacement can be prepared.' };
    }
    if (stateName === 'provider_private_signed_url_expired') {
        return { label: stateName, pill: 'ready', message: 'Provider-private signed URL receipt has expired; a replacement can be prepared.' };
    }
    if (stateName === 'provider_private_signed_url_prepared') {
        return { label: stateName, pill: 'ready', message: 'Provider-private signed URL receipt is prepared; use remains closed for this lane.' };
    }
    if (recordedExternalExportDownloadPrepare() && externalExportDownloadDeliveryUiAdmitted()) {
        return { label: 'provider_private_signed_url_ui_ready', pill: 'ready', message: 'Ready to prepare a redacted provider-private signed URL receipt.' };
    }
    return { label: 'provider_private_signed_url_ui_unavailable', pill: 'blocked', message: 'Prepare external export/download readiness before provider-private signed URL controls.' };
}

function providerPrivateSignedUrlDisplayValue(value) {
    if (Array.isArray(value)) return value.length ? value.join(', ') : 'none';
    if (value === true) return 'true';
    if (value === false) return 'false';
    return value ?? 'none';
}

function renderProviderPrivateSignedUrlPanel() {
    const provider = State.providerPrivateSignedUrlRevoke || State.providerPrivateSignedUrlStatus || State.providerPrivateSignedUrlPrepare || {};
    const panelState = providerPrivateSignedUrlPanelState();
    const audit = provider.audit_receipt || {};
    const rows = {
        receipt_id: provider.provider_signed_url_receipt_id,
        provider_private_state: provider.provider_signed_url_state,
        delivery_mode: provider.delivery_mode,
        provider_url_redacted: provider.provider_url_redacted,
        expires_at: provider.provider_url_expires_at,
        replay_policy: provider.provider_url_replay_policy,
        use_count: provider.provider_url_use_count,
        max_use_count: provider.provider_url_max_use_count,
        revoked: provider.provider_url_revoked,
        source_artifact_hash: provider.source_artifact_hash,
        source_artifact_size_bytes: provider.source_artifact_size_bytes,
        audit_receipt_id: audit.audit_event_id || audit.provider_private_signed_url_audit_event_id,
        audit_reason_code: audit.reason_code,
        next_allowed_actions: provider.next_allowed_actions,
        use_route: 'closed_not_implemented',
    };
    elements.providerPrivateSignedUrlPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            ${Object.entries(rows).map(([label, value]) => `
                <section class="result-review-card">
                    <strong>${escapeHtml(label.replace(/_/g, ' '))}</strong>
                    <p>${escapeHtml(providerPrivateSignedUrlDisplayValue(value))}</p>
                </section>
            `).join('')}
        </div>
    `;
    elements.providerPrivateSignedUrlPrepare.disabled = !canPrepareProviderPrivateSignedUrl();
    elements.providerPrivateSignedUrlStatus.disabled = !canInspectProviderPrivateSignedUrl();
    elements.providerPrivateSignedUrlRevoke.disabled = !canRevokeProviderPrivateSignedUrl();
}

function providerPublicUrlPanelState() {
    if (State.providerPublicUrlError) {
        return { label: State.providerPublicUrlError.error_code || 'provider_public_url_blocked', pill: 'blocked', message: State.providerPublicUrlError.message || 'Provider-public URL control is blocked.' };
    }
    const stateName = providerPublicUrlLatestState();
    if (stateName === 'provider_public_url_revoked') {
        return { label: stateName, pill: 'ready', message: 'Provider-public URL receipt has been revoked; a replacement can be prepared from provider-private authority.' };
    }
    if (stateName === 'provider_public_url_expired') {
        return { label: stateName, pill: 'ready', message: 'Provider-public URL receipt has expired; a replacement can be prepared from provider-private authority.' };
    }
    if (stateName === 'provider_public_url_prepared') {
        return { label: stateName, pill: 'ready', message: 'Provider-public URL receipt is prepared; delivery/use and raw public URL exposure remain closed.' };
    }
    if (providerPrivateSignedUrlReceiptId() && providerPrivateSignedUrlLatestState() === 'provider_private_signed_url_prepared') {
        return { label: 'provider_public_url_ui_ready', pill: 'ready', message: 'Ready to prepare a server-redacted provider-public URL receipt.' };
    }
    return { label: 'provider_public_url_ui_unavailable', pill: 'blocked', message: 'Prepare a provider-private receipt before provider-public URL controls.' };
}

function providerPublicUrlDisplayValue(value) {
    if (Array.isArray(value)) return value.length ? value.join(', ') : 'none';
    if (value === true) return 'true';
    if (value === false) return 'false';
    return value ?? 'none';
}

function renderProviderPublicUrlPanel() {
    const provider = State.providerPublicUrlRevoke || State.providerPublicUrlStatus || State.providerPublicUrlPrepare || {};
    const panelState = providerPublicUrlPanelState();
    const audit = provider.audit_receipt || {};
    const rows = {
        receipt_id: provider.provider_public_url_receipt_id,
        provider_public_state: provider.provider_public_url_state,
        provider_private_receipt_id: provider.provider_private_signed_url_receipt_id || providerPrivateSignedUrlReceiptId(),
        delivery_mode: provider.delivery_mode || 'provider_public_url',
        provider_public_url_redacted: provider.provider_public_url_redacted,
        expires_at: provider.provider_public_url_expires_at,
        replay_policy: provider.provider_public_url_replay_policy,
        revocation_supported: provider.provider_public_url_revocation_supported,
        revoked: provider.provider_public_url_revoked,
        raw_public_url_exposed: provider.raw_public_url_exposed === true ? true : false,
        public_url_enabled: provider.public_url_enabled === true ? true : false,
        source_artifact_hash: provider.source_artifact_hash,
        source_artifact_size_bytes: provider.source_artifact_size_bytes,
        audit_receipt_id: audit.audit_event_id || audit.provider_public_url_audit_event_id,
        audit_reason_code: audit.reason_code,
        next_allowed_actions: provider.next_allowed_actions,
        delivery_route: 'closed_not_implemented',
        use_route: 'closed_not_implemented',
        raw_public_url_display: 'blocked_not_rendered',
        browser_durable_authority: 'blocked_not_persisted',
    };
    elements.providerPublicUrlPanel.innerHTML = `
        <div class="result-review-status">
            <span class="status-pill ${escapeHtml(panelState.pill)}">${escapeHtml(panelState.label)}</span>
            <span class="rail-label">${escapeHtml(panelState.message)}</span>
        </div>
        <div class="result-review-grid">
            ${Object.entries(rows).map(([label, value]) => `
                <section class="result-review-card">
                    <strong>${escapeHtml(label.replace(/_/g, ' '))}</strong>
                    <p>${escapeHtml(providerPublicUrlDisplayValue(value))}</p>
                </section>
            `).join('')}
        </div>
    `;
    elements.providerPublicUrlPrepare.disabled = !canPrepareProviderPublicUrl();
    elements.providerPublicUrlStatus.disabled = !canInspectProviderPublicUrl();
    elements.providerPublicUrlRevoke.disabled = !canRevokeProviderPublicUrl();
}

function setGateControls() {
    const gateCCommitted = isTypingCommitted();
    const sessionId = currentSessionId();
    const authority = selectedResultAuthority();
    const reviewRecorded = Boolean(recordedResultReview());
    const resultReviewControlsEnabled = Boolean(
        State.resultStatus?.result_status_available === true
        && !reviewRecorded
        && !State.resultReviewPending
        && !State.packageReviewPreviewPending
        && !State.packageConstructionPending
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const packageReviewControlsEnabled = Boolean(
        (packageReviewSubmitState() || {}).package_review_submit_enabled === true
        && !State.packageReviewSubmitPending
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const handoffExportControlsEnabled = Boolean(
        State.sessionSummary?.handoff_export_prepare?.available === true
        && (packageReviewSubmitState()?.package_review_state || packageReviewSubmitState()?.state) === 'package_review_approved'
        && !recordedHandoffExportPrepare()
        && !State.handoffExportPreparePending
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const apsHandoffControlsEnabled = Boolean(
        apsHandoffDispatchState()?.available === true
        && !recordedApsHandoffDispatch()
        && !State.apsHandoffDispatchPending
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const externalExportDownloadControlsEnabled = Boolean(
        State.sessionSummary?.external_export_download?.available === true
        && !recordedExternalExportDownloadPrepare()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const externalExportDownloadDeliveryControlsEnabled = Boolean(
        recordedExternalExportDownloadPrepare()
        && externalExportDownloadDeliveryUiAdmitted()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    const externalExportDownloadSignedReferenceControlsEnabled = Boolean(
        recordedExternalExportDownloadPrepare()
        && externalExportDownloadDeliveryUiAdmitted()
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
        && !State.externalExportDownloadSignedReferencePending
        && !State.externalExportDownloadSignedReferenceUsePending
    );
    elements.gateBSubmit.disabled = !(State.materialPreview?.material_candidates || []).length;
    if (elements.rawMixedMaterialize) {
        elements.rawMixedMaterialize.disabled = !canMaterializeRawMixed();
    }
    elements.gateCPreview.disabled = !sessionId || gateCCommitted;
    elements.gateCCommit.disabled = !sessionId || gateCCommitted;
    elements.planPreview.disabled = !canPlanPreview() || Boolean(State.planApproval) || Boolean(State.planRevision) || State.planRevisionPending;
    elements.planReject.disabled = !canPlanRevise();
    elements.planRequestRevision.disabled = !canPlanRevise();
    elements.planApprove.disabled = !canPlanApprove();
    elements.executionSelect.disabled = !canSelectExecution();
    elements.executionStart.disabled = !canStartExecution();
    elements.resultReviewRefresh.disabled = !canRefreshSessionSummary();
    elements.resultStatusInspect.disabled = !canInspectResultStatus();
    elements.resultReviewDecision.disabled = !resultReviewControlsEnabled;
    elements.resultReviewNotes.disabled = !resultReviewControlsEnabled;
    elements.resultReviewSubmit.disabled = !canSubmitResultReview();
    elements.packageReviewPreviewInspect.disabled = !canInspectPackageReviewPreview();
    elements.packageConstructionCommit.disabled = !canCommitPackageConstruction();
    elements.packageReviewSubmitDecision.disabled = !packageReviewControlsEnabled;
    elements.packageReviewSubmitNotes.disabled = !packageReviewControlsEnabled;
    elements.packageReviewSubmit.disabled = !canSubmitPackageReview();
    elements.handoffExportPrepareDecision.disabled = !handoffExportControlsEnabled;
    elements.handoffExportPrepareNotes.disabled = !handoffExportControlsEnabled;
    elements.handoffExportPrepareSubmit.disabled = !canSubmitHandoffExportPrepare();
    elements.apsHandoffDispatchSubmit.disabled = !apsHandoffControlsEnabled || !canSubmitApsHandoffDispatch();
    elements.externalExportDownloadPrepareSubmit.disabled = !externalExportDownloadControlsEnabled || !canSubmitExternalExportDownloadPrepare();
    elements.externalExportDownloadDeliverySubmit.disabled = !externalExportDownloadDeliveryControlsEnabled || !canSubmitExternalExportDownloadDelivery();
    elements.externalExportDownloadSignedReferenceGenerate.disabled = !externalExportDownloadSignedReferenceControlsEnabled || !canGenerateExternalExportDownloadSignedReference();
    elements.externalExportDownloadSignedReferenceUse.disabled = !externalExportDownloadSignedReferenceControlsEnabled || !canUseExternalExportDownloadSignedReference();
    elements.providerPrivateSignedUrlPrepare.disabled = !externalExportDownloadSignedReferenceControlsEnabled || !canPrepareProviderPrivateSignedUrl();
    elements.providerPrivateSignedUrlStatus.disabled = !externalExportDownloadSignedReferenceControlsEnabled || !canInspectProviderPrivateSignedUrl();
    elements.providerPrivateSignedUrlRevoke.disabled = !externalExportDownloadSignedReferenceControlsEnabled || !canRevokeProviderPrivateSignedUrl();
    elements.providerPublicUrlPrepare.disabled = !canPrepareProviderPublicUrl();
    elements.providerPublicUrlStatus.disabled = !canInspectProviderPublicUrl();
    elements.providerPublicUrlRevoke.disabled = !canRevokeProviderPublicUrl();
    setStepChip(elements.planStep, canPlanPreview());
    setStepChip(elements.executionStep, Boolean(State.executionSelection || State.sessionSummary?.execution_selection?.selected));
    setStepChip(elements.resultsStep, Boolean(authority.selected && authority.terminal));
    setStepChip(elements.packageStep, isPackageActive());
    setStepChip(elements.handoffStep, isHandoffActive());
}

function renderAll() {
    renderMockupThemeShell();
    renderAuthority();
    renderRawMixedMaterializationPanel();
    renderDatasetVersionCandidates();
    renderApsContentDocumentCandidates();
    renderSublayerMap();
    renderUnavailable(currentDownstreamUnavailable());
    renderContext();
    renderMaterialLedger();
    renderAuthorityMatrixReviewPanel();
    renderLayer3E2EGovernanceLifecycleDashboardPanel();
    renderGateCPanel();
    renderPlanPanel();
    renderExecutionSelectionStartPanel();
    renderResultReviewPanel();
    renderPackageReviewPreviewPanel();
    renderPackageLifecycleDashboardPanel();
    renderDownstreamAccessLifecycleDashboardPanel();
    renderHandoffExportPreparePanel();
    renderApsHandoffDispatchPanel();
    renderExternalExportDownloadPreparePanel();
    renderExternalExportDownloadDeliveryPanel();
    renderExternalExportDownloadSignedReferencePanel();
    renderProviderPrivateSignedUrlPanel();
    renderProviderPublicUrlPanel();
    setGateControls();
    renderOperationsDock();
}

function executionSelectionPayload() {
    const authority = executionPlanAuthority();
    return {
        client_request_id: requestId(),
        session_id: currentSessionId(),
        analysis_plan_id: authority.analysisPlanId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
    };
}

function executionStartPayload() {
    const selection = executionSelectionState();
    const authority = executionPlanAuthority();
    const passRunIds = Array.isArray(selection.pass_run_ids)
        ? selection.pass_run_ids
        : [];
    return {
        client_request_id: requestId(),
        session_id: currentSessionId(),
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: passRunIds[0],
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        execution_mode: 'synchronous_single_pass',
    };
}

function resultStatusPayload(authority = selectedResultAuthority()) {
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        operator_view_mode: 'status_only',
    };
    if (authority.analysisRunId) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    return payload;
}

function resultReviewPayload(authority = selectedResultAuthority()) {
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        operator_decision: elements.resultReviewDecision.value,
        review_notes: elements.resultReviewNotes.value.trim(),
    };
    if (authority.analysisRunId) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    const reviewedOutputItems = associatedCohortReviewedOutputItems(authority);
    if (reviewedOutputItems.length) {
        payload.reviewed_output_items = reviewedOutputItems;
    }
    return payload;
}

function packageReviewPreviewPayload(authority = selectedResultAuthority()) {
    const review = recordedApprovedResultReview();
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
    };
    if (authority.analysisRunId) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    if (review?.review_record_ref) {
        payload.result_review_record_ref = review.review_record_ref;
    }
    return payload;
}

function packageConstructionPayload(authority = selectedResultAuthority()) {
    const review = recordedApprovedResultReview();
    const preview = State.packageReviewPreview || {};
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: preview.result_review_record_ref || review?.review_record_ref,
        package_review_preview_hash: preview.package_review_preview_hash,
        expected_package_kinds: PACKAGE_REVIEW_PACKAGE_KINDS,
    };
    if (authority.analysisRunId) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    return payload;
}

function packageReviewSubmitPayload(authority = selectedResultAuthority()) {
    const review = recordedApprovedResultReview();
    const submit = packageReviewSubmitState() || {};
    const construction = packageConstructionState() || {};
    const qualitativeAps = isQualitativeApsPackageSubmitState(submit, construction);
    const constructionBasisHash = packageConstructionBasisHash();
    const previewHash = packageReviewPreviewHash();
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: submit.result_review_record_ref || construction.result_review_record_ref || review?.review_record_ref,
        package_review_preview_hash: previewHash,
        reconciliation_record_id: submit.reconciliation_record_id,
        output_package_ids: packageOutputPackageIds(),
        payload_refs: packagePayloadRefs(),
        payload_hashes: packagePayloadHashes(),
        operator_decision: elements.packageReviewSubmitDecision.value,
        decision_notes: elements.packageReviewSubmitNotes.value.trim(),
        expected_package_kinds: PACKAGE_REVIEW_PACKAGE_KINDS,
    };
    if (constructionBasisHash) {
        payload.construction_basis_hash = constructionBasisHash;
    }
    if (authority.analysisRunId && !qualitativeAps) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    return payload;
}

function handoffExportPreparePayload(authority = selectedResultAuthority()) {
    const handoff = State.sessionSummary?.handoff_export_prepare || {};
    const submit = packageReviewSubmitState() || {};
    const qualitativeAps = isQualitativeApsPackageSubmitState(submit, packageConstructionState() || {});
    const constructionBasisHash = qualitativeAps ? handoff.construction_basis_hash || packageConstructionBasisHash() : null;
    const notes = elements.handoffExportPrepareNotes.value.trim();
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: handoff.result_review_record_ref || submit.result_review_record_ref,
        package_review_preview_hash: handoff.package_review_preview_hash || submit.package_review_preview_hash,
        reconciliation_record_id: handoff.reconciliation_record_id || submit.reconciliation_record_id,
        output_package_ids: packageOutputPackageIds(),
        payload_refs: packagePayloadRefs(),
        payload_hashes: packagePayloadHashes(),
        package_review_submit_record_ref: handoff.package_review_submit_record_ref || submit.submit_record_ref,
        package_review_state: submit.package_review_state || submit.state || handoff.package_review_state,
        package_review_submit_schema_id: handoff.package_review_submit_schema_id || submit.package_review_submit_schema_id || submit.schema_id,
        handoff_target: 'internal_export_envelope',
        export_mode: 'prepare_only',
        operator_decision: elements.handoffExportPrepareDecision.value,
        expected_package_kinds: PACKAGE_REVIEW_PACKAGE_KINDS,
    };
    if (notes) {
        payload.decision_notes = notes;
    }
    if (constructionBasisHash) {
        payload.construction_basis_hash = constructionBasisHash;
    }
    if (handoff.analysis_run_id || authority.analysisRunId) {
        payload.analysis_run_id = handoff.analysis_run_id || authority.analysisRunId;
    }
    return payload;
}

function apsHandoffDispatchPayload(authority = selectedResultAuthority()) {
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: handoff.result_review_record_ref || submit.result_review_record_ref,
        package_review_preview_hash: handoff.package_review_preview_hash || submit.package_review_preview_hash,
        reconciliation_record_id: handoff.reconciliation_record_id || submit.reconciliation_record_id,
        output_package_ids: packageOutputPackageIds(),
        package_kinds: packageKindsFromState(),
        payload_refs: packagePayloadRefs(),
        payload_hashes: packagePayloadHashes(),
        package_review_submit_record_ref: handoff.package_review_submit_record_ref || submit.submit_record_ref,
        package_review_state: submit.package_review_state || submit.state || handoff.package_review_state,
        prepare_record_ref: handoff.prepare_record_ref,
        handoff_export_state: handoff.handoff_export_state || handoff.next_state || handoff.state,
        handoff_export_envelope_ref: handoffExportEnvelopeRef(handoff),
        handoff_target: 'internal_export_envelope',
        export_mode: 'prepare_only',
        aps_handoff_target: 'aps_evidence_bundle',
        dispatch_mode: 'server_side_aps_handoff',
        operator_decision: 'dispatch_aps_handoff',
    };
    if (handoff.analysis_run_id || authority.analysisRunId) {
        payload.analysis_run_id = handoff.analysis_run_id || authority.analysisRunId;
    }
    return payload;
}

function externalExportDownloadPreparePayload(authority = selectedResultAuthority()) {
    const external = State.sessionSummary?.external_export_download || {};
    const aps = apsHandoffDispatchState() || {};
    const handoff = handoffExportPrepareState() || {};
    const submit = packageReviewSubmitState() || {};
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: external.result_review_record_ref || handoff.result_review_record_ref || submit.result_review_record_ref,
        package_review_preview_hash: external.package_review_preview_hash || handoff.package_review_preview_hash || submit.package_review_preview_hash,
        reconciliation_record_id: external.reconciliation_record_id || handoff.reconciliation_record_id || submit.reconciliation_record_id,
        output_package_ids: Array.isArray(external.output_package_ids) && external.output_package_ids.length ? external.output_package_ids : packageOutputPackageIds(),
        package_kinds: Array.isArray(external.package_kinds) && external.package_kinds.length ? external.package_kinds : packageKindsFromState(),
        payload_refs: Array.isArray(external.payload_refs) && external.payload_refs.length ? external.payload_refs : packagePayloadRefs(),
        payload_hashes: Array.isArray(external.payload_hashes) && external.payload_hashes.length ? external.payload_hashes : packagePayloadHashes(),
        package_review_submit_record_ref: external.package_review_submit_record_ref || handoff.package_review_submit_record_ref || submit.submit_record_ref,
        package_review_state: external.package_review_state || submit.package_review_state || submit.state || handoff.package_review_state,
        prepare_record_ref: external.prepare_record_ref || handoff.prepare_record_ref,
        handoff_export_state: external.handoff_export_state || handoff.handoff_export_state || handoff.next_state || handoff.state,
        handoff_export_envelope_ref: external.handoff_export_envelope_ref || handoffExportEnvelopeRef(handoff),
        handoff_target: external.handoff_target || 'internal_export_envelope',
        export_mode: external.export_mode || 'prepare_only',
        aps_handoff_record_ref: external.aps_handoff_record_ref || aps.aps_handoff_record_ref,
        aps_handoff_state: external.aps_handoff_state || apsHandoffStateName(aps),
        aps_handoff_target: external.aps_handoff_target || aps.aps_handoff_target || 'aps_evidence_bundle',
        dispatch_mode: external.dispatch_mode || aps.dispatch_mode || 'server_side_aps_handoff',
        aps_output_package_id: external.aps_output_package_id || aps.aps_output_package_id,
        aps_output_package_kind: external.aps_output_package_kind || aps.aps_output_package_kind,
        aps_bundle_ref: external.aps_bundle_ref || aps.aps_bundle_ref,
        aps_bundle_id: external.aps_bundle_id || aps.aps_bundle_id,
        aps_schema_id: external.aps_schema_id || aps.aps_schema_id,
        export_download_target: external.export_download_target || 'aps_evidence_bundle_download_reference',
        download_mode: external.download_mode || 'reference_only_prepare',
        operator_decision: 'prepare_external_export_download',
    };
    if (external.analysis_run_id || handoff.analysis_run_id || authority.analysisRunId) {
        payload.analysis_run_id = external.analysis_run_id || handoff.analysis_run_id || authority.analysisRunId;
    }
    if (external.source_artifact_hash) {
        payload.aps_bundle_hash = external.source_artifact_hash;
    }
    if (external.source_artifact_size_bytes != null) {
        payload.aps_bundle_size_bytes = external.source_artifact_size_bytes;
    }
    return payload;
}

function externalExportDownloadDeliveryPayload(authority = selectedResultAuthority()) {
    const external = externalExportDownloadPrepareState() || {};
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: external.result_review_record_ref,
        package_review_preview_hash: external.package_review_preview_hash,
        reconciliation_record_id: external.reconciliation_record_id,
        output_package_ids: Array.isArray(external.output_package_ids) && external.output_package_ids.length ? external.output_package_ids : packageOutputPackageIds(),
        package_kinds: Array.isArray(external.package_kinds) && external.package_kinds.length ? external.package_kinds : packageKindsFromState(),
        payload_refs: Array.isArray(external.payload_refs) && external.payload_refs.length ? external.payload_refs : packagePayloadRefs(),
        payload_hashes: Array.isArray(external.payload_hashes) && external.payload_hashes.length ? external.payload_hashes : packagePayloadHashes(),
        package_review_submit_record_ref: external.package_review_submit_record_ref,
        package_review_state: external.package_review_state,
        prepare_record_ref: external.prepare_record_ref,
        handoff_export_state: external.handoff_export_state,
        handoff_export_envelope_ref: external.handoff_export_envelope_ref,
        handoff_target: external.handoff_target || 'internal_export_envelope',
        export_mode: external.export_mode || 'prepare_only',
        aps_handoff_record_ref: external.aps_handoff_record_ref,
        aps_handoff_state: external.aps_handoff_state,
        aps_handoff_target: external.aps_handoff_target || 'aps_evidence_bundle',
        dispatch_mode: external.dispatch_mode || 'server_side_aps_handoff',
        aps_output_package_id: external.aps_output_package_id,
        aps_output_package_kind: external.aps_output_package_kind,
        aps_bundle_ref: external.aps_bundle_ref,
        aps_bundle_id: external.aps_bundle_id,
        aps_schema_id: external.aps_schema_id,
        export_download_target: external.export_download_target || 'aps_evidence_bundle_download_reference',
        download_mode: external.download_mode || 'reference_only_prepare',
        operator_decision: 'deliver_external_export_download',
        external_export_download_record_ref: external.external_export_download_record_ref,
        export_download_descriptor_ref: external.export_download_descriptor_ref,
        external_export_download_state: externalExportDownloadStateName(external),
        delivery_mode: 'same_origin_artifact_stream',
    };
    if (external.analysis_run_id || authority.analysisRunId) {
        payload.analysis_run_id = external.analysis_run_id || authority.analysisRunId;
    }
    if (external.source_artifact_hash) {
        payload.aps_bundle_hash = external.source_artifact_hash;
    }
    if (external.source_artifact_size_bytes != null) {
        payload.aps_bundle_size_bytes = external.source_artifact_size_bytes;
    }
    return payload;
}

function externalExportDownloadSignedReferencePayload(authority = selectedResultAuthority()) {
    return externalExportDownloadDeliveryPayload(authority);
}

function providerPrivateSignedUrlPreparePayload(authority = selectedResultAuthority()) {
    const external = externalExportDownloadPrepareState() || {};
    const externalPayload = externalExportDownloadDeliveryPayload(authority);
    return {
        client_request_id: providerPrivateSignedUrlPrepareRequestId(),
        session_id: externalPayload.session_id,
        analysis_plan_id: externalPayload.analysis_plan_id,
        pass_run_id: externalPayload.pass_run_id,
        reconciliation_record_id: externalPayload.reconciliation_record_id,
        external_export_download_record_ref: externalPayload.external_export_download_record_ref,
        export_download_descriptor_ref: externalPayload.export_download_descriptor_ref,
        external_export_download_state: externalPayload.external_export_download_state,
        export_download_target: externalPayload.export_download_target,
        download_mode: externalPayload.download_mode,
        delivery_mode: 'provider_private_signed_url',
        operator_decision: 'prepare_provider_private_signed_url',
        source_artifact_hash: external.source_artifact_hash,
        source_artifact_size_bytes: external.source_artifact_size_bytes,
        recipient_scope: 'external_downstream_recipient_private_artifact_delivery',
        requested_ttl_seconds: 300,
        signed_reference_receipt_id: State.externalExportDownloadSignedReferenceUse?.signedReferenceReceiptId
            || State.externalExportDownloadSignedReference?.signed_reference_receipt_id,
        decision_notes: 'Rendered workbench prepare/status/revoke lane; provider-private use remains closed.',
    };
}

function providerPrivateSignedUrlRevokePayload() {
    const receiptId = providerPrivateSignedUrlReceiptId();
    return {
        client_request_id: requestId(),
        provider_signed_url_receipt_id: receiptId,
        idempotency_key: `provider-private-revoke:${receiptId}`,
        revoked_by: 'layer3-rendered-workbench',
        revocation_reason: 'operator revoked provider-private signed URL from rendered workbench',
        operator_decision: 'revoke_provider_private_signed_url',
        decision_notes: 'Rendered workbench revoke lane; provider-private use remains closed.',
    };
}

function providerPublicUrlPrepareRequestId() {
    if (!State.providerPublicUrlPrepareClientRequestId) {
        State.providerPublicUrlPrepareClientRequestId = requestId();
    }
    return State.providerPublicUrlPrepareClientRequestId;
}

function providerPublicUrlPreparePayload() {
    return {
        client_request_id: providerPublicUrlPrepareRequestId(),
        provider_private_signed_url_receipt_id: providerPrivateSignedUrlReceiptId(),
        recipient_scope: 'external_downstream_recipient_provider_public_url_access',
        requested_ttl_seconds: 300,
        delivery_mode: 'provider_public_url',
        operator_decision: 'prepare_provider_public_url',
        decision_notes: 'Rendered workbench prepare/status/revoke lane; provider-public delivery/use and raw URL exposure remain closed.',
    };
}

function providerPublicUrlRevokePayload() {
    const receiptId = providerPublicUrlReceiptId();
    return {
        client_request_id: requestId(),
        provider_public_url_receipt_id: receiptId,
        idempotency_key: `provider-public-revoke:${receiptId}`,
        revoked_by: 'layer3-rendered-workbench',
        revocation_reason: 'operator revoked provider-public URL from rendered workbench',
        operator_decision: 'revoke_provider_public_url',
        decision_notes: 'Rendered workbench revoke lane; provider-public delivery/use and raw URL exposure remain closed.',
    };
}

async function useExternalExportDownloadSignedReferenceToken(token) {
    const res = await fetch(`${API_ROOT}/handoff/export/download/signed-reference/use`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signed_reference_token: token }),
    });
    if (!res.ok) {
        const data = await res.json().catch(() => null);
        const err = new Error(data?.message || `HTTP ${res.status}`);
        err.status = res.status;
        err.payload = data;
        throw err;
    }
    await res.arrayBuffer();
    return {
        state: res.headers.get('x-layer3-signed-reference-state') || res.headers.get('x-layer3-delivery-state') || 'external_export_download_signed_reference_delivered',
        schemaId: res.headers.get('x-layer3-schema-id') || 'layer3.external_export_download_signed_reference_use.v1',
        sourceArtifactHash: res.headers.get('x-layer3-source-artifact-hash'),
        expiresAt: res.headers.get('x-layer3-signed-reference-expires-at'),
        signedReferenceReceiptId: res.headers.get('x-layer3-signed-reference-receipt-id'),
        contentType: res.headers.get('content-type'),
    };
}

async function selectExecution() {
    if (!canSelectExecution()) return;
    State.executionSelectionPending = true;
    State.executionSelectionError = null;
    setBusy(elements.executionSelect, true, 'Select Execution');
    try {
        State.executionSelection = await postJson('/execution/select', executionSelectionPayload());
        State.executionStart = null;
        State.executionStartError = null;
        State.resultStatus = null;
        State.resultStatusError = null;
        State.resultReview = null;
        State.resultReviewError = null;
        State.packageReviewPreview = null;
        State.packageReviewPreviewError = null;
        State.packageConstruction = null;
        State.packageConstructionError = null;
        State.packageReviewSubmit = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepare = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatch = null;
        State.apsHandoffDispatchError = null;
        clearExternalExportDownloadPrepareState();
        addEvent('Execution selected for approved plan.');
        renderAll();
    } catch (error) {
        State.executionSelectionError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'execution_selection_request_failed',
            message: error.message,
        };
        addEvent(`Execution selection blocked: ${error.message}`);
        renderAll();
    } finally {
        State.executionSelectionPending = false;
        setBusy(elements.executionSelect, false, 'Select Execution');
        setGateControls();
        renderAll();
    }
}

async function startExecution() {
    if (!canStartExecution()) return;
    State.executionStartPending = true;
    State.executionStartError = null;
    setBusy(elements.executionStart, true, 'Start Execution');
    try {
        State.executionStart = await postJson('/execution/start', executionStartPayload());
        State.resultStatus = null;
        State.resultStatusError = null;
        State.resultReview = null;
        State.resultReviewError = null;
        State.packageReviewPreview = null;
        State.packageReviewPreviewError = null;
        State.packageConstruction = null;
        State.packageConstructionError = null;
        State.packageReviewSubmit = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepare = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatch = null;
        State.apsHandoffDispatchError = null;
        clearExternalExportDownloadPrepareState();
        addEvent('Execution started for selected pass.');
        renderAll();
    } catch (error) {
        State.executionStartError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'analysis_execution_start_request_failed',
            message: error.message,
        };
        addEvent(`Execution start blocked: ${error.message}`);
        renderAll();
    } finally {
        State.executionStartPending = false;
        setBusy(elements.executionStart, false, 'Start Execution');
        setGateControls();
        renderAll();
    }
}

async function refreshSessionSummary() {
    const sessionId = currentSessionId();
    if (!sessionId) return;
    setBusy(elements.resultReviewRefresh, true, 'Refresh Session State');
    try {
        const previousSessionId = State.sessionSummary?.session_id;
        State.sessionSummary = await getJson(`/session/${encodeURIComponent(sessionId)}`);
        if (previousSessionId && previousSessionId !== State.sessionSummary.session_id) {
            clearResultReviewState({ keepSummary: true });
        }
        persistSessionRecoveryAnchor('manual_refresh');
        State.executionSelectionError = null;
        State.executionStartError = null;
        State.resultStatusError = null;
        State.resultReviewError = null;
        State.packageReviewPreviewError = null;
        State.packageConstructionError = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        State.externalExportDownloadSignedReferenceError = null;
        addEvent('Session state refreshed.');
        renderAll();
    } catch (error) {
        State.resultStatusError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'session_summary_request_failed',
            message: error.message,
        };
        addEvent(`Session refresh blocked: ${error.message}`);
        renderAll();
    } finally {
        setBusy(elements.resultReviewRefresh, false, 'Refresh Session State');
        setGateControls();
    }
}

async function inspectResultStatus() {
    if (!canInspectResultStatus()) return;
    setBusy(elements.resultStatusInspect, true, 'Inspect Result Status');
    try {
        State.resultStatus = await postJson('/execution/result/status', resultStatusPayload());
        State.resultStatusError = null;
        State.resultReviewError = null;
        State.packageReviewPreview = null;
        State.packageReviewPreviewError = null;
        State.packageConstruction = null;
        State.packageConstructionError = null;
        State.packageReviewSubmit = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepare = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatch = null;
        State.apsHandoffDispatchError = null;
        clearExternalExportDownloadPrepareState();
        addEvent('Result/status authority loaded.');
        renderAll();
    } catch (error) {
        State.resultStatusError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'execution_result_status_request_failed',
            message: error.message,
        };
        addEvent(`Result/status blocked: ${error.message}`);
        renderAll();
    } finally {
        setBusy(elements.resultStatusInspect, false, 'Inspect Result Status');
        setGateControls();
    }
}

async function inspectPackageReviewPreview() {
    if (!canInspectPackageReviewPreview()) return;
    State.packageReviewPreviewPending = true;
    State.packageReviewPreviewError = null;
    State.handoffExportPrepare = null;
    State.handoffExportPrepareError = null;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.packageReviewPreviewInspect, true, 'Inspect Package Preview');
    try {
        State.packageReviewPreview = await postJson('/package/review/preview', packageReviewPreviewPayload());
        State.packageReviewPreviewError = null;
        State.packageConstructionError = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        addEvent('Package review preview loaded.');
        renderAll();
    } catch (error) {
        State.packageReviewPreviewError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'package_review_preview_request_failed',
            message: error.message,
        };
        addEvent(`Package preview blocked: ${error.message}`);
        renderAll();
    } finally {
        State.packageReviewPreviewPending = false;
        setBusy(elements.packageReviewPreviewInspect, false, 'Inspect Package Preview');
        renderAll();
    }
}

async function commitPackageConstruction() {
    if (!canCommitPackageConstruction()) return;
    State.packageConstructionPending = true;
    State.packageConstructionError = null;
    State.packageReviewSubmitError = null;
    State.handoffExportPrepare = null;
    State.handoffExportPrepareError = null;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.packageConstructionCommit, true, 'Commit Package Set');
    try {
        State.packageConstruction = await postJson('/package/review/commit', packageConstructionPayload());
        State.packageConstructionError = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        addEvent('Package set committed.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.packageConstruction.session_id)}`);
            persistSessionRecoveryAnchor('package_construction_refresh');
        } catch (refreshError) {
            addEvent(`Package committed; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.packageConstructionError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'package_construction_commit_request_failed',
            message: error.message,
        };
        addEvent(`Package commit blocked: ${error.message}`);
        renderAll();
    } finally {
        State.packageConstructionPending = false;
        setBusy(elements.packageConstructionCommit, false, 'Commit Package Set');
        renderAll();
    }
}

async function submitPackageReview(event) {
    event.preventDefault();
    if (!canSubmitPackageReview()) return;
    State.packageReviewSubmitPending = true;
    State.packageReviewSubmitError = null;
    State.handoffExportPrepare = null;
    State.handoffExportPrepareError = null;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.packageReviewSubmit, true, 'Submit Package Review');
    try {
        State.packageReviewSubmit = await postJson('/package/review/submit', packageReviewSubmitPayload());
        State.packageReviewSubmitError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        addEvent('Package review submitted.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.packageReviewSubmit.session_id)}`);
            persistSessionRecoveryAnchor('package_review_submit_refresh');
        } catch (refreshError) {
            addEvent(`Package review submitted; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.packageReviewSubmitError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'package_review_submit_request_failed',
            message: error.message,
        };
        addEvent(`Package review submit blocked: ${error.message}`);
        renderAll();
    } finally {
        State.packageReviewSubmitPending = false;
        setBusy(elements.packageReviewSubmit, false, 'Submit Package Review');
        renderAll();
    }
}

async function submitHandoffExportPrepare(event) {
    event.preventDefault();
    if (!canSubmitHandoffExportPrepare()) return;
    State.handoffExportPreparePending = true;
    State.handoffExportPrepareError = null;
    State.apsHandoffDispatch = null;
    State.apsHandoffDispatchError = null;
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.handoffExportPrepareSubmit, true, 'Submit Preparation');
    try {
        State.handoffExportPrepare = await postJson('/handoff/export/prepare', handoffExportPreparePayload());
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        addEvent('Handoff/export preparation recorded.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.handoffExportPrepare.session_id)}`);
            persistSessionRecoveryAnchor('handoff_export_prepare_refresh');
        } catch (refreshError) {
            addEvent(`Handoff/export preparation recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.handoffExportPrepareError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'handoff_export_prepare_request_failed',
            message: error.message,
        };
        addEvent(`Handoff/export preparation blocked: ${error.message}`);
        renderAll();
    } finally {
        State.handoffExportPreparePending = false;
        setBusy(elements.handoffExportPrepareSubmit, false, 'Submit Preparation');
        renderAll();
    }
}

async function submitApsHandoffDispatch(event) {
    event.preventDefault();
    if (!canSubmitApsHandoffDispatch()) return;
    State.apsHandoffDispatchPending = true;
    State.apsHandoffDispatchError = null;
    clearExternalExportDownloadPrepareState();
    renderAll();
    setBusy(elements.apsHandoffDispatchSubmit, true, 'Dispatch APS Handoff');
    try {
        State.apsHandoffDispatch = await postJson('/handoff/aps/dispatch', apsHandoffDispatchPayload());
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
        addEvent('APS handoff dispatch recorded.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.apsHandoffDispatch.session_id)}`);
            persistSessionRecoveryAnchor('aps_handoff_dispatch_refresh');
        } catch (refreshError) {
            addEvent(`APS handoff dispatch recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.apsHandoffDispatchError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'aps_handoff_dispatch_request_failed',
            message: error.message,
        };
        addEvent(`APS handoff dispatch blocked: ${error.message}`);
        renderAll();
    } finally {
        State.apsHandoffDispatchPending = false;
        setBusy(elements.apsHandoffDispatchSubmit, false, 'Dispatch APS Handoff');
        renderAll();
    }
}

async function submitExternalExportDownloadPrepare(event) {
    event.preventDefault();
    if (!canSubmitExternalExportDownloadPrepare()) return;
    State.externalExportDownloadPreparePending = true;
    State.externalExportDownloadPrepareError = null;
    renderAll();
    setBusy(elements.externalExportDownloadPrepareSubmit, true, 'Prepare External Readiness');
    try {
        State.externalExportDownloadPrepare = await postJson('/handoff/export/download/prepare', externalExportDownloadPreparePayload());
        State.externalExportDownloadPrepareError = null;
        addEvent('External export/download readiness recorded.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.externalExportDownloadPrepare.session_id)}`);
            persistSessionRecoveryAnchor('external_export_download_prepare_refresh');
        } catch (refreshError) {
            addEvent(`External readiness recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.externalExportDownloadPrepareError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'external_export_download_prepare_request_failed',
            message: error.message,
        };
        addEvent(`External export/download readiness blocked: ${error.message}`);
        renderAll();
    } finally {
        State.externalExportDownloadPreparePending = false;
        setBusy(elements.externalExportDownloadPrepareSubmit, false, 'Prepare External Readiness');
        renderAll();
    }
}

async function submitExternalExportDownloadDelivery(event) {
    event.preventDefault();
    if (!canSubmitExternalExportDownloadDelivery()) return;
    State.externalExportDownloadDeliveryPending = true;
    State.externalExportDownloadDeliveryError = null;
    renderAll();
    setBusy(elements.externalExportDownloadDeliverySubmit, true, 'Deliver External Bundle');
    try {
        const delivery = await submitAttachmentForm('/handoff/export/download/deliver', externalExportDownloadDeliveryPayload());
        State.externalExportDownloadDelivery = {
            state: delivery.state || 'external_export_download_delivered',
            schemaId: delivery.schemaId,
            filename: delivery.filename,
            sourceArtifactHash: delivery.sourceArtifactHash,
            externalExportDownloadRecordRef: delivery.externalExportDownloadRecordRef,
        };
        State.externalExportDownloadDeliveryError = null;
        addEvent('External export/download bundle submitted as browser-managed same-origin attachment.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(currentSessionId())}`);
            persistSessionRecoveryAnchor('external_export_download_delivery_refresh');
        } catch (refreshError) {
            addEvent(`External delivery completed; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.externalExportDownloadDelivery = null;
        State.externalExportDownloadDeliveryError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'external_export_download_delivery_request_failed',
            message: error.message,
        };
        addEvent(`External export/download delivery blocked: ${error.message}`);
        renderAll();
    } finally {
        State.externalExportDownloadDeliveryPending = false;
        setBusy(elements.externalExportDownloadDeliverySubmit, false, 'Deliver External Bundle');
        renderAll();
    }
}

async function submitExternalExportDownloadSignedReference(event) {
    event.preventDefault();
    if (!canGenerateExternalExportDownloadSignedReference()) return;
    State.externalExportDownloadSignedReferencePending = true;
    State.externalExportDownloadSignedReferenceError = null;
    State.externalExportDownloadSignedReferenceUse = null;
    renderAll();
    setBusy(elements.externalExportDownloadSignedReferenceGenerate, true, 'Generate Signed Reference');
    try {
        State.externalExportDownloadSignedReference = await postJson(
            '/handoff/export/download/signed-reference/generate',
            externalExportDownloadSignedReferencePayload(),
        );
        State.externalExportDownloadSignedReferenceError = null;
        addEvent('External export/download signed reference generated.');
        renderAll();
    } catch (error) {
        State.externalExportDownloadSignedReference = null;
        State.externalExportDownloadSignedReferenceError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'external_export_download_signed_reference_request_failed',
            message: error.message,
        };
        addEvent(`External export/download signed reference blocked: ${error.message}`);
        renderAll();
    } finally {
        State.externalExportDownloadSignedReferencePending = false;
        setBusy(elements.externalExportDownloadSignedReferenceGenerate, false, 'Generate Signed Reference');
        renderAll();
    }
}

async function useExternalExportDownloadSignedReference() {
    if (!canUseExternalExportDownloadSignedReference()) return;
    State.externalExportDownloadSignedReferenceUsePending = true;
    State.externalExportDownloadSignedReferenceError = null;
    renderAll();
    setBusy(elements.externalExportDownloadSignedReferenceUse, true, 'Use Signed Reference');
    try {
        State.externalExportDownloadSignedReferenceUse = await useExternalExportDownloadSignedReferenceToken(
            State.externalExportDownloadSignedReference.signed_reference_token,
        );
        addEvent('External export/download signed reference used through same-origin endpoint.');
        renderAll();
    } catch (error) {
        State.externalExportDownloadSignedReferenceUse = null;
        State.externalExportDownloadSignedReferenceError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'external_export_download_signed_reference_use_failed',
            message: error.message,
        };
        addEvent(`External export/download signed reference use blocked: ${error.message}`);
        renderAll();
    } finally {
        State.externalExportDownloadSignedReferenceUsePending = false;
        setBusy(elements.externalExportDownloadSignedReferenceUse, false, 'Use Signed Reference');
        renderAll();
    }
}

async function submitResultReview(event) {
    event.preventDefault();
    if (!canSubmitResultReview()) return;
    State.resultReviewPending = true;
    State.resultReviewError = null;
    renderAll();
    setBusy(elements.resultReviewSubmit, true, 'Submit Result Review');
    try {
        State.resultReview = await postJson('/execution/result/review', resultReviewPayload());
        State.resultReviewError = null;
        State.packageReviewPreview = null;
        State.packageReviewPreviewError = null;
        State.packageConstruction = null;
        State.packageConstructionError = null;
        State.packageReviewSubmit = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepare = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatch = null;
        State.apsHandoffDispatchError = null;
        clearExternalExportDownloadPrepareState();
        addEvent('Result review recorded.');
        try {
            State.sessionSummary = await getJson(`/session/${encodeURIComponent(State.resultReview.session_id)}`);
            persistSessionRecoveryAnchor('result_review_refresh');
        } catch (refreshError) {
            addEvent(`Review recorded; session refresh blocked: ${refreshError.message}`);
        }
        renderAll();
    } catch (error) {
        State.resultReviewError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'execution_result_review_request_failed',
            message: error.message,
        };
        addEvent(`Result review blocked: ${error.message}`);
        renderAll();
    } finally {
        State.resultReviewPending = false;
        setBusy(elements.resultReviewSubmit, false, 'Submit Result Review');
        renderAll();
    }
}

async function materializeRawMixedSources() {
    if (!canMaterializeRawMixed()) return;
    State.rawMixedMaterializationPending = true;
    State.rawMixedMaterializationError = null;
    State.rawMixedMaterialization = null;
    renderAll();
    setBusy(elements.rawMixedMaterialize, true, 'Materialize Source IDs');
    try {
        const materialization = await postJson('/source/mixed-corpus/materialize', rawMixedMaterializationPayload());
        const datasetCandidatesRefreshed = await loadDatasetVersionCandidates();
        const apsContentCandidatesRefreshed = await loadApsContentDocumentCandidates();
        if (!datasetCandidatesRefreshed || !apsContentCandidatesRefreshed) {
            State.rawMixedMaterializationError = {
                schema_id: 'layer3.workbench_error.v1',
                error_code: 'raw_mixed_materialized_source_candidate_refresh_failed',
                message: 'Materialized source IDs were not applied because candidate refresh failed.',
            };
            addEvent('Raw mixed materialization blocked after candidate refresh failure.');
            return;
        }
        if (!materializedSourceIdsVisible(materialization)) {
            State.rawMixedMaterializationError = {
                schema_id: 'layer3.workbench_error.v1',
                error_code: 'raw_mixed_materialized_source_candidate_refresh_mismatch',
                message: 'Materialized source IDs were not present after candidate refresh.',
            };
            addEvent('Raw mixed materialization blocked after candidate refresh mismatch.');
            return;
        }
        clearLayer3FlowStateForSourceChange();
        State.rawMixedMaterialization = materialization;
        applyMaterializedSourceIds(materialization);
        addEvent('Raw mixed materialized source IDs selected.');
    } catch (error) {
        State.rawMixedMaterializationError = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'raw_mixed_materialization_request_failed',
            message: error.message,
        };
        addEvent(`Raw mixed materialization blocked: ${error.message}`);
    } finally {
        State.rawMixedMaterializationPending = false;
        setBusy(elements.rawMixedMaterialize, false, 'Materialize Source IDs');
        renderAll();
    }
}

async function runPreflightFlow(event) {
    event.preventDefault();
    const intent = elements.intentInput.value.trim();
    const sourceClasses = selectedSourceClasses();
    const datasetVersionIds = selectedDatasetVersionIds();
    const apsContentDocumentIds = selectedApsContentDocumentIds();
    if (datasetVersionIds.length && !sourceClasses.includes('dataset_version')) {
        addEvent('DatasetVersion IDs require the Dataset version source class.');
        renderAll();
        return;
    }
    if (apsContentDocumentIds.length && !sourceClasses.includes('aps_content_document')) {
        addEvent('APS content document IDs require the APS content document source class.');
        renderAll();
        return;
    }
    setBusy(elements.runPreflight, true, 'Run Preflight');
    try {
        State.preflight = await postJson('/preflight', {
            schema_id: 'layer3.preflight_request.v1',
            client_request_id: requestId(),
            natural_language_intent: intent,
            manual_constraints: {
                source_classes: sourceClasses,
            },
            actor: 'operator',
        });
        addEvent('Preflight passed.');
        State.sourcePreview = await postJson('/source-preview', {
            schema_id: 'layer3.source_preview_request.v1',
            client_request_id: requestId(),
            preflight_id: State.preflight.preflight_id,
            selected_source_classes: sourceClasses,
        });
        addEvent('Source preview loaded.');
        State.materialPreview = await postJson('/material-preview', {
            schema_id: 'layer3.material_preview_request.v1',
            client_request_id: requestId(),
            preflight_id: State.preflight.preflight_id,
            source_set_id: State.sourcePreview.source_set_id,
            source_candidate_ids: State.sourcePreview.source_candidates.map((candidate) => candidate.source_candidate_id),
            dataset_version_ids: datasetVersionIds,
            aps_content_document_ids: apsContentDocumentIds,
            query_basis: {
                terms: termsFromIntent(intent),
            },
        });
        initializeGateBDecisions();
        State.gateB = null;
        State.gateC = null;
        State.sessionSummary = null;
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearSessionRecoveryAnchor();
        clearResultReviewState();
        addEvent('Material preview loaded.');
        renderAll();
    } catch (error) {
        addEvent(`Blocked: ${error.message}`);
        if (error.payload?.authority_rail) {
            renderAuthority(error.payload.authority_rail);
        }
    } finally {
        setBusy(elements.runPreflight, false, 'Run Preflight');
        setGateControls();
    }
}

async function commitGateB() {
    const decisions = collectGateBDecisions();
    setBusy(elements.gateBSubmit, true, 'Commit Gate B');
    try {
        State.gateB = await postJson('/gate-b/decision', {
            schema_id: 'layer3.gate_b_decision_request.v1',
            client_request_id: gateBRequestId(),
            preflight_id: State.preflight?.preflight_id,
            source_set_id: State.sourcePreview?.source_set_id,
            material_preview_id: State.materialPreview?.material_preview_id,
            material_preview_hash: State.materialPreview?.material_preview_hash,
            candidate_decisions: decisions,
            commit_reason: 'operator_gate_b_decision',
            actor: 'operator',
        });
        State.gateC = null;
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
        clearGateBDraftSnapshot();
        persistSessionRecoveryAnchor('gate_b_commit');
        addEvent(`Gate B committed session ${State.gateB.session_id}.`);
        renderAll();
    } catch (error) {
        addEvent(`Gate B blocked: ${error.message}`);
    } finally {
        setBusy(elements.gateBSubmit, false, 'Commit Gate B');
        setGateControls();
    }
}

async function previewGateC() {
    const sessionId = currentSessionId();
    if (!sessionId) return;
    if (isTypingCommitted()) return;
    setBusy(elements.gateCPreview, true, 'Preview Gate C');
    try {
        State.gateC = await postJson('/gate-c/preview', {
            schema_id: 'layer3.gate_c_preview_request.v1',
            client_request_id: requestId(),
            session_id: sessionId,
            commit_typing: false,
        });
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
        persistSessionRecoveryAnchor('gate_c_preview');
        addEvent('Gate C typing preview loaded.');
        renderAll();
    } catch (error) {
        addEvent(`Gate C blocked: ${error.message}`);
    } finally {
        setBusy(elements.gateCPreview, false, 'Preview Gate C');
        setGateControls();
    }
}

async function commitGateC() {
    const sessionId = currentSessionId();
    if (!sessionId) return;
    setBusy(elements.gateCCommit, true, 'Commit Gate C Typing');
    try {
        State.gateC = await postJson('/gate-c/preview', {
            schema_id: 'layer3.gate_c_preview_request.v1',
            client_request_id: requestId(),
            session_id: sessionId,
            commit_typing: true,
        });
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
        persistSessionRecoveryAnchor('gate_c_commit');
        addEvent('Gate C typing committed.');
        renderAll();
    } catch (error) {
        addEvent(`Gate C commit blocked: ${error.message}`);
    } finally {
        setBusy(elements.gateCCommit, false, 'Commit Gate C Typing');
        setGateControls();
    }
}

async function previewPlan() {
    if (!canPlanPreview()) return;
    setBusy(elements.planPreview, true, 'Preview Plan');
    try {
        State.planPreview = await postJson('/plan/preview', {
            schema_id: 'layer3.plan_preview_request.v1',
            client_request_id: requestId(),
            session_id: currentSessionId(),
            include_exclusions: true,
            preview_scope: 'owner_service_default',
        });
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
        persistSessionRecoveryAnchor('plan_preview');
        addEvent('Plan preview loaded.');
        renderAll();
    } catch (error) {
        State.planPreview = error.payload || {
            schema_id: 'layer3.workbench_error.v1',
            error_code: 'plan_preview_request_failed',
            message: error.message,
            next_allowed_actions: [],
        };
        addEvent(`Plan preview blocked: ${error.message}`);
        renderAll();
    } finally {
        setBusy(elements.planPreview, false, 'Preview Plan');
        setGateControls();
    }
}

async function approvePlan() {
    if (!canPlanApprove()) return;
    setBusy(elements.planApprove, true, 'Approve Plan');
    try {
        State.planApproval = await postJson('/plan/approve', {
            schema_id: 'layer3.plan_approval_request.v1',
            client_request_id: requestId(),
            session_id: currentSessionId(),
            preview_id: State.planPreview.preview_id,
            preview_hash: State.planPreview.preview_hash,
            operator_confirmation: true,
            approval_scope: 'owner_service_default',
        });
        clearResultReviewState();
        persistSessionRecoveryAnchor('plan_approval');
        addEvent('Plan approved. Execution has not started.');
        renderAll();
    } catch (error) {
        addEvent(`Plan approval blocked: ${error.message}`);
    } finally {
        setBusy(elements.planApprove, false, 'Approve Plan');
        setGateControls();
    }
}

async function revisePlan(operatorDecision) {
    if (!canPlanRevise()) return;
    const button = operatorDecision === 'reject_current_preview' ? elements.planReject : elements.planRequestRevision;
    const label = operatorDecision === 'reject_current_preview' ? 'Reject Plan' : 'Request Revision';
    State.planRevisionPending = true;
    setBusy(button, true, label);
    setGateControls();
    try {
        State.planRevision = await postJson('/plan/revise', {
            schema_id: 'layer3.plan_revision_request.v1',
            client_request_id: requestId(),
            session_id: currentSessionId(),
            preview_id: State.planPreview.preview_id,
            preview_hash: State.planPreview.preview_hash,
            operator_decision: operatorDecision,
        });
        clearResultReviewState();
        persistSessionRecoveryAnchor('plan_revision');
        addEvent(operatorDecision === 'reject_current_preview' ? 'Plan rejected. Execution has not started.' : 'Plan revision requested. Execution has not started.');
        renderAll();
    } catch (error) {
        addEvent(`Plan revision blocked: ${error.message}`);
    } finally {
        State.planRevisionPending = false;
        setBusy(button, false, label);
        setGateControls();
    }
}

async function submitProviderPrivateSignedUrlPrepare(event) {
    event.preventDefault();
    if (!canPrepareProviderPrivateSignedUrl()) return;
    State.providerPrivateSignedUrlPending = true;
    State.providerPrivateSignedUrlError = null;
    State.providerPrivateSignedUrlStatus = null;
    State.providerPrivateSignedUrlRevoke = null;
    renderAll();
    setBusy(elements.providerPrivateSignedUrlPrepare, true, 'Prepare Provider-Private Receipt');
    try {
        State.providerPrivateSignedUrlPrepare = await postJson(
            '/handoff/export/download/provider-private-signed-url/prepare',
            providerPrivateSignedUrlPreparePayload(),
        );
        persistProviderPrivateReceiptSnapshot(State.providerPrivateSignedUrlPrepare);
        State.providerPrivateSignedUrlPrepareClientRequestId = null;
        addEvent('Provider-private signed URL receipt prepared with redacted state.');
        renderAll();
    } catch (error) {
        State.providerPrivateSignedUrlError = error.payload || { error_code: 'provider_private_signed_url_prepare_failed', message: error.message };
        addEvent(`Provider-private signed URL prepare blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPrivateSignedUrlPending = false;
        setBusy(elements.providerPrivateSignedUrlPrepare, false, 'Prepare Provider-Private Receipt');
        setGateControls();
    }
}

async function inspectProviderPrivateSignedUrlStatus() {
    if (!canInspectProviderPrivateSignedUrl()) return;
    const receiptId = providerPrivateSignedUrlReceiptId();
    State.providerPrivateSignedUrlPending = true;
    State.providerPrivateSignedUrlError = null;
    renderAll();
    setBusy(elements.providerPrivateSignedUrlStatus, true, 'Inspect Provider-Private Status');
    try {
        State.providerPrivateSignedUrlStatus = await getJson(
            `/handoff/export/download/provider-private-signed-url/status/${encodeURIComponent(receiptId)}`,
        );
        persistProviderPrivateReceiptSnapshot(State.providerPrivateSignedUrlStatus);
        addEvent('Provider-private signed URL status inspected with redacted state.');
        renderAll();
    } catch (error) {
        State.providerPrivateSignedUrlError = error.payload || { error_code: 'provider_private_signed_url_status_failed', message: error.message };
        addEvent(`Provider-private signed URL status blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPrivateSignedUrlPending = false;
        setBusy(elements.providerPrivateSignedUrlStatus, false, 'Inspect Provider-Private Status');
        setGateControls();
    }
}

async function revokeProviderPrivateSignedUrl() {
    if (!canRevokeProviderPrivateSignedUrl()) return;
    State.providerPrivateSignedUrlPending = true;
    State.providerPrivateSignedUrlError = null;
    renderAll();
    setBusy(elements.providerPrivateSignedUrlRevoke, true, 'Revoke Provider-Private Receipt');
    try {
        State.providerPrivateSignedUrlRevoke = await postJson(
            '/handoff/export/download/provider-private-signed-url/revoke',
            providerPrivateSignedUrlRevokePayload(),
        );
        persistProviderPrivateReceiptSnapshot(State.providerPrivateSignedUrlRevoke);
        addEvent('Provider-private signed URL receipt revoked.');
        renderAll();
    } catch (error) {
        State.providerPrivateSignedUrlError = error.payload || { error_code: 'provider_private_signed_url_revoke_failed', message: error.message };
        addEvent(`Provider-private signed URL revoke blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPrivateSignedUrlPending = false;
        setBusy(elements.providerPrivateSignedUrlRevoke, false, 'Revoke Provider-Private Receipt');
        setGateControls();
    }
}

async function submitProviderPublicUrlPrepare(event) {
    event.preventDefault();
    if (!canPrepareProviderPublicUrl()) return;
    State.providerPublicUrlPending = true;
    State.providerPublicUrlError = null;
    State.providerPublicUrlStatus = null;
    State.providerPublicUrlRevoke = null;
    renderAll();
    setBusy(elements.providerPublicUrlPrepare, true, 'Prepare Provider-Public Receipt');
    try {
        State.providerPublicUrlPrepare = await postJson(
            '/handoff/export/download/provider-public-url/prepare',
            providerPublicUrlPreparePayload(),
        );
        State.providerPublicUrlPrepareClientRequestId = null;
        addEvent('Provider-public URL receipt prepared with redacted state only.');
        renderAll();
    } catch (error) {
        State.providerPublicUrlError = error.payload || { error_code: 'provider_public_url_prepare_failed', message: error.message };
        addEvent(`Provider-public URL prepare blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPublicUrlPending = false;
        setBusy(elements.providerPublicUrlPrepare, false, 'Prepare Provider-Public Receipt');
        setGateControls();
    }
}

async function inspectProviderPublicUrlStatus() {
    if (!canInspectProviderPublicUrl()) return;
    const receiptId = providerPublicUrlReceiptId();
    State.providerPublicUrlPending = true;
    State.providerPublicUrlError = null;
    renderAll();
    setBusy(elements.providerPublicUrlStatus, true, 'Inspect Provider-Public Status');
    try {
        State.providerPublicUrlStatus = await getJson(
            `/handoff/export/download/provider-public-url/status/${encodeURIComponent(receiptId)}`,
        );
        addEvent('Provider-public URL status inspected with redacted state only.');
        renderAll();
    } catch (error) {
        State.providerPublicUrlError = error.payload || { error_code: 'provider_public_url_status_failed', message: error.message };
        addEvent(`Provider-public URL status blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPublicUrlPending = false;
        setBusy(elements.providerPublicUrlStatus, false, 'Inspect Provider-Public Status');
        setGateControls();
    }
}

async function revokeProviderPublicUrl() {
    if (!canRevokeProviderPublicUrl()) return;
    State.providerPublicUrlPending = true;
    State.providerPublicUrlError = null;
    renderAll();
    setBusy(elements.providerPublicUrlRevoke, true, 'Revoke Provider-Public Receipt');
    try {
        State.providerPublicUrlRevoke = await postJson(
            '/handoff/export/download/provider-public-url/revoke',
            providerPublicUrlRevokePayload(),
        );
        addEvent('Provider-public URL receipt revoked.');
        renderAll();
    } catch (error) {
        State.providerPublicUrlError = error.payload || { error_code: 'provider_public_url_revoke_failed', message: error.message };
        addEvent(`Provider-public URL revoke blocked: ${error.message}`);
        renderAll();
    } finally {
        State.providerPublicUrlPending = false;
        setBusy(elements.providerPublicUrlRevoke, false, 'Revoke Provider-Public Receipt');
        setGateControls();
    }
}

async function loadDatasetVersionCandidates() {
    try {
        State.datasetVersionCandidates = await getJson('/dataset-version-candidates');
        State.datasetVersionCandidateError = null;
        addEvent(`Loaded ${State.datasetVersionCandidates.candidate_count || 0} APS-derived DatasetVersion candidate(s).`);
        return true;
    } catch (error) {
        State.datasetVersionCandidateError = error.message;
        addEvent(`DatasetVersion candidate lookup blocked: ${error.message}`);
        return false;
    }
}

async function loadApsContentDocumentCandidates() {
    try {
        State.apsContentDocumentCandidates = await getJson('/aps-content-document-candidates');
        State.apsContentDocumentCandidateError = null;
        addEvent(`Loaded ${State.apsContentDocumentCandidates.candidate_count || 0} APS content document candidate(s).`);
        return true;
    } catch (error) {
        State.apsContentDocumentCandidateError = error.message;
        addEvent(`APS content document lookup blocked: ${error.message}`);
        return false;
    }
}

async function init() {
    try {
        State.bootstrap = await getJson('/bootstrap');
        await loadDatasetVersionCandidates();
        await loadApsContentDocumentCandidates();
        const sessionRecovered = await recoverSessionFromStorage();
        if (!sessionRecovered) {
            restoreGateBDraftSnapshot();
        }
        restoreProviderPrivateReceiptSnapshot();
        renderUnavailable(State.bootstrap.unavailable_gate_labels);
        renderAuthority(State.bootstrap.authority_rail);
        renderContext();
        addEvent('Workbench bootstrap loaded.');
    } catch (error) {
        addEvent(`Bootstrap failed: ${error.message}`);
        renderUnavailable();
    }
    renderAll();
}

if (elements.themeSelector) {
    applyThemePreference(State.themePreference, { persist: false });
    elements.themeSelector.addEventListener('change', (event) => applyThemePreference(event.target.value));
}

if (systemThemeQuery) {
    systemThemeQuery.addEventListener('change', () => {
        if (State.themePreference === 'system') {
            applyThemePreference('system', { persist: false });
        }
    });
}

elements.stepChips.forEach((chip) => {
    chip.addEventListener('click', () => navigateToStep(chip));
});
elements.intentForm.addEventListener('submit', runPreflightFlow);
elements.intentInput.addEventListener('input', renderSublayerMap);
elements.sourceFieldset.addEventListener('change', (event) => {
    if (event.target?.name === 'source-class') {
        clearRawMixedMaterializationState({ clearAppliedSources: true });
    }
    renderSublayerMap();
    renderAll();
});
[
    elements.rawMixedCorpusBatchId,
    elements.rawMixedManifestRef,
    elements.rawMixedManifestHash,
].forEach((input) => {
    input.addEventListener('input', handleRawMixedMaterializationInputChange);
    input.addEventListener('keydown', preventRawMixedManifestEnterSubmit);
});
elements.rawMixedOperatorConfirmation.addEventListener('change', handleRawMixedMaterializationInputChange);
elements.rawMixedMaterialize.addEventListener('click', materializeRawMixedSources);
elements.datasetVersionIds.addEventListener('input', renderAll);
elements.datasetVersionCandidates.addEventListener('change', renderAll);
elements.apsContentDocumentIds.addEventListener('input', renderAll);
elements.apsContentDocumentCandidates.addEventListener('change', renderAll);
elements.gateBSubmit.addEventListener('click', commitGateB);
elements.gateCPreview.addEventListener('click', previewGateC);
elements.gateCCommit.addEventListener('click', commitGateC);
elements.planPreview.addEventListener('click', previewPlan);
elements.planReject.addEventListener('click', () => revisePlan('reject_current_preview'));
elements.planRequestRevision.addEventListener('click', () => revisePlan('request_revision'));
elements.planApprove.addEventListener('click', approvePlan);
elements.executionSelect.addEventListener('click', selectExecution);
elements.executionStart.addEventListener('click', startExecution);
elements.resultReviewRefresh.addEventListener('click', refreshSessionSummary);
elements.resultStatusInspect.addEventListener('click', inspectResultStatus);
elements.resultReviewForm.addEventListener('submit', submitResultReview);
elements.packageReviewPreviewInspect.addEventListener('click', inspectPackageReviewPreview);
elements.packageConstructionCommit.addEventListener('click', commitPackageConstruction);
elements.packageReviewSubmitForm.addEventListener('submit', submitPackageReview);
elements.handoffExportPrepareForm.addEventListener('submit', submitHandoffExportPrepare);
elements.apsHandoffDispatchForm.addEventListener('submit', submitApsHandoffDispatch);
elements.externalExportDownloadPrepareForm.addEventListener('submit', submitExternalExportDownloadPrepare);
elements.externalExportDownloadDeliveryForm.addEventListener('submit', submitExternalExportDownloadDelivery);
elements.externalExportDownloadSignedReferenceForm.addEventListener('submit', submitExternalExportDownloadSignedReference);
elements.externalExportDownloadSignedReferenceUse.addEventListener('click', useExternalExportDownloadSignedReference);
elements.providerPrivateSignedUrlForm.addEventListener('submit', submitProviderPrivateSignedUrlPrepare);
elements.providerPrivateSignedUrlStatus.addEventListener('click', inspectProviderPrivateSignedUrlStatus);
elements.providerPrivateSignedUrlRevoke.addEventListener('click', revokeProviderPrivateSignedUrl);
elements.providerPublicUrlForm.addEventListener('submit', submitProviderPublicUrlPrepare);
elements.providerPublicUrlStatus.addEventListener('click', inspectProviderPublicUrlStatus);
elements.providerPublicUrlRevoke.addEventListener('click', revokeProviderPublicUrl);
elements.resultReviewDecision.addEventListener('change', setGateControls);
elements.resultReviewNotes.addEventListener('input', setGateControls);
elements.packageReviewSubmitDecision.addEventListener('change', setGateControls);
elements.packageReviewSubmitNotes.addEventListener('input', setGateControls);
elements.handoffExportPrepareDecision.addEventListener('change', setGateControls);
elements.handoffExportPrepareNotes.addEventListener('input', setGateControls);
elements.materialFilter.addEventListener('input', (event) => {
    State.materialFilter = event.target.value;
    renderMaterialLedger();
});
elements.materialLedgerBody.addEventListener('change', (event) => {
    const row = event.target.closest('tr[data-candidate-id]');
    if (row) {
        syncDecisionStateFromRow(row);
        renderSublayerMap();
    }
});
elements.materialLedgerBody.addEventListener('input', (event) => {
    const row = event.target.closest('tr[data-candidate-id]');
    if (row) {
        syncDecisionStateFromRow(row);
        renderSublayerMap();
    }
});

init();

(function sourceIntakeRenderedControls() {
    const sourceIntakeApiRoot = '/api/v1/layer3';
    const sourceIntakeState = {
        latestRecordId: null,
        pendingUpload: false,
        pendingGateB: false,
        latestPreview: null,
        gateBClientRequestId: null,
        committedPreviewId: null,
    };
    const byId = (id) => document.getElementById(id);
    const escapeSourceIntakeText = (value) => String(value ?? '').replace(/[&<>"]/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
    }[char]));

    function setSourceIntakeStatus(message, state = 'idle') {
        const status = byId('source-intake-status');
        if (!status) return;
        status.textContent = message;
        status.dataset.state = state;
    }

    function setSourceIntakeGateBStatus(message, state = 'idle') {
        const status = byId('source-intake-gate-b-status');
        if (!status) return;
        status.textContent = message;
        status.dataset.state = state;
    }

    async function sourceIntakeJson(response) {
        const text = await response.text();
        let body = null;
        if (text) {
            try {
                body = JSON.parse(text);
            } catch (error) {
                throw new Error(`Source intake API returned non-JSON response (${response.status}).`);
            }
        }
        if (!response.ok) {
            const message = body?.detail || body?.message || `Source intake API failed (${response.status}).`;
            throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
        }
        return body;
    }

    function sourceIntakeFreshnessIso(rawValue) {
        if (!rawValue) return '';
        const parsed = new Date(rawValue);
        return Number.isNaN(parsed.getTime()) ? rawValue : parsed.toISOString();
    }

    function sourceIntakeGateBDecisionBasis(candidate) {
        return {
            source_ref: candidate.source_ref,
            query_basis: candidate.query_basis,
            provenance_ref: candidate.provenance_ref,
            source_identity: candidate.source_identity,
            source_provenance: candidate.source_provenance,
            payload: candidate.payload,
            load_summary: candidate.load_summary,
        };
    }

    function sourceIntakeGateBPayload(preview) {
        const candidate = preview?.material_candidate;
        if (!candidate?.candidate_id || !preview?.material_preview_id || !preview?.material_preview_hash) {
            throw new Error('Source intake Gate B admission requires a complete server preview candidate.');
        }
        if (!sourceIntakeState.gateBClientRequestId) {
            sourceIntakeState.gateBClientRequestId = requestId();
        }
        return {
            schema_id: 'layer3.gate_b_decision_request.v1',
            client_request_id: sourceIntakeState.gateBClientRequestId,
            material_preview_id: preview.material_preview_id,
            material_preview_hash: preview.material_preview_hash,
            candidate_decisions: [
                {
                    candidate_id: candidate.candidate_id,
                    decision: 'approved',
                    operator_reason: 'Rendered source-intake Gate B admission from server preview.',
                    decision_basis: sourceIntakeGateBDecisionBasis(candidate),
                },
            ],
            commit_reason: 'source_intake_gate_b_rendered_admission',
            actor: 'operator',
        };
    }

    function renderSourceIntakeGateBAdmission(payload) {
        const candidate = payload.material_candidate || {};
        return `
            <div class="source-intake-gate-b-admission">
                <div>
                    <h4>Gate B admission candidate</h4>
                    <p>This control commits exactly the server-previewed source-intake material candidate through the existing Gate B API.</p>
                </div>
                <ul class="source-intake-proof-list">
                    <li><strong>candidate:</strong> ${escapeSourceIntakeText(candidate.candidate_id || 'missing')}</li>
                    <li><strong>preview:</strong> ${escapeSourceIntakeText(payload.material_preview_id || 'missing')}</li>
                    <li><strong>hash:</strong> ${escapeSourceIntakeText(payload.material_preview_hash || 'missing')}</li>
                </ul>
                <button class="primary-btn" id="source-intake-gate-b-submit" type="button">Commit Preview To Gate B</button>
            </div>`;
    }

    function renderSourceIntakeInventory(payload) {
        const list = byId('source-intake-inventory-list');
        if (!list) return;
        const records = Array.isArray(payload?.records) ? payload.records : [];
        if (!records.length) {
            list.textContent = 'No durable source-intake records returned.';
            return;
        }
        list.innerHTML = records.map((record) => {
            const recordId = record.source_intake_record_id || record.record_id || '';
            const label = record.source_label || record.original_filename || 'Unlabeled source';
            const mediaType = record.media_type || record.declared_media_type || record.detected_media_type || 'media type unavailable';
            const byteSize = record.content_size_bytes ?? record.byte_size ?? record.content_length ?? 'unknown';
            const createdAt = record.created_at || record.freshness_timestamp || 'timestamp unavailable';
            return `
                <article class="source-intake-inventory-item">
                    <div>
                        <strong>${escapeSourceIntakeText(label)}</strong>
                        <div class="source-intake-meta">
                            <span>${escapeSourceIntakeText(recordId)}</span>
                            <span>${escapeSourceIntakeText(mediaType)}</span>
                            <span>${escapeSourceIntakeText(byteSize)} bytes</span>
                            <span>${escapeSourceIntakeText(createdAt)}</span>
                        </div>
                    </div>
                    <button class="secondary-btn source-intake-preview-button" type="button" data-source-intake-record-id="${escapeSourceIntakeText(recordId)}">Preview</button>
                </article>
            `;
        }).join('');
    }

    async function refreshSourceIntakeInventory() {
        setSourceIntakeStatus('Refreshing durable source-intake inventory...', 'busy');
        const payload = await sourceIntakeJson(await fetch(`${sourceIntakeApiRoot}/source/intake/inventory?limit=10`));
        renderSourceIntakeInventory(payload);
        setSourceIntakeStatus('Inventory refreshed from server-authoritative records.', 'ok');
        return payload;
    }

    async function uploadSourceIntake(event) {
        event.preventDefault();
        const form = event.currentTarget;
        const fileInput = byId('source-intake-file');
        if (!fileInput?.files?.length) {
            setSourceIntakeStatus('Select a file before upload.', 'error');
            return;
        }
        if (sourceIntakeState.pendingUpload) {
            setSourceIntakeStatus('Upload already in progress; wait for the current source-intake request to finish.', 'busy');
            return;
        }
        const submitButton = byId('source-intake-upload-submit');
        sourceIntakeState.pendingUpload = true;
        if (submitButton) submitButton.disabled = true;
        const formData = new FormData(form);
        try {
            if (!String(formData.get('client_request_id') || '').trim()) {
                formData.set('client_request_id', `source-intake-ui-${Date.now()}`);
            }
            const freshness = sourceIntakeFreshnessIso(formData.get('freshness_timestamp'));
            if (freshness) {
                formData.set('freshness_timestamp', freshness);
            } else {
                formData.delete('freshness_timestamp');
            }
            setSourceIntakeStatus('Uploading source intake through existing durable API...', 'busy');
            const payload = await sourceIntakeJson(await fetch(`${sourceIntakeApiRoot}/source/intake/upload`, {
                method: 'POST',
                body: formData,
            }));
            sourceIntakeState.latestRecordId = payload?.source_intake_record_id || null;
            setSourceIntakeStatus(`Source intake recorded: ${sourceIntakeState.latestRecordId || 'record id unavailable'}.`, 'ok');
            try {
                await refreshSourceIntakeInventory();
                setSourceIntakeStatus(`Source intake recorded: ${sourceIntakeState.latestRecordId || 'record id unavailable'}. Inventory refreshed.`, 'ok');
            } catch (refreshError) {
                setSourceIntakeStatus(`Source intake recorded: ${sourceIntakeState.latestRecordId || 'record id unavailable'}. Inventory refresh failed: ${refreshError.message}`, 'error');
            }
        } finally {
            sourceIntakeState.pendingUpload = false;
            if (submitButton) submitButton.disabled = false;
        }
    }

    async function previewSourceIntake(recordId) {
        const panel = byId('source-intake-preview-panel');
        if (!recordId || !panel) return;
        setSourceIntakeStatus('Requesting bounded server preview...', 'busy');
        const payload = await sourceIntakeJson(await fetch(`${sourceIntakeApiRoot}/source/intake/${encodeURIComponent(recordId)}/preview?max_chars=1000`));
        sourceIntakeState.latestPreview = payload;
        sourceIntakeState.gateBClientRequestId = null;
        const candidate = payload?.material_candidate || {};
        const previewText = candidate.preview_text || payload?.preview_text || payload?.text_preview || payload?.content_preview || '';
        panel.innerHTML = `
            <h3>Bounded text preview</h3>
            <div class="source-intake-meta">
                <span>${escapeSourceIntakeText(recordId)}</span>
                <span>${escapeSourceIntakeText(candidate.media_type || payload?.declared_media_type || payload?.detected_media_type || 'media type unavailable')}</span>
                <span>${escapeSourceIntakeText(candidate.preview_truncated || payload?.partial_retrieval ? 'truncated' : 'not truncated')}</span>
            </div>
            <pre class="source-intake-preview-text">${escapeSourceIntakeText(previewText || 'No preview text returned.')}</pre>
            ${renderSourceIntakeGateBAdmission(payload)}
        `;
        setSourceIntakeStatus('Bounded preview returned by existing source-intake API.', 'ok');
        setSourceIntakeGateBStatus('Gate B admission is ready for the server-previewed material candidate.', 'idle');
    }

    async function submitSourceIntakeGateB() {
        const preview = sourceIntakeState.latestPreview;
        if (!preview) {
            setSourceIntakeGateBStatus('Gate B admission requires an active source-intake preview.', 'error');
            return;
        }
        if (sourceIntakeState.pendingGateB) {
            setSourceIntakeGateBStatus('Gate B admission is already in progress.', 'busy');
            return;
        }
        if (State.gateB?.session_id && sourceIntakeState.committedPreviewId === preview.material_preview_id) {
            setSourceIntakeGateBStatus(`Gate B already committed session ${State.gateB.session_id} for this preview.`, 'ok');
            return;
        }
        const button = byId('source-intake-gate-b-submit');
        try {
            sourceIntakeState.pendingGateB = true;
            if (button) setBusy(button, true, 'Commit Preview To Gate B');
            setSourceIntakeGateBStatus('Committing server-previewed source-intake candidate to Gate B...', 'busy');
            State.gateB = await postJson('/gate-b/decision', sourceIntakeGateBPayload(preview));
            State.materialPreview = {
                schema_id: preview.schema_id,
                material_preview_id: preview.material_preview_id,
                material_preview_hash: preview.material_preview_hash,
                source_intake_record_id: preview.source_intake_record_id,
                material_candidates: [preview.material_candidate],
                partial_retrieval: preview.partial_retrieval || false,
            };
            State.gateC = null;
            State.planPreview = null;
            State.planApproval = null;
            State.planRevision = null;
            clearResultReviewState();
            persistSessionRecoveryAnchor('source_intake_gate_b_commit');
            sourceIntakeState.committedPreviewId = preview.material_preview_id;
            addEvent(`Source intake Gate B committed session ${State.gateB.session_id}.`);
            setSourceIntakeGateBStatus(`Gate B committed session ${State.gateB.session_id} from source-intake preview.`, 'ok');
            renderAll();
            setGateControls();
        } catch (error) {
            const detail = error.payload?.detail;
            const errorMessage = typeof detail === 'string' ? detail : detail?.message || error.message;
            const errorCodeValue = error.payload?.error_code || detail?.error_code || detail?.code;
            const errorCode = errorCodeValue ? ` (${errorCodeValue})` : '';
            setSourceIntakeGateBStatus(`Gate B admission blocked: ${errorMessage}${errorCode}`, 'error');
            addEvent(`Source intake Gate B blocked: ${errorMessage}${errorCode}`);
        } finally {
            sourceIntakeState.pendingGateB = false;
            if (button) setBusy(button, false, 'Commit Preview To Gate B');
        }
    }

    function bindSourceIntakeControls() {
        const panel = byId('source-intake-rendered-controls');
        if (!panel) return;
        const form = byId('source-intake-upload-form');
        const refresh = byId('source-intake-refresh');
        form?.addEventListener('submit', (event) => {
            uploadSourceIntake(event).catch((error) => setSourceIntakeStatus(error.message, 'error'));
        });
        refresh?.addEventListener('click', () => {
            refreshSourceIntakeInventory().catch((error) => setSourceIntakeStatus(error.message, 'error'));
        });
        panel.addEventListener('click', (event) => {
            const target = event.target instanceof Element ? event.target : null;
            const button = target?.closest('.source-intake-preview-button');
            const recordId = button?.getAttribute('data-source-intake-record-id');
            if (recordId) {
                previewSourceIntake(recordId).catch((error) => setSourceIntakeStatus(error.message, 'error'));
            }
            if (target?.closest('#source-intake-gate-b-submit')) {
                submitSourceIntakeGateB();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindSourceIntakeControls);
    } else {
        bindSourceIntakeControls();
    }
}());
