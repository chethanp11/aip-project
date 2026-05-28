/**
 * Stateful KMS Micro-Frontend Controller
 * Coordinates Enterprise-grade Agentic Knowledge Lifecycles & retriever Controls
 */

const API_BASE = window.location.origin + '/api/v1';

// Authed Fetch Interceptor matching standard session storage
const originalFetch = window.fetch;
window.fetch = async function(url, options = {}) {
    const token = localStorage.getItem('AIP_API_KEY') || '';
    if (url.includes('/api/v1')) {
        options.headers = options.headers || {};
        if (token) {
            options.headers['Authorization'] = `Bearer ${token}`;
        }
    }
    return originalFetch(url, options);
};

let currentUserRole = localStorage.getItem('AIP_USER_ROLE') || 'Analyst';
let currentUserClearance = (currentUserRole === 'SME' ? 'Confidential' : 'Internal');
let allCandidates = [];

document.addEventListener('DOMContentLoaded', () => {
    setupTabsNavigation();
    setupRBACProfileSelector();
    setupFoundationalSandbox();
    setupAgenticIntakeDropzone();
    setupContextOptimizer();
    
    // Load scalable UI options from the database
    loadKmsOptions();
    
    // Apply dynamic permissions and initial load
    applyRolePermissions();
});

// ==========================================================
// 🎛️ TAB SWITCHING CONTROLLER
// ==========================================================
function setupTabsNavigation() {
    const tabs = ['sandbox', 'intake', 'optimizer'];
    
    tabs.forEach(tab => {
        const btn = document.getElementById(`tab-${tab}`);
        if (btn) {
            btn.addEventListener('click', () => {
                // Deactivate all tabs
                tabs.forEach(t => {
                    document.getElementById(`tab-${t}`).classList.remove('active');
                    document.getElementById(`panel-${t}`).classList.remove('active');
                });
                
                // Activate clicked
                btn.classList.add('active');
                document.getElementById(`panel-${tab}`).classList.add('active');
                
                // Refresh data if needed
                if (tab === 'intake') {
                    loadConnectorsStatusGrid();
                    loadCandidatesReviewQueue();
                }
            });
        }
    });
}

// ==========================================================
// 🎚️ DYNAMIC KMS OPTION LOADER
// ==========================================================
function optionMarkup(value, label = value, selected = false) {
    return `<option value="${escapeHtml(value)}"${selected ? ' selected' : ''}>${escapeHtml(label)}</option>`;
}

function setSelectOptions(selectId, values, defaultLabel, selectedValue = '') {
    const select = document.getElementById(selectId);
    if (!select) return;
    const rows = [];
    if (defaultLabel !== null) rows.push(optionMarkup('', defaultLabel));
    (values || []).forEach(v => rows.push(optionMarkup(v, v, v === selectedValue)));
    select.innerHTML = rows.join('');
}

async function loadKmsOptions() {
    try {
        const response = await fetch(`${API_BASE}/kms/options`);
        const options = await parseJsonResponse(response);
        if (!response.ok) throw new Error(options.detail || 'Failed to fetch KMS options');

        setSelectOptions('filter-domain', options.domains, 'All Domains');
        setSelectOptions('filter-source', options.sources, 'All Sources');
        setSelectOptions('filter-type', options.knowledgeTypes, 'All Types');
        setSelectOptions('filter-sme', options.smes, 'All SMEs');
        setSelectOptions('filter-search-mode', options.searchModes, null, 'Hybrid');
        setSelectOptions('filter-freshness', options.freshness, 'All Dates');
        setSelectOptions('ingest-domain', options.domains, null);
        setSelectOptions('edit-cand-domain', options.domains, null);
        setSelectOptions('new-conn-domain', options.domains, null);
        setSelectOptions('new-conn-type', options.connectorTypes, null);
        setSelectOptions('ingest-classification', options.securityClassifications, null, 'Internal');
    } catch (e) {
        console.error('Error loading KMS options:', e);
    }
}

async function parseJsonResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    const text = await response.text();
    if (!contentType.includes('application/json')) {
        const preview = text.trim().slice(0, 120);
        throw new Error(`Expected JSON but received ${response.status} ${response.statusText}: ${preview}`);
    }
    return text ? JSON.parse(text) : {};
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, ch => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
    }[ch]));
}

// ==========================================================
// 👤 SECURITY / RBAC CONSOLE & PERMISSIONS ENFORCEMENT
// ==========================================================
function setupRBACProfileSelector() {
    const select = document.getElementById('user-role-select');
    if (select) {
        select.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val === 'SME') {
                // Hold dropdown selector visually at currentUserRole until verification passes
                select.value = currentUserRole;
                showSMELoginModal();
            } else {
                currentUserRole = 'Analyst';
                currentUserClearance = 'Internal';
                applyRolePermissions();
                
                // Auto reload sandbox if query exists
                const q = document.getElementById('sandbox-query').value.trim();
                if (q) executeSandboxSearch(q);
            }
        });
    }
}

window.showSMELoginModal = function() {
    document.getElementById('sme-username').value = '';
    document.getElementById('sme-password').value = '';
    document.getElementById('sme-login-error').style.display = 'none';
    document.getElementById('sme-login-modal').classList.add('active');
};

window.cancelSMELogin = function() {
    document.getElementById('sme-login-modal').classList.remove('active');
    const select = document.getElementById('user-role-select');
    if (select) {
        select.value = currentUserRole;
    }
};

window.submitSMELogin = async function() {
    const u = document.getElementById('sme-username').value.trim();
    const p = document.getElementById('sme-password').value.trim();
    const error = document.getElementById('sme-login-error');
    error.style.display = 'none';
    
    try {
        const res = await originalFetch(`${API_BASE}/auth/sme-login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });
        const data = await parseJsonResponse(res);
        if (!res.ok || !data.success) throw new Error(data.detail || 'Invalid SME credentials.');

        localStorage.setItem('AIP_API_KEY', data.token);
        currentUserRole = 'SME';
        currentUserClearance = data.clearance || 'Confidential';
        document.getElementById('sme-login-modal').classList.remove('active');
        
        const select = document.getElementById('user-role-select');
        if (select) select.value = 'SME';
        
        console.log(`[RBAC Switch] Active Role: ${currentUserRole} | Clearance Level: ${currentUserClearance}`);
        applyRolePermissions();
        
        const q = document.getElementById('sandbox-query').value.trim();
        if (q) executeSandboxSearch(q);
    } catch (err) {
        error.innerText = err.message;
        error.style.display = 'block';
    }
};

function applyRolePermissions() {
    const intakeBtn = document.getElementById('tab-intake');
    const connectorsCard = document.getElementById('sme-connectors-card');
    const candidatesCard = document.getElementById('sme-candidates-card');
    
    if (currentUserRole === 'Analyst') {
        // Hide Ingestion panel tab for Analysts
        if (intakeBtn) intakeBtn.style.display = 'none';
        if (connectorsCard) connectorsCard.style.display = 'none';
        if (candidatesCard) connectorsCard.style.display = 'none';
        
        // If active tab was intake, redirect to sandbox
        const activeBtn = document.querySelector('.tab-btn.active');
        if (activeBtn && activeBtn.id === 'tab-intake') {
            document.getElementById('tab-sandbox').click();
        }
    } else {
        // Show for SME
        if (intakeBtn) intakeBtn.style.display = 'inline-flex';
        if (connectorsCard) connectorsCard.style.display = 'block';
        if (candidatesCard) candidatesCard.style.display = 'block';
    }
    
    // Refresh lists dynamically
    loadConnectorsStatusGrid();
    loadCandidatesReviewQueue();
}

// ==========================================================
// 🔎 TAB 1: ADVANCED SANDBOX SEARCH WITH ANALYST FILTERS
// ==========================================================
function setupFoundationalSandbox() {
    const btn = document.getElementById('sandbox-btn');
    const inp = document.getElementById('sandbox-query');
    
    if (btn && inp) {
        btn.addEventListener('click', () => {
            const q = inp.value.trim();
            if (q) executeSandboxSearch(q);
        });
        
        inp.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const q = inp.value.trim();
                if (q) executeSandboxSearch(q);
            }
        });
    }
}

async function executeSandboxSearch(queryStr) {
    const grid = document.getElementById('sandbox-results-grid');
    const vecPanel = document.getElementById('sandbox-vector-results');
    const graphPanel = document.getElementById('sandbox-graph-results');
    
    vecPanel.innerHTML = '<div style="color:var(--accent-color); font-weight:600;">🔍 Retrieval Planner Agent formulation mapping...</div>';
    graphPanel.innerHTML = '';
    grid.style.display = 'grid';
    
    // Extract filter states
    const filters = {
        domain: document.getElementById('filter-domain').value,
        source: document.getElementById('filter-source').value,
        type: document.getElementById('filter-type').value,
        sme: document.getElementById('filter-sme').value,
        freshness: document.getElementById('filter-freshness').value,
        tag: document.getElementById('filter-tag').value.trim()
    };
    
    const searchMode = document.getElementById('filter-search-mode').value;
    
    try {
        const res = await fetch(`${API_BASE}/kms/query-advanced`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: queryStr,
                userRole: currentUserRole,
                clearance: currentUserClearance,
                searchMode: searchMode,
                filters: filters,
                limit: 6
            })
        });
        const data = await parseJsonResponse(res);
        
        if (!res.ok) {
            vecPanel.innerHTML = `<span style="color:var(--danger-color);">Error: ${data.detail}</span>`;
            return;
        }
        
        // 1. Render matched vector chunks
        if (!data.matchedChunks || data.matchedChunks.length === 0) {
            vecPanel.innerHTML = '<div style="color:var(--text-muted); font-style:italic; padding:12px;">No vector similarity matches cleared for this profile & filters.</div>';
        } else {
            vecPanel.innerHTML = data.matchedChunks.map(c => `
                <div class="chunk-box" style="border-left: 3px solid #cbd5e1; margin-bottom:12px; padding:12px; border-radius:6px; background:#fff;">
                    <div class="chunk-meta" style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:var(--accent-color); margin-bottom:6px;">
                        <span>Similarity Score: ${(c.score * 100).toFixed(0)}%</span>
                        <span>Node Ref: <code>${c.node_id}</code></span>
                    </div>
                    <p style="color:var(--text-main); font-size:12px; line-height:1.5;">"${c.text}"</p>
                    <div style="margin-top:8px; font-size:9px; color:var(--text-muted);">
                        📚 Citation: Grounded standard reference passage
                    </div>
                </div>
            `).join('');
        }
        
        // 2. Render traversed graph nodes
        if (!data.matchedNodes || data.matchedNodes.length === 0) {
            graphPanel.innerHTML = '<div style="color:var(--text-muted); font-style:italic; padding:12px;">No relational graph nodes cleared for this profile & filters.</div>';
        } else {
            graphPanel.innerHTML = data.matchedNodes.map(n => {
                let usedBy = "PRISM, Reporting Suite";
                if (n.title.includes("HQLA") || n.title.includes("Basel")) {
                    usedBy = "PRISM, What-if Simulation, Treasury Dashboards";
                } else if (n.title.includes("Reserve") || n.title.includes("Sweeps")) {
                    usedBy = "Asset Sweep Automation, Corporate Ledgers";
                }
                
                return `
                <div class="node-box" style="border-left: 4px solid var(--accent-color); padding: 14px; background:#fff; border-radius:8px; margin-bottom:12px; border: 1px solid var(--border-color); border-left-width: 4px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h5 style="font-size:13px; font-weight:700; color:var(--text-main);">📌 [${n.type || 'Entity'}] ${n.title}</h5>
                        <span class="status-badge status-Approved" style="font-size:9px; padding:2px 6px;">APPROVED</span>
                    </div>
                    <p style="font-size:12px; color:#334155; margin-top:8px; line-height:1.5;">${n.content}</p>
                    
                    <div class="node-badges" style="display:flex; gap:6px; margin-top:10px; flex-wrap:wrap;">
                        <span class="badge badge-domain" style="font-size:9px; background:#e0e7ff; color:#312e81;">Domain: ${n.business_domain || 'General'}</span>
                        <span class="badge badge-sme" style="font-size:9px; background:#ecfdf5; color:#065f46;">SME: ${n.sme || 'System'}</span>
                        <span class="badge badge-clearance" style="font-size:9px; background:#fef2f2; color:#991b1b;">Clearance: ${n.security_classification || 'Internal'}</span>
                        <span class="badge" style="font-size:9px; background:#f1f5f9; color:#475569;">Freshness: <code>${n.freshness_date || '2026-05-01'}</code></span>
                    </div>
                    
                    <div style="margin-top:10px; border-top:1px dashed #e2e8f0; padding-top:8px; display:flex; justify-content:space-between; align-items:center; font-size:10px; color:var(--text-muted);">
                        <span>🔗 Citation: <code>${n.source_traceability || 'Federal Reserve BCBS Board'}</code></span>
                        <span>🖥️ Used by: <strong style="color:var(--accent-color);">${usedBy}</strong></span>
                    </div>
                </div>
            `;
            }).join('');
        }
    } catch(err) {
        vecPanel.innerHTML = `<span style="color:var(--danger-color);">RAG search exception: ${err.message}</span>`;
    }
}

// ==========================================================
// 📥 TAB 2: SME LIFE-CYCLE INGESTION & CONNECTORS GRID
// ==========================================================
function setupAgenticIntakeDropzone() {
    const dropzone = document.getElementById('ingest-dropzone');
    const fileInput = document.getElementById('ingest-file-input');
    const logsBox = document.getElementById('agent-logs-stream');
    const statusLabel = document.getElementById('agent-status-label');
    
    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => {
            fileInput.click();
        });
        
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = async function(evt) {
                const content = evt.target.result;
                const owner = document.getElementById('ingest-owner').value.trim();
                const sme = document.getElementById('ingest-sme').value.trim();
                const domain = document.getElementById('ingest-domain').value;
                const classification = document.getElementById('ingest-classification').value;
                
                statusLabel.innerText = "COORDINATING";
                statusLabel.style.color = "var(--warning-color)";
                logsBox.innerHTML = `<div style="color:#38bdf8;">⏳ Ingesting '${file.name}' into Multi-Agent coordinator...</div>`;
                
                try {
                    const res = await fetch(`${API_BASE}/kms/upload`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            filename: file.name,
                            content: content,
                            owner: owner,
                            sme: sme,
                            businessDomain: domain,
                            securityClassification: classification
                        })
                    });
                    const data = await parseJsonResponse(res);
                    
                    if (res.ok) {
                        statusLabel.innerText = "INGESTED";
                        statusLabel.style.color = "var(--success-color)";
                        
                        logsBox.innerHTML = '';
                        (data.agentTraces || []).forEach(t => {
                            const line = document.createElement('div');
                            line.className = 'agent-log-line';
                            line.innerHTML = `
                                <span style="color:#64748b;">[${t.timestamp}]</span>
                                <span class="agent-tag">[${t.agent}]</span>
                                <span style="color:#94a3b8;">${t.action}:</span>
                                <span style="color:#f8fafc;">${t.details}</span>
                            `;
                            logsBox.appendChild(line);
                        });
                        logsBox.scrollTop = logsBox.scrollHeight;
                        
                        // Reload candidates review queue
                        loadCandidatesReviewQueue();
                    } else {
                        statusLabel.innerText = "FAILED";
                        statusLabel.style.color = "var(--danger-color)";
                        logsBox.innerHTML = `<div style="color:var(--danger-color);">❌ Ingestion coordinator failure: ${data.detail}</div>`;
                    }
                } catch(err) {
                    statusLabel.innerText = "ERROR";
                    statusLabel.style.color = "var(--danger-color)";
                    logsBox.innerHTML = `<div style="color:var(--danger-color);">❌ Server Ingestion exception: ${err.message}</div>`;
                }
            };
            reader.readAsText(file);
        });
    }
}

// 🔌 Load Connected source connectors status grid
async function loadConnectorsStatusGrid() {
    const grid = document.getElementById('connectors-status-grid');
    if (!grid) return;
    
    const isSme = (currentUserRole === 'SME');
    if (!isSme) {
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); font-size: 12px; padding: 20px; font-style: italic;">Access Restricted: Switch to Subject Matter Expert (SME) profile to view connectors.</div>';
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/kms/connectors`);
        const data = await parseJsonResponse(res);
        
        if (data.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); font-size: 12px; padding: 20px; font-style: italic;">No active corporate connectors established.</div>';
            return;
        }
        
        grid.innerHTML = data.map(c => `
            <div class="connector-card">
                <div class="connector-header">
                    <span class="connector-title">${c.name}</span>
                    <span class="connector-status-pill status-${c.status}">${c.status}</span>
                </div>
                <div class="connector-details">
                    Type: <strong>${c.type}</strong><br/>
                    Domain: <strong>${c.domain || 'Regulatory Compliance'}</strong><br/>
                    Owner Unit: <strong>${c.owner || 'Corporate Operations'}</strong><br/>
                    Sync Mode: <code>${c.sync_method}</code><br/>
                    Last Synced: <code>${c.last_sync_timestamp || 'Never'}</code>
                </div>
                <div style="border-top:1px solid #f1f5f9; padding-top:10px; margin-top:10px; display:flex; justify-content:space-between; align-items:center;">
                    <button class="action-btn" onclick="triggerConnectorSync('${c.connector_id}')" style="color:var(--accent-color); font-weight:700;">🔄 Sync Now</button>
                    ${c.error_logs ? `<span style="color:var(--danger-color); font-size:10px; font-weight:700; cursor:pointer;" onclick="alert('Error details: ${c.error_logs}')">⚠️ View Error</span>` : `<span style="color:var(--success-color); font-size:10px;">✔ Healthy</span>`}
                </div>
            </div>
        `).join('');
    } catch(err) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--danger-color); padding: 20px;">Failed to load connectors: ${err.message}</div>`;
    }
}

async function triggerConnectorSync(connectorId) {
    const logsBox = document.getElementById('agent-logs-stream');
    const statusLabel = document.getElementById('agent-status-label');
    
    statusLabel.innerText = "COORDINATING";
    statusLabel.style.color = "var(--warning-color)";
    logsBox.innerHTML = `<div style="color:#38bdf8;">⏳ Polling connector '${connectorId}' API stream... Triggering 12-Agent sequential extraction...</div>`;
    
    try {
        const res = await fetch(`${API_BASE}/kms/connectors/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ connectorId: connectorId })
        });
        const data = await parseJsonResponse(res);
        
        if (res.ok) {
            statusLabel.innerText = "INGESTED";
            statusLabel.style.color = "var(--success-color)";
            
            logsBox.innerHTML = '';
            (data.agentTraces || []).forEach(t => {
                const line = document.createElement('div');
                line.className = 'agent-log-line';
                line.innerHTML = `
                    <span style="color:#64748b;">[${t.timestamp}]</span>
                    <span class="agent-tag">[${t.agent}]</span>
                    <span style="color:#94a3b8;">${t.action}:</span>
                    <span style="color:#f8fafc;">${t.details}</span>
                `;
                logsBox.appendChild(line);
            });
            logsBox.scrollTop = logsBox.scrollHeight;
            
            // Reload the grids
            loadConnectorsStatusGrid();
            loadCandidatesReviewQueue();
        } else {
            statusLabel.innerText = "FAILED";
            statusLabel.style.color = "var(--danger-color)";
            logsBox.innerHTML = `<div style="color:var(--danger-color);">❌ Connector Sync failed: ${data.detail}</div>`;
        }
    } catch(err) {
        statusLabel.innerText = "ERROR";
        statusLabel.style.color = "var(--danger-color)";
        logsBox.innerHTML = `<div style="color:var(--danger-color);">❌ Server sync exception: ${err.message}</div>`;
    }
}

// 🔌 Established Connection Modal triggers
function showAddConnectorModal() {
    document.getElementById('add-connector-modal').classList.add('active');
}
function closeConnectorModal() {
    document.getElementById('add-connector-modal').classList.remove('active');
}
async function submitNewConnector() {
    const name = document.getElementById('new-conn-name').value.trim();
    const type = document.getElementById('new-conn-type').value;
    const domain = document.getElementById('new-conn-domain').value;
    const owner = document.getElementById('new-conn-owner').value.trim();
    const authPlaceholder = document.getElementById('new-conn-auth').value;
    
    if (!name) {
        alert("Please specify a connector name!");
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/kms/connectors`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name, type, domain, owner, authPlaceholder, syncMethod: 'Manual'
            })
        });
        if (res.ok) {
            alert("New connector Established successfully!");
            closeConnectorModal();
            loadConnectorsStatusGrid();
        } else {
            const data = await parseJsonResponse(res);
            alert(`Failed to add connector: ${data.detail}`);
        }
    } catch(err) {
        alert(`Establish connection exception: ${err.message}`);
    }
}

// ==========================================================
// 🗳️ SME CANDIDATE KNOWLEDGE LIFECYCLE QUEUE
// ==========================================================
async function loadCandidatesReviewQueue() {
    const listDiv = document.getElementById('candidates-review-list');
    if (!listDiv) return;
    
    const isSme = (currentUserRole === 'SME');
    if (!isSme) {
        listDiv.innerHTML = '<div style="text-align: center; color: var(--text-muted); font-size: 12px; padding: 20px; font-style: italic;">Access Restricted: Switch to Subject Matter Expert (SME) profile to view candidate queue.</div>';
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/kms/candidates`);
        const data = await parseJsonResponse(res);
        allCandidates = data;
        
        // Filter active pending review candidates
        const pending = data.filter(c => c.review_status === 'Pending Review' || c.review_status === 'Draft' || c.review_status === 'Needs Clarification');
        
        if (pending.length === 0) {
            listDiv.innerHTML = '<div style="text-align: center; color: var(--text-muted); font-size: 12px; padding: 20px; font-style: italic;">No candidate knowledge cards in review queue. Sync a connector or upload a file.</div>';
            return;
        }
        
        listDiv.innerHTML = pending.map(c => `
            <div class="candidate-row-card" style="border-left-color: ${c.review_status === 'Needs Clarification' ? 'var(--warning-color)' : 'var(--accent-color)'}">
                <div class="candidate-main">
                    <div class="candidate-header-row">
                        <span class="candidate-title">${c.title}</span>
                        <span class="status-badge" style="background:#e0e7ff; color:#312e81; font-size:9px;">${c.review_status}</span>
                        <span class="status-badge" style="background:#f1f5f9; color:#475569; font-size:9px;">${c.knowledge_type}</span>
                    </div>
                    <div class="candidate-meta-line">
                        Domain: <strong>${c.domain}</strong> | Source: <strong>${c.source_application} (${c.source_document})</strong>
                    </div>
                    <p class="candidate-summary">${c.summary || 'No summary generated yet.'}</p>
                    <div class="candidate-indicators">
                        <span class="indicator-item" style="color:var(--success-color);">🎯 Confidence: <strong>${(c.confidence_score * 100).toFixed(0)}%</strong></span>
                        <span class="indicator-item">📂 Dup Score: <strong>${(c.duplicate_score * 100).toFixed(0)}%</strong></span>
                        ${c.duplicate_score > 0.3 ? `<span class="indicator-item indicator-warn">⚠️ Duplicate Warning!</span>` : ''}
                        ${c.conflict_warning && c.conflict_warning !== 'None' ? `<span class="indicator-item indicator-warn">⚠️ Conflict: ${c.conflict_warning}</span>` : ''}
                    </div>
                </div>
                <div class="candidate-actions-col">
                    <button class="btn-prime" onclick="openCandidateReviewModal('${c.candidate_id}')" style="padding: 6px 12px; font-size: 11px;">Inspect & Action</button>
                    <span style="font-size:10px; color:var(--text-muted);">Suggested SME: ${c.suggested_sme || 'None'}</span>
                </div>
            </div>
        `).join('');
    } catch(err) {
        listDiv.innerHTML = `<div style="text-align: center; color: var(--danger-color); padding: 20px;">Failed to load candidate queue: ${err.message}</div>`;
    }
}

// Modal inspection controls
window.openCandidateReviewModal = function(candidateId) {
    const cand = allCandidates.find(c => c.candidate_id === candidateId);
    if (!cand) return;
    
    document.getElementById('edit-cand-id').value = cand.candidate_id;
    document.getElementById('edit-cand-title').value = cand.title;
    document.getElementById('edit-cand-summary').value = cand.summary || '';
    document.getElementById('edit-cand-domain').value = cand.domain;
    document.getElementById('edit-cand-tags').value = cand.tags || '';
    document.getElementById('edit-cand-relationships').value = cand.relationships || '';
    document.getElementById('edit-cand-comments').value = cand.reviewer_comments || '';
    
    document.getElementById('edit-cand-extracted').innerText = cand.extracted_text;
    
    document.getElementById('candidate-review-modal').classList.add('active');
};

window.closeCandidateModal = function() {
    document.getElementById('candidate-review-modal').classList.remove('active');
};

window.saveCandidateEdits = async function() {
    const candidateId = document.getElementById('edit-cand-id').value;
    const title = document.getElementById('edit-cand-title').value.trim();
    const summary = document.getElementById('edit-cand-summary').value.trim();
    const domain = document.getElementById('edit-cand-domain').value;
    const tags = document.getElementById('edit-cand-tags').value.trim();
    const relationships = document.getElementById('edit-cand-relationships').value.trim();
    
    try {
        const res = await fetch(`${API_BASE}/kms/candidates/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidateId, title, summary, domain, tags, relationships
            })
        });
        if (res.ok) {
            alert("Candidate edits saved in draft queue successfully!");
            closeCandidateModal();
            loadCandidatesReviewQueue();
        } else {
            const data = await parseJsonResponse(res);
            alert(`Save failed: ${data.detail}`);
        }
    } catch(err) {
        alert(`Save exception: ${err.message}`);
    }
};

window.actOnCandidate = async function(status) {
    const candidateId = document.getElementById('edit-cand-id').value;
    const comments = document.getElementById('edit-cand-comments').value.trim();
    
    try {
        const res = await fetch(`${API_BASE}/kms/candidates/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidateId, status, comments
            })
        });
        if (res.ok) {
            closeCandidateModal();
            loadCandidatesReviewQueue();
        } else {
            const data = await parseJsonResponse(res);
            alert(`Action failed: ${data.detail}`);
        }
    } catch(err) {
        alert(`Action exception: ${err.message}`);
    }
};

// ==========================================================
// 📦 TAB 4: retriever WORKSPACE CONTROLLER
// ==========================================================
function setupContextOptimizer() {
    const btn = document.getElementById('optimizer-btn');
    const inp = document.getElementById('optimizer-query');
    const meta = document.getElementById('opt-meta-box');
    const output = document.getElementById('optimizer-output');
    const contrBox = document.getElementById('opt-contradictions-box');
    const gapsBox = document.getElementById('opt-gaps-box');
    const dlBtn = document.getElementById('retriever-download-btn');
    
    if (btn && inp) {
        btn.addEventListener('click', async () => {
            const q = inp.value.trim();
            if (!q) {
                alert("Please enter the grounding query prompt first!");
                return;
            }
            
            output.innerHTML = '<span style="color:var(--accent-color);">⏳ Compiling optimized evidence context package and compressing token buffers...</span>';
            meta.style.display = 'none';
            contrBox.style.display = 'none';
            gapsBox.style.display = 'none';
            if (dlBtn) dlBtn.style.display = 'none';
            
            try {
                const res = await fetch(`${API_BASE}/kms/context-package`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: q,
                        userRole: currentUserRole,
                        clearance: currentUserClearance
                    })
                });
                const data = await parseJsonResponse(res);
                
                if (res.ok) {
                    meta.style.display = 'block';
                    meta.innerHTML = `
                        <strong>Optimized Context Package:</strong> Deduplicated & Compressed<br/>
                        <span>Original words size: <strong>${data.originalTokensCount}</strong> | Optimized words size: <strong>${data.compressedTokensCount}</strong></span><br/>
                        <span>Retrieval Quality Confidence Score: <strong style="color:var(--success-color);">${data.contextQualityScore * 100}%</strong></span>
                    `;
                    
                    // Contradictions
                    if (data.contradictionsDetected && data.contradictionsDetected.length > 0) {
                        contrBox.style.display = 'block';
                        contrBox.innerHTML = `⚠️ <strong>Contradiction warning:</strong> ${data.contradictionsDetected.join(', ')}`;
                    }
                    
                    // Gaps
                    if (data.missingContextGaps && data.missingContextGaps.length > 0) {
                        gapsBox.style.display = 'block';
                        gapsBox.innerHTML = `📌 <strong>Missing Gaps Warning:</strong> ${data.missingContextGaps.join(', ')}`;
                    }
                    
                    output.innerText = data.optimizedContext;
                    
                    // Display Retriever Download button
                    if (dlBtn) dlBtn.style.display = 'inline-block';
                } else {
                    output.innerText = `Optimization error: ${data.detail}`;
                }
            } catch(err) {
                output.innerText = `Context compression failed: ${err.message}`;
            }
        });
        
        if (dlBtn) {
            dlBtn.addEventListener('click', downloadContextPackZip);
        }
    }
}

// 📦 Objective B: Download Context Packs (.zip)
async function downloadContextPackZip() {
    const q = document.getElementById('optimizer-query').value.trim();
    if (!q) {
        alert("Please enter the query first!");
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/kms/retriever/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: q,
                userRole: currentUserRole,
                clearance: currentUserClearance
            })
        });
        
        if (!response.ok) {
            const data = await response.json();
            alert(`Download failed: ${data.detail}`);
            return;
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `context_pack_${q.substring(0, 15).replace(/\s+/g, '_')}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (err) {
        alert(`Failed to download context pack: ${err.message}`);
    }
}

// Export custom modal triggers globals for HTML binds
window.showAddConnectorModal = showAddConnectorModal;
window.closeConnectorModal = closeConnectorModal;
window.submitNewConnector = submitNewConnector;
window.triggerConnectorSync = triggerConnectorSync;