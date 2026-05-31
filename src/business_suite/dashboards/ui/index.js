/**
 * AIP Dashboards Workspace Controller
 */

const API_BASE = '/api/v1';
let currentReportsList = [];

// Authed Fetch Interceptor to include JWT token in the headers for subproduct iframe endpoints
async function authedFetch(url, options = {}) {
  const apiKey = localStorage.getItem('AIP_API_KEY') || '';
  options.headers = options.headers || {};
  if (apiKey) {
    options.headers['Authorization'] = `Bearer ${apiKey}`;
  }
  return fetch(url, options);
}

document.addEventListener('DOMContentLoaded', () => {
  loadReportsCatalog();
  setupEventListeners();
});

function setupEventListeners() {
  const refreshBtn = document.getElementById('refresh-reports-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadReportsCatalog();
    });
  }

  const searchInput = document.getElementById('report-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase().trim();
      renderReportsList(filterReports(query));
    });
  }
}

async function loadReportsCatalog() {
  const container = document.getElementById('reports-list-container');
  if (container) {
    container.innerHTML = '<div class="loading-state">Refreshing shared catalog...</div>';
  }

  try {
    const res = await authedFetch(`${API_BASE}/dashboards/reports`);
    if (res.ok) {
      currentReportsList = await res.json();
      
      // Update Total Reports count stat card
      const countEl = document.getElementById('stats-total-count');
      if (countEl) countEl.innerText = currentReportsList.length;

      renderReportsList(currentReportsList);
    } else {
      showErrorState("Could not refresh reports: Server returned error.");
    }
  } catch (error) {
    console.error("Failed to load reports catalog:", error);
    showErrorState(`Authentication required or network error: ${error.message}`);
  }
}

function filterReports(query) {
  if (!query) return currentReportsList;
  return currentReportsList.filter(r => 
    r.title.toLowerCase().includes(query) || 
    r.category.toLowerCase().includes(query) ||
    r.filename.toLowerCase().includes(query)
  );
}

function renderReportsList(reports) {
  const container = document.getElementById('reports-list-container');
  if (!container) return;

  if (reports.length === 0) {
    container.innerHTML = '<div class="loading-state">No matching reports found.</div>';
    return;
  }

  container.innerHTML = '';
  reports.forEach(report => {
    const item = document.createElement('div');
    item.className = 'report-item';
    item.dataset.filename = report.filename;
    
    // Add LOB specific badges
    const badgeClass = report.category.toLowerCase();
    
    item.innerHTML = `
      <div class="report-item-title">${report.title}</div>
      <div class="report-item-meta">
        <span class="report-badge ${badgeClass}">${report.category}</span>
        <span>${report.sizeKb} KB</span>
      </div>
    `;
    
    item.addEventListener('click', () => {
      // Manage active classes
      document.querySelectorAll('.report-item').forEach(el => el.classList.remove('active'));
      item.classList.add('active');
      
      selectReport(report);
    });
    
    container.appendChild(item);
  });
}

function selectReport(report) {
  // 1. Update stats board values
  const activeTitle = document.getElementById('stats-active-title');
  const activeLob = document.getElementById('stats-active-lob');
  const activeOwner = document.getElementById('stats-active-owner');
  
  if (activeTitle) activeTitle.innerText = report.title;
  if (activeLob) activeLob.innerText = report.category;
  if (activeOwner) activeOwner.innerText = report.owner || "Report Builder";

  // 2. Load the HTML content directly inside the iframe safely!
  const iframe = document.getElementById('report-display-frame');
  const emptyState = document.getElementById('viewport-empty-state');
  
  if (iframe && emptyState) {
    emptyState.classList.add('hide');
    iframe.classList.remove('hide');
    
    // We point the iframe directly to our authenticated API endpoint
    // To ensure the Authorization Bearer header is passed safely, we fetch the HTML response
    // and load it as a data object blob URL inside the iframe! This is a master-level security pattern!
    iframe.src = 'about:blank'; // reset
    
    authedFetch(`${API_BASE}/dashboards/reports/${report.filename}`)
      .then(res => {
        if (res.ok) return res.blob();
        throw new Error("Could not load report content safely.");
      })
      .then(blob => {
        const blobUrl = URL.createObjectURL(blob);
        iframe.src = blobUrl;
      })
      .catch(err => {
        console.error("Iframe load failure:", err);
        iframe.classList.add('hide');
        emptyState.classList.remove('hide');
        emptyState.innerHTML = `
          <span class="empty-icon" style="background: rgba(239, 68, 68, 0.1); color: var(--danger); border-color: rgba(239,68,68,0.2)">⚠️</span>
          <h2 style="color: var(--danger)">Loading Error</h2>
          <p>${err.message}</p>
        `;
      });
  }
}

function showErrorState(message) {
  const container = document.getElementById('reports-list-container');
  if (container) {
    container.innerHTML = `<div class="loading-state" style="color: var(--danger)">⚠️ ${message}</div>`;
  }
}
