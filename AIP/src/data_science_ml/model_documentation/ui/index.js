
            document.getElementById('doc-btn').addEventListener('click', async () => {
                const resBox = document.getElementById('doc-results');
                resBox.innerHTML = '<div class="loader">📘 Rending validation layouts...</div>';
                resBox.classList.remove('hide');
                
                try {
                    const res = await fetch(`${API_BASE}/workflows/ds/document`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            modelId: 'MD-902',
                            framework: 'XGBoost Outcomes Classifier',
                            championRun: 'run_9x_auc'
                        })
                    });
                    const data = await res.json();
                    resBox.innerHTML = `
                        <h4 class="success">Audits Compliant</h4>
                        <p>${data.documentationSummary}</p>
                    `;
                } catch(err) {
                    resBox.innerHTML = `<p class="error">Governance compiler failure: ${err.message}</p>`;
                }
            });
        