
            document.getElementById('rca-btn').addEventListener('click', async () => {
                const btn = document.getElementById('rca-btn');
                const resBox = document.getElementById('rca-results');
                const m = document.getElementById('rca-metric').value;
                
                try {
                    const res = await fetch(`${API_BASE}/workflows/analytics/rca`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            datasetName: m,
                            metricsData: [
                                { segment: 'North Plaza Treasury', value: 45.2 },
                                { segment: 'South Bay Escrows', value: 12.5 }
                            ]
                        })
                    });
                    const data = await res.json();
                    
                    document.getElementById('rca-summary').innerText = data.profiling.summary;
                    document.getElementById('rca-drivers').innerHTML = data.drivers.map(d => `
                        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                            <span>${d.segment}</span>
                            <strong>${d.value}% Contribution</strong>
                        </div>
                    `).join('');
                    resBox.classList.remove('hide');
                } catch(err) {
                    alert("RCA failed: " + err.message);
                }
            });
        