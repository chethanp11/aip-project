
            const earning = document.getElementById('sim-earning');
            const dep = document.getElementById('sim-dep');
            const assets = document.getElementById('sim-assets');
            const npl = document.getElementById('sim-npl');

            async function runSim() {
                document.getElementById('lbl-earning').innerText = earning.value;
                document.getElementById('lbl-dep').innerText = dep.value;
                document.getElementById('lbl-assets').innerText = assets.value;
                document.getElementById('lbl-npl').innerText = npl.value;
                
                try {
                    const res = await fetch(`${API_BASE}/workflows/analytics/what-if`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            earningRate: earning.value,
                            resourceCostRate: dep.value,
                            assets: assets.value,
                            nplRate: npl.value
                        })
                    });
                    const data = await res.json();
                    document.getElementById('res-nim').innerText = `${data.netInterestMargin.toFixed(2)}%`;
                    document.getElementById('res-profit').innerText = `$${Math.round(data.netSpreadProfit).toLocaleString()}`;
                } catch(err) {
                    console.error(err);
                }
            }
            [earning, dep, assets, npl].forEach(el => el.addEventListener('input', runSim));
            runSim();
        