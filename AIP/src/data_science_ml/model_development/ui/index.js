
document.getElementById('dev-btn').addEventListener('click', async () => {
    const btn = document.getElementById('dev-btn');
    const container = document.getElementById('results-container');
    const chatFeed = document.getElementById('chat-feed');
    const tbody = document.getElementById('experiments-body');

    // Get input parameters to mock specific updates
    const customLr = parseFloat(document.getElementById('lr-slider').value);
    const customDepth = parseInt(document.getElementById('depth-slider').value);
    const customEst = parseInt(document.getElementById('est-slider').value);

    btn.disabled = true;
    btn.innerHTML = '🧪 Running Grid Trials...';
    container.classList.add('hide');
    chatFeed.innerHTML = '';
    tbody.innerHTML = '';

    try {
        const res = await fetch(`${API_BASE}/workflows/ds/experiments`);
        if (!res.ok) {
            throw new Error(`Server returned code ${res.status}`);
        }
        
        const data = await res.json();
        container.classList.remove('hide');

        // Dynamically adjust the champion run hyperparameters to match the user's sliders
        const experimentsList = data.experiments.map(exp => {
            if (exp.runId === data.championRun) {
                return {
                    ...exp,
                    hyperparameters: {
                        learningRate: customLr,
                        maxDepth: customDepth,
                        estimators: customEst,
                        batchSize: 32
                    }
                };
            }
            return exp;
        });

        // 1. Animate Multi-Agent Dialogue with deliberate slight pacing delays
        let bubbleIndex = 0;
        function renderNextBubble() {
            if (bubbleIndex < data.agentDialogue.length) {
                const item = data.agentDialogue[bubbleIndex];
                const bubble = document.createElement('div');
                bubble.className = 'chat-bubble';
                
                let avatar = '👤';
                if (item.agent.includes('Optimizer')) avatar = '⚙️';
                else if (item.agent.includes('Evaluator')) avatar = '📊';
                else if (item.agent.includes('Risk')) avatar = '🛡️';

                bubble.innerHTML = `
                    <div class="agent-avatar">${avatar}</div>
                    <div class="chat-text">
                        <h6>${item.agent}</h6>
                        <p>${item.message.replace('0.001', customLr).replace('300', customEst).replace('10', customDepth)}</p>
                        <span class="action-badge">⚡ ${item.action}</span>
                    </div>
                `;
                chatFeed.appendChild(bubble);
                chatFeed.scrollTop = chatFeed.scrollHeight;
                
                bubbleIndex++;
                setTimeout(renderNextBubble, 700);
            } else {
                btn.disabled = false;
                btn.innerHTML = 'List Experimental Training Grid';
            }
        }
        renderNextBubble();

        // 2. Render Experiments Table Rows
        experimentsList.forEach(e => {
            const tr = document.createElement('tr');
            const isChamp = e.runId === data.championRun;
            if (isChamp) {
                tr.className = 'champion-row';
            }
            
            // Format Hyperparameters
            let hyperparamsStr = '';
            if (e.hyperparameters.maxDepth > 0) {
                hyperparamsStr = `depth: <strong>${e.hyperparameters.maxDepth}</strong>, LR: <strong>${e.hyperparameters.learningRate}</strong>, est: <strong>${e.hyperparameters.estimators}</strong>`;
            } else {
                hyperparamsStr = `batchSize: <strong>${e.hyperparameters.batchSize}</strong>`;
            }

            let statusBadge = isChamp 
                ? `<span class="champion-badge">🏆 Champion</span>` 
                : `<span class="challenger-badge">Challenger</span>`;

            tr.innerHTML = `
                <td><code>${e.runId}</code></td>
                <td><strong>${e.modelName}</strong></td>
                <td>${hyperparamsStr}</td>
                <td><strong>${(e.accuracy * 100).toFixed(0)}%</strong></td>
                <td style="color:#60a5fa; font-weight:600;">${e.rocArea.toFixed(2)}</td>
                <td>${e.f1Score.toFixed(2)}</td>
                <td style="color:#94a3b8;">${e.latency}ms</td>
                <td style="text-align: right;">${statusBadge}</td>
            `;
            tbody.appendChild(tr);
        });

    } catch(err) {
        btn.disabled = false;
        btn.innerHTML = 'List Experimental Training Grid';
        chatFeed.innerHTML = `<div style="color:#ef4444; font-size:13px; font-weight:600; padding:10px;">❌ Tuning sweep failed: ${err.message}</div>`;
        console.error(err);
    }
});