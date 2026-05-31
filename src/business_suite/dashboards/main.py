"""
Business Suite Dashboard View Backend Logic
Scans and registers shared analytical reports under Infra/shared.
"""

import os
import time
from typing import List, Dict, Any
from src.shared.config import config
from src.shared.infra_client.storage_client import StorageClient

def get_dashboard_reports() -> List[Dict[str, Any]]:
    """Lists all HTML report files inside config.SHARED_REPORT_PATH with file metadata."""
    reports = []
    shared_dir = config.SHARED_REPORT_PATH
    
    if not os.path.exists(shared_dir):
        os.makedirs(shared_dir, exist_ok=True)
        
    for file in os.listdir(shared_dir):
        if file.endswith('.html'):
            file_path = os.path.join(shared_dir, file)
            stat = os.stat(file_path)
            size_kb = round(stat.st_size / 1024, 1)
            modified_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
            
            # Formulate user-friendly titles based on filename
            title = file.replace('.html', '').replace('_', ' ').replace('-', ' ').title()
            
            # Assign category LOB
            category = "General"
            if "liquidity" in file.lower() or "treasury" in file.lower():
                category = "Treasury"
            elif "compliance" in file.lower() or "audit" in file.lower():
                category = "Compliance"
            elif "wealth" in file.lower() or "portfolio" in file.lower() or "investment" in file.lower():
                category = "Wealth"
            elif "credit" in file.lower() or "risk" in file.lower():
                category = "Credit"
                
            reports.append({
                'filename': file,
                'title': title,
                'sizeKb': size_kb,
                'lastModified': modified_time,
                'category': category,
                'owner': "Report Builder Agent"
            })
            
    # Sort by modification time (newest first)
    reports.sort(key=lambda x: x['lastModified'], reverse=True)
    return reports

def seed_premium_reports_if_empty():
    """Seeds three premium, highly styled, interactive HTML sample reports into shared folder if empty."""
    shared_dir = config.SHARED_REPORT_PATH
    if not os.path.exists(shared_dir):
        os.makedirs(shared_dir, exist_ok=True)
        
    # Check if there are already any html files
    html_files = [f for f in os.listdir(shared_dir) if f.endswith('.html')]
    if len(html_files) > 0:
        return
        
    print("[Dashboard Seeder] Seeding premium sample reports into Infra/shared...")
    
    # 1. Treasury Liquidity Report
    treasury_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Treasury Liquidity & Sweep Performance Report</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@500;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
      --card-bg: rgba(30, 41, 59, 0.7);
      --border-color: rgba(255, 255, 255, 0.08);
      --text-main: #f8fafc;
      --text-sub: #94a3b8;
      --primary: #3b82f6;
      --primary-glow: rgba(59, 130, 246, 0.35);
      --success: #10b981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg-gradient);
      color: var(--text-main);
      min-height: 100vh;
      padding: 30px;
    }
    .header {
      margin-bottom: 30px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 20px;
    }
    h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 28px;
      font-weight: 700;
      background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 6px;
    }
    .subtitle { color: var(--text-sub); font-size: 14px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      backdrop-filter: blur(12px);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    .metric-value {
      font-family: 'Outfit', sans-serif;
      font-size: 32px;
      font-weight: 700;
      color: var(--primary);
      margin: 10px 0 5px 0;
      text-shadow: 0 0 10px var(--primary-glow);
    }
    .metric-title { font-size: 12px; font-weight: 600; color: var(--text-sub); text-transform: uppercase; }
    .metric-change { font-size: 13px; color: var(--success); display: flex; align-items: center; gap: 4px; }
    .chart-container {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 30px;
    }
    h2 { font-family: 'Outfit', sans-serif; font-size: 20px; margin-bottom: 20px; color: #93c5fd; }
    .table-container { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    th { padding: 12px 16px; border-bottom: 2px solid var(--border-color); color: var(--text-sub); font-size: 12px; text-transform: uppercase; font-weight: 600; }
    td { padding: 16px; border-bottom: 1px solid var(--border-color); font-size: 14px; }
    tr:hover { background: rgba(255, 255, 255, 0.02); }
    .badge {
      display: inline-block;
      padding: 4px 8px;
      font-size: 11px;
      font-weight: 600;
      border-radius: 6px;
      background: rgba(16, 185, 129, 0.15);
      color: var(--success);
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>📊 Corporate Treasury & Liquidity Sweep Analytics</h1>
    <p class="subtitle">Platform Generated: Treasury Ledger Insights & Sweeps Operations Summary</p>
  </div>
  
  <div class="grid">
    <div class="card">
      <div class="metric-title">Total Sweeps Handled</div>
      <div class="metric-value">4,812,050</div>
      <div class="metric-change">⬆ +12.4% vs last month</div>
    </div>
    <div class="card">
      <div class="metric-title">Net Liquidity Optimized</div>
      <div class="metric-value" style="color: #10b981; text-shadow: 0 0 10px rgba(16,185,129,0.3)">$1.42 Billion</div>
      <div class="metric-change">⬆ +8.1% target exceeded</div>
    </div>
    <div class="card">
      <div class="metric-title">ZBA Efficiency Rate</div>
      <div class="metric-value" style="color: #fbbf24; text-shadow: 0 0 10px rgba(251,191,36,0.3)">99.85%</div>
      <div class="metric-change">Stable baseline verified</div>
    </div>
  </div>

  <div class="chart-container">
    <h2>📈 Cash Inflows vs Sweeps Outflows (Millions $)</h2>
    <div style="height: 120px; display: flex; align-items: flex-end; gap: 15px; padding-bottom: 10px; border-bottom: 1px solid var(--border-color);">
      <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px;">
        <div style="width: 100%; height: 60px; background: var(--primary); border-radius: 4px; box-shadow: 0 0 12px var(--primary-glow);"></div>
        <span style="font-size: 11px; color: var(--text-sub);">Q1</span>
      </div>
      <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px;">
        <div style="width: 100%; height: 80px; background: var(--primary); border-radius: 4px; box-shadow: 0 0 12px var(--primary-glow);"></div>
        <span style="font-size: 11px; color: var(--text-sub);">Q2</span>
      </div>
      <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px;">
        <div style="width: 100%; height: 95px; background: var(--primary); border-radius: 4px; box-shadow: 0 0 12px var(--primary-glow);"></div>
        <span style="font-size: 11px; color: var(--text-sub);">Q3</span>
      </div>
      <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px;">
        <div style="width: 100%; height: 110px; background: var(--success); border-radius: 4px; box-shadow: 0 0 12px rgba(16,185,129,0.35);"></div>
        <span style="font-size: 11px; color: var(--text-sub);">Q4</span>
      </div>
    </div>
  </div>

  <div class="card" style="margin-bottom: 0;">
    <h2>💼 Active Branch Balances Details</h2>
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>Branch Location</th>
            <th>Cash Inflows</th>
            <th>Optimized Sweep Sums</th>
            <th>Fulfillment Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>New York (NY-10)</td>
            <td>$450,000,000</td>
            <td>$449,850,000</td>
            <td><span class="badge">Fulfilled</span></td>
          </tr>
          <tr>
            <td>Chicago (CH-08)</td>
            <td>$320,000,000</td>
            <td>$319,920,000</td>
            <td><span class="badge">Fulfilled</span></td>
          </tr>
          <tr>
            <td>San Francisco (SF-14)</td>
            <td>$290,000,000</td>
            <td>$289,800,000</td>
            <td><span class="badge">Fulfilled</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>"""

    # 2. Compliance Audit Summary
    compliance_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Regulatory Compliance Audit Summary</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@500;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-gradient: linear-gradient(135deg, #090d16 0%, #111827 100%);
      --card-bg: rgba(17, 24, 39, 0.75);
      --border-color: rgba(255, 255, 255, 0.08);
      --text-main: #f3f4f6;
      --text-sub: #9ca3af;
      --danger: #ef4444;
      --success: #10b981;
      --warning: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg-gradient);
      color: var(--text-main);
      min-height: 100vh;
      padding: 30px;
    }
    .header {
      margin-bottom: 30px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 20px;
    }
    h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 28px;
      font-weight: 700;
      background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 6px;
    }
    .subtitle { color: var(--text-sub); font-size: 14px; }
    .alert-banner {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 30px;
      color: #fca5a5;
      font-size: 14px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      backdrop-filter: blur(12px);
    }
    .metric-value {
      font-family: 'Outfit', sans-serif;
      font-size: 32px;
      font-weight: 700;
      color: var(--danger);
      margin: 10px 0 5px 0;
      text-shadow: 0 0 10px rgba(239, 68, 68, 0.2);
    }
    .metric-title { font-size: 12px; font-weight: 600; color: var(--text-sub); text-transform: uppercase; }
    .table-container { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    th { padding: 12px 16px; border-bottom: 2px solid var(--border-color); color: var(--text-sub); font-size: 12px; text-transform: uppercase; }
    td { padding: 16px; border-bottom: 1px solid var(--border-color); font-size: 14px; }
    .badge-error {
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger);
      padding: 4px 8px;
      font-size: 11px;
      font-weight: 600;
      border-radius: 6px;
    }
    .badge-ok {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success);
      padding: 4px 8px;
      font-size: 11px;
      font-weight: 600;
      border-radius: 6px;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>🛡️ AML & KYC Regulatory Compliance Audit Summary</h1>
    <p class="subtitle">Compliance & Audit Division Quarterly Summary Report</p>
  </div>

  <div class="alert-banner">
    ⚠️ <strong>Action Required:</strong> 3 AML breach exceptions identified in the current billing cycle. Security patches pending approval.
  </div>
  
  <div class="grid">
    <div class="card">
      <div class="metric-title">Compliance Rating</div>
      <div class="metric-value" style="color: #10b981; text-shadow: 0 0 10px rgba(16,185,129,0.2)">98.4%</div>
      <span style="font-size: 12px; color: var(--text-sub)">Target threshold: >99.0%</span>
    </div>
    <div class="card">
      <div class="metric-title">Open Risk Exceptions</div>
      <div class="metric-value">3</div>
      <span style="font-size: 12px; color: var(--text-sub)">High severity incidents flagged</span>
    </div>
    <div class="card">
      <div class="metric-title">Last Audit Date</div>
      <div class="metric-value" style="color: #60a5fa; text-shadow: 0 0 10px rgba(96,165,250,0.2)">2026-05-28</div>
      <span style="font-size: 12px; color: var(--text-sub)">Cycle status: Completed</span>
    </div>
  </div>

  <div class="card">
    <h2 style="font-family: 'Outfit', sans-serif; font-size: 20px; margin-bottom: 20px; color: #fca5a5;">🔍 Audit Exceptions Ledger Details</h2>
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>Control ID</th>
            <th>Exception Type</th>
            <th>Incident Date</th>
            <th>Severity</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>CTRL-884</td>
            <td>AML Transaction Threshold Deviation</td>
            <td>2026-05-12</td>
            <td><span class="badge-error">High</span></td>
            <td>Investigation Pending</td>
          </tr>
          <tr>
            <td>CTRL-901</td>
            <td>KYC Document Expiry Audit Failure</td>
            <td>2026-05-18</td>
            <td><span class="badge-ok" style="background: rgba(245,158,11,0.15); color: var(--warning)">Medium</span></td>
            <td>Remediation In Progress</td>
          </tr>
          <tr>
            <td>CTRL-763</td>
            <td>Sanctions List Screening Mismatch</td>
            <td>2026-05-22</td>
            <td><span class="badge-error">High</span></td>
            <td>Bypassed/Approved by SME</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>"""

    # 3. Wealth Investment Outlook
    wealth_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Wealth Management Investment Outlook</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@500;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-gradient: linear-gradient(135deg, #022c22 0%, #064e3b 100%);
      --card-bg: rgba(6, 78, 59, 0.45);
      --border-color: rgba(255, 255, 255, 0.08);
      --text-main: #f0fdf4;
      --text-sub: #a7f3d0;
      --primary: #10b981;
      --primary-glow: rgba(16, 185, 129, 0.35);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg-gradient);
      color: var(--text-main);
      min-height: 100vh;
      padding: 30px;
    }
    .header {
      margin-bottom: 30px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 20px;
    }
    h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 28px;
      font-weight: 700;
      background: linear-gradient(135deg, #34d399 0%, #10b981 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 6px;
    }
    .subtitle { color: var(--text-sub); font-size: 14px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      backdrop-filter: blur(12px);
    }
    .metric-value {
      font-family: 'Outfit', sans-serif;
      font-size: 32px;
      font-weight: 700;
      color: #34d399;
      margin: 10px 0 5px 0;
      text-shadow: 0 0 10px var(--primary-glow);
    }
    .metric-title { font-size: 12px; font-weight: 600; color: var(--text-sub); text-transform: uppercase; }
  </style>
</head>
<body>
  <div class="header">
    <h1>📈 Wealth Management Quarterly Strategy & Portfolio Outlook</h1>
    <p class="subtitle">Advisory Team: Asset Allocation & Investment Strategy Briefing</p>
  </div>

  <div class="grid">
    <div class="card">
      <div class="metric-title">Portfolio Yield Objective</div>
      <div class="metric-value">6.85%</div>
      <span style="font-size: 12px; color: var(--text-sub)">Target net spread margin</span>
    </div>
    <div class="card">
      <div class="metric-title">Equities Allocation</div>
      <div class="metric-value" style="color: #60a5fa; text-shadow: 0 0 10px rgba(96,165,250,0.3)">60%</div>
      <span style="font-size: 12px; color: var(--text-sub)">Aggressive strategic growth</span>
    </div>
    <div class="card">
      <div class="metric-title">Fixed Income Target</div>
      <div class="metric-value" style="color: #fbbf24; text-shadow: 0 0 10px rgba(251,191,36,0.3)">40%</div>
      <span style="font-size: 12px; color: var(--text-sub)">Treasuries & AAA Corporate</span>
    </div>
  </div>

  <div class="card">
    <h2 style="font-family: 'Outfit', sans-serif; font-size: 20px; margin-bottom: 16px; color: #6ee7b7;">📋 Executive Summary Takeaways</h2>
    <p style="font-size: 14px; line-height: 1.6; color: var(--text-sub); margin-bottom: 12px;">
      1. Strategic overweight stance in enterprise technology sectors with a strong baseline in cybersecurity and generative AI ledgers.
    </p>
    <p style="font-size: 14px; line-height: 1.6; color: var(--text-sub); margin-bottom: 12px;">
      2. Yield curve stabilization allows re-entry to short-term AAA corporate debt brackets, increasing standard liquidity sweep return allocations.
    </p>
    <p style="font-size: 14px; line-height: 1.6; color: var(--text-sub);">
      3. Recommend regular periodic rebalancing across all customer advisory segments to limit credit default risk and control overall segment volatility.
    </p>
  </div>
</body>
</html>"""

    # Save to disk
    StorageClient().save_file(shared_dir, "treasury_liquidity_report.html", treasury_html)
    StorageClient().save_file(shared_dir, "compliance_audit_summary.html", compliance_html)
    StorageClient().save_file(shared_dir, "wealth_investment_outlook.html", wealth_html)
    print("[Dashboard Seeder] Seeding completed successfully.")
