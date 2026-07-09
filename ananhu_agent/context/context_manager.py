from __future__ import annotations

from ananhu_agent.schemas import AgentContext


class ContextManager:
    """按固定分区构造 Agent 上下文，并记录裁剪证据。"""

    def __init__(self, max_chars: int = 4000) -> None:
        self.max_chars = max_chars

    def build_sections(self, ctx: AgentContext) -> tuple[dict[str, str], dict[str, list[str]]]:
        sections = {
            "system_prefix": "你是工伤政策咨询助手，必须基于依据回答。",
            "active_slots": str(ctx.conversation.active_slots),
            "rag_evidence": "",
            "recent_turns": ctx.conversation.history_summary,
            "working_memory": ctx.conversation.last_answer_summary,
            "current_query": ctx.request.user_query,
        }
        trimmed_sections: list[str] = []

        total_chars = sum(len(value) for value in sections.values())
        if total_chars > self.max_chars:
            # 当前问题是本轮任务事实来源，裁剪只能发生在可压缩的历史和证据分区。
            for key in ("recent_turns", "working_memory", "rag_evidence"):
                if sections[key]:
                    sections[key] = sections[key][: max(0, self.max_chars // 6)]
                    trimmed_sections.append(key)

        return sections, {"trimmed_sections": trimmed_sections}
