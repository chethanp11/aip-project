
document.getElementById('pulse-btn').addEventListener('click', async () => {
    const btn = document.getElementById('pulse-btn');
    const container = document.getElementById('results-container');
    const statusText = document.getElementById('drift-status');
    const psiScoreText = document.getElementById('psi-score');
    const latencyScoreText = document.getElementById('latency-score');
    const explanationText = document.getElementById('drift-explanation');
    const retrainBtn = document.getElementById('retrain-btn');
    const chatFeed = document.getElementById('chat-feed');

    const selectedBatch = document.getElementById('batch-select').value;
    
    // Select accurate metrics array based on user's drop down choice to simulate drift
    let accuracyArray = [];
    if (selectedBatch === 'stable') {
        accuracyArray = [0.94, 0.93, 0.93, 0.94, 0.93];
    } else if (selectedBatch === 'warning') {
        accuracyArray = [0.94, 0.93, 0.92, 0.88, 0.86];
    } else {
        accuracyArray = [0.94, 0.91, 0.87, 0.80, 0.73];
    }

    btn.disabled = true;
    btn.innerHTML = '🩺 Auditing Telemetry...';
    container.classList.add('hide');
    chatFeed.innerHTML = '';
    retrainBtn.style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/workflows/ds/model-pulse`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                accuracyMetrics: accuracyArray,
                prompt: `Audit monthly covariance logs for ${selectedBatch} distribution shift.`
            })
        });

        if (!res.ok) {
            throw new Error(`Server returned code ${res.status}`);
        }

        const data = await res.json();
        container.classList.remove('hide');

        // 1. Update Alert Status Indicators
        const status = data.status.toUpperCase();
        statusText.innerText = status;
        
        let statusColor = '#10b981'; // stable emerald
        if (status === 'WARNING') {
            statusColor = '#f59e0b'; // warning amber
            statusText.style.color = '#f59e0b';
            retrainBtn.style.display = 'block';
            retrainBtn.innerText = 'Launch Retraining Approval Pipeline';
        } else if (status === 'CRITICAL') {
            statusColor = '#ef4444'; // critical red
            statusText.style.color = '#ef4444';
            retrainBtn.style.display = 'block';
            retrainBtn.innerText = '🚨 Force Automated Retraining Workflow';
        } else {
            statusText.style.color = '#10b981';
        }

        psiScoreText.innerText = data.psiScore.toFixed(3);
        psiScoreText.style.color = data.psiScore >= 0.25 ? '#ef4444' : (data.psiScore >= 0.10 ? '#f59e0b' : '#fff');
        latencyScoreText.innerText = data.avgLatency;

        explanationText.innerHTML = `<strong>Operational Analysis:</strong> ${data.explanation}<br/><br/>${data.performanceReport}`;

        // 2. Embed the Vega-Lite interactive line chart
        if (window.vegaEmbed && data.accuracyVegaSpec) {
            // Apply customized dark theme color properties to chart borders
            const spec = data.accuracyVegaSpec;
            spec.width = document.getElementById('chart-canvas').clientWidth - 40;
            vegaEmbed('#chart-canvas', spec, { actions: false }).catch(err => {
                console.error("Vega plotting failed: ", err);
            });
        }

        // 3. Animate Multi-Agent Dialogue with deliberate slight pacing delays
        let bubbleIndex = 0;
        function renderNextBubble() {
            if (bubbleIndex < data.agentDialogue.length) {
                const item = data.agentDialogue[bubbleIndex];
                const bubble = document.createElement('div');
                bubble.className = 'chat-bubble';
                
                let avatar = '👤';
                if (item.agent.includes('Monitor')) avatar = '💓';
                else if (item.agent.includes('Auditor')) avatar = '🔍';
                else if (item.agent.includes('Coord')) avatar = '⚡';

                bubble.innerHTML = `
                    <div class="agent-avatar">${avatar}</div>
                    <div class="chat-text">
                        <h6>${item.agent}</h6>
                        <p>${item.message}</p>
                        <span class="action-badge">⚙️ ${item.action}</span>
                    </div>
                `;
                chatFeed.appendChild(bubble);
                chatFeed.scrollTop = chatFeed.scrollHeight;
                
                bubbleIndex++;
                setTimeout(renderNextBubble, 700);
            } else {
                btn.disabled = false;
                btn.innerHTML = 'Audit Prediction Drift';
            }
        }
        renderNextBubble();

    } catch(err) {
        btn.disabled = false;
        btn.innerHTML = 'Audit Prediction Drift';
        console.error(err);
    }
});

// Trigger a mock active automated approval retraining pipeline
document.getElementById('retrain-btn').addEventListener('click', async () => {
    const retrainBtn = document.getElementById('retrain-btn');
    retrainBtn.disabled = true;
    retrainBtn.innerHTML = '⚡ Deploying Active Retraining DAG...';

    try {
        // Dispatch mock retraining task details
        setTimeout(() => {
            retrainBtn.innerHTML = '✅ Retraining Dispatched (SLA Pending)';
            alert('🚀 Auto-Retraining Triggered! A stateful retraining pipeline has been initiated. Active approvals workflow was created under Candidate SLA #9921.');
        }, 1000);
    } catch(err) {
        retrainBtn.disabled = false;
        retrainBtn.innerHTML = 'Launch Retraining Approval Pipeline';
        console.error(err);
    }
});