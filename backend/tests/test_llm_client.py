"""Tests for LLMClient — uses mock AsyncOpenAI client, no real API key needed."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.utils.llm_client import LLMClient


def _make_mock_client(return_content: str):
    """Build an LLMClient whose internal AsyncOpenAI client is fully mocked."""
    client = LLMClient()
    mock_openai = AsyncMock()
    mock_openai.chat.completions.create = AsyncMock()
    client._client = mock_openai
    return client, mock_openai


class TestLLMClient:

    @pytest.mark.asyncio
    async def test_chat_returns_content(self):
        client, mock_openai = _make_mock_client("")
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(message=AsyncMock(content="Hello, world"))
        ]
        mock_openai.chat.completions.create.return_value = mock_response

        result = await client.chat(
            [{"role": "system", "content": "System prompt"},
             {"role": "user", "content": "User input"}]
        )
        assert result == "Hello, world"

    @pytest.mark.asyncio
    async def test_chat_with_json_output_parses_json(self):
        client, mock_openai = _make_mock_client("")
        json_str = '{"score": 8.5, "reasoning": "good match"}'
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock(message=AsyncMock(content=json_str))]
        mock_openai.chat.completions.create.return_value = mock_response

        result = await client.chat_with_json_output(
            "User prompt",
            system_prompt="System prompt",
        )
        assert isinstance(result, dict)
        assert result["score"] == 8.5
        assert result["reasoning"] == "good match"

    @pytest.mark.asyncio
    async def test_chat_with_json_markdown_block(self):
        """LLM returns JSON wrapped in ```json block."""
        client, mock_openai = _make_mock_client("")
        json_str = '```json\n{"score": 7.0}\n```'
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock(message=AsyncMock(content=json_str))]
        mock_openai.chat.completions.create.return_value = mock_response

        result = await client.chat_with_json_output("prompt")
        assert result["score"] == 7.0

    @pytest.mark.asyncio
    async def test_chat_stream_yields_tokens(self):
        client, mock_openai = _make_mock_client("")
        tokens = ["Hello", ", ", "world", "!"]

        class MockDelta:
            def __init__(self, content):
                self.content = content

        class MockChoice:
            def __init__(self, content):
                self.delta = MockDelta(content)

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(content)]

        # Return an async iterable of mock chunks
        async def mock_aiter():
            for t in tokens:
                yield MockChunk(t)
            yield MockChunk("")  # sentinel

        mock_openai.chat.completions.create.return_value = mock_aiter()

        collected = []
        async for token in client.chat_stream(
            [{"role": "user", "content": "test"}]
        ):
            collected.append(token)
        assert "".join(collected) == "Hello, world!"

    @pytest.mark.asyncio
    async def test_json_parse_failure_fallback(self):
        """Malformed JSON returns dict with raw_output and parse_error key."""
        client, mock_openai = _make_mock_client("")
        bad_json = "not valid json at all — just some prose response"
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock(message=AsyncMock(content=bad_json))]
        mock_openai.chat.completions.create.return_value = mock_response

        result = await client.chat_with_json_output("prompt")
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        # Fallback preserves raw text and marks parse_error
        assert result.get("raw_output") == bad_json
        assert result.get("parse_error") is True

    @pytest.mark.asyncio
    async def test_parse_json_with_regex_extraction(self):
        """JSON buried in prose text is extracted via regex."""
        client, _ = _make_mock_client("")
        text = "Here is the analysis:\n\n{\"score\": 9.0, \"reasoning\": \"excellent\"}\n\nHope this helps."
        result = client._parse_json_response(text)
        assert result["score"] == 9.0
        assert result["reasoning"] == "excellent"

    @pytest.mark.asyncio
    async def test_parse_json_direct_valid(self):
        """Clean JSON parses directly."""
        client, _ = _make_mock_client("")
        text = '{"key": "value", "num": 42}'
        result = client._parse_json_response(text)
        assert result == {"key": "value", "num": 42}

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self):
        client, mock_openai = _make_mock_client("")
        await client.close()
        assert client._client is None
        mock_openai.close.assert_called_once()  # close() delegates to the underlying client
