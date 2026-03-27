/**
 * NRC APS Review UI Controller
 */

const State = {
    runs: [],
    selectedRunId: null,
    viewMode: 'run',
    graphData: null,
    treeData: null,
    selectedNodeId: null,
    selectedTreeId: null,
    openTreeIds: new Set(),
};

const elements = {
    runSelector: document.getElementById('run-selector'),
    viewGeneral: document.getElementById('view-general'),
    viewRun: document.getElementById('view-run'),
    mermaidContainer: document.getElementById('mermaid-container'),
    fileTree: document.getElementById('file-tree'),
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
    async fetchPipelineDefinition() {
        const res = await fetch('/api/v1/review/nrc-aps/pipeline-definition');
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
};

let panZoomInstance = null;

function escapeMermaidLabel(label) {
    return String(label ?? '').replace(/"/g, '&quot;');
}

function renderGraphClasses(graph, nodeStates = {}) {
    let mermaidText = 'flowchart TD\n';
    mermaidText += '    classDef state_complete fill:#d9f2e3,stroke:#1f7a45,stroke-width:2px;\n';
    mermaidText += '    classDef state_missing fill:#fbe3e6,stroke:#b42318,stroke-width:2px,stroke-dasharray:5 3;\n';
    mermaidText += '    classDef state_not_exercised fill:#eceff3,stroke:#6b7280,stroke-width:2px,stroke-dasharray:3 3;\n';
    mermaidText += '    classDef state_unknown fill:#eef2ff,stroke:#4f46e5,stroke-width:2px;\n';
    mermaidText += '    classDef selected fill:#dbeafe,stroke:#1d4ed8,stroke-width:4px;\n';

    graph.nodes.forEach((node) => {
        const stateInfo = nodeStates[node.node_id] || { state: 'unknown', warnings: [] };
        let labelSuffix = '';
        if ((stateInfo.warnings || []).length > 0) {
            labelSuffix = ' [!]';
        } else if (stateInfo.state === 'missing') {
            labelSuffix = ' [x]';
        }

        mermaidText += `    ${node.node_id}["${escapeMermaidLabel(node.label + labelSuffix)}"]\n`;
        mermaidText += `    click ${node.node_id} handleNodeClick\n`;
        mermaidText += `    class ${node.node_id} state_${stateInfo.state || 'unknown'}\n`;
        if (State.selectedNodeId === node.node_id) {
            mermaidText += `    class ${node.node_id} selected\n`;
        }
    });

    graph.edges.forEach((edge) => {
        mermaidText += `    ${edge.source_id} --> ${edge.target_id}\n`;
    });

    return mermaidText;
}

async function renderGraph() {
    if (!State.graphData) {
        elements.mermaidContainer.innerHTML = '<div class="graph-placeholder">No graph data available.</div>';
        return;
    }

    const graph = State.viewMode === 'general'
        ? (State.graphData.canonical_graph || State.graphData)
        : State.graphData.graph?.canonical_graph;

    const nodeStates = State.viewMode === 'general'
        ? {}
        : (State.graphData.graph?.node_states || {});

    if (!graph || !graph.nodes || !graph.edges) {
        elements.mermaidContainer.innerHTML = '<div class="graph-placeholder">No graph data available.</div>';
        return;
    }

    const mermaidText = renderGraphClasses(graph, nodeStates);
    elements.mermaidContainer.innerHTML = '<div class="graph-placeholder">Rendering graph...</div>';

    try {
        const renderId = `nrc-aps-graph-${Date.now()}`;
        const rendered = await mermaid.render(renderId, mermaidText);
        elements.mermaidContainer.innerHTML = rendered.svg;
        if (typeof rendered.bindFunctions === 'function') {
            rendered.bindFunctions(elements.mermaidContainer);
        }

        const svgElement = elements.mermaidContainer.querySelector('svg');
        if (!svgElement) {
            elements.mermaidContainer.innerHTML = '<div class="graph-placeholder">Graph render returned no SVG output.</div>';
            return;
        }

        svgElement.setAttribute('width', '100%');
        svgElement.setAttribute('height', '100%');

        if (panZoomInstance) {
            panZoomInstance.destroy();
        }
        panZoomInstance = svgPanZoom(svgElement, {
            zoomEnabled: true,
            controlIconsEnabled: true,
            fit: true,
            center: true,
            minZoom: 0.5,
        });
    } catch (error) {
        console.error('Mermaid parsing error', error);
        elements.mermaidContainer.innerHTML = `<pre class="warning">Graph render failed: ${error.message}</pre>`;
    }
}

window.handleNodeClick = async (nodeId) => {
    State.selectedNodeId = nodeId;
    State.selectedTreeId = null;
    await renderGraph();
    renderTree();
    await loadDetails('node', nodeId);
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
        node.children.forEach((child) => {
            ul.appendChild(buildTreeElement(child, depth + 1));
        });
        li.appendChild(ul);
    }

    return li;
}

function renderTree() {
    if (!State.treeData || !State.treeData.tree || !State.treeData.tree.root) {
        elements.fileTree.innerHTML = '<li>No tree data available</li>';
        return;
    }

    elements.fileTree.innerHTML = '';
    const rootNode = State.treeData.tree.root;
    State.openTreeIds.add(rootNode.tree_id);
    elements.fileTree.appendChild(buildTreeElement(rootNode));
}

async function handleTreeClick(button) {
    const treeId = button.dataset.treeId;
    const isDir = button.dataset.isDir === 'true';
    const mappedNodeIds = JSON.parse(button.dataset.mappedNodeIds || '[]');

    if (isDir) {
        if (State.openTreeIds.has(treeId)) {
            State.openTreeIds.delete(treeId);
        } else {
            State.openTreeIds.add(treeId);
        }
    }

    State.selectedTreeId = treeId;
    if (!isDir && mappedNodeIds.length > 0) {
        State.selectedNodeId = mappedNodeIds[0];
    }

    renderTree();
    if (State.selectedNodeId) {
        await renderGraph();
    }

    if (!isDir) {
        await loadDetails('file', treeId);
    }
}

function openDrawer() {
    elements.detailsDrawer.classList.add('open');
}

function closeDrawer() {
    elements.detailsDrawer.classList.remove('open');
}

function formatValue(value) {
    if (typeof value === 'object' && value !== null) {
        return `<pre>${JSON.stringify(value, null, 2)}</pre>`;
    }
    return String(value);
}

function renderDetails(data, type) {
    let html = '';

    if (type === 'node') {
        html += `<h3>${data.label}</h3>`;
        html += `<dl>
            <dt>ID</dt><dd>${data.node_id}</dd>
            <dt>Stage Family</dt><dd>${data.stage_family}</dd>
            <dt>State</dt><dd>${data.state}</dd>`;

        if (data.warnings && data.warnings.length > 0) {
            html += `<dt class="warning">Warnings</dt><dd class="warning">${data.warnings.join('<br>')}</dd>`;
        }

        if (data.mapped_file_refs && data.mapped_file_refs.length > 0) {
            html += '<dt>Mapped Files</dt><dd><ul>';
            data.mapped_file_refs.forEach((ref) => {
                html += `<li>${ref}</li>`;
            });
            html += '</ul></dd>';
        }

        if (data.structured_summary && Object.keys(data.structured_summary).length > 0) {
            html += '<dt>Summary Metrics</dt><dd><ul>';
            Object.entries(data.structured_summary).forEach(([key, value]) => {
                html += `<li><strong>${key}:</strong> ${formatValue(value)}</li>`;
            });
            html += '</ul></dd>';
        }
        html += '</dl>';
    } else if (type === 'file') {
        html += `<h3>${data.name}</h3>`;
        html += `<dl>
            <dt>Path</dt><dd>${data.path}</dd>
            <dt>Size</dt><dd>${data.size_bytes ? `${data.size_bytes} bytes` : '-'}</dd>
            <dt>Modified</dt><dd>${data.modified_time ? new Date(parseFloat(data.modified_time) * 1000).toLocaleString() : '-'}</dd>`;

        if (data.mapped_node_ids && data.mapped_node_ids.length > 0) {
            html += `<dt>Mapped Nodes</dt><dd>${data.mapped_node_ids.join(', ')}</dd>`;
        }

        if (data.structured_summary && Object.keys(data.structured_summary).length > 0) {
            html += '<dt>Metadata Summary</dt><dd><ul>';
            Object.entries(data.structured_summary).forEach(([key, value]) => {
                html += `<li><strong>${key}:</strong> ${formatValue(value)}</li>`;
            });
            html += '</ul></dd>';
        }
        html += '</dl>';
    }

    elements.detailsContent.innerHTML = html;
    openDrawer();
}

async function loadDetails(type, id) {
    try {
        elements.detailsContent.innerHTML = '<p>Loading details...</p>';
        openDrawer();

        if (type === 'node') {
            const data = await API.fetchNodeDetails(State.selectedRunId, id);
            renderDetails(data, 'node');
        } else if (type === 'file') {
            const data = await API.fetchFileDetails(State.selectedRunId, id);
            renderDetails(data, 'file');
        }
    } catch (error) {
        elements.detailsContent.innerHTML = `<p class="warning">Error loading details: ${error.message}</p>`;
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
        State.graphData = null;
        State.treeData = null;
        await renderGraph();
        renderTree();
        return;
    }

    elements.disabledOverlay.classList.add('hidden');

    try {
        if (State.viewMode === 'general') {
            State.graphData = await API.fetchPipelineDefinition();
            State.treeData = await API.fetchOverview(runId);
        } else {
            const overview = await API.fetchOverview(runId);
            State.graphData = overview;
            State.treeData = overview;
        }
        await renderGraph();
        renderTree();
    } catch (error) {
        console.error('Failed to load run data', error);
        elements.disabledOverlay.classList.remove('hidden');
        elements.disabledReason.textContent = 'Failed to load overview payload.';
    }
}

async function init() {
    mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'loose',
        flowchart: { useMaxWidth: false, htmlLabels: true },
    });

    elements.runSelector.addEventListener('change', async (event) => {
        await loadRun(event.target.value);
    });

    elements.viewGeneral.addEventListener('change', async () => {
        State.viewMode = 'general';
        await loadRun(State.selectedRunId);
    });

    elements.viewRun.addEventListener('change', async () => {
        State.viewMode = 'run';
        await loadRun(State.selectedRunId);
    });

    elements.fileTree.addEventListener('click', async (event) => {
        const button = event.target.closest('button.tree-entry');
        if (!button) {
            return;
        }
        event.preventDefault();
        await handleTreeClick(button);
    });

    elements.closeDrawerBtn.addEventListener('click', closeDrawer);

    try {
        const data = await API.fetchRuns();
        State.runs = data.runs;
        elements.runSelector.innerHTML = data.runs.map((run) => (
            `<option value="${run.run_id}" ${!run.reviewable ? 'disabled' : ''}>${run.display_label || run.run_id}${!run.reviewable ? ` (${run.disabled_reason_code})` : ''}</option>`
        )).join('');

        if (data.default_run_id) {
            elements.runSelector.value = data.default_run_id;
            await loadRun(data.default_run_id);
        } else if (data.runs.length > 0) {
            elements.runSelector.value = data.runs[0].run_id;
            await loadRun(data.runs[0].run_id);
        } else {
            elements.runSelector.innerHTML = '<option>No NRC APS runs found</option>';
            elements.disabledOverlay.classList.remove('hidden');
            elements.disabledReason.textContent = 'No runs available.';
        }
    } catch (error) {
        console.error('Initialization failed', error);
        elements.disabledOverlay.classList.remove('hidden');
        elements.disabledReason.textContent = 'Failed to load run catalog.';
    }
}

document.addEventListener('DOMContentLoaded', init);
