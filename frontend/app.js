// Claw Monitor v3 — Redesigned
const API = '';
let refreshTimer = null;
let currentPage = 'overview';

// ─── INIT ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (getCookie('clawmonitor_dashboard_session')) { hideLogin(); showPage('overview'); }
  setupLogin(); setupNav(); setupActions(); setupChat();
  setupSearch();
  startAutoRefresh();
  startStatusBar();
  
  document.addEventListener('visibilitychange', () => {
    logsPaused = document.hidden;
    if(!document.hidden && currentPage === 'logs') loadLogContent(currentLog, true);
  });
});

// ─── AUTH ───────────────────────────────────────────────────
function setupLogin() {
  document.getElementById('loginBtn')?.addEventListener('click', doLogin);
  document.getElementById('loginPass')?.addEventListener('keydown', e => { if(e.key==='Enter') doLogin(); });
}

async function doLogin() {
  const u = document.getElementById('loginUser')?.value||'';
  const p = document.getElementById('loginPass')?.value||'';
  const msg = document.getElementById('loginMsg');
  try {
    const r = await fetch(`${API}/api/auth/login`, {method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body:JSON.stringify({username:u,password:p})});
    if(r.ok) { hideLogin(); showPage('overview'); } else msg.textContent='Неверный логин или пароль';
  } catch { msg.textContent='Ошибка соединения'; }
}

function hideLogin() { document.getElementById('loginOverlay')?.remove(); }
function getCookie(n) { return document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith(n+'=')); }

// ─── NAV ────────────────────────────────────────────────────
function setupNav() {
  document.querySelectorAll('[data-page]').forEach(el => {
    el.addEventListener('click', e => { e.preventDefault(); showPage(el.dataset.page); });
  });
}

function showPage(page) {
  currentPage = page;
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === `page-${page}`));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.page === page));
  document.querySelectorAll('.sidebar a').forEach(n => n.classList.toggle('active', n.dataset.page === page));
  const loaders = {overview:loadOverview, agents:loadAgents, llm:loadLLM, incidents:loadIncidents, growth:loadGrowth, system:loadSystem, topology:loadTopology, logs:loadLogs, claims:loadClaims};
  if (page !== 'logs') { clearTimeout(logTimer); logTimer = null; lastLogLines = ''; }
  loaders[page]?.();
}

// ─── SEARCH (Ctrl+K) ────────────────────────────────────────
const SEARCH_ITEMS = [
  { icon:'📊', label:'Обзор', page:'overview' },
  { icon:'🤖', label:'Агенты', page:'agents' },
  { icon:'💰', label:'LLM Usage', page:'llm' },
  { icon:'🚨', label:'Инциденты', page:'incidents' },
  { icon:'🌱', label:'Growth', page:'growth' },
  { icon:'🔗', label:'Топология', page:'topology' },
  { icon:'⚙️', label:'Система', page:'system' },
  { icon:'💬', label:'Чат', page:'chat' },
  { icon:'📋', label:'Логи', page:'logs' },
];

function setupSearch() {
  const overlay = document.getElementById('searchOverlay');
  const input = document.getElementById('searchInput');
  const results = document.getElementById('searchResults');
  
  // Ctrl+K / Cmd+K
  document.addEventListener('keydown', e => {
    if((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); openSearch(); }
    if(e.key === 'Escape') closeSearch();
  });
  overlay?.addEventListener('click', e => { if(e.target === overlay) closeSearch(); });
  input?.addEventListener('input', () => renderSearch(input.value));
  input?.addEventListener('keydown', e => {
    const items = results?.querySelectorAll('.search-result');
    const active = results?.querySelector('.search-result.active');
    let idx = active ? Array.from(items).indexOf(active) : -1;
    if(e.key === 'ArrowDown') { e.preventDefault(); idx = Math.min(idx+1, items.length-1); setActiveResult(items, idx); }
    else if(e.key === 'ArrowUp') { e.preventDefault(); idx = Math.max(idx-1, 0); setActiveResult(items, idx); }
    else if(e.key === 'Enter') { e.preventDefault(); active?.click(); }
  });
}

function openSearch() {
  const overlay = document.getElementById('searchOverlay');
  const input = document.getElementById('searchInput');
  overlay?.classList.add('open');
  input.value = '';
  input?.focus();
  renderSearch('');
}
function closeSearch() { document.getElementById('searchOverlay')?.classList.remove('open'); }
function setActiveResult(items, idx) { items.forEach((el,i) => el.classList.toggle('active', i===idx)); }

function renderSearch(query) {
  const results = document.getElementById('searchResults');
  const q = query.toLowerCase().trim();
  const filtered = q ? SEARCH_ITEMS.filter(i => i.label.toLowerCase().includes(q)) : SEARCH_ITEMS;
  results.innerHTML = filtered.map(i => `
    <div class="search-result" onclick="closeSearch();showPage('${i.page}')">
      <span class="search-result-icon">${i.icon}</span>
      <span>${i.label}</span>
    </div>
  `).join('') || '<div class="search-result" style="color:var(--text-muted)">Ничего не найдено</div>';
  // Activate first
  const first = results.querySelector('.search-result');
  if(first) first.classList.add('active');
}

// ─── STATUS BAR ─────────────────────────────────────────────
function startStatusBar() {
  updateStatusBar();
  setInterval(updateStatusBar, 10000); // every 10s
}

async function updateStatusBar() {
  try {
    const r = await fetch(`${API}/api/system/status`, {credentials:'include'});
    if(!r.ok) return;
    const d = await r.json();
    
    const cpu = d.loadavg1 ? parseFloat(d.loadavg1) : null;
    const cpuCores = navigator.hardwareConcurrency || 4;
    const cpuPct = cpu !== null ? Math.min(Math.round((cpu / cpuCores) * 100), 100) : null;
    
    // CPU
    const cpuEl = document.getElementById('statusCpu');
    if(cpuEl && cpuPct !== null) cpuEl.textContent = cpuPct + '%';
    
    // RAM
    const ramEl = document.getElementById('statusRam');
    if(ramEl && d.memory) {
      const usedPct = d.memory.totalMb ? Math.round((d.memory.usedMb / d.memory.totalMb) * 100) : null;
      ramEl.textContent = usedPct !== null ? usedPct + '%' : '—';
    }
    
    // Disk
    const diskEl = document.getElementById('statusDisk');
    if(diskEl && d.disk && d.disk.totalGb) {
      const usedPct = Math.round(((d.disk.totalGb - d.disk.freeGb) / d.disk.totalGb) * 100);
      diskEl.textContent = usedPct + '%';
    }
    
    // Uptime
    const upEl = document.getElementById('statusUptime');
    if(upEl && d.uptimeSeconds) {
      const h = Math.floor(d.uptimeSeconds / 3600);
      const m = Math.floor((d.uptimeSeconds % 3600) / 60);
      upEl.textContent = h > 0 ? h + 'h ' + m + 'm' : m + 'm';
    }
    
    // Sessions (from runtime summary if available)
    const sessEl = document.getElementById('statusSessions');
    if(sessEl) {
      try {
        const sr = await fetch(`${API}/api/details/snapshot`, {credentials:'include'});
        if(sr.ok) {
          const snap = await sr.json();
          const total = snap.runtime?.summary?.total || 0;
          sessEl.textContent = total;
        }
      } catch {}
    }
    
    // Status dot color based on CPU
    const dot = document.getElementById('statusDot');
    if(dot && cpuPct !== null) {
      dot.className = 'status-dot' + (cpuPct > 80 ? ' err' : cpuPct > 50 ? ' warn' : '');
    }
  } catch {}
}

// ─── SNAPSHOT ───────────────────────────────────────────────
async function fetchSnapshot() {
  const r = await fetch(`${API}/api/details/snapshot`, {credentials:'include'});
  return r.ok ? await r.json() : null;
}

// ─── OVERVIEW (redesigned — large numbers, icons) ──────────
async function loadOverview() {
  const cards = document.getElementById('overview-cards');
  const alerts = document.getElementById('overview-alerts');
  if(!cards) return;
  cards.innerHTML = '<div class="spinner"></div>';
  try {
    const snap = await fetchSnapshot();
    if(!snap) throw new Error('no snap');
    const rt = snap.runtime?.summary || {};
    const llm = snap.llm?.summary || {};
    const growth = snap.growth?.summary || {};
    const reg = snap.registry?.summary || {};
    const sys = snap.system || {};
    const costs = snap.llm?.expensiveSessions?.items || [];
    const runtimeAgents = snap.runtime?.agents || [];
    const registryAgents = snap.registry?.agents || [];
    const growthProposals = snap.growth?.proposals || [];

    const totalCost = costs.reduce((a,s) => a + (s.estimatedCostUsd||0), 0);
    const totalTokens = (llm.tokensTotal||0);

    window._overviewData = { runtimeAgents, registryAgents, costs, growthProposals, llm, sys, rt, reg, growth };

    // New card design: icon + large number + compact meta
    cards.innerHTML = `
      <div class="card clickable" onclick="showOverviewDetail('sessions')">
        <div class="icon-row">
          <span class="card-icon">📡</span>
          <span class="label">Сессии</span>
        </div>
        <div class="value">${rt.total ?? '—'}</div>
        <div class="meta">🟢 ${rt.active||0} active · 🟡 ${rt.warm||0} warm · ⚪ ${rt.idle||0} idle</div>
      </div>
      <div class="card clickable" onclick="showOverviewDetail('agents')">
        <div class="icon-row">
          <span class="card-icon">🤖</span>
          <span class="label">Агенты</span>
        </div>
        <div class="value">${reg.canonicalCore ?? registryAgents.length}</div>
        <div class="meta">в реестре</div>
      </div>
      <div class="card clickable ${totalCost > 2 ? 'danger' : ''}" onclick="showOverviewDetail('llm')">
        <div class="icon-row">
          <span class="card-icon">💰</span>
          <span class="label">LLM расход</span>
        </div>
        <div class="value ${totalCost > 2 ? 'red' : 'green'}">$${(totalCost || 0).toFixed(2)}</div>
        <div class="meta">${fmtTokens(totalTokens)} токенов · ${llm.providerCount||0} провайдеров</div>
      </div>
      <div class="card clickable" id="quota-card" onclick="showOverviewDetail('quota')">
        <div class="icon-row">
          <span class="card-icon">💳</span>
          <span class="label">Квота OpenRouter</span>
        </div>
        <div class="value" id="quota-value">...</div>
        <div class="meta" id="quota-meta">загрузка...</div>
      </div>
      <div class="card clickable" onclick="showOverviewDetail('disk')">
        <div class="icon-row">
          <span class="card-icon">💾</span>
          <span class="label">Диск</span>
        </div>
        <div class="value cyan">${sys.disk?.freeGb ?? '—'}</div>
        <div class="meta">свободно GB из ${sys.disk?.totalGb || '?'} GB</div>
      </div>
      <div class="card full clickable ${growth.openProposals > 0 ? 'highlight' : ''}" onclick="showOverviewDetail('growth')">
        <div class="icon-row">
          <span class="card-icon">🌱</span>
          <span class="label">Growth</span>
        </div>
        <div class="value purple">${growth.openProposals ?? 0}</div>
        <div class="meta">${growth.bestNextMove?.title || 'Нет предложений'}</div>
      </div>
    `;

    const al = snap.alerts?.items || [];
    alerts.innerHTML = al.length ? al.slice(0,6).map((a,i) => `
      <div class="item level-${a.level} clickable" onclick='showOverviewDetail("alert", ${JSON.stringify(a).replace(/'/g,"&#39;")})'>
        <div class="item-title">${esc(a.title)}</div>
        <div class="item-sub">${esc(a.message||'')}</div>
      </div>
    `).join('') : '<div class="empty-state"><span class="emoji">✅</span>Всё спокойно</div>';

    updateRefreshTime();
    updateQuotaCard();
  } catch(e) {
    cards.innerHTML = `<div class="empty-state"><span class="emoji">⚠️</span>Ошибка загрузки</div>`;
  }
}

// ─── CLAIMS ─────────────────────────────────────────────────
async function loadClaims() {
  const statsEl = document.getElementById('claims-stats');
  const listEl = document.getElementById('claims-list');
  const countEl = document.getElementById('claims-count');
  if(!statsEl) return;
  statsEl.innerHTML = '<div class="spinner"></div>';
  try {
    const r = await fetch(`${API}/api/claims/list`, {credentials:'include'});
    if(!r.ok) throw new Error('no data');
    const data = await r.json();
    const claims = data.claims || [];
    
    if(countEl) countEl.textContent = claims.filter(c => c.status === 'new').length;
    
    // Stats cards
    statsEl.innerHTML = `
      <div class="card"><div class="icon-row"><span class="card-icon">📋</span><span class="label">Всего</span></div><div class="value">${data.count||0}</div></div>
      <div class="card"><div class="icon-row"><span class="card-icon">🆕</span><span class="label">Новые</span></div><div class="value orange">${data.new||0}</div></div>
      <div class="card"><div class="icon-row"><span class="card-icon">🔄</span><span class="label">В работе</span></div><div class="value cyan">${data.in_progress||0}</div></div>
      <div class="card"><div class="icon-row"><span class="card-icon">✅</span><span class="label">Готово</span></div><div class="value green">${data.done||0}</div></div>
    `;
    
    // Claims list
    const statusIcons = {done:'✅', in_progress:'🔄', new:'🆕', cancelled:'❌'};
    const statusLabels = {done:'Готово', in_progress:'В работе', new:'Новая', cancelled:'Отменена'};
    
    listEl.innerHTML = claims.map(c => {
      const icon = statusIcons[c.status] || '❓';
      const deadline = c.deadline || '—';
      const isOverdue = c.deadline && c.deadline < new Date().toISOString().slice(0,10) && c.status !== 'done';
      
      return `<div class="item ${isOverdue ? 'level-critical' : ''}">
        <div class="item-title">${c.emoji||'📋'} ${c.id} — ${esc(c.client||'—')}</div>
        <div class="item-sub">📍 ${esc(c.address||'—')}</div>
        <div class="item-sub">📋 ${esc(c.description||'—')}</div>
        <div class="item-badges">
          <span class="badge ${c.status==='done'?'ok':c.status==='new'?'warn':'info'}">${icon} ${statusLabels[c.status]||c.status}</span>
          <span class="badge ${isOverdue ? 'err' : 'dim'}">⏰ ${deadline}</span>
        </div>
      </div>`;
    }).join('') || '<div class="empty-state"><span class="emoji">📋</span>Нет заявок</div>';
    
    document.getElementById('claims-refresh-time').textContent = new Date().toLocaleTimeString('ru-RU');
  } catch {
    statsEl.innerHTML = '<div class="empty-state">Ошибка загрузки</div>';
  }
}

// ─── AGENTS (tier-colored borders) ─────────────────────────
async function loadAgents() {
  const grid = document.getElementById('agents-grid');
  if(!grid) return;
  grid.innerHTML = '<div class="spinner"></div>';
  try {
    const [regR, snapR] = await Promise.all([
      fetch(`${API}/api/registry/agents`, {credentials:'include'}),
      fetch(`${API}/api/details/snapshot`, {credentials:'include'}),
    ]);
    const agents = regR.ok ? await regR.json() : [];
    const snap = snapR.ok ? await snapR.json() : {};
    const runtimeAgents = snap.runtime?.agents || [];
    const runtimeMap = {};
    runtimeAgents.forEach(a => { runtimeMap[a.id] = a; });
    
    if(!agents.length) { grid.innerHTML = '<div class="empty-state">Нет агентов</div>'; return; }
    
    const stateIcons = {active:'🟢', warm:'🟡', idle:'⚪', unknown:'❓'};
    const stateLabels = {active:'✅ Работает', warm:'🟡 Недавно', idle:'⏸ Простой', unknown:'❓ Нет сигнала'};
    const stateColors = {active:'var(--green)', warm:'var(--orange)', idle:'var(--text-dim)', unknown:'var(--red)'};
    
    // Tier colors for borders (CSS handles via data-tier)
    const tierLabels = {orchestrator:'🎯 Оркестратор', specialists:'🧠 Специалист', execution_backends:'⚡ Backend', experimental:'🧪 Experimental', default:''};
    
    const renderNode = (a, level) => {
      const rt = runtimeMap[a.id] || {};
      const state = rt.runtimeState || 'unknown';
      const ago = rt.lastSeenSecondsAgo != null 
        ? (rt.lastSeenSecondsAgo < 60 ? 'сейчас' 
           : rt.lastSeenSecondsAgo < 3600 ? Math.floor(rt.lastSeenSecondsAgo/60)+'м назад'
           : rt.lastSeenSecondsAgo < 86400 ? Math.floor(rt.lastSeenSecondsAgo/3600)+'ч назад'
           : Math.floor(rt.lastSeenSecondsAgo/86400)+'д назад')
        : '';
      const msg = rt.latestMessage ? esc(rt.latestMessage.slice(0,80)) : '—';
      const name = esc(a.name||a.id);
      const tier = a.tier || 'default';
      
      let statusLabel = stateLabels[state] || stateLabels.unknown;
      if(state === 'active' && msg && msg !== '—') statusLabel = '✅ ' + msg;
      else if(state === 'warm') statusLabel = '🟡 ' + (msg !== '—' ? msg : ago);
      else if(state === 'idle') statusLabel = '⏸ Простой ' + ago;
      
      return `<div class="tree-node level-${level}">
        <div class="tree-node-card" data-tier="${tier}" onclick="showAgentDetail('${esc(a.id)}')">
          <div class="tree-node-header">
            <span class="tree-node-icon">${stateIcons[state]||'❓'}</span>
            <span class="tree-node-name">${name}</span>
            <span class="tree-node-tier">${esc(tierLabels[tier]?.split(' ').pop()||tier)}</span>
          </div>
          <div class="tree-node-status">${statusLabel}</div>
          ${a.status && a.status !== 'canonical' ? `<div style="margin-top:4px"><span class="badge ${statusBadge(a.status)}" style="font-size:10px">${esc(a.status)}</span></div>` : ''}
        </div>
        <div class="tree-children" id="children-${a.id}"></div>
      </div>`;
    };
    
    let html = '<div class="agents-tree">';
    
    const orchestrator = agents.find(a => a.tier === 'orchestrator');
    const specialists = agents.filter(a => a.tier === 'specialists');
    const backends = agents.filter(a => a.tier === 'execution_backends');
    const experimental = agents.filter(a => a.tier === 'experimental');
    
    if(orchestrator) {
      html += renderNode(orchestrator, 0);
      html += '<div class="tree-branch-line"></div>';
      html += '<div class="tree-level">';
      specialists.forEach(s => { html += renderNode(s, 1); });
      html += '</div>';
      html += '<div class="tree-branch-line"></div>';
      html += '<div class="tree-level">';
      backends.forEach(b => { html += renderNode(b, 2); });
      html += '</div>';
    }
    
    html += '</div>';
    
    if(experimental.length) {
      html += `<div class="agents-collapsed">
        <div class="collapsed-header" onclick="document.getElementById('collapsed-list').classList.toggle('show')">
          <span>🧪 Неактивные и экспериментальные (${experimental.length})</span>
          <span class="collapsed-arrow">▾</span>
        </div>
        <div id="collapsed-list" class="collapsed-content">
          <div class="collapsed-grid">${experimental.map(a => {
            const rt = runtimeMap[a.id] || {};
            return `<div class="collapsed-item" onclick="showAgentDetail('${esc(a.id)}')">
              <span class="collapsed-name">${esc(a.name||a.id)}</span>
              <span class="collapsed-status">${rt.sessionCount ? rt.sessionCount+' сессий' : 'никогда'}</span>
            </div>`;
          }).join('')}</div>
        </div>
      </div>`;
    }
    
    grid.innerHTML = html;
  } catch(e) { grid.innerHTML = `<div class="empty-state">Ошибка: ${e.message}</div>`; }
}

async function showAgentDetail(id) {
  try {
    const r = await fetch(`${API}/api/details/agent/${id}`, {credentials:'include'});
    const d = r.ok ? await r.json() : {};
    openModal(`
      <h3 style="margin-bottom:12px">${esc(d.agent?.name||id)}</h3>
      <div class="card full" style="margin-bottom:10px"><div class="label">Status</div><div class="value" style="font-size:20px">${esc(d.agent?.status||'—')}</div></div>
      <div class="card full" style="margin-bottom:10px"><div class="label">Runtime</div><div class="value" style="font-size:20px">${esc(d.agent?.runtimeState||'—')}</div></div>
      ${d.relatedTasks?.length ? `<div class="section-label">Задачи</div><div class="list">${d.relatedTasks.map(t=>`<div class="item"><div class="item-title" style="font-size:14px">${esc(t.title||t.id)}</div><div class="item-sub">${esc(t.status||'')}</div></div>`).join('')}</div>` : ''}
    `);
  } catch {}
}

// ─── LLM ────────────────────────────────────────────────────
async function loadLLM() {
  const sumEl = document.getElementById('llm-summary');
  const provEl = document.getElementById('llm-providers');
  const sessEl = document.getElementById('llm-sessions');
  if(!sumEl) return;
  sumEl.innerHTML = '<div class="spinner"></div>';
  try {
    const [sumR, provR, sessR] = await Promise.all([
      fetch(`${API}/api/llm/summary`, {credentials:'include'}),
      fetch(`${API}/api/llm/providers`, {credentials:'include'}),
      fetch(`${API}/api/llm/hot-sessions`, {credentials:'include'}),
    ]);
    const sum = sumR.ok ? await sumR.json() : {};
    const prov = provR.ok ? await provR.json() : {items:[]};
    const sess = sessR.ok ? await sessR.json() : {items:[]};

    sumEl.innerHTML = `<div class="cards">
      <div class="card"><div class="icon-row"><span class="card-icon">📊</span><span class="label">Сессий</span></div><div class="value">${sum.sessionsTracked||0}</div><div class="meta">свежих: ${sum.freshSessions||0}</div></div>
      <div class="card"><div class="icon-row"><span class="card-icon">🔢</span><span class="label">Токены</span></div><div class="value cyan">${fmtTokens(sum.tokensTotal||0)}</div><div class="meta">${sum.providerCount||0} провайдеров · ${sum.modelCount||0} моделей</div></div>
    </div>`;

    provEl.innerHTML = (prov.items||[]).map(p => `
      <div class="item">
        <div class="item-title">${esc(p.provider)}</div>
        <div class="item-sub">${p.sessions} сессий · ${fmtTokens(p.tokens)} токенов</div>
        <div class="item-badges">${(p.models||[]).map(m=>`<span class="badge dim">${esc(m.split('/').pop())}</span>`).join('')}</div>
      </div>
    `).join('') || '<div class="empty-state">Нет данных</div>';

    sessEl.innerHTML = (sess.items||[]).slice(0,10).map(s => `
      <div class="item">
        <div class="item-title" style="font-size:13px">${esc(s.sessionKey?.slice(0,50)||'—')}</div>
        <div class="item-sub">${esc(s.model||'')} · ${s.messageCount||0} сообщ.</div>
        <div class="item-badges">
          ${s.hotScore > 20 ? '<span class="badge warn">🔥 горячая</span>' : ''}
          ${s.isRunning ? '<span class="badge ok">running</span>' : ''}
        </div>
      </div>
    `).join('') || '<div class="empty-state">Нет горячих сессий</div>';
  } catch { sumEl.innerHTML = '<div class="empty-state">Ошибка</div>'; }
}

// ─── INCIDENTS ──────────────────────────────────────────────
async function loadIncidents() {
  const sumEl = document.getElementById('inc-summary');
  const listEl = document.getElementById('inc-list');
  if(!sumEl) return;
  sumEl.innerHTML = '<div class="spinner"></div>';
  try {
    const [sumR, evR] = await Promise.all([
      fetch(`${API}/api/incidents/summary`, {credentials:'include'}),
      fetch(`${API}/api/incidents/events`, {credentials:'include'}),
    ]);
    const sum = sumR.ok ? await sumR.json() : {};
    const ev = evR.ok ? await evR.json() : {items:[]};
    const events = ev.items || [];
    const crit = events.filter(e=>e.level==='critical').length;
    const warn = events.filter(e=>e.level==='warning').length;

    sumEl.innerHTML = `<div class="cards">
      <div class="card ${crit?'danger':''}"><div class="icon-row"><span class="card-icon">🔴</span><span class="label">Critical</span></div><div class="value red">${crit}</div></div>
      <div class="card ${warn?'highlight':''}"><div class="icon-row"><span class="card-icon">🟡</span><span class="label">Warning</span></div><div class="value orange">${warn}</div></div>
      <div class="card"><div class="icon-row"><span class="card-icon">📋</span><span class="label">Всего</span></div><div class="value">${events.length}</div></div>
    </div>`;

    listEl.innerHTML = events.slice(0,20).map(e => `
      <div class="item level-${e.level||'info'}" onclick="showIncidentDetail('${esc(e.id||e.eventId||'')}')">
        <div class="item-title">${esc(e.kind||e.title||'Incident')}</div>
        <div class="item-sub">${esc(e.provider||e.source||'')} · ${timeAgo(e.ts||e.timestamp)}</div>
      </div>
    `).join('') || '<div class="empty-state"><span class="emoji">✅</span>Инцидентов нет</div>';
  } catch { sumEl.innerHTML = '<div class="empty-state">Ошибка</div>'; }
}

async function showIncidentDetail(id) {
  if(!id) return;
  try {
    const r = await fetch(`${API}/api/incidents/detail/${encodeURIComponent(id)}`, {credentials:'include'});
    const d = r.ok ? await r.json() : {};
    openModal(`
      <h3 style="margin-bottom:12px">${esc(d.kind||d.title||'Incident')}</h3>
      <div class="card full" style="margin-bottom:8px"><div class="label">Provider</div><div class="meta">${esc(d.provider||'—')}</div></div>
      <div class="card full" style="margin-bottom:8px"><div class="label">Level</div><div class="meta">${esc(d.level||'—')}</div></div>
      <div class="card full"><div class="label">Сообщение</div><div class="meta">${esc(d.message||d.summary||'—')}</div></div>
    `);
  } catch {}
}

// ─── GROWTH ─────────────────────────────────────────────────
async function loadGrowth() {
  const sumEl = document.getElementById('growth-summary');
  const listEl = document.getElementById('growth-proposals');
  if(!sumEl) return;
  sumEl.innerHTML = '<div class="spinner"></div>';
  try {
    const [sumR, propR] = await Promise.all([
      fetch(`${API}/api/growth/summary`, {credentials:'include'}),
      fetch(`${API}/api/growth/proposals`, {credentials:'include'}),
    ]);
    const sum = sumR.ok ? await sumR.json() : {};
    const prop = propR.ok ? await propR.json() : [];

    sumEl.innerHTML = `<div class="cards">
      <div class="card ${sum.openProposals>0?'highlight':''}"><div class="icon-row"><span class="card-icon">📬</span><span class="label">Открыто</span></div><div class="value purple">${sum.openProposals||0}</div></div>
      <div class="card"><div class="icon-row"><span class="card-icon">✅</span><span class="label">Реализовано</span></div><div class="value green">${sum.implemented||0}</div></div>
    </div>
    ${sum.bestNextMove ? `<div class="card full highlight" style="margin-top:10px"><div class="icon-row"><span class="card-icon">🎯</span><span class="label">Следующий шаг</span></div><div class="value" style="font-size:17px">${esc(sum.bestNextMove.title)}</div><div class="meta">${esc(sum.bestNextMove.type||'')} · ${esc(sum.bestNextMove.complexity||'')}</div></div>` : ''}`;

    const items = Array.isArray(prop) ? prop : (prop.items||[]);
    listEl.innerHTML = items.slice(0,15).map(p => `
      <div class="item">
        <div class="item-title">${esc(p.title)}</div>
        <div class="item-sub">${esc(p.type||'')} · ${esc(p.complexity||'')}</div>
        <div class="item-badges"><span class="badge ${p.status==='implemented'?'ok':p.status==='proposed'?'info':'dim'}">${esc(p.status)}</span></div>
      </div>
    `).join('') || '<div class="empty-state">Нет предложений</div>';
  } catch { sumEl.innerHTML = '<div class="empty-state">Ошибка</div>'; }
}

// ─── SYSTEM ─────────────────────────────────────────────────
async function loadSystem() {
  const el = document.getElementById('system-info');
  if(!el) return;
  el.innerHTML = '<div class="spinner"></div>';
  try {
    const r = await fetch(`${API}/api/system/status`, {credentials:'include'});
    const d = r.ok ? await r.json() : {};
    el.innerHTML = `
      <div class="cards">
        <div class="card"><div class="icon-row"><span class="card-icon">${d.status === 'ok' ? '✅' : '⚠️'}</span><span class="label">Статус</span></div><div class="value" style="font-size:20px">${d.status === 'ok' ? 'OK' : esc(d.status)}</div></div>
        <div class="card"><div class="icon-row"><span class="card-icon">📈</span><span class="label">Load</span></div><div class="value">${esc(d.loadavg1||'—')}</div></div>
        <div class="card"><div class="icon-row"><span class="card-icon">💾</span><span class="label">Disk</span></div><div class="value cyan">${d.disk?.freeGb||'?'} GB</div><div class="meta">из ${d.disk?.totalGb||'?'} GB</div></div>
        <div class="card"><div class="icon-row"><span class="card-icon">🐍</span><span class="label">Python</span></div><div class="value" style="font-size:16px">${esc(d.python||'—')}</div></div>
      </div>
    `;
    const tr = await fetch(`${API}/api/tasks/queue`, {credentials:'include'});
    const tasks = tr.ok ? await tr.json() : {items:[]};
    const items = tasks.items || [];
    if(items.length) {
      el.innerHTML += `<div class="section-label">📋 Очередь задач (${items.length})</div><div class="list">${items.slice(0,10).map(t => `
        <div class="item">
          <div class="item-title" style="font-size:14px">${esc(t.title||t.id||t.name||'—')}</div>
          <div class="item-sub">${esc(t.status||t.state||'')} · ${esc(t.assignedAgent||t.agent||'')}</div>
        </div>
      `).join('')}</div>`;
    }
  } catch { el.innerHTML = '<div class="empty-state">Ошибка</div>'; }
}

// ─── TOPOLOGY ───────────────────────────────────────────────
async function loadTopology() {
  const board = document.getElementById('topology-board');
  if(!board) return;
  board.innerHTML = '<div class="spinner"></div>';
  try {
    const r = await fetch(`${API}/api/registry/topology`, {credentials:'include'});
    const d = r.ok ? await r.json() : {};
    const tiers = d.tiers || {};
    const names = {orchestrator:'🎯 Оркестратор', specialists:'🧠 Специалисты', execution_backends:'⚡ Backends', experimental:'🧪 Эксперимент'};
    board.innerHTML = `<div class="topo-cols">` + Object.entries(tiers).map(([key, agents]) => `
      <div class="topo-col">
        <h4>${names[key]||key}</h4>
        ${(agents||[]).map(a => `
          <div class="topo-node">
            <div class="tn-name">${esc(a.name||a.id||'')}</div>
            <div style="font-size:12px;color:var(--text-dim)">${esc(a.role||a.type||'')} · <span class="badge ${statusBadge(a.status)}" style="font-size:10px">${esc(a.status||'')}</span></div>
          </div>
        `).join('') || '<div style="font-size:13px;color:var(--text-dim)">—</div>'}
      </div>
    `).join('') + '</div>';
  } catch { board.innerHTML = '<div class="empty-state">Ошибка</div>'; }
}

// ─── ACTIONS ────────────────────────────────────────────────
function setupActions() {
  document.querySelectorAll('.action-btn[data-action]').forEach(btn => {
    btn.addEventListener('click', () => runAction(btn.dataset.action, btn));
  });
}

async function runAction(action, btn) {
  const out = document.getElementById('action-result');
  if(!out) return;
  btn.disabled = true; out.textContent = 'Выполняю...';
  try {
    const r = await fetch(`${API}/api/actions`, {method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body:JSON.stringify({action})});
    const d = r.ok ? await r.json() : {};
    out.textContent = d.ok ? (d.message||'✅ Готово') : (d.message||'❌ Ошибка');
  } catch { out.textContent = '❌ Ошибка соединения'; }
  btn.disabled = false;
}

// ─── CHAT ───────────────────────────────────────────────────
function setupChat() {
  document.getElementById('chat-send')?.addEventListener('click', sendChat);
  document.getElementById('chat-input')?.addEventListener('keydown', e => { if(e.key==='Enter') sendChat(); });
  document.querySelectorAll('.chat-hint').forEach(h => {
    h.addEventListener('click', () => { const i = document.getElementById('chat-input'); if(i) i.value = h.dataset.text||''; sendChat(); });
  });
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const msgs = document.getElementById('chat-messages');
  const text = input?.value?.trim();
  if(!text) return;
  input.value = '';
  msgs.innerHTML += `<div class="chat-msg user">${esc(text)}</div>`;
  msgs.scrollTop = msgs.scrollHeight;
  try {
    const r = await fetch(`${API}/api/chat`, {method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body:JSON.stringify({message:text})});
    const d = r.ok ? await r.json() : {};
    msgs.innerHTML += `<div class="chat-msg bot">${esc(d.reply||d.message||'Нет ответа')}</div>`;
  } catch { msgs.innerHTML += `<div class="chat-msg bot">Ошибка соединения</div>`; }
  msgs.scrollTop = msgs.scrollHeight;
}

// ─── MODAL ──────────────────────────────────────────────────
function openModal(html) {
  let ov = document.getElementById('modal-overlay');
  if(!ov) {
    ov = document.createElement('div'); ov.id = 'modal-overlay'; ov.className = 'modal-overlay';
    ov.innerHTML = `<div class="modal-sheet"><div class="modal-handle"></div><button class="modal-close" onclick="closeModal()">✕</button><div id="modal-content"></div></div>`;
    document.body.appendChild(ov);
    ov.addEventListener('click', e => { if(e.target===ov) closeModal(); });
  }
  document.getElementById('modal-content').innerHTML = html;
  ov.classList.add('open');
}
function closeModal() { document.getElementById('modal-overlay')?.classList.remove('open'); }

// ─── AUTO-REFRESH ───────────────────────────────────────────
function startAutoRefresh() {
  const btn = document.getElementById('refresh-btn');
  btn?.addEventListener('click', () => showPage(currentPage));
}

// ─── UTILS ──────────────────────────────────────────────────
function esc(s) { if(!s) return ''; const d=document.createElement('div'); d.textContent=String(s); return d.innerHTML; }
function fmtTokens(n) { if(!n) return '0'; if(n>=1e6) return (n/1e6).toFixed(1)+'M'; if(n>=1e3) return (n/1e3).toFixed(1)+'K'; return String(n); }
function timeAgo(ts) {
  if(!ts) return '';
  const diff = Date.now() - new Date(ts).getTime();
  if(diff<60000) return 'только что';
  if(diff<3600000) return Math.floor(diff/60000)+'м назад';
  if(diff<86400000) return Math.floor(diff/3600000)+'ч назад';
  return Math.floor(diff/86400000)+'д назад';
}
function statusBadge(s) {
  if(!s) return 'dim';
  if(['canonical','active'].includes(s)) return 'ok';
  if(['draft','experimental','transitional'].includes(s)) return 'warn';
  return 'err';
}
function updateRefreshTime() {
  const el = document.getElementById('refresh-time');
  if(el) el.textContent = new Date().toLocaleTimeString('ru-RU');
}

// ─── QUOTA CARD ─────────────────────────────────────────────
async function updateQuotaCard() {
  const valueEl = document.getElementById('quota-value');
  const metaEl = document.getElementById('quota-meta');
  const cardEl = document.getElementById('quota-card');
  if(!valueEl) return;
  try {
    const r = await fetch(`${API}/api/quota/status`, {credentials:'include'});
    if(!r.ok) throw new Error('no data');
    const data = await r.json();
    const or = Array.isArray(data) ? data.find(d => d.provider === 'openrouter') : null;
    if(!or || or.error) throw new Error('no openrouter');
    
    const remaining = or.remaining || 0;
    const pct = or.remaining_pct || 0;
    const status = or.status || 'ok';
    
    valueEl.textContent = `$${remaining.toFixed(2)}`;
    valueEl.className = 'value ' + (status === 'ok' ? 'green' : status === 'warning' ? 'orange' : 'red');
    metaEl.textContent = `${pct.toFixed(0)}% осталось · ${or.usage_pct?.toFixed(0) || 0}% потрачено`;
    
    // Update card border color
    if(cardEl) {
      cardEl.style.borderColor = status === 'ok' ? 'var(--green)' : status === 'warning' ? 'var(--orange)' : 'var(--red)';
    }
  } catch {
    valueEl.textContent = '—';
    metaEl.textContent = 'нет данных';
  }
}

// ─── OVERVIEW DETAIL ────────────────────────────────────────
function showOverviewDetail(type, data) {
  const d = window._overviewData || {};
  let html = '';
  
  if(type === 'sessions') {
    const agents = d.runtimeAgents || [];
    const active = agents.filter(a => a.runtimeState === 'active');
    const warm = agents.filter(a => a.runtimeState === 'warm');
    const idle = agents.filter(a => a.runtimeState === 'idle');
    const unknown = agents.filter(a => a.runtimeState === 'unknown');
    
    const renderAgentRow = (a) => {
      const stateLabels = {active:'🟢 Активен', warm:'🟡 Недавно', idle:'⚪ Простой', unknown:'❓ Нет сигнала'};
      const ago = a.lastSeenSecondsAgo != null ? (a.lastSeenSecondsAgo < 60 ? 'сейчас' : a.lastSeenSecondsAgo < 3600 ? Math.floor(a.lastSeenSecondsAgo/60)+'м назад' : Math.floor(a.lastSeenSecondsAgo/3600)+'ч назад') : '—';
      return `<div class="item">
        <div class="item-title">${esc(a.name||a.id)}</div>
        <div class="item-sub">${esc(a.tier||'')} · ${stateLabels[a.runtimeState]||a.runtimeState} · ${ago} · ${a.sessionCount||0} сессий</div>
      </div>`;
    };
    
    html = `<h3>Сессии и агенты</h3>
      <div class="cards" style="margin:12px 0">
        <div class="card"><div class="label">Active</div><div class="value green">${active.length}</div></div>
        <div class="card"><div class="label">Warm</div><div class="value orange">${warm.length}</div></div>
        <div class="card"><div class="label">Idle</div><div class="value">${idle.length}</div></div>
        <div class="card"><div class="label">Unknown</div><div class="value red">${unknown.length}</div></div>
      </div>`;
    if(active.length) html += `<div class="section-label">🟢 Активные (${active.length})</div><div class="list">${active.map(renderAgentRow).join('')}</div>`;
    if(warm.length) html += `<div class="section-label" style="margin-top:12px">🟡 Недавно активные</div><div class="list">${warm.map(renderAgentRow).join('')}</div>`;
    if(idle.length) html += `<div class="section-label" style="margin-top:12px">⚪ В простое</div><div class="list">${idle.map(renderAgentRow).join('')}</div>`;
    if(unknown.length) html += `<div class="section-label" style="margin-top:12px">❓ Нет сигнала</div><div class="list">${unknown.map(renderAgentRow).join('')}</div>`;
    
  } else if(type === 'agents') {
    const agents = d.registryAgents || [];
    const c = d.reg?.counts || {};
    html = `<h3>Реестр агентов</h3>
      <div class="cards" style="margin:12px 0">
        <div class="card"><div class="label">Orchestrator</div><div class="value orange">${c.orchestrator||0}</div></div>
        <div class="card"><div class="label">Specialists</div><div class="value green">${c.specialists||0}</div></div>
        <div class="card"><div class="label">Backend</div><div class="value cyan">${c.executionBackends||0}</div></div>
        <div class="card"><div class="label">Experimental</div><div class="value purple">${c.experimental||0}</div></div>
      </div>
      <div class="section-label">Все агенты</div>
      <div class="list">${agents.map(a => `
        <div class="item clickable" onclick="showAgentDetail('${esc(a.id)}')">
          <div class="item-title">${esc(a.name||a.id)}</div>
          <div class="item-sub">${esc(a.tier||'')} · ${esc(a.role||'')} · ${esc(a.status||'')}</div>
        </div>
      `).join('')}</div>`;
    
  } else if(type === 'llm') {
    const costs = d.costs || [];
    const llm = d.llm || {};
    html = `<h3>LLM расход (подробно)</h3>
      <div class="cards" style="margin:12px 0">
        <div class="card"><div class="label">Токенов</div><div class="value cyan">${fmtTokens(llm.tokensTotal||0)}</div></div>
        <div class="card"><div class="label">Провайдеров</div><div class="value">${llm.providerCount||0}</div></div>
        <div class="card"><div class="label">Моделей</div><div class="value">${llm.modelCount||0}</div></div>
        <div class="card"><div class="label">Свежих сессий</div><div class="value green">${llm.freshSessions||0}</div></div>
      </div>`;
    if(costs.length) {
      html += `<div class="section-label">🔥 Самые дорогие сессии</div>
        <div class="list">${costs.slice(0,10).map(s => `
          <div class="item">
            <div class="item-title">${esc((s.sessionKey||'—').slice(0,50))}</div>
            <div class="item-sub">${esc(s.model||'')} · ${fmtTokens(s.totalTokens||0)} токенов</div>
            <div class="item-badges">
              ${s.estimatedCostUsd ? `<span class="badge ${s.estimatedCostUsd > 0.5 ? 'err' : 'warn'}">$${s.estimatedCostUsd.toFixed(4)}</span>` : ''}
              ${s.messageCount ? `<span class="badge dim">${s.messageCount} сообщ.</span>` : ''}
            </div>
          </div>
        `).join('')}</div>`;
    }
    
  } else if(type === 'disk') {
    const sys = d.sys || {};
    const disk = sys.disk || {};
    const used = (disk.usedGb||0).toFixed(1);
    const total = (disk.totalGb||0).toFixed(1);
    const free = (disk.freeGb||0).toFixed(1);
    const pct = total > 0 ? Math.round((parseFloat(used)/parseFloat(total))*100) : 0;
    html = `<h3>Диск</h3>
      <div style="margin:16px 0;text-align:center">
        <div style="font-size:48px;font-weight:800;color:${pct>80?'var(--red)':pct>60?'var(--orange)':'var(--cyan)'}">${pct}%</div>
        <div style="background:var(--border);border-radius:99px;height:8px;margin:12px 0;overflow:hidden">
          <div style="background:${pct>80?'var(--red)':pct>60?'var(--orange)':'var(--cyan)'};width:${pct}%;height:100%;border-radius:99px"></div>
        </div>
        <div class="meta">${free} GB свободно из ${total} GB</div>
      </div>`;
    
  } else if(type === 'growth') {
    const proposals = d.growthProposals || [];
    const openProposals = proposals.filter(p => p.status !== 'implemented');
    const implemented = proposals.filter(p => p.status === 'implemented');
    html = `<h3>Growth — Предложения</h3>
      <div class="cards" style="margin:12px 0">
        <div class="card highlight"><div class="label">Открыто</div><div class="value purple">${openProposals.length}</div></div>
        <div class="card"><div class="label">Реализовано</div><div class="value green">${implemented.length}</div></div>
      </div>`;
    if(openProposals.length) {
      html += `<div class="section-label">📋 Открытые</div>
        <div class="list">${openProposals.map(p => `
          <div class="item"><div class="item-title">${esc(p.title)}</div><div class="item-sub">${esc(p.type||'')} · ${esc(p.complexity||'')}</div></div>
        `).join('')}</div>`;
    }
    
  } else if(type === 'quota') {
    html = `<h3>💳 Квота OpenRouter</h3>
      <div class="cards" style="margin:12px 0">
        <div class="card"><div class="label">Осталось</div><div class="value green">$2.81</div></div>
        <div class="card"><div class="label">Потрачено</div><div class="value red">$12.87</div></div>
        <div class="card"><div class="label">Баланс</div><div class="value">$15.69</div></div>
      </div>
      <div class="section-label">📊 Расход по времени</div>
      <div style="background:var(--border);border-radius:99px;height:12px;margin:12px 0;overflow:hidden">
        <div style="background:var(--orange);width:82%;height:100%;border-radius:99px"></div>
      </div>
      <div class="meta" style="text-align:center">82% потрачено · 18% осталось</div>
      <div class="section-label" style="margin-top:16px">⚠️ Рекомендация</div>
      <div class="item level-warning">
        <div class="item-title">Пополнить баланс</div>
        <div class="item-sub">При текущей нагрузке ${'$2.81'.replace('$','')} хватит на ~1-2 дня. Пополни сейчас чтобы не прерывать работу.</div>
      </div>`;
  
  } else if(type === 'alert') {
    html = `<h3>${esc(data.title)}</h3>
      <div class="item level-${data.level}" style="margin:12px 0"><div class="item-sub" style="font-size:14px">${esc(data.message)}</div></div>
      <p class="meta">Источник: ${esc(data.source||'unknown')}</p>
      ${data.remediation?.hints ? `<div class="section-label">Подсказки</div><ul style="padding-left:20px">${data.remediation.hints.map(h=>`<li style="margin-bottom:6px;font-size:14px">${esc(h)}</li>`).join('')}</ul>` : ''}
      ${data.remediation?.safeActions?.length ? `<div class="section-label">Безопасные действия</div><div style="display:flex;gap:8px;flex-wrap:wrap">${data.remediation.safeActions.map(a=>`<button onclick="runAction('${a.action}');closeModal();" style="font-size:12px;padding:6px 10px">${esc(a.label)}</button>`).join('')}</div>` : ''}`;
  }
  openModal(html);
}

// ─── LOGS ───────────────────────────────────────────────────
let currentLog = 'gateway';
let logTimer = null;
let logsPaused = false;

async function loadLogs() {
  document.querySelectorAll('.log-select-btn').forEach(btn => {
    btn.onclick = () => {
      currentLog = btn.dataset.log;
      document.getElementById('logs-name').textContent = currentLog;
      document.querySelectorAll('.log-select-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadLogContent(currentLog, true);
    };
  });
  document.getElementById('logs-refresh')?.addEventListener('click', () => loadLogContent(currentLog, true));
  loadLogContent(currentLog, true);
}

let lastLogLines = '';
async function loadLogContent(source, reset) {
  const el = document.getElementById('logs-content');
  if (!el) return;
  try {
    const r = await fetch(`${API}/api/logs/tail/${source}?lines=100`, {credentials:'include'});
    const d = r.ok ? await r.json() : {};
    const content = d.content || 'Нет данных';
    if (content !== lastLogLines || reset) {
      el.textContent = content;
      lastLogLines = content;
      el.scrollTop = el.scrollHeight;
    }
  } catch { el.textContent = 'Ошибка загрузки'; }
  clearTimeout(logTimer);
  if(!logsPaused) logTimer = setTimeout(() => loadLogContent(currentLog, false), 15000);
}
