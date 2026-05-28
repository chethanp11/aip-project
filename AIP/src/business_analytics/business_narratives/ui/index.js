
            document.getElementById('nar-btn').addEventListener('click', async () => {
                const btn = document.getElementById('nar-btn');
                const resBox = document.getElementById('nar-results');
                
                try {
                    const res = await fetch(`${API_BASE}/workflows/analytics/business-narratives`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            channel: 'slack',
                            metricName: document.getElementById('nar-metric').value,
                            value: document.getElementById('nar-val').value,
                            growthRate: '12.4',
                            primaryDriver: document.getElementById('nar-driver').value
                        })
                    });
                    const data = await res.json();
                    document.getElementById('nar-text').innerText = data.narrative;
                    resBox.classList.remove('hide');
                } catch(err) {
                    alert("Narrative failed: " + err.message);
                }
            });
        