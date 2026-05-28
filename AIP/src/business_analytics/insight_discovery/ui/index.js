
            document.getElementById('disc-btn').addEventListener('click', async () => {
                const btn = document.getElementById('disc-btn');
                const grid = document.getElementById('disc-results');
                btn.disabled = true;
                
                try {
                    const res = await fetch(`${API_BASE}/workflows/analytics/insight-discovery`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ segmentsData: [
                            { cohort: 'Global Segment A', timeline: [1.2, 1.3, 1.4, 2.8] },
                            { cohort: 'Retail Cohort B', timeline: [85.0, 89.2, 94.5] }
                        ]})
                    });
                    const data = await res.json();
                    
                    grid.innerHTML = data.insights.map(ins => `
                        <div class="item">
                            <h5>${ins.cohort}</h5>
                            <p class="badge-fill">${ins.direction} (${ins.growthRate}%)</p>
                            <p class="details">${ins.explanation}</p>
                        </div>
                    `).join('');
                    grid.classList.remove('hide');
                } catch(err) {
                    alert("Insight discovery failed: " + err.message);
                } finally {
                    btn.disabled = false;
                }
            });
        