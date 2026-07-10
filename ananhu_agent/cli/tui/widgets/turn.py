from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Markdown, Static

from ananhu_agent.cli.tui.presentation import InspectorModel
from ananhu_agent.cli.tui.widgets.run_inspector import RunInspector


class TurnWidget(Vertical):
    """单轮会话按用户、检查器、答复和 usage 的稳定顺序组合。"""

    def __init__(
        self,
        user_message: str,
        inspector_model: InspectorModel,
        assistant_message: str = "",
        usage_line: str = "",
        *,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.user_message = user_message
        self.inspector_model = inspector_model
        self.assistant_message = assistant_message
        self.usage_line = usage_line

    def compose(self):
        yield Static(self.user_message, classes="turn-user")
        yield RunInspector(self.inspector_model, id="run-inspector")
        yield Markdown(self.assistant_message, id="assistant-message")
        yield Static(self.usage_line, classes="turn-usage")
