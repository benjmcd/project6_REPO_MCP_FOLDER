const PAGE_ROUTE = '/review/nrc-aps/candidate-b-trace';
const API_ROOT = '/api/v1/review/nrc-aps/candidate-b-trace';
const TAB_ORDER = ['annotated_pdf', 'summary', 'raw_json', 'raw_markdown'];
const THEME_KEY = 'nrc_aps_review_theme';

const state = {
    manifest: null,
    cachedJson: null,
    cachedMarkdown: null,
    candidateBBundleId: '',
    fixtureId: '',
    tabId: '',
};

const els = {
    themeSelector: document.getElementById('theme-selector'),
    disabledOverlay: document.getElementById('disabled-overlay'),
    disabledTitle: document.getElementById('disabled-title'),
    disabledReason: document.getElementById('disabled-reason'),
    workspace: document.getElementById('candidate-b-trace-workspace'),
    identitySummary: document.getElementById('identity-summary'),
    badgeStrip: document.getElementById('badge-strip'),
    warningList: document.getElementById('warning-list'),
    limitationList: document.getElementById('limitation-list'),
    tabsHeader: document.getElementById('tabs-header'),
    tabContentArea: document.getElementById('tab-content-area'),
};

function readQueryState() {
    const params = new URLSearchParams(window.location.search);
    state.candidateBBundleId = params.get('candidate_b_bundle_id') || '';
    state.fixtureId = params.get('fixture_id') || '';
    state.tabId = params.get('tab') || '';
    if (!TAB_ORDER.includes(state.tabId)) {
        state.tabId = '';
    }
}

function syncQueryState() {
    const params = new URLSearchParams();
    if (state.candidateBBundleId) params.set('candidate_b_bundle_id', state.candidateBBundleId);
    if (state.fixtureId) params.set('fixture_id', state.fixtureId);
    if (state.tabId && state.tabId !== 'summary') params.set('tab', state.tabId);
    const next = params.toString();
    const nextUrl = next ? `${PAGE_ROUTE}?${next}` : PAGE_ROUTE;
    window.history.replaceState({}, '', nextUrl);
}

function setTheme(preference) {
    const prefersDark = typeof window.matchMedia === 'function'
        && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const resolved = preference === 'dark'
        ? 'dark'
        : preference === 'light'
            ? 'light'
            : (prefersDark ? 'dark' : 'light');
    document.documentElement.dataset.themePreference = preference;
    document.documentElement.dataset.theme = resolved;
    try {
        localStorage.setItem(THEME_KEY, preference);
    } catch (error) {
        // no-op
    }
}

async function fetchJson(url) {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
            const payload = await response.json();
            if (payload && payload.detail) {
                detail = String(payload.detail);
            }
        } catch (error) {
            // ignore
        }
        throw new Error(detail);
    }
    return response.json();
}

async function fetchText(url) {
    const response = await fetch(url, { headers: { Accept: 'text/plain' } });
    if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
            const payload = await response.json();
            if (payload && payload.detail) {
                detail = String(payload.detail);
            }
        } catch (error) {
            // ignore
        }
        throw new Error(detail);
    }
    return response.text();
}

function setOverlay(title, message) {
    els.disabledTitle.textContent = title;
    els.disabledReason.textContent = message;
    els.disabledOverlay.classList.remove('hidden');
    els.workspace.classList.add('hidden');
}

function clearOverlay() {
    els.disabledOverlay.classList.add('hidden');
    els.workspace.classList.remove('hidden');
}

function renderIdentitySummary(manifest) {
    const identity = manifest.identity;
    els.identitySummary.innerHTML = `
        <div class="meta-item"><span class="meta-label">Fixture</span><span>${escapeHtml(identity.fixture_id || 'n/a')}</span></div>
        <div class="meta-item"><span class="meta-label">Bundle</span><span>${escapeHtml(identity.bundle_id || 'n/a')}</span></div>
        <div class="meta-item"><span class="meta-label">Candidate B Run</span><span>${escapeHtml(identity.candidate_b_run_id || 'n/a')}</span></div>
        <div class="meta-item"><span class="meta-label">Title</span><span>${escapeHtml(identity.document_title || 'n/a')}</span></div>
        <div class="meta-item"><span class="meta-label">Source</span><span>${escapeHtml(identity.source_file_name || 'n/a')}</span></div>
        <div class="meta-item"><span class="meta-label">Document Ref</span><span>${escapeHtml(identity.document_ref || 'n/a')}</span></div>
    `;
}

function renderBadges(manifest) {
    const summary = manifest.summary;
    const badges = [
        {
            label: 'Processing',
            value: summary.processing_status || 'unknown',
            severity: summary.processing_status === 'succeeded' ? 'success' : 'warning',
        },
        {
            label: 'Decision',
            value: summary.decision_recommendation || 'unknown',
            severity: 'info',
        },
        {
            label: 'Annotated PDF',
            value: summary.annotated_pdf_status || 'missing',
            severity: summary.annotated_pdf_status === 'present' ? 'success' : 'warning',
        },
    ];
    els.badgeStrip.innerHTML = '';
    for (const badge of badges) {
        const item = document.createElement('div');
        item.className = `trace-badge ${badge.severity}`;
        item.innerHTML = `<span>${escapeHtml(badge.label)}</span><strong>${escapeHtml(badge.value)}</strong>`;
        els.badgeStrip.appendChild(item);
    }
}

function renderNoticeList(listEl, items, emptyMessage) {
    listEl.innerHTML = '';
    if (!items.length) {
        const item = document.createElement('li');
        item.className = 'empty';
        item.textContent = emptyMessage;
        listEl.appendChild(item);
        return;
    }
    for (const entry of items) {
        const item = document.createElement('li');
        item.textContent = entry;
        listEl.appendChild(item);
    }
}

function renderTabs(manifest) {
    els.tabsHeader.innerHTML = '';
    for (const tab of manifest.tabs) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `tab-btn${tab.tab_id === state.tabId ? ' active' : ''}`;
        button.textContent = tab.label;
        button.disabled = !tab.available;
        button.addEventListener('click', async () => {
            if (state.tabId === tab.tab_id || !tab.available) {
                return;
            }
            state.tabId = tab.tab_id;
            syncQueryState();
            renderTabs(manifest);
            await renderActiveTab();
        });
        els.tabsHeader.appendChild(button);
    }
}

function renderDefinitionList(data) {
    return Object.entries(data).map(([key, value]) => `
        <dt>${escapeHtml(key)}</dt>
        <dd>${renderScalarValue(value)}</dd>
    `).join('');
}

function renderScalarValue(value) {
    if (value === null || value === undefined || value === '') {
        return 'n/a';
    }
    if (Array.isArray(value) || typeof value === 'object') {
        return `<pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
    }
    return escapeHtml(String(value));
}

function renderSummaryTab(manifest) {
    const summary = manifest.summary;
    els.tabContentArea.innerHTML = `
        <div class="detail-grid">
            <section class="detail-panel">
                <h3>Summary</h3>
                <dl class="detail-list">
                    ${renderDefinitionList({
                        processing_status: summary.processing_status,
                        decision_recommendation: summary.decision_recommendation,
                        page_count: summary.page_count,
                        normalized_char_count: summary.normalized_char_count,
                        struct_tree_state: summary.struct_tree_state,
                        heading_count: summary.heading_count,
                        list_count: summary.list_count,
                        image_count: summary.image_count,
                        table_count: summary.table_count,
                        hidden_text_present: summary.hidden_text_present,
                        annotated_pdf_status: summary.annotated_pdf_status,
                    })}
                </dl>
            </section>
            <section class="detail-panel">
                <h3>Fixture Posture</h3>
                <dl class="detail-list">
                    ${renderDefinitionList({
                        footer_page_numbers: summary.footer_page_numbers,
                        image_sources: summary.image_sources,
                        expected_gain_claims: summary.expected_gain_claims,
                        expected_non_equivalences: summary.expected_non_equivalences,
                        regime_labels: summary.regime_labels,
                        review_notes: summary.review_notes,
                    })}
                </dl>
            </section>
        </div>
    `;
}

function renderAnnotatedPdfTab(manifest) {
    if (!manifest.artifacts.annotated_pdf) {
        els.tabContentArea.innerHTML = '<div class="placeholder">Annotated PDF is unavailable for this fixture.</div>';
        return;
    }
    els.tabContentArea.innerHTML = `
        <div class="artifact-shell">
            <div class="artifact-actions">
                <a class="artifact-link" href="${manifest.artifacts.annotated_pdf}" target="_blank" rel="noopener noreferrer">Open annotated PDF in new tab</a>
            </div>
            <iframe class="artifact-frame" src="${manifest.artifacts.annotated_pdf}" title="Candidate B Annotated PDF"></iframe>
        </div>
    `;
}

async function renderRawJsonTab(manifest) {
    if (!manifest.artifacts.raw_json) {
        els.tabContentArea.innerHTML = '<div class="placeholder">Raw JSON is unavailable for this fixture.</div>';
        return;
    }
    if (state.cachedJson === null) {
        state.cachedJson = await fetchJson(manifest.artifacts.raw_json);
    }
    els.tabContentArea.innerHTML = `
        <div class="artifact-shell">
            <div class="artifact-actions">
                <a class="artifact-link" href="${manifest.artifacts.raw_json}" target="_blank" rel="noopener noreferrer">Open raw JSON in new tab</a>
            </div>
            <pre class="artifact-pre">${escapeHtml(JSON.stringify(state.cachedJson, null, 2))}</pre>
        </div>
    `;
}

async function renderRawMarkdownTab(manifest) {
    if (!manifest.artifacts.raw_markdown) {
        els.tabContentArea.innerHTML = '<div class="placeholder">Raw Markdown is unavailable for this fixture.</div>';
        return;
    }
    if (state.cachedMarkdown === null) {
        state.cachedMarkdown = await fetchText(manifest.artifacts.raw_markdown);
    }
    els.tabContentArea.innerHTML = `
        <div class="artifact-shell">
            <div class="artifact-actions">
                <a class="artifact-link" href="${manifest.artifacts.raw_markdown}" target="_blank" rel="noopener noreferrer">Open raw Markdown in new tab</a>
            </div>
            <pre class="artifact-pre">${escapeHtml(state.cachedMarkdown)}</pre>
        </div>
    `;
}

async function renderActiveTab() {
    const manifest = state.manifest;
    if (!manifest) {
        return;
    }
    els.tabContentArea.innerHTML = '<div class="placeholder">Loading Candidate B trace...</div>';
    if (state.tabId === 'annotated_pdf') {
        renderAnnotatedPdfTab(manifest);
        return;
    }
    if (state.tabId === 'raw_json') {
        await renderRawJsonTab(manifest);
        return;
    }
    if (state.tabId === 'raw_markdown') {
        await renderRawMarkdownTab(manifest);
        return;
    }
    renderSummaryTab(manifest);
}

async function loadManifest() {
    if (!state.candidateBBundleId || !state.fixtureId) {
        setOverlay('Candidate B Trace Unavailable', 'candidate_b_bundle_id and fixture_id are required for Candidate B Trace.');
        return;
    }
    const params = new URLSearchParams({
        candidate_b_bundle_id: state.candidateBBundleId,
        fixture_id: state.fixtureId,
    });
    state.manifest = await fetchJson(`${API_ROOT}/manifest?${params.toString()}`);
    state.candidateBBundleId = state.manifest.candidate_b_bundle_id;
    state.fixtureId = state.manifest.fixture_id;
    const availableTabs = new Set((state.manifest.tabs || []).filter((tab) => tab.available).map((tab) => tab.tab_id));
    if (!availableTabs.has(state.tabId)) {
        state.tabId = state.manifest.default_tab || 'summary';
    }
    if (!availableTabs.has(state.tabId)) {
        state.tabId = 'summary';
    }
    state.cachedJson = null;
    state.cachedMarkdown = null;
    syncQueryState();
    renderIdentitySummary(state.manifest);
    renderBadges(state.manifest);
    renderNoticeList(els.warningList, state.manifest.warnings || [], 'No warnings.');
    renderNoticeList(els.limitationList, state.manifest.limitations || [], 'No limitations.');
    renderTabs(state.manifest);
    clearOverlay();
    await renderActiveTab();
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function bootstrapTheme() {
    let preference = 'system';
    try {
        preference = localStorage.getItem(THEME_KEY) || 'system';
    } catch (error) {
        preference = 'system';
    }
    els.themeSelector.value = preference;
    setTheme(preference);
    els.themeSelector.addEventListener('change', (event) => {
        setTheme(event.target.value);
    });
}

async function init() {
    bootstrapTheme();
    readQueryState();
    syncQueryState();
    try {
        await loadManifest();
    } catch (error) {
        setOverlay('Error Loading Candidate B Trace', error instanceof Error ? error.message : 'Unknown error');
    }
}

window.addEventListener('DOMContentLoaded', init);
