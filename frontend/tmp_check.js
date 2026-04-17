
  /* ───────────────────────────────────────────────
      STATE
  ─────────────────────────────────────────────── */
  let API = 'http://localhost:8000';
  let USER_ID = '';

  const SMS_SAMPLES = [
    "INB:Your A/c XX4521 debited Rs.349.00 on 17-Apr-26 to VPA swiggy@icici. Avl Bal:Rs.12,450.50 -HDFC Bank",
    "Dear Customer, INB txn: Rs 2199.00 debited from A/c XX7831 to Amazon Seller on 17-Apr-26. Bal: Rs 8,201.00",
    "INB Alert: Rs 15,000.00 CREDITED to A/c XX3892 from RAZORPAY PAYMENTS on 17-Apr-26. Bal: Rs 23,450.00",
    "Acct XX5432: Rs.599.00 debited for AIRTEL RECHARGE on 17-Apr-26. Avl Bal Rs.5,832.10. -SBI Bank",
    "Your a/c XX1234 debited Rs.850.00 on 17-Apr-26 for PORTER LOGISTICS. Bal: Rs 9,150.00",
    "Salary Credited: Rs.45,000.00 credited to your account XX8891 on 17-Apr-26 from EMPLOYER. Bal Rs.48,200.00",
    "EMI alert: Rs.8,500.00 auto-debited from A/c XX5512 for HDFC Bank EMI on 17-Apr-26. Avl Bal Rs.3,200.00",
    "INB: AWS CLOUD SERVICES Rs.3,240.00 debited from A/c XX7743 on 17-Apr-26. Avl Bal Rs 14,560.00"
  ];

  /* ───────────────────────────────────────────────
      NAVIGATION
  ─────────────────────────────────────────────── */
  function navigate(page) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
    document.getElementById('section-' + page).classList.add('active');
    document.getElementById('nav-' + page).classList.add('active');

    // auto‑fill uid inputs
    const uidInputs = ['sms-uid','pdf-uid','txn-uid','ins-uid','act-uid','itc-uid','book-uid','fs-uid','tax-uid','rec-uid','audit-uid','sim-uid','comp-uid','reports-uid'];
    uidInputs.forEach(id => {
      const el = document.getElementById(id);
      if (el && !el.value && USER_ID) el.value = USER_ID;
    });
  }

  /* ───────────────────────────────────────────────
      CONFIG
  ─────────────────────────────────────────────── */
  function saveConfig() {
    API = document.getElementById('cfg-api-url').value.replace(/\/$/, '');
    USER_ID = document.getElementById('cfg-user-id').value.trim();
    document.getElementById('api-url-display').textContent = API;
    document.getElementById('m-uid').textContent = USER_ID || 'None';
    showToast('Config saved — testing connection…', 'success');
    checkHealthSilent();
  }

  /* ───────────────────────────────────────────────
      HEALTH
  ─────────────────────────────────────────────── */
  async function checkHealthSilent() {
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-text');
    const ms_el = document.getElementById('m-latency');
    const m_status = document.getElementById('m-status');
    try {
      const t0 = Date.now();
      const r = await fetch(API + '/health');
      const ms = Date.now() - t0;
      if (r.ok) {
        dot.className = 'dot online';
        txt.textContent = 'Online';
        if (ms_el) ms_el.textContent = ms + 'ms';
        if (m_status) m_status.textContent = '✅ OK';
      } else {
        throw new Error(r.status);
      }
    } catch {
      dot.className = 'dot offline';
      txt.textContent = 'Offline';
      if (ms_el) ms_el.textContent = '—';
      if (m_status) m_status.textContent = '❌ Down';
    }
  }

  async function checkHealth() {
    const panel = document.getElementById('health-response');
    const badge = document.getElementById('health-status-badge');
    panel.className = 'response-body';
    panel.textContent = 'Pinging…';
    badge.innerHTML = '';
    try {
      const t0 = Date.now();
      const r = await fetch(API + '/health');
      const ms = Date.now() - t0;
      const data = await r.json();
      badge.innerHTML = `<span class="status-code status-200">${r.status}</span>`;
      panel.textContent = JSON.stringify(data, null, 2) + '\n\n// Response time: ' + ms + 'ms';
      showToast('Backend is healthy ✅', 'success');
      document.getElementById('status-dot').className = 'dot online';
      document.getElementById('status-text').textContent = 'Online';
    } catch (e) {
      badge.innerHTML = `<span class="status-code status-5xx">Error</span>`;
      panel.textContent = 'Connection failed: ' + e.message + '\n\nMake sure the FastAPI server is running:\n  cd pocket-cfo-parser\n  uvicorn api.main:app --reload';
      showToast('Connection failed ❌', 'error');
      document.getElementById('status-dot').className = 'dot offline';
      document.getElementById('status-text').textContent = 'Offline';
    }
  }

  /* ───────────────────────────────────────────────
      CREATE USER
  ─────────────────────────────────────────────── */
  async function createUser() {
    const btn = document.getElementById('btn-create-user');
    const panel = document.getElementById('user-response');
    const badge = document.getElementById('user-status-badge');
    const payload = {
      name: document.getElementById('u-name').value.trim(),
      phone: document.getElementById('u-phone').value.trim(),
      business_name: document.getElementById('u-biz').value.trim()
    };
    if (!payload.name || !payload.phone || !payload.business_name) {
      showToast('Fill all fields first', 'error'); return;
    }
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Creating…';
    panel.className = 'response-body';
    panel.textContent = 'Sending request…';
    badge.innerHTML = '';
    try {
      const r = await fetch(API + '/users/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await r.json();
      badge.innerHTML = `<span class="status-code status-200">${r.status}</span>`;
      panel.textContent = JSON.stringify(data, null, 2);
      if (data.backend_user_id) {
        document.getElementById('uid-copy-card').style.display = 'block';
        document.getElementById('created-uid').value = data.backend_user_id;
        showToast('User created successfully!', 'success');
      }
    } catch (e) {
      badge.innerHTML = `<span class="status-code status-5xx">Error</span>`;
      panel.textContent = 'Error: ' + e.message;
      showToast('Request failed', 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '🚀 Create User';
    }
  }

  function fillDemoUser() {
    document.getElementById('u-name').value = 'Rajesh Kumar';
    document.getElementById('u-phone').value = '+919876543210';
    document.getElementById('u-biz').value = 'Kumar Electronics';
  }

  function copyUID() {
    const el = document.getElementById('created-uid');
    el.select();
    document.execCommand('copy');
    showToast('User ID copied!', 'success');
  }

  function useUID() {
    const uid = document.getElementById('created-uid').value;
    USER_ID = uid;
    document.getElementById('cfg-user-id').value = uid;
    document.getElementById('m-uid').textContent = uid;
    showToast('User ID set as active session', 'success');
  }

  /* ───────────────────────────────────────────────
      SMS INGEST
  ─────────────────────────────────────────────── */
  function loadSMS(idx) {
    document.getElementById('sms-text').value = SMS_SAMPLES[idx];
    if (!document.getElementById('sms-uid').value && USER_ID)
      document.getElementById('sms-uid').value = USER_ID;
  }

  function clearSMS() {
    document.getElementById('sms-text').value = '';
    document.getElementById('sms-response').className = 'response-placeholder';
    document.getElementById('sms-response').textContent = '☝️ Paste an SMS and hit Parse';
    document.getElementById('sms-parsed-card').style.display = 'none';
    document.getElementById('sms-status-badge').innerHTML = '';
  }

  async function ingestSMS() {
    const btn = document.getElementById('btn-sms');
    const panel = document.getElementById('sms-response');
    const badge = document.getElementById('sms-status-badge');
    const uid = document.getElementById('sms-uid').value.trim();
    const text = document.getElementById('sms-text').value.trim();
    if (!uid || !text) { showToast('Enter User ID and SMS text', 'error'); return; }
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Parsing…';
    panel.className = 'response-body';
    panel.textContent = 'Sending to agent…';
    badge.innerHTML = '';
    document.getElementById('sms-parsed-card').style.display = 'none';
    try {
      const r = await fetch(API + '/ingest/sms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: uid, text })
      });
      const data = await r.json();
      badge.innerHTML = `<span class="status-code status-200">${r.status}</span>`;
      panel.textContent = JSON.stringify(data, null, 2);
      if (data.amount !== undefined) {
        renderParsedTransaction(data);
        showToast('SMS parsed successfully!', 'success');
      } else if (data.status === 'skipped') {
        showToast('Non-transactional SMS — skipped', 'error');
      }
    } catch (e) {
      badge.innerHTML = `<span class="status-code status-5xx">Error</span>`;
      panel.textContent = 'Error: ' + e.message;
      showToast('Request failed', 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '⚡ Parse SMS';
    }
  }

  function renderParsedTransaction(t) {
    const card = document.getElementById('sms-parsed-card');
    const vis = document.getElementById('sms-parsed-visual');
    const conf = Math.round((t.confidence || 0) * 100);
    const confColor = conf >= 80 ? 'var(--emerald)' : conf >= 50 ? 'var(--amber)' : 'var(--rose)';
    vis.innerHTML = `
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">Party</div>
          <div style="font-family:'Syne',sans-serif; font-size:1.1rem; font-weight:700; margin-top:2px;">${t.party || '—'}</div>
        </div>
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">Amount</div>
          <div style="font-family:'Syne',sans-serif; font-size:1.1rem; font-weight:700; color:${t.type==='credit'?'var(--emerald)':'var(--rose)'}; margin-top:2px;">
            ${t.type==='credit'?'+':'-'}₹${(t.amount||0).toLocaleString('en-IN')}
          </div>
        </div>
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">Category</div>
          <div style="margin-top:2px;">${t.category || '—'}</div>
        </div>
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">Date</div>
          <div style="font-family:'DM Mono',monospace; font-size:0.85rem; margin-top:2px;">${t.date || '—'}</div>
        </div>
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">Source</div>
          <div style="margin-top:2px;">${t.source || 'sms'}</div>
        </div>
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">Confidence</div>
          <div style="display:flex; align-items:center; gap:8px; margin-top:4px;">
            <div class="conf-bar" style="width:80px;"><div class="conf-fill" style="width:${conf}%; background:${confColor};"></div></div>
            <span style="font-size:0.8rem; color:${confColor}; font-weight:600;">${conf}%</span>
          </div>
        </div>
      </div>`;
    card.style.display = 'block';
  }

  /* ───────────────────────────────────────────────
      PDF INGEST
  ─────────────────────────────────────────────── */
  async function ingestPDF() {
    const btn = document.getElementById('btn-pdf');
    const panel = document.getElementById('pdf-response');
    const badge = document.getElementById('pdf-status-badge');
    const uid = document.getElementById('pdf-uid').value.trim();
    const file = document.getElementById('pdf-file').files[0];
    if (!uid || !file) { showToast('Select a file and enter User ID', 'error'); return; }
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Uploading…';
    panel.className = 'response-body';
    panel.textContent = 'Uploading and parsing…';
    badge.innerHTML = '';
    try {
      const form = new FormData();
      form.append('user_id', uid);
      form.append('file', file);
      const r = await fetch(API + '/ingest/pdf', { method: 'POST', body: form });
      const data = await r.json();
      badge.innerHTML = `<span class="status-code status-200">${r.status}</span>`;
      panel.textContent = JSON.stringify(data, null, 2);
      showToast(`Extracted ${data.count || 0} transactions!`, 'success');
    } catch (e) {
      badge.innerHTML = `<span class="status-code status-5xx">Error</span>`;
      panel.textContent = 'Error: ' + e.message;
      showToast('Upload failed', 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '📤 Upload & Parse';
    }
  }

  /* ───────────────────────────────────────────────
      TRANSACTIONS
  ─────────────────────────────────────────────── */
  let allTxns = [];

  async function fetchTransactions() {
    const uid = document.getElementById('txn-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    document.getElementById('txn-tbody').innerHTML = `<tr><td colspan="7"><div class="empty-state">⏳ Fetching transactions…</div></td></tr>`;
    try {
      const r = await fetch(API + '/transactions/' + uid);
      const data = await r.json();
      allTxns = data.transactions || [];
      renderTxnMetrics(allTxns);
      filterTable();
      showToast(`Loaded ${allTxns.length} transactions`, 'success');
    } catch (e) {
      document.getElementById('txn-tbody').innerHTML = `<tr><td colspan="7"><div class="empty-state">❌ ${e.message}</div></td></tr>`;
      showToast('Failed to fetch', 'error');
    }
  }

  function renderTxnMetrics(txns) {
    const credits = txns.filter(t => t.type === 'credit');
    const debits = txns.filter(t => t.type === 'debit');
    const totalCredit = credits.reduce((s, t) => s + (t.amount || 0), 0);
    const totalDebit = debits.reduce((s, t) => s + (t.amount || 0), 0);
    const el = document.getElementById('txn-metrics');
    el.style.display = 'grid';
    el.innerHTML = `
      <div class="metric-card emerald"><div class="metric-label">Total Credits</div><div class="metric-value">₹${totalCredit.toLocaleString('en-IN', {maximumFractionDigits:0})}</div><div class="metric-sub">${credits.length} transactions</div></div>
      <div class="metric-card rose"><div class="metric-label">Total Debits</div><div class="metric-value">₹${totalDebit.toLocaleString('en-IN', {maximumFractionDigits:0})}</div><div class="metric-sub">${debits.length} transactions</div></div>
      <div class="metric-card amber"><div class="metric-label">Net Flow</div><div class="metric-value" style="color:${(totalCredit-totalDebit)>=0?'var(--emerald)':'var(--rose)'}">₹${Math.abs(totalCredit-totalDebit).toLocaleString('en-IN', {maximumFractionDigits:0})}</div><div class="metric-sub">${(totalCredit-totalDebit)>=0?'Positive':'Negative'}</div></div>
      <div class="metric-card indigo"><div class="metric-label">Total Entries</div><div class="metric-value">${txns.length}</div><div class="metric-sub">In the ledger</div></div>`;
  }

  function filterTable() {
    const filter = document.getElementById('txn-filter').value;
    const search = (document.getElementById('txn-search').value || '').toLowerCase();
    const filtered = allTxns.filter(t => {
      const typeMatch = filter === 'all' || t.type === filter;
      const searchMatch = !search || (t.party || '').toLowerCase().includes(search);
      return typeMatch && searchMatch;
    });
    renderTxnTable(filtered);
  }

  function renderTxnTable(txns) {
    const tbody = document.getElementById('txn-tbody');
    if (!txns.length) {
      tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="icon">📭</div>No transactions match your filter</div></td></tr>`;
      return;
    }
    tbody.innerHTML = txns.map(t => {
      const conf = Math.round((t.confidence || 0) * 100);
      const confColor = conf >= 80 ? 'var(--emerald)' : conf >= 50 ? 'var(--amber)' : 'var(--rose)';
      const confBadge = conf >= 70 ? 'high' : conf >= 40 ? 'med' : 'low';
      return `<tr>
        <td class="text-mono">${t.date || '—'}</td>
        <td style="font-weight:500;">${t.party || 'Unknown'}</td>
        <td style="font-family:'DM Mono',monospace; color:${t.type==='credit'?'var(--emerald)':'var(--rose)'};">
          ${t.type==='credit'?'+':'-'}₹${(t.amount||0).toLocaleString('en-IN')}
        </td>
        <td><span class="badge badge-${t.type}">${t.type}</span></td>
        <td>${t.category || 'Uncategorized'}</td>
        <td class="text-muted">${t.source || '—'}</td>
        <td>
          <div style="display:flex; align-items:center; gap:6px;">
            <div class="conf-bar"><div class="conf-fill" style="width:${conf}%; background:${confColor};"></div></div>
            <span class="badge badge-${confBadge}" style="font-size:0.65rem;">${conf}%</span>
          </div>
        </td>
      </tr>`;
    }).join('');
  }

  /* ───────────────────────────────────────────────
      INSIGHTS (COMBINED)
  ─────────────────────────────────────────────── */
  async function fetchInsights() {
    const uid = document.getElementById('ins-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    document.getElementById('insights-grid').style.display = 'none';
    try {
      const r = await fetch(API + '/insights/' + uid);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const expenseSummary = data.expense_summary || data.top_expense_categories || {};
      const profitSummary = data.profit_summary || data.financial_overview || {};
      renderExpenseSummary(expenseSummary, 'expense-content');
      renderProfitSummary(profitSummary, 'profit-content');
      renderTrendSummary(data, allTxns);
      document.getElementById('insights-raw').textContent = JSON.stringify(data, null, 2);
      document.getElementById('insights-grid').style.display = 'grid';
      showToast('Insights loaded from agents', 'success');
    } catch (e) {
      showToast('Failed: ' + e.message, 'error');
    }
  }

  /* ───────────────────────────────────────────────
      EXPENSE AGENT
  ─────────────────────────────────────────────── */
  async function fetchExpenseAgent() {
    const uid = document.getElementById('exp-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    document.getElementById('exp-grid').style.display = 'none';
    document.getElementById('exp-metrics').style.display = 'none';
    try {
      const r = await fetch(API + '/expenses/' + uid);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const categories = data.categories || data.by_category || {};
      
      const total = data.total_expenses || 0;
      const count = data.transaction_count || Object.values(categories).reduce((sum, cat) => sum + (cat.transaction_count || 0), 0);
      const top = data.top_category || 'None';
      const anomCount = data.anomaly_count || 0;
      
      document.getElementById('exp-metrics').style.display = 'grid';
      document.getElementById('exp-metrics').innerHTML = `
        <div class="metric-card rose"><div class="metric-label">Total Spent</div><div class="metric-value">₹${total.toLocaleString('en-IN')}</div><div class="metric-sub">${count} transactions</div></div>
        <div class="metric-card amber"><div class="metric-label">Top Category</div><div class="metric-value" style="font-size:1.4rem;">${top}</div><div class="metric-sub">Highest outflow</div></div>
        <div class="metric-card ${anomCount>0?'rose':'emerald'}"><div class="metric-label">Anomalies</div><div class="metric-value">${anomCount}</div><div class="metric-sub">${anomCount>0?'Outliers detected':'Normal spending'}</div></div>
        <div class="metric-card indigo" style="grid-column: span 1;"><div class="metric-label">Agent Insight</div><div style="font-size:0.85rem; line-height:1.4; margin-top:8px;">${data.insight}</div></div>
      `;
      
      renderExpenseSummary({ ...data, by_category: categories }, 'exp-categories');
      
      const anomEl = document.getElementById('exp-anomalies');
      if (anomCount === 0) {
        anomEl.innerHTML = '<div class="empty-state"><div class="icon">✅</div>No spending anomalies detected</div>';
      } else {
        anomEl.innerHTML = (data.anomalies || []).map(a => `
          <div class="action-card red">
            <div class="action-priority">🔴 OUTLIER: ${a.category}</div>
            <div class="action-title">${a.transaction.party} — ₹${a.transaction.amount.toLocaleString()}</div>
            <div class="action-msg">${a.anomaly_reason}</div>
          </div>
        `).join('');
      }
      
      document.getElementById('exp-raw').textContent = JSON.stringify(data, null, 2);
      document.getElementById('exp-grid').style.display = 'grid';
      showToast('Expense agent completed', 'success');
    } catch (e) {
      showToast('Expense agent failed: ' + e.message, 'error');
    }
  }

  /* ───────────────────────────────────────────────
      PROFIT AGENT
  ─────────────────────────────────────────────── */
  async function fetchProfitAgent() {
    const uid = document.getElementById('pro-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    document.getElementById('pro-grid').style.display = 'none';
    document.getElementById('pro-metrics').style.display = 'none';
    try {
      const r = await fetch(API + '/profit/' + uid);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const overall = data.overall || data;
      const rev = overall.total_revenue || 0;
      const exp = overall.total_expenses || 0;
      const net = overall.net_profit || 0;
      const itc = overall.total_itc_claimable || 0;
      const effectiveTaxRate = overall.total_expenses > 0 ? ((overall.total_gst_paid || 0) / overall.total_expenses) * 100 : 0;
      const itcTip = itc > 0
        ? `You can recover ₹${itc.toLocaleString('en-IN', { maximumFractionDigits: 2 })} through ITC.`
        : 'No major ITC opportunity identified in current dataset.';
      
      document.getElementById('pro-metrics').style.display = 'grid';
      document.getElementById('pro-metrics').innerHTML = `
        <div class="metric-card emerald"><div class="metric-label">Revenue</div><div class="metric-value">₹${rev.toLocaleString('en-IN')}</div><div class="metric-sub">${overall.revenue_transactions || 0} credits</div></div>
        <div class="metric-card rose"><div class="metric-label">Expenses</div><div class="metric-value">₹${exp.toLocaleString('en-IN')}</div><div class="metric-sub">${overall.expense_transactions || 0} debits</div></div>
        <div class="metric-card amber"><div class="metric-label">ITC Recovery</div><div class="metric-value">₹${itc.toLocaleString('en-IN')}</div><div class="metric-sub">Claimable Input Tax</div></div>
        <div class="metric-card ${net>=0?'emerald':'rose'}"><div class="metric-label">Net Profit</div><div class="metric-value">₹${Math.abs(net).toLocaleString('en-IN')}</div><div class="metric-sub">${net>=0?'Profitable':'Operating at a loss'}</div></div>
      `;
      
      renderProfitSummary(overall, 'pro-breakdown');
      
      document.getElementById('pro-gst').innerHTML = `
        <div class="insight-row"><b>Total GST Paid</b><b style="color:var(--rose);">₹${(overall.total_gst_paid || 0).toLocaleString('en-IN')}</b></div>
        <div class="insight-row"><b>Claimable ITC</b><b style="color:var(--emerald);">₹${itc.toLocaleString('en-IN')}</b></div>
        <div class="insight-row"><span>Effective Tax Rate</span><span class="text-mono">${effectiveTaxRate.toFixed(1)}%</span></div>
        <div class="action-card ${itc>0?'green':'amber'} mt-2" style="border:none;">
          <div class="action-priority">Agent Verdict</div>
          <div class="action-msg">${itcTip}</div>
        </div>
      `;
      
      document.getElementById('pro-raw').textContent = JSON.stringify(data, null, 2);
      document.getElementById('pro-grid').style.display = 'grid';
      showToast('Profit agent completed', 'success');
    } catch (e) {
      showToast('Profit agent failed: ' + e.message, 'error');
    }
  }

  async function fetchBookkeeping() {
    const uid = document.getElementById('book-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    document.getElementById('book-grid').style.display = 'none';
    document.getElementById('book-metrics').style.display = 'none';
    try {
      const r = await fetch(API + '/bookkeeping/' + uid);
      const data = await r.json();
      const summary = data.bookkeeping_summary?.balance_summary || {};

      document.getElementById('book-metrics').style.display = 'grid';
      document.getElementById('book-metrics').innerHTML = `
        <div class="metric-card emerald"><div class="metric-label">Credits</div><div class="metric-value">₹${(summary.total_credits || 0).toLocaleString('en-IN')}</div><div class="metric-sub">Total inflow</div></div>
        <div class="metric-card rose"><div class="metric-label">Debits</div><div class="metric-value">₹${(summary.total_debits || 0).toLocaleString('en-IN')}</div><div class="metric-sub">Total outflow</div></div>
        <div class="metric-card amber"><div class="metric-label">ITC Claimable</div><div class="metric-value">₹${(summary.total_itc_claimable || 0).toLocaleString('en-IN')}</div><div class="metric-sub">Potential recovery</div></div>
        <div class="metric-card indigo"><div class="metric-label">Net Cash Flow</div><div class="metric-value">₹${(summary.net_cash_flow || 0).toLocaleString('en-IN')}</div><div class="metric-sub">Including ITC</div></div>
      `;

      document.getElementById('book-summary').innerHTML = `
        <div class="insight-row"><b>Transactions</b><b>${summary.transaction_count || 0}</b></div>
        <div class="insight-row"><span>Uncategorized</span><span>${summary.uncategorized_count || 0}</span></div>
        <div class="insight-row"><span>Low confidence</span><span>${summary.low_confidence_count || 0}</span></div>
        <div class="insight-row"><span>GST Efficiency</span><span>${summary.gst_efficiency || 0}%</span></div>
        <div class="insight-row"><span>Top categories</span><span>${Object.keys(summary.category_counts || {}).slice(0,3).join(', ') || 'None'}</span></div>
      `;

      // Add detailed breakdowns
      const detailedHtml = `
        <div class="book-details">
          <div class="detail-section">
            <h4>Business vs Personal Breakdown</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <span>Business Credits</span>
                <span>₹${(summary.business_vs_personal?.business_credits || 0).toLocaleString('en-IN')}</span>
              </div>
              <div class="detail-item">
                <span>Business Debits</span>
                <span>₹${(summary.business_vs_personal?.business_debits || 0).toLocaleString('en-IN')}</span>
              </div>
              <div class="detail-item">
                <span>Personal Credits</span>
                <span>₹${(summary.business_vs_personal?.personal_credits || 0).toLocaleString('en-IN')}</span>
              </div>
              <div class="detail-item">
                <span>Personal Debits</span>
                <span>₹${(summary.business_vs_personal?.personal_debits || 0).toLocaleString('en-IN')}</span>
              </div>
            </div>
          </div>

          ${summary.gst_rate_breakdown && Object.keys(summary.gst_rate_breakdown).length > 0 ? `
            <div class="detail-section">
              <h4>GST Rate Breakdown</h4>
              <div class="detail-grid">
                ${Object.entries(summary.gst_rate_breakdown).map(([rate, amount]) => `
                  <div class="detail-item">
                    <span>${rate} GST</span>
                    <span>₹${amount.toLocaleString('en-IN')}</span>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}

          ${summary.monthly_trends && summary.monthly_trends.length > 0 ? `
            <div class="detail-section">
              <h4>Monthly Trends</h4>
              <div class="monthly-trends">
                ${summary.monthly_trends.slice(-6).map(month => `
                  <div class="month-item">
                    <span>${month.month}</span>
                    <div class="month-details">
                      <span>In: ₹${month.credits.toLocaleString('en-IN')}</span>
                      <span>Out: ₹${month.debits.toLocaleString('en-IN')}</span>
                      <span>Net: ₹${month.net.toLocaleString('en-IN')}</span>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}

          ${summary.largest_parties && summary.largest_parties.length > 0 ? `
            <div class="detail-section">
              <h4>Top Transaction Parties</h4>
              <div class="parties-list">
                ${summary.largest_parties.slice(0,8).map(party => `
                  <div class="party-item">
                    <span>${party.party}</span>
                    <span>${party.count} transactions</span>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      `;

      // Insert detailed breakdown before the notes
      const notesElement = document.getElementById('book-notes');
      notesElement.insertAdjacentHTML('beforebegin', detailedHtml);

      const notes = data.bookkeeping_summary?.recommendations || [];
      const suggestions = summary.suggestions || [];
      const actionItems = summary.action_items || [];
      const insights = summary.insights || [];

      const allNotes = [...notes, ...suggestions.map(s => s.message), ...actionItems.map(a => a.message), ...insights];
      document.getElementById('book-notes').innerHTML = allNotes.length ? allNotes.map(n => `<div class="action-card amber"><div class="action-msg">${n}</div></div>`).join('') : '<div class="empty-state">No bookkeeping notes generated</div>';
      document.getElementById('book-raw').textContent = JSON.stringify(data, null, 2);
      document.getElementById('book-grid').style.display = 'grid';
      showToast('Bookkeeping summary loaded', 'success');
    } catch (e) {
      showToast('Bookkeeping fetch failed: ' + e.message, 'error');
    }
  }

  function renderExpenseSummary(exp, targetId = 'expense-content') {
    const el = document.getElementById(targetId);
    if (!exp || !Object.keys(exp).length) { el.innerHTML = '<div class="empty-state">No expense data yet</div>'; return; }
    const cats = exp.by_category || exp.categories || {};
    const total = exp.total_expenses || 0;
    const catRows = Object.entries(cats).map(([k, v]) => {
      const amount = typeof v === 'number' ? v : (v.total_spent || 0);
      const pct = total > 0 ? Math.round((amount / total) * 100) : 0;
      return `<div class="insight-row">
        <div>${k}</div>
        <div style="display:flex; align-items:center; gap:10px;">
          <div class="progress-bar"><div class="progress-fill" style="width:${pct}%; background:var(--amber);"></div></div>
          <span class="text-mono" style="color:var(--amber);">₹${amount.toLocaleString('en-IN', {maximumFractionDigits:0})}</span>
        </div>
      </div>`;
    }).join('');
    el.innerHTML = `
      <div class="insight-row">
        <b>Total Expenses</b>
        <b style="color:var(--rose);">₹${total.toLocaleString('en-IN', {maximumFractionDigits:0})}</b>
      </div>
      ${catRows}
      <div class="insight-row" style="margin-top:8px;">
        <span class="text-muted">Anomalies flagged</span>
        <span>${(exp.anomalies || []).length}</span>
      </div>`;
  }

  function renderProfitSummary(pro, targetId = 'profit-content') {
    const el = document.getElementById(targetId);
    if (!pro || !Object.keys(pro).length) { el.innerHTML = '<div class="empty-state">No profit data yet</div>'; return; }
    const netColor = (pro.net_profit || 0) >= 0 ? 'var(--emerald)' : 'var(--rose)';
    el.innerHTML = `
      <div class="insight-row"><b>Total Revenue</b><b style="color:var(--emerald);">₹${(pro.total_revenue||0).toLocaleString('en-IN',{maximumFractionDigits:0})}</b></div>
      <div class="insight-row"><span>Total Expenses</span><span style="color:var(--rose);">₹${(pro.total_expenses||0).toLocaleString('en-IN',{maximumFractionDigits:0})}</span></div>
      <div class="insight-row">
        <b>Net Profit</b>
        <b style="color:${netColor}; font-size:1.1rem; font-family:'Syne',sans-serif;">
          ${(pro.net_profit||0)>=0?'▲':'▼'} ₹${Math.abs(pro.net_profit||0).toLocaleString('en-IN',{maximumFractionDigits:0})}
        </b>
      </div>
      <div class="insight-row"><span>Profit Margin</span><span style="color:${netColor};">${(pro.profit_margin || pro.profit_margin_percent || 0).toFixed(1)}%</span></div>
      <div class="insight-row"><span class="text-muted">Summary</span></div>
      <div style="font-size:0.82rem; color:var(--muted); margin-top:4px; line-height:1.5;">${pro.summary || pro.verdict || '—'}</div>`;
  }

  function formatCurrency(v) {
    return `₹${Number(v || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  }

  function safeNum(v, fallback = 0) {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
  }

  function renderTrendSummary(insightData, txns = []) {
    const el = document.getElementById('trend-content');
    if (!el) return;
    const transactions = Array.isArray(txns) ? txns : [];
    const debits = transactions.filter(t => t.type === 'debit');
    const monthly = {};
    debits.forEach(t => {
      const d = new Date(t.date);
      if (Number.isNaN(d.getTime())) return;
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      monthly[key] = (monthly[key] || 0) + Number(t.amount || 0);
    });
    const monthEntries = Object.entries(monthly).sort((a, b) => a[0].localeCompare(b[0])).slice(-6);
    const maxMonthSpend = Math.max(...monthEntries.map(([, amt]) => amt), 1);

    const topCats = Object.entries((insightData && insightData.top_expense_categories) || {})
      .sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0))
      .slice(0, 5);
    const maxCatSpend = Math.max(...topCats.map(([, amt]) => Number(amt || 0)), 1);

    if (!monthEntries.length && !topCats.length) {
      el.innerHTML = '<div class="empty-state"><div class="icon">📉</div>Not enough data for trend analytics yet</div>';
      return;
    }

    const monthBars = monthEntries.map(([month, amt]) => {
      const pct = Math.max(8, Math.round((amt / maxMonthSpend) * 100));
      return `<div class="insight-row">
        <span>${month}</span>
        <div style="display:flex; align-items:center; gap:8px; flex:1; justify-content:flex-end;">
          <div class="progress-bar" style="max-width:220px;"><div class="progress-fill" style="width:${pct}%; background:var(--sky);"></div></div>
          <span class="text-mono">${formatCurrency(amt)}</span>
        </div>
      </div>`;
    }).join('');

    const catBars = topCats.map(([cat, amt]) => {
      const nAmt = Number(amt || 0);
      const pct = Math.max(8, Math.round((nAmt / maxCatSpend) * 100));
      return `<div class="insight-row">
        <span>${cat}</span>
        <div style="display:flex; align-items:center; gap:8px; flex:1; justify-content:flex-end;">
          <div class="progress-bar" style="max-width:220px;"><div class="progress-fill" style="width:${pct}%; background:var(--amber);"></div></div>
          <span class="text-mono">${formatCurrency(nAmt)}</span>
        </div>
      </div>`;
    }).join('');

    el.innerHTML = `
      <div class="grid-2">
        <div>
          <div class="card-title"><span class="icon">📆</span> Month-over-Month Expense Trend</div>
          ${monthBars || '<div class="text-muted">No monthly debit data</div>'}
        </div>
        <div>
          <div class="card-title"><span class="icon">🕳️</span> Top Expense Leak Categories</div>
          ${catBars || '<div class="text-muted">No category data</div>'}
        </div>
      </div>`;
  }

  async function seedDemoForCurrentUser() {
    const uid = (document.getElementById('cfg-user-id').value.trim() || USER_ID || '').trim();
    if (!uid) { showToast('Set a User ID in Configuration first', 'error'); return; }
    try {
      const r = await fetch(`${API}/seed/demo/${uid}?months=6`, { method: 'POST' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      USER_ID = uid;
      document.getElementById('cfg-user-id').value = uid;
      showToast(`Seeded ${data.seeded_transactions || 0} transactions`, 'success');
    } catch (e) {
      showToast('Seeding failed: ' + e.message, 'error');
    }
  }

  async function runFullDemoJourney() {
    const uid = (document.getElementById('cfg-user-id').value.trim() || USER_ID || '').trim();
    if (!uid) { showToast('Set a User ID in Configuration first', 'error'); return; }
    USER_ID = uid;
    document.getElementById('m-uid').textContent = uid;

    try {
      showToast('Seeding demo data…', 'success');
      const seedResp = await fetch(`${API}/seed/demo/${uid}?months=6`, { method: 'POST' });
      if (!seedResp.ok) throw new Error(`Seed failed: HTTP ${seedResp.status}`);

      document.getElementById('txn-uid').value = uid;
      document.getElementById('ins-uid').value = uid;
      document.getElementById('act-uid').value = uid;
      document.getElementById('tax-uid').value = uid;
      document.getElementById('rec-uid').value = uid;
      document.getElementById('audit-uid').value = uid;
      document.getElementById('sim-uid').value = uid;

      await fetchTransactions();
      await fetchInsights();
      await fetchActions();
      await fetchIncomeTax();
      await fetchReconciliation();
      await fetchAudit();
      navigate('actions');
      showToast('Full demo journey is ready', 'success');
    } catch (e) {
      showToast('Demo journey failed: ' + e.message, 'error');
    }
  }

  async function downloadCABrief() {
    const uid = (document.getElementById('cfg-user-id').value.trim() || USER_ID || '').trim();
    if (!uid) { showToast('Set a User ID in Configuration first', 'error'); return; }
    try {
      const r = await fetch(`${API}/ca-summary/${uid}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const s = data.summary || {};
      const brief = [
        'POCKET CFO - CA BRIEF',
        `User ID: ${uid}`,
        `Generated: ${(new Date()).toISOString()}`,
        '',
        'KEY METRICS',
        `- Net Profit: ${formatCurrency(s.net_profit)}`,
        `- Revenue: ${formatCurrency(s.total_revenue)}`,
        `- Expenses: ${formatCurrency(s.total_expenses)}`,
        `- Profit Margin: ${Number(s.profit_margin || 0).toFixed(2)}%`,
        `- Potential Monthly Savings: ${formatCurrency(s.potential_monthly_savings)}`,
        `- GST Payable: ${formatCurrency(s.gst_payable)}`,
        `- Refund Available: ${formatCurrency(s.refund_available)}`,
        '',
        'ACTION FOCUS',
        ...(Array.isArray(data.action_items) && data.action_items.length
          ? data.action_items.map((item, i) => `${i + 1}. ${item}`)
          : ['1. No high-priority actions currently flagged.']),
        '',
        'Generated by Pocket CFO Agent'
      ].join('\n');

      const blob = new Blob([brief], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ca-brief-${uid}.txt`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast('CA brief downloaded', 'success');
    } catch (e) {
      showToast('Failed to download CA brief: ' + e.message, 'error');
    }
  }

  /* ───────────────────────────────────────────────
      ACTIONS
  ─────────────────────────────────────────────── */
  async function fetchActions() {
    const uid = document.getElementById('act-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    document.getElementById('actions-list').innerHTML = '<div class="empty-state">⏳ Running all agents…</div>';
    try {
      const r = await fetch(API + '/actions/' + uid);
      const data = await r.json();
      const actions = data.actions || [];
      const red = actions.filter(a => a.priority === 'red');
      const amber = actions.filter(a => a.priority === 'amber');
      const green = actions.filter(a => a.priority === 'green');
      document.getElementById('act-red-count').textContent = red.length;
      document.getElementById('act-amber-count').textContent = amber.length;
      document.getElementById('act-green-count').textContent = green.length;
      document.getElementById('action-summary-row').style.display = 'grid';

      if (!actions.length) {
        document.getElementById('actions-list').innerHTML = '<div class="empty-state"><div class="icon">🎉</div>No alerts — everything looks good!</div>';
        return;
      }
      const sorted = [...red, ...amber, ...green];
      document.getElementById('actions-list').innerHTML = sorted.map(a => `
        <div class="action-card ${a.priority}">
          <div class="action-priority">${a.priority === 'red' ? '🔴 CRITICAL' : a.priority === 'amber' ? '🟡 WARNING' : '🟢 OPPORTUNITY'}</div>
          <div class="action-title">${a.title}</div>
          <div class="action-msg">${a.message}</div>
          ${a.amount != null ? `<div class="action-amount">₹${Number(a.amount).toLocaleString('en-IN', {maximumFractionDigits:2})}</div>` : ''}
        </div>`).join('');
      showToast(`${actions.length} action cards generated`, 'success');
    } catch (e) {
      document.getElementById('actions-list').innerHTML = `<div class="empty-state">❌ ${e.message}</div>`;
      showToast('Failed: ' + e.message, 'error');
    }
  }

  /* ───────────────────────────────────────────────
      GST CLASSIFIER
  ─────────────────────────────────────────────── */
  function loadMerchant(party, amount) {
    document.getElementById('gst-party').value = party;
    document.getElementById('gst-amount').value = amount;
  }

  async function classifyGST() {
    const party = document.getElementById('gst-party').value.trim();
    const amount = parseFloat(document.getElementById('gst-amount').value) || 1000;
    const type = document.getElementById('gst-type').value;
    if (!party) { showToast('Enter a merchant name', 'error'); return; }

    const panel = document.getElementById('gst-response');
    const badge = document.getElementById('gst-status-badge');
    panel.className = 'response-body';
    panel.textContent = 'Sending single transaction to /ingest/sms for GST classification preview…';
    badge.innerHTML = '';
    document.getElementById('gst-result-card').style.display = 'none';

    // We test via the GST agent logic by ingesting a synthetic SMS
    const syntheticSMS = `Dear Customer, A/c XX1234 ${type==='debit'?'debited':'credited'} Rs.${amount} on 17-Apr-26 to/from ${party}. Avl Bal Rs.10000`;
    const uid = USER_ID || 'test-gst-user';

    try {
      const r = await fetch(API + '/ingest/sms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: uid, text: syntheticSMS })
      });
      const data = await r.json();
      badge.innerHTML = `<span class="status-code status-200">${r.status}</span>`;
      panel.textContent = JSON.stringify(data, null, 2);

      // Display a local GST classification result based on known rules
      renderGSTResult(party, amount, type);
      showToast('GST classification complete', 'success');
    } catch (e) {
      badge.innerHTML = `<span class="status-code status-5xx">Error</span>`;
      panel.textContent = 'Error: ' + e.message + '\n\nShowing local rule-based classification below:';
      renderGSTResult(party, amount, type);
      showToast('API error — showing local classification', 'error');
    }
  }

  const GST_RULES_CLIENT = {
    swiggy: { gst_rate: 5, hsn_sac: '9963', itc_eligible: false, category: 'Food & Beverage' },
    zomato: { gst_rate: 5, hsn_sac: '9963', itc_eligible: false, category: 'Food & Beverage' },
    amazon: { gst_rate: 18, hsn_sac: '9961', itc_eligible: true, category: 'Retail & E-commerce' },
    flipkart: { gst_rate: 18, hsn_sac: '9961', itc_eligible: true, category: 'Retail & E-commerce' },
    porter: { gst_rate: 18, hsn_sac: '9967', itc_eligible: true, category: 'Logistics' },
    delhivery: { gst_rate: 18, hsn_sac: '9967', itc_eligible: true, category: 'Logistics' },
    airtel: { gst_rate: 18, hsn_sac: '9984', itc_eligible: true, category: 'Telecommunications' },
    jio: { gst_rate: 18, hsn_sac: '9984', itc_eligible: true, category: 'Telecommunications' },
    uber: { gst_rate: 5, hsn_sac: '9964', itc_eligible: false, category: 'Transport' },
    ola: { gst_rate: 5, hsn_sac: '9964', itc_eligible: false, category: 'Transport' },
    razorpay: { gst_rate: 18, hsn_sac: '9971', itc_eligible: true, category: 'Payments & Fintech' },
    paytm: { gst_rate: 18, hsn_sac: '9971', itc_eligible: true, category: 'Payments & Fintech' },
    aws: { gst_rate: 18, hsn_sac: '9984', itc_eligible: true, category: 'Telecom & Cloud' },
    google: { gst_rate: 18, hsn_sac: '9984', itc_eligible: true, category: 'Telecom & Cloud' },
    microsoft: { gst_rate: 18, hsn_sac: '9984', itc_eligible: true, category: 'Telecom & Cloud' },
    hpcl: { gst_rate: 0, hsn_sac: 'EXEMPT', itc_eligible: false, category: 'Fuel' },
    bpcl: { gst_rate: 0, hsn_sac: 'EXEMPT', itc_eligible: false, category: 'Fuel' },
    petrol: { gst_rate: 0, hsn_sac: 'EXEMPT', itc_eligible: false, category: 'Fuel' },
    salary: { gst_rate: 0, hsn_sac: 'EXEMPT', itc_eligible: false, category: 'Payroll' },
    rent: { gst_rate: 18, hsn_sac: '9972', itc_eligible: true, category: 'Rent & Real Estate' },
  };

  function renderGSTResult(party, amount, type) {
    const partyLower = party.toLowerCase();
    let rule = null;
    for (const [key, val] of Object.entries(GST_RULES_CLIENT)) {
      if (partyLower.includes(key)) { rule = { ...val, matched_rule: key, confidence: 0.9 }; break; }
    }
    if (!rule) rule = { gst_rate: 18, hsn_sac: 'UNKNOWN', itc_eligible: false, category: 'Uncategorized', matched_rule: 'gemini-fallback', confidence: 0.7 };

    const gst_amount = (amount * rule.gst_rate / (100 + rule.gst_rate)).toFixed(2);
    const itc_amount = rule.itc_eligible ? gst_amount : '0.00';
    const source = rule.matched_rule === 'gemini-fallback' ? '🤖 Gemini AI Fallback' : '📖 Deterministic Rules Engine';

    document.getElementById('gst-result-visual').innerHTML = `
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem;">
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">Category</div>
          <div style="font-weight:600; margin-top:2px;">${rule.category}</div>
        </div>
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">HSN/SAC Code</div>
          <div style="font-family:'DM Mono',monospace; font-size:0.9rem; margin-top:2px; color:var(--sky);">${rule.hsn_sac}</div>
        </div>
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">GST Rate</div>
          <div style="font-size:1.2rem; font-family:'Syne',sans-serif; font-weight:700; color:var(--amber); margin-top:2px;">${rule.gst_rate}%</div>
        </div>
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">ITC Eligibility</div>
          <div style="margin-top:4px;">
            <span class="gst-chip ${rule.itc_eligible?'itc-yes':'itc-no'}">${rule.itc_eligible?'✅ ITC Claimable':'❌ Not Eligible'}</span>
          </div>
        </div>
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">GST Amount (back-calc)</div>
          <div style="font-family:'DM Mono',monospace; color:var(--amber); margin-top:2px;">₹${Number(gst_amount).toLocaleString('en-IN')}</div>
        </div>
        <div>
          <div class="text-muted" style="font-size:0.7rem; text-transform:uppercase; letter-spacing:.05em;">ITC Amount</div>
          <div style="font-family:'DM Mono',monospace; color:${rule.itc_eligible?'var(--emerald)':'var(--muted)'}; margin-top:2px;">₹${Number(itc_amount).toLocaleString('en-IN')}</div>
        </div>
      </div>
      <div style="display:flex; align-items:center; gap:8px; padding:0.6rem 0.75rem; background:var(--bg3); border-radius:8px; border:1px solid var(--border);">
        <span style="font-size:0.75rem; color:var(--muted);">Classified by:</span>
        <span style="font-size:0.8rem; font-weight:600;">${source}</span>
        <span style="margin-left:auto; font-size:0.75rem; color:var(--muted);">Confidence: <b style="color:var(--text);">${Math.round(rule.confidence*100)}%</b></span>
      </div>`;
    document.getElementById('gst-result-card').style.display = 'block';
  }

  async function downloadCAPDF() {
    const uid = document.getElementById('reports-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter User ID for CA PDF', 'error'); return; }
    try {
      const resp = await fetch(`${API}/ca-summary/${uid}/pdf`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `CA_Report_${uid}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast('CA PDF downloaded', 'success');
    } catch (e) {
      showToast('Download failed: ' + e.message, 'error');
    }
  }

  async function triggerDeadlineNotifications() {
    const uid = document.getElementById('comp-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter User ID to send notifications', 'error'); return; }
    try {
      const resp = await fetch(API + '/compliance/calendar/notify/' + uid, { method: 'POST' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      document.getElementById('calendar-result').textContent = `Notifications sent: ${data.notifications_sent}`;
      setComplianceRaw(data);
      showToast('Deadline notifications triggered', 'success');
    } catch (e) {
      showToast('Notification trigger failed: ' + e.message, 'error');
    }
  }

  async function fetchITC() {
    const uid = document.getElementById('itc-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    const el = document.getElementById('itc-result');
    el.innerHTML = '<div class="text-muted">⏳ Analyzing ITC opportunities…</div>';
    try {
      // pull from actions for ITC data
      const r2 = await fetch(API + '/actions/' + uid);
      if (!r2.ok) throw new Error(`HTTP ${r2.status}`);
      const d2 = await r2.json();
      const itcAction = (d2.actions || []).find(a => a.title === 'Input Tax Credit Available');
      el.innerHTML = itcAction
        ? `<div class="action-card green"><div class="action-priority">🟢 ITC OPPORTUNITY</div><div class="action-title">${itcAction.title}</div><div class="action-msg">${itcAction.message}</div><div class="action-amount">₹${Number(itcAction.amount||0).toLocaleString('en-IN', {maximumFractionDigits:2})}</div></div>`
        : `<div class="text-muted" style="font-size:0.82rem; margin-top:8px;">No ITC opportunities found yet. Ingest more transactions first.</div>`;
      showToast('ITC analysis complete', 'success');
    } catch (e) {
      el.innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      showToast('Failed', 'error');
    }
  }

  async function runWhatIfSimulation() {
    const uid = document.getElementById('sim-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    const category = document.getElementById('sim-category').value.trim();
    const reduction = Number(document.getElementById('sim-reduction').value || 0);
    const revenue = Number(document.getElementById('sim-revenue').value || 0);

    const query = new URLSearchParams({
      reduction_percent: String(reduction),
      revenue_increase_percent: String(revenue)
    });
    if (category) query.set('expense_category', category);

    try {
      const r = await fetch(`${API}/what-if/${uid}?${query.toString()}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      if (!data || !data.baseline || !data.simulation || !data.impact) {
        throw new Error('Unexpected what-if response');
      }

      const baseNet = Number(data.baseline.net_profit || 0);
      const newNet = Number(data.simulation.net_profit || 0);
      const deltaNet = Number(data.impact.net_profit_delta || 0);
      const deltaMargin = Number(data.impact.margin_delta || 0);
      const recommendation = deltaNet > 0
        ? `Projected gain: ₹${deltaNet.toLocaleString('en-IN')} in net profit. Prioritize this scenario for the next cycle.`
        : 'This scenario does not improve profitability. Try smaller cost cuts in another category or combine with revenue growth.';

      document.getElementById('sim-base-net').textContent = `₹${Math.abs(baseNet).toLocaleString('en-IN')}`;
      document.getElementById('sim-base-net').style.color = baseNet >= 0 ? 'var(--emerald)' : 'var(--rose)';
      document.getElementById('sim-base-margin').textContent = `Margin ${Number(data.baseline.profit_margin_percent || 0).toFixed(1)}%`;
      document.getElementById('sim-new-net').textContent = `₹${Math.abs(newNet).toLocaleString('en-IN')}`;
      document.getElementById('sim-new-net').style.color = newNet >= 0 ? 'var(--emerald)' : 'var(--rose)';
      document.getElementById('sim-new-margin').textContent = `Margin ${Number(data.simulation.profit_margin_percent || 0).toFixed(1)}%`;
      document.getElementById('sim-delta-net').textContent = `${deltaNet >= 0 ? '+' : '-'}₹${Math.abs(deltaNet).toLocaleString('en-IN')}`;
      document.getElementById('sim-delta-net').style.color = deltaNet >= 0 ? 'var(--emerald)' : 'var(--rose)';
      document.getElementById('sim-delta-margin').textContent = `Margin delta ${deltaMargin >= 0 ? '+' : ''}${deltaMargin.toFixed(1)}%`;
      document.getElementById('sim-reco').textContent = recommendation;
      document.getElementById('sim-raw').textContent = JSON.stringify(data, null, 2);
      document.getElementById('sim-grid').style.display = 'grid';
      showToast('What-if simulation ready', 'success');
    } catch (e) {
      document.getElementById('sim-grid').style.display = 'none';
      showToast('What-if simulation failed: ' + e.message, 'error');
    }
  }

  /* ───────────────────────────────────────────────
      COMPLIANCE LAB (PHASE 1-5)
  ─────────────────────────────────────────────── */
  let aaConsentId = '';

  function getComplianceUid() {
    return document.getElementById('comp-uid').value.trim() || USER_ID;
  }

  function setComplianceRaw(data) {
    const el = document.getElementById('compliance-raw');
    if (el) el.textContent = JSON.stringify(data, null, 2);
  }

  async function aaRequestConsent() {
    const uid = getComplianceUid();
    if (!uid) { showToast('Enter User ID for compliance tests', 'error'); return; }
    const aaHandle = document.getElementById('aa-handle').value.trim();
    const fiTypes = (document.getElementById('aa-fitypes').value || 'DEPOSIT').split(',').map(s => s.trim()).filter(Boolean);
    try {
      const r = await fetch(API + '/aa/consent/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: uid,
          aa_handle: aaHandle,
          fi_types: fiTypes,
          from_date: '2025-04-01',
          to_date: '2026-03-31'
        })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      aaConsentId = data.consent_id || '';
      document.getElementById('aa-result').textContent = `Consent requested. consent_id=${aaConsentId}`;
      setComplianceRaw(data);
      showToast('AA consent request created', 'success');
    } catch (e) {
      showToast('AA consent request failed: ' + e.message, 'error');
    }
  }

  async function aaMarkConsentActive() {
    if (!aaConsentId) { showToast('Request consent first', 'error'); return; }
    try {
      const r = await fetch(API + '/aa/webhook/consent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ consent_id: aaConsentId, status: 'ACTIVE', payload: { source: 'ui' } })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('aa-result').textContent = `Consent status updated: ${data.status}`;
      setComplianceRaw(data);
      showToast('AA consent set to ACTIVE', 'success');
    } catch (e) {
      showToast('Consent update failed: ' + e.message, 'error');
    }
  }

  async function aaDataReadyFetch() {
    const uid = getComplianceUid();
    if (!aaConsentId) { showToast('Request consent first', 'error'); return; }
    try {
      const r = await fetch(API + '/aa/webhook/data-ready', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ consent_id: aaConsentId, session_id: 'sess-ui-1', user_id: uid, payload: { source: 'ui' } })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('aa-result').textContent = `AA fetch complete. upserted=${data.fetch_result?.upserted_transactions || 0}`;
      setComplianceRaw(data);
      showToast('AA data fetched and persisted', 'success');
    } catch (e) {
      showToast('AA data fetch failed: ' + e.message, 'error');
    }
  }

  async function verifyMSME() {
    const uid = getComplianceUid();
    if (!uid) { showToast('Enter User ID first', 'error'); return; }
    try {
      const r = await fetch(API + '/vendors/verify-msme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: uid,
          vendor_name: document.getElementById('msme-vendor').value.trim(),
          pan: document.getElementById('msme-pan').value.trim()
        })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('msme-result').textContent = `MSME verified: ${data.msme?.enterprise_type || 'UNKNOWN'} (${data.msme?.active_status || 'UNKNOWN'})`;
      setComplianceRaw(data);
      showToast('MSME verification completed', 'success');
    } catch (e) {
      showToast('MSME verify failed: ' + e.message, 'error');
    }
  }

  async function createPayable() {
    const uid = getComplianceUid();
    if (!uid) { showToast('Enter User ID first', 'error'); return; }
    try {
      const r = await fetch(API + '/payables/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: uid,
          vendor_pan: document.getElementById('msme-pan').value.trim(),
          invoice_number: document.getElementById('payable-inv').value.trim(),
          invoice_date: document.getElementById('payable-date').value.trim(),
          amount: 120000
        })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('msme-result').textContent = `Payable created: ${data.invoice_number}`;
      setComplianceRaw(data);
      showToast('Payable created', 'success');
    } catch (e) {
      showToast('Create payable failed: ' + e.message, 'error');
    }
  }

  async function run43BH() {
    const uid = getComplianceUid();
    if (!uid) { showToast('Enter User ID first', 'error'); return; }
    try {
      const r = await fetch(API + '/payables/43bh/' + uid);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('msme-result').textContent = `43B(h) scan done. flagged=${data.flagged_count || 0}`;
      setComplianceRaw(data);
      showToast('43B(h) aging scan completed', 'success');
    } catch (e) {
      showToast('43B(h) scan failed: ' + e.message, 'error');
    }
  }

  async function generateW8BEN() {
    try {
      const r = await fetch(API + '/compliance/w8ben/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: document.getElementById('w8-name').value.trim(),
          registered_address: document.getElementById('w8-address').value.trim(),
          pan: document.getElementById('w8-pan').value.trim()
        })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('cross-result').textContent = `W-8BEN generated at: ${data.file_path || 'generated/'}`;
      setComplianceRaw(data);
      showToast('W-8BEN generated', 'success');
    } catch (e) {
      showToast('W-8BEN generation failed: ' + e.message, 'error');
    }
  }

  async function createForeignRemittance() {
    const uid = getComplianceUid();
    if (!uid) { showToast('Enter User ID first', 'error'); return; }
    try {
      const r = await fetch(API + '/compliance/foreign-remittance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: uid,
          remitter_name: 'Pocket CFO',
          remitter_pan: document.getElementById('w8-pan').value.trim(),
          remittee_name: 'US Vendor',
          remittee_country: 'USA',
          amount_inr: Number(document.getElementById('remit-amount').value || 0),
          purpose_code: 'P0802',
          dtaa_applicable: true,
          taxability: 'TAXABLE',
          withholding_rate: 0
        })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('cross-result').textContent = `Foreign remittance saved. 15CA required=${data.needs_form_15ca ? 'Yes' : 'No'}`;
      setComplianceRaw(data);
      showToast('Foreign remittance workflow completed', 'success');
    } catch (e) {
      showToast('Foreign remittance failed: ' + e.message, 'error');
    }
  }

  async function checkOIDAR() {
    try {
      const r = await fetch(API + '/compliance/oidar/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          party: document.getElementById('oidar-party').value.trim(),
          amount: Number(document.getElementById('oidar-amount').value || 0)
        })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('gstcomp-result').textContent = `OIDAR=${data.oidar_import ? 'Yes' : 'No'} | RCM=${data.rcm_applicable ? 'Yes' : 'No'} | IGST=${data.igst_rcm_liability || 0}`;
      setComplianceRaw(data);
      showToast('OIDAR/RCM check completed', 'success');
    } catch (e) {
      showToast('OIDAR check failed: ' + e.message, 'error');
    }
  }

  async function runGSTPreflight() {
    const uid = getComplianceUid();
    if (!uid) { showToast('Enter User ID first', 'error'); return; }
    try {
      const r = await fetch(API + '/compliance/gst/preflight', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: uid,
          gstr1_total_tax: Number(document.getElementById('preflight-g1').value || 0),
          gstr3b_total_tax: Number(document.getElementById('preflight-g3b').value || 0)
        })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('gstcomp-result').textContent = `Preflight ${data.blocked ? 'BLOCKED' : 'PASSED'} | diff=${data.difference}`;
      setComplianceRaw(data);
      showToast('GST preflight completed', data.blocked ? 'error' : 'success');
    } catch (e) {
      showToast('GST preflight failed: ' + e.message, 'error');
    }
  }

  async function scheduleComplianceCalendar() {
    const uid = getComplianceUid();
    if (!uid) { showToast('Enter User ID first', 'error'); return; }
    try {
      const r = await fetch(API + '/compliance/calendar/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: uid,
          entity_type: document.getElementById('calendar-entity').value.trim(),
          financial_year_end: document.getElementById('calendar-fy').value.trim()
        })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('calendar-result').textContent = `Calendar scheduled. reminders=${(data.reminders || []).length}`;
      setComplianceRaw(data);
      showToast('Compliance calendar scheduled', 'success');
    } catch (e) {
      showToast('Calendar scheduling failed: ' + e.message, 'error');
    }
  }

  async function triggerDRL() {
    const uid = getComplianceUid();
    if (!uid) { showToast('Enter User ID first', 'error'); return; }
    try {
      const r = await fetch(API + '/compliance/drl/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: uid,
          threshold_amount: Number(document.getElementById('drl-threshold').value || 20000)
        })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('calendar-result').textContent = `DRL triggered: ${(data.requests || []).length} requests`;
      setComplianceRaw(data);
      showToast('DRL trigger completed', 'success');
    } catch (e) {
      showToast('DRL trigger failed: ' + e.message, 'error');
    }
  }

  async function runComplianceSmoke() {
    try {
      await aaRequestConsent();
      await aaMarkConsentActive();
      await aaDataReadyFetch();
      await verifyMSME();
      await createPayable();
      await run43BH();
      await generateW8BEN();
      await createForeignRemittance();
      await checkOIDAR();
      await runGSTPreflight();
      await scheduleComplianceCalendar();
      await triggerDRL();
      showToast('Compliance smoke test completed', 'success');
    } catch (e) {
      showToast('Compliance smoke test failed: ' + e.message, 'error');
    }
  }

  /* ───────────────────────────────────────────────
      REPORTS HUB
  ─────────────────────────────────────────────── */
  async function autoScheduleFromParsedData() {
    const uid = document.getElementById('reports-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    try {
      const r = await fetch(`${API}/compliance/calendar/auto/${uid}`, { method: 'POST' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('reports-analysis-grid').style.display = 'grid';
      document.getElementById('reports-raw').textContent = JSON.stringify(data, null, 2);
      showToast('Deadlines scheduled from parsed data', 'success');
    } catch (e) {
      showToast('Auto scheduling failed: ' + e.message, 'error');
    }
  }

  async function generateAllReports() {
    const uid = document.getElementById('reports-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    try {
      const r = await fetch(`${API}/reports/generate-all/${uid}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('reports-analysis-grid').style.display = 'grid';
      document.getElementById('reports-raw').textContent = JSON.stringify(data, null, 2);
      showToast(data.status === 'ok' ? 'All reports generated' : (data.message || 'No data found'), data.status === 'ok' ? 'success' : 'error');
    } catch (e) {
      showToast('Generate reports failed: ' + e.message, 'error');
    }
  }

  async function analyzeReports() {
    const uid = document.getElementById('reports-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    try {
      const r = await fetch(`${API}/reports/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: uid })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      document.getElementById('reports-analysis-grid').style.display = 'grid';
      document.getElementById('reports-analysis-metrics').style.display = 'grid';
      document.getElementById('reports-raw').textContent = JSON.stringify(data, null, 2);

      const analysis = data.analysis || {};
      const highlights = analysis.highlights || [];
      const recommendations = analysis.recommendations || [];
      const exec = analysis.executive_summary || '';
      const topRisks = analysis.top_risks || [];
      const nextActions = analysis.next_actions || [];
      document.getElementById('ra-risk-score').textContent = String(analysis.risk_score || 0);
      document.getElementById('ra-highlights-count').textContent = String(highlights.length);
      document.getElementById('ra-reco-count').textContent = String(recommendations.length);

      document.getElementById('ra-highlights').innerHTML = highlights.length
        ? highlights.map(h => `<div class="action-card indigo"><div class="action-msg">${h}</div></div>`).join('')
        : '<div class="empty-state">No highlights available</div>';
      document.getElementById('ra-recommendations').innerHTML = recommendations.length
        ? recommendations.map(item => `<div class="action-card amber"><div class="action-msg">${item}</div></div>`).join('')
        : '<div class="empty-state">No recommendations available</div>';

      const execText = exec || 'AI summary not available. Add OPENAI_API_KEY and install openai dependency.';
      const risksHtml = topRisks.length ? `<div class="mt-2"><div class="text-muted" style="font-size:0.75rem; text-transform:uppercase; letter-spacing:.05em;">Top Risks</div>${topRisks.map(r => `<div class="action-card rose"><div class="action-msg">${r}</div></div>`).join('')}</div>` : '';
      const actionsHtml = nextActions.length ? `<div class="mt-2"><div class="text-muted" style="font-size:0.75rem; text-transform:uppercase; letter-spacing:.05em;">Next Actions</div>${nextActions.map(a => `<div class="action-card emerald"><div class="action-msg">${a}</div></div>`).join('')}</div>` : '';
      document.getElementById('ra-exec').innerHTML = `<div style="color:var(--text); font-weight:600; margin-bottom:6px;">Executive Summary</div><div class="text-muted" style="line-height:1.6;">${execText}</div>${risksHtml}${actionsHtml}`;

      showToast('Report analysis completed', 'success');
    } catch (e) {
      showToast('Analyze reports failed: ' + e.message, 'error');
    }
  }

  async function downloadReports() {
    const uid = document.getElementById('reports-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    try {
      const url = `${API}/reports/download/${uid}?format=json`;
      const a = document.createElement('a');
      a.href = url;
      a.download = '';
      document.body.appendChild(a);
      a.click();
      a.remove();
      showToast('Downloading reports JSON…', 'success');
    } catch (e) {
      showToast('Download failed: ' + e.message, 'error');
    }
  }

  function buildCalendarHTML(monthDate, eventsByDate) {
    const year = monthDate.getFullYear();
    const month = monthDate.getMonth();
    const first = new Date(year, month, 1);
    const startDay = first.getDay(); // 0 Sun
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const monthKey = `${year}-${String(month + 1).padStart(2, '0')}`;

    const headers = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
      .map(h => `<th style="text-align:left; font-size:0.75rem; color:var(--muted); padding:8px;">${h}</th>`).join('');

    let cells = '';
    let day = 1;
    for (let row = 0; row < 6; row++) {
      let rowHtml = '';
      for (let col = 0; col < 7; col++) {
        const idx = row * 7 + col;
        if (idx < startDay || day > daysInMonth) {
          rowHtml += `<td style="padding:8px; border:1px solid rgba(255,255,255,0.06); color:var(--muted);"></td>`;
        } else {
          const dateStr = `${monthKey}-${String(day).padStart(2, '0')}`;
          const ev = eventsByDate[dateStr] || [];
          const dot = ev.length ? `<div style="margin-top:6px; display:flex; gap:4px; flex-wrap:wrap;">${ev.slice(0,3).map(e => `<span class="badge" style="font-size:0.62rem;">${e.form_code}</span>`).join('')}</div>` : '';
          rowHtml += `<td style="vertical-align:top; padding:8px; border:1px solid rgba(255,255,255,0.06); min-width:110px;">
            <div style="font-weight:700; font-family:'DM Mono',monospace; font-size:0.85rem;">${day}</div>
            ${dot}
          </td>`;
          day++;
        }
      }
      cells += `<tr>${rowHtml}</tr>`;
      if (day > daysInMonth) break;
    }

    return `<div class="text-muted" style="font-size:0.82rem; margin-bottom:8px;">Month: <b style="color:var(--text);">${monthDate.toLocaleString('en-IN',{month:'long'})} ${year}</b></div>
      <div class="table-wrap">
        <table>
          <thead><tr>${headers}</tr></thead>
          <tbody>${cells}</tbody>
        </table>
      </div>`;
  }

  async function viewScheduledCalendar() {
    const uid = document.getElementById('reports-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    try {
      const r = await fetch(`${API}/compliance/calendar/${uid}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const cal = data.calendar;
      if (!cal) {
        showToast('No calendar found. Click Auto Schedule first.', 'error');
        return;
      }

      const reminders = cal.reminders || [];
      const eventsByDate = {};
      reminders.forEach(ev => {
        const d = ev.reminder_date;
        if (!eventsByDate[d]) eventsByDate[d] = [];
        eventsByDate[d].push(ev);
      });
      const upcoming = (data.upcoming || []).slice(0, 6);
      const monthToShow = upcoming.length ? new Date(upcoming[0].reminder_date) : new Date();

      const card = document.getElementById('calendar-card');
      card.style.display = 'block';
      document.getElementById('calendar-meta').textContent = `Entity: ${cal.entity_type || '—'} | FY End: ${cal.financial_year_end || '—'} | Total reminders: ${reminders.length}`;
      const upcomingList = upcoming.length ? `<div class="mt-2"><div class="text-muted" style="font-size:0.75rem; text-transform:uppercase; letter-spacing:.05em;">Upcoming Reminders</div>${upcoming.map(u => `<div class="action-card amber"><div class="action-msg"><b>${u.form_code}</b> — ${u.reminder_date} (T-${u.offset_days} days)</div></div>`).join('')}</div>` : '';
      document.getElementById('calendar-grid').innerHTML = buildCalendarHTML(monthToShow, eventsByDate) + upcomingList;
      document.getElementById('reports-raw').textContent = JSON.stringify(data, null, 2);
      document.getElementById('reports-analysis-grid').style.display = 'grid';
      showToast('Calendar loaded', 'success');
    } catch (e) {
      showToast('Calendar view failed: ' + e.message, 'error');
    }
  }

  /* ───────────────────────────────────────────────
      FINANCIAL STATEMENTS AGENT
  ─────────────────────────────────────────────── */
  async function fetchFinancialStatements() {
    const uid = document.getElementById('fs-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    
    // Show loading state
    document.getElementById('fs-pl').innerHTML = '<div class="text-muted">⏳ Generating P&L…</div>';
    document.getElementById('fs-bs').innerHTML = '<div class="text-muted">⏳ Generating Balance Sheet…</div>';
    document.getElementById('fs-cf').innerHTML = '<div class="text-muted">⏳ Generating Cash Flow…</div>';
    
    try {
      const r = await fetch(API + '/financial-statements/' + uid);
      const data = await r.json();
      if (!data || !data.financial_statements) throw new Error('No financial statements data');
      
      const { financial_statements: statements } = data;
      
      // Update P&L
      document.getElementById('fs-pl').innerHTML = `
        <div class="fs-section">
          <h5>Revenue</h5>
          ${Object.entries(statements.profit_and_loss?.revenue || {}).map(([k,v]) => `<div class="fs-row"><span>${k}</span><span>₹${Number(v).toLocaleString('en-IN')}</span></div>`).join('')}
        </div>
        <div class="fs-section">
          <h5>Expenses</h5>
          ${Object.entries(statements.profit_and_loss?.expenses || {}).map(([k,v]) => `<div class="fs-row"><span>${k}</span><span>₹${Number(v).toLocaleString('en-IN')}</span></div>`).join('')}
        </div>
        <div class="fs-total">
          <div class="fs-row"><span>Net Profit</span><span>₹${Number(statements.profit_and_loss?.net_profit || 0).toLocaleString('en-IN')}</span></div>
        </div>
      `;
      
      // Update Balance Sheet
      document.getElementById('fs-bs').innerHTML = `
        <div class="fs-section">
          <h5>Assets</h5>
          ${Object.entries(statements.balance_sheet?.assets || {}).map(([k,v]) => `<div class="fs-row"><span>${k}</span><span>₹${Number(v).toLocaleString('en-IN')}</span></div>`).join('')}
        </div>
        <div class="fs-section">
          <h5>Liabilities</h5>
          ${Object.entries(statements.balance_sheet?.liabilities || {}).map(([k,v]) => `<div class="fs-row"><span>${k}</span><span>₹${Number(v).toLocaleString('en-IN')}</span></div>`).join('')}
        </div>
        <div class="fs-total">
          <div class="fs-row"><span>Equity</span><span>₹${Number(statements.balance_sheet?.equity || 0).toLocaleString('en-IN')}</span></div>
        </div>
      `;
      
      // Update Cash Flow
      document.getElementById('fs-cf').innerHTML = `
        <div class="fs-section">
          <h5>Operating Activities</h5>
          ${Object.entries(statements.cash_flow_statement?.operating_activities || {}).map(([k,v]) => `<div class="fs-row"><span>${k}</span><span>₹${Number(v).toLocaleString('en-IN')}</span></div>`).join('')}
        </div>
        <div class="fs-section">
          <h5>Investing Activities</h5>
          ${Object.entries(statements.cash_flow_statement?.investing_activities || {}).map(([k,v]) => `<div class="fs-row"><span>${k}</span><span>₹${Number(v).toLocaleString('en-IN')}</span></div>`).join('')}
        </div>
        <div class="fs-section">
          <h5>Financing Activities</h5>
          ${Object.entries(statements.cash_flow_statement?.financing_activities || {}).map(([k,v]) => `<div class="fs-row"><span>${k}</span><span>₹${Number(v).toLocaleString('en-IN')}</span></div>`).join('')}
        </div>
        <div class="fs-total">
          <div class="fs-row"><span>Net Cash Flow</span><span>₹${Number(statements.cash_flow_statement?.net_change_in_cash || 0).toLocaleString('en-IN')}</span></div>
        </div>
      `;
      
      document.getElementById('fs-raw').textContent = JSON.stringify(data, null, 2);
      document.getElementById('fs-grid').style.display = 'grid';
      showToast('Financial statements generated', 'success');
    } catch (e) {
      document.getElementById('fs-pl').innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      document.getElementById('fs-bs').innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      document.getElementById('fs-cf').innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      showToast('Failed to generate financial statements', 'error');
    }
  }

  function showFSTab(tab) {
    document.querySelectorAll('.fs-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.fs-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`[onclick="showFSTab('${tab}')"]`).classList.add('active');
    document.getElementById(`${tab}-content`).classList.add('active');
  }

  /* ───────────────────────────────────────────────
      INCOME TAX AGENT
  ─────────────────────────────────────────────── */
  async function fetchIncomeTax() {
    const uid = document.getElementById('tax-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    
    // Show loading state
    document.getElementById('tax-summary').innerHTML = '<div class="text-muted">⏳ Calculating tax summary…</div>';
    document.getElementById('tax-liability').innerHTML = '<div class="text-muted">⏳ Calculating tax liability…</div>';
    
    try {
      const r = await fetch(API + '/income-tax/' + uid);
      const data = await r.json();
      if (!data || !data.income_tax_summary) throw new Error('No tax calculation data');
      
      const { income_tax_summary: taxData } = data;
      const taxable = taxData.taxable_income_summary || {};
      const deductions = taxable.deductions || {};
      const liability = taxData.tax_liability || {};
      
      // Update tax summary
      document.getElementById('tax-summary').innerHTML = `
        <div class="tax-summary">
          <div class="tax-card">
            <div class="tax-label">Gross Income</div>
            <div class="tax-amount">₹${safeNum(taxable.gross_total_income).toLocaleString('en-IN')}</div>
          </div>
          <div class="tax-card">
            <div class="tax-label">Deductions</div>
            <div class="tax-amount">₹${safeNum(deductions.total_deductions).toLocaleString('en-IN')}</div>
          </div>
          <div class="tax-card">
            <div class="tax-label">Taxable Income</div>
            <div class="tax-amount">₹${safeNum(taxable.taxable_income).toLocaleString('en-IN')}</div>
          </div>
        </div>
        <div class="tax-breakdown">
          <h4>Tax Breakdown</h4>
          <div class="tax-slabs">
            ${(liability.slab_breakdown || []).map(slab => `
              <div class="slab-row">
                <span>${safeNum(slab.rate).toFixed(0)}% slab</span>
                <span>₹${safeNum(slab.tax).toLocaleString('en-IN')}</span>
              </div>
            `).join('')}
          </div>
        </div>
      `;
      
      // Update tax liability
      document.getElementById('tax-liability').innerHTML = `
        <div class="tax-card primary" style="margin-bottom: 1rem;">
          <div class="tax-label">Tax Liability</div>
          <div class="tax-amount">₹${safeNum(liability.total_tax_liability).toLocaleString('en-IN')}</div>
        </div>
        <div class="tax-recommendations">
          <h4>Tax Saving Recommendations</h4>
          ${(taxData.tax_planning_advice || []).map(rec => `
            <div class="action-card blue">
              <div class="action-msg">${rec}</div>
            </div>
          `).join('') || '<div class="empty-state">No recommendations available</div>'}
        </div>
      `;
      
      document.getElementById('tax-raw').textContent = JSON.stringify(data, null, 2);
      document.getElementById('tax-grid').style.display = 'grid';
      showToast('Income tax calculated', 'success');
    } catch (e) {
      document.getElementById('tax-summary').innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      document.getElementById('tax-liability').innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      showToast('Failed to calculate income tax', 'error');
    }
  }

  /* ───────────────────────────────────────────────
      RECONCILIATION AGENT
  ─────────────────────────────────────────────── */
  async function fetchReconciliation() {
    const uid = document.getElementById('rec-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    
    // Show loading state
    document.getElementById('rec-issues').innerHTML = '<div class="text-muted">⏳ Checking for issues…</div>';
    document.getElementById('rec-balance').innerHTML = '<div class="text-muted">⏳ Checking balances…</div>';
    
    try {
      const r = await fetch(API + '/reconciliation/' + uid);
      const data = await r.json();
      if (!data || !data.reconciliation_report) throw new Error('No reconciliation data');
      
      const { reconciliation_report: reconciliation } = data;
      const issues = reconciliation.issues || {};
      const summary = issues.summary || {};
      const duplicates = issues.duplicate_transactions || [];
      const gaps = issues.gap_alerts || [];
      const lowConfidence = issues.low_confidence_transactions || [];
      
      // Update issues summary
      document.getElementById('rec-issues').innerHTML = `
        <div class="rec-summary">
          <div class="rec-card">
            <div class="rec-label">Total Transactions</div>
            <div class="rec-amount">${safeNum(summary.duplicate_count) + safeNum(summary.uncategorized_count) + safeNum(summary.low_confidence_count)}</div>
          </div>
          <div class="rec-card">
            <div class="rec-label">Duplicates Found</div>
            <div class="rec-amount">${safeNum(summary.duplicate_count)}</div>
          </div>
          <div class="rec-card">
            <div class="rec-label">Low Confidence</div>
            <div class="rec-amount">${safeNum(summary.low_confidence_count)}</div>
          </div>
          <div class="rec-card ${safeNum(summary.duplicate_count) === 0 ? 'success' : 'warning'}">
            <div class="rec-label">Status</div>
            <div class="rec-amount">${safeNum(summary.duplicate_count) === 0 ? 'clean' : 'review'}</div>
          </div>
        </div>
        ${duplicates.length ? `
          <div class="rec-issues">
            <h4>Duplicate Transactions</h4>
            <div class="issues-list">
              ${duplicates.slice(0,3).map(dup => `
                <div class="issue-card">
                  <div class="issue-header">Duplicate Transaction</div>
                  <div class="issue-details">
                    <div>Amount: ₹${safeNum(dup.duplicate_key?.amount).toLocaleString('en-IN')}</div>
                    <div>Party: ${(dup.duplicate_key?.party || 'N/A')}</div>
                    <div>Count: ${safeNum(dup.count)}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
      `;
      
      // Update balance check
      document.getElementById('rec-balance').innerHTML = `
        ${gaps.length ? `
          <div class="rec-issues">
            <h4>Gap Alerts</h4>
            <div class="issues-list">
              ${gaps.slice(0,3).map(issue => `
                <div class="issue-card warning">
                  <div class="issue-header">Gap Alert</div>
                  <div class="issue-details">
                    <div>Previous: ${issue.previous_date || '-'}</div>
                    <div>Current: ${issue.current_date || '-'}</div>
                    <div>Gap Days: ${safeNum(issue.gap_days)}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : '<div class="empty-state">No major gap alerts found</div>'}
        ${lowConfidence.length ? `
          <div class="rec-issues">
            <h4>Low Confidence Transactions</h4>
            <div class="issues-list">
              ${lowConfidence.slice(0,3).map(item => `
                <div class="issue-card warning">
                  <div class="issue-header">${item.party || 'Unknown Party'}</div>
                  <div class="issue-details">
                    <div>Amount: ₹${safeNum(item.amount).toLocaleString('en-IN')}</div>
                    <div>Confidence: ${Math.round(safeNum(item.confidence) * 100)}%</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
        <div class="rec-recommendations">
          <h4>Reconciliation Recommendations</h4>
          ${(reconciliation.recommendations || []).map(rec => `
            <div class="action-card amber">
              <div class="action-msg">${rec}</div>
            </div>
          `).join('') || '<div class="empty-state">No recommendations available</div>'}
        </div>
      `;
      
      document.getElementById('rec-raw').textContent = JSON.stringify(data, null, 2);
      document.getElementById('rec-grid').style.display = 'grid';
      showToast('Reconciliation completed', 'success');
    } catch (e) {
      document.getElementById('rec-issues').innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      document.getElementById('rec-balance').innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      showToast('Failed to perform reconciliation', 'error');
    }
  }

  /* ───────────────────────────────────────────────
      AUDIT AGENT
  ─────────────────────────────────────────────── */
  async function fetchAudit() {
    const uid = document.getElementById('audit-uid').value.trim() || USER_ID;
    if (!uid) { showToast('Enter a User ID', 'error'); return; }
    
    // Show loading state
    document.getElementById('audit-gst').innerHTML = '<div class="text-muted">⏳ Performing audit…</div>';
    document.getElementById('audit-suspicious').innerHTML = '<div class="text-muted">⏳ Performing audit…</div>';
    document.getElementById('audit-raw').innerHTML = '<div class="text-muted">⏳ Performing audit…</div>';
    
    // Show the grid
    document.getElementById('audit-grid').style.display = 'grid';
    
    try {
      const r = await fetch(API + '/audit/' + uid);
      const data = await r.json();
      if (!data || !data.audit_report) throw new Error('No audit data');
      
      const { audit_report: audit } = data;
      const gstIssues = audit.gst_validation_issues || [];
      const suspicious = audit.suspicious_transactions || [];
      const summary = audit.summary || {};
      
      // Update GST Validation section
      document.getElementById('audit-gst').innerHTML = `
        <div class="audit-summary">
          <div class="audit-card">
            <div class="audit-label">GST Issues</div>
            <div class="audit-amount ${safeNum(summary.gst_issues_count) === 0 ? 'success' : 'warning'}">${safeNum(summary.gst_issues_count)}</div>
          </div>
          <div class="audit-card">
            <div class="audit-label">Suspicious Flags</div>
            <div class="audit-amount ${safeNum(summary.suspicious_transactions_count) > 0 ? 'warning' : 'success'}">${safeNum(summary.suspicious_transactions_count)}</div>
          </div>
          <div class="audit-card">
            <div class="audit-label">Overall Status</div>
            <div class="audit-amount ${safeNum(summary.gst_issues_count) + safeNum(summary.suspicious_transactions_count) > 0 ? 'warning' : 'success'}">${safeNum(summary.gst_issues_count) + safeNum(summary.suspicious_transactions_count) > 0 ? 'review' : 'clean'}</div>
          </div>
        </div>
        ${gstIssues.length ? `
          <div class="audit-issues">
            <h4>GST Compliance Issues</h4>
            <div class="issues-list">
              ${gstIssues.slice(0, 6).map(issue => `
                <div class="issue-card error">
                  <div class="issue-header">GST Issue</div>
                  <div class="issue-details">
                    <div>Transaction ID: ${issue.transaction_id || '-'}</div>
                    <div>Expected GST: ₹${safeNum(issue.expected_gst_amount).toLocaleString('en-IN')}</div>
                    <div>Detected Issues: ${(issue.issues || []).join(', ') || 'N/A'}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : '<div class="empty-state">No GST compliance issues found</div>'}
      `;
      
      // Update Suspicious Transactions section
      document.getElementById('audit-suspicious').innerHTML = `
        <div class="audit-summary">
          <div class="audit-card">
            <div class="audit-label">Anomalies Detected</div>
            <div class="audit-amount">${suspicious.length || 0}</div>
          </div>
        </div>
        ${suspicious.length ? `
          <div class="audit-issues">
            <h4>Anomalies Detected</h4>
            <div class="issues-list">
              ${suspicious.slice(0, 8).map(anomaly => `
                <div class="issue-card warning">
                  <div class="issue-header">Anomaly</div>
                  <div class="issue-details">
                    <div>Issue: ${anomaly.issue || 'Suspicious Pattern'}</div>
                    <div>Party: ${anomaly.party || anomaly.transaction?.party || 'N/A'}</div>
                    <div>Amount: ₹${safeNum(anomaly.amount || anomaly.transaction?.amount).toLocaleString('en-IN')}</div>
                    <div>Type: ${anomaly.type || anomaly.transaction?.type || 'N/A'}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : '<div class="empty-state">No anomalies detected</div>'}
        ${audit.recommendations?.length ? `
          <div class="audit-recommendations">
            <h4>Audit Recommendations</h4>
            ${(audit.recommendations || []).map(rec => `
              <div class="action-card blue">
                <div class="action-msg">${rec}</div>
              </div>
            `).join('')}
          </div>
        ` : ''}
      `;
      
      // Update raw response
      document.getElementById('audit-raw').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
      
      showToast('Audit completed', 'success');
    } catch (e) {
      document.getElementById('audit-gst').innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      document.getElementById('audit-suspicious').innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      document.getElementById('audit-raw').innerHTML = `<div class="text-muted">Error: ${e.message}</div>`;
      showToast('Failed to perform audit', 'error');
    }
  }

  /* ───────────────────────────────────────────────
      TOAST
  ─────────────────────────────────────────────── */
  let toastTimer;
  function showToast(msg, type = 'success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = `show ${type}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.className = ''; }, 3000);
  }

  /* ───────────────────────────────────────────────
      INIT
  ─────────────────────────────────────────────── */
  window.addEventListener('DOMContentLoaded', () => {
    checkHealthSilent();
    setInterval(() => {
      if (!document.hidden) checkHealthSilent();
    }, 60000);
  });

