// Claw Monitor — Mobile-First Frontend v2
const API = '';
let refreshTimer = null;
let currentPage = 'overview';

// ─── INIT ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (getCookie('llm_deck_session')) { hideLogin(); showPage('overview'); }
  setupLogin(); setupNav(); setupActions(); setupChat();
  startAutoRefresh();
  
  // Pause polling when tab is hidden (saves CPU)
  document.addEventListener('visibilitychange', () => {
    logsPaused = document.hidden;
    if(!document.hidden && currentPage === 'logs') {
      loadLogContent(currentLog, true);
    }
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
  document.querySelectorAll('.desktop-nav a').forEach(n => n.classList.toggle('active', n.dataset.page === page));
  const loaders = {overview:loadOverview, agents:loadAgents, llm:loadLLM, incidents:loadIncidents, growth:loadGrowth, system:loadSystem, topology:loadTopology, logs:loadLogs};
  // cleanup
  if (page !== 'logs') { clearTimeout(logTimer); logTimer = null; lastLogLines = ''; }
  
  loaders[page]?.();
}

// ─── SNAPSHOT (one call for overview) ───────────────────────
async function fetchSnapshot() {
  const r = await fetch(`${API}/api/details/snapshot`, {credentials:'include'});
  return r.ok ? await r.json() : null;
}

// ─── OVERVIEW ───────────────────────────────────────────────
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

    // Store full data for modals
    window._overviewData = { runtimeAgents, registryAgents, costs, growthProposals, llm, sys, rt, reg, growth };

    cards.innerHTML = `
      <div class="card clickable" onclick="showOverviewDetail('sessions')">
        <div class="label">Сессии</div>
        <div class="value">${rt.total ?? '—'}</div>
        <div class="meta">active: ${rt.active||0} · warm: ${rt.warm||0} · idle: ${rt.idle||0} · 👆 подробнее</div>
      </div>
      <div class="card clickable" onclick="showOverviewDetail('agents')">
        <div class="label">Агенты</div>
        <div class="value">${reg.canonicalCore ?? registryAgents.length}</div>
        <div class="meta">в реестре · 👆 подробнее</div>
      </div>
      <div class="card clickable ${totalCost > 2 ? 'danger' : ''}" onclick="showOverviewDetail('llm')">
        <div class="label">LLM расход</div>
        <div class="value">$${(totalCost || 0).toFixed(2)}</div>
        <div class="meta">${fmtTokens(totalTokens)} токенов · ${llm.providerCount||0} провайдеров · 👆</div>
      </div>
      <div class="card clickable" onclick="showOverviewDetail('disk')">
        <div class="label">Диск</div>
        <div class="value">${sys.disk?.freeGb ?? '—'} GB</div>
        <div class="meta">свободно из ${sys.disk?.totalGb || '?'} GB · 👆</div>
      </div>
      <div class="card full clickable ${growth.openProposals > 0 ? 'highlight' : ''}" onclick="showOverviewDetail('growth')">
        <div class="label">🌱 Growth</div>
        <div class="value">${growth.openProposals ?? 0} предложений</div>
        <div class="meta">${growth.bestNextMove?.title || 'Нет предложений'} · 👆 подробнее</div>
      </div>
    `;

    const al = snap.alerts?.items || [];
    alerts.innerHTML = al.length ? al.slice(0,6).map((a,i) => `
      <div class="item level-${a.level} clickable" onclick='showOverviewDetail("alert", ${JSON.stringify(a).replace(/'/g,"&#39;")})'>
        <div class="item-title">${esc(a.title)}</div>
        <div class="item-sub">${esc(a.message||'')} · 👆</div>
      </div>
    `).join('') : '<div class="empty-state"><div class="emoji">✅</div>Всё спокойно</div>';

    updateRefreshTime();
  } catch(e) {
    cards.innerHTML = `<div class="empty-state"><div class="emoji">⚠️</div>Ошибка загрузки</div>`;
  }
}

// ─── AGENTS ─────────────────────────────────────────────────
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
    const snapAgents = snap.registry?.agents || [];
    const runtimeMap = {};
    runtimeAgents.forEach(a => { runtimeMap[a.id] = a; });
    
    // Build lookup for registry agent data with links
    const regData = {};
    snapAgents.forEach(a => { regData[a.id] = a; });
    
    if(!agents.length) { grid.innerHTML = '<div class="empty-state">Нет агентов</div>'; return; }
    
    const stateIcons = {active:'🟢', warm:'🟡', idle:'⚪', unknown:'❓'};
    const stateLabels = {active:'✅ Работает', warm:'🟡 Недавно', idle:'⏸ Простой', unknown:'❌ Не выполнял'};
    const stateColors = {active:'var(--green)', warm:'var(--orange)', idle:'var(--text-dim)', unknown:'var(--red)'};
    
    // Build tree: get links from registry
    const reg = snap.registry || {};
    const links = reg.topology?.links || [];
    
    // Find children for each node
    const childrenMap = {};
    links.forEach(l => {
      const from = l.from || l.source;
      const to = l.to || l.target;
      if(!childrenMap[from]) childrenMap[from] = [];
      childrenMap[from].push(to);
    });
    
    // Also build from tiers: orchestrator -> specialists, specialists -> backends
    const orchestrator = agents.find(a => a.tier === 'orchestrator');
    const specialists = agents.filter(a => a.tier === 'specialists');
    const backends = agents.filter(a => a.tier === 'execution_backends');
    const experimental = agents.filter(a => a.tier === 'experimental');
    
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
      
      // Determine status label
      let statusLabel = stateLabels[state] || stateLabels.unknown;
      if(state === 'active' && msg && msg !== '—') statusLabel = '✅ ' + msg;
      else if(state === 'warm') statusLabel = '🟡 ' + (msg !== '—' ? msg : ago);
      else if(state === 'idle') statusLabel = '⏸ Простой ' + ago;
      
      return `<div class="tree-node level-${level}">
        <div class="tree-node-card" onclick="showAgentDetail('${esc(a.id)}')" style="border-left: 3px solid ${stateColors[state]||'var(--border)'}">
          <div class="tree-node-header">
            <span class="tree-node-icon">${stateIcons[state]||'❓'}</span>
            <span class="tree-node-name">${name}</span>
            <span class="tree-node-tier">${esc(a.tier==='specialists'?'спец':a.tier==='execution_backends'?'бэк':a.tier==='orchestrator'?'орк':a.tier||'')}</span>
          </div>
          <div class="tree-node-status">${statusLabel}</div>
          ${a.status && a.status !== 'canonical' ? `<div class="tree-node-badge"><span class="badge ${statusBadge(a.status)}" style="font-size:10px">${esc(a.status)}</span></div>` : ''}
        </div>
        <div class="tree-children" id="children-${a.id}"></div>
      </div>`;
    };
    
    let html = '<div class="agents-tree">';
    
    // Orchestrator at top
    if(orchestrator) {
      html += renderNode(orchestrator, 0);
      
      // Draw connection line
      html += '<div class="tree-branch-line"></div>';
      
      // Specialists
      html += '<div class="tree-level">';
      specialists.forEach(s => {
        html += renderNode(s, 1);
      });
      html += '</div>';
      
      // Backends
      html += '<div class="tree-branch-line"></div>';
      html += '<div class="tree-level">';
      backends.forEach(b => {
        html += renderNode(b, 2);
      });
      html += '</div>';
    }
    
    html += '</div>';
    
    // Experimental / Inactive collapsed section
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
      <div class="card full" style="margin-bottom:10px"><div class="label">Status</div><div class="value">${esc(d.agent?.status||'—')}</div></div>
      <div class="card full" style="margin-bottom:10px"><div class="label">Runtime</div><div class="value">${esc(d.agent?.runtimeState||'—')}</div></div>
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
      <div class="card"><div class="label">Сессий</div><div class="value">${sum.sessionsTracked||0}</div><div class="meta">свежих: ${sum.freshSessions||0}</div></div>
      <div class="card"><div class="label">Токены</div><div class="value">${fmtTokens(sum.tokensTotal||0)}</div><div class="meta">${sum.providerCount||0} провайдеров · ${sum.modelCount||0} моделей</div></div>
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
      <div class="card ${crit?'danger':''}"><div class="label">Critical</div><div class="value">${crit}</div></div>
      <div class="card ${warn?'highlight':''}"><div class="label">Warning</div><div class="value">${warn}</div></div>
      <div class="card"><div class="label">Всего</div><div class="value">${events.length}</div></div>
    </div>`;

    listEl.innerHTML = events.slice(0,20).map(e => `
      <div class="item level-${e.level||'info'}" onclick="showIncidentDetail('${esc(e.id||e.eventId||'')}')">
        <div class="item-title">${esc(e.kind||e.title||'Incident')}</div>
        <div class="item-sub">${esc(e.provider||e.source||'')} · ${timeAgo(e.ts||e.timestamp)}</div>
      </div>
    `).join('') || '<div class="empty-state"><div class="emoji">✅</div>Инцидентов нет</div>';
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
      <div class="card ${sum.openProposals>0?'highlight':''}"><div class="label">Открыто</div><div class="value">${sum.openProposals||0}</div></div>
      <div class="card"><div class="label">Реализовано</div><div class="value">${sum.implemented||0}</div></div>
    </div>
    ${sum.bestNextMove ? `<div class="card full highlight" style="margin-top:10px"><div class="label">🎯 Следующий шаг</div><div class="value" style="font-size:17px">${esc(sum.bestNextMove.title)}</div><div class="meta">${esc(sum.bestNextMove.type||'')} · ${esc(sum.bestNextMove.complexity||'')}</div></div>` : ''}`;

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
        <div class="card"><div class="label">Статус</div><div class="value" style="font-size:16px">${d.status === 'ok' ? '✅ OK' : '⚠️ ' + esc(d.status)}</div></div>
        <div class="card"><div class="label">Load</div><div class="value">${esc(d.loadavg1||'—')}</div></div>
        <div class="card"><div class="label">Disk</div><div class="value">${d.disk?.freeGb||'?'} GB</div><div class="meta">из ${d.disk?.totalGb||'?'} GB</div></div>
        <div class="card"><div class="label">Python</div><div class="value" style="font-size:14px">${esc(d.python||'—')}</div></div>
      </div>
    `;
    // tasks queue
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
  const toggle = document.getElementById('auto-refresh-toggle');
  const btn = document.getElementById('refresh-btn');
  btn?.addEventListener('click', () => showPage(currentPage));
  toggle?.addEventListener('change', () => {
    if(toggle.checked) refreshTimer = setInterval(() => showPage(currentPage), 30000);
    else { clearInterval(refreshTimer); refreshTimer = null; }
  });
  // Start auto-refresh OFF by default (user can enable manually)
  if(toggle?.checked) refreshTimer = setInterval(() => showPage(currentPage), 30000);
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
// ─── OVERVIEW DETAIL ─────────────────────────────────────────
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
      const stateColors = {active:'ok', warm:'warn', idle:'dim', unknown:'err'};
      const stateLabels = {active:'🟢 Активен', warm:'🟡 Недавно', idle:'⚪ Простой', unknown:'❓ Нет сигнала'};
      const ago = a.lastSeenSecondsAgo != null ? (a.lastSeenSecondsAgo < 60 ? 'сейчас' : a.lastSeenSecondsAgo < 3600 ? Math.floor(a.lastSeenSecondsAgo/60)+'м назад' : Math.floor(a.lastSeenSecondsAgo/3600)+'ч назад') : '—';
      return `<div class="item">
        <div class="item-title">${esc(a.name||a.id)}</div>
        <div class="item-sub">${esc(a.tier||'')} · ${stateLabels[a.runtimeState]||a.runtimeState} · ${ago} · ${a.sessionCount||0} сессий</div>
      </div>`;
    };
    
    html = `<h3>Сессии и агенты</h3>
      <div class="cards" style="margin:12px 0">
        <div class="card"><div class="label">Active</div><div class="value">${active.length}</div></div>
        <div class="card"><div class="label">Warm</div><div class="value">${warm.length}</div></div>
        <div class="card"><div class="label">Idle</div><div class="value">${idle.length}</div></div>
        <div class="card"><div class="label">Unknown</div><div class="value">${unknown.length}</div></div>
      </div>`;
    
    if(active.length) {
      html += `<div class="section-label">🟢 Активные (${active.length})</div><div class="list">${active.map(renderAgentRow).join('')}</div>`;
    }
    if(warm.length) {
      html += `<div class="section-label" style="margin-top:12px">🟡 Недавно активные (${warm.length})</div><div class="list">${warm.map(renderAgentRow).join('')}</div>`;
    }
    if(idle.length) {
      html += `<div class="section-label" style="margin-top:12px">⚪ В простое (${idle.length})</div><div class="list">${idle.map(renderAgentRow).join('')}</div>`;
    }
    if(unknown.length) {
      html += `<div class="section-label" style="margin-top:12px">❓ Нет сигнала (${unknown.length})</div><div class="list">${unknown.map(renderAgentRow).join('')}</div>`;
    }
    
  } else if(type === 'agents') {
    const agents = d.registryAgents || [];
    const c = d.reg?.counts || {};
    
    html = `<h3>Реестр агентов</h3>
      <div class="cards" style="margin:12px 0">
        <div class="card"><div class="label">Orchestrator</div><div class="value">${c.orchestrator||0}</div></div>
        <div class="card"><div class="label">Specialists</div><div class="value">${c.specialists||0}</div></div>
        <div class="card"><div class="label">Backend</div><div class="value">${c.executionBackends||0}</div></div>
        <div class="card"><div class="label">Experimental</div><div class="value">${c.experimental||0}</div></div>
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
        <div class="card"><div class="label">Токенов</div><div class="value">${fmtTokens(llm.tokensTotal||0)}</div></div>
        <div class="card"><div class="label">Провайдеров</div><div class="value">${llm.providerCount||0}</div></div>
        <div class="card"><div class="label">Моделей</div><div class="value">${llm.modelCount||0}</div></div>
        <div class="card"><div class="label">Свежих сессий</div><div class="value">${llm.freshSessions||0}</div></div>
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
      <div style="margin:16px 0">
        <div style="background:var(--border);border-radius:99px;height:24px;overflow:hidden">
          <div style="background:${pct>80?'var(--red)':pct>60?'var(--warn)':'var(--accent)'};width:${pct}%;height:100%;border-radius:99px;transition:width .3s"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:8px">
          <span class="meta">${free} GB свободно</span>
          <span class="meta">${used} GB / ${total} GB</span>
        </div>
        <div style="text-align:center;margin-top:12px;font-size:36px;font-weight:700">${pct}%</div>
      </div>
      <div class="section-label">Детали</div>
      <div class="list">
        <div class="item"><div class="item-title">Использовано</div><div class="item-sub">${used} GB</div></div>
        <div class="item"><div class="item-title">Свободно</div><div class="item-sub">${free} GB</div></div>
        <div class="item"><div class="item-title">Всего</div><div class="item-sub">${total} GB</div></div>
      </div>`;
    
  } else if(type === 'growth') {
    const proposals = d.growthProposals || [];
    const openProposals = proposals.filter(p => p.status !== 'implemented');
    const implemented = proposals.filter(p => p.status === 'implemented');
    
    html = `<h3>Growth — Предложения</h3>
      <div class="cards" style="margin:12px 0">
        <div class="card highlight"><div class="label">Открыто</div><div class="value">${openProposals.length}</div></div>
        <div class="card"><div class="label">Реализовано</div><div class="value">${implemented.length}</div></div>
        <div class="card"><div class="label">Всего</div><div class="value">${proposals.length}</div></div>
      </div>`;
    
    if(openProposals.length) {
      html += `<div class="section-label">📋 Открытые предложения</div>
        <div class="list">${openProposals.map(p => `
          <div class="item">
            <div class="item-title">${esc(p.title)}</div>
            <div class="item-sub">${esc(p.type||'')} · ${esc(p.complexity||'')} · ${esc(p.status)}</div>
            ${p.description ? `<div class="meta" style="margin-top:4px">${esc(p.description.slice(0,150))}</div>` : ''}
          </div>
        `).join('')}</div>`;
    }
    if(implemented.length) {
      html += `<div class="section-label" style="margin-top:12px">✅ Реализованные</div>
        <div class="list">${implemented.map(p => `
          <div class="item">
            <div class="item-title">${esc(p.title)}</div>
            <div class="item-sub">${esc(p.type||'')} · ${esc(p.complexity||'')}</div>
          </div>
        `).join('')}</div>`;
    }
    
  } else if(type === 'alert') {
    html = `<h3>${esc(data.title)}</h3>
      <div class="item level-${data.level}" style="margin:12px 0">
        <div class="item-sub" style="font-size:14px">${esc(data.message)}</div>
      </div>
      <p class="meta">Источник: ${esc(data.source||'unknown')}</p>
      ${data.remediation?.hints ? `<div class="section-label">Подсказки</div><ul style="padding-left:20px">${data.remediation.hints.map(h=>`<li style="margin-bottom:6px;font-size:14px">${esc(h)}</li>`).join('')}</ul>` : ''}
      ${data.remediation?.safeActions?.length ? `<div class="section-label">Безопасные действия</div><div style="display:flex;gap:8px;flex-wrap:wrap">${data.remediation.safeActions.map(a=>`<button onclick="runAction('${a.action}');closeModal();" style="font-size:12px;padding:6px 10px">${esc(a.label)}</button>`).join('')}</div>` : ''}`;
  }
  openModal(html);
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

// ─── LOGS ───────────────────────────────────────────────────
let currentLog = 'gateway';
let logTimer = null;
let logsPaused = false; // pause logs when tab not visible

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
  
  // poll every 15s (paused when tab hidden)
  clearTimeout(logTimer);
  if(!logsPaused) logTimer = setTimeout(() => loadLogContent(currentLog, false), 15000);
}
