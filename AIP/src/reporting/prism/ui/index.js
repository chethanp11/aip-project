/**
 * PRISM Micro-Frontend Shell Controller
 */

let selectedFiles = [];
let sandboxLoaded = false;
let seedReports = [];

document.addEventListener('DOMContentLoaded', () => {
    setupDragAndDrop();
    setupActions();
});

// ==========================================
// 📁 DRAG & DROP FILE SELECTION BINDINGS
// ==========================================
function setupDragAndDrop() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-uploader');
    
    if (!dropzone || !fileInput) return;
    
    dropzone.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', (e) => {
        handleFileSelection(e.target.files);
    });
    
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });
    
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });
    
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        handleFileSelection(e.dataTransfer.files);
    });
}

function handleFileSelection(files) {
    for (let file of files) {
        // Prevent duplicate file selections
        if (selectedFiles.some(f => f.name === file.name && f.size === file.size)) continue;
        selectedFiles.push(file);
    }
    sandboxLoaded = false;
    renderSelectedFiles();
}

function renderSelectedFiles() {
    const list = document.getElementById('selected-files-list');
    list.innerHTML = '';
    
    selectedFiles.forEach((file, idx) => {
        const badge = document.createElement('div');
        badge.className = 'file-badge';
        badge.innerHTML = `
            <span>📄 ${file.name}</span>
            <span class="file-remove" onclick="removeSelectedFile(${idx})">&times;</span>
        `;
        list.appendChild(badge);
    });
}

window.removeSelectedFile = function(idx) {
    selectedFiles.splice(idx, 1);
    renderSelectedFiles();
};

// ==========================================
// 🚀 ACTIONS AND API ORCHESTRATION
// ==========================================
function setupActions() {
    const btnSandbox = document.getElementById('btn-load-sandbox');
    const btnAudit = document.getElementById('prism-audit-btn');
    
    // Load Sandbox
    btnSandbox.addEventListener('click', () => {
        seedReports = [
            { 
                name: 'NIM Breakdown Q1', 
                query: 'SELECT interest_income, interest_expense, earning_assets, net_profit FROM branch_ledger', 
                columns: ['interest_income', 'interest_expense', 'earning_assets', 'net_profit'], 
                usage: 120, 
                owner: 'Finance Dept',
                type: 'Excel'
            },
            { 
                name: 'Interest Spread Review', 
                query: 'SELECT interest_income, interest_expense, earning_assets, net_interest_margin FROM branch_ledger', 
                columns: ['interest_income', 'interest_expense', 'earning_assets', 'net_interest_margin'], 
                usage: 8, 
                owner: 'ALCO Committee',
                type: 'Excel'
            },
            { 
                name: 'Regional LDR Ledger', 
                query: 'SELECT total_loans, total_deposits, branch_name FROM customer_deposits', 
                columns: ['total_loans', 'total_deposits', 'branch_name'], 
                usage: 84, 
                owner: 'Treasury Dept',
                type: 'HTML'
            }
        ];
        selectedFiles = [];
        sandboxLoaded = true;
        renderSelectedFiles();
        
        // Show sandbox alert
        const list = document.getElementById('selected-files-list');
        list.innerHTML = `<div style="font-size: 11px; color: var(--primary); font-weight: 600;">📦 Sandbox Seeds Active (${seedReports.length} reports pre-loaded)</div>`;
    });
    
    // Core Screening Auditer
    btnAudit.addEventListener('click', async () => {
        if (!sandboxLoaded && selectedFiles.length === 0) {
            alert("Please choose/drag files or load Sandbox seed reports first!");
            return;
        }
        
        btnAudit.disabled = true;
        btnAudit.innerText = "Analyzing Report Structures...";
        
        const directive = document.getElementById('prism-directive').value.trim();
        
        try {
            let data = null;
            
            if (sandboxLoaded) {
                // Call standard JSON route
                const res = await fetch(`${API_BASE}/workflows/reporting/prism-lite`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reports: seedReports, prompt: directive })
                });
                data = await res.json();
            } else {
                // Call multipart file upload route
                const formData = new FormData();
                selectedFiles.forEach(file => {
                    formData.append('files', file);
                });
                formData.append('prompt', directive);
                
                const res = await fetch(`${API_BASE}/workflows/reporting/prism/upload`, {
                    method: 'POST',
                    body: formData
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "File parse error");
                }
                data = await res.json();
            }
            
            renderAuditOutcomes(data);
            
        } catch(err) {
            alert("Rationalization failed: " + err.message);
        } finally {
            btnAudit.disabled = false;
            btnAudit.innerText = "Screen & Rationalize Inventory";
        }
    });
}

// ==========================================
// 📊 RENDER COMPREHENSIVE OUTCOMES & PLANS
// ==========================================
function renderAuditOutcomes(data) {
    // Show active canvas panels
    document.getElementById('canvas-empty-state').classList.add('hide');
    document.getElementById('canvas-active-state').classList.remove('hide');
    
    // Update overview stats
    const totalReportsCount = sandboxLoaded ? seedReports.length : (data.duplicates.length + data.overlaps.length + data.usageInsights.length || 3);
    document.getElementById('stat-total-reports').innerText = totalReportsCount;
    document.getElementById('stat-duplicates').innerText = data.duplicates.length;
    document.getElementById('stat-overlaps').innerText = data.overlaps.length;
    
    // Sum estimated savings
    let totalSavingsPct = 0;
    if (data.consolidationPlans && data.consolidationPlans.length > 0) {
        data.consolidationPlans.forEach(p => {
            const num = parseInt(p.savings.replace(/\D/g, '')) || 0;
            totalSavingsPct += num;
        });
    }
    document.getElementById('stat-savings').innerText = `${totalSavingsPct || 25}%`;
    
    // AI Lead recommendation
    document.getElementById('ai-banner-summary').innerText = data.summary;
    
    // Duplicates list
    const dupBox = document.getElementById('duplicates-accordion');
    dupBox.innerHTML = '';
    
    if (data.duplicates.length === 0 && data.overlaps.length === 0) {
        dupBox.innerHTML = '<div style="color: #64748b; font-style: italic; padding: 20px; font-size:12px;">No structural conflicts or overlaps detected.</div>';
    } else {
        data.duplicates.forEach(d => {
            const item = document.createElement('div');
            item.className = 'accordion-item';
            item.innerHTML = `
                <div class="accordion-item-header">
                    <span class="name">⚠️ Redundant: ${d.reportA} & ${d.reportB}</span>
                    <span class="badge">DUPLICATE</span>
                </div>
                <div class="accordion-item-body">
                    <strong>Match Type:</strong> ${d.matchType}<br/>
                    <strong>Calculations:</strong> <code>${d.querySnippet}</code>
                </div>
            `;
            dupBox.appendChild(item);
        });
        
        data.overlaps.forEach(o => {
            const item = document.createElement('div');
            item.className = 'accordion-item';
            item.innerHTML = `
                <div class="accordion-item-header">
                    <span class="name">📐 Overlap: ${o.reportA} & ${o.reportB}</span>
                    <span class="badge overlap">${o.coefficient}% similarity</span>
                </div>
                <div class="accordion-item-body">
                    <strong>Identified Conflict:</strong> Shared dimension fields mapping detected.<br/>
                    <strong>Recommendation:</strong> Merge metrics calculations to optimize ledger lookups.
                </div>
            `;
            dupBox.appendChild(item);
        });
    }
    
    // Consolidation plans
    const planBox = document.getElementById('plans-container');
    planBox.innerHTML = '';
    
    if (!data.consolidationPlans || data.consolidationPlans.length === 0) {
        planBox.innerHTML = '<div style="color: #64748b; font-style: italic; padding: 20px; font-size:12px;">No active consolidation builds proposed. Try increasing file similarities.</div>';
    } else {
        data.consolidationPlans.forEach((plan, idx) => {
            const pCard = document.createElement('div');
            pCard.className = 'plan-card';
            pCard.innerHTML = `
                <div class="plan-card-header">
                    <div class="plan-title-wrapper">
                        <h4>💎 Merge Candidate (${plan.similarity}% Overlap)</h4>
                        <p>${plan.proposedName}</p>
                    </div>
                    <span class="plan-badge">${plan.savings}</span>
                </div>
                <div class="plan-card-body">
                    <div class="plan-detail-row">
                        <label>Reports Targeted</label>
                        <p>${plan.reports.join('  &  ')}</p>
                    </div>
                    <div class="plan-detail-row">
                        <label>Rationalization Narrative</label>
                        <p>${plan.explanation}</p>
                    </div>
                    <div class="plan-detail-row">
                        <label>Consolidation Strategy</label>
                        <p style="font-size:11px; background:#f8fafc; border:1px solid #f1f5f9; padding:8px; border-radius:6px; font-family:monospace; color:#475569;">
                            ${plan.proposedRequirements}
                        </p>
                    </div>
                </div>
                <div class="plan-card-footer">
                    <button class="btn-action-builder" onclick="initializeConsolidationBuild(${idx})">
                        ➔ Initialize Consolidation Build
                    </button>
                </div>
            `;
            
            // Store plan object inside element dataset to retrieve on click
            pCard.dataset.planObj = JSON.stringify(plan);
            planBox.appendChild(pCard);
        });
    }
}

// ==========================================
// ➔ SEAMLESS TRANSITION TO REPORT BUILDER
// ==========================================
window.initializeConsolidationBuild = function(idx) {
    const cards = document.querySelectorAll('.plan-card');
    if (!cards[idx]) return;
    
    const plan = JSON.parse(cards[idx].dataset.planObj);
    
    // Store consolidation payload in localStorage shared with report builder iframe
    localStorage.setItem('prism_consolidation_plan', JSON.stringify({
        requirements: plan.proposedRequirements,
        context: plan.proposedContext,
        reportName: plan.proposedName
    }));
    
    // Dynamically trigger parent page navigation tab switch
    if (window.parent && typeof window.parent.switchSubProduct === 'function') {
        window.parent.switchSubProduct('reporting', 'builder');
    } else {
        alert("Consolidation Plan cached! Switch to the 'Reporting' tab to compile.");
    }
};