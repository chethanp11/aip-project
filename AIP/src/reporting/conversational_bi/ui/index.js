
            document.getElementById('chat-send').addEventListener('click', async () => {
                const inp = document.getElementById('chat-in');
                const box = document.getElementById('chat-box');
                const text = inp.value.trim();
                if (!text) return;
                
                // Add user message
                const uMsg = document.createElement('div');
                uMsg.className = 'message user';
                uMsg.innerText = text;
                box.appendChild(uMsg);
                inp.value = '';
                
                // Add loader message
                const lMsg = document.createElement('div');
                lMsg.className = 'message bot loader';
                lMsg.innerText = "Resolving query using AIP-Infra LMS and KMS...";
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
                    
                    const bMsg = document.createElement('div');
                    bMsg.className = 'message bot';
                    bMsg.innerHTML = (data.narrative || 'No narrative returned.').replace(/\n/g, '<br/>');
                    box.appendChild(bMsg);
                } catch(err) {
                    lMsg.innerText = `Error: ${err.message}`;
                    lMsg.className = 'message bot error';
                }
                box.scrollTop = box.scrollHeight;
            });
        
