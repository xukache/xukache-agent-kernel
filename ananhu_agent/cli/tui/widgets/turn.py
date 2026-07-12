from __future__ import annotations

from textual.css.query import NoMatches
from textual.containers import Vertical
from textual.widgets import Button, LoadingIndicator, Markdown, Static

from ananhu_agent.cli.tui.presentation import InspectorModel
from ananhu_agent.cli.tui.widgets.run_inspector import RunInspector


class RunSpinner(LoadingIndicator):
    """单轮运行指示器；running 是供交互层读取的显式可见状态。"""

    def __init__(self, *, id: str) -> None:
        super().__init__(id=id)
        self.running = True

    def set_running(self, running: bool) -> None:
        self.running = running
        self.display = running
        self.auto_refresh = 1 / 16 if running else None


class TurnWidget(Vertical):
    """单轮会话按用户、检查器、答复和 usage 的稳定顺序组合。"""

    DEFAULT_CSS = """
    TurnWidget {
        width: 1fr;
        height: auto;
        overflow: hidden hidden;
    }
    TurnWidget > #inspector-toggle {
        width: 3;
        height: 1;
        min-width: 3;
        padding: 0;
    }
    """

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
        self.inspector_collapsed = False
        self.inspector_manually_expanded = False

    def compose(self):
        yield Static(self.user_message, classes="turn-user")
        spinner = RunSpinner(id="run-spinner")
        spinner.set_running(True)
        yield spinner
        yield Button("+", id="inspector-toggle", tooltip="展开运行详情")
        yield RunInspector(self.inspector_model, id="run-inspector")
        yield Markdown(self.assistant_message, id="assistant-message")
        yield Static(self.usage_line, classes="turn-usage")

    def update_inspector(self, model: InspectorModel) -> None:
        """只更新本轮展示模型，不把 UI 状态回写到工作流。"""

        self.inspector_model = model
        try:
            inspector = self.query_one("#run-inspector", RunInspector)
        except NoMatches:
            return
        inspector.model = model
        inspector.refresh_tree()

    def collapse_inspector(self, *, force: bool = False) -> None:
        if self.inspector_manually_expanded and not force:
            return
        self.inspector_collapsed = True
        try:
            self.query_one("#run-inspector", RunInspector).display = False
            button = self.query_one("#inspector-toggle", Button)
            button.display = True
            button.label = "+"
            button.tooltip = "展开运行详情"
        except NoMatches:
            return

    def expand_inspector(self) -> None:
        self.inspector_manually_expanded = True
        self.inspector_collapsed = False
        try:
            self.query_one("#run-inspector", RunInspector).display = True
            button = self.query_one("#inspector-toggle", Button)
            button.display = True
            button.label = "-"
            button.tooltip = "收起运行详情"
        except NoMatches:
            return

    def start_spinner(self) -> None:
        try:
            self.query_one("#run-spinner", RunSpinner).set_running(True)
        except NoMatches:
            return

    def stop_spinner(self) -> None:
        try:
            self.query_one("#run-spinner", RunSpinner).set_running(False)
        except NoMatches:
            return

    def set_usage_line(self, usage_line: str) -> None:
        """运行结束时仅刷新本轮聚合 usage 的展示文本。"""

        self.usage_line = usage_line
        try:
            self.query_one(".turn-usage", Static).update(usage_line)
        except NoMatches:
            return

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "inspector-toggle":
            if self.inspector_collapsed:
                self.expand_inspector()
            else:
                self.collapse_inspector(force=True)
