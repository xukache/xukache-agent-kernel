from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Static


class InformationModal(ModalScreen[None]):
    """TUI 的轻量信息弹窗；业务数据由应用层受控投影后传入。"""

    BINDINGS = [("escape", "dismiss", "关闭")]

    def __init__(self, title: str, content: str) -> None:
        super().__init__()
        self.title = title
        self.content = content

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-content"):
            yield Static(self.title, classes="modal-title")
            yield Static(self.content, id="modal-information")

    def action_dismiss(self) -> None:
        self.dismiss()


class FeedbackModal(ModalScreen[dict[str, str | bool] | None]):
    """收集用户反馈；记录动作仍由 app 层映射到既有 badcase 协议。"""

    BINDINGS = [("escape", "dismiss", "关闭")]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-content"):
            yield Static("反馈", classes="modal-title")
            yield Button("回答有帮助", id="feedback-good")
            yield Button("记录问题", id="feedback-bad")
            yield Input(placeholder="问题类型，如 4 或 region_policy_mismatch", id="issue-type")
            yield Input(placeholder="期望答案或修正方向", id="expected-answer")
            yield Input(placeholder="补充说明", id="correction-note")
            yield Checkbox("加入 eval", id="added-to-eval")
            yield Button("提交负向反馈", id="feedback-submit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "feedback-good":
            self.dismiss({"kind": "good"})
        elif event.button.id == "feedback-bad":
            self.query_one("#issue-type", Input).focus()
        elif event.button.id == "feedback-submit":
            self.dismiss({
                "kind": "bad",
                "issue_type": self.query_one("#issue-type", Input).value,
                "expected_answer": self.query_one("#expected-answer", Input).value,
                "correction_note": self.query_one("#correction-note", Input).value,
                "added_to_eval": self.query_one("#added-to-eval", Checkbox).value,
            })

    def action_dismiss(self) -> None:
        self.dismiss(None)
