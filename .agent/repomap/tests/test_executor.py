import sys
import unittest
import asyncio
from pathlib import Path
from types import SimpleNamespace

# ---------------------------------------------------------------------
# Mock budget module to avoid filesystem side‑effects.
# ---------------------------------------------------------------------
mock_budget = SimpleNamespace(
    BudgetExceeded=RuntimeError,
    BudgetTracker=lambda: SimpleNamespace(
        reset_task=lambda: None,
        record=lambda tier, in_tok, out_tok: None,
    ),
    check_and_update_budget=lambda tokens=0: True,
)
AGENT_DIR = Path(__file__).resolve().parents[2]
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from repomap.core.executor import Task, Stage, Executor, get_executor

# Helper functions for testing
async def async_increment(counter: dict, key: str, delay: float = 0.0):
    await asyncio.sleep(delay)
    counter[key] = counter.get(key, 0) + 1
    return counter[key]

def sync_increment(counter: dict, key: str):
    counter[key] = counter.get(key, 0) + 1
    return counter[key]

class ExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_task_sync_execution(self):
        counter = {}
        t = Task(sync_increment, counter, 'a', name='sync', budget_tokens=0)
        result = await t.run()
        self.assertEqual(result, 1)
        self.assertEqual(counter['a'], 1)

    async def test_task_async_execution(self):
        counter = {}
        t = Task(async_increment, counter, 'b', name='async', budget_tokens=0)
        result = await t.run()
        self.assertEqual(result, 1)
        self.assertEqual(counter['b'], 1)

    async def test_task_budget_exceeded(self):
        import repomap.core.executor as executor_mod
        orig_check = executor_mod.check_and_update_budget
        executor_mod.check_and_update_budget = lambda tokens=0: False
        try:
            t = Task(sync_increment, {}, 'c', name='budget', budget_tokens=10)
            with self.assertRaises(executor_mod.BudgetExceeded):
                await t.run()
        finally:
            executor_mod.check_and_update_budget = orig_check

    async def test_stage_sequential(self):
        counter = {}
        stage = Stage('seq', parallel=False)
        stage.add_task(Task(sync_increment, counter, 'x', name='t1'))
        stage.add_task(Task(sync_increment, counter, 'y', name='t2'))
        await stage.run()
        self.assertEqual(counter, {'x': 1, 'y': 1})

    async def test_stage_parallel(self):
        counter = {}
        stage = Stage('par', parallel=True)
        stage.add_task(Task(async_increment, counter, 'p1', name='t1', budget_tokens=0, delay=0.1))
        stage.add_task(Task(async_increment, counter, 'p2', name='t2', budget_tokens=0, delay=0.1))
        await stage.run()
        # Both counters should be incremented
        self.assertEqual(counter, {'p1': 1, 'p2': 1})

    async def test_executor_order(self):
        order = []
        exec = Executor()
        s1 = exec.add_stage('first')
        s2 = exec.add_stage('second')
        s1.add_task(Task(lambda: order.append('a'), name='a'))
        s1.add_task(Task(lambda: order.append('b'), name='b'))
        s2.add_task(Task(lambda: order.append('c'), name='c'))
        await exec.run()
        self.assertEqual(order, ['a', 'b', 'c'])

    async def test_singleton_factory(self):
        e1 = get_executor()
        e2 = get_executor()
        self.assertIs(e1, e2)

if __name__ == '__main__':
    unittest.main()
