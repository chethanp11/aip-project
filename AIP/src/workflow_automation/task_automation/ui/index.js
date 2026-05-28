
const codeSeed = `import sys
import time

print("--- COGNITIVE OPERATIONAL SWEEP REPORT ---")
print("Authenticating secure API retrieval endpoints...")
time.sleep(0.4)
print("Querying LMS database liquidity sweep records...")
print("Analyzing historical branch default patterns...")

# Verify compliance checks
limit = 110.0
current_buffer = 114.5
compliant = current_buffer >= limit

print(f"Required Basel III LCR Ratio: {limit}%")
print(f"Active ALCO HQLA Level 1 Buffer: {current_buffer}%")
print(f"Compliance status check: {'PASSED' if compliant else 'FAILED'}")
if compliant:
    print("STATUS: COMPLIANT | Sweeps authorized for branch transfers.")
else:
    print("STATUS: OUTFLOW_WARNING | Potential liquidity stress identified.")
`;

// Seed the code input immediately
document.getElementById('task-code-in').value = codeSeed;

async function getApprovals() {
    const feed = document.getElementById('approvals-feed');
    feed.innerHTML = '<div class="loader">🔍 Auditing compliance queues...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/workflows/automation/approvals`);
        const data = await res.json();
        feed.innerHTML = '';
        
        if (data.length === 0) {
            feed.innerHTML = '<p class="success-msg" style="font-size:12px;">✅ Compliance approvals cleared. Zero active gates.</p>';
            return;
        }
        
        feed.innerHTML = data.map(app => `
            <div class="approval-card">
                <div style="margin-bottom: 10px;">
                    <strong style="color: #38bdf8; font-size:13px;">${app.name}</strong>
                    <p style="font-size:11px; color:#94a3b8; margin-top:2px;">Approval Session ID: <strong>${app.id}</strong></p>
                    <p style="font-size:11px; color:#94a3b8; margin-top:2px;">Active Gate: <strong>${app.step}</strong></p>
                </div>
                <div style="display:flex; gap:8px;">
                    <button class="btn-approve" onclick="approveGate('${app.id}', true)">🛡️ Approve</button>
                    <button class="btn-reject" onclick="approveGate('${app.id}', false)">❌ Reject</button>
                </div>
            </div>
        `).join('');
    } catch(err) {
        feed.innerHTML = `<p class="error">Query failed: ${err.message}</p>';`;
    }
}

async function approveGate(id, state) {
    const traceBox = document.getElementById('resumed-traces-box');
    const container = document.getElementById('resumed-traces');
    
    traceBox.classList.remove('hide');
    container.innerHTML = '<div class="loader">⚙️ Synced with Redis session cache. Resuming LangGraph execution loop...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/workflows/automation/approve`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ approvalId: id, approved: state })
        });
        const data = await res.json();
        
        if (res.ok) {
            if (state) {
                container.innerHTML = `
                    <p class="success-msg" style="margin-bottom: 10px;">✅ Pipeline successfully approved and executed to completion!</p>
                    <div style="display:flex; flex-direction:column; gap:6px;">
                        ${(data.traces || []).map(t => `
                            <div style="background:#0f172a; padding:6px 10px; border-radius:4px; border:1px solid #334155;">
                                <span style="color:#0ea5e9;">${t.stepId}</span>: ${t.status.toUpperCase()} (${t.durationMs || 0}ms)
                            </div>
                        `).join('')}
                    </div>
                `;
            } else {
                container.innerHTML = `<p class="error">❌ Workflow rejected and session purged from cache.</p>`;
            }
        } else {
            container.innerHTML = `<p class="error">❌ Resume failed: ${data.detail || 'Gate error'}</p>`;
        }
        getApprovals();
    } catch(err) {
        container.innerHTML = `<p class="error">❌ Gate communication error: ${err.message}</p>`;
    }
}

async function fetchTaskHistory() {
    const feed = document.getElementById('tasks-history-feed');
    
    try {
        const res = await fetch(`${API_BASE}/workflows/automation/tasks/history`);
        if (!res.ok) return; // Route may not be loaded yet
        const data = await res.json();
        
        if (data.length === 0) {
            feed.innerHTML = '<p style="color: #64748b; font-style: italic; font-size: 12px;">No runs triggered yet.</p>';
            return;
        }
        
        feed.innerHTML = data.map(task => {
            const isCompleted = task.status === 'completed';
            const badgeClass = isCompleted ? 'completed' : (task.status === 'running' ? 'running' : 'failed');
            const fileLink = isCompleted && task.artifacts && task.artifacts.length > 0 ? task.artifacts[0].path : '';
            
            return `
                <div class="history-item">
                    <div class="history-header">
                        <div>
                            Task: <strong>${task.id}</strong>
                            <span style="font-size:10px; color:#64748b; margin-left:6px;">[Trigger: ${task.trigger}]</span>
                        </div>
                        <span class="badge-status ${badgeClass}">${task.status.toUpperCase()}</span>
                    </div>
                    <div style="font-size:10px; color:#94a3b8; margin-top:4px;">
                        Started: ${task.startTime || 'unknown'} | Latency: ${task.durationMs || 0}ms
                    </div>
                    ${task.stdout ? `<div class="console-box">${task.stdout}</div>` : ''}
                    ${task.stderr ? `<div class="console-box" style="color:#ef4444; border-color:rgba(239,68,68,0.3); background:rgba(239,68,68,0.05);">${task.stderr}</div>` : ''}
                    ${fileLink ? `
                        <div style="font-size:10px; margin-top:8px; color:#10b981; font-weight:500;">
                            📄 Physical Storage Artifact: <span style="color:#f8fafc; font-family:monospace;">${fileLink.split('/').pop()}</span>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
    } catch(e) {
        console.warn("Could not fetch task history:", e);
    }
}

document.getElementById('btn-submit-task').addEventListener('click', async () => {
    const tId = document.getElementById('task-id-in').value.trim();
    const trigger = document.getElementById('task-trigger-in').value;
    const code = document.getElementById('task-code-in').value.trim();
    
    if (!tId || !code) {
        alert("Please specify a Task ID and Python code string!");
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/workflows/automation/tasks/submit`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ taskId: tId, trigger: trigger, code: code })
        });
        
        if (res.ok) {
            // Trigger rapid polling to trace execution output
            fetchTaskHistory();
            let count = 0;
            const interval = setInterval(() => {
                fetchTaskHistory();
                count++;
                if (count > 5) clearInterval(interval);
            }, 1000);
        } else {
            alert("Sandbox submission failed. Verify endpoints.");
        }
    } catch(err) {
        alert("Sandbox submission error: " + err.message);
    }
});

window.approveGate = approveGate;
document.getElementById('load-approvals').addEventListener('click', getApprovals);

// Initial query calls
getApprovals();
fetchTaskHistory();

// Poll background history periodically
setInterval(fetchTaskHistory, 4000);