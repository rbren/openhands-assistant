"""Example e2e test: ask the agent a simple question."""

import os

from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.terminal import TerminalTool

from tests.framework.recorder import Mode


def _make_agent() -> Agent:
    api_key = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "mock-key"
    llm = LLM(
        model=os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
        api_key=api_key,
    )
    return Agent(llm=llm, tools=[Tool(name=TerminalTool.name)])


def test_hello(llm_recorder, workspace):
    agent = _make_agent()
    with llm_recorder:
        conv = Conversation(agent=agent, workspace=workspace)
        conv.send_message("Say exactly: HELLO_TEST_PASS")
        conv.run()

    assert llm_recorder.calls, "Expected at least one LLM call"

    last_response = llm_recorder.calls[-1]["response"]
    resp_str = str(last_response)
    assert "HELLO_TEST_PASS" in resp_str, (
        f"Expected agent to say HELLO_TEST_PASS, got: {resp_str[:200]}"
    )
