/**
 * AIM Intelligence Platform Shell Controller
 */

const API_BASE = '/api/v1';

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
  setupNavigation();
  setupAuthHandler();
  
  const key = localStorage.getItem('AIP_API_KEY') || '';
  if (key.startsWith('AIP-')) {
    fetchAndApplyUIConfiguration();
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
      
      refreshPlatformTelemetry();
      reloadActiveIframes();

      // Retrieve dynamic UI layouts
      await fetchAndApplyUIConfiguration();
      setupUIConfigManager();
    } else {
      if (loginScreen) loginScreen.classList.remove('hide');
      if (mainAppShell) mainAppShell.classList.add('hide');
    }
  }
 
  // Configure logout button click handler
  const logoutBtn = document.getElementById('shell-logout-btn');
  if (logoutBtn && !logoutBtn.dataset.listenerBound) {
    logoutBtn.dataset.listenerBound = 'true';
    logoutBtn.addEventListener('click', async () => {
      try {
        await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
      } catch (err) {
        console.warn("Logout request failed:", err);
      }
      localStorage.removeItem('AIP_API_KEY');
      localStorage.removeItem('AIP_USER_ROLE');
      localStorage.removeItem('AIP_USER_NAME');
      localStorage.removeItem('AIP_USER_UNAME');
      localStorage.removeItem('AIP_USER_CATEGORY');
      checkAuthStatus();
    });
  }

  // Configure clear cache button click handler
  const clearCacheBtn = document.getElementById('clear-cache-btn');
  if (clearCacheBtn && !clearCacheBtn.dataset.listenerBound) {
    clearCacheBtn.dataset.listenerBound = 'true';
    clearCacheBtn.addEventListener('click', async () => {
      if (confirm('Are you sure you want to clear session caches and reset all logged-in credentials?')) {
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
        window.location.reload();
      }
    });
  }
 
  checkAuthStatus();
}

// ==========================================================================
// ⚙️ DYNAMIC CLIENT-SIDE UI CONFIGURATION APPLICATOR & SME CONSOLE HANDLER
// ==========================================================================
let currentUIConfigurations = {};

async function fetchAndApplyUIConfiguration() {
  const key = localStorage.getItem('AIP_API_KEY') || '';
  if (!key.startsWith('AIP-')) return;

  try {
    const res = await fetch(`${API_BASE}/ui/config?_=${Date.now()}`);
    if (res.ok) {
      currentUIConfigurations = await res.json();
      applyUIConfiguration();
    }
  } catch (err) {
    console.error("Failed to fetch UI configurations:", err);
  }
}

function applyUIConfiguration() {
  const role = localStorage.getItem('AIP_USER_ROLE') || 'Analyst';
  
  // Resolve category strictly based on database role to ensure configuration matches authenticated persona
  let category;
  if (role === 'SME') {
    category = 'Business Admin';
  } else if (role === 'Analyst') {
    category = 'Analytics Professional';
  } else {
    category = 'Business User';
  }
  
  // Sync the category in local storage
  localStorage.setItem('AIP_USER_CATEGORY', category);
  
  const config = currentUIConfigurations[category];
  if (!config) return;
  
  const visibleSuites = [...(config.visible_suites || [])];
  const visibleSubproducts = config.visible_subproducts || {};

  // Auto-enable parent suite if any of its subproducts are allowed
  const suiteIds = ['reporting', 'analytics', 'automation', 'data-science'];
  suiteIds.forEach(suiteId => {
    const allowedTabs = visibleSubproducts[suiteId] || [];
    if (allowedTabs.length > 0 && !visibleSuites.includes(suiteId)) {
      visibleSuites.push(suiteId);
    }
  });

  // 1. Hide/Show Sidebar Nav Links
  const navItems = document.querySelectorAll('.nav-item');
  let firstVisiblePage = null;
  let isCurrentPageVisible = false;
  
  // Find current active page
  const activeNav = document.querySelector('.nav-item.active');
  const currentPageId = activeNav ? activeNav.getAttribute('data-page') : 'home';

  navItems.forEach(item => {
    const pageId = item.getAttribute('data-page');
    const isVisible = visibleSuites.includes(pageId);
    
    if (isVisible) {
      item.classList.remove('hide');
      if (!firstVisiblePage) firstVisiblePage = pageId;
      if (pageId === currentPageId) isCurrentPageVisible = true;
    } else {
      item.classList.add('hide');
    }
  });

  // 2. Hide/Show Subproduct Tabs inside sections
  suiteIds.forEach(suiteId => {
    const suiteSection = document.getElementById(`page-${suiteId}`);
    if (!suiteSection) return;
    
    const allowedTabs = visibleSubproducts[suiteId] || [];
    const tabsContainer = suiteSection.querySelector('.suite-tabs');
    if (!tabsContainer) return;

    const tabButtons = tabsContainer.querySelectorAll('.tab-btn');
    let firstVisibleTab = null;
    let isCurrentTabVisible = false;

    // Find active tab in suite
    const activeTabBtn = tabsContainer.querySelector('.tab-btn.active');
    let currentTabId = null;
    if (activeTabBtn) {
      const onclickAttr = activeTabBtn.getAttribute('onclick') || '';
      const match = onclickAttr.match(/switchSubProduct\(\s*'[^']+'\s*,\s*'([^']+)'\s*\)/);
      if (match) currentTabId = match[1];
    }

    tabButtons.forEach(btn => {
      const onclickAttr = btn.getAttribute('onclick') || '';
      const match = onclickAttr.match(/switchSubProduct\(\s*'[^']+'\s*,\s*'([^']+)'\s*\)/);
      if (!match) return;
      const tabId = match[1];
      const isVisible = allowedTabs.includes(tabId);
      
      const panel = document.getElementById(`subproduct-${suiteId}-${tabId}`);
      if (isVisible) {
        btn.classList.remove('hide');
        if (!firstVisibleTab) firstVisibleTab = tabId;
        if (tabId === currentTabId) isCurrentTabVisible = true;
      } else {
        btn.classList.add('hide');
        if (panel) panel.classList.remove('active');
      }
    });

    // Fallback if current active tab is hidden, switch to the first allowed visible tab
    if (!isCurrentTabVisible && firstVisibleTab) {
      switchSubProduct(suiteId, firstVisibleTab);
    }
  });

  // Fallback if current active page is hidden, redirect to Dashboard Home (or first visible allowed page)
  if (!isCurrentPageVisible) {
    if (visibleSuites.includes('home')) {
      switchPage('home');
    } else if (firstVisiblePage) {
      switchPage(firstVisiblePage);
    }
  }
}

function setupUIConfigManager() {
  const saveBtn = document.getElementById('uiconfig-save-btn');
  const resetBtn = document.getElementById('uiconfig-reset-btn');
  const selectCategory = document.getElementById('uiconfig-select-category');
  const msgEl = document.getElementById('uiconfig-msg');

  if (!selectCategory) return;

  // Load selected category's configuration to form checkboxes
  function loadCategoryConfigToForm() {
    const category = selectCategory.value;
    const config = currentUIConfigurations[category];
    if (!config) return;

    const visibleSuites = config.visible_suites || [];
    const visibleSubproducts = config.visible_subproducts || {};

    // Check/uncheck suites
    document.querySelectorAll('.config-suite-checkbox').forEach(cb => {
      cb.checked = visibleSuites.includes(cb.value);
    });

    // Check/uncheck tabs
    const suitesList = ['reporting', 'analytics', 'automation', 'data-science'];
    suitesList.forEach(suiteId => {
      const allowedTabs = visibleSubproducts[suiteId] || [];
      const tabGroup = document.getElementById(`config-tabs-${suiteId}`);
      if (!tabGroup) return;
      
      tabGroup.querySelectorAll('.config-tab-checkbox').forEach(cb => {
        cb.checked = allowedTabs.includes(cb.value);
      });
    });
  }

  // Clear previous event listener checks by defining clean hooks
  if (!selectCategory.dataset.listenerBound) {
    selectCategory.dataset.listenerBound = 'true';
    selectCategory.addEventListener('change', loadCategoryConfigToForm);
  }

  // Reset button
  if (resetBtn && !resetBtn.dataset.listenerBound) {
    resetBtn.dataset.listenerBound = 'true';
    resetBtn.addEventListener('click', loadCategoryConfigToForm);
  }

  // Save button
  if (saveBtn && !saveBtn.dataset.listenerBound) {
    saveBtn.dataset.listenerBound = 'true';
    saveBtn.addEventListener('click', async () => {
      const category = selectCategory.value;
      
      // Collect visible suites
      const suites = [];
      document.querySelectorAll('.config-suite-checkbox').forEach(cb => {
        if (cb.checked) suites.push(cb.value);
      });

      // Collect subproducts
      const visible_subproducts = {};
      const suitesList = ['reporting', 'analytics', 'automation', 'data-science'];
      suitesList.forEach(suiteId => {
        const tabs = [];
        const tabGroup = document.getElementById(`config-tabs-${suiteId}`);
        if (tabGroup) {
          tabGroup.querySelectorAll('.config-tab-checkbox').forEach(cb => {
            if (cb.checked) tabs.push(cb.value);
          });
        }
        visible_subproducts[suiteId] = tabs;
        
        // Auto-include parent suite if any subproducts are checked
        if (tabs.length > 0 && !suites.includes(suiteId)) {
          suites.push(suiteId);
        }
      });
      const visible_suites = suites.join(',');

      try {
        const res = await fetch(`${API_BASE}/ui/config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category, visible_suites, visible_subproducts })
        });
        const data = await res.json();

        if (data.success) {
          msgEl.innerText = data.message || "UI configuration saved successfully!";
          msgEl.style.background = "#d1fae5";
          msgEl.style.color = "#065f46";
          msgEl.classList.remove('hide');

          // Refresh the configurations local state and apply them in real-time
          await fetchAndApplyUIConfiguration();
          
          setTimeout(() => {
            msgEl.classList.add('hide');
          }, 3000);
        } else {
          msgEl.innerText = data.error || "Failed to save UI configuration.";
          msgEl.style.background = "#fee2e2";
          msgEl.style.color = "#991b1b";
          msgEl.classList.remove('hide');
        }
      } catch (err) {
        msgEl.innerText = `Save failed: ${err.message}`;
        msgEl.style.background = "#fee2e2";
        msgEl.style.color = "#991b1b";
        msgEl.classList.remove('hide');
      }
    });
  }

  // Initial load
  loadCategoryConfigToForm();
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
