
            document.getElementById('prep-btn').addEventListener('click', async () => {
                const resBox = document.getElementById('prep-results');
                resBox.innerHTML = '<div class="loader">🧹 Imputing default risk attributes...</div>';
                resBox.classList.remove('hide');
                
                try {
                    const res = await fetch(`${API_BASE}/workflows/ds/prep`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            columns: ['balance', 'risk_score', 'interest_rate'],
                            dataset: [{ balance: 120000.0, risk_score: null }]
                        })
                    });
                    const data = await res.json();
                    resBox.innerHTML = `
                        <h4>Feature Pipeline Output</h4>
                        <p>Total Null Cells Resolved: <strong>${data.imputedCellsCount}</strong></p>
                        <p>Columns Cleaned: <strong>${data.featuresGrounded.join(', ')}</strong></p>
                    `;
                } catch(err) {
                    resBox.innerHTML = `<p class="error">Data prep failed: ${err.message}</p>`;
                }
            });
        