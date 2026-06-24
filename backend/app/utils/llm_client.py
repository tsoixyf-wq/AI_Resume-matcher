"""
Unified LLM client supporting multiple providers (DeepSeek, OpenAI, Qwen, Ollama).

Usage:
    from app.utils.llm_client import LLMClient

    client = LLMClient()
    response = await client.chat([{"role": "user", "content": "Hello"}])
    result = await client.chat_with_json_output(prompt, output_schema)
"""

import json
from typing import Any, Type

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class LLMClient:
    """Unified async client for multiple LLM providers."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.settings.LLM_API_KEY,
                base_url=self.settings.LLM_BASE_URL,
            )
        return self._client

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> str:
        """Send a chat completion request and return the text response."""
        try:
            response = await self.client.chat.completions.create(
                model=model or self.settings.LLM_MODEL,
                messages=messages,
                temperature=temperature or self.settings.LLM_TEMPERATURE,
                max_tokens=max_tokens or self.settings.LLM_MAX_TOKENS,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM chat failed", error=str(e), provider=self.settings.LLM_PROVIDER)
            raise

    async def chat_with_json_output(
        self,
        prompt: str,
        output_schema: Type[BaseModel] | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """
        Send a prompt and get structured JSON output.
        The model is instructed to return valid JSON matching the schema.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        schema_instruction = ""
        if output_schema:
            schema_json = output_schema.model_json_schema()
            schema_instruction = (
                "\n\n请严格按照以下 JSON Schema 格式返回结果，只返回 JSON，不要包含其他文字：\n"
                f"```json\n{json.dumps(schema_json, ensure_ascii=False, indent=2)}\n```"
            )

        messages.append({"role": "user", "content": prompt + schema_instruction})

        text = await self.chat(messages, temperature=temperature)

        # Try to extract JSON from the response
        return self._parse_json_response(text)

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        model: str | None = None,
    ):
        """Stream chat completion tokens."""
        stream = await self.client.chat.completions.create(
            model=model or self.settings.LLM_MODEL,
            messages=messages,
            temperature=temperature or self.settings.LLM_TEMPERATURE,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        """Extract JSON object from LLM response text."""
        text = text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass

        # Try to find JSON object with regex
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.warning("Failed to parse JSON from LLM response", text_preview=text[:200])
        return {"raw_output": text, "parse_error": True}

    async def close(self):
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.close()
            self._client = None
