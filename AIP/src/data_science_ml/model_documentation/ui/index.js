
let activeBookletText = ''; // Stores the raw compiled markdown booklet

document.getElementById('doc-btn').addEventListener('click', async () => {
    const btn = document.getElementById('doc-btn');
    const container = document.getElementById('results-container');
    const chatFeed = document.getElementById('chat-feed');
    const checksGrid = document.getElementById('checks-grid');
    const bookletContent = document.getElementById('booklet-content');

    const modelId = document.getElementById('model-id-input').value.trim() || 'MD-902';
    const runId = document.getElementById('run-id-input').value.trim() || 'run_xgb_credit_003';
    const guidancePrompt = document.getElementById('guidance-input').value.trim();

    btn.disabled = true;
    btn.innerHTML = '📘 Compiling SR 11-7 Booklet...';
    container.classList.add('hide');
    chatFeed.innerHTML = '';
    checksGrid.innerHTML = '';
    bookletContent.innerHTML = '';
    activeBookletText = '';

    try {
        const res = await fetch(`${API_BASE}/workflows/ds/document`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                modelId: modelId,
                framework: 'XGBoost Credit Classifier',
                championRun: runId,
                prompt: guidancePrompt
            })
        });

        if (!res.ok) {
            throw new Error(`Server returned code ${res.status}`);
        }

        const data = await res.json();
        container.classList.remove('hide');
        activeBookletText = data.governanceBooklet;

        // 1. Animate Multi-Agent Dialogue with deliberate slight pacing delays
        let bubbleIndex = 0;
        function renderNextBubble() {
            if (bubbleIndex < data.agentDialogue.length) {
                const item = data.agentDialogue[bubbleIndex];
                const bubble = document.createElement('div');
                bubble.className = 'chat-bubble';
                
                let avatar = '👤';
                if (item.agent.includes('Writer')) avatar = '✍️';
                else if (item.agent.includes('Audit')) avatar = '🔍';
                else if (item.agent.includes('Chief')) avatar = '🛡️';

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
                btn.innerHTML = 'Compile Compliance Booklet';
            }
        }
        renderNextBubble();

        // 2. Render Compliance Checklist Grid
        data.complianceChecks.forEach(check => {
            const card = document.createElement('div');
            card.className = 'check-card';
            
            let isCompliant = check.status.toLowerCase() === 'compliant';
            let checkIcon = isCompliant ? '🟢' : '🟡';
            let statusColor = isCompliant ? '#10b981' : '#f59e0b';

            card.innerHTML = `
                <div class="check-icon">${checkIcon}</div>
                <div class="check-info">
                    <h5 style="color: ${statusColor};">${check.checkName}</h5>
                    <p style="font-size: 10px; color:#cbd5e1; font-weight:600; margin-bottom: 2px;">Assigned: ${check.agent}</p>
                    <p>${check.details}</p>
                </div>
            `;
            checksGrid.appendChild(card);
        });

        // 3. Render compiled Markdown booklet (high-fidelity custom parsing)
        bookletContent.innerHTML = parseMarkdownToHtml(data.governanceBooklet);

    } catch(err) {
        btn.disabled = false;
        btn.innerHTML = 'Compile Compliance Booklet';
        chatFeed.innerHTML = `<div style="color:#ef4444; font-size:13px; font-weight:600; padding:10px;">❌ Compliance compilation failed: ${err.message}</div>`;
        console.error(err);
    }
});

// Direct file download trigger for compiled booklet markdown
document.getElementById('download-btn').addEventListener('click', () => {
    if (!activeBookletText) return;
    
    const blob = new Blob([activeBookletText], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `model_governance_briefing_${new Date().toISOString().slice(0,10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

// Simple regex-based high-fidelity Markdown parser for local rendering
function parseMarkdownToHtml(md) {
    if (!md) return '';
    let html = md;
    
    // Replace Headers
    html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
    html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    
    // Replace bold text
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Replace bullet lists
    html = html.replace(/^\* (.*?)$/gm, '<li>$1</li>');
    html = html.replace(/<li>(.*?)<\/li>/g, function(match) {
        return `<ul>${match}</ul>`;
    });
    // Consolidate adjacent <ul> blocks
    html = html.replace(/<\/ul>\s*<ul>/g, '');
    
    // Replace single line breaks outside blocks with paragraphs
    html = html.replace(/^(?!<[a-z]+>)(.*?)$/gm, '<p>$1</p>');
    // Clean empty paragraphs
    html = html.replace(/<p><\/p>/g, '');
    
    return html;
}