const State = {
    runs: [],
    documents: [],
    selectedRunId: null,
    selectedTargetId: null,
    activeTab: 'summary',
    themePreference: document.documentElement.dataset.themePreference || 'system',
    manifest: null,
    tabData: {
        diagnostics: null,
        normalized_text: null,
        indexed_chunks: null,
        extracted_units: null
    },
    tabRequests: {
        extracted_units: null
    },
    viewer: {
        runId: null,
        targetId: null,
        pdfDoc: null,
        objectUrl: null,
        currentPage: 1,
        focusedPage: 1,
        totalPages: 0,
        scale: 1.0,
        showBboxes: true,
        rendering: false,
        pageFocusCleanup: null
    }
};

const TAB_SCOPE = {
    summary: 'document',
    diagnostics: 'document',
    normalized_text: 'document',
    indexed_chunks: 'document',
    extracted_units: 'page',
    downstream_usage: 'document',
};

const elements = {
    runSelector: document.getElementById('run-selector'),
    docSelector: document.getElementById('doc-selector'),
    themeSelector: document.getElementById('theme-selector'),
    disabledOverlay: document.getElementById('disabled-overlay'),
    disabledTitle: document.querySelector('#disabled-overlay h2'),
    disabledReason: document.getElementById('disabled-reason'),
    traceWorkspace: document.getElementById('trace-workspace'),
    identitySummary: document.getElementById('identity-summary'),
    tabsHeader: document.getElementById('tabs-header'),
    tabContentArea: document.getElementById('tab-content-area'),
};

const THEME_STORAGE_KEY = 'nrc_aps_review_theme';
const systemThemeQuery = typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : null;

// --- API Helpers ---
const API = {
    async fetchRuns() {
        const res = await fetch('/api/v1/review/nrc-aps/runs');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },
    async fetchDocuments(runId) {
        const res = await fetch(`/api/v1/review/nrc-aps/runs/${encodeURIComponent(runId)}/documents`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },
    async fetchTrace(runId, targetId) {
        const res = await fetch(`/api/v1/review/nrc-aps/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/trace`);
        if (!res.ok) {
            if (res.status === 404) throw new Error(`Document target not found in run.`);
            throw new Error(`HTTP ${res.status}`);
        }
        return await res.json();
    },
    async fetchDiagnostics(runId, targetId) {
        const res = await fetch(`/api/v1/review/nrc-aps/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/diagnostics`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },
    async fetchNormalizedText(runId, targetId) {
        const res = await fetch(`/api/v1/review/nrc-aps/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/normalized-text`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },
    async fetchIndexedChunks(runId, targetId) {
        const res = await fetch(`/api/v1/review/nrc-aps/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/indexed-chunks`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },
    async fetchExtractedUnits(runId, targetId, pageNumber = null) {
        const url = new URL(`/api/v1/review/nrc-aps/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/extracted-units`, window.location.origin);
        if (pageNumber !== null) url.searchParams.set('page_number', String(pageNumber));
        const res = await fetch(url.pathname + url.search);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    }
};

let _actionSeq = 0;

function escapeHtml(str) {
    return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatTraceContext(runId = State.selectedRunId, targetId = State.selectedTargetId) {
    const safeRunId = escapeHtml(runId || 'unknown run');
    if (targetId) {
        return `target ${escapeHtml(targetId)} in run ${safeRunId}`;
    }
    return `run ${safeRunId}`;
}

function formatReasonCode(reasonCode) {
    if (!reasonCode) return '';
    return String(reasonCode)
        .replace(/[_-]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function formatUnavailableMessage(label, { runId, targetId, reasonCode } = {}) {
    const context = formatTraceContext(runId, targetId);
    const reason = formatReasonCode(reasonCode);
    return `${escapeHtml(label)} is not available for ${context}.${reason ? ` Reason: ${escapeHtml(reason)}.` : ''}`;
}

function formatEmptyMessage(label, { runId, targetId, detail } = {}) {
    const context = formatTraceContext(runId, targetId);
    const suffix = detail ? ` ${escapeHtml(detail)}` : '';
    return `No ${escapeHtml(label)} are available for ${context}.${suffix}`;
}

function renderScopeContextBar(tabId) {
    const scope = TAB_SCOPE[tabId] || 'document';
    if (scope === 'page') return '';
    return '<div class="scope-context-bar">Scope: entire document \u2014 not affected by page navigation</div>';
}

function formatBbox(bbox) {
    if (!Array.isArray(bbox) || bbox.length !== 4) return null;
    return bbox.map(value => {
        if (typeof value !== 'number' || !Number.isFinite(value)) return '?';
        return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, '');
    }).join(', ');
}

function formatArtifactDimensions(artifact) {
    const width = typeof artifact?.width === 'number' && Number.isFinite(artifact.width) ? artifact.width : null;
    const height = typeof artifact?.height === 'number' && Number.isFinite(artifact.height) ? artifact.height : null;
    if (width === null || height === null) return null;
    return `${width}x${height}`;
}

function renderVisualArtifactCard(artifact) {
    const detailParts = [];
    if (artifact.page_number !== null && artifact.page_number !== undefined) detailParts.push(`p. ${artifact.page_number}`);
    if (artifact.status) detailParts.push(`status ${artifact.status}`);
    if (artifact.visual_page_class) detailParts.push(`class ${artifact.visual_page_class}`);
    if (artifact.artifact_semantics) detailParts.push(`semantics ${artifact.artifact_semantics}`);
    if (artifact.dpi !== null && artifact.dpi !== undefined) detailParts.push(`${artifact.dpi} dpi`);
    if (artifact.format) detailParts.push(artifact.format.toUpperCase());
    const dimensions = formatArtifactDimensions(artifact);
    if (dimensions) detailParts.push(dimensions);

    const metaText = detailParts.join(' | ');
    const safeEndpoint = artifact.endpoint ? escapeHtml(artifact.endpoint) : '';
    const previewAlt = `Visual artifact preview for ${formatTraceContext(State.selectedRunId, State.selectedTargetId)} on page ${artifact.page_number || '?'}`;
    const previewHtml = safeEndpoint
        ? `<a class="eu-visual-preview-link" href="${safeEndpoint}" target="_blank" rel="noopener noreferrer">
                <img class="eu-visual-preview" src="${safeEndpoint}" alt="${escapeHtml(previewAlt)}" loading="lazy">
           </a>`
        : `<div class="eu-visual-preview-fallback">${formatUnavailableMessage('Visual artifact preview', { runId: State.selectedRunId, targetId: State.selectedTargetId })}</div>`;

    return `
        <article class="chunk-card eu-card eu-visual-card">
            <div class="chunk-card-header">
                <span class="chunk-card-meta">${escapeHtml(artifact.visual_page_class || artifact.artifact_semantics || 'visual artifact')}</span>
                <span class="eu-precision-badge">${escapeHtml(artifact.status || 'metadata')}</span>
            </div>
            ${metaText ? `<div class="eu-card-details">${escapeHtml(metaText)}</div>` : ''}
            ${previewHtml}
        </article>
    `;
}

function hasRenderableBbox(bbox) {
    if (!Array.isArray(bbox) || bbox.length !== 4) return false;
    return bbox.every(v => typeof v === 'number' && Number.isFinite(v));
}

function clearViewerOverlays() {
    document.querySelectorAll('.pdf-page-overlay').forEach(o => o.replaceChildren());
}

function syncBboxToggleControl() {
    const toggle = document.getElementById('bbox-visibility-toggle');
    if (toggle) toggle.checked = State.viewer.showBboxes;
}

function setBboxVisibility(enabled) {
    State.viewer.showBboxes = enabled !== false;
    syncBboxToggleControl();
    syncViewerOverlays();
}

function syncViewerOverlays() {
    const extractedUnits = State.tabData.extracted_units;
    const pageShells = document.querySelectorAll('.pdf-page-shell');
    if (pageShells.length === 0) return;

    if (!State.viewer.showBboxes || !extractedUnits || !extractedUnits.available || !Array.isArray(extractedUnits.units)) {
        clearViewerOverlays();
        return;
    }

    pageShells.forEach((pageShell) => {
        const pageNum = Number.parseInt(pageShell.dataset.pageNum || '', 10);
        const overlay = pageShell.querySelector('.pdf-page-overlay');
        if (!Number.isInteger(pageNum) || !overlay) return;

        const shellWidth = pageShell.clientWidth;
        const shellHeight = pageShell.clientHeight;
        const shellArea = shellWidth * shellHeight;
        const pageUnits = extractedUnits.units.filter(u => u.page_number === pageNum && hasRenderableBbox(u.bbox));

        overlay.replaceChildren();
        pageUnits.forEach((unit) => {
            let [x0, y0, x1, y1] = unit.bbox;
            // Normalize inverted coordinates
            if (x0 > x1) { const t = x0; x0 = x1; x1 = t; }
            if (y0 > y1) { const t = y0; y0 = y1; y1 = t; }

            const left = x0 * State.viewer.scale;
            const top = y0 * State.viewer.scale;
            const width = (x1 - x0) * State.viewer.scale;
            const height = (y1 - y0) * State.viewer.scale;

            // Suppress zero or near-zero extents
            if (width < 1 || height < 1) return;

            // Suppress page-coverage boxes
            if (shellArea > 0 && (width * height) / shellArea >= 0.98) return;

            const marker = document.createElement('div');
            marker.className = 'pdf-bbox-marker';
            marker.dataset.unitId = unit.unit_id || '';
            marker.title = [unit.unit_kind || 'unit', formatBbox(unit.bbox) || ''].filter(Boolean).join(' | ');
            marker.style.left = `${left}px`;
            marker.style.top = `${top}px`;
            marker.style.width = `${width}px`;
            marker.style.height = `${height}px`;
            overlay.appendChild(marker);
        });
    });
}

async function ensureExtractedUnitsLoaded(seq = _actionSeq) {
    if (State.tabData.extracted_units !== null) {
        syncViewerOverlays();
        return State.tabData.extracted_units;
    }

    if (State.tabRequests.extracted_units) {
        return State.tabRequests.extracted_units;
    }

    const requestedRunId = State.selectedRunId;
    const requestedTargetId = State.selectedTargetId;
    const requestPromise = API.fetchExtractedUnits(requestedRunId, requestedTargetId)
        .then((data) => {
            if (seq !== _actionSeq) return null;
            if (State.selectedRunId !== requestedRunId || State.selectedTargetId !== requestedTargetId) return null;
            State.tabData.extracted_units = data;
            syncViewerOverlays();
            return data;
        })
        .finally(() => {
            if (State.tabRequests.extracted_units === requestPromise) {
                State.tabRequests.extracted_units = null;
            }
        });

    State.tabRequests.extracted_units = requestPromise;
    return requestPromise;
}

function getFocusedSourcePage() {
    return Number.isInteger(State.viewer.focusedPage) && State.viewer.focusedPage > 0 ? State.viewer.focusedPage : 1;
}

function setFocusedSourcePage(pageNum, { force = false } = {}) {
    if (!Number.isInteger(pageNum) || pageNum < 1) return;
    const nextPage = State.viewer.totalPages > 0 ? Math.min(pageNum, State.viewer.totalPages) : pageNum;
    const changed = force || State.viewer.focusedPage !== nextPage || State.viewer.currentPage !== nextPage;
    State.viewer.focusedPage = nextPage;
    State.viewer.currentPage = nextPage;
    PDFViewer.updatePageInfo();
    if (changed && State.activeTab === 'extracted_units' && State.tabData.extracted_units !== null) {
        renderExtractedUnitsTab();
    }
}

function detectFocusedPdfPage(container) {
    const shells = Array.from(container.querySelectorAll('.pdf-page-shell[data-page-num]'));
    if (shells.length === 0) return null;

    const containerRect = container.getBoundingClientRect();
    let bestPage = null;
    let bestVisibleHeight = -1;
    let bestTopDistance = Number.POSITIVE_INFINITY;

    shells.forEach((shell) => {
        const pageNum = Number.parseInt(shell.dataset.pageNum || '', 10);
        if (!Number.isInteger(pageNum)) return;

        const rect = shell.getBoundingClientRect();
        const visibleTop = Math.max(rect.top, containerRect.top);
        const visibleBottom = Math.min(rect.bottom, containerRect.bottom);
        const visibleHeight = Math.max(0, visibleBottom - visibleTop);
        const topDistance = Math.abs(rect.top - containerRect.top);

        if (visibleHeight > bestVisibleHeight || (visibleHeight === bestVisibleHeight && topDistance < bestTopDistance)) {
            bestPage = pageNum;
            bestVisibleHeight = visibleHeight;
            bestTopDistance = topDistance;
        }
    });

    return bestPage;
}

function attachViewerPageFocusTracking() {
    if (State.viewer.pageFocusCleanup) {
        State.viewer.pageFocusCleanup();
        State.viewer.pageFocusCleanup = null;
    }

    const container = document.getElementById('pdf-viewer-container');
    if (!container) return;

    let debounceHandle = null;
    const syncFocusedPage = () => {
        const detectedPage = detectFocusedPdfPage(container);
        if (detectedPage !== null) setFocusedSourcePage(detectedPage);
    };
    const onScroll = () => {
        if (debounceHandle !== null) window.clearTimeout(debounceHandle);
        debounceHandle = window.setTimeout(syncFocusedPage, 120);
    };

    container.addEventListener('scroll', onScroll, { passive: true });
    syncFocusedPage();

    State.viewer.pageFocusCleanup = () => {
        container.removeEventListener('scroll', onScroll);
        if (debounceHandle !== null) window.clearTimeout(debounceHandle);
    };
}

function jumpToSourcePage(pageNum) {
    if (!State.viewer.pdfDoc) return;
    if (!Number.isInteger(pageNum) || pageNum < 1) return;
    PDFViewer.goToPage(pageNum);
}

if (elements.tabContentArea) {
    elements.tabContentArea.addEventListener('click', (event) => {
        const trigger = event.target.closest('.eu-jump-btn');
        if (!trigger) return;
        const pageNum = Number.parseInt(trigger.dataset.pageNumber || '', 10);
        jumpToSourcePage(pageNum);
    });
}

// --- Theme Management ---
function persistThemePreference(preference) {
    try { localStorage.setItem(THEME_STORAGE_KEY, preference); } catch (e) {}
}

function applyThemePreference(preference, { persist = true } = {}) {
    const valid = ['system', 'light', 'dark'].includes(preference) ? preference : 'system';
    const resolved = valid === 'system' ? (systemThemeQuery?.matches ? 'dark' : 'light') : valid;
    State.themePreference = valid;
    document.documentElement.dataset.themePreference = valid;
    document.documentElement.dataset.theme = resolved;
    if (elements.themeSelector) elements.themeSelector.value = valid;
    if (persist) persistThemePreference(valid);
}

// --- PDF Viewer Lifecycle ---
const PDFViewer = {
    ZOOM_STEP: 0.25,
    MIN_SCALE: 0.5,
    MAX_SCALE: 3.0,

    async init(runId, targetId, viewerKind, blobRefPresent) {
        // Only init for PDFs with available blobs
        const sourceContent = document.getElementById('source-content');
        if (!blobRefPresent) {
            sourceContent.innerHTML = `<div class="source-fallback"><span id="observed-source-status">${formatUnavailableMessage('Source file', { runId, targetId })}</span></div>`;
            return;
        }
        if (viewerKind !== 'pdf') {
            sourceContent.innerHTML = `<div class="source-fallback"><span id="observed-source-status">Source preview for ${escapeHtml(viewerKind || 'unknown')} content is not supported for ${formatTraceContext(runId, targetId)}.</span></div>`;
            return;
        }

        // Build viewer DOM
        sourceContent.innerHTML = `
            <div class="pdf-viewer-stage">
                <div class="pdf-viewer-controls" id="pdf-controls">
                    <button id="pdf-prev" title="Previous page">&laquo; Prev</button>
                    <span class="page-info" id="pdf-page-info">-- / --</span>
                    <button id="pdf-next" title="Next page">Next &raquo;</button>
                    <span style="border-left:1px solid var(--border-color);height:20px;"></span>
                    <button id="pdf-zoom-out" title="Zoom out">&minus;</button>
                    <span class="zoom-info" id="pdf-zoom-info">100%</span>
                    <button id="pdf-zoom-in" title="Zoom in">&plus;</button>
                    <button id="pdf-zoom-fit" title="Fit width">Fit</button>
                </div>
                <label class="bbox-toggle-float" for="bbox-visibility-toggle" aria-label="Toggle bounding box overlays">
                    <input id="bbox-visibility-toggle" type="checkbox" checked aria-label="Show bounding box overlays">
                    <span>BBoxes</span>
                </label>
                <div class="pdf-viewer-container" id="pdf-viewer-container">
                    <div class="placeholder">Loading PDF...</div>
                </div>
            </div>
        `;

        // Wire controls
        document.getElementById('pdf-prev').addEventListener('click', () => PDFViewer.goToPage(State.viewer.currentPage - 1));
        document.getElementById('pdf-next').addEventListener('click', () => PDFViewer.goToPage(State.viewer.currentPage + 1));
        document.getElementById('pdf-zoom-in').addEventListener('click', () => PDFViewer.setZoom(State.viewer.scale + PDFViewer.ZOOM_STEP));
        document.getElementById('pdf-zoom-out').addEventListener('click', () => PDFViewer.setZoom(State.viewer.scale - PDFViewer.ZOOM_STEP));
        document.getElementById('pdf-zoom-fit').addEventListener('click', () => PDFViewer.fitWidth());
        document.getElementById('bbox-visibility-toggle').addEventListener('change', (e) => {
            setBboxVisibility(e.target.checked);
        });
        syncBboxToggleControl();

        // Fetch and render
        try {
            const url = `/api/v1/review/nrc-aps/runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(targetId)}/source`;
            const resp = await fetch(url);
            // Check stale: if target changed while fetching, abort
            if (State.selectedRunId !== runId || State.selectedTargetId !== targetId) return;
            if (!resp.ok) {
                const container = document.getElementById('pdf-viewer-container');
                if (container) container.innerHTML = `<div class="source-fallback"><span id="observed-source-status">Source fetch failed for ${formatTraceContext(runId, targetId)}: HTTP ${resp.status}.</span></div>`;
                return;
            }
            const blob = await resp.blob();
            if (State.selectedRunId !== runId || State.selectedTargetId !== targetId) return;

            const objUrl = URL.createObjectURL(blob);
            State.viewer.objectUrl = objUrl;
            State.viewer.runId = runId;
            State.viewer.targetId = targetId;

            // Wait for PDF.js to be ready
            const pdfjsLib = window.pdfjsLib;
            if (!pdfjsLib) {
                const container = document.getElementById('pdf-viewer-container');
                if (container) container.innerHTML = `<div class="source-fallback">PDF viewer library not loaded for ${formatTraceContext(runId, targetId)}.</div>`;
                return;
            }

            const loadingTask = pdfjsLib.getDocument(objUrl);
            const pdfDoc = await loadingTask.promise;
            if (State.selectedRunId !== runId || State.selectedTargetId !== targetId) {
                pdfDoc.destroy();
                return;
            }

            State.viewer.pdfDoc = pdfDoc;
            State.viewer.totalPages = pdfDoc.numPages;
            setFocusedSourcePage(1, { force: true });
            await PDFViewer.renderAllVisiblePages();
        } catch (err) {
            if (State.selectedRunId !== runId || State.selectedTargetId !== targetId) return;
            const container = document.getElementById('pdf-viewer-container');
            if (container) container.innerHTML = `<div class="source-fallback"><span id="observed-source-status">Error loading PDF for ${formatTraceContext(runId, targetId)}: ${escapeHtml(err.message)}</span></div>`;
        }
    },

    async renderAllVisiblePages() {
        const container = document.getElementById('pdf-viewer-container');
        if (!container || !State.viewer.pdfDoc) return;
        container.innerHTML = '';

        const pdfDoc = State.viewer.pdfDoc;
        for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
            const page = await pdfDoc.getPage(pageNum);
            const viewport = page.getViewport({ scale: State.viewer.scale });

            const pageShell = document.createElement('div');
            pageShell.className = 'pdf-page-shell';
            pageShell.dataset.pageNum = pageNum;
            pageShell.style.width = `${viewport.width}px`;
            pageShell.style.height = `${viewport.height}px`;

            const canvas = document.createElement('canvas');
            canvas.className = 'pdf-page-canvas';
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            pageShell.appendChild(canvas);

            const overlay = document.createElement('div');
            overlay.className = 'pdf-page-overlay';
            overlay.setAttribute('aria-hidden', 'true');
            pageShell.appendChild(overlay);

            container.appendChild(pageShell);

            const ctx = canvas.getContext('2d');
            await page.render({ canvasContext: ctx, viewport }).promise;
        }
        syncViewerOverlays();
        PDFViewer.scrollToPage(getFocusedSourcePage());
        attachViewerPageFocusTracking();
    },

    scrollToPage(pageNum) {
        const container = document.getElementById('pdf-viewer-container');
        if (!container) return;
        const pageShell = container.querySelector(`.pdf-page-shell[data-page-num="${pageNum}"]`);
        if (pageShell) pageShell.scrollIntoView({ behavior: 'auto', block: 'start' });
    },

    goToPage(pageNum) {
        if (!State.viewer.pdfDoc) return;
        const clamped = Math.max(1, Math.min(pageNum, State.viewer.totalPages));
        setFocusedSourcePage(clamped, { force: true });
        PDFViewer.scrollToPage(clamped);
    },

    setZoom(newScale) {
        const clamped = Math.max(PDFViewer.MIN_SCALE, Math.min(newScale, PDFViewer.MAX_SCALE));
        State.viewer.scale = clamped;
        PDFViewer.updateZoomInfo();
        PDFViewer.renderAllVisiblePages();
    },

    fitWidth() {
        const container = document.getElementById('pdf-viewer-container');
        if (!container || !State.viewer.pdfDoc) return;
        State.viewer.pdfDoc.getPage(State.viewer.currentPage).then(page => {
            const unscaled = page.getViewport({ scale: 1.0 });
            const availableWidth = container.clientWidth - 40; // padding
            const fitScale = availableWidth / unscaled.width;
            PDFViewer.setZoom(fitScale);
        });
    },

    updatePageInfo() {
        const el = document.getElementById('pdf-page-info');
        if (el) el.textContent = `${State.viewer.currentPage} / ${State.viewer.totalPages}`;
    },

    updateZoomInfo() {
        const el = document.getElementById('pdf-zoom-info');
        if (el) el.textContent = `${Math.round(State.viewer.scale * 100)}%`;
    },

    teardown() {
        if (State.viewer.pdfDoc) {
            State.viewer.pdfDoc.destroy();
            State.viewer.pdfDoc = null;
        }
        if (State.viewer.objectUrl) {
            URL.revokeObjectURL(State.viewer.objectUrl);
            State.viewer.objectUrl = null;
        }
        State.viewer.runId = null;
        State.viewer.targetId = null;
        State.viewer.currentPage = 1;
        State.viewer.focusedPage = 1;
        State.viewer.totalPages = 0;
        State.viewer.scale = 1.0;
        if (State.viewer.pageFocusCleanup) {
            State.viewer.pageFocusCleanup();
            State.viewer.pageFocusCleanup = null;
        }
    }
};

// --- UI Updates ---
function updateUrlParams(method = 'replace') {
    const url = new URL(window.location);
    if (State.selectedRunId) url.searchParams.set('run_id', State.selectedRunId);
    else url.searchParams.delete('run_id');
    
    if (State.selectedTargetId) url.searchParams.set('target_id', State.selectedTargetId);
    else url.searchParams.delete('target_id');

    if (State.activeTab && State.activeTab !== 'summary') url.searchParams.set('tab', State.activeTab);
    else url.searchParams.delete('tab');
    
    if (method === 'push') {
        window.history.pushState({ tab: State.activeTab, targetId: State.selectedTargetId, runId: State.selectedRunId }, '', url);
    } else {
        window.history.replaceState({ tab: State.activeTab, targetId: State.selectedTargetId, runId: State.selectedRunId }, '', url);
    }
}

function renderShellError(message, title) {
    elements.traceWorkspace.classList.add('hidden');
    elements.disabledOverlay.classList.remove('hidden');
    if (elements.disabledTitle) elements.disabledTitle.textContent = title || 'Trace Unavailable';
    elements.disabledReason.textContent = message;
}

function renderTraceShell() {
    elements.disabledOverlay.classList.add('hidden');
    elements.traceWorkspace.classList.remove('hidden');
    
    const { identity, source } = State.manifest;
    
    // 1. Identity Summary — run + document identity
    const runInfo = State.runs.find(r => r.run_id === State.selectedRunId);
    const runStatus = runInfo ? runInfo.status || 'unknown' : 'unknown';
    elements.identitySummary.innerHTML = `
        <div class="layout-entry">
            <strong>RUN</strong>
            <span>${escapeHtml(State.selectedRunId)} (${escapeHtml(runStatus)})</span>
        </div>
        <div class="layout-entry">
            <strong>ACCESSION NUMBER</strong>
            <span>${escapeHtml(identity.accession_number || 'N/A')}</span>
        </div>
        <div class="layout-entry">
            <strong>DOCUMENT TYPE</strong>
            <span>${escapeHtml(identity.document_type || 'N/A')}</span>
        </div>
        <div class="layout-entry">
            <strong>TARGET ID</strong>
            <span>${escapeHtml(State.selectedTargetId)}</span>
        </div>
    `;

    // 2. Source pane — metadata bar + viewer initialization
    const sourceContent = document.getElementById('source-content');
    if (source) {
        const availabilityStatus = source.blob_ref_present ? 'Available' : 'Missing';
        // Build compact metadata bar at top of source pane
        let metaBarHtml = `<div class="source-meta-bar">`;
        metaBarHtml += `<div class="meta-item"><span class="meta-label">Status:</span> <span id="observed-source-status">${escapeHtml(availabilityStatus)}</span></div>`;
        metaBarHtml += `<div class="meta-item"><span class="meta-label">Viewer:</span> ${escapeHtml(source.viewer_kind || 'none')}</div>`;
        if (source.content_type) metaBarHtml += `<div class="meta-item"><span class="meta-label">Type:</span> ${escapeHtml(source.content_type)}</div>`;
        if (identity.source_file_name) metaBarHtml += `<div class="meta-item"><span class="meta-label">File:</span> ${escapeHtml(identity.source_file_name)}</div>`;
        metaBarHtml += `</div>`;

        // Only initialize viewer if the viewer isn't already loaded for this target
        if (State.viewer.runId === State.selectedRunId && State.viewer.targetId === State.selectedTargetId && State.viewer.pdfDoc) {
            // Viewer already initialized for this target — preserve it, just ensure meta bar exists
            const existingMetaBar = sourceContent.querySelector('.source-meta-bar');
            if (!existingMetaBar) {
                sourceContent.insertAdjacentHTML('afterbegin', metaBarHtml);
            }
        } else {
            // Initialize fresh viewer
            PDFViewer.teardown();
            sourceContent.innerHTML = metaBarHtml + `<div class="source-fallback">Initializing viewer...</div>`;
            PDFViewer.init(State.selectedRunId, State.selectedTargetId, source.viewer_kind, source.blob_ref_present);
        }
    } else {
        PDFViewer.teardown();
        sourceContent.innerHTML = `<div class="source-fallback"><span id="observed-source-status">${formatUnavailableMessage('Source metadata', { runId: State.selectedRunId, targetId: State.selectedTargetId })}</span></div>`;
    }
}

// --- Tab Rendering Helpers ---

function renderSummaryTab() {
    const { summary, trace_completeness, sync_capabilities, warnings, limitations } = State.manifest;
    let html = `<div class="tab-pane-content">`;
    html += renderScopeContextBar('summary');

    html += `
        <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px;">
            <div class="layout-entry card-stat"><strong>DOCUMENT CLASS</strong><br><span>${escapeHtml(summary.document_class || 'Unknown')}</span></div>
            <div class="layout-entry card-stat"><strong>QUALITY STATUS</strong><br><span>${escapeHtml(summary.quality_status || 'Unknown')}</span></div>
            <div class="layout-entry card-stat"><strong>PAGE COUNT</strong><br><span>${summary.page_count}</span></div>
            <div class="layout-entry card-stat"><strong>UNIT COUNT</strong><br><span>${summary.ordered_unit_count}</span></div>
            <div class="layout-entry card-stat"><strong>CHUNK COUNT</strong><br><span>${summary.indexed_chunk_count}</span></div>
            <div class="layout-entry card-stat"><strong>VISUAL PAGES</strong><br><span>${summary.visual_page_ref_count}</span></div>
            <div class="layout-entry card-stat"><strong>VISUAL-DERIVED UNITS</strong><br><span>${summary.visual_derivative_unit_count}</span></div>
        </div>
    `;

    html += `<h3>Trace Completeness</h3><ul style="margin-bottom: 20px">`;
    html += `<li>Source Blob: ${trace_completeness.has_source_blob ? 'Yes' : 'No'}</li>`;
    html += `<li>Diagnostics: ${trace_completeness.has_diagnostics ? 'Yes' : 'No'}</li>`;
    html += `<li>Normalized Text: ${trace_completeness.has_normalized_text ? 'Yes' : 'No'}</li>`;
    html += `<li>Indexed Chunks: ${trace_completeness.has_indexed_chunks ? 'Yes' : 'No'}</li>`;
    html += `<li>Visual Derivatives: ${trace_completeness.has_visual_derivatives ? 'Yes' : 'No'}</li>`;
    html += `</ul>`;

    html += `<h3>Sync Capabilities</h3><ul style="margin-bottom: 20px">`;
    html += `<li>Source to Units: ${escapeHtml(sync_capabilities.source_to_units)}</li>`;
    html += `<li>Units to Source: ${escapeHtml(sync_capabilities.units_to_source)}</li>`;
    html += `<li>Chunk to Source: ${escapeHtml(sync_capabilities.chunk_to_source)}</li>`;
    html += `</ul>`;

    if (warnings && warnings.length > 0) {
        html += `<div style="color: #c92a2a; margin-top: 20px;"><strong>Warnings:</strong><ul>`;
        warnings.forEach(w => html += `<li>${escapeHtml(w)}</li>`);
        html += `</ul></div>`;
    }
    
    html += `</div>`;
    elements.tabContentArea.innerHTML = html;
}

function renderDiagnosticsTab() {
    const data = State.tabData.diagnostics;
    if (!data || !data.available) {
        elements.tabContentArea.innerHTML = `<div class="tab-pane-content">${renderScopeContextBar('diagnostics')}<div class="placeholder">${formatUnavailableMessage('Diagnostics', { runId: data?.run_id, targetId: data?.target_id })}</div></div>`;
        return;
    }

    let html = `<div class="tab-pane-content">`;
    html += renderScopeContextBar('diagnostics');

    html += `
        <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px;">
            <div class="layout-entry card-stat"><strong>DOCUMENT CLASS</strong><br><span>${escapeHtml(data.document_class || 'Unknown')}</span></div>
            <div class="layout-entry card-stat"><strong>QUALITY STATUS</strong><br><span>${escapeHtml(data.quality_status || 'Unknown')}</span></div>
            <div class="layout-entry card-stat"><strong>PAGE COUNT</strong><br><span>${data.page_count}</span></div>
            <div class="layout-entry card-stat"><strong>UNIT COUNT</strong><br><span>${data.ordered_unit_count}</span></div>
            <div class="layout-entry card-stat"><strong>VISUAL PAGES</strong><br><span>${data.visual_page_ref_count}</span></div>
            <div class="layout-entry card-stat"><strong>VISUAL-DERIVED UNITS</strong><br><span>${data.visual_derivative_unit_count}</span></div>
        </div>
    `;

    const unitKindEntries = Object.entries(data.unit_kind_counts || {});
    if (unitKindEntries.length > 0) {
        html += `<h3>Unit Kind Breakdown</h3><ul style="margin-bottom: 20px">`;
        unitKindEntries.forEach(([unitKind, count]) => {
            html += `<li>${escapeHtml(unitKind)}: ${count}</li>`;
        });
        html += `</ul>`;
    }

    if (data.extractor_metadata) {
        html += `<h3>Extractor Metadata</h3><div class="text-scroll-block"><pre>${escapeHtml(JSON.stringify(data.extractor_metadata, null, 2))}</pre></div>`;
    }

    if (data.degradation_codes && data.degradation_codes.length > 0) {
        html += `<div style="margin-top: 20px;"><strong>Degradation Codes:</strong><ul>`;
        data.degradation_codes.forEach(w => html += `<li>${escapeHtml(w)}</li>`);
        html += `</ul></div>`;
    }

    if (data.warnings && data.warnings.length > 0) {
        html += `<div style="color: #c92a2a; margin-top: 20px;"><strong>Warnings:</strong><ul>`;
        data.warnings.forEach(w => html += `<li>${escapeHtml(w)}</li>`);
        html += `</ul></div>`;
    }

    html += `</div>`;
    elements.tabContentArea.innerHTML = html;
}

function renderNormalizedTextTab() {
    const data = State.tabData.normalized_text;
    if (!data || !data.available) {
        elements.tabContentArea.innerHTML = `<div class="tab-pane-content">${renderScopeContextBar('normalized_text')}<div class="placeholder">${formatUnavailableMessage('Normalized Text', { runId: data?.run_id, targetId: data?.target_id })}</div></div>`;
        return;
    }

    let html = `<div class="tab-pane-content" style="display:flex; flex-direction:column; height: 100%;">`;
    html += renderScopeContextBar('normalized_text');

    html += `
        <div style="display: flex; gap: 20px; margin-bottom: 12px; flex-shrink: 0;">
            <div class="layout-entry card-stat"><strong>CHARACTER COUNT</strong><br><span>${data.char_count}</span></div>
            <div class="layout-entry card-stat"><strong>MAPPING PRECISION</strong><br><span>${escapeHtml(data.mapping_precision || 'Unknown')}</span></div>
        </div>
    `;

    html += `<div class="text-scroll-block" style="flex:1; margin-top: 10px; font-family: monospace; white-space: pre-wrap;">${escapeHtml(data.text || '')}</div>`;
    html += `</div>`;
    elements.tabContentArea.innerHTML = html;
}

function renderIndexedChunksTab() {
    const data = State.tabData.indexed_chunks;
    if (!data || !data.available) {
        elements.tabContentArea.innerHTML = `<div class="tab-pane-content">${renderScopeContextBar('indexed_chunks')}<div class="placeholder">${formatUnavailableMessage('Indexed Chunks', { runId: data?.run_id, targetId: data?.target_id })}</div></div>`;
        return;
    }

    let html = `<div class="tab-pane-content">`;
    html += renderScopeContextBar('indexed_chunks');

    html += `
        <div style="display: flex; gap: 20px; margin-bottom: 20px;">
            <div class="layout-entry card-stat"><strong>CHUNK COUNT</strong><br><span>${data.chunk_count}</span></div>
        </div>
    `;

    html += `<div class="card-list">`;
    data.chunks.forEach(c => {
        const pages = (c.page_start !== null && c.page_end !== null) ? `Pages ${c.page_start}-${c.page_end}` : 'Unknown Pages';
        const chars = (c.start_char !== null && c.end_char !== null) ? `Chars ${c.start_char}-${c.end_char}` : 'Unknown Chars';
        html += `
            <div class="chunk-card">
                <div class="chunk-card-header">
                    <strong>Chunk #${c.chunk_ordinal}</strong>
                    <span style="float: right; font-size: 0.85em; color: var(--muted-text);">${escapeHtml(pages)} | ${escapeHtml(chars)}</span>
                </div>
                <div class="chunk-card-meta">
                    ${c.unit_kind ? `<span>Kind: ${escapeHtml(c.unit_kind)}</span> ` : ''}
                    ${c.quality_status ? `<span style="margin-left:8px;">Status: ${escapeHtml(c.quality_status)}</span>` : ''}
                </div>
                <div class="chunk-card-text">${escapeHtml(c.chunk_text)}</div>
            </div>
        `;
    });
    html += `</div></div>`;
    elements.tabContentArea.innerHTML = html;
}

function renderExtractedUnitsTab() {
    const data = State.tabData.extracted_units;
    if (!data) {
        elements.tabContentArea.innerHTML = `<div class="placeholder">${formatUnavailableMessage('Extracted Units')}</div>`;
        return;
    }

    const focusedPage = getFocusedSourcePage();
    const totalPages = State.viewer.totalPages;
    const allUnits = Array.isArray(data.units) ? data.units : [];
    const allVisualArtifacts = Array.isArray(data.visual_artifacts) ? data.visual_artifacts : [];
    const hasPageScope = totalPages > 0;
    const scopedUnits = hasPageScope ? allUnits.filter(unit => unit.page_number === focusedPage) : allUnits;
    const scopedVisualArtifacts = hasPageScope
        ? allVisualArtifacts.filter(artifact => artifact.page_number === focusedPage)
        : allVisualArtifacts;
    const precisionLabel = data.source_precision === 'unit' ? 'unit (page-level jump)' : (data.source_precision || 'none');
    const pageScopeLabel = hasPageScope
        ? `Page ${focusedPage}${totalPages ? ` / ${totalPages}` : ''}`
        : 'Page scope unavailable';
    const pageCountLabel = hasPageScope
        ? `${scopedUnits.length} units and ${scopedVisualArtifacts.length} visual artifacts on this page (${data.total_unit_count} total units, ${allVisualArtifacts.length} total visual artifacts)`
        : `${allUnits.length} units loaded and ${allVisualArtifacts.length} visual artifacts loaded`;

    let html = `<div class="tab-pane-content eu-pane" data-source-layer="${escapeHtml(data.source_layer || 'diagnostics_ordered_units')}" data-sync-precision="${escapeHtml(data.source_precision || 'none')}">`;
    html += `
        <div class="eu-provenance-bar">
            <span class="eu-provenance">Source: diagnostics ordered_units</span>
            <span class="eu-precision" data-sync-precision="${escapeHtml(data.source_precision || 'none')}">Sync: ${escapeHtml(precisionLabel)}</span>
        </div>
        <div class="eu-page-scope">
            <span class="eu-page-badge">${escapeHtml(pageScopeLabel)}</span>
            <span class="eu-page-count">${escapeHtml(pageCountLabel)}</span>
        </div>
    `;

    if (hasPageScope && scopedUnits.length === 0 && scopedVisualArtifacts.length === 0) {
        html += `<div class="placeholder eu-empty-state">${formatEmptyMessage('extracted units or visual artifacts', { runId: data.run_id, targetId: data.target_id, detail: `Page ${focusedPage}.` })}</div>`;
        html += `</div>`;
        elements.tabContentArea.innerHTML = html;
        return;
    }

    if (scopedVisualArtifacts.length > 0) {
        html += `<section class="eu-section"><h3 class="eu-section-title">Visual Artifacts on This Page</h3><div class="card-list">`;
        scopedVisualArtifacts.forEach((artifact) => {
            html += renderVisualArtifactCard(artifact);
        });
        html += `</div></section>`;
    }

    if (!data.available) {
        html += `<div class="placeholder eu-inline-note">${formatUnavailableMessage('Extracted Units', { runId: data.run_id, targetId: data.target_id, reasonCode: data.reason_code })}</div>`;
        html += `</div>`;
        elements.tabContentArea.innerHTML = html;
        return;
    }

    if (scopedUnits.length === 0) {
        html += `<div class="placeholder eu-inline-note">${formatEmptyMessage('extracted units', { runId: data.run_id, targetId: data.target_id, detail: `Page ${focusedPage}.` })}</div>`;
        html += `</div>`;
        elements.tabContentArea.innerHTML = html;
        return;
    }

    html += `<section class="eu-section"><h3 class="eu-section-title">Extracted Units</h3>`;
    html += `<div class="card-list">`;
    scopedUnits.forEach((unit) => {
        const detailParts = [];
        if (unit.page_number !== null && unit.page_number !== undefined) detailParts.push(`p. ${unit.page_number}`);
        if (unit.start_char !== null && unit.start_char !== undefined && unit.end_char !== null && unit.end_char !== undefined) {
            detailParts.push(`chars ${unit.start_char}-${unit.end_char}`);
        }
        const bboxText = formatBbox(unit.bbox);
        if (bboxText) detailParts.push(`bbox ${bboxText}`);

        const metaText = detailParts.join(' | ');
        const unitKind = escapeHtml(unit.unit_kind || 'unit');
        const mappingPrecision = escapeHtml(unit.mapping_precision || 'none');
        const unitText = escapeHtml(unit.text || '');
        const canJump = Number.isInteger(unit.page_number) && unit.page_number > 0;

        if (canJump) {
            html += `
                <button
                    type="button"
                    class="chunk-card eu-card eu-card-in-scope eu-card-clickable eu-jump-btn"
                    data-page-number="${unit.page_number}"
                    data-unit-id="${escapeHtml(unit.unit_id || '')}"
                    aria-label="Jump source viewer to page ${unit.page_number}"
                >
                    <div class="chunk-card-header">
                        <span class="chunk-card-meta">${unitKind}</span>
                        <span class="eu-precision-badge" data-unit-precision="${mappingPrecision}">${mappingPrecision}</span>
                    </div>
                    ${metaText ? `<div class="eu-card-details">${escapeHtml(metaText)}</div>` : ''}
                    <div class="chunk-card-text">${unitText}</div>
                </button>
            `;
        } else {
            html += `
                <article class="chunk-card eu-card eu-card-in-scope" data-unit-id="${escapeHtml(unit.unit_id || '')}">
                    <div class="chunk-card-header">
                        <span class="chunk-card-meta">${unitKind}</span>
                        <span class="eu-precision-badge" data-unit-precision="${mappingPrecision}">${mappingPrecision}</span>
                    </div>
                    ${metaText ? `<div class="eu-card-details">${escapeHtml(metaText)}</div>` : ''}
                    <div class="chunk-card-text">${unitText}</div>
                </article>
            `;
        }
    });
    html += `</div></section></div>`;
    elements.tabContentArea.innerHTML = html;
}

window.switchTab = async function(tabId, pushHistory = true) {
    if (!State.manifest) return;

    // Reject unimplemented tabs immediately and fallback to summary
    const supportedTabs = ['summary', 'diagnostics', 'normalized_text', 'indexed_chunks', 'extracted_units'];
    if (!supportedTabs.includes(tabId)) {
        tabId = 'summary';
    }

    const tabMeta = State.manifest.tabs.find(t => t.tab_id === tabId);
    if (!tabMeta || !tabMeta.available) {
        if (tabId !== 'summary') {
            tabId = 'summary';
        }
    }

    State.activeTab = tabId;
    
    // Update active UI button states
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.trim().toLowerCase().replace(' ', '_') === tabId) {
            btn.classList.add('active'); // Wait, label matching is brittle. Re-render shell.
        }
    });
    // Simpler to just re-generate the tabs header
    elements.tabsHeader.innerHTML = State.manifest.tabs.map(t => {
        const isActive = t.tab_id === State.activeTab;
        const isAvailable = t.available;
        const clickHandler = isAvailable ? `onclick="window.switchTab('${escapeHtml(t.tab_id)}', true)"` : '';
        const scope = TAB_SCOPE[t.tab_id] || 'document';
        const scopeLabel = scope === 'page' ? 'page' : 'doc';
        return `<button class="tab-btn ${isActive ? 'active' : ''}" ${!isAvailable ? 'disabled title="Data unavailable"' : ''} ${clickHandler}>
            ${escapeHtml(t.label || t.tab_id)}
            <span class="tab-scope-badge">${scopeLabel}</span>
        </button>`;
    }).join('');

    if (pushHistory) updateUrlParams('push');
    else updateUrlParams('replace');

    loadActiveTab();
};

async function loadActiveTab() {
    const tabId = State.activeTab;
    const seq = _actionSeq;

    if (tabId === 'summary') {
        renderSummaryTab();
        return;
    }

    // Check Cache
    if (State.tabData[tabId] !== null) {
        if (tabId === 'diagnostics') renderDiagnosticsTab();
        else if (tabId === 'normalized_text') renderNormalizedTextTab();
        else if (tabId === 'indexed_chunks') renderIndexedChunksTab();
        else if (tabId === 'extracted_units') renderExtractedUnitsTab();
        return;
    }

    // Fetch
    elements.tabContentArea.innerHTML = `<div class="placeholder">Loading...</div>`;
    try {
        if (tabId === 'diagnostics') {
            const data = await API.fetchDiagnostics(State.selectedRunId, State.selectedTargetId);
            if (seq !== _actionSeq) return;
            State.tabData.diagnostics = data;
            renderDiagnosticsTab();
        } else if (tabId === 'normalized_text') {
            const data = await API.fetchNormalizedText(State.selectedRunId, State.selectedTargetId);
            if (seq !== _actionSeq) return;
            State.tabData.normalized_text = data;
            renderNormalizedTextTab();
        } else if (tabId === 'indexed_chunks') {
            const data = await API.fetchIndexedChunks(State.selectedRunId, State.selectedTargetId);
            if (seq !== _actionSeq) return;
            State.tabData.indexed_chunks = data;
            renderIndexedChunksTab();
        } else if (tabId === 'extracted_units') {
            const data = await ensureExtractedUnitsLoaded(seq);
            if (seq !== _actionSeq || data === null) return;
            renderExtractedUnitsTab();
        }
    } catch (err) {
        if (seq !== _actionSeq) return;
        elements.tabContentArea.innerHTML = `<div class="placeholder" style="color:var(--danger-color)">Failed to load ${escapeHtml(tabId)} for ${escapeHtml(State.selectedTargetId)} in run ${escapeHtml(State.selectedRunId)}: ${escapeHtml(err.message)}</div>`;
    }
}


// --- Bootstrapping Actions ---
async function loadTargetDoc(targetId, seq) {
    State.selectedTargetId = targetId;
    elements.docSelector.value = targetId || "";
    
    // Clear tab state cache since target changed
    State.tabData = { diagnostics: null, normalized_text: null, indexed_chunks: null, extracted_units: null };
    State.tabRequests.extracted_units = null;

    // Tear down old viewer for previous target
    PDFViewer.teardown();

    // Immediately update run identity and clear stale document identity
    const runInfo = State.runs.find(r => r.run_id === State.selectedRunId);
    const runStatus = runInfo ? runInfo.status || 'unknown' : 'unknown';
    elements.identitySummary.innerHTML = `
        <div class="layout-entry">
            <strong>RUN</strong>
            <span>${escapeHtml(State.selectedRunId)} (${escapeHtml(runStatus)})</span>
        </div>
    `;

    updateUrlParams('replace');

    if (!targetId) {
        renderShellError(`No document selected for run ${State.selectedRunId}.`, 'No Document Selected');
        return;
    }

    if (State.documents.length && !State.documents.some(d => d.target_id === targetId)) {
        renderShellError(`Document ${targetId} is not available in run ${State.selectedRunId}.`, 'Document Not Available');
        return;
    }

    try {
        const manifest = await API.fetchTrace(State.selectedRunId, targetId);
        if (seq !== _actionSeq) return;
        State.manifest = manifest;
        renderTraceShell();
        ensureExtractedUnitsLoaded(seq).catch(() => {});
        window.switchTab(State.activeTab, false);
    } catch (err) {
        if (seq !== _actionSeq) return;
        renderShellError(`Failed to load trace for ${targetId} in run ${State.selectedRunId}: ${err.message}`, 'Error Loading Trace');
    }
}

async function loadRun(runId, targetIdOverride, seq) {
    State.selectedRunId = runId;
    elements.runSelector.value = runId || "";
    elements.docSelector.innerHTML = '<option value="">Loading...</option>';
    elements.docSelector.disabled = true;

    const runInfo = State.runs.find(r => r.run_id === runId);
    if (runInfo && !runInfo.reviewable) {
        elements.docSelector.innerHTML = '<option value="">Run not reviewable</option>';
        renderShellError(`Run ${runId} is not reviewable (${runInfo.disabled_reason_code || 'unknown reason'}).`, 'Run Not Reviewable');
        updateUrlParams('replace');
        return;
    }

    try {
        const docRes = await API.fetchDocuments(runId);
        if (seq !== _actionSeq) return;
        State.documents = docRes.documents || [];

        if (State.documents.length === 0) {
            elements.docSelector.innerHTML = '<option value="">No documents found</option>';
            renderShellError(`No documents available in run ${runId}.`, 'No Documents Available');
            updateUrlParams('replace');
            return;
        }

        elements.docSelector.innerHTML = State.documents.map(d => {
            const label = [d.accession_number, d.document_title].filter(Boolean).join(' - ') || d.target_id;
            return `<option value="${escapeHtml(d.target_id)}">${escapeHtml(label)}</option>`;
        }).join('');
        elements.docSelector.disabled = false;

        // Determine target
        if (!targetIdOverride) {
            await loadTargetDoc(State.documents[0].target_id, seq);
            return;
        }

        if (!State.documents.some(d => d.target_id === targetIdOverride)) {
            State.selectedTargetId = targetIdOverride;
            elements.docSelector.value = "";
            renderShellError(`Document ${targetIdOverride} is not available in run ${runId}.`, 'Document Not Available');
            updateUrlParams('replace');
            return;
        }

        await loadTargetDoc(targetIdOverride, seq);
    } catch (err) {
        if (seq !== _actionSeq) return;
        elements.docSelector.innerHTML = '<option value="">Error</option>';
        renderShellError(`Failed to fetch documents for run ${runId}.`, 'Error Loading Documents');
    }
}

window.addEventListener('popstate', (e) => {
    // History back/forward handler
    if (e.state) {
        const seq = ++_actionSeq;
        if (State.selectedRunId !== e.state.runId || State.selectedTargetId !== e.state.targetId) {
            State.activeTab = e.state.tab || 'summary';
            loadRun(e.state.runId, e.state.targetId, seq);
        } else if (State.activeTab !== e.state.tab) {
            // Same run+target, different tab: apply tab state through the shared path
            window.switchTab(e.state.tab || 'summary', false);
        }
    }
});

async function init() {
    const urlParams = new URLSearchParams(window.location.search);
    const initialRunId = urlParams.get('run_id');
    const initialTargetId = urlParams.get('target_id');
    State.activeTab = urlParams.get('tab') || 'summary';
    
    // Setup theme listeners
    elements.themeSelector.value = State.themePreference;
    elements.themeSelector.addEventListener('change', (e) => applyThemePreference(e.target.value));
    if (systemThemeQuery) {
        systemThemeQuery.addEventListener?.('change', () => {
            if (State.themePreference === 'system') applyThemePreference('system', { persist: false });
        });
    }

    // Setup Selectors
    elements.runSelector.addEventListener('change', (e) => {
        const seq = ++_actionSeq;
        State.activeTab = 'summary'; // Reset tab on new run
        loadRun(e.target.value, null, seq);
    });
    elements.docSelector.addEventListener('change', (e) => {
        const seq = ++_actionSeq;
        loadTargetDoc(e.target.value, seq);
    });

    const seq = ++_actionSeq;
    try {
        const data = await API.fetchRuns();
        if (seq !== _actionSeq) return;
        
        State.runs = data.runs;
        elements.runSelector.innerHTML = State.runs.map(r => {
            const disabled = !r.reviewable ? ' disabled' : '';
            const suffix = !r.reviewable ? ` (${escapeHtml(r.disabled_reason_code || 'not reviewable')})` : '';
            return `<option value="${escapeHtml(r.run_id)}"${disabled}>${escapeHtml(r.display_label || r.run_id)}${suffix}</option>`;
        }).join('');

        let runToLoad = initialRunId;
        if (!runToLoad || !State.runs.some(r => r.run_id === runToLoad)) {
            runToLoad = data.default_run_id || State.runs[0]?.run_id;
        }

        if (runToLoad) {
            await loadRun(runToLoad, initialTargetId, seq);
        } else {
            elements.runSelector.innerHTML = '<option value="">No runs available</option>';
            renderShellError('No NRC APS runs are available.', 'No Runs Available');
        }
    } catch (err) {
        if (seq !== _actionSeq) return;
        renderShellError('Failed to load the run catalog.', 'Error');
    }
}

document.addEventListener('DOMContentLoaded', init);
