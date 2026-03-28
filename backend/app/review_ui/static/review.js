const State = {
    runs: [],
    selectedRunId: null,
    viewMode: 'run_heavy',
    pipelineDefinition: null,
    overview: null,
    selectedNodeId: null,
    selectedTreeId: null,
    openTreeIds: new Set(),
};

const elements = {
    runSelector: document.getElementById('run-selector'),
    viewPipeline: document.getElementById('view-pipeline'),
    viewRunLight: document.getElementById('view-run-light'),
    viewRunHeavy: document.getElementById('view-run-heavy'),
    mermaidContainer: document.getElementById('mermaid-container'),
    fileTree: document.getElementById('file-tree'),
    treePaneHeader: document.querySelector('#tree-pane .pane-header'),
    detailsDrawer: document.getElementById('details-drawer'),
    detailsContent: document.getElementById('details-content'),
    closeDrawerBtn: document.getElementById('close-drawer'),
    disabledOverlay: document.getElementById('disabled-overlay'),
    disabledReason: document.getElementById('disabled-reason'),
};

const API = {
    async fetchRuns() {
        const res = await fetch('/api/v1/review/nrc-aps/runs');
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return await res.json();
    },
    async fetchOverview(runId) {
        const res = await fetch(`/api/v1/review/nrc-aps/runs/${runId}/overview`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return await res.json();
    },
    async fetchPipelineDefinition(runId) {
        const res = await fetch(`/api/v1/review/nrc-aps/pipeline-definition?run_id=${encodeURIComponent(runId)}`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return await res.json();
    },
    async fetchNodeDetails(runId, nodeId) {
        const res = await fetch(`/api/v1/review/nrc-aps/runs/${runId}/nodes/${nodeId}`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return await res.json();
    },
    async fetchFileDetails(runId, treeId) {
        const res = await fetch(`/api/v1/review/nrc-aps/runs/${runId}/files/${encodeURIComponent(treeId)}`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return await res.json();
    },
    async fetchFilePreview(runId, treeId) {
        const res = await fetch(`/api/v1/review/nrc-aps/runs/${runId}/files/${encodeURIComponent(treeId)}/preview`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return await res.json();
    },
};

let panZoomInstance = null;

function escapeMermaidLabel(label) {
    return String(label ?? '').replace(/"/g, '&quot;');
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatValue(value) {
    if (typeof value === 'object' && value !== null) {
        return `<pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
    }
    return escapeHtml(String(value));
}

function isPipelineMode() {
    return State.viewMode === 'pipeline';
}

function isRunLightMode() {
    return State.viewMode === 'run_light';
}

function isRunHeavyMode() {
    return State.viewMode === 'run_heavy';
}

function buildCanonicalProjection() {
    const graph = State.pipelineDefinition?.canonical_graph;
    if (!graph) return null;
    return {
        projection_id: graph.pipeline_id || 'nrc_aps_canonical_pipeline',
        nodes: graph.nodes.map((node) => ({
            projection_id: node.node_id,
            title: node.label,
            detail_lines: [],
            stage_family: node.stage_family,
            canonical_node_ids: [node.node_id],
            state: 'unknown',
            warnings: [],
            mapped_file_refs: [],
            mapped_tree_ids: [],
            artifact_refs: [],
            structured_summary: {
                description: node.description || '',
                expected_artifact_classes: node.expected_artifact_classes || [],
            },
            is_composite: false,
        })),
        edges: graph.edges.map((edge) => ({ source_id: edge.source_id, target_id: edge.target_id })),
    };
}

function currentGraph() {
    if (isPipelineMode()) {
        return buildCanonicalProjection();
    }
    if (isRunLightMode()) {
        return State.pipelineDefinition?.pipeline_projection ?? null;
    }
    return State.overview?.run_projection ?? null;
}

function findCurrentNode(nodeId) {
    const graph = currentGraph();
    return graph?.nodes?.find((node) => node.projection_id === nodeId) ?? null;
}

function nodeMermaidLabel(node) {
    const lines = [node.title, ...(node.detail_lines || []), ...((node.warnings || []).slice(0, 2).map((warning) => `[!] ${warning}`))];
    return lines.filter(Boolean).join('<br/>');
}

function projectionClasses(node) {
    const classes = [`state_${node.state || 'unknown'}`];
    if (node.is_composite) classes.push('projection_composite');
    else if (isPipelineMode()) classes.push('projection_canonical');
    else if (isRunLightMode()) classes.push('projection_light');
    else classes.push('projection_heavy');
    if (State.selectedNodeId === node.projection_id) classes.push('selected');
    return classes;
}

function buildMermaidText(graph) {
    let text = 'flowchart TD\n';
    text += '    classDef state_complete fill:#e5f7ec,stroke:#20864f,stroke-width:2px;\n';
    text += '    classDef state_missing fill:#fde8e8,stroke:#b42318,stroke-width:2px,stroke-dasharray:5 3;\n';
    text += '    classDef state_mismatch fill:#fff4d7,stroke:#b54708,stroke-width:2px;\n';
    text += '    classDef state_unknown fill:#eef2ff,stroke:#4f46e5,stroke-width:2px;\n';
    text += '    classDef projection_canonical fill:#ffffff,stroke:#4f46e5,stroke-width:1.75px,color:#1f2557;\n';
    text += '    classDef projection_light fill:#f6f8fc,stroke:#506176,stroke-width:1.75px,color:#18212f;\n';
    text += '    classDef projection_heavy fill:#f8fff9,stroke:#1f7a45,stroke-width:1.5px,color:#10261a;\n';
    text += '    classDef projection_composite fill:#eef4fb,stroke:#315ea8,stroke-width:2.5px,color:#10233f;\n';
    text += '    classDef selected fill:#dbeafe,stroke:#1d4ed8,stroke-width:4px;\n';

    graph.nodes.forEach((node) => {
        text += `    ${node.projection_id}["${escapeMermaidLabel(nodeMermaidLabel(node))}"]\n`;
        text += `    click ${node.projection_id} handleNodeClick\n`;
        text += `    class ${node.projection_id} ${projectionClasses(node).join(',')}\n`;
    });
    graph.edges.forEach((edge) => {
        text += `    ${edge.source_id} --> ${edge.target_id}\n`;
    });
    return text;
}

async function renderGraph() {
    const graph = currentGraph();
    if (!graph || !graph.nodes || !graph.edges) {
        elements.mermaidContainer.innerHTML = '<div class="graph-placeholder">No graph data available.</div>';
        return;
    }

    elements.mermaidContainer.innerHTML = '<div class="graph-placeholder">Rendering graph...</div>';
    try {
        const renderId = `nrc-aps-graph-${Date.now()}`;
        const rendered = await mermaid.render(renderId, buildMermaidText(graph));
        elements.mermaidContainer.innerHTML = rendered.svg;
        if (typeof rendered.bindFunctions === 'function') rendered.bindFunctions(elements.mermaidContainer);
        const svgElement = elements.mermaidContainer.querySelector('svg');
        if (!svgElement) throw new Error('Graph render returned no SVG output.');
        svgElement.setAttribute('width', '100%');
        svgElement.setAttribute('height', '100%');
        if (panZoomInstance) panZoomInstance.destroy();
        panZoomInstance = svgPanZoom(svgElement, {
            zoomEnabled: true,
            controlIconsEnabled: true,
            fit: true,
            center: true,
            minZoom: 0.45,
        });
    } catch (error) {
        elements.mermaidContainer.innerHTML = `<pre class="warning">Graph render failed: ${escapeHtml(error.message)}</pre>`;
    }
}

window.handleNodeClick = async (nodeId) => {
    State.selectedNodeId = nodeId;
    if (isRunHeavyMode()) {
        State.selectedTreeId = null;
        await renderGraph();
        renderSidePane();
        await loadDetails('node', nodeId);
        return;
    }
    if (isRunLightMode()) {
        State.selectedTreeId = null;
        await renderGraph();
        renderSidePane();
        const node = findCurrentNode(nodeId);
        if (node?.is_composite) {
            renderProjectionNodeDetails(node);
            return;
        }
        await loadDetails('node', nodeId);
        return;
    }
    await renderGraph();
    renderSidePane();
    renderPipelineNodeDetails(nodeId);
};

function buildTreeElement(node, depth = 0) {
    const li = document.createElement('li');
    const mappedToSelectedNode = State.selectedNodeId && (node.mapped_node_ids || []).includes(State.selectedNodeId);
    const isOpen = Boolean(node.is_dir && (depth === 0 || mappedToSelectedNode || State.openTreeIds.has(node.tree_id)));
    li.classList.toggle('dir', Boolean(node.is_dir));
    li.classList.toggle('selected', State.selectedTreeId === node.tree_id);
    li.classList.toggle('mapped', Boolean(mappedToSelectedNode));
    li.classList.toggle('open', isOpen);
    li.dataset.treeId = node.tree_id;

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'tree-entry';
    button.dataset.treeId = node.tree_id;
    button.dataset.isDir = String(Boolean(node.is_dir));
    button.dataset.mappedNodeIds = JSON.stringify(node.mapped_node_ids || []);
    button.textContent = node.name;
    li.appendChild(button);

    if (node.is_dir && node.children && node.children.length > 0) {
        const ul = document.createElement('ul');
        node.children.forEach((child) => ul.appendChild(buildTreeElement(child, depth + 1)));
        li.appendChild(ul);
    }
    return li;
}

function renderPipelineLayout() {
    const layout = State.overview?.pipeline_layout;
    elements.treePaneHeader.textContent = 'Pipeline Layout Summary';
    if (!layout || !layout.sections) {
        elements.fileTree.innerHTML = '<li>No layout summary available</li>';
        return;
    }
    const wrapper = document.createElement('div');
    wrapper.className = 'layout-summary';
    layout.sections.forEach((section) => {
        const block = document.createElement('section');
        block.className = 'layout-section';
        const title = document.createElement('h3');
        title.textContent = section.title;
        block.appendChild(title);
        const list = document.createElement('ul');
        section.entries.forEach((entry) => {
            const li = document.createElement('li');
            li.className = 'layout-entry';
            if (entry.path) li.classList.toggle('mapped', Boolean(State.selectedNodeId && findCurrentNode(State.selectedNodeId)?.mapped_file_refs?.includes(entry.path)));
            li.innerHTML = `<strong>${escapeHtml(entry.label)}</strong><span>${escapeHtml(entry.value)}</span>`;
            list.appendChild(li);
        });
        block.appendChild(list);
        wrapper.appendChild(block);
    });
    elements.fileTree.innerHTML = '';
    const li = document.createElement('li');
    li.className = 'layout-shell';
    li.appendChild(wrapper);
    elements.fileTree.appendChild(li);
}

function renderTree() {
    elements.treePaneHeader.textContent = 'Strict Filesystem Tree';
    if (!State.overview?.tree?.root) {
        elements.fileTree.innerHTML = '<li>No tree data available</li>';
        return;
    }
    elements.fileTree.innerHTML = '';
    const rootNode = State.overview.tree.root;
    State.openTreeIds.add(rootNode.tree_id);
    elements.fileTree.appendChild(buildTreeElement(rootNode));
}

function renderSidePane() {
    if (isRunHeavyMode()) {
        renderTree();
        return;
    }
    renderPipelineLayout();
}

async function handleTreeClick(button) {
    const treeId = button.dataset.treeId;
    const isDir = button.dataset.isDir === 'true';
    const mappedNodeIds = JSON.parse(button.dataset.mappedNodeIds || '[]');
    if (isDir) {
        if (State.openTreeIds.has(treeId)) State.openTreeIds.delete(treeId);
        else State.openTreeIds.add(treeId);
    }
    State.selectedTreeId = treeId;
    if (!isDir && mappedNodeIds.length > 0) State.selectedNodeId = mappedNodeIds[0];
    renderSidePane();
    if (State.selectedNodeId) await renderGraph();
    if (!isDir) await loadDetails('file', treeId);
}

function openDrawer() { elements.detailsDrawer.classList.add('open'); }
function closeDrawer() { elements.detailsDrawer.classList.remove('open'); }

function renderPipelineNodeDetails(nodeId) {
    const node = findCurrentNode(nodeId);
    if (!node) return;
    let html = `<h3>${escapeHtml(node.title)}</h3><dl>`;
    html += `<dt>Projection ID</dt><dd>${escapeHtml(node.projection_id)}</dd>`;
    html += `<dt>Canonical Nodes</dt><dd>${escapeHtml((node.canonical_node_ids || []).join(', '))}</dd>`;
    html += `<dt>Stage Family</dt><dd>${escapeHtml(node.stage_family)}</dd>`;
    const description = node.structured_summary?.description;
    if (description) {
        html += `<dt>Description</dt><dd>${escapeHtml(description)}</dd>`;
    }
    const expectedArtifacts = node.structured_summary?.expected_artifact_classes || [];
    if (expectedArtifacts.length) {
        html += `<dt>Expected Artifact Classes</dt><dd>${escapeHtml(expectedArtifacts.join(', '))}</dd>`;
    }
    html += '</dl>';
    elements.detailsContent.innerHTML = html;
    openDrawer();
}

function renderProjectionNodeDetails(node) {
    let html = `<h3>${escapeHtml(node.title)}</h3><dl>`;
    html += `<dt>Projection ID</dt><dd>${escapeHtml(node.projection_id)}</dd>`;
    html += `<dt>Canonical Nodes</dt><dd>${escapeHtml((node.canonical_node_ids || []).join(', '))}</dd>`;
    html += `<dt>Stage Family</dt><dd>${escapeHtml(node.stage_family)}</dd>`;
    if (node.detail_lines?.length) {
        html += '<dt>Summary</dt><dd><ul>';
        node.detail_lines.forEach((line) => { html += `<li>${escapeHtml(line)}</li>`; });
        html += '</ul></dd>';
    }
    if (node.warnings?.length) {
        html += `<dt class="warning">Warnings</dt><dd class="warning">${node.warnings.map(escapeHtml).join('<br>')}</dd>`;
    }
    if (node.mapped_file_refs?.length) {
        html += '<dt>Mapped Files</dt><dd><ul>';
        node.mapped_file_refs.forEach((ref) => { html += `<li>${escapeHtml(ref)}</li>`; });
        html += '</ul></dd>';
    }
    if (node.structured_summary && Object.keys(node.structured_summary).length) {
        html += '<dt>Structured Summary</dt><dd><ul>';
        Object.entries(node.structured_summary).forEach(([key, value]) => {
            html += `<li><strong>${escapeHtml(key)}:</strong> ${formatValue(value)}</li>`;
        });
        html += '</ul></dd>';
    }
    html += '</dl>';
    elements.detailsContent.innerHTML = html;
    openDrawer();
}

function renderDetails(data, type) {
    let html = '';
    if (type === 'node') {
        html += `<h3>${escapeHtml(data.label)}</h3><dl>`;
        html += `<dt>ID</dt><dd>${escapeHtml(data.node_id)}</dd>`;
        html += `<dt>Stage Family</dt><dd>${escapeHtml(data.stage_family)}</dd>`;
        html += `<dt>State</dt><dd>${escapeHtml(data.state)}</dd>`;
        if (data.warnings?.length) html += `<dt class="warning">Warnings</dt><dd class="warning">${data.warnings.map(escapeHtml).join('<br>')}</dd>`;
        if (data.mapped_file_refs?.length) {
            html += '<dt>Mapped Files</dt><dd><ul>';
            data.mapped_file_refs.forEach((ref) => { html += `<li>${escapeHtml(ref)}</li>`; });
            html += '</ul></dd>';
        }
        if (data.structured_summary && Object.keys(data.structured_summary).length) {
            html += '<dt>Summary Metrics</dt><dd><ul>';
            Object.entries(data.structured_summary).forEach(([key, value]) => { html += `<li><strong>${escapeHtml(key)}:</strong> ${formatValue(value)}</li>`; });
            html += '</ul></dd>';
        }
        html += '</dl>';
    } else {
        html += `<h3>${escapeHtml(data.name)}</h3><dl>`;
        html += `<dt>Path</dt><dd>${escapeHtml(data.path)}</dd>`;
        html += `<dt>Size</dt><dd>${data.size_bytes ? `${data.size_bytes} bytes` : '-'}</dd>`;
        html += `<dt>Modified</dt><dd>${data.modified_time ? new Date(parseFloat(data.modified_time) * 1000).toLocaleString() : '-'}</dd>`;
        if (data.mapped_node_ids?.length) html += `<dt>Mapped Nodes</dt><dd>${escapeHtml(data.mapped_node_ids.join(', '))}</dd>`;
        if (data.preview_available) html += `<dt>Preview</dt><dd><div id="file-preview-container" class="preview-container loading">Loading ${escapeHtml(data.preview_kind)} preview...</div></dd>`;
        if (data.structured_summary && Object.keys(data.structured_summary).length) {
            html += '<dt>Metadata Summary</dt><dd><ul>';
            Object.entries(data.structured_summary).forEach(([key, value]) => { html += `<li><strong>${escapeHtml(key)}:</strong> ${formatValue(value)}</li>`; });
            html += '</ul></dd>';
        }
        html += '</dl>';
    }
    elements.detailsContent.innerHTML = html;
    openDrawer();
}

function renderFilePreview(preview) {
    const container = document.getElementById('file-preview-container');
    if (!container) return;
    const truncatedNote = preview.truncated ? `<div class="preview-note">Preview truncated to ${preview.max_chars} characters.</div>` : '';
    container.classList.remove('loading');
    container.innerHTML = `<div class="preview-meta">${escapeHtml(preview.preview_kind.toUpperCase())} preview</div>${truncatedNote}<pre class="preview-block"><code class="language-${escapeHtml(preview.language)}">${escapeHtml(preview.content)}</code></pre>`;
}

function renderPreviewError(message) {
    const container = document.getElementById('file-preview-container');
    if (!container) return;
    container.classList.remove('loading');
    container.innerHTML = `<div class="warning">${escapeHtml(message)}</div>`;
}

async function loadDetails(type, id) {
    try {
        elements.detailsContent.innerHTML = '<p>Loading details...</p>';
        openDrawer();
        if (type === 'node') {
            const data = await API.fetchNodeDetails(State.selectedRunId, id);
            renderDetails(data, 'node');
        } else {
            const data = await API.fetchFileDetails(State.selectedRunId, id);
            renderDetails(data, 'file');
            if (data.preview_available) {
                try {
                    renderFilePreview(await API.fetchFilePreview(State.selectedRunId, id));
                } catch (previewError) {
                    renderPreviewError(`Preview unavailable: ${previewError.message}`);
                }
            }
        }
    } catch (error) {
        elements.detailsContent.innerHTML = `<p class="warning">Error loading details: ${escapeHtml(error.message)}</p>`;
    }
}

async function loadRun(runId) {
    State.selectedRunId = runId;
    State.selectedNodeId = null;
    State.selectedTreeId = null;
    State.openTreeIds = new Set();
    closeDrawer();

    const runInfo = State.runs.find((run) => run.run_id === runId);
    if (runInfo && !runInfo.reviewable) {
        elements.disabledOverlay.classList.remove('hidden');
        elements.disabledReason.textContent = runInfo.disabled_reason_code || 'Unknown reason';
        State.pipelineDefinition = null;
        State.overview = null;
        await renderGraph();
        renderSidePane();
        return;
    }

    elements.disabledOverlay.classList.add('hidden');
    try {
        const [pipelineDefinition, overview] = await Promise.all([API.fetchPipelineDefinition(runId), API.fetchOverview(runId)]);
        State.pipelineDefinition = pipelineDefinition;
        State.overview = overview;
        await renderGraph();
        renderSidePane();
    } catch (error) {
        elements.disabledOverlay.classList.remove('hidden');
        elements.disabledReason.textContent = 'Failed to load overview payload.';
    }
}

async function setViewMode(viewMode) {
    State.viewMode = viewMode;
    State.selectedNodeId = null;
    if (!isRunHeavyMode()) State.selectedTreeId = null;
    closeDrawer();
    await renderGraph();
    renderSidePane();
}

async function init() {
    mermaid.initialize({ startOnLoad: false, securityLevel: 'loose', flowchart: { useMaxWidth: false, htmlLabels: true } });

    elements.runSelector.addEventListener('change', async (event) => { await loadRun(event.target.value); });
    elements.viewPipeline.addEventListener('change', async () => { await setViewMode('pipeline'); });
    elements.viewRunLight.addEventListener('change', async () => { await setViewMode('run_light'); });
    elements.viewRunHeavy.addEventListener('change', async () => { await setViewMode('run_heavy'); });
    elements.fileTree.addEventListener('click', async (event) => {
        const button = event.target.closest('button.tree-entry');
        if (!button || !isRunHeavyMode()) return;
        event.preventDefault();
        await handleTreeClick(button);
    });
    elements.closeDrawerBtn.addEventListener('click', closeDrawer);

    try {
        const data = await API.fetchRuns();
        State.runs = data.runs;
        elements.runSelector.innerHTML = data.runs.map((run) => (
            `<option value="${run.run_id}" ${!run.reviewable ? 'disabled' : ''}>${escapeHtml(run.display_label || run.run_id)}${!run.reviewable ? ` (${escapeHtml(run.disabled_reason_code)})` : ''}</option>`
        )).join('');
        const defaultRun = data.default_run_id || data.runs[0]?.run_id;
        if (defaultRun) {
            elements.runSelector.value = defaultRun;
            await loadRun(defaultRun);
        } else {
            elements.runSelector.innerHTML = '<option>No NRC APS runs found</option>';
            elements.disabledOverlay.classList.remove('hidden');
            elements.disabledReason.textContent = 'No runs available.';
        }
    } catch (error) {
        elements.disabledOverlay.classList.remove('hidden');
        elements.disabledReason.textContent = 'Failed to load run catalog.';
    }
}

document.addEventListener('DOMContentLoaded', init);
