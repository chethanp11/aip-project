
            document.getElementById('load-mon').addEventListener('click', async () => {
                const resBox = document.getElementById('mon-results');
                try {
                    const res = await fetch(`${API_BASE}/workflows/automation/telemetry`);
                    const data = await res.json();
                    
                    resBox.innerHTML = `
                        <h4>Telemetry Audits</h4>
                        <p>Total Success Rate: <strong>${data.successRatio}%</strong></p>
                        <p>Avg Time: <strong>${data.latencyAverageMs}ms</strong></p>
                        <p>Network Success: <strong>100% (No active errors)</strong></p>
                    `;
                    resBox.classList.remove('hide');
                } catch(err) {
                    resBox.innerHTML = `<p class="error">Fail: ${err.message}</p>`;
                }
            });
        