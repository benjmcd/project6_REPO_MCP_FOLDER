const API_ROOT = '/api/v1/layer3';
const THEME_STORAGE_KEY = 'nrc_aps_review_theme';
const LAYER3_THEME_STORAGE_KEY = 'layer3_workbench_theme';

const State = {
    bootstrap: null,
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
    gateBDecisions: {},
    materialFilter: '',
    events: [],
    themePreference: document.documentElement.dataset.themePreference || 'system',
};

const elements = {
    themeSelector: document.getElementById('theme-selector'),
    authorityRail: document.getElementById('authority-rail'),
    sublayerMapPanel: document.getElementById('sublayer-map-panel'),
    intentForm: document.getElementById('intent-form'),
    intentInput: document.getElementById('layer3-intent'),
    sourceFieldset: document.getElementById('source-fieldset'),
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
    handoffExportPrepareForm: document.getElementById('handoff-export-prepare-form'),
    handoffExportPreparePanel: document.getElementById('handoff-export-prepare-panel'),
    handoffExportPrepareDecision: document.getElementById('handoff-export-prepare-decision'),
    handoffExportPrepareNotes: document.getElementById('handoff-export-prepare-notes'),
    handoffExportPrepareSubmit: document.getElementById('handoff-export-prepare-submit'),
    apsHandoffDispatchForm: document.getElementById('aps-handoff-dispatch-form'),
    apsHandoffDispatchPanel: document.getElementById('aps-handoff-dispatch-panel'),
    apsHandoffDispatchSubmit: document.getElementById('aps-handoff-dispatch-submit'),
    externalExportDownloadPrepareForm: document.getElementById('external-export-download-prepare-form'),
    externalExportDownloadPreparePanel: document.getElementById('external-export-download-prepare-panel'),
    externalExportDownloadPrepareSubmit: document.getElementById('external-export-download-prepare-submit'),
    externalExportDownloadDeliveryForm: document.getElementById('external-export-download-delivery-form'),
    externalExportDownloadDeliveryPanel: document.getElementById('external-export-download-delivery-panel'),
    externalExportDownloadDeliverySubmit: document.getElementById('external-export-download-delivery-submit'),
    contextList: document.getElementById('context-list'),
    eventList: document.getElementById('event-list'),
    unavailableList: document.getElementById('unavailable-list'),
    stepChips: Array.from(document.querySelectorAll('.step-chip[data-step-target]')),
};

const systemThemeQuery = typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-color-scheme: dark)')
    : null;
const TERMINAL_PASS_STATUSES = new Set(['completed', 'completed_with_warnings', 'failed']);
const RESULT_REVIEW_DECISIONS_REQUIRING_NOTES = new Set(['changes_requested', 'rejected', 'blocked']);
const PACKAGE_REVIEW_DECISIONS_REQUIRING_NOTES = new Set(['changes_requested', 'rejected', 'blocked']);
const HANDOFF_EXPORT_PREPARE_DECISIONS_REQUIRING_NOTES = new Set(['hold', 'decline', 'blocked']);
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

function isValidThemePreference(value) {
    return isSharedThemePreference(value) || value === 'workbench';
}

function resolveTheme(preference) {
    if (preference === 'light' || preference === 'dark' || preference === 'workbench') return preference;
    return systemThemeQuery?.matches ? 'dark' : 'light';
}

function applyThemePreference(preference, { persist = true } = {}) {
    const normalized = isValidThemePreference(preference) ? preference : 'system';
    document.documentElement.dataset.themePreference = normalized;
    document.documentElement.dataset.theme = resolveTheme(normalized);
    State.themePreference = normalized;
    if (elements.themeSelector) {
        elements.themeSelector.value = normalized;
    }
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

function selectedSourceClassLabels() {
    return Array.from(document.querySelectorAll('input[name="source-class"]'))
        .filter((input) => input.checked)
        .map((input) => input.closest('label')?.textContent || input.value)
        .map((label) => label.replace(/\s+/g, ' ').trim())
        .filter(Boolean);
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
}

function clearResultReviewState({ keepSummary = false } = {}) {
    if (!keepSummary) {
        State.sessionSummary = null;
    }
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
    const selection = summary.execution_selection || {};
    const startState = summary.analysis_execution_start || {};
    const statusBody = State.resultStatus || {};
    const reviewBody = State.resultReview || {};
    const passRunIds = Array.isArray(selection.pass_run_ids) ? selection.pass_run_ids : [];
    const firstPassRunId = passRunIds[0] || startState.pass_run_id || statusBody.pass_run_id || reviewBody.pass_run_id || null;
    const passRunStatuses = selection.pass_run_statuses || {};
    const passStatus = statusBody.pass_run_status || startState.pass_run_status || passRunStatuses[firstPassRunId] || null;
    const analysisRunIds = Array.isArray(selection.analysis_run_ids) ? selection.analysis_run_ids : [];
    const analysisRunId = statusBody.analysis_run_id || startState.analysis_run_id || analysisRunIds[0] || reviewBody.analysis_run_id || null;
    const previewIdentity = statusBody.preview_identity || reviewBody.preview_identity || {};
    const previewId = selection.source_preview_id || startState.source_preview_id || previewIdentity.preview_id || null;
    const previewHash = selection.source_preview_hash || startState.source_preview_hash || previewIdentity.preview_hash || null;
    const analysisPlanId = selection.analysis_plan_id || startState.analysis_plan_id || statusBody.analysis_plan_id || reviewBody.analysis_plan_id || null;
    return {
        sessionId: summary.session_id || currentSessionId(),
        analysisPlanId,
        passRunId: firstPassRunId,
        previewId,
        previewHash,
        analysisRunId,
        passStatus,
        selected: selection.selected === true && Boolean(firstPassRunId),
        terminal: TERMINAL_PASS_STATUSES.has(passStatus),
        executionStarted: Boolean(selection.execution_started || startState.pass_run_id || statusBody.execution_started),
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

function canRefreshSessionSummary() {
    return Boolean(
        currentSessionId()
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
            package_review_submit_enabled: true,
            handoff_enabled: false,
            export_enabled: false,
            downstream_unavailable: construction.downstream_unavailable,
        };
    }
    if (State.sessionSummary?.package_review_submit) {
        return State.sessionSummary.package_review_submit;
    }
    return null;
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
    return State.apsHandoffDispatch || State.sessionSummary?.aps_handoff_dispatch || null;
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

function handoffExportEnvelopeRef(handoff = State.sessionSummary?.handoff_export_prepare || handoffExportPrepareState() || {}) {
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
    const preview = State.packageReviewPreview || {};
    const submit = packageReviewSubmitState() || {};
    const notes = elements.packageReviewSubmitNotes.value.trim();
    return Boolean(
        hasResultAuthorityIdentity(authority)
        && authority.selected
        && authority.terminal
        && review?.review_record_ref
        && preview.package_review_preview_hash
        && submit.package_review_submit_enabled === true
        && submit.reconciliation_record_id
        && packageOutputPackageIds().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
        && packagePayloadHashes().length === PACKAGE_REVIEW_PACKAGE_KINDS.length
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
    const aps = State.sessionSummary?.aps_handoff_dispatch || {};
    const handoff = State.sessionSummary?.handoff_export_prepare || handoffExportPrepareState() || {};
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
    const aps = State.sessionSummary?.aps_handoff_dispatch || apsHandoffDispatchState() || {};
    const handoff = State.sessionSummary?.handoff_export_prepare || handoffExportPrepareState() || {};
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
    const handoff = State.sessionSummary?.handoff_export_prepare || handoffExportPrepareState() || {};
    const aps = State.sessionSummary?.aps_handoff_dispatch || apsHandoffDispatchState() || {};
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
        recordedApprovedResultReview()
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
    return [
        candidate.candidate_id,
        candidate.source_label,
        candidate.source_class,
        candidate.owner_service_source_shape,
        candidate.planning_shape_family,
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
    const hasRoutedInputs = typingObjects.length > 0 || persistedAnalysisSetObjects.length > 0;
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
        <div class="flow-object-list diagram-chip-grid" data-field-label="${escapeHtml(fieldLabel)}" data-object-count="${items.length}">
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
        </div>
    `;
}

function renderModalityBucket(bucket) {
    const { modality, meta, objects, state } = bucket;
    return `
        <section class="modality-bucket modality-${escapeHtml(modality)} viz-state-${escapeHtml(state)}" aria-label="${escapeHtml(meta.label)}" data-modality="${escapeHtml(modality)}" data-object-count="${objects.length}">
            <div class="modality-heading">
                <span class="modality-dot" aria-hidden="true"></span>
                <h4>${escapeHtml(meta.label)}</h4>
                <span>${objects.length} objects</span>
            </div>
            <div class="modality-route-label" aria-hidden="true">Object bank / grouping field</div>
            ${renderFlowObjects(objects, meta.empty, { fieldLabel: `${meta.label} object bank`, slotCount: 3 })}
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
            <div class="plane-flow">
                <section class="plane-column plane-inputs">
                    <h5>Input objects</h5>
                    <div class="plane-input-group">
                        <span class="plane-bracket" aria-hidden="true"></span>
                        ${renderFlowObjects(inputs, 'No live input object is available for this plane.', { fieldLabel: `${meta.label} input objects`, slotCount: 3 })}
                    </div>
                </section>
                <span class="plane-arrow plane-arrow-process" aria-hidden="true"></span>
                <section class="plane-process" aria-label="${escapeHtml(meta.plane)} process status">
                    <h5>Process / Status</h5>
                    <ul>${processBody}</ul>
                </section>
                <span class="plane-arrow plane-arrow-output" aria-hidden="true"></span>
                <section class="plane-column plane-outputs">
                    <h5>Output cards</h5>
                    ${renderFlowObjects(outputs.map((card) => ({
                        id: card.secondary,
                        label: card.label,
                        kind: 'output card',
                        primary: card.primary,
                        secondary: card.secondary,
                        badge: card.badge,
                        modality,
                        live: true,
                    })), 'No live output, insight, fact, or data card has been produced for this plane.', { fieldLabel: `${meta.label} output field`, slotCount: 6 })}
                </section>
            </div>
        </article>
    `;
}

function renderSublayerMap() {
    if (!elements.sublayerMapPanel) return;
    const model = currentSublayerVisualizationModel();
    const rail = model.rail;
    const sourceLabels = model.sourceLabels;

    elements.sublayerMapPanel.dataset.vizState = `${model.threeA.state}|${model.threeB.state}|${model.threeC.state}`;
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
                ${renderFlowObjects(model.threeA.objects, 'No material preview, session entry, or material ledger object is currently loaded.', { fieldLabel: '3A material ledger object field', slotCount: 6 })}
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
                <div class="modality-buckets">
                    ${model.threeB.buckets.map((bucket) => renderModalityBucket(bucket)).join('')}
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
                <div class="analysis-planes">
                    ${model.threeC.planes.map((plane) => renderAnalysisPlane(plane)).join('')}
                </div>
            </section>
        </section>
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
        elements.materialLedgerBody.innerHTML = `<tr><td colspan="6" class="empty-cell">${escapeHtml(message)}</td></tr>`;
        return;
    }
    elements.materialLedgerBody.innerHTML = visible.map((candidate) => {
        const currentDecision = decisionState(candidate.candidate_id);
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
    for (const candidate of State.materialPreview?.material_candidates || []) {
        State.gateBDecisions[candidate.candidate_id] = {
            decision: 'approved',
            operator_reason: '',
        };
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
    return Boolean(State.gateB?.session_id && State.gateC?.authority_rail?.typing_status === 'committed');
}

function canPlanApprove() {
    return Boolean(
        State.gateB?.session_id
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
        State.gateB?.session_id
        && State.planPreview?.schema_id === 'layer3.plan_preview_result.v1'
        && State.planPreview?.preview_id
        && State.planPreview?.preview_hash
        && !State.planApproval
        && !State.planRevision
        && !State.planRevisionPending
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
    if (State.resultReviewPending) {
        return { label: 'result_review_ui_recording', pill: 'preview', message: 'Recording one bounded operator decision.' };
    }
    if (recordedResultReview()) {
        return { label: 'result_review_ui_recorded', pill: 'ok', message: 'Server state already contains a result-review record.' };
    }
    if (State.resultReviewError || State.resultStatusError) {
        return { label: 'result_review_ui_blocked', pill: 'blocked', message: 'Server authority rejected or blocked the latest result-review action.' };
    }
    if (!authority.sessionId) {
        return { label: 'result_review_ui_unavailable', pill: 'blocked', message: 'No Layer 3 session id is available.' };
    }
    if (!State.sessionSummary) {
        return { label: 'result_review_ui_unavailable', pill: 'blocked', message: 'Refresh session state before inspecting result status.' };
    }
    if (!hasResultAuthorityIdentity(authority) || !authority.selected) {
        return { label: 'result_review_ui_waiting_for_selection', pill: 'blocked', message: 'Server summary has no selected pass authority.' };
    }
    if (!authority.terminal) {
        return { label: 'result_review_ui_waiting_for_execution_start', pill: 'blocked', message: 'Selected pass is not terminal.' };
    }
    if (State.resultStatus?.result_status_available === true) {
        return { label: 'result_review_ui_review_ready', pill: 'ok', message: 'Result/status authority is available for one selected terminal pass.' };
    }
    if (State.resultStatus) {
        return { label: 'result_review_ui_blocked', pill: 'blocked', message: 'Result/status authority is not available for review.' };
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

function renderResultReviewPanel() {
    const authority = selectedResultAuthority();
    const statusBody = State.resultStatus || {};
    const reviewState = recordedResultReview();
    const panelState = resultReviewPanelState(authority);
    const metadata = statusBody.output_metadata_summary || {};
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
        return { label: State.packageReviewPreview.next_state || 'package_review_preview_ready', pill: 'ok', message: 'Package-review preview is available and can be committed as a package set.' };
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
    const handoff = State.sessionSummary?.handoff_export_prepare || handoffExportPrepareState() || {};
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
    const handoff = State.sessionSummary?.handoff_export_prepare || handoffExportPrepareState() || {};
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
    const aps = State.sessionSummary?.aps_handoff_dispatch || apsHandoffDispatchState() || {};
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
    const aps = State.sessionSummary?.aps_handoff_dispatch || apsHandoffDispatchState() || {};
    const handoff = State.sessionSummary?.handoff_export_prepare || handoffExportPrepareState() || {};
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
    if (stateName === 'external_export_download_prepared') {
        return { label: 'external_export_download_delivery_ui_unavailable', pill: 'blocked', message: 'Recorded readiness is present, but the server summary is missing required delivery basis.' };
    }
    return { label: 'external_export_download_delivery_ui_unavailable', pill: 'blocked', message: 'Prepare external export/download readiness before delivery.' };
}

function renderExternalExportDownloadDeliveryPanel() {
    const external = externalExportDownloadPrepareState() || {};
    const panelState = externalExportDownloadDeliveryPanelState();
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

function setGateControls() {
    const gateCCommitted = State.gateC?.authority_rail?.typing_status === 'committed';
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
        State.sessionSummary?.aps_handoff_dispatch?.available === true
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
        && !State.externalExportDownloadPreparePending
        && !State.externalExportDownloadDeliveryPending
    );
    elements.gateBSubmit.disabled = !(State.materialPreview?.material_candidates || []).length;
    elements.gateCPreview.disabled = !State.gateB?.session_id || gateCCommitted;
    elements.gateCCommit.disabled = !State.gateB?.session_id || gateCCommitted;
    elements.planPreview.disabled = !canPlanPreview() || Boolean(State.planApproval) || Boolean(State.planRevision) || State.planRevisionPending;
    elements.planReject.disabled = !canPlanRevise();
    elements.planRequestRevision.disabled = !canPlanRevise();
    elements.planApprove.disabled = !canPlanApprove();
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
    setStepChip(elements.planStep, canPlanPreview());
    setStepChip(elements.executionStep, Boolean(State.sessionSummary?.execution_selection?.selected));
    setStepChip(elements.resultsStep, Boolean(authority.selected && authority.terminal));
    setStepChip(elements.packageStep, isPackageActive());
    setStepChip(elements.handoffStep, isHandoffActive());
}

function renderAll() {
    renderAuthority();
    renderSublayerMap();
    renderUnavailable(currentDownstreamUnavailable());
    renderContext();
    renderMaterialLedger();
    renderGateCPanel();
    renderPlanPanel();
    renderResultReviewPanel();
    renderPackageReviewPreviewPanel();
    renderHandoffExportPreparePanel();
    renderApsHandoffDispatchPanel();
    renderExternalExportDownloadPreparePanel();
    renderExternalExportDownloadDeliveryPanel();
    setGateControls();
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
    const preview = State.packageReviewPreview || {};
    const submit = packageReviewSubmitState() || {};
    const payload = {
        client_request_id: requestId(),
        session_id: authority.sessionId,
        analysis_plan_id: authority.analysisPlanId,
        pass_run_id: authority.passRunId,
        preview_id: authority.previewId,
        preview_hash: authority.previewHash,
        result_review_record_ref: preview.result_review_record_ref || review?.review_record_ref,
        package_review_preview_hash: preview.package_review_preview_hash,
        reconciliation_record_id: submit.reconciliation_record_id,
        output_package_ids: packageOutputPackageIds(),
        payload_hashes: packagePayloadHashes(),
        operator_decision: elements.packageReviewSubmitDecision.value,
        decision_notes: elements.packageReviewSubmitNotes.value.trim(),
        expected_package_kinds: PACKAGE_REVIEW_PACKAGE_KINDS,
    };
    if (authority.analysisRunId) {
        payload.analysis_run_id = authority.analysisRunId;
    }
    return payload;
}

function handoffExportPreparePayload(authority = selectedResultAuthority()) {
    const handoff = State.sessionSummary?.handoff_export_prepare || {};
    const submit = packageReviewSubmitState() || {};
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
        handoff_target: 'internal_export_envelope',
        export_mode: 'prepare_only',
        operator_decision: elements.handoffExportPrepareDecision.value,
        expected_package_kinds: PACKAGE_REVIEW_PACKAGE_KINDS,
    };
    if (notes) {
        payload.decision_notes = notes;
    }
    if (handoff.analysis_run_id || authority.analysisRunId) {
        payload.analysis_run_id = handoff.analysis_run_id || authority.analysisRunId;
    }
    return payload;
}

function apsHandoffDispatchPayload(authority = selectedResultAuthority()) {
    const handoff = State.sessionSummary?.handoff_export_prepare || handoffExportPrepareState() || {};
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
    const aps = State.sessionSummary?.aps_handoff_dispatch || apsHandoffDispatchState() || {};
    const handoff = State.sessionSummary?.handoff_export_prepare || handoffExportPrepareState() || {};
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
        State.resultStatusError = null;
        State.resultReviewError = null;
        State.packageReviewPreviewError = null;
        State.packageConstructionError = null;
        State.packageReviewSubmitError = null;
        State.handoffExportPrepareError = null;
        State.apsHandoffDispatchError = null;
        State.externalExportDownloadPrepareError = null;
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

async function runPreflightFlow(event) {
    event.preventDefault();
    const intent = elements.intentInput.value.trim();
    const sourceClasses = selectedSourceClasses();
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
                query_basis: {
                    terms: termsFromIntent(intent),
                },
            });
        initializeGateBDecisions();
        State.gateB = null;
        State.gateC = null;
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
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
            client_request_id: requestId(),
            preflight_id: State.preflight?.preflight_id,
            source_set_id: State.sourcePreview?.source_set_id,
            material_preview_id: State.materialPreview?.material_preview_id,
            candidate_decisions: decisions,
            commit_reason: 'operator_gate_b_decision',
            actor: 'operator',
        });
        State.gateC = null;
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
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
    if (!State.gateB?.session_id) return;
    if (State.gateC?.authority_rail?.typing_status === 'committed') return;
    setBusy(elements.gateCPreview, true, 'Preview Gate C');
    try {
        State.gateC = await postJson('/gate-c/preview', {
            schema_id: 'layer3.gate_c_preview_request.v1',
            client_request_id: requestId(),
            session_id: State.gateB.session_id,
            commit_typing: false,
        });
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
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
    if (!State.gateB?.session_id) return;
    setBusy(elements.gateCCommit, true, 'Commit Gate C Typing');
    try {
        State.gateC = await postJson('/gate-c/preview', {
            schema_id: 'layer3.gate_c_preview_request.v1',
            client_request_id: requestId(),
            session_id: State.gateB.session_id,
            commit_typing: true,
        });
        State.planPreview = null;
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
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
            session_id: State.gateB.session_id,
            include_exclusions: true,
            preview_scope: 'owner_service_default',
        });
        State.planApproval = null;
        State.planRevision = null;
        clearResultReviewState();
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
            session_id: State.gateB.session_id,
            preview_id: State.planPreview.preview_id,
            preview_hash: State.planPreview.preview_hash,
            operator_confirmation: true,
            approval_scope: 'owner_service_default',
        });
        clearResultReviewState();
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
            session_id: State.gateB.session_id,
            preview_id: State.planPreview.preview_id,
            preview_hash: State.planPreview.preview_hash,
            operator_decision: operatorDecision,
        });
        clearResultReviewState();
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

async function init() {
    try {
        State.bootstrap = await getJson('/bootstrap');
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
elements.sourceFieldset.addEventListener('change', renderSublayerMap);
elements.gateBSubmit.addEventListener('click', commitGateB);
elements.gateCPreview.addEventListener('click', previewGateC);
elements.gateCCommit.addEventListener('click', commitGateC);
elements.planPreview.addEventListener('click', previewPlan);
elements.planReject.addEventListener('click', () => revisePlan('reject_current_preview'));
elements.planRequestRevision.addEventListener('click', () => revisePlan('request_revision'));
elements.planApprove.addEventListener('click', approvePlan);
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
