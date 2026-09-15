"""LLM 客户端：OpenAI 兼容接口，负责查询改写与答案生成。"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from openai import OpenAI

logger = logging.getLogger(__name__)

REWRITE_SYSTEM_PROMPT = (
    "请结合历史上下文，把当前问题改写为一个独立、完整、适合在知识库中检索的查询。\n"
    "改写建议：\n"
    "1. 如果你认为回答该问题需要检索一些代码或图表等含中文较少的内容，请编造一个假设性的、陈述性的回答来进行检索；\n"
    "2. 如果你认为回答该问题需要查询多个子问题，请输出几个关键词来进行检索；\n"
    "3. 如果用户的提问指代模糊不清或包含缩写，请补全指代和缩写，并将用户的提问转写得更具有专业性；\n"
    "注意：只输出改写后的查询文本，不要做任何解释。你的思考过程并不代表真实输出。"
)

ANSWER_SYSTEM_TEMPLATE = (
    "你是一个个人博客的知识库问答助手。请仅根据下面给出的参考资料回答用户问题。\n"
    "要求：\n"
    "1. 尽量展开论述，分点或分段说明，提供背景、解释和可能的延伸思考，但整体保持逻辑连贯、语言流畅，使用中文；\n"
    "2. 如果参考资料不足以回答问题，你可以基于自身知识提供参考性回答，但必须在最后使用 [注意] 明确标注，提醒用户哪个部分不是资料内容；\n"
    "3. 不得将你自己的观点伪装成参考资料的内容，所有非资料内容必须有显式标识。\n\n"
    "参考资料：\n{contexts}"
)


class LLMClient:
    def __init__(self, api_key: str, model: str, base_url: str, temperature: float = 0.3):
        self.model = model
        self.temperature = temperature
        self._client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

    @property
    def available(self) -> bool:
        return self._client is not None

    def rewrite_query(self, messages: list[dict]) -> str | None:
        """基于对话历史改写用户最新问题，失败或未配置时返回 None。"""
        if not self.available:
            return None
        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": REWRITE_SYSTEM_PROMPT}, *messages],
                temperature=0,
                max_tokens=200,
            )
            rewritten = (completion.choices[0].message.content or "").strip()
            return rewritten or None
        except Exception as exc:  # noqa: BLE001 - 降级到原始问题
            logger.warning(f"查询改写失败，使用原始问题检索：{exc}")
            return None

    def generate_answer(self, question: str, contexts: list[tuple[str, str]]) -> str:
        """生成回答。contexts: [(来源标题, 片段内容), ...]，失败时抛出异常。"""
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=self._answer_messages(question, contexts),
            temperature=self.temperature,
        )
        return (completion.choices[0].message.content or "").strip()

    def stream_answer(self, question: str, contexts: list[tuple[str, str]]) -> Iterator[str]:
        """以增量文本返回回答，供 SSE 接口转发给前端。"""
        if not self.available:
            return
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=self._answer_messages(question, contexts),
            temperature=self.temperature,
            stream=True,
        )
        for chunk in completion:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content or ""
            if content:
                yield content

    @staticmethod
    def _answer_messages(question: str, contexts: list[tuple[str, str]]) -> list[dict]:
        rendered = "\n\n".join(
            f"[{index}] 来源：{title}\n{content}"
            for index, (title, content) in enumerate(contexts, start=1)
        )
        return [
            {"role": "system", "content": ANSWER_SYSTEM_TEMPLATE.format(contexts=rendered)},
            {"role": "user", "content": question},
        ]
