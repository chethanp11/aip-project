
            async function loadAlerts() {
                const feed = document.getElementById('alerts-feed');
                feed.innerHTML = '<div class="loader">🔍 Auditing metrics and performance ratios...</div>';
                try {
                    const res = await fetch(`${API_BASE}/workflows/reporting/proactive-insights`);
                    const data = await res.json();
                    feed.innerHTML = '';
                    
                    if (data.alerts.length === 0) {
                        feed.innerHTML = '<p class="success-msg">✅ Ledger states optimal. No breaches flagged.</p>';
                        return;
                    }
                    
                    feed.innerHTML = data.alerts.map(a => `
                        <div class="alert-card ${a.severity.toLowerCase()}">
                            <strong>[${a.severity}] ${a.metric}</strong>
                            <p>${a.message}</p>
                            <span class="recom">Recommendation: ${a.recommendation}</span>
                        </div>
                    `).join('');
                } catch(err) {
                    feed.innerHTML = `<p class="error">Load failed: ${err.message}</p>`;
                }
            }
            document.getElementById('refresh-alerts').addEventListener('click', loadAlerts);
            loadAlerts();
        