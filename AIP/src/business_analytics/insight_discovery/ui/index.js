// Default Predefined Seed Cohorts for business demonstration
let segmentsList = [
    { cohort: 'Digital Cash Accounts', timeline: [1.2, -0.4, 2.5, 8.4, 12.6] },
    { cohort: 'High Yield Loans', timeline: [85.0, 79.4, 62.1, 45.3] },
    { cohort: 'Treasury Reserve Balance', timeline: [4.5, 4.6, 4.7, 4.8, 5.0] },
    { cohort: 'SME Credit Portfolios', timeline: [12.4, 11.2, 8.4, -6.5] }
];

const container = document.getElementById('cohorts-container');
const resultsEmpty = document.getElementById('results-empty');
const resultsGrid = document.getElementById('disc-results');
const scanCountLbl = document.getElementById('scan-count');

// Render the Registry UI
function renderCohorts() {
    container.innerHTML = '';
    segmentsList.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'cohort-item';
        div.innerHTML = `
            <div class="cohort-info">
                <span class="cohort-name">${item.cohort}</span>
                <span class="cohort-data-points">Timeline: [${item.timeline.join(', ')}]</span>
            </div>
            <button class="btn-remove" onclick="removeCohort(${index})">✕</button>
        `;
        container.appendChild(div);
    });
}

// Remove segment
window.removeCohort = function(index) {
    segmentsList.splice(index, 1);
    renderCohorts();
};

// Add Custom segment
document.getElementById('btn-add-cohort').addEventListener('click', () => {
    const nameInput = document.getElementById('new-cohort-name');
    const timelineInput = document.getElementById('new-cohort-timeline');
    
    const name = nameInput.value.trim();
    const rawTimeline = timelineInput.value.trim();
    
    if (!name) {
        alert("Please enter a valid cohort name.");
        return;
    }
    
    // Parse floats
    const timeline = rawTimeline.split(',')
        .map(v => parseFloat(v.trim()))
        .filter(v => !isNaN(v));
        
    if (timeline.length === 0) {
        alert("Please enter a comma-separated list of numeric historical MoM growth values.");
        return;
    }
    
    segmentsList.push({ cohort: name, timeline: timeline });
    nameInput.value = '';
    timelineInput.value = '';
    renderCohorts();
});

// Render Dynamic SVGs Sparklines
function generateSparklineSvg(timeline, isSurging) {
    if (timeline.length < 2) return '';
    const width = 180;
    const height = 40;
    const padding = 4;
    
    const maxVal = Math.max(...timeline);
    const minVal = Math.min(...timeline);
    const range = maxVal - minVal === 0 ? 1 : maxVal - minVal;
    
    const points = timeline.map((val, idx) => {
        const x = (idx / (timeline.length - 1)) * (width - padding * 2) + padding;
        const y = height - ((val - minVal) / range) * (height - padding * 2) - padding;
        return `${x},${y}`;
    }).join(' ');
    
    const strokeColor = isSurging ? '#10b981' : '#ef4444';
    
    return `
        <svg class="sparkline-svg" viewBox="0 0 ${width} ${height}">
            <polyline class="sparkline-path" points="${points}" stroke="${strokeColor}" />
        </svg>
    `;
}

// Trigger Segment Scan via POST endpoint
document.getElementById('disc-btn').addEventListener('click', async () => {
    const btn = document.getElementById('disc-btn');
    btn.disabled = true;
    btn.innerHTML = '🔍 Scanning Segment Timelines...';
    
    try {
        const res = await fetch(`${API_BASE}/workflows/analytics/insight-discovery`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ segmentsData: segmentsList })
        });
        
        if (!res.ok) {
            throw new Error(`HTTP Error Status: ${res.status}`);
        }
        
        const data = await res.json();
        
        scanCountLbl.innerText = `Scanned: ${data.totalScanned || segmentsList.length} cohorts`;
        
        if (!data.insights || data.insights.length === 0) {
            resultsGrid.classList.add('hide');
            resultsEmpty.innerHTML = `
                <div class="empty-icon">✓</div>
                <h4>Scan Completed: All Segments Stable</h4>
                <p class="app-desc" style="font-size: 12px; margin-top: 4px;">No material growth volatility exceeding the 5.0% threshold was detected.</p>
            `;
            resultsEmpty.classList.remove('hide');
            return;
        }
        
        resultsEmpty.classList.add('hide');
        resultsGrid.innerHTML = data.insights.map(ins => {
            const isSurging = ins.direction === 'Surging';
            const badgeClass = isSurging ? 'surging' : 'declining';
            const matchingCohort = segmentsList.find(s => s.cohort === ins.cohort);
            const timelineData = matchingCohort ? matchingCohort.timeline : [0, ins.growthRate];
            
            return `
                <div class="insight-card ${badgeClass}">
                    <div class="insight-card-header">
                        <span class="insight-cohort-name">${ins.cohort}</span>
                        <span class="badge ${badgeClass}">${ins.direction}</span>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 4px;">
                        <span class="insight-rate">${isSurging ? '▲' : '▼'} ${ins.growthRate.toFixed(1)}%</span>
                        <div class="sparkline-container">
                            ${generateSparklineSvg(timelineData, isSurging)}
                        </div>
                    </div>
                    <p class="insight-explanation">${ins.explanation}</p>
                </div>
            `;
        }).join('');
        
        resultsGrid.classList.remove('hide');
        
    } catch(err) {
        alert("Insight Discovery Scan failed: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🔍 Run Segment Scan';
    }
});

// Initial Render on startup
renderCohorts();