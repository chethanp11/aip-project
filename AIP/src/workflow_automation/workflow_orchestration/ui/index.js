
let workflowsMap = {};
let selectedDag = null;

async function fetchWorkflows() {
    const selector = document.getElementById('workflow-selector');
    selector.innerHTML = '<option value="">⏳ Fetching KMS Registry...</option>';
    
    try {
        const res = await fetch(`${API_BASE}/kms/canonical`);
        const data = await res.json();
        
        // Filter workflows (entries with tag workflow or title Workflow:)
        const workflows = data.filter(item => 
            (item.tags && item.tags.includes('workflow')) || 
            (item.title && item.title.startsWith('Workflow:'))
        );
        
        selector.innerHTML = '<option value="">-- Select Designed Workflow from KMS --</option>';
        workflowsMap = {};
        
        if (workflows.length === 0) {
            selector.innerHTML = '<option value="">⚠️ No workflows registered in KMS yet.</option>';
            return;
        }
        
        workflows.forEach(wf => {
            try {
                const parsedContent = JSON.parse(wf.content);
                workflowsMap[wf.node_id] = parsedContent;
                
                const opt = document.createElement('option');
                opt.value = wf.node_id;
                opt.textContent = `${parsedContent.name || wf.title} (${wf.node_id})`;
                selector.appendChild(opt);
            } catch(e) {
                console.warn(`Could not parse content for workflow node ${wf.node_id}:`, e);
            }
        });
    } catch(err) {
        selector.innerHTML = '<option value="">❌ Fetch failed. Retry.</option>';
        console.error(err);
    }
}

function handleWorkflowSelection(e) {
    const wfId = e.target.value;
    const flowchartBox = document.getElementById('dag-flowchart-box');
    const canvas = document.getElementById('dag-canvas');
    const btn = document.getElementById('orch-btn');
    
    document.getElementById('pause-alert').classList.add('hide');
    document.getElementById('orch-results').classList.add('hide');
    
    if (!wfId || !workflowsMap[wfId]) {
        selectedDag = null;
        flowchartBox.classList.add('hide');
        btn.disabled = true;
        return;
    }
    
    selectedDag = workflowsMap[wfId];
    flowchartBox.classList.remove('hide');
    btn.disabled = false;
    
    // Draw visual flowchart of selected DAG
    let nodeMap = {};
    selectedDag.nodes.forEach(n => nodeMap[n.id] = n);
    
    // Order topological
    let inDegree = {};
    selectedDag.nodes.forEach(n => inDegree[n.id] = 0);
    selectedDag.edges.forEach(e => {
        if (inDegree[e.target] !== undefined) inDegree[e.target]++;
    });
    
    let queue = selectedDag.nodes.filter(n => inDegree[n.id] === 0).map(n => n.id);
    let order = [];
    while (queue.length > 0) {
        let u = queue.shift();
        order.push(u);
        selectedDag.edges.forEach(e => {
            if (e.source === u) {
                inDegree[e.target]--;
                if (inDegree[e.target] === 0) queue.push(e.target);
            }
        });
    }
    
    selectedDag.nodes.forEach(n => {
        if (!order.includes(n.id)) order.push(n.id);
    });
    
    let html = [];
    order.forEach((nId, idx) => {
        const node = nodeMap[nId];
        if (!node) return;
        
        const isApp = node.requireApproval;
        html.push(`
            <div class="flow-node ${isApp ? 'approval' : ''}">
                <div style="font-size:9px; opacity:0.7;">${node.capability}</div>
                <div>${node.id}</div>
            </div>
        `);
        
        if (idx < order.length - 1) {
            html.push(`<div class="flow-arrow">➡️</div>`);
        }
    });
    
    canvas.innerHTML = html.join('');
}

async function executeWorkflow() {
    if (!selectedDag) return;
    
    const resultsBox = document.getElementById('orch-results');
    const container = document.getElementById('traces-container');
    const pauseAlert = document.getElementById('pause-alert');
    const btn = document.getElementById('orch-btn');
    
    pauseAlert.classList.add('hide');
    resultsBox.classList.remove('hide');
    container.innerHTML = '<div class="loader">⚙️ Initializing LangGraph state graph and driving execution loop...</div>';
    btn.disabled = true;
    
    try {
        const res = await fetch(`${API_BASE}/workflows/automation/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config: selectedDag })
        });
        
        const data = await res.json();
        btn.disabled = false;
        container.innerHTML = '';
        
        const traces = data.traces || [];
        if (traces.length === 0) {
            container.innerHTML = '<p style="color:#94a3b8; font-style:italic;">No step traces returned from orchestrator.</p>';
            return;
        }
        
        container.innerHTML = traces.map((t, idx) => {
            const isPaused = t.status === 'paused';
            const isFailed = t.status === 'failed';
            const statusClass = isPaused ? 'paused' : (isFailed ? 'failed' : 'completed');
            const detailStr = isFailed ? (t.error || 'Execution failed') : JSON.stringify(t.output, null, 2);
            
            return `
                <div class="trace-item">
                    <div class="trace-header">
                        <div>
                            <span style="color:#0ea5e9;">#${idx+1}</span> Step Node: <strong>${t.stepId}</strong>
                            <span style="font-size:11px; color:#64748b; margin-left:8px;">[Capability: ${t.capability}]</span>
                        </div>
                        <div style="display:flex; gap:12px; align-items:center;">
                            <span style="color:#94a3b8; font-size:11px;">${t.durationMs || 0}ms</span>
                            <span class="trace-status ${statusClass}">${t.status.toUpperCase()}</span>
                        </div>
                    </div>
                    <div class="mt-10">
                        <button class="btn" style="padding:4px 8px; font-size:10px; background:#334155; border:1px solid #475569;" onclick="toggleTraceDetail('${t.stepId}')">🔍 View Outputs</button>
                    </div>
                    <div class="trace-detail hide" id="detail-${t.stepId}">${detailStr}</div>
                </div>
            `;
        }).join('');
        
        if (data.paused) {
            pauseAlert.classList.remove('hide');
            document.getElementById('pause-node-id').textContent = selectedDag.nodes.find(n => n.requireApproval)?.id || 'Outbound Notifications';
            document.getElementById('pause-app-id').textContent = data.approvalId;
        }
    } catch(err) {
        btn.disabled = false;
        container.innerHTML = `<p class="error">Execution loop failed: ${err.message}</p>`;
    }
}

window.toggleTraceDetail = function(id) {
    const el = document.getElementById(`detail-${id}`);
    if (el.classList.contains('hide')) {
        el.classList.remove('hide');
    } else {
        el.classList.add('hide');
    }
};

document.getElementById('load-workflows-btn').addEventListener('click', fetchWorkflows);
document.getElementById('workflow-selector').addEventListener('change', handleWorkflowSelection);
document.getElementById('orch-btn').addEventListener('click', executeWorkflow);

// Initial load
fetchWorkflows();