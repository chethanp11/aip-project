// Seed segment contribution entries
let ledgerItems = [
    { segment: 'North Plaza Operations', value: 45.2 },
    { segment: 'Digital Core Allocations', value: 24.8 },
    { segment: 'South Bay Segment', value: 12.5 },
    { segment: 'Treasury Overheads', value: 6.5 }
];

const tbody = document.getElementById('ledger-rows');
const emptyState = document.getElementById('results-empty');
const resultsBox = document.getElementById('rca-results');
const primaryDriverText = document.getElementById('primary-driver-text');
const waterfallChart = document.getElementById('waterfall-chart');
const narrativeContainer = document.getElementById('rca-narrative');

// Render spreadsheet grid
function renderGrid() {
    tbody.innerHTML = '';
    ledgerItems.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <input type="text" class="spreadsheet-input" value="${item.segment}" onchange="updateSegmentField(${index}, 'segment', this.value)" placeholder="Enter segment name..." />
            </td>
            <td>
                <input type="number" class="spreadsheet-input" step="0.1" value="${item.value}" onchange="updateSegmentField(${index}, 'value', this.value)" placeholder="Weight..." />
            </td>
            <td>
                <button class="spreadsheet-btn-del" onclick="deleteRow(${index})">✕</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Update field in live list
window.updateSegmentField = function(index, field, val) {
    if (field === 'value') {
        const floatVal = parseFloat(val);
        ledgerItems[index][field] = isNaN(floatVal) ? 0.0 : floatVal;
    } else {
        ledgerItems[index][field] = val.trim();
    }
};

// Delete row
window.deleteRow = function(index) {
    ledgerItems.splice(index, 1);
    renderGrid();
};

// Add new row
document.getElementById('btn-add-row').addEventListener('click', () => {
    ledgerItems.push({ segment: '', value: 0.0 });
    renderGrid();
});

// A simple high-fidelity Markdown parser for the diagnostic summary
function parseMarkdown(mdText) {
    if (!mdText) return '';
    let html = mdText;
    
    // Clean escape newlines
    html = html.replace(/\n/g, '<br/>');
    
    // Headers
    html = html.replace(/### (.*?)(<br\/>|$)/g, '<h3>$1</h3>');
    html = html.replace(/## (.*?)(<br\/>|$)/g, '<h2>$1</h2>');
    html = html.replace(/# (.*?)(<br\/>|$)/g, '<h1>$1</h1>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Lists
    html = html.replace(/\* (.*?)(<br\/>|$)/g, '<li>$1</li>');
    
    return html;
}

// Perform RCA Diagnostic Scan
document.getElementById('rca-btn').addEventListener('click', async () => {
    const btn = document.getElementById('rca-btn');
    btn.disabled = true;
    btn.innerHTML = '🔍 Executing Diagnostics...';
    
    const dataset = document.getElementById('rca-dataset').value;
    const directives = document.getElementById('rca-prompt').value.trim();
    
    // Filter clean list
    const cleanedMetrics = ledgerItems.filter(item => item.segment !== '');
    
    try {
        const res = await fetch(`${API_BASE}/workflows/analytics/rca`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                datasetName: dataset,
                metricsData: cleanedMetrics,
                prompt: directives
            })
        });
        
        if (!res.ok) {
            throw new Error(`HTTP Error Status: ${res.status}`);
        }
        
        const data = await res.json();
        
        emptyState.classList.add('hide');
        
        // Render primary driver alert
        primaryDriverText.innerHTML = `Identified **${data.primaryDriver}** as the primary factor responsible for overall variance. Recommend focused audits on this channel.`;
        primaryDriverText.innerHTML = parseMarkdown(primaryDriverText.innerHTML);
        
        // Render dynamic waterfall/contribution rows
        const maxVal = Math.max(...data.drivers.map(d => d.value), 1);
        waterfallChart.innerHTML = data.drivers.map(d => {
            const pct = Math.max(Math.min((d.value / maxVal) * 100, 100), 2); // Cap between 2% and 100%
            return `
                <div class="waterfall-row">
                    <span class="waterfall-label">${d.segment}</span>
                    <div class="waterfall-track">
                        <div class="waterfall-bar" style="width: ${pct}%"></div>
                    </div>
                    <span class="waterfall-value">${d.value.toFixed(1)}%</span>
                </div>
            `;
        }).join('');
        
        // Render diagnostic narrative brief
        narrativeContainer.innerHTML = parseMarkdown(data.narrative);
        
        resultsBox.classList.remove('hide');
        
    } catch(err) {
        alert("RCA Diagnostic failed: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🔍 Run Diagnostic Scan';
    }
});

// Load baseline on initialize
renderGrid();