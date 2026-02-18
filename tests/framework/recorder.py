"""LLM call recorder/replayer for e2e tests.

In RECORD mode, real LLM calls are made and responses are saved to cassette files.
In MOCK mode, saved responses are replayed in order without hitting the LLM.
"""

from __future__ import annotations

import json
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any
from unittest.mock import patch

CASSETTES_DIR = Path(__file__).parent.parent / "cassettes"

SCRUB_KEYS = {"api_key", "api_base", "api_version", "authorization", "token", "secret", "password", "credential"}
SECRET_PATTERN = re.compile(r"sk-[a-zA-Z0-9_-]{10,}")


def _scrub_secrets(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: ("REDACTED" if k.lower() in SCRUB_KEYS else _scrub_secrets(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_scrub_secrets(item) for item in obj]
    if isinstance(obj, str) and SECRET_PATTERN.search(obj):
        return SECRET_PATTERN.sub("REDACTED", obj)
    return obj



class Mode(Enum):
    RECORD = "record"
    MOCK = "mock"

def _serialize_response(resp: Any) -> dict:
    if hasattr(resp, "model_dump"):
        return {"_type": type(resp).__module__ + "." + type(resp).__qualname__, "data": resp.model_dump()}
    if hasattr(resp, "to_dict"):
        return {"_type": type(resp).__module__ + "." + type(resp).__qualname__, "data": resp.to_dict()}
    return {"_type": "raw", "data": resp}


def _deserialize_response(entry: dict) -> Any:
    type_str = entry.get("_type", "raw")
    data = entry["data"]
    if type_str == "raw":
        return data
    try:
        from litellm.types.utils import ModelResponse
        from litellm.types.llms.openai import ResponsesAPIResponse
        TYPE_MAP = {
            "litellm.types.utils.ModelResponse": ModelResponse,
            "litellm.types.llms.openai.ResponsesAPIResponse": ResponsesAPIResponse,
        }
        cls = TYPE_MAP.get(type_str)
        if cls:
            return cls(**data)
    except Exception:
        pass
    return data


def _serialize_args(args: tuple, kwargs: dict) -> dict:
    def _safe(v: Any) -> Any:
        if hasattr(v, "model_dump"):
            return v.model_dump()
        if hasattr(v, "to_dict"):
            return v.to_dict()
        try:
            json.dumps(v)
            return v
        except (TypeError, ValueError):
            return str(v)

    return {
        "args": [_safe(a) for a in args],
        "kwargs": {k: _safe(v) for k, v in kwargs.items()},
    }


class LLMRecorder:
    """Context manager that patches litellm.completion and litellm.responses.

    Usage:
        with LLMRecorder("test_name", Mode.RECORD):
            # ... run agent ...

        with LLMRecorder("test_name", Mode.MOCK):
            # ... run agent, no real LLM calls ...
    """

    def __init__(self, cassette_name: str, mode: Mode):
        self.cassette_name = cassette_name
        self.mode = mode
        self.cassette_dir = CASSETTES_DIR / cassette_name
        self.calls: list[dict] = []
        self._replay_index = 0
        self._patches: list[Any] = []

    @property
    def cassette_file(self) -> Path:
        return self.cassette_dir / "calls.json"

    def __enter__(self) -> LLMRecorder:
        if self.mode == Mode.RECORD:
            self.cassette_dir.mkdir(parents=True, exist_ok=True)
            self.calls = []
        elif self.mode == Mode.MOCK:
            if not self.cassette_file.exists():
                raise FileNotFoundError(
                    f"No cassette found at {self.cassette_file}. "
                    "Run in RECORD mode first."
                )
            with open(self.cassette_file) as f:
                self.calls = json.load(f)
            self._replay_index = 0

        import litellm
        from litellm.responses.main import responses as _orig_responses

        orig_completion = litellm.completion
        orig_responses = _orig_responses

        recorder = self

        def patched_completion(*args, **kwargs):
            if recorder.mode == Mode.RECORD:
                resp = orig_completion(*args, **kwargs)
                recorder.calls.append({
                    "api": "completion",
                    "request": _serialize_args(args, kwargs),
                    "response": _serialize_response(resp),
                })
                return resp
            else:
                if recorder._replay_index >= len(recorder.calls):
                    raise RuntimeError(
                        f"Cassette exhausted: expected at most {len(recorder.calls)} "
                        f"calls, but got call #{recorder._replay_index + 1}"
                    )
                entry = recorder.calls[recorder._replay_index]
                recorder._replay_index += 1
                return _deserialize_response(entry["response"])

        def patched_responses(*args, **kwargs):
            if recorder.mode == Mode.RECORD:
                resp = orig_responses(*args, **kwargs)
                recorder.calls.append({
                    "api": "responses",
                    "request": _serialize_args(args, kwargs),
                    "response": _serialize_response(resp),
                })
                return resp
            else:
                if recorder._replay_index >= len(recorder.calls):
                    raise RuntimeError(
                        f"Cassette exhausted: expected at most {len(recorder.calls)} "
                        f"calls, but got call #{recorder._replay_index + 1}"
                    )
                entry = recorder.calls[recorder._replay_index]
                recorder._replay_index += 1
                return _deserialize_response(entry["response"])

        p1 = patch("litellm.completion", side_effect=patched_completion)
        p2 = patch("litellm.responses.main.responses", side_effect=patched_responses)
        # Also patch the imported references in the SDK's llm module
        p3 = patch(
            "openhands.sdk.llm.llm.litellm_completion",
            side_effect=patched_completion,
        )
        p4 = patch(
            "openhands.sdk.llm.llm.litellm_responses",
            side_effect=patched_responses,
        )
        self._patches = [p1, p2, p3, p4]
        for p in self._patches:
            p.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for p in self._patches:
            p.stop()
        self._patches = []

        if self.mode == Mode.RECORD and not exc_type:
            scrubbed = _scrub_secrets(self.calls)
            with open(self.cassette_file, "w") as f:
                json.dump(scrubbed, f, indent=2, default=str)

        return False
