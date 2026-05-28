
            const seedReports = [
                { name: 'Margin Breakdown Q1', query: 'SELECT (revenue - cost) / active_base FROM regional_ledger', usage: 120, owner: 'Planning' },
                { name: 'Yield Spread Review', query: 'SELECT (revenue-cost)/active_base FROM regional_ledger', usage: 8, owner: 'Leadership Review' },
                { name: 'Regional Balance Ledger', query: 'SELECT allocated_value / baseline_value FROM operating_balances', usage: 84, owner: 'Operations' }
            ];

            document.getElementById('prism-btn').addEventListener('click', async () => {
                const btn = document.getElementById('prism-btn');
                const resBox = document.getElementById('prism-results');
                const ul = document.getElementById('prism-recom');
                
                btn.disabled = true;
                btn.innerText = "Analyzing Report SQL Queries...";
                
                try {
                    const res = await fetch(`${API_BASE}/workflows/reporting/prism-lite`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ reports: seedReports })
                    });
                    const data = await res.json();
                    
                    ul.innerHTML = data.recommendations.map(r => `<li>👉 ${r}</li>`).join('');
                    resBox.classList.remove('hide');
                } catch(err) {
                    alert("Rationalization failed: " + err.message);
                } finally {
                    btn.disabled = false;
                    btn.innerText = "Catalog Rationalized";
                }
            });
        