/**
 * Meta-Harness System Observatory Client Controller
 * Handles real-time polling, feature matrix filtering, cache inspection, and live RPC probes.
 */

// Application State
const state = {
  telemetry: null,
  features: [],
  activeFilter: 'ALL',
  searchQuery: '',
  pollInterval: null,
  pollFrequencyMs: 2000,
  chatMessages: [],
  selectedPersona: 'auto',
  isChatSending: false
};

// DOM References
const elements = {
  uptimeVal: document.getElementById('val-uptime'),
  quotaSpendVal: document.getElementById('val-quota-spend'),
  globalStatusPill: document.getElementById('global-status-pill'),
  globalStatusText: document.getElementById('global-status-text'),
  autoRefreshCheck: document.getElementById('auto-refresh-check'),
  
  // Radial Gauge
  gaugeSpendCircle: document.getElementById('gauge-spend-circle'),
  gaugeSpendPct: document.getElementById('gauge-spend-pct'),
  statSpendCost: document.getElementById('stat-spend-cost'),
  statSpendTokens: document.getElementById('stat-spend-tokens'),
  badgeCircuitBreaker: document.getElementById('badge-circuit-breaker'),
  
  // Context Tokens
  labelTokenUtil: document.getElementById('label-token-util'),
  barTokenUtil: document.getElementById('bar-token-util'),
  statIngestedTokens: document.getElementById('stat-ingested-tokens'),
  statBundledTokens: document.getElementById('stat-bundled-tokens'),
  statActiveBranch: document.getElementById('stat-active-branch'),
  badgeEngineStatus: document.getElementById('badge-engine-status'),

  // Cache
  statWalMode: document.getElementById('stat-wal-mode'),
  statDbSize: document.getElementById('stat-db-size'),
  statParseCacheCount: document.getElementById('stat-parse-cache-count'),
  statSymbolRefCount: document.getElementById('stat-symbol-ref-count'),
  statExportRegCount: document.getElementById('stat-export-reg-count'),

  // Test
  statTestStatus: document.getElementById('stat-test-status'),
  statTestTime: document.getElementById('stat-test-time'),
  statTestDuration: document.getElementById('stat-test-duration'),

  // Features
  tabFeatCount: document.getElementById('tab-feat-count'),
  featuresGrid: document.getElementById('features-grid-container'),
  featureSearchInput: document.getElementById('feature-search-input'),
  filterPills: document.querySelectorAll('.filter-btn'),

  // Modal
  modal: document.getElementById('feature-detail-modal'),
  modalCloseBtn: document.getElementById('modal-close-btn'),
  modalSubsystem: document.getElementById('modal-subsystem'),
  modalTitle: document.getElementById('modal-title'),
  modalDesc: document.getElementById('modal-desc'),
  modalFile: document.getElementById('modal-file'),
  modalTier: document.getElementById('modal-tier'),
  modalStatus: document.getElementById('modal-status'),
  modalDeps: document.getElementById('modal-deps'),

  // Cache Inspector
  selectCacheTable: document.getElementById('select-cache-table'),
  btnRefreshCacheTable: document.getElementById('btn-refresh-cache-table'),
  cacheTableHead: document.getElementById('cache-table-head'),
  cacheTableBody: document.getElementById('cache-table-body'),

  // Probes
  btnRunRouteProbe: document.getElementById('btn-run-route-probe'),
  probeRoutePrompt: document.getElementById('probe-route-prompt'),
  probeRouteFocus: document.getElementById('probe-route-focus'),
  probeRouteTierBadge: document.getElementById('probe-route-tier-badge'),
  probeRouteOutput: document.getElementById('probe-route-output'),

  probeSkelFile: document.getElementById('probe-skel-file'),
  probeSkelBudget: document.getElementById('probe-skel-budget'),
  budgetSliderVal: document.getElementById('budget-slider-val'),
  btnRunSkelProbe: document.getElementById('btn-run-skel-probe'),
  probeSkelMeta: document.getElementById('probe-skel-meta'),
  probeSkelOutput: document.getElementById('probe-skel-output'),

  probeBlastSymbol: document.getElementById('probe-blast-symbol'),
  probeBlastDir: document.getElementById('probe-blast-dir'),
  probeBlastDepth: document.getElementById('probe-blast-depth'),
  btnRunBlastProbe: document.getElementById('btn-run-blast-probe'),
  probeBlastMeta: document.getElementById('probe-blast-meta'),
  probeBlastOutput: document.getElementById('probe-blast-output')
};

// ==========================================================================
// API Interaction
// ==========================================================================

async function fetchTelemetry() {
  try {
    const res = await fetch('/api/telemetry');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.telemetry = data;
    state.features = data.features || [];
    renderHUD(data);
    renderFeatures();
  } catch (err) {
    console.error('Telemetry fetch error:', err);
    elements.globalStatusText.textContent = 'CONNECTIVITY OFFLINE';
    elements.globalStatusPill.classList.add('tripped');
  }
}

async function fetchCacheTableData() {
  const table = elements.selectCacheTable.value;
  elements.cacheTableBody.innerHTML = '<tr><td colspan="10">Loading sample records...</td></tr>';
  try {
    const res = await fetch(`/api/cache/tables?table=${encodeURIComponent(table)}&limit=30`);
    const data = await res.json();
    if (data.error) {
      elements.cacheTableHead.innerHTML = '<th>Error</th>';
      elements.cacheTableBody.innerHTML = `<tr><td>${data.error}</td></tr>`;
      return;
    }

    // Render Table Headers
    const cols = data.columns || [];
    elements.cacheTableHead.innerHTML = cols.map(c => `<th>${escapeHtml(c)}</th>`).join('');

    // Render Rows
    if (!data.rows || data.rows.length === 0) {
      elements.cacheTableBody.innerHTML = `<tr><td colspan="${cols.length}">No records found in table '${table}'</td></tr>`;
      return;
    }

    elements.cacheTableBody.innerHTML = data.rows.map(row => {
      return `<tr>` + cols.map(c => `<td>${escapeHtml(row[c] ?? '')}</td>`).join('') + `</tr>`;
    }).join('');
  } catch (err) {
    elements.cacheTableBody.innerHTML = `<tr><td colspan="10">Failed to fetch records: ${err.message}</td></tr>`;
  }
}

// ==========================================================================
// HUD Rendering
// ==========================================================================

function renderHUD(data) {
  // Global Header
  elements.uptimeVal.textContent = `${Math.floor(data.uptime_seconds)}s`;
  elements.quotaSpendVal.textContent = `$${data.quota.cost.toFixed(4)} / $${data.quota.daily_cap.toFixed(2)}`;

  if (data.quota.circuit_breaker_tripped) {
    elements.globalStatusText.textContent = 'CIRCUIT BREAKER TRIPPED';
    elements.globalStatusPill.className = 'status-pill tripped';
  } else {
    elements.globalStatusText.textContent = `${data.operational_features}/${data.total_features} MODULES ACTIVE`;
    elements.globalStatusPill.className = 'status-pill';
  }

  // Radial Gauge for Quota Spend
  const pct = Math.min(data.quota.cost_percent, 100);
  elements.gaugeSpendPct.textContent = `${pct.toFixed(1)}%`;
  
  // Circumference = 2 * PI * 42 ≈ 263.89
  const circumference = 263.89;
  const offset = circumference - (pct / 100) * circumference;
  elements.gaugeSpendCircle.style.strokeDashoffset = offset;

  if (data.quota.circuit_breaker_tripped) {
    elements.gaugeSpendCircle.className = 'gauge-fill tripped';
    elements.badgeCircuitBreaker.className = 'badge badge-danger';
    elements.badgeCircuitBreaker.textContent = 'TRIPPED ($0.33/day CAP)';
  } else if (pct > 75) {
    elements.gaugeSpendCircle.className = 'gauge-fill warning';
    elements.badgeCircuitBreaker.className = 'badge badge-warning';
    elements.badgeCircuitBreaker.textContent = 'WARNING (>75%)';
  } else {
    elements.gaugeSpendCircle.className = 'gauge-fill';
    elements.badgeCircuitBreaker.className = 'badge badge-success';
    elements.badgeCircuitBreaker.textContent = 'NORMAL';
  }

  elements.statSpendCost.textContent = `$${data.quota.cost.toFixed(6)}`;
  elements.statSpendTokens.textContent = data.quota.tokens.toLocaleString();

  // Context Ingestion & Token Packing
  const m = data.metrics;
  elements.labelTokenUtil.textContent = `${m.tokens_total_bundled.toLocaleString()} / ${m.budget_limit.toLocaleString()} tokens (${m.utilization_pct.toFixed(1)}%)`;
  elements.barTokenUtil.style.width = `${Math.min(m.utilization_pct, 100)}%`;
  elements.statIngestedTokens.textContent = m.tokens_total_ingested.toLocaleString();
  elements.statBundledTokens.textContent = m.tokens_total_bundled.toLocaleString();
  elements.statActiveBranch.textContent = m.git_active_branch;

  // SQLite-WAL Cache Health
  const c = data.cache;
  elements.statWalMode.textContent = c.wal_enabled ? 'WAL ENABLED' : 'ROLLBACK';
  elements.statWalMode.className = c.wal_enabled ? 'badge badge-success' : 'badge badge-danger';
  elements.statDbSize.textContent = `${(c.db_size_bytes / (1024 * 1024)).toFixed(2)} MB`;
  elements.statParseCacheCount.textContent = c.parse_cache_count.toLocaleString();
  elements.statSymbolRefCount.textContent = c.symbol_references_count.toLocaleString();
  elements.statExportRegCount.textContent = c.export_registry_count.toLocaleString();

  // Test Metrics
  elements.statTestStatus.textContent = m.status;
  elements.statTestStatus.className = m.status === 'SUCCESS' ? 'badge badge-success' : 'badge badge-danger';
  elements.statTestTime.textContent = m.last_run_timestamp ? new Date(m.last_run_timestamp).toLocaleTimeString() : 'N/A';
  elements.statTestDuration.textContent = m.execution_duration_ms ? `${m.execution_duration_ms.toFixed(1)} ms` : 'N/A';

  // Model Vendor Provider Toggles
  if (data.vendors && data.vendors.vendors) {
    const v = data.vendors.vendors;
    const hfEl = document.getElementById('badge-vendor-hf');
    const hfChk = document.getElementById('toggle-vendor-hf');
    if (hfEl && hfChk && v.huggingface) {
      hfEl.textContent = v.huggingface.enabled ? 'ENABLED' : 'DISABLED';
      hfEl.className = v.huggingface.enabled ? 'badge badge-info' : 'badge badge-danger';
      hfChk.checked = v.huggingface.enabled;
    }

    const vxEl = document.getElementById('badge-vendor-vertex');
    const vxChk = document.getElementById('toggle-vendor-vertex');
    if (vxEl && vxChk && v.vertex) {
      vxEl.textContent = v.vertex.enabled ? 'ENABLED' : 'DISABLED';
      vxEl.className = v.vertex.enabled ? 'badge badge-info' : 'badge badge-danger';
      vxChk.checked = v.vertex.enabled;
    }

    const agEl = document.getElementById('badge-vendor-antigravity');
    const agChk = document.getElementById('toggle-vendor-antigravity');
    if (agEl && agChk && v.antigravity) {
      agEl.textContent = v.antigravity.enabled ? 'ENABLED' : 'DISABLED';
      agEl.className = v.antigravity.enabled ? 'badge badge-info' : 'badge badge-danger';
      agChk.checked = v.antigravity.enabled;
    }
  }

  // Agent Activity Tracker
  if (data.agent_activity) {
    renderAgentActivity(data.agent_activity);
  }
}

// ==========================================================================
// Agent Activity Tracker Rendering
// ==========================================================================

function renderAgentActivity(act) {
  const taskIdEl = document.getElementById('agent-task-id');
  const objTitleEl = document.getElementById('agent-objective-title');
  const badgeEl = document.getElementById('agent-lifecycle-badge');

  if (taskIdEl) taskIdEl.textContent = act.task_id || 'TASK-STANDBY';
  if (objTitleEl) objTitleEl.textContent = act.objective || 'Observatory Agent Activity Tracker';
  if (badgeEl) {
    badgeEl.textContent = `STATE: ${act.workflow_status}`;
    badgeEl.className = act.workflow_status === 'COMPLETE' ? 'badge badge-success' : (act.workflow_status === 'FAILED' ? 'badge badge-danger' : 'badge badge-info');
  }

  const activeCountEl = document.getElementById('nav-agent-active-count');
  if (activeCountEl && act.personas) {
    const activeCount = act.personas.filter(p => p.status === 'ACTIVE' || p.status === 'REPAIRING').length;
    activeCountEl.textContent = `${activeCount || 0} active / ${act.personas.length}`;
  }

  // Lifecycle Pipeline Steps
  const order = ['INTAKE', 'PLANNING', 'CODING', 'TESTING', 'REVIEWING', 'DEBUGGING', 'COMPLETE'];
  const curIdx = order.indexOf(act.workflow_status);

  document.querySelectorAll('.lifecycle-step').forEach(node => {
    const step = node.getAttribute('data-step');
    const idx = order.indexOf(step);
    node.className = 'lifecycle-step';
    if (idx === curIdx) {
      node.classList.add('active');
    } else if (idx < curIdx || act.workflow_status === 'COMPLETE') {
      node.classList.add('completed');
    }
  });

  // Persona Grid
  const personasContainer = document.getElementById('agent-personas-container');
  if (personasContainer && act.personas) {
    const icons = {
      orchestrator: '⚡',
      planner: '📐',
      coder: '💻',
      tester: '🧪',
      reviewer: '🛡️',
      debugger: '🔍'
    };

    personasContainer.innerHTML = act.personas.map(p => {
      const icon = icons[p.persona] || '🤖';
      const activeClass = p.status === 'ACTIVE' ? 'active' : (p.status === 'REPAIRING' ? 'repairing' : '');
      const badgeClass = p.status === 'ACTIVE' ? 'badge-info' : (p.status === 'REPAIRING' ? 'badge-danger' : 'badge-success');

      let currentAction = 'Standing by in ready queue';
      if (p.status === 'ACTIVE') {
        currentAction = `⚡ Currently executing: ${p.role_description}`;
      } else if (p.status === 'REPAIRING') {
        currentAction = `🛠️ Performing repair iteration ${p.repair_iterations}`;
      }

      return `
        <div class="card glass-card agent-card ${activeClass}">
          <div class="persona-header">
            <div class="persona-avatar">${icon}</div>
            <div class="persona-meta">
              <span class="persona-title">${escapeHtml(p.name)}</span>
              <span class="persona-model font-mono">${escapeHtml(p.active_model)}</span>
            </div>
          </div>
          <p class="persona-role-desc">${escapeHtml(p.role_description)}</p>
          <div class="persona-action-box font-mono">
            <span class="text-dim">Action:</span> ${escapeHtml(currentAction)}
            ${p.current_subtask_id ? `<div class="subtask-binding text-dim">Target Subtask: <strong>${escapeHtml(p.current_subtask_id)}</strong></div>` : ''}
          </div>
          <div class="persona-footer">
            <span class="badge ${badgeClass}">${p.status}</span>
            <span class="font-mono text-dim">Repairs: ${p.repair_iterations} | Esc: ${p.escalation_count}</span>
          </div>
        </div>
      `;
    }).join('');
  }

  // Terminal Event Stream
  const termStream = document.getElementById('agent-terminal-stream');
  const logCountBadge = document.getElementById('log-count-badge');
  if (termStream && act.event_log) {
    if (logCountBadge) logCountBadge.textContent = `${act.event_log.length} EVENTS`;
    if (act.event_log.length === 0) {
      termStream.innerHTML = '<div class="log-line text-muted">[SYSTEM] Observatory Agent Event Stream connected...</div>';
    } else {
      termStream.innerHTML = act.event_log.map(line => `<div class="log-line">${escapeHtml(line)}</div>`).join('');
      termStream.scrollTop = termStream.scrollHeight;
    }
  }

  // Subtasks List
  const subtasksContainer = document.getElementById('agent-subtasks-container');
  if (subtasksContainer && act.subtasks) {
    if (act.subtasks.length === 0) {
      subtasksContainer.innerHTML = '<p class="text-muted">No subtasks in pipeline.</p>';
    } else {
      subtasksContainer.innerHTML = act.subtasks.map(st => {
        const badgeClass = st.status === 'RUNNING' ? 'badge-info' : (st.status === 'PASSED' || st.status === 'COMPLETE' ? 'badge-success' : 'badge-danger');
        return `
          <div class="subtask-item">
            <div class="subtask-info">
              <h5>[${st.id}] ${escapeHtml(st.name)}</h5>
              <span class="subtask-files font-mono">Modifying: ${(st.files_to_modify || []).join(', ') || 'N/A'}</span>
            </div>
            <span class="badge ${badgeClass}">${st.status}</span>
          </div>
        `;
      }).join('');
    }
  }
}

// ==========================================================================
// Feature Grid & Filtering
// ==========================================================================

function renderFeatures() {
  const query = state.searchQuery.toLowerCase().trim();
  const filter = state.activeFilter;

  const filtered = state.features.filter(f => {
    const matchesFilter = (filter === 'ALL' || f.subsystem === filter);
    if (!matchesFilter) return false;
    if (!query) return true;

    return f.id.toLowerCase().includes(query) ||
           f.name.toLowerCase().includes(query) ||
           f.description.toLowerCase().includes(query) ||
           f.module_path.toLowerCase().includes(query) ||
           (f.tier && f.tier.toLowerCase().includes(query));
  });

  elements.tabFeatCount.textContent = state.features.length;

  if (filtered.length === 0) {
    elements.featuresGrid.innerHTML = `
      <div class="glass-card" style="grid-column: 1 / -1; text-align: center; padding: 2rem;">
        <p class="text-muted">No features match current filter '${filter}' and query '${query}'</p>
      </div>`;
    return;
  }

  elements.featuresGrid.innerHTML = filtered.map(f => {
    const statusBadgeClass = f.status === 'OPERATIONAL' ? 'badge-success' : (f.status === 'TRIPPED' ? 'badge-danger' : 'badge-info');
    const subsystemColor = f.subsystem === 'Repomap' ? 'text-cyan' : (f.subsystem === 'Router' ? 'text-violet' : (f.subsystem === 'Orchestrator' ? 'text-amber' : 'text-emerald'));

    return `
      <div class="card glass-card feature-card" data-feature-id="${f.id}">
        <div class="feature-top">
          <div class="feature-meta-ribbon">
            <span class="feature-id-tag">${f.id}</span>
            <span class="badge ${statusBadgeClass}">${f.status}</span>
          </div>
          <h4 class="feature-title">${escapeHtml(f.name)}</h4>
          <p class="feature-desc">${escapeHtml(f.description)}</p>
        </div>
        <div class="feature-bottom">
          <span class="font-mono ${subsystemColor}">[${f.subsystem}] ${f.tier || ''}</span>
          ${f.metric_summary ? `<span class="feature-metric-summary">${escapeHtml(f.metric_summary)}</span>` : `<span class="font-mono text-dim">${f.module_path.split('/').pop()}</span>`}
        </div>
      </div>
    `;
  }).join('');

  // Attach card click handlers for details modal
  document.querySelectorAll('.feature-card').forEach(card => {
    card.addEventListener('click', () => {
      const fid = card.getAttribute('data-feature-id');
      const feat = state.features.find(x => x.id === fid);
      if (feat) openFeatureModal(feat);
    });
  });
}

function openFeatureModal(f) {
  elements.modalSubsystem.textContent = `${f.subsystem.toUpperCase()} // ${f.id}`;
  elements.modalTitle.textContent = f.name;
  elements.modalDesc.textContent = f.description;
  elements.modalFile.textContent = f.module_path;
  elements.modalTier.textContent = f.tier || 'Standard Component';
  elements.modalStatus.textContent = f.status;
  elements.modalStatus.className = `badge ${f.status === 'OPERATIONAL' ? 'badge-success' : (f.status === 'TRIPPED' ? 'badge-danger' : 'badge-info')}`;
  elements.modalDeps.textContent = (f.dependencies && f.dependencies.length > 0) ? f.dependencies.join(', ') : 'None (Independent Foundation)';

  elements.modal.classList.add('open');
}

// ==========================================================================
// Interactive Feature Probes
// ==========================================================================

async function runRouteProbe() {
  const prompt = elements.probeRoutePrompt.value.trim();
  const focusRaw = elements.probeRouteFocus.value.trim();
  const focus_files = focusRaw ? focusRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

  elements.btnRunRouteProbe.disabled = true;
  elements.btnRunRouteProbe.textContent = 'Routing...';
  elements.probeRouteOutput.textContent = '// Querying router pipeline...';

  try {
    const res = await fetch('/api/probe/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, focus_files })
    });
    const data = await res.json();
    if (data.success) {
      elements.probeRouteTierBadge.textContent = data.tier_selected;
      elements.probeRouteTierBadge.className = data.tier_selected.includes('Stage 1') ? 'badge badge-info' : 'badge badge-success';
      elements.probeRouteOutput.textContent = JSON.stringify(data.manifest, null, 2);
    } else {
      elements.probeRouteTierBadge.textContent = 'FAILED';
      elements.probeRouteTierBadge.className = 'badge badge-danger';
      elements.probeRouteOutput.textContent = `Error: ${data.error}`;
    }
  } catch (err) {
    elements.probeRouteOutput.textContent = `Network Error: ${err.message}`;
  } finally {
    elements.btnRunRouteProbe.disabled = false;
    elements.btnRunRouteProbe.textContent = 'Execute Route Test';
  }
}

async function runSkeletonProbe() {
  const filepath = elements.probeSkelFile.value.trim();
  const budget = parseInt(elements.probeSkelBudget.value, 10);

  elements.btnRunSkelProbe.disabled = true;
  elements.btnRunSkelProbe.textContent = 'Skeletonizing...';
  elements.probeSkelOutput.textContent = '// Parsing AST & pruning docstrings...';

  try {
    const res = await fetch('/api/probe/skeleton', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filepath, budget })
    });
    const data = await res.json();
    if (data.success) {
      elements.probeSkelMeta.textContent = `${data.skeleton_lines} lines (~${data.estimated_tokens} tokens) | ${data.pruning_mode}`;
      elements.probeSkelOutput.textContent = data.skeleton;
    } else {
      elements.probeSkelMeta.textContent = 'ERROR';
      elements.probeSkelOutput.textContent = `Error: ${data.error}`;
    }
  } catch (err) {
    elements.probeSkelOutput.textContent = `Network Error: ${err.message}`;
  } finally {
    elements.btnRunSkelProbe.disabled = false;
    elements.btnRunSkelProbe.textContent = 'Generate AST Skeleton';
  }
}

async function runBlastRadiusProbe() {
  const symbol = elements.probeBlastSymbol.value.trim();
  const direction = elements.probeBlastDir.value;
  const depth = parseInt(elements.probeBlastDepth.value, 10);

  elements.btnRunBlastProbe.disabled = true;
  elements.btnRunBlastProbe.textContent = 'Tracing...';
  elements.probeBlastOutput.textContent = '// Traversing micro/macro call graph...';

  try {
    const res = await fetch('/api/probe/blast_radius', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, direction, depth })
    });
    const data = await res.json();
    if (data.success) {
      elements.probeBlastMeta.textContent = `${data.upstream_count} callers, ${data.downstream_count} callees (depth <= ${depth})`;
      elements.probeBlastOutput.textContent = JSON.stringify(data.result, null, 2);
    } else {
      elements.probeBlastMeta.textContent = 'ERROR';
      elements.probeBlastOutput.textContent = `Error: ${data.error}`;
    }
  } catch (err) {
    elements.probeBlastOutput.textContent = `Network Error: ${err.message}`;
  } finally {
    elements.btnRunBlastProbe.disabled = false;
    elements.btnRunBlastProbe.textContent = 'Trace Blast Radius';
  }
}

// ==========================================================================
// Utilities & Event Listeners
// ==========================================================================

function escapeHtml(str) {
  if (typeof str !== 'string') return String(str);
  return str.replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[m]));
}

function setupEventListeners() {
  // Navigation Tabs
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPanel = document.getElementById(tab.getAttribute('data-tab'));
      if (targetPanel) targetPanel.classList.add('active');

      if (tab.getAttribute('data-tab') === 'tab-cache') {
        fetchCacheTableData();
      } else if (tab.getAttribute('data-tab') === 'tab-chat') {
        fetchChatHistory();
      }
    });
  });

  // Filter Pills
  elements.filterPills.forEach(btn => {
    btn.addEventListener('click', () => {
      elements.filterPills.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.activeFilter = btn.getAttribute('data-filter');
      renderFeatures();
    });
  });

  // Feature Search
  elements.featureSearchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value;
    renderFeatures();
  });

  // Modal Close
  elements.modalCloseBtn.addEventListener('click', () => elements.modal.classList.remove('open'));
  elements.modal.addEventListener('click', (e) => {
    if (e.target === elements.modal) elements.modal.classList.remove('open');
  });

  // Auto Refresh Toggle
  elements.autoRefreshCheck.addEventListener('change', (e) => {
    if (e.target.checked) {
      startPolling();
    } else {
      stopPolling();
    }
  });

  // Model Vendor Toggles
  document.querySelectorAll('.vendor-toggle').forEach(chk => {
    chk.addEventListener('change', async (e) => {
      const vendor = e.target.getAttribute('data-vendor');
      const enabled = e.target.checked;
      try {
        await fetch('/api/vendors/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ vendor, enabled })
        });
        fetchTelemetry();
      } catch (err) {
        console.error('Failed to toggle vendor:', err);
      }
    });
  });

  // Cache Selector
  elements.selectCacheTable.addEventListener('change', fetchCacheTableData);
  elements.btnRefreshCacheTable.addEventListener('click', fetchCacheTableData);

  // Probe Buttons
  elements.btnRunRouteProbe.addEventListener('click', runRouteProbe);
  elements.btnRunSkelProbe.addEventListener('click', runSkeletonProbe);
  elements.btnRunBlastProbe.addEventListener('click', runBlastRadiusProbe);

  // Slider Live Label
  elements.probeSkelBudget.addEventListener('input', (e) => {
    elements.budgetSliderVal.textContent = `${e.target.value} tokens`;
  });

  // Workflow Demo Trigger Button
  const btnTriggerStep = document.getElementById('btn-trigger-agent-step');
  if (btnTriggerStep) {
    btnTriggerStep.addEventListener('click', async () => {
      btnTriggerStep.disabled = true;
      btnTriggerStep.textContent = 'Stepping...';
      try {
        await fetch('/api/probe/agent_simulation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ objective: 'Refactor database storage layer and verify circuit breaker telemetry' })
        });
        await fetchTelemetry();
      } catch (err) {
        console.error('Agent step simulation error:', err);
      } finally {
        btnTriggerStep.disabled = false;
        btnTriggerStep.textContent = 'Step Workflow Demo';
      }
    });
  }
  // Chat Event Listeners
  setupChatListeners();
}

/* ==========================================================================
   AGENT CHAT HUB CONTROLLER
   ========================================================================== */

function setupChatListeners() {
  const personaItems = document.querySelectorAll('.persona-pick-item');
  const chatDisplay = document.getElementById('chat-target-display');
  const chatModelBadge = document.getElementById('chat-model-badge');
  const chatForm = document.getElementById('chat-input-form');
  const chatInput = document.getElementById('chat-prompt-input');
  const btnClearChat = document.getElementById('btn-clear-chat');
  const quickChips = document.querySelectorAll('.chip-btn');

  // Persona switching
  personaItems.forEach(item => {
    item.addEventListener('click', () => {
      personaItems.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      state.selectedPersona = item.getAttribute('data-persona');
      
      const name = item.querySelector('.persona-pick-name').textContent;
      if (chatDisplay) chatDisplay.textContent = `Agent Chat: ${name}`;

      const modelMap = {
        auto: 'Auto (Fast-Path / Flash)',
        orchestrator: 'gemini-2.0-flash-lite',
        planner: 'gemini-2.5-flash',
        coder: 'gemini-2.0-flash',
        tester: 'gemini-2.0-flash',
        reviewer: 'gemini-2.5-flash',
        debugger: 'gemini-2.5-flash'
      };
      if (chatModelBadge) chatModelBadge.textContent = modelMap[state.selectedPersona] || 'gemini-2.0-flash';
    });
  });

  // Quick chips
  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const preset = chip.getAttribute('data-preset');
      if (chatInput) {
        chatInput.value = preset;
        chatInput.focus();
      }
    });
  });

  // Form submit
  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      await handleChatSubmit();
    });
  }

  // Shift+Enter / Enter handling in textarea
  if (chatInput) {
    chatInput.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        await handleChatSubmit();
      }
    });
  }

  // Clear chat button
  if (btnClearChat) {
    btnClearChat.addEventListener('click', async () => {
      if (!confirm('Clear the agent conversation transcript?')) return;
      try {
        const res = await fetch('/api/chat/clear', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          state.chatMessages = data.messages || [];
          renderChatMessages();
        }
      } catch (err) {
        console.error('Failed to clear chat:', err);
      }
    });
  }
}

async function handleChatSubmit() {
  const chatInput = document.getElementById('chat-prompt-input');
  const btnSend = document.getElementById('btn-send-chat');
  const contextFilesInput = document.getElementById('chat-context-files');
  if (!chatInput || state.isChatSending) return;

  const text = chatInput.value.trim();
  if (!text) return;

  state.isChatSending = true;
  chatInput.disabled = true;
  if (btnSend) {
    btnSend.disabled = true;
    btnSend.innerHTML = `<span>Thinking...</span><span class="spinner-small"></span>`;
  }

  // Parse comma-separated context files
  let focusFiles = [];
  if (contextFilesInput && contextFilesInput.value.trim()) {
    focusFiles = contextFilesInput.value.split(',').map(s => s.trim()).filter(Boolean);
  }

  // Optimistically append user message to UI
  const optimisticUserMsg = {
    id: `opt_${Date.now()}`,
    sender: 'user',
    sender_name: 'You',
    role: 'user',
    content: text,
    timestamp: new Date().toLocaleTimeString(),
    target_persona: state.selectedPersona
  };
  state.chatMessages.push(optimisticUserMsg);
  renderChatMessages();
  chatInput.value = '';

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        persona: state.selectedPersona,
        context_files: focusFiles,
        backend: 'vertex'
      })
    });
    const result = await resp.json();
    if (result.success && result.message) {
      // Refresh transcript from server
      await fetchChatHistory();
      // Update telemetry spend counters
      fetchTelemetry();
    } else {
      alert(`Agent dispatch failed: ${result.error || 'Unknown error'}`);
    }
  } catch (err) {
    console.error('Chat dispatch error:', err);
    alert('Failed to connect to agent server endpoint.');
  } finally {
    state.isChatSending = false;
    chatInput.disabled = false;
    chatInput.focus();
    if (btnSend) {
      btnSend.disabled = false;
      btnSend.innerHTML = `<span>Dispatch to Agent</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>`;
    }
  }
}

async function fetchChatHistory() {
  try {
    const res = await fetch('/api/chat');
    const data = await res.json();
    if (data.messages) {
      state.chatMessages = data.messages;
      renderChatMessages();
    }
  } catch (err) {
    console.error('Failed to load chat history:', err);
  }
}

function renderChatMessages() {
  const container = document.getElementById('chat-messages-container');
  if (!container) return;

  if (!state.chatMessages || state.chatMessages.length === 0) {
    container.innerHTML = `<p class="text-muted" style="text-align: center; margin-top: 2rem;">No messages in transcript. Send an instruction below to begin.</p>`;
    return;
  }

  const personaAvatarMap = {
    user: '&#128100;',
    orchestrator: '&#128736;',
    planner: '&#128506;',
    coder: '&#128187;',
    tester: '&#129514;',
    reviewer: '&#128065;',
    debugger: '&#128269;'
  };

  container.innerHTML = state.chatMessages.map(msg => {
    const isUser = msg.role === 'user' || msg.sender === 'user';
    const avatar = personaAvatarMap[msg.sender] || (isUser ? '&#128100;' : '&#10024;');
    const formattedBody = formatMessageContent(msg.content);

    return `
      <div class="chat-msg ${isUser ? 'user' : 'assistant'}" id="${escapeHtml(msg.id || '')}">
        <div class="chat-msg-avatar">${avatar}</div>
        <div class="chat-msg-bubble">
          <div class="chat-msg-meta">
            <span class="chat-msg-sender">${escapeHtml(msg.sender_name || (isUser ? 'User' : msg.sender))}</span>
            <span class="chat-msg-time font-mono">${escapeHtml(msg.timestamp || '')}</span>
            ${msg.model ? `<span class="chat-msg-tag-badge font-mono text-cyan">${escapeHtml(msg.model)}</span>` : ''}
            ${msg.tokens ? `<span class="chat-msg-tag-badge font-mono text-muted">${msg.tokens} tok</span>` : ''}
            ${msg.routing_info ? `<span class="chat-msg-tag-badge text-amber">${escapeHtml(msg.routing_info)}</span>` : ''}
          </div>
          <div class="chat-msg-body">
            ${formattedBody}
          </div>
        </div>
      </div>
    `;
  }).join('');

  // Auto-scroll to bottom
  container.scrollTop = container.scrollHeight;
}

function formatMessageContent(raw) {
  if (!raw) return '';
  let str = escapeHtml(raw);

  // Fenced code blocks with optional language
  str = str.replace(/```([a-z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
  });

  // Inline code
  str = str.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headings
  str = str.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  str = str.replace(/^## (.*$)/gim, '<h3>$1</h3>');

  // Bold
  str = str.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Italic
  str = str.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Markdown lists
  str = str.replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>');
  str = str.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

  // Newlines to line breaks (outside pre)
  str = str.split(/(<pre>[\s\S]*?<\/pre>)/).map((segment, idx) => {
    if (idx % 2 === 1) return segment; // pre block, leave untouched
    return segment.replace(/\n\n+/g, '<br><br>').replace(/\n/g, '<br>');
  }).join('');

  return str;
}

function startPolling() {
  stopPolling();
  state.pollInterval = setInterval(fetchTelemetry, state.pollFrequencyMs);
}

function stopPolling() {
  if (state.pollInterval) {
    clearInterval(state.pollInterval);
    state.pollInterval = null;
  }
}

// Initial Boot
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  fetchTelemetry();
  startPolling();
});
