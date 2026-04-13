const API_ROOT = '/api/v1/review/nrc-aps/workbench-compare';
const PAGE_ROUTE = '/review/nrc-aps/workbench-compare';
const TAB_ORDER = ['summary', 'normalized_text', 'diagnostics', 'structure'];
const THEME_KEY = 'nrc_aps_review_theme';

const state = {
    sources: null,
    targets: null,
    manifest: null,
    tabPayload: null,
    baselineRunId: '',
    candidateARunId: '',
    candidateBBundleId: '',
    fixtureId: '',
    tabId: 'summary',
};

const els = {
    baselineRunSelector: document.getElementById('baseline-run-selector'),
    candidateARunSelector: document.getElementById('candidate-a-run-selector'),
    candidateBBundleSelector: document.getElementById('candidate-b-bundle-selector'),
    targetSelector: document.getElementById('target-selector'),
    themeSelector: document.getElementById('theme-selector'),
    disabledOverlay: document.getElementById('disabled-overlay'),
    disabledTitle: document.getElementById('disabled-title'),
    disabledReason: document.getElementById('disabled-reason'),
    compareWorkspace: document.getElementById('compare-workspace'),
    identitySummary: document.getElementById('compare-identity-summary'),
    badgeStrip: document.getElementById('badge-strip'),
    warningList: document.getElementById('warning-list'),
    limitationList: document.getElementById('limitation-list'),
    traceLinkCluster: document.getElementById('trace-link-cluster'),
    tabsHeader: document.getElementById('tabs-header'),
    compareTabContent: document.getElementById('compare-tab-content'),
};

function readQueryState() {
    const params = new URLSearchParams(window.location.search);
    state.baselineRunId = params.get('baseline_run_id') || '';
    state.candidateARunId = params.get('candidate_a_run_id') || '';
    state.candidateBBundleId = params.get('candidate_b_bundle_id') || '';
    state.fixtureId = params.get('fixture_id') || '';
    state.tabId = params.get('tab') || 'summary';
    if (!TAB_ORDER.includes(state.tabId)) {
        state.tabId = 'summary';
    }
}

function syncQueryState() {
    const params = new URLSearchParams();
    if (state.baselineRunId) params.set('baseline_run_id', state.baselineRunId);
    if (state.candidateARunId) params.set('candidate_a_run_id', state.candidateARunId);
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

async function fetchJson(path, params = null) {
    const url = params ? `${path}?${params.toString()}` : path;
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

function setOverlay(title, message) {
    els.disabledTitle.textContent = title;
    els.disabledReason.textContent = message;
    els.disabledOverlay.classList.remove('hidden');
    els.compareWorkspace.classList.add('hidden');
}

function clearOverlay() {
    els.disabledOverlay.classList.add('hidden');
    els.compareWorkspace.classList.remove('hidden');
}

function setOptions(selectEl, items, valueKey, labelKey, currentValue, placeholder) {
    selectEl.innerHTML = '';
    if (!items.length) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = placeholder;
        selectEl.appendChild(option);
        selectEl.disabled = true;
        return '';
    }
    selectEl.disabled = false;
    for (const item of items) {
        const option = document.createElement('option');
        option.value = item[valueKey];
        option.textContent = item[labelKey];
        selectEl.appendChild(option);
    }
    const values = new Set(items.map((item) => item[valueKey]));
    const resolved = values.has(currentValue) ? currentValue : items[0][valueKey];
    selectEl.value = resolved;
    return resolved;
}

function renderIdentitySummary(manifest) {
    const identity = manifest.source_identity;
    els.identitySummary.innerHTML = `
        <div class="meta-item"><span class="meta-label">Fixture</span><span>${escapeHtml(identity.fixture_id || 'n/a')}</span></div>
        <div class="meta-item"><span class="meta-label">Title</span><span>${escapeHtml(identity.document_title || 'n/a')}</span></div>
        <div class="meta-item"><span class="meta-label">Type</span><span>${escapeHtml(identity.document_type || 'n/a')}</span></div>
        <div class="meta-item"><span class="meta-label">Source</span><span>${escapeHtml(identity.source_file_name || 'n/a')}</span></div>
        <div class="meta-item"><span class="meta-label">Accession</span><span>${escapeHtml(identity.accession_number || 'n/a')}</span></div>
        <div class="meta-item"><span class="meta-label">Document Ref</span><span>${escapeHtml(identity.document_ref || 'n/a')}</span></div>
    `;
}

function renderBadges(badges) {
    els.badgeStrip.innerHTML = '';
    for (const badge of badges) {
        const item = document.createElement('div');
        item.className = `compare-badge ${badge.severity || 'info'}`;
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

function renderTraceLinks(manifest) {
    const links = [];
    if (manifest.deep_links?.baseline_trace) {
        links.push(`<a href="${manifest.deep_links.baseline_trace}">Baseline Trace</a>`);
    }
    if (manifest.deep_links?.candidate_a_trace) {
        links.push(`<a href="${manifest.deep_links.candidate_a_trace}">Candidate A Trace</a>`);
    }
    if (manifest.deep_links?.candidate_b_trace) {
        links.push(`<a href="${manifest.deep_links.candidate_b_trace}">Candidate B Trace</a>`);
    }
    els.traceLinkCluster.innerHTML = links.length ? links.join('') : '<span class="meta-item">No trace links available.</span>';
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
            if (state.tabId === tab.tab_id) {
                return;
            }
            state.tabId = tab.tab_id;
            syncQueryState();
            renderTabs(manifest);
            await loadTab();
        });
        els.tabsHeader.appendChild(button);
    }
}

function renderLegend(legend) {
    const entries = Object.entries(legend || {});
    if (!entries.length) {
        return '';
    }
    return `
        <div class="legend-strip">
            ${entries.map(([key, value]) => `<div class="legend-chip"><strong>${escapeHtml(key)}</strong><span>${escapeHtml(value)}</span></div>`).join('')}
        </div>
    `;
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

function renderObjectPanel(title, data) {
    const rows = Object.entries(data || {}).map(([key, value]) => `
        <dt>${escapeHtml(key)}</dt>
        <dd>${renderScalarValue(value)}</dd>
    `).join('');
    return `
        <div class="compare-panel">
            <h4>${escapeHtml(title)}</h4>
            <div class="compare-data">
                <dl>${rows || '<dt>state</dt><dd>no data</dd>'}</dl>
            </div>
        </div>
    `;
}

function renderTextPanel(data) {
    return `
        <div class="compare-panel">
            <h4>Normalized Text</h4>
            <div class="compare-data">
                <dl>
                    <dt>char_count</dt>
                    <dd>${renderScalarValue(data.char_count)}</dd>
                    <dt>mapping_precision</dt>
                    <dd>${renderScalarValue(data.mapping_precision)}</dd>
                </dl>
                <pre>${escapeHtml(data.text || '')}</pre>
            </div>
        </div>
    `;
}

function renderListPanel(title, items, emptyMessage) {
    return `
        <div class="compare-panel">
            <h4>${escapeHtml(title)}</h4>
            <ul>${items.length ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join('') : `<li>${escapeHtml(emptyMessage)}</li>`}</ul>
        </div>
    `;
}

function renderColumn(column) {
    const warnings = column.warnings || [];
    const limitations = column.limitations || [];
    const deepLink = column.deep_link ? `<a class="compare-column-link" href="${column.deep_link}">Open trace</a>` : '';
    let dataHtml = renderObjectPanel('Data', column.data || {});
    if (state.tabId === 'normalized_text') {
        dataHtml = renderTextPanel(column.data || {});
    }
    return `
        <article class="compare-column ${escapeHtml(column.comparability_class)}">
            <div class="compare-column-header">
                <div>
                    <h3>${escapeHtml(column.label)}</h3>
                    <div class="compare-meta">${escapeHtml(column.comparability_class)}</div>
                </div>
                ${deepLink}
            </div>
            ${dataHtml}
            ${renderListPanel('Warnings', warnings, 'None')}
            ${renderListPanel('Limitations', limitations, 'None')}
        </article>
    `;
}

function renderTab(tabPayload) {
    const columns = ['baseline', 'candidate_a', 'candidate_b']
        .map((key) => tabPayload.columns[key])
        .filter(Boolean);
    els.compareTabContent.innerHTML = `
        ${renderLegend(tabPayload.comparability_legend)}
        <div class="compare-grid">
            ${columns.map((column) => renderColumn(column)).join('')}
        </div>
    `;
}

async function loadSources() {
    state.sources = await fetchJson(`${API_ROOT}/sources`);
    state.baselineRunId = setOptions(
        els.baselineRunSelector,
        state.sources.baseline_runs || [],
        'run_id',
        'display_label',
        state.baselineRunId || state.sources.default_baseline_run_id || '',
        'No baseline runs found',
    );
    state.candidateARunId = setOptions(
        els.candidateARunSelector,
        state.sources.candidate_a_runs || [],
        'run_id',
        'display_label',
        state.candidateARunId || state.sources.default_candidate_a_run_id || '',
        'No Candidate A runs found',
    );
    state.candidateBBundleId = setOptions(
        els.candidateBBundleSelector,
        state.sources.candidate_b_bundles || [],
        'bundle_id',
        'display_label',
        state.candidateBBundleId || state.sources.default_candidate_b_bundle_id || '',
        'No Candidate B bundles found',
    );

    if (!state.baselineRunId || !state.candidateARunId || !state.candidateBBundleId) {
        setOverlay(
            'Compare Unavailable',
            'This checkout does not currently expose a full baseline, Candidate A, and Candidate B source set.',
        );
        return false;
    }
    return true;
}

async function loadTargets() {
    const params = new URLSearchParams({
        baseline_run_id: state.baselineRunId,
        candidate_a_run_id: state.candidateARunId,
        candidate_b_bundle_id: state.candidateBBundleId,
    });
    state.targets = await fetchJson(`${API_ROOT}/targets`, params);
    state.fixtureId = setOptions(
        els.targetSelector,
        state.targets.targets || [],
        'fixture_id',
        'display_label',
        state.fixtureId || state.targets.default_fixture_id || '',
        'No comparable fixtures found',
    );
    if (!state.fixtureId) {
        setOverlay(
            'No Comparable Targets',
            'The selected baseline, Candidate A, and Candidate B sources do not share a strict fixture intersection.',
        );
        return false;
    }
    return true;
}

async function loadManifest() {
    const params = new URLSearchParams({
        baseline_run_id: state.baselineRunId,
        candidate_a_run_id: state.candidateARunId,
        candidate_b_bundle_id: state.candidateBBundleId,
    });
    state.manifest = await fetchJson(`${API_ROOT}/targets/${encodeURIComponent(state.fixtureId)}/manifest`, params);
    renderIdentitySummary(state.manifest);
    renderBadges(state.manifest.summary_badges || []);
    renderNoticeList(els.warningList, state.manifest.warnings || [], 'No manifest warnings.');
    renderNoticeList(els.limitationList, state.manifest.limitations || [], 'No manifest limitations.');
    renderTraceLinks(state.manifest);
    renderTabs(state.manifest);
}

async function loadTab() {
    const params = new URLSearchParams({
        baseline_run_id: state.baselineRunId,
        candidate_a_run_id: state.candidateARunId,
        candidate_b_bundle_id: state.candidateBBundleId,
    });
    state.tabPayload = await fetchJson(`${API_ROOT}/targets/${encodeURIComponent(state.fixtureId)}/tabs/${encodeURIComponent(state.tabId)}`, params);
    renderTab(state.tabPayload);
}

async function refreshWorkspace() {
    try {
        const haveSources = await loadSources();
        syncQueryState();
        if (!haveSources) {
            return;
        }
        const haveTargets = await loadTargets();
        syncQueryState();
        if (!haveTargets) {
            return;
        }
        await loadManifest();
        await loadTab();
        syncQueryState();
        clearOverlay();
    } catch (error) {
        setOverlay('Error Loading Compare', error instanceof Error ? error.message : 'Unknown compare workspace error.');
    }
}

function attachSelectorListeners() {
    els.baselineRunSelector.addEventListener('change', async () => {
        state.baselineRunId = els.baselineRunSelector.value;
        state.fixtureId = '';
        await refreshWorkspace();
    });
    els.candidateARunSelector.addEventListener('change', async () => {
        state.candidateARunId = els.candidateARunSelector.value;
        state.fixtureId = '';
        await refreshWorkspace();
    });
    els.candidateBBundleSelector.addEventListener('change', async () => {
        state.candidateBBundleId = els.candidateBBundleSelector.value;
        state.fixtureId = '';
        await refreshWorkspace();
    });
    els.targetSelector.addEventListener('change', async () => {
        state.fixtureId = els.targetSelector.value;
        await loadManifest();
        await loadTab();
        syncQueryState();
    });
    els.themeSelector.addEventListener('change', () => {
        setTheme(els.themeSelector.value);
    });
}

function initThemeSelector() {
    const preference = document.documentElement.dataset.themePreference || 'system';
    els.themeSelector.value = preference;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

async function init() {
    readQueryState();
    initThemeSelector();
    attachSelectorListeners();
    await refreshWorkspace();
}

window.addEventListener('DOMContentLoaded', init);
