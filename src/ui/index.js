/**
 * AIM Intelligence Platform Shell Controller
 */

const API_BASE = '/api/v1';

const PRODUCT_CATALOG = {
  'dashboards': {
    label: 'Dashboards',
    icon: '📊',
    group: 'Business Suite',
    description: 'Monitor curated KPIs, executive views, operational dashboards, cataloged reports, and dashboard search.'
  },
  'conversational-bi': {
    label: 'Conversational BI',
    icon: '💬',
    group: 'Business Suite',
    description: 'Ask natural-language questions, drill into metrics, and receive business-friendly answers.'
  },
  'proactive-alerts': {
    label: 'Proactive Alerts',
    icon: '🚨',
    group: 'Business Suite',
    description: 'Track KPI thresholds, anomalies, trends, subscriptions, and alert history.'
  },
  'deep-insights': {
    label: 'Deep Insights',
    icon: '🔎',
    group: 'Business Suite',
    description: 'Interpret trends, identify drivers, risks, opportunities, and supporting evidence.'
  },
  'scenario-analysis': {
    label: 'Scenario Analysis',
    icon: '🧮',
    group: 'Business Suite',
    description: 'Compare what-if assumptions, forecasts, impact estimates, and sensitivity analysis.'
  },
  'prism': {
    label: 'PRISM',
    icon: '🔁',
    group: 'Analyst Actions',
    description: 'Rationalize report inventories, detect duplicates, quantify overlap, and plan consolidation.'
  },
  'research': {
    label: 'Research',
    icon: '📚',
    group: 'Analyst Actions',
    description: 'Find glossary context, historical analysis, artifacts, outcomes, and institutional knowledge.'
  },
  'explore-data': {
    label: 'Explore Data',
    icon: '🛢️',
    group: 'Analyst Actions',
    description: 'Understand, profile, and query enterprise datasets for analytical work.'
  },
  'build-report': {
    label: 'Build Report',
    icon: '📝',
    group: 'Analyst Actions',
    description: 'Assemble governed reports, summaries, evidence, and reusable outputs.'
  },
  'root-cause-analysis': {
    label: 'Root Cause Analysis',
    icon: '🧭',
    group: 'Analyst Actions',
    description: 'Investigate drivers, contribution patterns, and evidence behind business changes.'
  },
  'recommend-actions': {
    label: 'Recommend Actions',
    icon: '✅',
    group: 'Analyst Actions',
    description: 'Generate action options, expected impacts, risks, and decision-support rationale.'
  }
};

const PERSONA_PRODUCT_IDS = {
  'Business User': ['dashboards', 'conversational-bi', 'proactive-alerts', 'deep-insights', 'scenario-analysis'],
  'Analytics Professional': ['prism', 'research', 'explore-data', 'build-report', 'root-cause-analysis', 'recommend-actions'],
  'Business Admin': ['prism', 'research', 'explore-data', 'build-report', 'root-cause-analysis', 'recommend-actions']
};

function getCurrentPersonaCategory() {
  const role = localStorage.getItem('AIP_USER_ROLE') || 'Analyst';
  if (role === 'SME') return 'Business Admin';
  if (role === 'Analyst') return 'Analytics Professional';
  return 'Business User';
}

function getPersonaProductIds(category = getCurrentPersonaCategory()) {
  const role = localStorage.getItem('AIP_USER_ROLE') || 'Analyst';
  if (role === 'SME') return [];
  return PERSONA_PRODUCT_IDS[category] || PERSONA_PRODUCT_IDS['Business User'];
}

function renderPersonaProducts(category = getCurrentPersonaCategory()) {
  const productIds = getPersonaProductIds(category);
  const navContainer = document.getElementById('persona-product-nav');
  const grid = document.getElementById('persona-product-grid');
  const heading = document.getElementById('persona-product-heading');
  const navTitle = document.getElementById('persona-product-nav-title');
  const role = localStorage.getItem('AIP_USER_ROLE') || 'Analyst';

  if (role === 'SME') {
    if (navTitle) navTitle.classList.add('hide');
    if (heading) heading.classList.add('hide');
  } else {
    if (navTitle) navTitle.classList.remove('hide');
    if (heading) heading.classList.remove('hide');
    const groupLabel = category === 'Business User' ? 'Business Suite' : 'Analyst Actions';
    if (heading) heading.innerText = `${groupLabel} Products`;
  }

  if (navContainer) {
    if (role === 'SME') {
      navContainer.innerHTML = '';
    } else {
      navContainer.innerHTML = productIds.map(productId => {
        const product = PRODUCT_CATALOG[productId];
        return `<a href="#" class="nav-item persona-product-item" data-page="${productId}" data-product="true" data-tooltip="${product.label}">
          <span class="nav-icon">${product.icon}</span> <span class="nav-text">${product.label}</span>
        </a>`;
      }).join('');

      navContainer.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
          e.preventDefault();
          switchPage(item.getAttribute('data-page'));
        });
      });
    }
  }

  if (grid) {
    if (role === 'SME') {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; background: rgba(255, 255, 255, 0.4); backdrop-filter: blur(10px); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.2); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05); margin-top: 10px;">
          <div style="font-size: 48px; margin-bottom: 16px;">📚</div>
          <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">SME Governance Dashboard</h3>
          <p style="font-size: 14px; color: var(--text-secondary); max-width: 500px; margin: 0 auto 20px; line-height: 1.5;">
            You are logged in as a Subject Matter Expert (SME). No business suite or analytics products are available to your profile. Please navigate to the KMS Workspace to manage and approve enterprise knowledge.
          </p>
          <button class="btn" style="background: var(--accent-color); font-weight: 600; padding: 10px 20px; border-radius: 6px; cursor: pointer; border: none; color: #fff; transition: opacity 0.2s;" onclick="switchPage('kms')">Go to KMS Workspace</button>
        </div>
      `;
    } else {
      grid.innerHTML = productIds.map(productId => {
        const product = PRODUCT_CATALOG[productId];
        return `<div class="product-card" onclick="switchPage('${productId}')">
          <div class="product-icon">${product.icon}</div>
          <h3>${product.label}</h3>
          <p>${product.description}</p>
        </div>`;
      }).join('');
    }
  }
}

function openFirstPersonaProduct() {
  const firstProductId = getPersonaProductIds()[0];
  if (firstProductId) switchPage(firstProductId);
}
window.openFirstPersonaProduct = openFirstPersonaProduct;

// Authed Fetch Interceptor matching standard session storage
const originalFetch = window.fetch;
window.fetch = async function(url, options = {}) {
  const apiKey = localStorage.getItem('AIP_API_KEY') || '';
  if (url.includes('/api/v1')) {
    options.headers = options.headers || {};
    if (apiKey) {
      options.headers['Authorization'] = `Bearer ${apiKey}`;
    }
  }
  const response = await originalFetch(url, options);
  if (response.status === 401 && !url.includes('/auth/login')) {
    localStorage.removeItem('AIP_API_KEY');
    setupAuthHandler();
  }
  return response;
};

document.addEventListener('DOMContentLoaded', () => {
  initGlobalButtonFeedback();
  initSidebarCollapse();
  setupNavigation();
  setupAuthHandler();
  
  const key = localStorage.getItem('AIP_API_KEY') || '';
  if (key.startsWith('AIP-')) {
    applyPersonaVisibility();
  }
});

// ==========================================================================
// 🔑 CENTRAL AUTHENTICATION CONTROL CONSOLE (UNIFIED LOGIN & LOGOUT)
// ==========================================================================
function setupAuthHandler() {
  const loginForm = document.getElementById('login-form');
  const loginScreen = document.getElementById('auth-login-screen');
  const mainAppShell = document.getElementById('main-app-shell');
  const loginErrorMsg = document.getElementById('login-error-msg');
  const lockOverlay = document.getElementById('auth-lock-overlay');
  
  const selectLob = document.getElementById('login-business-lob');
  const selectCategory = document.getElementById('login-user-category');
  const usernameInput = document.getElementById('login-username');
  const passwordInput = document.getElementById('login-password');

  if (loginForm && !loginForm.dataset.listenerBound) {
    loginForm.dataset.listenerBound = 'true';
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const username = usernameInput.value.trim();
      const password = passwordInput.value.trim();
      const category = selectCategory ? selectCategory.value : 'Business User';
      const lob = selectLob ? selectLob.value : 'Treasury';
      
      try {
        const res = await originalFetch(`${API_BASE}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password, lob, category })
        });
        const data = await res.json();
        
        if (data.success && data.token) {
          localStorage.setItem('AIP_API_KEY', data.token);
          const serverRole = data.role || 'Analyst';
          localStorage.setItem('AIP_USER_ROLE', serverRole);
          localStorage.setItem('AIP_USER_NAME', data.displayName || 'Analytics Pro');
          localStorage.setItem('AIP_USER_UNAME', username);
          
          // Dynamically map and store category strictly based on the server-returned database role
          let resolvedCategory = 'Business User';
          if (serverRole === 'SME') {
            resolvedCategory = 'Business Admin';
          } else if (serverRole === 'Analyst') {
            resolvedCategory = 'Analytics Professional';
          } else if (serverRole === 'Business User') {
            resolvedCategory = 'Business User';
          } else {
            resolvedCategory = category;
          }
          localStorage.setItem('AIP_USER_CATEGORY', resolvedCategory);
          
          loginErrorMsg.classList.add('hide');
          checkAuthStatus();
        } else {
          loginErrorMsg.innerText = data.error || 'Invalid credentials.';
          loginErrorMsg.classList.remove('hide');
        }
      } catch (err) {
        loginErrorMsg.innerText = `Authentication server offline: ${err.message}`;
        loginErrorMsg.classList.remove('hide');
      }
    });
  }
 
  async function checkAuthStatus() {
    const key = localStorage.getItem('AIP_API_KEY') || '';
    if (key.startsWith('AIP-')) {
      if (loginScreen) loginScreen.classList.add('hide');
      if (mainAppShell) mainAppShell.classList.remove('hide');
      if (lockOverlay) lockOverlay.classList.add('hide');
      
      // Update sidebar dynamic profile values
      const name = localStorage.getItem('AIP_USER_NAME') || 'Analytics Pro';
      const role = localStorage.getItem('AIP_USER_ROLE') || 'Analyst';
      const uname = localStorage.getItem('AIP_USER_UNAME') || 'Treasury_Analyst';
      
      const avatarEl = document.getElementById('shell-user-avatar');
      const nameEl = document.getElementById('shell-user-name');
      const roleEl = document.getElementById('shell-user-role');
      
      if (avatarEl) {
        const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        avatarEl.innerText = initials;
      }
      if (nameEl) nameEl.innerText = name;
      if (roleEl) roleEl.innerText = `${role} (${uname})`;
      
      renderPersonaProducts(localStorage.getItem('AIP_USER_CATEGORY') || getCurrentPersonaCategory());
      applyPersonaVisibility();
      refreshPlatformTelemetry();
      reloadActiveIframes();
    } else {
      if (loginScreen) loginScreen.classList.remove('hide');
      if (mainAppShell) mainAppShell.classList.add('hide');
    }
  }
 


  const logoutBtn = document.getElementById('shell-logout-btn');
  if (logoutBtn && !logoutBtn.dataset.listenerBound) {
    logoutBtn.dataset.listenerBound = 'true';
    logoutBtn.addEventListener('click', async () => {
      const originalHtml = setButtonBusy(logoutBtn, '⏳ Logout in progress...');
      try {
        await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
      } catch (err) {
        console.warn("Logout request failed:", err);
      } finally {
        localStorage.removeItem('AIP_API_KEY');
        localStorage.removeItem('AIP_USER_ROLE');
        localStorage.removeItem('AIP_USER_NAME');
        localStorage.removeItem('AIP_USER_UNAME');
        localStorage.removeItem('AIP_USER_CATEGORY');
        restoreButton(logoutBtn, originalHtml);
        checkAuthStatus();
      }
    });
  }

  // Configure clear cache button click handler
  const clearCacheBtn = document.getElementById('clear-cache-btn');
  if (clearCacheBtn && !clearCacheBtn.dataset.listenerBound) {
    clearCacheBtn.dataset.listenerBound = 'true';
    clearCacheBtn.addEventListener('click', async () => {
      if (confirm('Are you sure you want to clear session caches and reset all logged-in credentials?')) {
        const originalHtml = setButtonBusy(clearCacheBtn, '⏳ Clearing session...');
        try {
          await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
        } catch (err) {
          console.warn("Logout request failed:", err);
        }
        localStorage.clear();
        sessionStorage.clear();
        document.cookie.split(";").forEach((c) => {
          document.cookie = c
            .replace(/^ +/, "")
            .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
        });
        restoreButton(clearCacheBtn, originalHtml);
        window.location.reload();
      }
    });
  }
 
  checkAuthStatus();
}

function setButtonBusy(button, busyText) {
  const originalHtml = button.innerHTML;
  button.dataset.originalHtml = originalHtml;
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  button.classList.add('is-busy');
  button.innerHTML = busyText;
  return originalHtml;
}

function restoreButton(button, originalHtml) {
  button.disabled = false;
  button.removeAttribute('aria-busy');
  button.classList.remove('is-busy');
  button.innerHTML = originalHtml || button.dataset.originalHtml || button.innerHTML;
  delete button.dataset.originalHtml;
}

function initGlobalButtonFeedback() {
  if (document.body.dataset.buttonFeedbackBound) return;
  document.body.dataset.buttonFeedbackBound = 'true';
  document.addEventListener('click', (event) => {
    const target = event.target.closest('button, .btn, .nav-item, .product-card');
    if (!target || target.disabled || target.getAttribute('aria-disabled') === 'true') return;
    target.classList.remove('is-clicked');
    void target.offsetWidth;
    target.classList.add('is-clicked');
    window.setTimeout(() => target.classList.remove('is-clicked'), 220);
  }, true);
}

// ==========================================================================
// 🧭 STATIC PERSONA VISIBILITY APPLICATOR
// ===========================================================================
function applyPersonaVisibility() {
  const category = getCurrentPersonaCategory();
  localStorage.setItem('AIP_USER_CATEGORY', category);
  renderPersonaProducts(category);

  const personaProductIds = getPersonaProductIds(category);
  const visibleSystemPages = ['home'];
  if (category === 'Business Admin') {
    visibleSystemPages.push('kms');
  }

  const activeNav = document.querySelector('.nav-item.active');
  const currentPageId = activeNav ? activeNav.getAttribute('data-page') : 'home';
  let currentPageVisible = false;

  document.querySelectorAll('.nav-item').forEach(item => {
    const pageId = item.getAttribute('data-page');
    const isProductNav = item.getAttribute('data-product') === 'true';
    const isVisible = isProductNav ? personaProductIds.includes(pageId) : visibleSystemPages.includes(pageId);

    item.classList.toggle('hide', !isVisible);
    if (isVisible && pageId === currentPageId) currentPageVisible = true;
  });

  if (!currentPageVisible) {
    switchPage(visibleSystemPages.includes('home') ? 'home' : personaProductIds[0]);
  }
}

// Force reload of active iframes when key state transitions (to fetch successfully)
function reloadActiveIframes() {
  document.querySelectorAll('iframe').forEach(iframe => {
    iframe.src = iframe.src;
  });
}

// ==========================================
// 🧭 DYNAMIC NAVIGATION CONTROLLER
// ==========================================
function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const pageId = item.getAttribute('data-page');
      switchPage(pageId);
    });
  });
}

function switchPage(pageId) {
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const activeNav = document.querySelector(`.nav-item[data-page="${pageId}"]`);
  if (activeNav) activeNav.classList.add('active');

  document.querySelectorAll('.page-view').forEach(el => el.classList.remove('active'));
  const activePage = document.getElementById(`page-${pageId}`);
  if (activePage) activePage.classList.add('active');

  refreshPlatformTelemetry();
}

window.switchPage = switchPage;

function switchSubProduct(suiteId, productId) {
  const tabsContainer = document.querySelector(`#page-${suiteId} .suite-tabs`);
  if (!tabsContainer) return;
  
  tabsContainer.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  const clickedBtn = Array.from(tabsContainer.querySelectorAll('.tab-btn'))
    .find(btn => btn.getAttribute('onclick').includes(`'${productId}'`));
  if (clickedBtn) clickedBtn.classList.add('active');

  document.querySelectorAll(`#page-${suiteId} .subproduct-panel`).forEach(panel => {
    panel.classList.remove('active');
  });
  
  const targetPanel = document.getElementById(`subproduct-${suiteId}-${productId}`);
  if (targetPanel) {
    targetPanel.classList.add('active');
    // Force reload active panel iframe
    const iframe = targetPanel.querySelector('iframe');
    if (iframe) iframe.src = iframe.src;
  }
  
  refreshPlatformTelemetry();
}

window.switchSubProduct = switchSubProduct;

// ==========================================
// 📊 CENTRAL TELEMETRY AUDITER
// ==========================================
async function refreshPlatformTelemetry() {
  const key = localStorage.getItem('AIP_API_KEY') || '';
  if (!key.startsWith('AIP-')) return;

  try {
    const capsRes = await fetch(`${API_BASE}/capabilities`);
    const caps = await capsRes.json();
    
    const logsRes = await fetch(`${API_BASE}/execution-logs`);
    const logs = await logsRes.json();
    
    const capsVal = document.getElementById('stats-caps-count');
    if (capsVal) capsVal.innerText = caps.length;
    
    const logsVal = document.getElementById('stats-logs-count');
    if (logsVal) logsVal.innerText = logs.length;
  } catch (error) {
    console.error("Telemetry query failed:", error);
  }
}

// ==========================================
// ◀ COLLAPSABLE SIDEBAR CONTROLLER
// ==========================================
function initSidebarCollapse() {
  const sidebar = document.getElementById('app-sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle-btn');
  if (!sidebar) return;

  const isCollapsed = localStorage.getItem('AIP_SIDEBAR_COLLAPSED') === 'true';
  if (isCollapsed) {
    sidebar.classList.add('collapsed');
    if (toggleBtn) {
      toggleBtn.title = 'Expand Sidebar';
    }
  } else {
    sidebar.classList.remove('collapsed');
    if (toggleBtn) {
      toggleBtn.title = 'Collapse Sidebar';
    }
  }

  if (toggleBtn && !toggleBtn.dataset.listenerBound) {
    toggleBtn.dataset.listenerBound = 'true';
    toggleBtn.addEventListener('click', () => {
      const collapsed = sidebar.classList.toggle('collapsed');
      localStorage.setItem('AIP_SIDEBAR_COLLAPSED', collapsed ? 'true' : 'false');
      toggleBtn.title = collapsed ? 'Expand Sidebar' : 'Collapse Sidebar';
    });
  }
}
