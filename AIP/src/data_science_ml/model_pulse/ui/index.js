
            document.getElementById('pulse-btn').addEventListener('click', async () => {
                const resBox = document.getElementById('pulse-results');
                try {
                    const res = await fetch(`${API_BASE}/workflows/ds/model-pulse`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ accuracyMetrics: [0.94, 0.93, 0.92, 0.88, 0.82] })
                    });
                    const data = await res.json();
                    
                    resBox.innerHTML = `
                        <h4>Covariance Audit Outcomes</h4>
                        <p>Status: <strong style="color: ${data.driftDetected ? 'red' : 'green'}">${data.status}</strong></p>
                        <p>Z-Score Drift metric: <strong>${data.driftScore.toFixed(3)}</strong></p>
                    `;
                    resBox.classList.remove('hide');
                } catch(err) {
                    resBox.innerHTML = `<p class="error">Pulse failed: ${err.message}</p>`;
                }
            });
        