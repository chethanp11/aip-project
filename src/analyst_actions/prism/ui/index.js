// Default seed report templates list
let reportCatalog = [
    { name: 'Margin Breakdown Q1', query: 'SELECT (revenue - cost) / active_base FROM regional_ledger', usage: 120, owner: 'Planning Operations', type: 'SQL Database' },
    { name: 'Yield Spread Review', query: 'SELECT (revenue-cost)/active_base FROM regional_ledger', usage: 8, owner: 'Leadership Review', type: 'SQL Database' },
    { name: 'Regional Balance Ledger', query: 'SELECT allocated_value / baseline_value FROM operating_balances', usage: 84, owner: 'Operations', type: 'SQL Database' },
    { name: 'Deposit Volatility Index', query: 'SELECT outflow_rate FROM liquidity_sweeps', usage: 4, owner: 'Compliance Planning', type: 'SQL Database' }
];

const tbody = document.getElementById('catalog-rows');
const thresholdSlider = document.getElementById('sim-threshold');
const thresholdLbl = document.getElementById('lbl-threshold');
const emptyState = document.getElementById('results-empty');
const resultsBox = document.getElementById('prism-results');
const statDups = document.getElementById('stat-dups');
const statOverlaps = document.getElementById('stat-overlaps');
const deprecationContainer = document.getElementById('deprecation-list-container');
const deprecationCards = document.getElementById('deprecation-cards');
const consolidationCards = document.getElementById('consolidation-cards');
const executiveSummary = document.getElementById('executive-summary');

// Render Catalog Grid
function renderCatalog() {
    tbody.innerHTML = '';
    reportCatalog.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <input type="text" class="spreadsheet-input" value="${item.name}" onchange="updateCatalogField(${index}, 'name', this.value)" placeholder="Report Name..." />
            </td>
            <td>
                <input type="text" class="spreadsheet-input" value="${item.query}" onchange="updateCatalogField(${index}, 'query', this.value)" placeholder="SQL Query / Columns..." />
            </td>
            <td>
                <input type="number" class="spreadsheet-input" value="${item.usage}" onchange="updateCatalogField(${index}, 'usage', this.value)" placeholder="Usage..." />
            </td>
            <td>
                <button class="spreadsheet-btn-del" onclick="deleteCatalogRow(${index})">✕</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Update live field in catalog
window.updateCatalogField = function(index, field, val) {
    if (field === 'usage') {
        const intVal = parseInt(val);
        reportCatalog[index][field] = isNaN(intVal) ? 0 : intVal;
    } else {
        reportCatalog[index][field] = val.trim();
    }
};

// Delete row
window.deleteCatalogRow = function(index) {
    reportCatalog.splice(index, 1);
    renderCatalog();
};

// Add row
document.getElementById('btn-add-row').addEventListener('click', () => {
    reportCatalog.push({ name: '', query: '', usage: 15, owner: 'Planning Operations', type: 'CustomSQL' });
    renderCatalog();
});

// Update threshold label
thresholdSlider.addEventListener('input', () => {
    thresholdLbl.innerText = thresholdSlider.value;
});

// Presets Loading
document.getElementById('preset-excel').addEventListener('click', () => {
    reportCatalog = [
        { name: 'Q1_Ledger - Deposits_Sheet', query: 'SELECT amount, balance, account_id FROM deposits', usage: 140, owner: 'Treasury Operations', type: 'Excel' },
        { name: 'Deposit_Ledger_Archive', query: 'SELECT balance, amount, account_id FROM deposits', usage: 5, owner: 'Retail Operations', type: 'Excel' },
        { name: 'Regulatory_Liquidity_Ratio', query: 'SELECT net_assets / liquidity_buffer FROM custom_table', usage: 78, owner: 'Compliance', type: 'Excel' }
    ];
    renderCatalog();
});

document.getElementById('preset-html').addEventListener('click', () => {
    reportCatalog = [
        { name: 'Basel Liquidity Sweeps', query: 'SELECT sweep_id, target_amount FROM sweeps', usage: 98, owner: 'Compliance', type: 'HTML' },
        { name: 'Liquidity Sweep Execution Card', query: 'SELECT sweep_id, target_amount, execution_date FROM sweeps', usage: 120, owner: 'Compliance Planning', type: 'HTML' },
        { name: 'SME Corporate Balances', query: 'SELECT corporate_id, balance FROM clients', usage: 3, owner: 'Credit Risk', type: 'HTML' }
    ];
    renderCatalog();
});

document.getElementById('preset-neutral').addEventListener('click', () => {
    reportCatalog = [
        { name: 'Margin Breakdown Q1', query: 'SELECT (revenue - cost) / active_base FROM regional_ledger', usage: 120, owner: 'Planning Operations', type: 'SQL Database' },
        { name: 'Yield Spread Review', query: 'SELECT (revenue-cost)/active_base FROM regional_ledger', usage: 8, owner: 'Leadership Review', type: 'SQL Database' },
        { name: 'Regional Balance Ledger', query: 'SELECT allocated_value / baseline_value FROM operating_balances', usage: 84, owner: 'Operations', type: 'SQL Database' },
        { name: 'Deposit Volatility Index', query: 'SELECT outflow_rate FROM liquidity_sweeps', usage: 4, owner: 'Compliance Planning', type: 'SQL Database' }
    ];
    renderCatalog();
});

// Perform Catalog Analysis
document.getElementById('prism-btn').addEventListener('click', async () => {
    const btn = document.getElementById('prism-btn');
    btn.disabled = true;
    btn.innerHTML = '🔍 Auditing Catalog...';
    
    const directives = document.getElementById('prism-prompt').value.trim();
    const thresholdVal = parseFloat(thresholdSlider.value) / 100.0;
    
    // Filter out rows with missing names or query columns
    const cleanedReports = reportCatalog.filter(r => r.name !== '' && r.query !== '');
    
    // Format mock columns so server Jaccard calculations work
    // Extracts tokens from SELECT query to mock schema columns
    const reportsPayload = cleanedReports.map(r => {
        let cols = [];
        if (r.query.toLowerCase().includes('select')) {
            const match = r.query.match(/select\s+(.*?)\s+from/i);
            if (match && match[1]) {
                cols = match[1].split(',').map(c => c.trim().replace(/\(.*?\)/g, '').replace(/[^a-zA-Z0-9_]/g, ''));
            }
        }
        if (cols.length === 0) {
            cols = ['amount', 'balance', 'id'];
        }
        return {
            name: r.name,
            query: r.query,
            columns: cols,
            usage: r.usage,
            owner: r.owner,
            type: r.type || 'Custom'
        };
    });
    
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/prism-lite`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                reports: reportsPayload,
                prompt: directives,
                threshold: thresholdVal
            })
        });
        
        if (!res.ok) {
            throw new Error(`HTTP Error Status: ${res.status}`);
        }
        
        const data = await res.json();
        
        emptyState.classList.add('hide');
        
        // Render stats counters
        statDups.innerText = data.duplicates ? data.duplicates.length : 0;
        statOverlaps.innerText = data.overlaps ? data.overlaps.length : 0;
        
        // Render Distilled AI summary
        executiveSummary.innerText = data.summary || 'Audit complete.';
        
        // Render low usage candidates
        if (data.usageInsights && data.usageInsights.length > 0) {
            deprecationCards.innerHTML = data.usageInsights.map(item => `
                <div class="deprecation-card">
                    ⚠️ Deprecate low-usage catalog card: <strong>${item.name}</strong> 
                    (Usage: ${item.usage} queries/mo, Owned by: ${item.owner})
                </div>
            `).join('');
            deprecationContainer.classList.remove('hide');
        } else {
            deprecationContainer.classList.add('hide');
        }
        
        // Render dynamic consolidation plan cards
        if (data.consolidationPlans && data.consolidationPlans.length > 0) {
            consolidationCards.innerHTML = data.consolidationPlans.map(plan => `
                <div class="plan-card">
                    <div class="plan-card-header">
                        <span class="plan-title">${plan.proposedName}</span>
                        <span class="badge overlap">${plan.similarity}% Overlap</span>
                    </div>
                    <div class="plan-field">
                        <strong>Redundancy Type:</strong> ${plan.redundancyType}
                    </div>
                    <div class="plan-field">
                        <strong>Explanation:</strong> ${plan.explanation}
                    </div>
                    <div class="plan-field" style="background:#f1f5f9; padding:8px; border-radius:6px; font-family:monospace; font-size:11px; margin-top:4px; border:1px solid var(--border-color);">
                        ${plan.proposedRequirements}
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                        <span class="plan-savings">✓ ${plan.savings}</span>
                    </div>
                </div>
            `).join('');
        } else {
            consolidationCards.innerHTML = `
                <div style="text-align:center; padding:24px; color:var(--text-secondary); font-size:12.5px; border:1px dashed var(--border-color); border-radius:8px;">
                    ✓ No consolidation action plans generated for this threshold.
                </div>
            `;
        }
        
        resultsBox.classList.remove('hide');
        
    } catch(err) {
        alert("PRISM Catalog Audit failed: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🔍 Analyze Catalog';
    }
});

// Initialize catalog grid on start
renderCatalog();