"""
Unified LLM Client for SpectraAI.

Provides a single interface for interacting with Claude (Anthropic)
and Gemini (Google) APIs, supporting both regular and streaming responses.

Handles API key management, retry logic, and response parsing.
"""

from __future__ import annotations

import json
import os
import re
import time
from enum import Enum
from typing import Optional, Generator, Any
from dataclasses import dataclass


class AIProvider(str, Enum):
    """Supported AI providers."""
    CLAUDE = "claude"
    GEMINI = "gemini"


@dataclass
class AIResponse:
    """Structured response from an LLM call."""
    text: str
    provider: str
    model: str
    usage: dict = None
    latency_ms: float = 0.0
    raw_response: Any = None

    def to_json(self) -> Optional[dict]:
        """Attempt to parse the response text as JSON."""
        try:
            # Strip markdown code fences if present
            cleaned = self.text.strip()
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            return None


class LLMClient:
    """
    Unified LLM API client supporting Claude and Gemini.

    Usage:
        client = LLMClient(provider="claude", api_key="sk-...")
        response = client.generate(system="You are...", user="Analyze...")
        data = response.to_json()
    """

    # Default models
    MODELS = {
        AIProvider.CLAUDE: "claude-sonnet-4-20250514",
        AIProvider.GEMINI: "gemini-2.5-flash",
    }

    def __init__(
        self,
        provider: str = "claude",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = AIProvider(provider)
        self.model = model or self.MODELS[self.provider]
        self._api_key = api_key or self._get_api_key()
        self._client = None
        self._init_client()

    def _get_api_key(self) -> str:
        """Retrieve API key from environment variables."""
        if self.provider == AIProvider.CLAUDE:
            key = os.environ.get("ANTHROPIC_API_KEY", "")
        else:
            key = os.environ.get("GOOGLE_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        return key.strip()

    def _init_client(self):
        """Initialize the appropriate API client."""
        if self.provider == AIProvider.CLAUDE:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self._api_key)
            except ImportError:
                raise ImportError("anthropic package required: pip install anthropic")
        elif self.provider == AIProvider.GEMINI:
            try:
                from google import genai
                if self._api_key:
                    self._client = genai.Client(api_key=self._api_key)
                else:
                    self._client = None
            except ImportError:
                raise ImportError("google-genai package required: pip install google-genai")

    @property
    def is_configured(self) -> bool:
        """Check if the client has a valid API key configured."""
        return bool(self._api_key and self._client)

    @property
    def provider_display_name(self) -> str:
        """Human-readable provider name."""
        return {
            AIProvider.CLAUDE: "Claude AI (Anthropic)",
            AIProvider.GEMINI: "Gemini AI (Google)",
        }[self.provider]

    def generate(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        images: Optional[list] = None,
        response_mime_type: Optional[str] = None,
    ) -> AIResponse:
        """
        Generate a response from the LLM.

        Args:
            system:      System prompt (role, instructions)
            user:        User message (data + question)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens:  Maximum response length
            images:      List of PIL Image objects
            response_mime_type: Optional MIME type for structured output

        Returns:
            AIResponse with text and metadata
        """
        start = time.time()

        if self.provider == AIProvider.CLAUDE:
            response = self._generate_claude(system, user, temperature, max_tokens, images)
        else:
            response = self._generate_gemini(system, user, temperature, max_tokens, images, response_mime_type)

        response.latency_ms = round((time.time() - start) * 1000, 1)
        return response

    def generate_json(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        images: Optional[list] = None,
    ) -> Optional[dict]:
        """
        Generate a response and parse it as JSON.

        The system prompt should instruct the model to return JSON.
        Falls back to None if parsing fails.
        """
        response = self.generate(system, user, temperature, max_tokens, images, response_mime_type="application/json")
        return response.to_json()

    def generate_stream(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """
        Stream a response from the LLM, yielding text chunks.

        Args:
            system, user, temperature, max_tokens: Same as generate()

        Yields:
            Text chunks as they arrive from the API
        """
        if self.provider == AIProvider.CLAUDE:
            yield from self._stream_claude(system, user, temperature, max_tokens)
        else:
            yield from self._stream_gemini(system, user, temperature, max_tokens)

    # ── Claude (Anthropic) implementation ─────────────────────────────────────

    def _generate_claude(self, system: str, user: str,
                          temperature: float, max_tokens: int, images: Optional[list] = None) -> AIResponse:
        """Generate using Claude API."""
        content = []
        if images:
            import base64
            from io import BytesIO
            for img in images:
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_str,
                    }
                })
        content.append({"type": "text", "text": user})
        
        message = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        text = message.content[0].text if message.content else ""
        usage = {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        }
        return AIResponse(
            text=text,
            provider="claude",
            model=self.model,
            usage=usage,
            raw_response=message,
        )

    def _stream_claude(self, system: str, user: str,
                        temperature: float, max_tokens: int) -> Generator[str, None, None]:
        """Stream using Claude API."""
        with self._client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    # ── Gemini (Google) implementation ────────────────────────────────────────

    def _generate_gemini(self, system: str, user: str,
                          temperature: float, max_tokens: int, images: Optional[list] = None, response_mime_type: Optional[str] = None) -> AIResponse:
        """Generate using Gemini API."""
        from google import genai

        contents = []
        if images:
            contents.extend(images)
            
        # Gemini combines system + user in the prompt
        full_prompt = f"{system}\n\n---\n\n{user}"
        contents.append(full_prompt)

        response = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type=response_mime_type,
            )
        )

        text = response.text if response.text else ""
        usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "input_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                "output_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
            }

        return AIResponse(
            text=text,
            provider="gemini",
            model=self.model,
            usage=usage,
            raw_response=response,
        )

    def _stream_gemini(self, system: str, user: str,
                        temperature: float, max_tokens: int) -> Generator[str, None, None]:
        """Stream using Gemini API."""
        from google import genai

        full_prompt = f"{system}\n\n---\n\n{user}"
        
        response = self._client.models.generate_content_stream(
            model=self.model,
            contents=full_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text
