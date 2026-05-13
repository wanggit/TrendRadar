"""
AI Service - Unified AI model interface using OpenAI-compatible API.

Supports DashScope (Qwen), OpenAI, and any OpenAI-compatible provider.
"""

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIService:
    """Async AI service using OpenAI-compatible API."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ):
        settings = get_settings()
        self.model = model or settings.AI_MODEL
        self.api_key = api_key or settings.AI_API_KEY
        self.api_base = api_base or settings.AI_API_BASE
        self.temperature = temperature if temperature is not None else settings.AI_TEMPERATURE
        self.max_tokens = max_tokens or settings.AI_MAX_TOKENS
        self.timeout = timeout or settings.AI_TIMEOUT

        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key or "sk-placeholder",
                base_url=self.api_base,
                timeout=self.timeout,
            )
        return self._client

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a chat completion request and return the response text."""
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )
        content = response.choices[0].message.content
        return content or ""

    async def score_and_tag(self, titles: list[str]) -> list[dict[str, Any]]:
        """
        Score and tag a batch of news titles using AI.

        Returns list of {"title": str, "score": float, "tag": str}.
        """
        if not titles:
            return []

        # Limit batch size to avoid JSON parsing issues
        max_batch = 20
        if len(titles) > max_batch:
            logger.warning(f"Batch size {len(titles)} exceeds max {max_batch}, truncating")
            titles = titles[:max_batch]

        titles_json = json.dumps(titles, ensure_ascii=False)
        system_prompt = (
            "你是一个专业的新闻分析师。请为每条新闻标题打分（0.0-1.0，表示新闻价值/重要性）"
            "并分配一个分类标签。"
            "标签只能从以下类别中选择：科技、财经、社会、娱乐、体育、国际、健康、教育、军事。"
            "请严格以 JSON 数组格式返回，每个元素包含 title, score, tag 三个字段。"
            "不要输出任何其他内容，不要使用 markdown 代码块。"
        )
        user_prompt = f"请分析以下新闻标题：\n{titles_json}"

        try:
            response_text = await self.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])

            # Parse JSON response
            response_text = response_text.strip()
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                lines = lines[1:]  # remove opening ```
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]  # remove closing ```
                response_text = "\n".join(lines).strip()

            results = json.loads(response_text)
            if isinstance(results, list):
                return results

            return []

        except json.JSONDecodeError as e:
            logger.error(f"AI score/tag JSON parse error: {e}")
            logger.error(f"Response text (first 500 chars): {response_text[:500]}")
            return []
        except Exception as e:
            logger.error(f"AI score/tag failed: {e}")
            return []

    async def translate(self, text: str, target_language: str = "中文") -> str:
        """Translate text to target language."""
        if not text:
            return ""

        system_prompt = f"你是一个专业的翻译。请将以下文本翻译为{target_language}。只输出翻译结果，不要解释。"

        try:
            result = await self.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ])
            return result.strip()
        except Exception as e:
            logger.error(f"AI translation failed: {e}")
            return text

    def is_configured(self) -> bool:
        """Check if AI service has a valid API key."""
        return bool(self.api_key and self.api_key != "sk-placeholder")
