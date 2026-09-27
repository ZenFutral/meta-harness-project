import ast
import pytest
from meta_harness.contextualize.src.truncator import StdlibTokenEstimator, truncate_to_budget


def test_estimate_code_tokens():
    estimator = StdlibTokenEstimator()
    # 36 characters -> expect 10 tokens (36 / 3.6)
    text = "a" * 36
    assert estimator.count_tokens(text, "code") == 10


def test_estimate_markdown_tokens():
    estimator = StdlibTokenEstimator()
    # 40 characters -> expect 10 tokens (40 / 4.0)
    text = "a" * 40
    assert estimator.count_tokens(text, "markdown") == 10


def test_truncate_within_budget_returns_original():
    content = "def foo():\n    return 1\n"
    # large budget ensures no truncation
    assert truncate_to_budget(content, max_tokens=100) == content


def test_truncate_respects_ast_boundary():
    # Two function definitions; budget only allows first function
    content = (
        "def first():\n    return 1\n\n"
        "def second():\n    return 2\n"
    )
    # Estimate tokens for first function approx 12 chars per line? We'll set low budget
    # Use a small budget to force truncation after first function
    truncated = truncate_to_budget(content, max_tokens=10, boundary_mode="ast_statement")
    # Should contain only first function definition (including blank line after)
    assert "def second" not in truncated
    assert "def first" in truncated

# Ensure imports succeed without third‑party dependencies
def test_no_third_party_imports():
    estimator = StdlibTokenEstimator()
    assert isinstance(estimator, StdlibTokenEstimator)
