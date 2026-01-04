# bot/services/llm.py
"""LLM service with OpenAI and Anthropic support and failover."""

import json
import logging
import re
from typing import Any, cast

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from config.prompts import EXTRACTION_SYSTEM_PROMPT, format_conversation_prompt

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["summary", "steps", "error_output", "extra_info", "confidence", "missing_info"]


def parse_llm_response(response: str) -> dict[str, Any]:
    """
    Parse JSON from LLM output, handling markdown code blocks.

    Args:
        response: Raw LLM response text

    Returns:
        Parsed JSON as a dictionary

    Raises:
        ValueError: If response cannot be parsed or is missing required fields
    """
    text = response.strip()

    # Handle markdown code blocks (```json ... ``` or ``` ... ```)
    code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    try:
        result: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e

    # Validate required fields
    for field in REQUIRED_FIELDS:
        if field not in result:
            raise ValueError(f"Missing required field: {field}")

    return result


class LLMService:
    """LLM service with OpenAI and Anthropic support and failover."""

    def __init__(
        self,
        provider: str = "openai",
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize LLM service with API clients.

        Args:
            provider: Primary provider ("openai" or "anthropic")
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key
            max_retries: Maximum retry attempts per provider
        """
        self.provider = provider
        self.max_retries = max_retries

        self._openai_client: AsyncOpenAI | None = None
        self._anthropic_client: AsyncAnthropic | None = None

        if openai_api_key:
            self._openai_client = AsyncOpenAI(api_key=openai_api_key)

        if anthropic_api_key:
            self._anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)

    def _get_provider_order(self) -> list[str]:
        """Get list of providers to try in order (primary first, then fallback)."""
        providers = []

        if self.provider == "openai":
            if self._openai_client:
                providers.append("openai")
            if self._anthropic_client:
                providers.append("anthropic")
        else:
            if self._anthropic_client:
                providers.append("anthropic")
            if self._openai_client:
                providers.append("openai")

        return providers

    async def _call_openai(self, messages: list[dict[str, str]]) -> str:
        """Call OpenAI API to extract bug report."""
        if not self._openai_client:
            raise RuntimeError("OpenAI client not configured")

        conversation_prompt = format_conversation_prompt(messages)

        response = await self._openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": conversation_prompt},
            ],
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("OpenAI returned empty response")
        return content

    async def _call_anthropic(self, messages: list[dict[str, str]]) -> str:
        """Call Anthropic API to extract bug report."""
        if not self._anthropic_client:
            raise RuntimeError("Anthropic client not configured")

        conversation_prompt = format_conversation_prompt(messages)

        response = await self._anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": conversation_prompt},
            ],
        )

        content_block = response.content[0]
        content = cast(str, getattr(content_block, "text", ""))
        if not content:
            raise ValueError("Anthropic returned empty response")
        return content

    async def _call_with_retry(
        self, provider: str, messages: list[dict[str, str]]
    ) -> str:
        """Call a provider with retry logic."""
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                if provider == "openai":
                    return await self._call_openai(messages)
                else:
                    return await self._call_anthropic(messages)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"{provider} attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )

        raise last_error or RuntimeError(f"{provider} failed after {self.max_retries} retries")

    async def extract(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """
        Extract bug report from Discord messages using LLM.

        Args:
            messages: List of message dicts with 'author' and 'content' keys

        Returns:
            Parsed bug report dictionary

        Raises:
            RuntimeError: If all providers fail
        """
        providers = self._get_provider_order()

        if not providers:
            raise RuntimeError("No LLM providers configured")

        last_error: Exception | None = None

        for provider in providers:
            try:
                logger.info(f"Attempting extraction with {provider}")
                response = await self._call_with_retry(provider, messages)
                result = parse_llm_response(response)
                logger.info(f"Successfully extracted bug report using {provider}")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"{provider} failed: {e}, trying next provider")

        raise RuntimeError(
            f"All LLM providers failed. Last error: {last_error}"
        )
