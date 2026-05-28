
            document.getElementById('orch-btn').addEventListener('click', async () => {
                const resBox = document.getElementById('orch-results');
                resBox.innerHTML = '<div class="loader">⚙️ Driving orchestrations flow...</div>';
                resBox.classList.remove('hide');
                
                try {
                    const res = await fetch(`${API_BASE}/workflows/automation/telemetry`);
                    const data = await res.json();
                    
                    resBox.innerHTML = `
                        <h4>Orchestration Live Stats</h4>
                        <p>Total Completed Pipelines: <strong>${data.workflowsCompleted}</strong></p>
                        <p>System Operating Latency: <strong>${data.latencyAverageMs}ms</strong></p>
                        <p>Aggregated Success Ratio: <strong>${data.successRatio}%</strong></p>
                    `;
                } catch(err) {
                    resBox.innerHTML = `<p class="error">Run failed: ${err.message}</p>`;
                }
            });
        