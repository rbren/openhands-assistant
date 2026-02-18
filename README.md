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
