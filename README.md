# openhands-assistant

A headless CLI coding agent powered by the [OpenHands SDK](https://docs.openhands.dev/sdk).

## Setup
```bash
uv sync
export ANTHROPIC_API_KEY=your-key
```

## Usage
```bash
uv run python main.py "your task here"
uv run python main.py "fix the bug in app.py" -w /path/to/project
uv run python main.py "refactor utils" -m openai/gpt-4o
```

## E2E Tests

Tests use a record/replay framework. Recorded LLM responses are stored as cassettes in `tests/cassettes/` and checked into git, so CI can run without an API key.

```bash
# Mock mode (default) — replays recorded responses, no API key needed
uv run pytest tests/ -v

# Record mode — makes real LLM calls and saves responses
LLM_API_KEY=$ANTHROPIC_API_KEY uv run pytest tests/ -v --record
```

### Writing a test

```python
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.terminal import TerminalTool

def test_my_feature(llm_recorder, workspace):
    llm = LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key="mock-key")
    agent = Agent(llm=llm, tools=[Tool(name=TerminalTool.name)])

    with llm_recorder:
        conv = Conversation(agent=agent, workspace=workspace)
        conv.send_message("do the thing")
        conv.run()

    # Assert on the recorded calls or workspace side-effects
    assert llm_recorder.calls
```

The `llm_recorder` fixture auto-selects record vs mock mode based on `--record`. Cassette names match the test function name.
