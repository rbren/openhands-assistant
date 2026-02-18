import os
import tempfile

import pytest

from tests.framework.recorder import LLMRecorder, Mode


def pytest_addoption(parser):
    parser.addoption(
        "--record",
        action="store_true",
        default=False,
        help="Run e2e tests in RECORD mode (requires LLM API key)",
    )


@pytest.fixture
def e2e_mode(request) -> Mode:
    if request.config.getoption("--record"):
        api_key = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("RECORD mode requires LLM_API_KEY or ANTHROPIC_API_KEY")
        return Mode.RECORD
    return Mode.MOCK


@pytest.fixture
def llm_recorder(request, e2e_mode):
    """Provides an LLMRecorder scoped to the test name.

    Usage in tests:
        def test_something(llm_recorder):
            with llm_recorder as rec:
                # run your agent
    """
    cassette_name = request.node.name
    return LLMRecorder(cassette_name, e2e_mode)


@pytest.fixture
def workspace(tmp_path):
    """Provides a temporary workspace directory for the agent."""
    return str(tmp_path)
