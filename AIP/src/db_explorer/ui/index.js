/**
 * Database Explorer Micro-Frontend Controller
 * Manages schema viewing, visual query filtering, SQL console execution, and interactive grid rendering.
 */

const API_BASE = '/api/v1';
let currentTable = null;
let currentSchema = [];
let queryResultsCache = null;

// Reusable authed fetch wrapper
async function authedFetch(url, options = {}) {
    let token = '';
    try {
        token = localStorage.getItem('AIP_API_KEY') || '';
    } catch (e) {
        console.warn("Storage access blocked inside iframe:", e);
    }
    
    // Fallback: try accessing parent window localStorage directly if same-origin is allowed
    if (!token) {
        try {
            if (window.parent && window.parent.localStorage) {
                token = window.parent.localStorage.getItem('AIP_API_KEY') || '';
            }
        } catch (e) {
            console.warn("Parent storage access blocked:", e);
        }
    }

    options.headers = options.headers || {};
    options.headers['Content-Type'] = options.headers['Content-Type'] || 'application/json';
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    return fetch(url, options);
}

// Guarantee application initialization under all load states
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

// ==========================================
// 🚀 APPLICATION INITIALIZATION
// ==========================================
async function initApp() {
    setupTabSwitching();
    setupEventListeners();
    await checkDatabaseConnection();
    await fetchTablesCatalog();
}

// Check database connection and update header status indicator
async function checkDatabaseConnection() {
    const statusPill = document.getElementById('connection-status');
    try {
        const res = await authedFetch(`${API_BASE}/analytics-data/tables`);
        if (res.ok) {
            statusPill.className = 'status-pill status-online';
            statusPill.innerHTML = '<span class="status-dot"></span> System Connected';
        } else {
            throw new Error(`Server returned code ${res.status}`);
        }
    } catch (err) {
        statusPill.className = 'status-pill status-offline';
        statusPill.innerHTML = '<span class="status-dot"></span> Connection Offline';
        showGridError("Failed to connect to the source database. Please verify the containers are active.");
    }
}

// Fetch tables and populate the sidebar
async function fetchTablesCatalog() {
    const list = document.getElementById('tables-list');
    try {
        const res = await authedFetch(`${API_BASE}/analytics-data/tables`);
        if (!res.ok) throw new Error("Catalog fetch failed");
        const tables = await res.json();
        
        if (tables.length === 0) {
            list.innerHTML = '<li class="loading-item">No tables found.</li>';
            return;
        }

        list.innerHTML = '';
        tables.forEach(table => {
            const li = document.createElement('li');
            li.className = 'table-item';
            li.setAttribute('data-table', table);
            li.innerHTML = `
                <span class="table-item-name">📄 ${table}</span>
                <span class="table-item-badge">Table</span>
            `;
            li.addEventListener('click', () => selectActiveTable(table));
            list.appendChild(li);
        });
    } catch (err) {
        list.innerHTML = '<li class="loading-item" style="color: var(--color-danger)">Failed to load catalog</li>';
    }
}

// ==========================================
// 🗂️ SELECT ACTIVE TABLE & SCHEMA RETRIEVAL
// ==========================================
async function selectActiveTable(tableName) {
    if (currentTable === tableName) return;
    
    currentTable = tableName;
    
    // Toggle active classes in sidebar
    document.querySelectorAll('.table-item').forEach(el => {
        if (el.getAttribute('data-table') === tableName) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });

    // Update main headers
    document.getElementById('active-table-title').innerText = tableName;
    document.getElementById('active-table-desc').innerText = `Construct filter criteria or execute read-only queries against '${tableName}' schema.`;

    // Reset Visual query builder and console
    document.getElementById('filter-rows-container').innerHTML = `
        <p class="filter-empty-text">No active filters. Query will retrieve all records (capped at 100 rows).</p>
    `;
    document.getElementById('sql-query-editor').value = `SELECT * FROM ${tableName} LIMIT 50;`;
    document.getElementById('console-metrics-display').className = 'console-metrics';
    document.getElementById('console-metrics-display').innerText = `Loaded schema for ${tableName}. Ready to execute custom query.`;

    // Fetch Table schema
    const schemaPills = document.getElementById('schema-columns-container');
    schemaPills.innerHTML = '<span class="schema-empty-text">Loading schema...</span>';
    
    try {
        const res = await authedFetch(`${API_BASE}/analytics-data/tables/${tableName}/schema`);
        if (!res.ok) throw new Error("Failed to fetch schema details");
        currentSchema = await res.json();
        
        schemaPills.innerHTML = '';
        currentSchema.forEach(col => {
            const pill = document.createElement('span');
            pill.className = 'schema-pill';
            pill.innerHTML = `
                <span class="col-name">${col.column_name}</span>
                <span class="col-type">${col.data_type}</span>
            `;
            schemaPills.appendChild(pill);
        });

        // Enable buttons
        document.getElementById('btn-add-filter').disabled = false;
        document.getElementById('btn-run-visual-query').disabled = false;
        
        // Auto trigger first query execution to preview table
        await runVisualQuery();

    } catch (err) {
        schemaPills.innerHTML = `<span class="schema-empty-text" style="color: var(--color-danger)">Failed to load schema: ${err.message}</span>`;
        document.getElementById('btn-add-filter').disabled = true;
        document.getElementById('btn-run-visual-query').disabled = true;
    }
}

// ==========================================
// ⚙️ TABS SWITCHING CONTROLLER
// ==========================================
function setupTabSwitching() {
    const btnBuilder = document.getElementById('tab-btn-builder');
    const btnSql = document.getElementById('tab-btn-sql');
    const panelBuilder = document.getElementById('panel-builder');
    const panelSql = document.getElementById('panel-sql');

    btnBuilder.addEventListener('click', () => {
        btnBuilder.classList.add('active');
        btnSql.classList.remove('active');
        panelBuilder.classList.add('active');
        panelSql.classList.remove('active');
    });

    btnSql.addEventListener('click', () => {
        btnSql.classList.add('active');
        btnBuilder.classList.remove('active');
        panelSql.classList.add('active');
        panelBuilder.classList.remove('active');
    });
}

// ==========================================
// 🛠️ FILTER BUILDER CONTROLLER
// ==========================================
function setupEventListeners() {
    const btnAddFilter = document.getElementById('btn-add-filter');
    const btnRunVisual = document.getElementById('btn-run-visual-query');
    const btnRunCustom = document.getElementById('btn-run-custom-query');
    const btnExportJson = document.getElementById('btn-export-json');

    btnAddFilter.addEventListener('click', () => addFilterRow());
    btnRunVisual.addEventListener('click', () => runVisualQuery());
    btnRunCustom.addEventListener('click', () => runCustomQuery());
    btnExportJson.addEventListener('click', () => exportResultsAsJSON());
}

function addFilterRow() {
    if (!currentTable || currentSchema.length === 0) return;

    const container = document.getElementById('filter-rows-container');
    const emptyText = container.querySelector('.filter-empty-text');
    if (emptyText) emptyText.remove();

    const row = document.createElement('div');
    row.className = 'filter-row';
    
    // 1. Column options dropdown
    let colOptions = currentSchema.map(col => `<option value="${col.column_name}">${col.column_name}</option>`).join('');
    
    row.innerHTML = `
        <select class="filter-select filter-col-select">
            ${colOptions}
        </select>
        <select class="filter-select filter-op-select">
            <option value="equals">=</option>
            <option value="contains">contains (LIKE)</option>
            <option value="greater_than">&gt;</option>
            <option value="less_than">&lt;</option>
            <option value="is_null">is null</option>
            <option value="is_not_null">is not null</option>
        </select>
        <input type="text" class="filter-input filter-val-input" placeholder="Type comparison value..." />
        <button class="btn-remove-filter" title="Remove filter row">✕</button>
    `;

    // Add removal listener
    row.querySelector('.btn-remove-filter').addEventListener('click', () => {
        row.remove();
        if (container.children.length === 0) {
            container.innerHTML = `
                <p class="filter-empty-text">No active filters. Query will retrieve all records (capped at 100 rows).</p>
            `;
        }
    });

    // Disable value input dynamically for IS NULL operators
    const opSelect = row.querySelector('.filter-op-select');
    const valInput = row.querySelector('.filter-val-input');
    opSelect.addEventListener('change', () => {
        const v = opSelect.value;
        if (v === 'is_null' || v === 'is_not_null') {
            valInput.disabled = true;
            valInput.style.opacity = '0.3';
            valInput.value = '';
        } else {
            valInput.disabled = false;
            valInput.style.opacity = '1';
        }
    });

    container.appendChild(row);
}

// ==========================================
// 🚀 QUERY EXECUTION ENGINE
// ==========================================
async function runVisualQuery() {
    if (!currentTable) return;
    
    showGridLoading();
    
    // Compile filters
    const filterRows = document.querySelectorAll('.filter-row');
    const filters = [];
    
    filterRows.forEach(row => {
        const column = row.querySelector('.filter-col-select').value;
        const operator = row.querySelector('.filter-op-select').value;
        const value = row.querySelector('.filter-val-input').value;
        
        filters.push({ column, operator, value });
    });

    const limit = parseInt(document.getElementById('query-limit').value) || 100;

    try {
        const res = await authedFetch(`${API_BASE}/analytics-data/query`, {
            method: 'POST',
            body: JSON.stringify({
                mode: 'visual',
                tableName: currentTable,
                filters,
                limit
            })
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Filtered query failed");
        }

        const data = await res.json();
        renderGridResults(data);
    } catch (err) {
        showGridError(err.message);
    }
}

async function runCustomQuery() {
    const sqlQuery = document.getElementById('sql-query-editor').value.trim();
    const metricsDisplay = document.getElementById('console-metrics-display');
    
    if (!sqlQuery) {
        metricsDisplay.className = 'console-metrics error';
        metricsDisplay.innerText = "Error: SQL editor is empty.";
        return;
    }

    showGridLoading();
    metricsDisplay.className = 'console-metrics';
    metricsDisplay.innerText = "Executing terminal query...";
    
    const startTime = performance.now();

    try {
        const res = await authedFetch(`${API_BASE}/analytics-data/query`, {
            method: 'POST',
            body: JSON.stringify({
                mode: 'custom',
                sqlQuery
            })
        });

        const duration = (performance.now() - startTime).toFixed(1);

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Query failed");
        }

        const data = await res.json();
        metricsDisplay.className = 'console-metrics success';
        metricsDisplay.innerText = `Success: Query completed in ${duration}ms (${data.length} rows returned).`;
        renderGridResults(data);
    } catch (err) {
        metricsDisplay.className = 'console-metrics error';
        metricsDisplay.innerText = `Terminal Failure: ${err.message}`;
        showGridError(err.message);
    }
}

// ==========================================
// 📊 INTERACTIVE RESULTS GRID RENDERER
// ==========================================
function renderGridResults(records) {
    const grid = document.getElementById('results-grid');
    const countBadge = document.getElementById('results-count');
    const btnExport = document.getElementById('btn-export-json');

    queryResultsCache = records;
    countBadge.innerText = `${records.length} row${records.length === 1 ? '' : 's'}`;

    if (records.length === 0) {
        grid.innerHTML = `
            <div class="grid-empty-state">
                <span class="empty-icon">🔍</span>
                <p>Query returned 0 records. Try broadening your filter parameters.</p>
            </div>
        `;
        btnExport.disabled = true;
        return;
    }

    btnExport.disabled = false;

    // Collect all unique keys dynamically (columns)
    const columns = Object.keys(records[0]);
    
    let tableHtml = '<table class="data-table"><thead><tr>';
    columns.forEach(col => {
        tableHtml += `<th>${col}</th>`;
    });
    tableHtml += '</tr></thead><tbody>';

    records.forEach(row => {
        tableHtml += '<tr>';
        columns.forEach(col => {
            const val = row[col];
            if (val === null || val === undefined) {
                tableHtml += '<td class="null-cell">NULL</td>';
            } else if (typeof val === 'number') {
                // If it looks like a currency/large number, format nicely
                const formatted = val % 1 === 0 ? val.toLocaleString() : val.toFixed(2);
                tableHtml += `<td class="num-cell">${formatted}</td>`;
            } else {
                tableHtml += `<td>${escapeHTML(String(val))}</td>`;
            }
        });
        tableHtml += '</tr>';
    });

    tableHtml += '</tbody></table>';
    grid.innerHTML = tableHtml;
}

// Helpers
function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

function showGridLoading() {
    const grid = document.getElementById('results-grid');
    grid.innerHTML = `
        <div class="grid-empty-state">
            <div class="loader-spinner"></div>
            <p>Querying analytics-source-db...</p>
        </div>
    `;
}

function showGridError(message) {
    const grid = document.getElementById('results-grid');
    grid.innerHTML = `
        <div class="grid-empty-state">
            <span class="empty-icon" style="color: var(--color-danger); opacity: 0.8;">🚨</span>
            <h4 style="color: var(--color-danger)">Execution Error</h4>
            <p style="max-width: 480px;">${escapeHTML(message)}</p>
        </div>
    `;
    document.getElementById('results-count').innerText = '0 rows';
    document.getElementById('btn-export-json').disabled = true;
}

// Export queries results cache to JSON file
function exportResultsAsJSON() {
    if (!queryResultsCache) return;
    
    const jsonString = JSON.stringify(queryResultsCache, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentTable || 'custom_query'}_export_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
