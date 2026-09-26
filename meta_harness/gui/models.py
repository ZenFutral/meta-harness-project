"""
Data models for the System Monitoring GUI and Feature Set Readout.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field


@dataclass
class FeatureItem:
    id: str
    subsystem: str  # Orchestrator, Router, Contextualize, Repomap
    name: str
    description: str
    module_path: str
    status: str  # OPERATIONAL, STANDBY, DEGRADED, TRIPPED
    tier: Optional[str] = None
    metric_summary: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class QuotaTelemetry:
    date: str
    tokens: int
    cost: float
    daily_cap: float = 0.33
    cost_percent: float = 0.0
    circuit_breaker_tripped: bool = False
    quota_file_exists: bool = False
    aggregate_quota: int = 2000
    concurrent_daily_cap: float = 0.33
    models: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheTelemetry:
    db_exists: bool
    db_size_bytes: int
    wal_enabled: bool
    parse_cache_count: int
    export_registry_count: int
    symbol_references_count: int
    wildcard_dependencies_count: int
    access_count: int = 42
    hit_count: int = 38
    miss_count: int = 4
    hit_rate_pct: float = 90.5


@dataclass
class TestMetricsTelemetry:
    last_run_timestamp: Optional[str]
    execution_duration_ms: Optional[float]
    status: str
    tokens_total_ingested: int
    tokens_total_bundled: int
    budget_limit: int
    utilization_pct: float
    fs_files_scanned: int
    fs_files_included: int
    git_diff_size_bytes: int
    git_active_branch: str


@dataclass
class AgentPersonaStatus:
    persona: str
    name: str
    status: str  # ACTIVE, IDLE, REPAIRING, STANDBY
    active_model: str
    current_subtask_id: Optional[str] = None
    repair_iterations: int = 0
    escalation_count: int = 0
    role_description: str = ""


@dataclass
class SubtaskActivityInfo:
    id: str
    name: str
    description: str
    status: str
    files_to_modify: List[str] = field(default_factory=list)
    repair_iterations: int = 0
    escalation_count: int = 0


@dataclass
class AgentActivityState:
    task_id: str
    objective: str
    workflow_status: str  # INTAKE, PLANNING, CODING, TESTING, REVIEWING, DEBUGGING, COMPLETE, FAILED
    active_agent: str
    next_agent: str
    current_subtask_idx: int
    total_subtasks: int
    subtasks: List[SubtaskActivityInfo] = field(default_factory=list)
    personas: List[AgentPersonaStatus] = field(default_factory=list)
    event_log: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class TelemetrySnapshot:
    timestamp: str
    uptime_seconds: float
    status: str
    subsystems_online: int
    total_features: int
    operational_features: int
    quota: QuotaTelemetry
    cache: CacheTelemetry
    metrics: TestMetricsTelemetry
    features: List[FeatureItem]
    vendors: Dict[str, Any] = field(default_factory=dict)
    agent_activity: Optional[AgentActivityState] = None
    codebase: Dict[str, Any] = field(default_factory=dict)
    agent_network: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
