function renderNarrative(text) {
    const escaped = String(text || 'No narrative returned.')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/^### (.*)$/gm, '<h4>$1</h4>')
        .replace(/^## (.*)$/gm, '<h3>$1</h3>')
        .replace(/^- (.*)$/gm, '<li>$1</li>')
        .replace(/\n/g, '<br/>');

    return escaped.replace(/(<li>.*?<\/li>)(<br\/>)?/gs, '<ul>$1</ul>');
}

function appendBotResponse(box, data) {
    const bMsg = document.createElement('div');
    bMsg.className = 'message bot visual-response';

    const visualHtml = data.visualHtml || `
        <div class="convbi-visual-card">
            <div class="convbi-visual-header">
                <div>
                    <span class="convbi-kicker">Visual BI Answer</span>
                    <h3>Conversation Snapshot</h3>
                    <p>No visualization payload was returned for this response.</p>
                </div>
            </div>
        </div>`;

    bMsg.innerHTML = `
        ${visualHtml}
        <div class="convbi-narrative">
            ${renderNarrative(data.narrative)}
        </div>
    `;
    box.appendChild(bMsg);
}

document.getElementById('chat-send').addEventListener('click', async () => {
    const inp = document.getElementById('chat-in');
    const box = document.getElementById('chat-box');
    const text = inp.value.trim();
    if (!text) return;

    const uMsg = document.createElement('div');
    uMsg.className = 'message user';
    uMsg.innerText = text;
    box.appendChild(uMsg);
    inp.value = '';

    const lMsg = document.createElement('div');
    lMsg.className = 'message bot loader';
    lMsg.innerText = 'Resolving query using AIP-Infra LMS and KMS...';
    box.appendChild(lMsg);
    box.scrollTop = box.scrollHeight;

    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/conversational-bi`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text })
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || data.error || `Request failed with status ${res.status}`);
        }
        lMsg.remove();
        appendBotResponse(box, data);
    } catch(err) {
        lMsg.innerText = `Error: ${err.message}`;
        lMsg.className = 'message bot error';
    }
    box.scrollTop = box.scrollHeight;
});

document.getElementById('chat-in').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        document.getElementById('chat-send').click();
    }
});
