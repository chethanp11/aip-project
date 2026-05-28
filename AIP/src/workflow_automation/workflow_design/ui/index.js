
            document.getElementById('wf-btn').addEventListener('click', async () => {
                const resBox = document.getElementById('wf-results');
                try {
                    const res = await fetch(`${API_BASE}/workflows/automation/run`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            config: {
                                name: document.getElementById('wf-name').value,
                                trigger: document.getElementById('wf-trigger').value,
                                task: 'profile',
                                notification: 'Slack Admin Alert',
                                requireApproval: true
                            }
                        })
                    });
                    const data = await res.json();
                    
                    resBox.innerHTML = `<h4>DAG Validation Fired</h4><p>Status: ${data.paused ? 'Paused for Approval Guard' : 'Completed'}</p>`;
                    resBox.classList.remove('hide');
                } catch(err) {
                    resBox.innerHTML = `<p class="error">Errors: ${err.message}</p>`;
                    resBox.classList.remove('hide');
                }
            });
        