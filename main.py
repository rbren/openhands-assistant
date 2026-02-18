import argparse
import os
import sys

from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool


def main():
    parser = argparse.ArgumentParser(description="OpenHands Assistant - headless coding agent")
    parser.add_argument("prompt", help="Task for the agent to perform")
    parser.add_argument(
        "-m", "--model",
        default=os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
        help="LLM model (default: anthropic/claude-sonnet-4-5-20250929)",
    )
    parser.add_argument(
        "-w", "--workspace",
        default=os.getcwd(),
        help="Working directory for the agent (default: current directory)",
    )
    args = parser.parse_args()

    api_key = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set LLM_API_KEY or ANTHROPIC_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    llm = LLM(
        model=args.model,
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL"),
    )

    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
    )

    conversation = Conversation(agent=agent, workspace=args.workspace)
    conversation.send_message(args.prompt)
    conversation.run()


if __name__ == "__main__":
    main()
