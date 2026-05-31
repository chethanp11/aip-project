// Event Bindings
const chatSend = document.getElementById('chat-send');
const chatIn = document.getElementById('chat-in');
const chatBox = document.getElementById('chat-box');
const sessionList = document.getElementById('session-list');
const newChatBtn = document.getElementById('new-chat-btn');

let currentSessionId = null;

function formatTimestamp(isoStr) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr);
        const now = new Date();
        const diffMs = now - d;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return '';
    }
}

async function loadSessions() {
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/conversational-bi/sessions`);
        if (!res.ok) throw new Error("Failed to load sessions");
        const sessions = await res.json();
        
        sessionList.innerHTML = '';
        
        if (sessions.length === 0) {
            const empty = document.createElement('div');
            empty.style.fontSize = '12px';
            empty.style.color = 'var(--text-secondary)';
            empty.style.fontStyle = 'italic';
            empty.style.padding = '8px';
            empty.innerText = 'No recent chats.';
            sessionList.appendChild(empty);
            return;
        }
        
        sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'session-item';
            if (session.sessionId === currentSessionId) {
                item.classList.add('active');
            }
            
            const title = document.createElement('div');
            title.className = 'session-item-title';
            title.innerText = session.title || 'BI Discussion';
            
            const time = document.createElement('div');
            time.className = 'session-item-time';
            time.innerText = formatTimestamp(session.timestamp);
            
            item.appendChild(title);
            item.appendChild(time);
            
            item.addEventListener('click', () => {
                loadSessionHistory(session.sessionId);
            });
            
            sessionList.appendChild(item);
        });
    } catch (err) {
        console.error("Error loading chat sessions:", err);
    }
}

async function loadSessionHistory(sessionId) {
    currentSessionId = sessionId;
    
    // Clear chat and show loading indicator
    chatBox.innerHTML = '<div class="message bot loader">Recovering discussion logs from storage...</div>';
    
    // Update active highlight state locally
    const items = sessionList.querySelectorAll('.session-item');
    items.forEach(el => el.classList.remove('active'));
    
    try {
        const res = await fetch(`${API_BASE}/workflows/reporting/conversational-bi/sessions/${sessionId}`);
        if (!res.ok) throw new Error("Failed to fetch session history");
        const session = await res.json();
        
        chatBox.innerHTML = '';
        
        if (session.messages && session.messages.length > 0) {
            session.messages.forEach(msg => {
                const bubble = document.createElement('div');
                if (msg.role === 'user') {
                    bubble.className = 'message user';
                    bubble.innerText = msg.content;
                } else {
                    bubble.className = 'message bot';
                    bubble.innerHTML = msg.renderedHtml || msg.content.replace(/\n/g, '<br/>');
                }
                chatBox.appendChild(bubble);
            });
        } else {
            chatBox.innerHTML = '<div class="message bot">This conversation has no recorded messages.</div>';
        }
        
        // Re-highlight list
        loadSessions();
    } catch (err) {
        chatBox.innerHTML = `<div class="message bot error">Failed to load conversation logs: ${err.message}</div>`;
    }
    chatBox.scrollTop = chatBox.scrollHeight;
}

function startNewChat() {
    currentSessionId = null;
    chatBox.innerHTML = '<div class="message bot">Hello! I am your Conversational BI Agent. Ask me anything grounded in our primary operational database.</div>';
    
    const items = sessionList.querySelectorAll('.session-item');
    items.forEach(el => el.classList.remove('active'));
    
    chatBox.scrollTop = chatBox.scrollHeight;
}

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
            body: JSON.stringify({ question: text, sessionId: currentSessionId })
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
        
        // Keep track of active session and reload list
        if (data.sessionId) {
            currentSessionId = data.sessionId;
            await loadSessions();
        }
        
    } catch(err) {
        lMsg.innerText = `Error: ${err.message}`;
        lMsg.className = 'message bot error';
    }
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Event Listeners
chatSend.addEventListener('click', handleSendMessage);
chatIn.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        handleSendMessage();
    }
});
newChatBtn.addEventListener('click', startNewChat);

// Initialize on page load
(async () => {
    // Wait slightly to let any authed token exchange complete
    await new Promise(r => setTimeout(r, 100));
    await loadSessions();
    
    // Check if new chat is forced via localStorage
    if (localStorage.getItem('AIP_FORCE_NEW_CHAT') === 'true') {
        localStorage.removeItem('AIP_FORCE_NEW_CHAT');
        startNewChat();
        
        // Handle prefill if any
        const prefill = localStorage.getItem('AIP_NEW_CHAT_PREFILL');
        if (prefill) {
            localStorage.removeItem('AIP_NEW_CHAT_PREFILL');
            chatIn.value = prefill;
            chatIn.focus();
        }
    } else {
        // Auto-select most recent session if available
        const firstItem = sessionList.querySelector('.session-item');
        if (firstItem) {
            firstItem.click();
        }
    }
})();