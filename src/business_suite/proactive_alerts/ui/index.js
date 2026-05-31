const refreshBtn = document.getElementById('refresh-alerts');
const alertsFeed = document.getElementById('alerts-feed');
const resultsEmpty = document.getElementById('results-empty');


const ruleInput = document.getElementById('rule-input');
const addRuleBtn = document.getElementById('add-rule-btn');
const activeRulesList = document.getElementById('active-rules-list');
const rulesCount = document.getElementById('rules-count');

// switch shell navigation page from iframe
function deepLinkToPage(pageName) {
    if (window.parent && typeof window.parent.switchPage === 'function') {
        window.parent.switchPage(pageName);
    } else {
        console.log(`Deep linking requested to parent view: ${pageName}`);
        alert(`Deep link target: switching view to '${pageName}'`);
    }
}

// Rules CRUD integrations
async function loadAlertRules() {
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/proactive-insights/rules`);
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        const rules = await res.json();
        rulesCount.innerText = rules.length;
        
        if (rules.length === 0) {
            activeRulesList.innerHTML = `<div class="empty-rules">No active rule scanners. Seeding defaults...</div>`;
            return;
        }
        
        activeRulesList.innerHTML = rules.map(r => `
            <div class="active-rule-item">
                <div class="rule-item-details">
                    <span class="rule-pulse-dot"></span>
                    <span class="rule-text-content">${r.rule}</span>
                </div>
                <button class="rule-delete-btn" onclick="deleteAlertRule('${r.id}')" title="Remove scanner">✕</button>
            </div>
        `).join('');
    } catch (err) {
        console.error("Failed to load rules:", err);
    }
}

async function addAlertRule(ruleText) {
    if (!ruleText.trim()) return;
    addRuleBtn.disabled = true;
    addRuleBtn.innerHTML = '⚡ Activating...';
    
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/proactive-insights/rules`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rule: ruleText })
        });
        
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        
        ruleInput.value = '';
        await loadAlertRules();
        await refreshAlertsStream();
    } catch (err) {
        alert("Failed to add rule: " + err.message);
    } finally {
        addRuleBtn.disabled = false;
        addRuleBtn.innerHTML = '⚡ Save & Activate Scanner';
    }
}

async function deleteAlertRule(ruleId) {
    if (!confirm("Are you sure you want to deactivate this rule scanner?")) return;
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/proactive-insights/rules/${ruleId}`, {
            method: 'DELETE'
        });
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        await loadAlertRules();
        await refreshAlertsStream();
    } catch (err) {
        alert("Failed to delete rule: " + err.message);
    }
}

function seedTemplate(templateText) {
    ruleInput.value = templateText;
    ruleInput.focus();
}

// Fetch baselines and alerts
async function refreshAlertsStream() {
    refreshBtn.disabled = true;
    refreshBtn.innerHTML = '🔍 Scanning Active Ledgers...';
    
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/proactive-insights`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!res.ok) {
            throw new Error(`HTTP Error Status: ${res.status}`);
        }
        
        const data = await res.json();
        
        if (data.alerts && data.alerts.length > 0) {
            resultsEmpty.classList.add('hide');
            
            alertsFeed.innerHTML = data.alerts.map(alertItem => {
                const sev = (alertItem.severity || 'Medium').toLowerCase();
                let sevBadgeClass = 'medium';
                let icon = '⚠️';
                
                if (sev === 'high') {
                    sevBadgeClass = 'high';
                    icon = '🚨';
                } else if (sev === 'low') {
                    sevBadgeClass = 'low';
                    icon = 'ℹ️';
                }
                
                // KMS Context details block
                const kmsBlock = alertItem.kms_grounding ? `
                    <div class="alert-kms-box">
                        <span class="kms-header">📚 Grounded via KMS Regulation Context</span>
                        <p class="kms-text">${alertItem.kms_grounding}</p>
                    </div>
                ` : '';
                
                return `
                    <div class="alert-item-card severity-${sev}">
                        <div class="alert-card-header">
                            <span class="alert-metric-name">${icon} ${alertItem.metric} Exception</span>
                            <span class="alert-badge ${sevBadgeClass}">${alertItem.severity} Risk</span>
                        </div>
                        <div class="alert-body">
                            <p class="alert-message-text">${alertItem.message}</p>
                            
                            ${kmsBlock}
                            
                            <div class="alert-recommendation-box">
                                <span class="recom-header">Recommended Standard Response Procedure</span>
                                <p class="recom-text">${alertItem.recommendation}</p>
                                
                                <div class="alert-shortcuts-row">
                                    <a class="shortcut-link" onclick="deepLinkToPage('scenario-analysis')">🎲 Run What-If Simulation</a>
                                    <span style="color:#cbd5e1;">|</span>
                                    <a class="shortcut-link" onclick="deepLinkToPage('kms')">📚 Search KMS Glossary</a>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
            alertsFeed.classList.remove('hide');
        } else {
            alertsFeed.classList.add('hide');
            resultsEmpty.innerHTML = `
                <div class="empty-icon">✓</div>
                <h4>Scan Complete: Ledgers Fully Optimal</h4>
                <p class="app-desc" style="font-size: 12px; margin-top: 4px;">Active monitoring has run. All custom and default rules reside safely inside target bounds.</p>
            `;
            resultsEmpty.classList.remove('hide');
        }
        
    } catch(err) {
        alert("Alert scanning failed: " + err.message);
    } finally {
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '🔍 Scan Active Ledgers';
    }
}

// Bind event listeners
addRuleBtn.addEventListener('click', () => {
    addAlertRule(ruleInput.value);
});

refreshBtn.addEventListener('click', refreshAlertsStream);

// Make globals for inline onclick calls in iframe context
window.seedTemplate = seedTemplate;
window.deleteAlertRule = deleteAlertRule;

// Initialize on startup
async function init() {
    await loadAlertRules();
    await refreshAlertsStream();
}
init();