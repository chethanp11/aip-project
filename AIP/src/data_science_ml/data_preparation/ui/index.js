
document.getElementById('prep-btn').addEventListener('click', async () => {
    const btn = document.getElementById('prep-btn');
    const container = document.getElementById('results-container');
    const chatFeed = document.getElementById('chat-feed');
    const statsContainer = document.getElementById('stats-container');
    const rawTable = document.getElementById('raw-table');
    const cleanedTable = document.getElementById('cleaned-table');

    btn.disabled = true;
    btn.innerHTML = '🧬 Analyzing Ledgers...';
    container.classList.add('hide');
    chatFeed.innerHTML = '';
    statsContainer.innerHTML = '';
    rawTable.innerHTML = '';
    cleanedTable.innerHTML = '';

    try {
        const res = await fetch(`${API_BASE}/workflows/ds/prep`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                columns: ['risk_score', 'balance', 'interest_rate', 'credit_rating', 'industry'],
                dataset: []
            })
        });
        
        if (!res.ok) {
            throw new Error(`Server returned code ${res.status}`);
        }
        
        const data = await res.json();
        container.classList.remove('hide');

        // 1. Animate Multi-Agent Dialogue with deliberate slight pacing delays
        let bubbleIndex = 0;
        function renderNextBubble() {
            if (bubbleIndex < data.agentDialogue.length) {
                const item = data.agentDialogue[bubbleIndex];
                const bubble = document.createElement('div');
                bubble.className = 'chat-bubble';
                
                let avatar = '👤';
                if (item.agent.includes('Profiler')) avatar = '📊';
                else if (item.agent.includes('Engineer')) avatar = '🛠️';
                else if (item.agent.includes('KMS')) avatar = '📚';

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
                setTimeout(renderNextBubble, 700); // 700ms staggered breathing delays
            } else {
                // Done rendering conversation, load stats cards and data grids
                btn.disabled = false;
                btn.innerHTML = 'Profile Features Dataset';
            }
        }
        renderNextBubble();

        // 2. Render Column Summary Cards
        data.columns.forEach(col => {
            const card = document.createElement('div');
            card.className = 'stat-card';
            
            let dataTypeBadge = `<span style="background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 2px 6px; border-radius: 4px; font-size: 10px;">${col.dataType}</span>`;
            let nullBadge = col.nullCount > 0 
                ? `<span style="background: rgba(239,68,68,0.2); color: #fca5a5; padding: 2px 6px; border-radius: 4px; font-size: 10px;">${col.nullCount} nulls</span>`
                : `<span style="background: rgba(16,185,129,0.2); color: #a7f3d0; padding: 2px 6px; border-radius: 4px; font-size: 10px;">Clean</span>`;

            card.innerHTML = `
                <div class="stat-card-header">
                    <h4>${col.name}</h4>
                    <div style="display:flex; gap: 4px;">${dataTypeBadge} ${nullBadge}</div>
                </div>
                <div style="font-size:11px; color:#cbd5e1; margin-top:8px; line-height:1.4;">
                    <strong>Imputation:</strong> ${col.recommendations[0] || 'MinMax continuous scaling'}
                </div>
            `;
            statsContainer.appendChild(card);
        });

        // 3. Render raw vs cleaned tables
        const featureCols = data.featuresGrounded;
        
        // Headers
        const rawHeaderTr = document.createElement('tr');
        const cleanHeaderTr = document.createElement('tr');
        rawHeaderTr.innerHTML = '<th>Client ID</th>' + featureCols.map(c => `<th>${c}</th>`).join('');
        cleanHeaderTr.innerHTML = '<th>Client ID</th>' + featureCols.map(c => `<th>${c}</th>`).join('');
        rawTable.appendChild(rawHeaderTr);
        cleanedTable.appendChild(cleanHeaderTr);

        // Raw Rows
        data.rawDatasetSample.forEach((row, idx) => {
            const tr = document.createElement('tr');
            const clientId = `C-${101 + idx}`;
            let cells = `<td><code>${clientId}</code></td>`;
            featureCols.forEach(col => {
                const val = row[col];
                if (val === null || val === undefined || val === '') {
                    cells += `<td><span class="null-cell">NULL</span></td>`;
                } else if (typeof val === 'number') {
                    cells += `<td>${val >= 1000000 ? (val/1000000).toFixed(1) + 'M' : val.toFixed(2)}</td>`;
                } else {
                    cells += `<td>${val}</td>`;
                }
            });
            tr.innerHTML = cells;
            rawTable.appendChild(tr);
        });

        // Cleaned Rows
        data.cleanedDatasetSample.forEach((row, idx) => {
            const tr = document.createElement('tr');
            const clientId = `C-${101 + idx}`;
            let cells = `<td><code>${clientId}</code></td>`;
            featureCols.forEach(col => {
                const cleanVal = row[col];
                const rawVal = data.rawDatasetSample[idx][col];
                
                let cellContent = '';
                if (rawVal === null || rawVal === undefined || rawVal === '') {
                    cellContent = `<span class="imputed-cell">${cleanVal}</span>`;
                } else if (typeof cleanVal === 'number') {
                    cellContent = cleanVal >= 1000000 ? (cleanVal/1000000).toFixed(1) + 'M' : cleanVal.toFixed(2);
                } else {
                    cellContent = cleanVal;
                }
                
                cells += `<td>${cellContent}</td>`;
            });
            tr.innerHTML = cells;
            cleanedTable.appendChild(tr);
        });

    } catch(err) {
        btn.disabled = false;
        btn.innerHTML = 'Profile Features Dataset';
        chatFeed.innerHTML = `<div style="color:#ef4444; font-size:13px; font-weight:600; padding:10px;">❌ Profiling failed: ${err.message}</div>`;
        console.error(err);
    }
});