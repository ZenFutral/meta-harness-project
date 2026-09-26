import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Coroutine, List, Optional, Union

# -------------------------------------------------------------------------
# Budget utilities – these are defined in the orchestrator package.
# The project root is added to PYTHONPATH when the repo is executed, so we can
# import them directly.  If import fails (e.g., during isolated testing) we fall
# back to no‑op placeholders.
# -------------------------------------------------------------------------
try:
    from meta_harness.orchestrator.budget import (
        BudgetTracker,
        BudgetExceeded,
        check_and_update_budget,
    )
except Exception:  # pragma: no cover
    BudgetTracker = None  # type: ignore
    BudgetExceeded = RuntimeError
    def check_and_update_budget(input_tokens: int = 0) -> bool:  # noqa: D401
        """Placeholder that always returns True when the real budget module is unavailable."""
        return True

# -------------------------------------------------------------------------
# Logging configuration – one logger for the hierarchy (singleton)
# -------------------------------------------------------------------------
LOGGER_NAME = "repomap.executor"
logger = logging.getLogger(LOGGER_NAME)
if not logger.handlers:
    handler = logging.StreamHandler()
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# -------------------------------------------------------------------------
# Core abstractions
# -------------------------------------------------------------------------
class Task:
    """Atomic unit of work.

    ``func`` may be a regular callable or an ``async`` coroutine.  ``budget_tokens``
    optionally specifies an estimated number of *input* tokens the task will consume –
    this is used with ``check_and_update_budget`` to enforce the daily $0.33 cap.
    """

    def __init__(
        self,
        func: Union[Callable[..., Any], Coroutine[Any, Any, Any]],
        *args,
        name: Optional[str] = None,
        budget_tokens: int = 0,
        **kwargs,
    ):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.name = name or getattr(func, "__name__", "unnamed_task")
        self.budget_tokens = budget_tokens

    async def run(self, tracker: Optional[BudgetTracker] = None) -> Any:
        """Execute the task.

        - If ``budget_tokens`` is set, ``check_and_update_budget`` is consulted first.
        - On failure a ``BudgetExceeded`` exception is raised.
        - When a ``BudgetTracker`` instance is supplied, the estimated cost is recorded.
        """
        logger.debug("Running task %s (budget_tokens=%s)", self.name, self.budget_tokens)
        # ---- Budget enforcement ----
        if self.budget_tokens:
            if not check_and_update_budget(self.budget_tokens):
                raise BudgetExceeded(
                    f"Daily quota exceeded before executing task {self.name}."
                )
        # ---- Execution ----
        try:
            if asyncio.iscoroutinefunction(self.func):
                result = await self.func(*self.args, **self.kwargs)
            else:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None, self.func, *self.args, **self.kwargs
                )
        except Exception as exc:
            logger.error("Task %s failed: %s", self.name, exc, exc_info=True)
            raise
        # ---- Record cost (optional) ----
        if tracker is not None and self.budget_tokens:
            try:
                # Output token count is unknown here; we log 0 for simplicity.
                tracker.record("gemini-2.0-flash", self.budget_tokens, 0)
            except Exception:  # pragma: no cover
                pass
        return result

class Stage:
    """A collection of tasks belonging to a single execution stage.

    ``parallel`` determines whether tasks run concurrently (via ``asyncio.gather``)
    or sequentially (await each in order).
    """

    def __init__(self, name: str, parallel: bool = False):
        self.name = name
        self.parallel = parallel
        self.tasks: List[Task] = []

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    async def run(self, tracker: Optional[BudgetTracker] = None) -> None:
        logger.info(
            "=== Starting stage: %s (parallel=%s) ===", self.name, self.parallel
        )
        if not self.tasks:
            logger.warning("Stage %s has no tasks", self.name)
            return
        # Reset per‑task accounting for the stage.
        if tracker is not None:
            tracker.reset_task()
        if self.parallel:
            await asyncio.gather(
                *(t.run(tracker) for t in self.tasks), return_exceptions=False
            )
        else:
            for t in self.tasks:
                await t.run(tracker)
        logger.info("=== Completed stage: %s ===", self.name)

class Executor:
    """Top‑level scheduler that holds ordered stages.

    Holds a single ``BudgetTracker`` (if available) shared across all stages.
    """

    def __init__(self):
        self.stages: List[Stage] = []
        self._budget_tracker: Optional[BudgetTracker] = (
            BudgetTracker() if BudgetTracker is not None else None
        )

    def add_stage(self, name: str, parallel: bool = False) -> Stage:
        stage = Stage(name, parallel)
        self.stages.append(stage)
        logger.debug("Added stage %s (parallel=%s)", name, parallel)
        return stage

    async def run(self) -> None:
        logger.info(
            ">>> Executor begins – %d stage(s) <<<", len(self.stages)
        )
        for stage in self.stages:
            await stage.run(self._budget_tracker)
        logger.info(">>> Executor finished <<<")

    @property
    def budget_tracker(self) -> Optional[BudgetTracker]:
        return self._budget_tracker

# -------------------------------------------------------------------------
# Convenience factory – singleton executor instance
# -------------------------------------------------------------------------
def get_executor() -> Executor:
    """Return a singleton ``Executor`` (lazy init)."""
    global _executor_instance
    try:
        return _executor_instance
    except NameError:
        _executor_instance = Executor()
        return _executor_instance
