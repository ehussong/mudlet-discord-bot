# tests/test_llm.py
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.services.llm import LLMService, parse_llm_response


def test_parse_llm_response_valid_json() -> None:
    response = json.dumps({
        "summary": "Test bug", "steps": ["Step 1"], "error_output": "",
        "extra_info": "Version 1.0", "confidence": "high", "missing_info": None
    })
    result = parse_llm_response(response)
    assert result["summary"] == "Test bug"
    assert result["confidence"] == "high"


def test_parse_llm_response_with_markdown() -> None:
    response = """```json
{"summary": "Bug in markdown", "steps": [], "error_output": "", "extra_info": "",
"confidence": "medium", "missing_info": null}
```"""
    result = parse_llm_response(response)
    assert result["summary"] == "Bug in markdown"


def test_parse_llm_response_invalid() -> None:
    with pytest.raises(ValueError, match="Failed to parse"):
        parse_llm_response("This is not JSON")


def test_parse_llm_response_missing_fields() -> None:
    response = json.dumps({"summary": "Only summary"})
    with pytest.raises(ValueError, match="Missing required field"):
        parse_llm_response(response)


@pytest.mark.asyncio
async def test_llm_service_extract_openai() -> None:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "summary": "OpenAI extracted bug", "steps": ["Step 1"], "error_output": "",
        "extra_info": "", "confidence": "high", "missing_info": None
    })
    with patch("bot.services.llm.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client
        service = LLMService(provider="openai", openai_api_key="test-key")
        result = await service.extract([{"author": "User", "content": "Bug report here"}])
        assert result["summary"] == "OpenAI extracted bug"


@pytest.mark.asyncio
async def test_llm_service_fallback_on_failure() -> None:
    mock_anthropic_response = MagicMock()
    mock_anthropic_response.content = [MagicMock()]
    mock_anthropic_response.content[0].text = json.dumps({
        "summary": "Anthropic fallback", "steps": [], "error_output": "",
        "extra_info": "", "confidence": "medium", "missing_info": None
    })
    with patch("bot.services.llm.AsyncOpenAI") as mock_openai, \
         patch("bot.services.llm.AsyncAnthropic") as mock_anthropic:
        mock_openai_client = AsyncMock()
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("OpenAI error")
        )
        mock_openai.return_value = mock_openai_client
        mock_anthropic_client = AsyncMock()
        mock_anthropic_client.messages.create = AsyncMock(return_value=mock_anthropic_response)
        mock_anthropic.return_value = mock_anthropic_client
        service = LLMService(provider="openai", openai_api_key="test", anthropic_api_key="test")
        result = await service.extract([{"author": "User", "content": "Bug"}])
        assert result["summary"] == "Anthropic fallback"
