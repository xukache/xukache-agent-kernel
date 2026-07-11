from __future__ import annotations

from pathlib import Path
from typing import Any

from ananhu_agent.infrastructure.knowledge.lexical_gateway import LexicalKnowledgeGateway
from ananhu_agent.ports.knowledge_gateway import KnowledgeQuery


DEFAULT_CORPUS_PATH = Path("data/policies/policy_corpus.v1.jsonl")


def search_policy(
    payload: dict[str, Any],
    *,
    gateway: LexicalKnowledgeGateway | None = None,
) -> dict[str, Any]:
    """兼容旧 PolicyRAGTool 输入，同时复用 KnowledgeGateway。

    现有 ToolExecutor 是同步 handler，因此这里调用同一 gateway 的同步适配；
    Native/LangGraph 不直接依赖该函数。
    """

    fixture_path = Path(payload.get("fixture_path", DEFAULT_CORPUS_PATH))
    gateway = gateway or LexicalKnowledgeGateway(fixture_path)
    return gateway.search_sync(KnowledgeQuery.from_payload(payload)).to_tool_payload()
