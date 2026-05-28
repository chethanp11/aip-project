/**
 * Stateful Controller for the 6-step Sequential HITL Report Builder Workspace
 */

let currentStep = 1;
let workflowSessionId = null;
let currentMode = 'create'; // 'create' or 'update'
let selectedReportIdToUpdate = null;
let publishedReports = [];
let latestStepData = {};

document.addEventListener('DOMContentLoaded', () => {
    setupModeToggle();
    setupNavigationButtons();
    loadPublishedReportsList();
    setupFileIngestion();
    setupFeedbackButtons();
    checkForPrismPlan();
});

// ==========================================================
// 🔄 MODE TOGGLING: CREATE VS UPDATE
// ==========================================================
function setupModeToggle() {
    const btnCreate = document.getElementById('mode-create');
    const btnUpdate = document.getElementById('mode-update');
    const updateSelectRow = document.getElementById('update-select-row');
    
    btnCreate.addEventListener('click', () => {
        currentMode = 'create';
        btnCreate.classList.add('active');
        btnUpdate.classList.remove('active');
        updateSelectRow.style.display = 'none';
        resetWorkflow();
    });
    
    btnUpdate.addEventListener('click', () => {
        currentMode = 'update';
        btnUpdate.classList.add('active');
        btnCreate.classList.remove('active');
        updateSelectRow.style.display = 'block';
        populateUpdateDropdown();
        resetWorkflow();
    });
}

function resetWorkflow() {
    currentStep = 1;
    workflowSessionId = null;
    latestStepData = {};
    updateStepUI();
}

async function populateUpdateDropdown() {
    const dropdown = document.getElementById('update-report-dropdown');
    dropdown.innerHTML = '<option value="">-- Choose Report to Update --</option>';
    
    await loadPublishedReportsList();
    
    publishedReports.forEach(rep => {
        const opt = document.createElement('option');
        opt.value = rep.id;
        opt.innerText = `${rep.name} (${rep.id})`;
        dropdown.appendChild(opt);
    });
}

// ==========================================================
// 📁 FILE INGESTION BINDING
// ==========================================================
function setupFileIngestion() {
    const browseBtn = document.getElementById('browse-btn');
    const fileInput = document.getElementById('step1-file-input');
    const ctxInput = document.getElementById('step1-ctx');
    
    if (browseBtn && fileInput && ctxInput) {
        browseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            fileInput.click();
        });
        
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(evt) {
                    ctxInput.value = evt.target.result;
                };
                reader.readAsText(file);
            }
        });
    }
}

// ==========================================================
// 🚀 PIPELINE NAVIGATION & SEQUENTIAL STEPS (HITL)
// ==========================================================
function setupNavigationButtons() {
    const btnNext = document.getElementById('next-btn');
    const btnPrev = document.getElementById('prev-btn');
    
    btnNext.addEventListener('click', async () => {
        if (currentStep === 1) {
            await handleStep1();
        } else if (currentStep === 2) {
            await handleCheckpoint(2);
        } else if (currentStep === 3) {
            await handleCheckpoint(3);
        } else if (currentStep === 4) {
            await handleCheckpoint(4);
        } else if (currentStep === 5) {
            await handleCheckpoint(5);
        } else if (currentStep === 6) {
            // Already published and completed
            resetWorkflow();
        }
    });
    
    btnPrev.addEventListener('click', () => {
        if (currentStep > 1 && currentStep < 6) {
            currentStep--;
            updateStepUI();
        }
    });
}

function updateStepUI() {
    // Hide all step panels
    document.querySelectorAll('.step-panel').forEach(panel => panel.classList.remove('active'));
    
    // Show active step panel
    const activePanel = document.getElementById(`panel-${currentStep}`);
    if (activePanel) activePanel.classList.add('active');
    
    // Update Indicators
    for (let i = 1; i <= 6; i++) {
        const ind = document.getElementById(`indicator-${i}`);
        if (i < currentStep) {
            ind.className = 'step-indicator completed';
        } else if (i === currentStep) {
            ind.className = 'step-indicator active';
        } else {
            ind.className = 'step-indicator';
        }
    }
    
    // Buttons state
    const btnNext = document.getElementById('next-btn');
    const btnPrev = document.getElementById('prev-btn');
    
    btnPrev.disabled = currentStep === 1 || currentStep === 6;
    
    if (currentStep === 6) {
        btnNext.innerText = "Start New Workflow ➔";
    } else {
        btnNext.innerText = "Approve & Progress Step ➔";
    }
}

// ==========================================================
// ⚙️ BACKEND WORKFLOW ROUTING HANDLERS
// ==========================================================
async function handleStep1() {
    const reqText = document.getElementById('step1-req').value.trim();
    const ctxText = document.getElementById('step1-ctx').value.trim();
    
    if (!reqText) {
        alert("Please enter report creation requirements!");
        return;
    }
    
    let targetReportId = null;
    if (currentMode === 'update') {
        targetReportId = document.getElementById('update-report-dropdown').value;
        if (!targetReportId) {
            alert("Please select a published report to update!");
            return;
        }
    }
    
    const btnNext = document.getElementById('next-btn');
    btnNext.disabled = true;
    btnNext.innerText = "Agent parsing requirements...";
    
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/build/initiate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mode: currentMode,
                reportId: targetReportId,
                requirements: reqText,
                context: ctxText
            })
        });
        const data = await res.json();
        
        if (res.ok) {
            workflowSessionId = data.sessionId;
            latestStepData = data.stepOutput;
            
            // Render the complex KPI, ER and schemas in step 2 for Human Audit
            renderStep2Data(latestStepData);
            renderAgentDecisions(2, latestStepData.agentDecisions);
            
            currentStep = 2;
            updateStepUI();
        } else {
            alert(`Initiation error: ${data.detail}`);
        }
    } catch(err) {
        alert(`Failed to communicate with Agentic server: ${err.message}`);
    } finally {
        btnNext.disabled = false;
        btnNext.innerText = "Approve & Progress Step ➔";
    }
}

async function handleCheckpoint(stepApproved) {
    const btnNext = document.getElementById('next-btn');
    btnNext.disabled = true;
    btnNext.innerText = `Submitting HITL Checkpoint approval for Step ${stepApproved}...`;
    
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/build/step`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sessionId: workflowSessionId,
                step: stepApproved,
                approved: true
            })
        });
        const data = await res.json();
        
        if (res.ok) {
            latestStepData = data.stepOutput;
            
            if (stepApproved === 2) {
                // Step 2 Approved, Render Step 3 (Transformed SQL summaries)
                const pre = document.getElementById('step3-sql-data');
                pre.innerText = JSON.stringify(latestStepData.transformedData, null, 2);
                renderAgentDecisions(3, latestStepData.agentDecisions);
                currentStep = 3;
            } else if (stepApproved === 3) {
                // Step 3 Approved, Render Step 4 (Data schema JSON)
                const pre = document.getElementById('step4-schema-json');
                pre.innerText = JSON.stringify(latestStepData.schema, null, 2);
                renderAgentDecisions(4, latestStepData.agentDecisions);
                currentStep = 4;
            } else if (stepApproved === 4) {
                // Step 4 Approved, Render Step 5 (Visual CSS/HTML scaffolding)
                const pre = document.getElementById('step5-skeleton-html');
                pre.innerText = latestStepData.skeletonHtml;
                renderAgentDecisions(5, latestStepData.agentDecisions);
                currentStep = 5;
            } else if (stepApproved === 5) {
                // Step 5 Approved, Report Published, Render Step 6 compliance panel
                const metaBox = document.getElementById('published-report-meta');
                metaBox.innerHTML = `
                    <p style="font-size:12px;"><strong>Report Name:</strong> ${latestStepData.name}</p>
                    <p style="font-size:12px;"><strong>Report ID:</strong> <code>${latestStepData.id}</code></p>
                    <p style="font-size:12px; margin-top:4px;"><strong>Static URL Mount:</strong> <a href="${latestStepData.path}" target="_blank" style="color:var(--accent-color); font-weight:600; text-decoration:underline;">${latestStepData.path}</a></p>
                `;
                
                // Bind open button
                document.getElementById('open-published-btn').onclick = () => {
                    window.open(latestStepData.path, '_blank');
                };
                
                currentStep = 6;
                loadPublishedReportsList(); // Refresh sidebar published grid
            }
            updateStepUI();
        } else {
            alert(`Checkpoint execution blocked: ${data.detail}`);
        }
    } catch(err) {
        alert(`Failed to confirm Step ${stepApproved} checkpoint: ${err.message}`);
    } finally {
        btnNext.disabled = false;
    }
}

// ==========================================================
// 📋 RENDERING GROUNDED DATA MODELS & COMPREHENSIVE KPIs
// ==========================================================
function renderStep2Data(stepData) {
    // 1. Matched KPIs
    const kpisBox = document.getElementById('step2-kpis-list');
    if (stepData.kpis && stepData.kpis.length > 0) {
        kpisBox.innerHTML = stepData.kpis.map(k => `
            <span class="badge-kpi">📌 KPI: ${k}</span>
        `).join('');
    } else {
        kpisBox.innerHTML = '<span style="color:#64748b; font-style:italic;">No KPIs matched.</span>';
    }

    // 2. ER Diagram
    const erDiagramBox = document.getElementById('step2-er-diagram');
    erDiagramBox.innerText = stepData.erDiagram || '';

    // 3. Fact & Dimension Tables
    const tablesBox = document.getElementById('step2-tables-structure');
    tablesBox.innerHTML = '';

    if (stepData.factTables) {
        const factTitle = document.createElement('h5');
        factTitle.style.margin = '8px 0 4px 0';
        factTitle.style.color = '#0f172a';
        factTitle.style.fontSize = '12px';
        factTitle.innerText = '📊 Fact Tables:';
        tablesBox.appendChild(factTitle);
        
        for (const [tableName, columns] of Object.entries(stepData.factTables)) {
            const tableDiv = document.createElement('div');
            tableDiv.style.marginBottom = '6px';
            tableDiv.innerHTML = `<strong>${tableName}</strong>: <code style="background:#e2e8f0; padding:2px 6px; border-radius:4px; font-size:10px;">${columns.join(', ')}</code>`;
            tablesBox.appendChild(tableDiv);
        }
    }

    if (stepData.dimensionTables) {
        const dimTitle = document.createElement('h5');
        dimTitle.style.margin = '12px 0 4px 0';
        dimTitle.style.color = '#0f172a';
        dimTitle.style.fontSize = '12px';
        dimTitle.innerText = '📐 Dimension Tables:';
        tablesBox.appendChild(dimTitle);
        
        for (const [tableName, columns] of Object.entries(stepData.dimensionTables)) {
            const tableDiv = document.createElement('div');
            tableDiv.style.marginBottom = '6px';
            tableDiv.innerHTML = `<strong>${tableName}</strong>: <code style="background:#e2e8f0; padding:2px 6px; border-radius:4px; font-size:10px;">${columns.join(', ')}</code>`;
            tablesBox.appendChild(tableDiv);
        }
    }
}

// ==========================================================
// 💬 INTERACTIVE HITL CONVERSATIONAL FEEDBACK LOOPS
// ==========================================================
function setupFeedbackButtons() {
    for (let i = 2; i <= 5; i++) {
        const btn = document.getElementById(`feedback-btn-${i}`);
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                handleFeedbackSubmission(i);
            });
        }
    }
}

async function handleFeedbackSubmission(step) {
    const feedbackInput = document.getElementById(`feedback-${step}`);
    const feedbackText = feedbackInput.value.trim();
    if (!feedbackText) {
        alert("Please enter your feedback or request for modifications before clicking modify!");
        return;
    }
    
    const btn = document.getElementById(`feedback-btn-${step}`);
    const originalText = btn.innerText;
    btn.disabled = true;
    btn.innerText = "Applying analyst feedback...";
    
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/build/step`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sessionId: workflowSessionId,
                step: step,
                approved: false,
                feedback: feedbackText
            })
        });
        const data = await res.json();
        
        if (res.ok) {
            latestStepData = data.stepOutput;
            feedbackInput.value = ''; // clear input
            
            // Render updated contents depending on step
            if (step === 2) {
                renderStep2Data(latestStepData);
                renderAgentDecisions(2, latestStepData.agentDecisions);
            } else if (step === 3) {
                const pre = document.getElementById('step3-sql-data');
                pre.innerText = JSON.stringify(latestStepData.transformedData, null, 2);
                renderAgentDecisions(3, latestStepData.agentDecisions);
            } else if (step === 4) {
                const pre = document.getElementById('step4-schema-json');
                pre.innerText = JSON.stringify(latestStepData.schema, null, 2);
                renderAgentDecisions(4, latestStepData.agentDecisions);
            } else if (step === 5) {
                const pre = document.getElementById('step5-skeleton-html');
                pre.innerText = latestStepData.skeletonHtml;
                renderAgentDecisions(5, latestStepData.agentDecisions);
            }
            alert(`Step ${step} updated successfully with feedback!`);
        } else {
            alert(`Failed to apply feedback: ${data.detail}`);
        }
    } catch (err) {
        alert(`Failed to communicate with Agentic server: ${err.message}`);
    } finally {
        btn.disabled = false;
        btn.innerText = originalText;
    }
}

// ==========================================================
// 📋 PUBLISHED REPORTS GRID SIDEBAR
// ==========================================================
async function loadPublishedReportsList() {
    const grid = document.getElementById('published-grid');
    
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/build/reports`);
        const data = await res.json();
        
        publishedReports = data;
        grid.innerHTML = '';
        
        if (data.length === 0) {
            grid.innerHTML = '<div class="placeholder-msg" style="text-align:center; font-size:12px; color:#94a3b8; padding:20px;">No published reports cataloged.</div>';
            return;
        }
        
        data.forEach(rep => {
            const card = document.createElement('div');
            card.className = 'published-item';
            card.innerHTML = `
                <div>
                    <span>📄 ${rep.name}</span><br/>
                    <code>${rep.id}</code>
                </div>
                <button class="btn" style="padding:4px 8px; font-size:11px;">View ➔</button>
            `;
            card.addEventListener('click', () => {
                window.open(rep.path, '_blank');
            });
            grid.appendChild(card);
        });
    } catch(err) {
        grid.innerHTML = `<div style="color:red; font-size:12px; padding:10px;">Load failed: ${err.message}</div>`;
    }
}

// ==========================================================
// 🤖 RENDERING MULTI-AGENT CONSENSUS DECISIONS LOG PANEL
// ==========================================================
function renderAgentDecisions(step, agentDecisions) {
    const box = document.getElementById(`agent-decisions-${step}`);
    if (!box) return;
    
    if (!agentDecisions || agentDecisions.length === 0) {
        box.style.display = 'none';
        return;
    }
    
    box.style.display = 'block';
    box.innerHTML = `
        <h4>🤖 Multi-Agent Decisions Dashboard</h4>
        ${agentDecisions.map(d => `
            <div class="agent-decision-item">
                <div>
                    <span class="agent-badge">${d.agent}</span>
                    <span style="font-weight:700; color:${d.status.includes('Signed') || d.status === 'Approved' ? 'var(--success-color)' : 'var(--accent-color)'}; font-size:10px;">
                        [${d.status.toUpperCase()}]
                    </span>
                    <span style="font-weight:600; font-size:12px; color:#1e293b;">${d.decision}</span>
                </div>
                <div class="agent-rationale">
                    <strong>Rationale:</strong> ${d.rationale}
                </div>
            </div>
        `).join('')}
    `;
}

// ==========================================================
// ✨ PRISM CONSOLIDATION STATE LOADER BRIDGE
// ==========================================================
function checkForPrismPlan() {
    const rawPlan = localStorage.getItem('prism_consolidation_plan');
    if (rawPlan) {
        try {
            const plan = JSON.parse(rawPlan);
            
            // Auto-populate Step 1 Form Fields
            document.getElementById('step1-req').value = plan.requirements || '';
            document.getElementById('step1-ctx').value = plan.context || '';
            
            // Force Workspace creation mode
            currentMode = 'create';
            const btnCreate = document.getElementById('mode-create');
            const btnUpdate = document.getElementById('mode-update');
            const updateSelectRow = document.getElementById('update-select-row');
            if (btnCreate && btnUpdate && updateSelectRow) {
                btnCreate.classList.add('active');
                btnUpdate.classList.remove('active');
                updateSelectRow.style.display = 'none';
            }
            
            // Render glassmorphic loading alert banner
            const alertBox = document.getElementById('prism-plan-alert');
            const alertTitle = document.getElementById('prism-plan-alert-title');
            if (alertBox && alertTitle) {
                alertTitle.innerText = `Merging: ${plan.reportName || 'Screened Inventory'}`;
                alertBox.classList.remove('hide');
                
                // Clear button handler
                document.getElementById('prism-clear-plan-btn').onclick = (e) => {
                    e.preventDefault();
                    localStorage.removeItem('prism_consolidation_plan');
                    alertBox.classList.add('hide');
                    document.getElementById('step1-req').value = '';
                    document.getElementById('step1-ctx').value = '';
                };
            }
            
            // Clear local storage key so page reload maintains current edits
            localStorage.removeItem('prism_consolidation_plan');
            
        } catch (e) {
            console.error("Failed to parse loaded PRISM consolidation plan:", e);
        }
    }
}

