// Event Bindings
const chatSend = document.getElementById('chat-send');
const chatIn = document.getElementById('chat-in');
const chatBox = document.getElementById('chat-box');

async function handleSendMessage() {
    const text = chatIn.value.trim();
    if (!text) return;
    
    // Add user message
    const uMsg = document.createElement('div');
    uMsg.className = 'message user';
    uMsg.innerText = text;
    chatBox.appendChild(uMsg);
    chatIn.value = '';
    
    // Add bot loader
    const lMsg = document.createElement('div');
    lMsg.className = 'message bot loader';
    lMsg.innerText = "Resolving query using Enterprise Ledger & KMS...";
    chatBox.appendChild(lMsg);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/conversational-bi`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text })
        });
        
        if (!res.ok) {
            throw new Error(`HTTP Error Status: ${res.status}`);
        }
        
        const data = await res.json();
        lMsg.remove();
        
        // Add bot message using the pre-rendered HTML narrative generated directly by backend agents
        const bMsg = document.createElement('div');
        bMsg.className = 'message bot';
        bMsg.innerHTML = data.renderedHtml || data.narrative.replace(/\n/g, '<br/>');
        chatBox.appendChild(bMsg);
        
    } catch(err) {
        lMsg.innerText = `Error: ${err.message}`;
        lMsg.className = 'message bot error';
    }
    chatBox.scrollTop = chatBox.scrollHeight;
}

chatSend.addEventListener('click', handleSendMessage);

chatIn.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        handleSendMessage();
    }
});