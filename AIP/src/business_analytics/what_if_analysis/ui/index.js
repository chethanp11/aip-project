const earning = document.getElementById('sim-earning');
const dep = document.getElementById('sim-dep');
const assets = document.getElementById('sim-assets');
const npl = document.getElementById('sim-npl');

const lblEarning = document.getElementById('lbl-earning');
const lblDep = document.getElementById('lbl-dep');
const lblAssets = document.getElementById('lbl-assets');
const lblNpl = document.getElementById('lbl-npl');

const resNim = document.getElementById('res-nim');
const resRev = document.getElementById('res-rev');
const resExp = document.getElementById('res-exp');
const resDef = document.getElementById('res-def');
const resProfit = document.getElementById('res-profit');
const yieldBar = document.getElementById('yield-bar');
const nimLabel = document.getElementById('res-nim-label');

// format raw currency
function formatCurrency(dollars) {
    if (Math.abs(dollars) >= 1000000000) {
        return `$${(dollars / 1000000000).toFixed(2)}B`;
    }
    return `$${Math.round(dollars).toLocaleString()}`;
}

// Perform Scenario Calculation
async function runSim() {
    lblEarning.innerText = earning.value;
    lblDep.innerText = dep.value;
    lblAssets.innerText = assets.value;
    lblNpl.innerText = npl.value;
    
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
        
        if (!res.ok) {
            throw new Error(`HTTP Error Status: ${res.status}`);
        }
        
        const data = await res.json();
        
        resNim.innerText = `${data.netInterestMargin.toFixed(2)}%`;
        resRev.innerText = formatCurrency(data.projectedInterestRevenue);
        resExp.innerText = formatCurrency(data.projectedInterestExpense);
        resDef.innerText = formatCurrency(data.projectedDefaultCosts);
        resProfit.innerText = formatCurrency(data.netSpreadProfit);
        
        // Yield bar calculations: NIM maxed scale of 6%
        const pct = Math.max(Math.min((data.netInterestMargin / 6.0) * 100, 100), 0);
        yieldBar.style.width = `${pct}%`;
        
        if (data.netInterestMargin < 1.0) {
            nimLabel.innerText = '⚠️ CRITICAL SPREAD RISK';
            nimLabel.style.color = 'var(--danger-color)';
            yieldBar.style.background = 'var(--danger-color)';
        } else if (data.netInterestMargin < 2.5) {
            nimLabel.innerText = '🟡 MODERATE COMPRESSION';
            nimLabel.style.color = 'var(--warning-color)';
            yieldBar.style.background = 'var(--warning-color)';
        } else {
            nimLabel.innerText = '🟢 OPTIMAL MARGIN YIELD';
            nimLabel.style.color = 'var(--success-color)';
            yieldBar.style.background = 'var(--success-color)';
        }
        
    } catch(err) {
        console.error("Simulation failed:", err);
    }
}

// Preset configurations
function loadPreset(earningVal, depVal, assetsVal, nplVal) {
    earning.value = earningVal;
    dep.value = depVal;
    assets.value = assetsVal;
    npl.value = nplVal;
    runSim();
}

document.getElementById('preset-inflation').addEventListener('click', () => {
    loadPreset(9.5, 4.5, 180, 1.2);
});

document.getElementById('preset-recession').addEventListener('click', () => {
    loadPreset(5.2, 3.5, 120, 5.8);
});

document.getElementById('preset-growth').addEventListener('click', () => {
    loadPreset(8.2, 1.2, 220, 0.8);
});

document.getElementById('preset-baseline').addEventListener('click', () => {
    loadPreset(6.5, 2.2, 150, 2.5);
});

// Event bindings
[earning, dep, assets, npl].forEach(el => el.addEventListener('input', runSim));

// Initial baseline simulation run
runSim();