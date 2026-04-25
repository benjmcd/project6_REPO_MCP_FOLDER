const API_ROOT = '/api/v1/layer3';
const THEME_STORAGE_KEY = 'nrc_aps_review_theme';

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
    gateBDecisions: {},
    materialFilter: '',
    events: [],
    themePreference: document.documentElement.dataset.themePreference || 'system',
};

const elements = {
    themeSelector: document.getElementById('theme-selector'),
    authorityRail: document.getElementById('authority-rail'),
    intentForm: document.getElementById('intent-form'),
    intentInput: document.getElementById('layer3-intent'),
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
    packageReviewPreviewPanel: document.getElementById('package-review-preview-panel'),
    contextList: document.getElementById('context-list'),
    eventList: document.getElementById('event-list'),
    unavailableList: document.getElementById('unavailable-list'),
};

const systemThemeQuery = typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-color-scheme: dark)')
    : null;
const TERMINAL_PASS_STATUSES = new Set(['completed', 'completed_with_warnings', 'failed']);
const RESULT_REVIEW_DECISIONS_REQUIRING_NOTES = new Set(['changes_requested', 'rejected', 'blocked']);

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function isValidThemePreference(value) {
    return value === 'system' || value === 'light' || value === 'dark';
}

function resolveTheme(preference) {
    if (preference === 'light' || preference === 'dark') return preference;
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
            localStorage.setItem(THEME_STORAGE_KEY, normalized);
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
    return State.packageReviewPreview?.authority_rail || State.sessionSummary?.authority_rail || State.resultReview?.authority_rail || State.resultStatus?.authority_rail
        || State.planApproval?.authority_rail || State.planRevision?.authority_rail || State.planPreview?.authority_rail || State.gateC?.authority_rail || State.gateB?.authority_rail
        || State.materialPreview?.authority_rail || State.sourcePreview?.authority_rail || State.preflight?.authority_rail
        || State.bootstrap?.authority_rail;
}

function currentDownstreamUnavailable() {
    return State.packageReviewPreview?.downstream_unavailable
        || State.resultReview?.downstream_unavailable
        || State.resultStatus?.downstream_unavailable
        || State.sessionSummary?.package_review_preview?.downstream_unavailable
        || State.sessionSummary?.execution_result_review?.downstream_unavailable
        || State.sessionSummary?.analysis_execution_start?.downstream_unavailable
        || State.sessionSummary?.downstream_unavailable
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
    return Boolean(currentSessionId() && !State.resultReviewPending && !State.packageReviewPreviewPending);
}

function canInspectResultStatus() {
    const authority = selectedResultAuthority();
    return Boolean(hasResultAuthorityIdentity(authority) && authority.selected && authority.terminal && !State.resultReviewPending && !State.packageReviewPreviewPending);
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
    if (State.packageReviewPreviewPending) {
        return { label: 'package_review_preview_inspecting', pill: 'preview', message: 'Inspecting read-only package-review readiness.' };
    }
    if (State.packageReviewPreview?.package_review_preview_enabled === true) {
        return { label: State.packageReviewPreview.next_state || 'package_review_preview_ready', pill: 'ok', message: 'Read-only package-review preview is available.' };
    }
    if (State.packageReviewPreviewError) {
        return { label: 'package_review_preview_blocked', pill: 'blocked', message: 'Server authority rejected or blocked package-review preview.' };
    }
    if (recordedApprovedResultReview()) {
        return { label: 'package_review_preview_unavailable', pill: 'preview', message: 'Approved result review can be inspected for package-preview readiness.' };
    }
    return { label: 'package_review_preview_unavailable', pill: 'blocked', message: 'Package preview requires an approved selected-pass result review.' };
}

function renderPackageReviewPreviewPanel() {
    const preview = State.packageReviewPreview || {};
    const panelState = packageReviewPanelState();
    const review = recordedApprovedResultReview() || {};
    const compatibility = preview.package_owner_compatibility || {};
    const candidateKinds = Array.isArray(preview.candidate_package_kinds) ? preview.candidate_package_kinds : [];
    const candidateRows = candidateKinds.length
        ? candidateKinds.map((candidate) => `
            <li>
                <code>${escapeHtml(candidate.package_kind)}</code>
                ${candidate.preview_only ? '<span class="status-pill preview">preview only</span>' : ''}
            </li>
        `).join('')
        : '<li>No package candidates loaded.</li>';
    const error = State.packageReviewPreviewError;
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
                <div class="downstream-locks">${renderDownstreamLocks(preview.downstream_unavailable || ['package_commit', 'package_review_submit', 'handoff', 'export'])}</div>
            </section>
            ${renderErrorCard(error)}
        </div>
    `;
}

function setBusy(button, busy, label) {
    button.disabled = busy;
    if (label) {
        button.textContent = busy ? 'Working...' : label;
    }
}

function setStepChip(element, active) {
    element.disabled = !active;
    element.classList.toggle('active', active);
    element.classList.toggle('unavailable', !active);
}

function setGateControls() {
    const gateCCommitted = State.gateC?.authority_rail?.typing_status === 'committed';
    const authority = selectedResultAuthority();
    const reviewRecorded = Boolean(recordedResultReview());
    const resultReviewControlsEnabled = Boolean(State.resultStatus?.result_status_available === true && !reviewRecorded && !State.resultReviewPending && !State.packageReviewPreviewPending);
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
    setStepChip(elements.planStep, canPlanPreview());
    setStepChip(elements.executionStep, Boolean(State.sessionSummary?.execution_selection?.selected));
    setStepChip(elements.resultsStep, Boolean(authority.selected && authority.terminal));
    setStepChip(elements.packageStep, false);
}

function renderAll() {
    renderAuthority();
    renderUnavailable(currentDownstreamUnavailable());
    renderContext();
    renderMaterialLedger();
    renderGateCPanel();
    renderPlanPanel();
    renderResultReviewPanel();
    renderPackageReviewPreviewPanel();
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
    renderAll();
    setBusy(elements.packageReviewPreviewInspect, true, 'Inspect Package Preview');
    try {
        State.packageReviewPreview = await postJson('/package/review/preview', packageReviewPreviewPayload());
        State.packageReviewPreviewError = null;
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

elements.intentForm.addEventListener('submit', runPreflightFlow);
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
elements.resultReviewDecision.addEventListener('change', setGateControls);
elements.resultReviewNotes.addEventListener('input', setGateControls);
elements.materialFilter.addEventListener('input', (event) => {
    State.materialFilter = event.target.value;
    renderMaterialLedger();
});
elements.materialLedgerBody.addEventListener('change', (event) => {
    const row = event.target.closest('tr[data-candidate-id]');
    if (row) {
        syncDecisionStateFromRow(row);
    }
});
elements.materialLedgerBody.addEventListener('input', (event) => {
    const row = event.target.closest('tr[data-candidate-id]');
    if (row) {
        syncDecisionStateFromRow(row);
    }
});

init();
