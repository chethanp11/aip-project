
async function refreshTelemetry() {
    const totalEl = document.getElementById('stat-total');
    const successEl = document.getElementById('stat-success');
    const latencyEl = document.getElementById('stat-latency');
    const costEl = document.getElementById('stat-cost');
    
    try {
        const res = await fetch(`${API_BASE}/workflows/automation/telemetry`);
        const data = await res.json();
        
        if (data.metrics) {
            totalEl.textContent = data.metrics.totalInvocations;
            successEl.textContent = data.metrics.successRate;
            latencyEl.textContent = data.metrics.avgLatency;
            costEl.textContent = data.metrics.totalTokenCost;
        }
        
        // Dynamic Chart Rendering
        const logsRes = await fetch(`${API_BASE}/execution-logs`);
        const logs = await logsRes.json();
        
        const latencies = logs.map(l => l.durationMs || 10).slice(-15);
        if (latencies.length === 0) {
            document.getElementById('chart-canvas').innerHTML = '<p style="color: #64748b; font-style: italic; font-size:12px;">No execution data recorded yet.</p>';
            return;
        }
        
        const maxLat = Math.max(...latencies, 200);
        const canvas = document.getElementById('chart-canvas');
        
        canvas.innerHTML = latencies.map(lat => `
            <div style="background: linear-gradient(to top, #06b6d4, #0ea5e9); width: 30px; height: ${Math.max(15, (lat / maxLat) * 100)}px; border-radius: 4px 4px 0 0; display: flex; justify-content: center; align-items: flex-end; cursor: pointer; transition: height 0.5s;" title="Duration: ${lat}ms">
                <span style="font-size: 8px; color: white; margin-bottom: 2px; font-weight:bold;">${lat}</span>
            </div>
        `).join('');
    } catch(err) {
        console.error("Could not load telemetry grid:", err);
    }
}

async function queryNeo4jLineage() {
    const feed = document.getElementById('lineage-feed');
    feed.innerHTML = '<div class="loader" style="text-align:center; padding:12px;">🌿 Traversing Neo4j Process Lineage indices...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/workflows/automation/monitoring/lineage`);
        if (!res.ok) {
            feed.innerHTML = '<p class="error" style="text-align:center; font-size:12px;">⚠️ Custom lineage endpoint not loaded in Gateway router.</p>';
            return;
        }
        
        const data = await res.json();
        
        if (data.length === 0) {
            feed.innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 12px; text-align:center; padding: 12px;">✅ No process lineage records found. Run a workflow first.</p>';
            return;
        }
        
        feed.innerHTML = data.map(item => `
            <div class="lineage-node">
                <div>
                    <span style="color:#0ea5e9; font-weight:600;">[Workflow Run]</span> 
                    <strong>${item.workflow}</strong>
                    <p style="font-size:11px; color:#94a3b8; margin-top:4px;">
                        Run: <strong>${item.run_id.substring(0, 15)}...</strong> | Step node: <span style="color:#38bdf8;">${item.step}</span>
                        ${item.artifact ? ` | Produced Artifact: <span style="color:#10b981; font-family:monospace;">${item.artifact}</span>` : ''}
                    </p>
                </div>
                <span class="badge-status ${item.step_status === 'completed' ? 'completed' : 'failed'}">${item.step_status.toUpperCase()}</span>
            </div>
        `).join('');
    } catch(err) {
        feed.innerHTML = `<p class="error" style="text-align:center; font-size:12px;">Traversal failed: ${err.message}</p>`;
    }
}

document.getElementById('load-mon').addEventListener('click', refreshTelemetry);
document.getElementById('btn-query-neo4j').addEventListener('click', queryNeo4jLineage);

// Initial load
refreshTelemetry();
queryNeo4jLineage();

// Auto-refresh periodically
setInterval(refreshTelemetry, 5000);