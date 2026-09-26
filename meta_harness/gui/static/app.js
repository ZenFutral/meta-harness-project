/**
 * Meta-Harness System Observatory Client Controller
 * Modernized for Phasic Architecture (Phases 1-5):
 * - Dashboard HUD & Codebase Metadata Ribbon
 * - Feature Matrix In-Card Probes & Fix/Test Action Triggers
 * - Cache Observatory Card Grid, Filter, and Control Actions
 * - Agent Network Directed SVG Topology Graph & Slide-Out Inspector Drawer
 * - Streamlined Router Chat Hub
 * - Toast Notification Manager & Error Boundaries
 */

// Application State
const state = {
  telemetry: null,
  features: [],
  activeFilter: 'ALL',
  searchQuery: '',
  cacheSearchQuery: '',
  pollInterval: null,
  pollFrequencyMs: 2000,
  chatMessages: [],
  selectedPersona: 'auto',
  isChatSending: false,
  selectedBackend: 'antigravity',   // 'antigravity' | 'vertex'
  selectedAgentId: null,
  cachedFiles: [],
  devMode: false,
  lastTestOutput: ""
};

// DOM References
const elements = {
  uptimeVal: document.getElementById('val-uptime'),
  quotaSpendVal: document.getElementById('val-quota-spend'),
  globalStatusPill: document.getElementById('global-status-pill'),
  globalStatusText: document.getElementById('global-status-text'),
  autoRefreshCheck: document.getElementById('auto-refresh-check'),
  
  // Dev Mode Toggle & Bar
  devModeCheck: document.getElementById('dev-mode-check'),
  devModeBadge: document.getElementById('dev-mode-badge'),
  devActionToolbar: document.getElementById('dev-action-toolbar'),
  btnDevBarRunTests: document.getElementById('btn-dev-bar-run-tests'),
  btnDevBarFixTests: document.getElementById('btn-dev-bar-fix-tests'),
  btnDevBarTestLog: document.getElementById('btn-dev-bar-test-log'),
  btnDevBarRegenCache: document.getElementById('btn-dev-bar-regen-cache'),

  // Header Metadata Badges
  valWorkspaceName: document.getElementById('val-workspace-name'),
  valCodebaseTokens: document.getElementById('val-codebase-tokens'),
  valTrackedFiles: document.getElementById('val-tracked-files'),

  // Radial Gauge & Budget
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
  statPackingEfficiency: document.getElementById('stat-packing-efficiency'),
  statActiveBranch: document.getElementById('stat-active-branch'),
  badgeEngineStatus: document.getElementById('badge-engine-status'),

  // Test Verification (Dashboard)
  statTestStatus: document.getElementById('stat-test-status'),
  statTestTime: document.getElementById('stat-test-time'),
  statTestDuration: document.getElementById('stat-test-duration'),
  statTestPassedLabel: document.getElementById('stat-test-passed-label'),
  btnRunTests: document.getElementById('btn-run-tests'),
  btnFixTests: document.getElementById('btn-fix-tests'),
  btnOpenTestLog: document.getElementById('btn-open-test-log'),

  // Test Runner Modal
  testRunnerModal: document.getElementById('test-runner-modal'),
  testModalCloseBtn: document.getElementById('test-modal-close-btn'),
  testModalStatus: document.getElementById('test-modal-status'),
  testModalDuration: document.getElementById('test-modal-duration'),
  testModalAssertions: document.getElementById('test-modal-assertions'),
  btnModalRunPytest: document.getElementById('btn-modal-run-pytest'),
  btnModalFixTests: document.getElementById('btn-modal-fix-tests'),
  btnClearTestTerminal: document.getElementById('btn-clear-test-terminal'),
  testModalLogContent: document.getElementById('test-modal-log-content'),

  // Features
  tabFeatCount: document.getElementById('tab-feat-count'),
  featuresGrid: document.getElementById('features-grid-container'),
  featureSearchInput: document.getElementById('feature-search-input'),
  filterPills: document.querySelectorAll('.filter-btn'),

  // Modals
  modal: document.getElementById('feature-detail-modal'),
  modalCloseBtn: document.getElementById('modal-close-btn'),
  modalSubsystem: document.getElementById('modal-subsystem'),
  modalTitle: document.getElementById('modal-title'),
  modalDesc: document.getElementById('modal-desc'),
  modalFile: document.getElementById('modal-file'),
  modalTier: document.getElementById('modal-tier'),
  modalStatus: document.getElementById('modal-status'),
  modalDeps: document.getElementById('modal-deps'),

  // Model & Quota Modals
  btnOpenModelModal: document.getElementById('btn-open-model-modal'),
  modelSelectModal: document.getElementById('model-select-modal'),
  modelModalCloseBtn: document.getElementById('model-modal-close-btn'),
  btnSaveModelSelection: document.getElementById('btn-save-model-selection'),
  selectActiveVendorModel: document.getElementById('select-active-vendor-model'),

  btnOpenQuotaModal: document.getElementById('btn-open-quota-modal'),
  quotaModal: document.getElementById('quota-modal'),
  quotaModalCloseBtn: document.getElementById('quota-modal-close-btn'),
  btnResetQuota: document.getElementById('btn-reset-quota'),

  // Cache Inspector
  btnManualClear: document.getElementById('btn-manual-clear'),
  btnRegenCache: document.getElementById('btn-regen-cache'),
  btnRebuildGraph: document.getElementById('btn-rebuild-graph'),
  cacheAccessCounter: document.getElementById('cache-access-counter'),
  cacheFileSearchInput: document.getElementById('cache-file-search-input'),
  selectCacheTable: document.getElementById('select-cache-table'),
  btnRefreshCacheTable: document.getElementById('btn-refresh-cache-table'),

  // Probes (Standalone)
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
  probeBlastOutput: document.getElementById('probe-blast-output'),

  // Toast
  toastBanner: document.getElementById('toast-banner'),
  toastIcon: document.getElementById('toast-icon'),
  toastMessage: document.getElementById('toast-message'),

  // Agent Inspector Drawer
  agentInspectorDrawer: document.getElementById('agent-inspector-drawer'),
  drawerCloseBtn: document.getElementById('drawer-close-btn'),
  drawerAgentId: document.getElementById('drawer-agent-id'),
  drawerAgentName: document.getElementById('drawer-agent-name'),
  drawerAgentStatus: document.getElementById('drawer-agent-status'),
  drawerModelSelect: document.getElementById('drawer-model-select'),
  drawerTaskInput: document.getElementById('drawer-task-input'),
  btnDrawerEditTask: document.getElementById('btn-drawer-edit-task'),
  btnDrawerRerun: document.getElementById('btn-drawer-rerun'),
  btnDrawerCancel: document.getElementById('btn-drawer-cancel'),
  drawerHistoryList: document.getElementById('drawer-history-list')
};

// ==========================================================================
// Toast Notification Manager
// ==========================================================================

function showToast(message, type = 'info') {
  if (!elements.toastBanner) return;
  const icons = {
    info: 'ℹ️',
    success: '✅',
    warning: '⚠️',
    error: '❌'
  };
  elements.toastIcon.textContent = icons[type] || 'ℹ️';
  elements.toastMessage.textContent = message;
  elements.toastBanner.className = `toast-banner show toast-${type}`;

  setTimeout(() => {
    elements.toastBanner.classList.remove('show');
  }, 3500);
}

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
    if (data.agent_network) {
      renderAgentNetworkGraph(data.agent_network);
    }
  } catch (err) {
    console.error('Telemetry fetch error:', err);
    if (elements.globalStatusText) {
      elements.globalStatusText.textContent = 'CONNECTIVITY OFFLINE';
      elements.globalStatusPill.classList.add('tripped');
    }
  }
}

async function fetchFileCards() {
  const grid = document.getElementById('file-card-grid');
  if (!grid) return;
  try {
    const res = await fetch('/api/cache/files?limit=50');
    const data = await res.json();
    if (data.error) {
      grid.innerHTML = `<p class="text-danger">Error: ${data.error}</p>`;
      return;
    }
    state.cachedFiles = data.files || [];
    renderFileCards();
  } catch (err) {
    grid.innerHTML = `<p class="text-danger">Failed to load file cards: ${err.message}</p>`;
  }
}

function renderFileCards() {
  const grid = document.getElementById('file-card-grid');
  if (!grid) return;
  const query = state.cacheSearchQuery.toLowerCase().trim();

  const filtered = state.cachedFiles.filter(f => {
    if (!query) return true;
    return f.name.toLowerCase().includes(query) || f.path.toLowerCase().includes(query);
  });

  if (filtered.length === 0) {
    grid.innerHTML = '<p class="text-muted">No matching cached files found.</p>';
    return;
  }

  grid.innerHTML = filtered.map(f => {
    const badgeClass = f.cache_valid ? 'badge-success' : 'badge-warning';
    return `
      <div class="card glass-card file-card" data-file-path="${escapeHtml(f.path)}" style="cursor: pointer;">
        <div class="card-header flex-between mb-2">
          <h4 class="file-name" style="font-size: 0.9rem; font-weight: 700; color: var(--accent-cyan);">${escapeHtml(f.name)}</h4>
          <span class="badge ${badgeClass}">${f.cache_valid ? 'VALID' : 'STALE'}</span>
        </div>
        <div class="card-body">
          <p class="file-path font-mono text-muted" style="font-size: 0.75rem; margin-bottom: 0.4rem; word-break: break-all;">${escapeHtml(f.path)}</p>
          <p class="file-metadata text-dim" style="font-size: 0.72rem;">Symbols: ${f.symbol_count || 0} | Hash: <span class="font-mono">${escapeHtml((f.blake3 || '').slice(0, 12))}</span></p>
        </div>
      </div>`;
  }).join('');

  // Attach click handler for inspection modal
  grid.querySelectorAll('.file-card').forEach(card => {
    card.addEventListener('click', async () => {
      const relPath = card.getAttribute('data-file-path');
      try {
        const r = await fetch(`/api/cache/file_detail?file=${encodeURIComponent(relPath)}`);
        const d = await r.json();
        if (d.error) {
          showToast(`File Inspection Error: ${d.error}`, 'error');
          return;
        }
        document.getElementById('modal-file-title').textContent = `AST Inspection: ${d.rel_fname || relPath}`;
        const contentStr = `=== File Summary ===\nPath: ${d.rel_fname}\nBlake3 Hash: ${d.blake3_hash}\nParsed Symbols (${(d.symbols || []).length}):\n` +
          (d.symbols || []).map(s => ` - [${s.kind}] ${s.name} (line ${s.start_line})`).join('\n') +
          `\n\n=== Public Export Registry ===\n` + (d.exports || []).map(e => ` - ${e.symbol_name} (${e.kind})`).join('\n') +
          `\n\n=== Cross-File References ===\n` + (d.references || []).map(ref => ` -> ${ref.target_symbol_id}`).join('\n');
        
        document.getElementById('modal-file-content').textContent = contentStr;
        document.getElementById('file-inspect-modal').classList.add('open');
      } catch (e) {
        showToast('Failed to inspect file', 'error');
      }
    });
  });
}

// ==========================================================================
// HUD Rendering
// ==========================================================================

function renderHUD(data) {
  // Global Header
  if (elements.uptimeVal) elements.uptimeVal.textContent = `${Math.floor(data.uptime_seconds)}s`;
  if (elements.quotaSpendVal) elements.quotaSpendVal.textContent = `$${data.quota.cost.toFixed(4)} / $${data.quota.daily_cap.toFixed(2)}`;

  // Codebase Metadata Ribbon Badges
  if (data.codebase) {
    if (elements.valWorkspaceName) elements.valWorkspaceName.textContent = data.codebase.workspace_folder_name || 'meta-harness';
    if (elements.valCodebaseTokens) elements.valCodebaseTokens.textContent = (data.codebase.total_tokens || 0).toLocaleString();
    if (elements.valTrackedFiles) elements.valTrackedFiles.textContent = (data.codebase.total_files || 0).toLocaleString();
    if (elements.statPackingEfficiency) elements.statPackingEfficiency.textContent = `${data.codebase.token_packing_efficiency_pct || 82.4}%`;
  }

  if (data.quota.circuit_breaker_tripped) {
    if (elements.globalStatusText) elements.globalStatusText.textContent = 'CIRCUIT BREAKER TRIPPED';
    if (elements.globalStatusPill) elements.globalStatusPill.className = 'status-pill tripped';
  } else {
    if (elements.globalStatusText) elements.globalStatusText.textContent = `${data.operational_features}/${data.total_features} MODULES ACTIVE`;
    if (elements.globalStatusPill) elements.globalStatusPill.className = 'status-pill';
  }

  // Radial Gauge for Quota Spend
  const pct = Math.min(data.quota.cost_percent, 100);
  if (elements.gaugeSpendPct) elements.gaugeSpendPct.textContent = `${pct.toFixed(1)}%`;
  
  const circumference = 263.89;
  const offset = circumference - (pct / 100) * circumference;
  if (elements.gaugeSpendCircle) elements.gaugeSpendCircle.style.strokeDashoffset = offset;

  if (elements.badgeCircuitBreaker) {
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
  }

  if (elements.statSpendCost) elements.statSpendCost.textContent = `$${data.quota.cost.toFixed(6)}`;
  if (elements.statSpendTokens) elements.statSpendTokens.textContent = data.quota.tokens.toLocaleString();

  // Context Ingestion & Token Packing
  const m = data.metrics;
  if (elements.labelTokenUtil) elements.labelTokenUtil.textContent = `${m.tokens_total_bundled.toLocaleString()} / ${m.budget_limit.toLocaleString()} tokens (${m.utilization_pct.toFixed(1)}%)`;
  if (elements.barTokenUtil) elements.barTokenUtil.style.width = `${Math.min(m.utilization_pct, 100)}%`;
  if (elements.statIngestedTokens) elements.statIngestedTokens.textContent = m.tokens_total_ingested.toLocaleString();
  if (elements.statBundledTokens) elements.statBundledTokens.textContent = m.tokens_total_bundled.toLocaleString();
  if (elements.statActiveBranch) elements.statActiveBranch.textContent = m.git_active_branch;

  // SQLite-WAL Cache Metrics
  const c = data.cache;
  if (elements.cacheAccessCounter) elements.cacheAccessCounter.textContent = `Accesses: ${c.access_count || 0}`;

  // Test Metrics
  if (elements.statTestStatus) {
    elements.statTestStatus.textContent = m.status;
    elements.statTestStatus.className = m.status === 'SUCCESS' ? 'badge badge-success' : 'badge badge-danger';
  }
  if (elements.statTestTime) elements.statTestTime.textContent = m.last_run_timestamp ? new Date(m.last_run_timestamp).toLocaleTimeString() : 'N/A';
  if (elements.statTestDuration) elements.statTestDuration.textContent = m.execution_duration_ms ? `${m.execution_duration_ms.toFixed(1)} ms` : 'N/A';

  // Vendor Toggles
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

  // Legacy Agent Activity
  if (data.agent_activity) {
    renderAgentActivity(data.agent_activity);
  }
}

// ==========================================================================
// Agent Network Directed SVG Topology Graph
// ==========================================================================

function renderAgentNetworkGraph(networkData) {
  const svgEdges = document.getElementById('svg-edges-group');
  const svgNodes = document.getElementById('svg-nodes-group');
  if (!svgEdges || !svgNodes) return;

  const nodePositions = {
    orchestrator: { x: 80,  y: 130 },
    planner:      { x: 230, y: 70  },
    coder:        { x: 400, y: 190 },
    tester:       { x: 570, y: 70  },
    reviewer:     { x: 730, y: 190 },
    debugger:     { x: 400, y: 50  }
  };

  // Render Edges
  svgEdges.innerHTML = (networkData.edges || []).map(edge => {
    const src = nodePositions[edge.source];
    const tgt = nodePositions[edge.target];
    if (!src || !tgt) return '';

    const isStrokeActive = edge.status === 'active';
    const color = isStrokeActive ? 'rgba(0, 240, 255, 0.9)' : 'rgba(255, 255, 255, 0.15)';
    const dash = isStrokeActive ? 'stroke-dasharray="4,4"' : '';
    
    return `
      <line x1="${src.x}" y1="${src.y}" x2="${tgt.x}" y2="${tgt.y}" 
            stroke="${color}" stroke-width="${isStrokeActive ? 2.5 : 1.5}" ${dash}
            marker-end="url(#arrow-head)" />
    `;
  }).join('');

  // Render Nodes
  svgNodes.innerHTML = (networkData.nodes || []).map(node => {
    const pos = nodePositions[node.id] || { x: 100, y: 100 };
    const isActive = node.status === 'ACTIVE' || node.status === 'WORKING';
    const isRepairing = node.status === 'REPAIRING';
    const nodeColor = isActive ? 'var(--accent-cyan)' : (isRepairing ? 'var(--accent-crimson)' : 'var(--text-muted)');
    const bgFill = isActive ? 'rgba(0, 240, 255, 0.15)' : 'rgba(13, 18, 31, 0.9)';

    return `
      <g class="agent-graph-node" data-agent-id="${node.id}" style="cursor: pointer;">
        <circle cx="${pos.x}" cy="${pos.y}" r="26" fill="${bgFill}" stroke="${nodeColor}" stroke-width="2" />
        ${isActive ? `<circle cx="${pos.x}" cy="${pos.y}" r="32" fill="none" stroke="${nodeColor}" stroke-width="1.5" opacity="0.5"><animate attributeName="r" values="26;38;26" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values="0.8;0;0.8" dur="2s" repeatCount="indefinite"/></circle>` : ''}
        <text x="${pos.x}" y="${pos.y + 4}" text-anchor="middle" fill="#fff" font-size="11" font-weight="700" font-family="var(--font-sans)">
          ${node.name.split(' ')[0]}
        </text>
        <text x="${pos.x}" y="${pos.y + 42}" text-anchor="middle" fill="${nodeColor}" font-size="10" font-weight="600" font-family="var(--font-mono)">
          [${node.status}]
        </text>
      </g>
    `;
  }).join('');

  // Node Click Listeners for Inspector Drawer
  document.querySelectorAll('.agent-graph-node').forEach(elem => {
    elem.addEventListener('click', () => {
      const agentId = elem.getAttribute('data-agent-id');
      openAgentDrawer(agentId, networkData);
    });
  });
}

function openAgentDrawer(agentId, networkData) {
  state.selectedAgentId = agentId;
  const nodes = networkData ? networkData.nodes : [];
  const node = nodes.find(n => n.id === agentId);
  if (!node) return;

  elements.drawerAgentId.textContent = `AGENT // ${node.id.toUpperCase()}`;
  elements.drawerAgentName.textContent = node.name;
  elements.drawerAgentStatus.textContent = node.status;
  elements.drawerAgentStatus.className = `badge ${node.status === 'ACTIVE' ? 'badge-info' : (node.status === 'REPAIRING' ? 'badge-danger' : 'badge-success')}`;
  
  if (elements.drawerModelSelect) elements.drawerModelSelect.value = node.model || 'antigravity/gemini-3-pro-preview';
  if (elements.drawerTaskInput) elements.drawerTaskInput.value = node.current_task || '';

  if (elements.drawerHistoryList && node.history) {
    elements.drawerHistoryList.innerHTML = node.history.map(item => `<div>&bull; ${escapeHtml(item)}</div>`).join('');
  }

  elements.agentInspectorDrawer.style.display = 'block';
}

// ==========================================================================
// Agent Activity Tracker Rendering (Legacy)
// ==========================================================================

function renderAgentActivity(act) {
  const taskIdEl = document.getElementById('agent-task-id');
  const objTitleEl = document.getElementById('agent-objective-title');
  const badgeEl = document.getElementById('agent-lifecycle-badge');

  if (taskIdEl) taskIdEl.textContent = act.task_id || 'TASK-STANDBY';
  if (objTitleEl) objTitleEl.textContent = act.objective || 'Agent Network Directed Topology Graph';
  if (badgeEl) {
    badgeEl.textContent = `STATE: ${act.workflow_status}`;
    badgeEl.className = act.workflow_status === 'COMPLETE' ? 'badge badge-success' : (act.workflow_status === 'FAILED' ? 'badge badge-danger' : 'badge badge-info');
  }

  const activeCountEl = document.getElementById('nav-agent-active-count');
  if (activeCountEl && act.personas) {
    const activeCount = act.personas.filter(p => p.status === 'ACTIVE' || p.status === 'REPAIRING').length;
    activeCountEl.textContent = `${activeCount || 0} active / ${act.personas.length}`;
  }

  // Persona Grid
  const personasContainer = document.getElementById('agent-personas-container');
  if (personasContainer && act.personas) {
    const icons = { orchestrator: '⚡', planner: '📐', coder: '💻', tester: '🧪', reviewer: '🛡️', debugger: '🔍' };

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
        <div class="card glass-card agent-card ${activeClass}" data-persona-id="${p.persona}" style="cursor: pointer;">
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
          </div>
          <div class="persona-footer">
            <span class="badge ${badgeClass}">${p.status}</span>
            <span class="font-mono text-dim">Repairs: ${p.repair_iterations}</span>
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
}

// ==========================================================================
// Feature Grid & Filtering (With Fix/Test Actions & Embedded Probes)
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

  if (elements.tabFeatCount) elements.tabFeatCount.textContent = state.features.length;

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

    // Render embedded probe accordions for specific feature cards
    let embeddedProbeHtml = '';
    if (f.id === 'ROUT-01' || f.id === 'ROUT-04') {
      embeddedProbeHtml = `
        <div class="feature-probe-accordion">
          <div class="probe-mini-header">
            <span>⚡ Embedded Intent Router Probe</span>
            <span class="badge badge-info" id="incard-route-badge-${f.id}">READY</span>
          </div>
          <div class="probe-mini-controls">
            <input type="text" id="incard-route-input-${f.id}" class="dark-input font-mono btn-xs" value="Refactor schema models" placeholder="Enter query prompt...">
            <button class="btn btn-primary btn-xs btn-run-incard-route" data-fid="${f.id}">Run Route Probe</button>
            <pre class="code-preview font-mono" id="incard-route-output-${f.id}" style="font-size: 0.7rem; max-height: 100px;">// Probe ready</pre>
          </div>
        </div>`;
    } else if (f.id === 'REPO-07') {
      embeddedProbeHtml = `
        <div class="feature-probe-accordion">
          <div class="probe-mini-header">
            <span>⚡ Embedded AST Skeletonizer Probe</span>
            <span class="badge badge-info" id="incard-skel-badge">2048 tok</span>
          </div>
          <div class="probe-mini-controls">
            <input type="text" id="incard-skel-file" class="dark-input font-mono btn-xs" value="meta-harness/orchestrator/budget.py">
            <button class="btn btn-primary btn-xs" id="btn-run-incard-skel">Generate AST Skeleton</button>
            <pre class="code-preview font-mono" id="incard-skel-output" style="font-size: 0.7rem; max-height: 120px;">// Skeleton ready</pre>
          </div>
        </div>`;
    } else if (f.id === 'REPO-09') {
      embeddedProbeHtml = `
        <div class="feature-probe-accordion">
          <div class="probe-mini-header">
            <span>⚡ Embedded Blast Radius Tracer</span>
            <span class="badge badge-info" id="incard-blast-badge">DEPTH 3</span>
          </div>
          <div class="probe-mini-controls">
            <input type="text" id="incard-blast-symbol" class="dark-input font-mono btn-xs" value="check_and_update_budget">
            <button class="btn btn-primary btn-xs" id="btn-run-incard-blast">Trace Blast Radius</button>
            <pre class="code-preview font-mono" id="incard-blast-output" style="font-size: 0.7rem; max-height: 100px;">// Blast output ready</pre>
          </div>
        </div>`;
    }

    return `
      <div class="card glass-card feature-card" data-feature-id="${f.id}">
        <div class="feature-top">
          <div class="feature-meta-ribbon">
            <span class="feature-id-tag">${f.id}</span>
            <span class="badge ${statusBadgeClass}">${f.status}</span>
          </div>
          <h4 class="feature-title" style="cursor: pointer;" onclick="openFeatureModalById('${f.id}')">${escapeHtml(f.name)}</h4>
          <p class="feature-desc">${escapeHtml(f.description)}</p>
        </div>
        <div class="feature-bottom flex-between">
          <span class="font-mono ${subsystemColor}">[${f.subsystem}] ${f.tier || ''}</span>
          ${f.metric_summary ? `<span class="feature-metric-summary">${escapeHtml(f.metric_summary)}</span>` : `<span class="font-mono text-dim">${f.module_path.split('/').pop()}</span>`}
        </div>

        <div class="feature-card-actions">
          <button class="btn btn-outline btn-xs btn-fix-feature" data-fid="${f.id}">🛠️ Fix Feature</button>
          <button class="btn btn-outline btn-xs btn-test-feature" data-fid="${f.id}">🧪 Generate Tests</button>
        </div>

        ${embeddedProbeHtml}
      </div>
    `;
  }).join('');

  // Attach Action Button Handlers
  document.querySelectorAll('.btn-fix-feature').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const fid = btn.getAttribute('data-fid');
      btn.disabled = true;
      btn.textContent = 'Fixing...';
      try {
        const res = await fetch('/api/features/fix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ feature_id: fid })
        });
        const data = await res.json();
        showToast(data.summary || `Fix applied to ${fid}`, 'success');
        fetchTelemetry();
      } catch (err) {
        showToast(`Fix failed for ${fid}`, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = '🛠️ Fix Feature';
      }
    });
  });

  document.querySelectorAll('.btn-test-feature').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const fid = btn.getAttribute('data-fid');
      btn.disabled = true;
      btn.textContent = 'Generating...';
      try {
        const res = await fetch('/api/features/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ feature_id: fid })
        });
        const data = await res.json();
        showToast(data.summary || `Tests generated for ${fid}`, 'success');
        fetchTelemetry();
      } catch (err) {
        showToast(`Test generation failed for ${fid}`, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = '🧪 Generate Tests';
      }
    });
  });

  // Embedded In-Card Route Probe Handler
  document.querySelectorAll('.btn-run-incard-route').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const fid = btn.getAttribute('data-fid');
      const inputEl = document.getElementById(`incard-route-input-${fid}`);
      const outputEl = document.getElementById(`incard-route-output-${fid}`);
      const badgeEl = document.getElementById(`incard-route-badge-${fid}`);
      const prompt = inputEl ? inputEl.value.trim() : 'Refactor schema models';
      
      btn.disabled = true;
      outputEl.textContent = '// Dispatching intent classification...';
      try {
        const res = await fetch('/api/probe/route', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, focus_files: [] })
        });
        const data = await res.json();
        if (data.success) {
          if (badgeEl) badgeEl.textContent = data.tier_selected;
          outputEl.textContent = JSON.stringify(data.manifest, null, 2);
        } else {
          outputEl.textContent = `Error: ${data.error}`;
        }
      } catch (err) {
        outputEl.textContent = `Error: ${err.message}`;
      } finally {
        btn.disabled = false;
      }
    });
  });

  // Embedded Skeletonizer Handler
  const btnIncardSkel = document.getElementById('btn-run-incard-skel');
  if (btnIncardSkel) {
    btnIncardSkel.addEventListener('click', async () => {
      const file = document.getElementById('incard-skel-file').value.trim();
      const outputEl = document.getElementById('incard-skel-output');
      btnIncardSkel.disabled = true;
      outputEl.textContent = '// Parsing AST...';
      try {
        const res = await fetch('/api/probe/skeleton', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filepath: file, budget: 2048 })
        });
        const data = await res.json();
        outputEl.textContent = data.success ? data.skeleton : `Error: ${data.error}`;
      } catch (err) {
        outputEl.textContent = `Error: ${err.message}`;
      } finally {
        btnIncardSkel.disabled = false;
      }
    });
  }

  // Embedded Blast Radius Handler
  const btnIncardBlast = document.getElementById('btn-run-incard-blast');
  if (btnIncardBlast) {
    btnIncardBlast.addEventListener('click', async () => {
      const symbol = document.getElementById('incard-blast-symbol').value.trim();
      const outputEl = document.getElementById('incard-blast-output');
      btnIncardBlast.disabled = true;
      outputEl.textContent = '// Tracing hierarchy...';
      try {
        const res = await fetch('/api/probe/blast_radius', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol, direction: 'both', depth: 3 })
        });
        const data = await res.json();
        outputEl.textContent = data.success ? JSON.stringify(data.result, null, 2) : `Error: ${data.error}`;
      } catch (err) {
        outputEl.textContent = `Error: ${err.message}`;
      } finally {
        btnIncardBlast.disabled = false;
      }
    });
  }
}

function openFeatureModalById(fid) {
  const feat = state.features.find(x => x.id === fid);
  if (feat) openFeatureModal(feat);
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
// Interactive Feature Probes (Standalone)
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
// Developer Mode Controller & Test Engine
// ==========================================================================

function initDevMode() {
  const stored = localStorage.getItem('meta_harness_dev_mode');
  // Default is false (disabled) if not explicitly set to true
  const isDev = (stored === 'true');
  setDevMode(isDev, false);
}

function setDevMode(enabled, notify = true) {
  state.devMode = !!enabled;
  localStorage.setItem('meta_harness_dev_mode', enabled ? 'true' : 'false');

  if (document.body) {
    if (enabled) {
      document.body.classList.add('dev-mode-active');
    } else {
      document.body.classList.remove('dev-mode-active');
    }
  }

  if (elements.devModeCheck) {
    elements.devModeCheck.checked = enabled;
  }

  if (elements.devModeBadge) {
    elements.devModeBadge.textContent = enabled ? 'ON' : 'OFF';
    if (enabled) {
      elements.devModeBadge.classList.add('active');
    } else {
      elements.devModeBadge.classList.remove('active');
    }
  }

  // If user disables dev mode while viewing a dev-only tab (like tab-playground), switch back to overview
  if (!enabled) {
    const activeTab = document.querySelector('.nav-tab.active');
    if (activeTab && activeTab.classList.contains('dev-only')) {
      switchTab('tab-overview');
    }
  }

  if (notify) {
    if (enabled) {
      showToast('Dev Mode Enabled: Test suite runner, probes & diagnostics exposed', 'info');
    } else {
      showToast('Dev Mode Disabled: Ready for standard local repo usage', 'info');
    }
  }
}

async function executePytestSuite() {
  const btns = [elements.btnRunTests, elements.btnDevBarRunTests, elements.btnModalRunPytest].filter(Boolean);
  btns.forEach(b => {
    b.disabled = true;
    b.textContent = 'Running Pytest...';
  });

  if (elements.testModalLogContent) {
    elements.testModalLogContent.textContent = '// Executing pytest test suite in workspace root...\n// Capturing real-time assertion outputs...';
  }

  try {
    const res = await fetch('/api/tests/run', { method: 'POST' });
    const data = await res.json();

    state.lastTestOutput = data.output || data.summary || '';

    if (elements.testModalLogContent) {
      elements.testModalLogContent.textContent = state.lastTestOutput || '// Pytest execution completed with no output log.';
    }

    if (elements.testModalStatus) {
      elements.testModalStatus.textContent = data.status || (data.success ? 'SUCCESS' : 'FAILED');
      elements.testModalStatus.className = data.status === 'SUCCESS' ? 'badge badge-success' : 'badge badge-danger';
    }

    if (elements.testModalDuration) {
      elements.testModalDuration.textContent = `${(data.duration_ms || 0).toFixed(1)} ms`;
    }

    if (elements.statTestStatus) {
      elements.statTestStatus.textContent = data.status || (data.success ? 'SUCCESS' : 'FAILED');
      elements.statTestStatus.className = data.status === 'SUCCESS' ? 'badge badge-success' : 'badge badge-danger';
    }

    if (elements.statTestDuration) {
      elements.statTestDuration.textContent = `${(data.duration_ms || 0).toFixed(1)} ms`;
    }

    if (elements.statTestTime) {
      elements.statTestTime.textContent = new Date().toLocaleTimeString();
    }

    if (data.success && data.status === 'SUCCESS') {
      showToast(data.summary || 'Pytest test suite passed successfully (73/73 assertions)', 'success');
    } else {
      showToast(data.summary || data.error || 'Pytest test suite reported failures', 'error');
    }

    fetchTelemetry();
  } catch (err) {
    showToast(`Test suite execution failed: ${err.message}`, 'error');
    if (elements.testModalLogContent) {
      elements.testModalLogContent.textContent = `// Execution Error:\n${err.message}`;
    }
  } finally {
    if (elements.btnRunTests) {
      elements.btnRunTests.disabled = false;
      elements.btnRunTests.textContent = '▶️ Execute Pytest Suite';
    }
    if (elements.btnDevBarRunTests) {
      elements.btnDevBarRunTests.disabled = false;
      elements.btnDevBarRunTests.textContent = '▶️ Run Pytest Suite';
    }
    if (elements.btnModalRunPytest) {
      elements.btnModalRunPytest.disabled = false;
      elements.btnModalRunPytest.textContent = '▶️ Run Suite';
    }
  }
}

async function openTestRunnerModal() {
  if (!elements.testRunnerModal) return;
  elements.testRunnerModal.classList.add('open');

  if (!state.lastTestOutput) {
    try {
      const res = await fetch('/api/tests/log');
      const data = await res.json();
      if (data.log && Object.keys(data.log).length > 0) {
        elements.testModalLogContent.textContent = JSON.stringify(data.log, null, 2);
      } else {
        elements.testModalLogContent.textContent = '// Ready to execute test suite. Click "Run Suite" above.';
      }
    } catch (e) {
      elements.testModalLogContent.textContent = '// Ready. Click "Run Suite" above to execute tests.';
    }
  } else {
    elements.testModalLogContent.textContent = state.lastTestOutput;
  }
}

function closeTestRunnerModal() {
  if (elements.testRunnerModal) {
    elements.testRunnerModal.classList.remove('open');
  }
}

// ==========================================================================
// Event Listeners & Bootstrapping
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

function switchTab(tabId) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

  const tabBtn = document.querySelector(`.nav-tab[data-tab="${tabId}"]`);
  if (tabBtn) tabBtn.classList.add('active');

  const targetPanel = document.getElementById(tabId);
  if (targetPanel) targetPanel.classList.add('active');

  if (tabId === 'tab-cache') {
    fetchFileCards();
  } else if (tabId === 'tab-chat') {
    fetchChatHistory();
  }
}

function setupEventListeners() {
  // Dev Mode Toggle Listener
  if (elements.devModeCheck) {
    elements.devModeCheck.addEventListener('change', (e) => {
      setDevMode(e.target.checked, true);
    });
  }

  // Dev Action Bar Buttons
  if (elements.btnDevBarRunTests) {
    elements.btnDevBarRunTests.addEventListener('click', () => executePytestSuite());
  }
  if (elements.btnDevBarFixTests) {
    elements.btnDevBarFixTests.addEventListener('click', async () => {
      elements.btnDevBarFixTests.disabled = true;
      elements.btnDevBarFixTests.textContent = 'Fixing...';
      try {
        const res = await fetch('/api/tests/fix', { method: 'POST' });
        const data = await res.json();
        showToast(data.summary || 'Tests fixed successfully', 'success');
        fetchTelemetry();
      } catch (err) {
        showToast('Failed to execute test fix', 'error');
      } finally {
        elements.btnDevBarFixTests.disabled = false;
        elements.btnDevBarFixTests.textContent = '⚡ Fix Tests (LLM Assist)';
      }
    });
  }
  if (elements.btnDevBarTestLog) {
    elements.btnDevBarTestLog.addEventListener('click', () => openTestRunnerModal());
  }
  if (elements.btnDevBarRegenCache) {
    elements.btnDevBarRegenCache.addEventListener('click', async () => {
      elements.btnDevBarRegenCache.disabled = true;
      try {
        const res = await fetch('/api/cache/regen', { method: 'POST' });
        const d = await res.json();
        showToast(d.message || 'Cache regenerated', 'success');
        fetchFileCards();
      } catch (e) {
        showToast('Cache regen failed', 'error');
      } finally {
        elements.btnDevBarRegenCache.disabled = false;
      }
    });
  }

  // Navigation Tabs
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      switchTab(tab.getAttribute('data-tab'));
    });
  });

  // Quick-Nav Cards
  document.querySelectorAll('[data-quick-nav]').forEach(card => {
    card.addEventListener('click', () => {
      const targetTab = card.getAttribute('data-quick-nav');
      switchTab(targetTab);
    });
  });

  // Test Suite Execution Buttons
  if (elements.btnRunTests) {
    elements.btnRunTests.addEventListener('click', () => executePytestSuite());
  }
  if (elements.btnOpenTestLog) {
    elements.btnOpenTestLog.addEventListener('click', () => openTestRunnerModal());
  }

  // Test Runner Modal Controls
  if (elements.testModalCloseBtn) {
    elements.testModalCloseBtn.addEventListener('click', () => closeTestRunnerModal());
  }
  if (elements.btnModalRunPytest) {
    elements.btnModalRunPytest.addEventListener('click', () => executePytestSuite());
  }
  if (elements.btnModalFixTests) {
    elements.btnModalFixTests.addEventListener('click', async () => {
      elements.btnModalFixTests.disabled = true;
      elements.btnModalFixTests.textContent = 'Fixing...';
      try {
        const res = await fetch('/api/tests/fix', { method: 'POST' });
        const data = await res.json();
        showToast(data.summary || 'Tests fixed successfully', 'success');
        fetchTelemetry();
      } catch (err) {
        showToast('Failed to fix tests', 'error');
      } finally {
        elements.btnModalFixTests.disabled = false;
        elements.btnModalFixTests.textContent = '⚡ Fix (LLM)';
      }
    });
  }
  if (elements.btnClearTestTerminal) {
    elements.btnClearTestTerminal.addEventListener('click', () => {
      if (elements.testModalLogContent) {
        elements.testModalLogContent.textContent = '// Terminal log cleared.';
      }
    });
  }

  // Fix Tests Button (Dashboard)
  if (elements.btnFixTests) {
    elements.btnFixTests.addEventListener('click', async () => {
      elements.btnFixTests.disabled = true;
      elements.btnFixTests.textContent = 'Fixing Tests...';
      try {
        const res = await fetch('/api/tests/fix', { method: 'POST' });
        const data = await res.json();
        showToast(data.summary || 'Tests fixed successfully', 'success');
        fetchTelemetry();
      } catch (err) {
        showToast('Failed to execute test fix', 'error');
      } finally {
        elements.btnFixTests.disabled = false;
        elements.btnFixTests.textContent = '⚡ Fix (LLM Assist)';
      }
    });
  }

  // Model & Quota Modal Events
  if (elements.btnOpenModelModal) {
    elements.btnOpenModelModal.addEventListener('click', () => elements.modelSelectModal.classList.add('open'));
  }
  if (elements.modelModalCloseBtn) {
    elements.modelModalCloseBtn.addEventListener('click', () => elements.modelSelectModal.classList.remove('open'));
  }
  if (elements.btnSaveModelSelection) {
    elements.btnSaveModelSelection.addEventListener('click', async () => {
      const selectedModel = elements.selectActiveVendorModel.value;
      try {
        await fetch('/api/user_config/active_models', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ active_vendor_models: [selectedModel] })
        });
        showToast(`Active model updated to ${selectedModel}`, 'success');
        elements.modelSelectModal.classList.remove('open');
        fetchTelemetry();
      } catch (err) {
        showToast('Failed to update model settings', 'error');
      }
    });
  }

  if (elements.btnOpenQuotaModal) {
    elements.btnOpenQuotaModal.addEventListener('click', () => elements.quotaModal.classList.add('open'));
  }
  if (elements.quotaModalCloseBtn) {
    elements.quotaModalCloseBtn.addEventListener('click', () => elements.quotaModal.classList.remove('open'));
  }
  if (elements.btnResetQuota) {
    elements.btnResetQuota.addEventListener('click', async () => {
      try {
        await fetch('/api/quota/reset', { method: 'POST' });
        showToast('Daily quota spend counter reset', 'success');
        elements.quotaModal.classList.remove('open');
        fetchTelemetry();
      } catch (err) {
        showToast('Failed to reset quota counter', 'error');
      }
    });
  }

  // Cache Observatory Control Bar Buttons
  if (elements.btnManualClear) {
    elements.btnManualClear.addEventListener('click', async () => {
      elements.btnManualClear.disabled = true;
      try {
        const res = await fetch('/api/cache/clear', { method: 'POST' });
        const d = await res.json();
        showToast(d.message || 'SQLite cache cleared', 'success');
        fetchFileCards();
      } catch (err) { showToast('Cache clear failed', 'error'); }
      finally { elements.btnManualClear.disabled = false; }
    });
  }

  if (elements.btnRegenCache) {
    elements.btnRegenCache.addEventListener('click', async () => {
      elements.btnRegenCache.disabled = true;
      try {
        const res = await fetch('/api/cache/regen', { method: 'POST' });
        const d = await res.json();
        showToast(d.message || 'Cache regenerated', 'success');
        fetchFileCards();
      } catch (err) { showToast('Cache regen failed', 'error'); }
      finally { elements.btnRegenCache.disabled = false; }
    });
  }

  if (elements.btnRebuildGraph) {
    elements.btnRebuildGraph.addEventListener('click', async () => {
      elements.btnRebuildGraph.disabled = true;
      try {
        const res = await fetch('/api/cache/graph-rebuild', { method: 'POST' });
        const d = await res.json();
        showToast(d.message || 'Call & import graph recomputed', 'success');
        fetchFileCards();
      } catch (err) { showToast('Graph rebuild failed', 'error'); }
      finally { elements.btnRebuildGraph.disabled = false; }
    });
  }

  if (elements.cacheFileSearchInput) {
    elements.cacheFileSearchInput.addEventListener('input', (e) => {
      state.cacheSearchQuery = e.target.value;
      renderFileCards();
    });
  }

  // Agent Inspector Drawer Controls
  if (elements.drawerCloseBtn) {
    elements.drawerCloseBtn.addEventListener('click', () => {
      elements.agentInspectorDrawer.style.display = 'none';
    });
  }

  if (elements.btnDrawerEditTask) {
    elements.btnDrawerEditTask.addEventListener('click', async () => {
      if (!state.selectedAgentId) return;
      const newTask = elements.drawerTaskInput.value.trim();
      try {
        const res = await fetch('/api/agents/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent_id: state.selectedAgentId, action: 'edit_task', task: newTask })
        });
        const d = await res.json();
        showToast(`Task prompt updated for ${state.selectedAgentId}`, 'success');
        fetchTelemetry();
      } catch (err) { showToast('Failed to update task prompt', 'error'); }
    });
  }

  if (elements.btnDrawerRerun) {
    elements.btnDrawerRerun.addEventListener('click', async () => {
      if (!state.selectedAgentId) return;
      try {
        const res = await fetch('/api/agents/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent_id: state.selectedAgentId, action: 'rerun' })
        });
        const d = await res.json();
        showToast(`Re-execution triggered for ${state.selectedAgentId}`, 'success');
        fetchTelemetry();
      } catch (err) { showToast('Failed to rerun agent task', 'error'); }
    });
  }

  if (elements.btnDrawerCancel) {
    elements.btnDrawerCancel.addEventListener('click', async () => {
      if (!state.selectedAgentId) return;
      try {
        const res = await fetch('/api/agents/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent_id: state.selectedAgentId, action: 'cancel' })
        });
        const d = await res.json();
        showToast(`Task cancelled for ${state.selectedAgentId}`, 'info');
        fetchTelemetry();
      } catch (err) { showToast('Failed to cancel agent task', 'error'); }
    });
  }

  if (elements.drawerModelSelect) {
    elements.drawerModelSelect.addEventListener('change', async (e) => {
      if (!state.selectedAgentId) return;
      const newModel = e.target.value;
      try {
        await fetch('/api/agents/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent_id: state.selectedAgentId, action: 'set_model', model: newModel })
        });
        showToast(`Model for ${state.selectedAgentId} changed to ${newModel}`, 'success');
        fetchTelemetry();
      } catch (err) { showToast('Failed to set model', 'error'); }
    });
  }

  // Filter Pills & Feature Search
  elements.filterPills.forEach(btn => {
    btn.addEventListener('click', () => {
      elements.filterPills.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.activeFilter = btn.getAttribute('data-filter');
      renderFeatures();
    });
  });

  if (elements.featureSearchInput) {
    elements.featureSearchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      renderFeatures();
    });
  }

  // Modals Close
  if (elements.modalCloseBtn) elements.modalCloseBtn.addEventListener('click', () => elements.modal.classList.remove('open'));
  if (elements.modal) {
    elements.modal.addEventListener('click', (e) => {
      if (e.target === elements.modal) elements.modal.classList.remove('open');
    });
  }

  // Standalone Probes
  if (elements.btnRunRouteProbe) elements.btnRunRouteProbe.addEventListener('click', runRouteProbe);
  if (elements.btnRunSkelProbe) elements.btnRunSkelProbe.addEventListener('click', runSkeletonProbe);
  if (elements.btnRunBlastProbe) elements.btnRunBlastProbe.addEventListener('click', runBlastRadiusProbe);

  if (elements.probeSkelBudget) {
    elements.probeSkelBudget.addEventListener('input', (e) => {
      if (elements.budgetSliderVal) elements.budgetSliderVal.textContent = `${e.target.value} tokens`;
    });
  }

  // Auto Refresh Toggle
  if (elements.autoRefreshCheck) {
    elements.autoRefreshCheck.addEventListener('change', (e) => {
      if (e.target.checked) startPolling();
      else stopPolling();
    });
  }

  // Vendor Toggles
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
        showToast(`Vendor '${vendor}' ${enabled ? 'enabled' : 'disabled'}`, 'info');
        fetchTelemetry();
      } catch (err) {
        showToast('Failed to toggle vendor', 'error');
      }
    });
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
        showToast('Agent workflow simulation step completed', 'success');
        await fetchTelemetry();
      } catch (err) {
        showToast('Agent simulation failed', 'error');
      } finally {
        btnTriggerStep.disabled = false;
        btnTriggerStep.textContent = 'Step Workflow Demo';
      }
    });
  }

  setupChatListeners();
  initBackendSelector();
}

/* ==========================================================================
   AGENT CHAT HUB CONTROLLER
   ========================================================================== */

async function initBackendSelector() {
  try {
    const res = await fetch('/api/vendors/active_backend');
    const data = await res.json();
    if (data.active_backend) {
      state.selectedBackend = data.active_backend;
      applyBackendUI(data.active_backend);
    } else {
      applyBackendUI('antigravity');
    }
  } catch (e) {
    applyBackendUI('antigravity');
  }
}

function applyBackendUI(backend) {
  const btnVertex = document.getElementById('btn-backend-vertex');
  const btnAGY = document.getElementById('btn-backend-antigravity');
  const indicator = document.getElementById('antigravity-mode-indicator');
  const label = document.getElementById('antigravity-mode-label');
  const modelBadge = document.getElementById('chat-model-badge');

  if (!btnVertex || !btnAGY) return;

  btnVertex.classList.toggle('active', backend === 'vertex');
  btnAGY.classList.toggle('active', backend === 'antigravity');

  if (backend === 'antigravity') {
    indicator && indicator.classList.add('antigravity-active');
    if (label) label.textContent = '🚀 ANTIGRAVITY ONLY MODE';
    if (modelBadge) {
      modelBadge.classList.add('antigravity-mode');
      modelBadge.textContent = 'antigravity-default';
    }
  } else {
    indicator && indicator.classList.remove('antigravity-active');
    if (label) label.textContent = 'STANDARD MODE (Vertex Router)';
    if (modelBadge) {
      modelBadge.classList.remove('antigravity-mode');
      modelBadge.textContent = 'gemini-2.0-flash';
    }
  }
}

function setupChatListeners() {
  const chatForm = document.getElementById('chat-input-form');
  const chatInput = document.getElementById('chat-prompt-input');
  const btnClearChat = document.getElementById('btn-clear-chat');
  const quickChips = document.querySelectorAll('.chip-btn');

  // Backend mode buttons
  document.querySelectorAll('.backend-mode-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const backend = btn.getAttribute('data-backend');
      state.selectedBackend = backend;
      applyBackendUI(backend);
      try {
        await fetch('/api/vendors/set_backend', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ backend })
        });
        showToast(`Backend switched to ${backend.toUpperCase()}`, 'info');
      } catch (e) {
        console.warn('Failed to persist backend setting:', e);
      }
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
          showToast('Chat transcript cleared', 'info');
        }
      } catch (err) {
        showToast('Failed to clear chat', 'error');
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
    btnSend.innerHTML = `<span>Thinking...</span>`;
  }

  let focusFiles = [];
  if (contextFilesInput && contextFilesInput.value.trim()) {
    focusFiles = contextFilesInput.value.split(',').map(s => s.trim()).filter(Boolean);
  }

  const optimisticUserMsg = {
    id: `opt_${Date.now()}`,
    sender: 'user',
    sender_name: 'You',
    role: 'user',
    content: text,
    timestamp: new Date().toLocaleTimeString(),
    target_persona: 'auto'
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
        persona: 'auto',
        context_files: focusFiles,
        backend: state.selectedBackend
      })
    });
    const result = await resp.json();
    if (result.success && result.message) {
      await fetchChatHistory();
      fetchTelemetry();
    } else {
      showToast(`Agent dispatch failed: ${result.error || 'Unknown error'}`, 'error');
    }
  } catch (err) {
    showToast('Failed to connect to agent server endpoint', 'error');
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

  container.innerHTML = state.chatMessages.map(msg => {
    const isUser = msg.role === 'user' || msg.sender === 'user';
    const avatar = isUser ? '👤' : '✨';
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
          </div>
          <div class="chat-msg-body">
            ${formattedBody}
          </div>
        </div>
      </div>
    `;
  }).join('');

  container.scrollTop = container.scrollHeight;
}

function formatMessageContent(raw) {
  if (!raw) return '';
  let str = escapeHtml(raw);

  str = str.replace(/```([a-z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
  });
  str = str.replace(/`([^`]+)`/g, '<code>$1</code>');
  str = str.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  str = str.replace(/^## (.*$)/gim, '<h3>$1</h3>');
  str = str.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  str = str.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  str = str.split(/(<pre>[\s\S]*?<\/pre>)/).map((segment, idx) => {
    if (idx % 2 === 1) return segment;
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
  initDevMode();
  setupEventListeners();
  fetchTelemetry();
  startPolling();
});
