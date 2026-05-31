
            document.getElementById('kms-btn').addEventListener('click', async () => {
                const q = document.getElementById('kms-q').value.trim();
                const resBox = document.getElementById('kms-results');
                if (!q) return;
                
                resBox.innerHTML = '<div class="loader">🔍 Grounding search in KMS glossary...</div>';
                resBox.classList.remove('hide');
                
                try {
                    const res = await fetch(`${API_BASE}/knowledge/search?q=${encodeURIComponent(q)}`);
                    const data = await res.json();
                    resBox.innerHTML = '';
                    
                    if (!data.context) {
                        resBox.innerHTML = '<p class="warn">No matching metrics or articles found.</p>';
                        return;
                    }
                    
                    const div = document.createElement('div');
                    div.className = 'kms-item';
                    div.innerHTML = `<h4>Matched KMS Seed</h4><p>${data.context.replace(/\n/g, '<br/>')}</p>`;
                    resBox.appendChild(div);
                } catch(err) {
                    resBox.innerHTML = `<p class="error">Query failed: ${err.message}</p>`;
                }
            });
        