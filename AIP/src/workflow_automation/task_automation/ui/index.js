
            async function getApprovals() {
                const feed = document.getElementById('approvals-feed');
                feed.innerHTML = '<div class="loader">🔍 Auditing compliance queues...</div>';
                
                try {
                    const res = await fetch(`${API_BASE}/workflows/automation/approvals`);
                    const data = await res.json();
                    feed.innerHTML = '';
                    
                    if (data.length === 0) {
                        feed.innerHTML = '<p class="success-msg">✅ Approvals cleared. Zero gates active.</p>';
                        return;
                    }
                    
                    feed.innerHTML = data.map(app => `
                        <div style="border:1px solid #ddd; padding:12px; border-radius:6px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <strong>${app.name}</strong>
                                <p style="font-size:11px; margin-top:2px;">Gate: ${app.step}</p>
                            </div>
                            <div style="display:flex; gap:8px;">
                                <button class="btn" style="background:#10b981; padding:4px 8px; font-size:11px;" onclick="approveGate('${app.id}', true)">Approve</button>
                                <button class="btn" style="background:#f43f5e; padding:4px 8px; font-size:11px;" onclick="approveGate('${app.id}', false)">Reject</button>
                            </div>
                        </div>
                    `).join('');
                } catch(err) {
                    feed.innerHTML = `<p class="error">Query failed: ${err.message}</p>`;
                }
            }

            async function approveGate(id, state) {
                try {
                    await fetch(`${API_BASE}/workflows/automation/approve`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ approvalId: id, approved: state })
                    });
                    alert(state ? "Approval Signed!" : "Task Purged!");
                    getApprovals();
                } catch(err) {
                    alert(err.message);
                }
            }
            window.approveGate = approveGate;
            document.getElementById('load-approvals').addEventListener('click', getApprovals);
            getApprovals();
        