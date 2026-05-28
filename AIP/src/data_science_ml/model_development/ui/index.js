
            document.getElementById('dev-btn').addEventListener('click', async () => {
                const resBox = document.getElementById('dev-results');
                try {
                    const res = await fetch(`${API_BASE}/workflows/ds/experiments`);
                    const data = await res.json();
                    
                    resBox.innerHTML = `
                        <h4>Outcome scoring Models Grid</h4>
                        ${data.map(e => `
                            <div style="border-bottom:1px solid #eee; padding:6px 0;">
                                <strong>Model: ${e.modelName}</strong> (Run: ${e.championRun})<br/>
                                Metric AUC: <strong>${e.accuracyAUC}</strong> | Depth: ${e.hyperparameters.maxDepth}
                            </div>
                        `).join('')}
                    `;
                    resBox.classList.remove('hide');
                } catch(err) {
                    resBox.innerHTML = `<p class="error">Experiment fetch failed: ${err.message}</p>`;
                }
            });
        