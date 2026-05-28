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
  
  const tabAnalyst = document.getElementById('login-tab-analyst');
  const tabSme = document.getElementById('login-tab-sme');
  
  const groupAnalyst = document.getElementById('group-analyst-ids');
  const groupSme = document.getElementById('group-sme-ids');
  
  const selectAnalyst = document.getElementById('login-analyst-id');
  const selectSme = document.getElementById('login-sme-id');
  
  const usernameInput = document.getElementById('login-username');
  const passwordInput = document.getElementById('login-password');
  
  // Tab click selectors
  if (tabAnalyst && tabSme) {
    tabAnalyst.addEventListener('click', () => {
      tabAnalyst.classList.add('active');
      tabAnalyst.style.background = 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)';
      tabAnalyst.style.boxShadow = '0 4px 12px rgba(59, 130, 246, 0.25)';
      tabAnalyst.style.color = '#fff';
      
      tabSme.classList.remove('active');
      tabSme.style.background = 'transparent';
      tabSme.style.boxShadow = 'none';
      tabSme.style.color = 'rgba(255, 255, 255, 0.5)';
      
      groupAnalyst.classList.remove('hide');
      groupSme.classList.add('hide');
      
      if (selectAnalyst && usernameInput) {
        usernameInput.value = selectAnalyst.value;
      }
    });

    tabSme.addEventListener('click', () => {
      tabSme.classList.add('active');
      tabSme.style.background = 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)';
      tabSme.style.boxShadow = '0 4px 12px rgba(59, 130, 246, 0.25)';
      tabSme.style.color = '#fff';
      
      tabAnalyst.classList.remove('active');
      tabAnalyst.style.background = 'transparent';
      tabAnalyst.style.boxShadow = 'none';
      tabAnalyst.style.color = 'rgba(255, 255, 255, 0.5)';
      
      groupSme.classList.remove('hide');
      groupAnalyst.classList.add('hide');
      
      if (selectSme && usernameInput) {
        usernameInput.value = selectSme.value;
      }
    });
  }

  // Handle changes to dropdown selects
  if (selectAnalyst && usernameInput) {
    selectAnalyst.addEventListener('change', () => {
      if (tabAnalyst.classList.contains('active')) {
        usernameInput.value = selectAnalyst.value;
      }
    });
  }
  if (selectSme && usernameInput) {
    selectSme.addEventListener('change', () => {
      if (tabSme.classList.contains('active')) {
        usernameInput.value = selectSme.value;
      }
    });
  }
 
  if (loginForm && !loginForm.dataset.listenerBound) {
    loginForm.dataset.listenerBound = 'true';
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      // Update dynamic target username right before submit
      if (tabAnalyst.classList.contains('active') && selectAnalyst) {
        usernameInput.value = selectAnalyst.value;
      } else if (tabSme.classList.contains('active') && selectSme) {
        usernameInput.value = selectSme.value;
      }

      const username = usernameInput.value.trim();
      const password = passwordInput.value.trim();
      
      try {
        const res = await originalFetch(`${API_BASE}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        
        if (data.success && data.token) {
          localStorage.setItem('AIP_API_KEY', data.token);
          localStorage.setItem('AIP_USER_ROLE', data.role || 'Analyst');
          localStorage.setItem('AIP_USER_NAME', data.displayName || 'Analytics Pro');
          localStorage.setItem('AIP_USER_UNAME', username);
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
 
  function checkAuthStatus() {
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
