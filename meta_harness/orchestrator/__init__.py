# Package initializer to expose core symbols for test imports

# Orchestrator core
from .orchestrator import Orchestrator, _parse_subtasks

# Agents
from .agents import PlannerAgent, CoderAgent, TesterAgent, ReviewerAgent, DebuggerAgent

# Budget utilities
from .budget import BudgetTracker, BudgetExceeded

# Router
from .router import ModelRouter

# Configuration (expose all symbols)
from .config import *

# State management
from .state import *

# Compatibility shims for legacy top-level imports
import importlib, sys
sys.modules.setdefault('agents', importlib.import_module('orchestrator.agents'))
sys.modules.setdefault('budget', importlib.import_module('orchestrator.budget'))
sys.modules.setdefault('state', importlib.import_module('orchestrator.state'))
sys.modules.setdefault('config', importlib.import_module('orchestrator.config'))
