from __future__ import annotations

from textual.binding import Binding
from textual.containers import ScrollableContainer
from textual.widgets import Static, Tree
from rich.syntax import Syntax

from ananhu_agent.cli.tui.presentation import InspectorItem, InspectorModel, json_view


class RunInspector(Static):
    """使用一个 Tree 呈现单轮运行过程，安全规则全部复用 presentation。"""

    DEFAULT_CSS = """
    RunInspector {
        height: auto;
        overflow-x: hidden;
    }
    RunInspector > Tree {
        height: auto;
        max-height: 12;
        overflow-x: hidden;
    }
    RunInspector > #json-detail {
        height: 12;
        overflow: auto;
        overflow-x: auto;
    }
    """

    BINDINGS = [Binding("r", "toggle_raw_json", "切换 JSON", show=False)]

    def __init__(self, model: InspectorModel, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.model = model
        self._tree = Tree[InspectorItem]("执行过程", id="run-tree")
        self._tree.show_root = False
        self._tree.auto_expand = False
        self._detail = Static(id="json-content")
        self.running_node: str | None = None

    def compose(self):
        yield self._tree
        yield ScrollableContainer(self._detail, id="json-detail")

    def on_mount(self) -> None:
        self.refresh_tree()

    def refresh_tree(self) -> None:
        self._tree.clear()
        for item_id in self.model.roots:
            self._add_tree_item(self._tree.root, self.model.item(item_id))
        self.running_node = next(
            (item.item_id for item in self.model.items() if item.kind == "node" and item.expanded),
            None,
        )

    def _add_tree_item(self, parent, item: InspectorItem) -> None:
        node = parent.add(item.label, data=item, expand=item.expanded)
        for child_id in item.children:
            self._add_tree_item(node, self.model.item(child_id))

    def on_tree_node_selected(self, event: Tree.NodeSelected[InspectorItem]) -> None:
        item = event.node.data
        if item is None:
            return
        self.model.toggle_from_mouse(item.item_id)
        self._show_detail(item)
        self.refresh_tree()

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[InspectorItem]) -> None:
        item = event.node.data
        if item is not None:
            item.expanded = True

    def on_tree_node_collapsed(self, event: Tree.NodeCollapsed[InspectorItem]) -> None:
        item = event.node.data
        if item is not None:
            item.expanded = False

    def action_toggle_raw_json(self) -> None:
        node = self._tree.cursor_node
        item = node.data if node is not None else None
        if item is None:
            return
        self.model.toggle_raw_json(item.item_id)
        self._show_detail(item)

    def _show_detail(self, item: InspectorItem) -> None:
        max_chars = 8_000 if item.show_raw_json else 600
        view = json_view(item.value, max_chars=max_chars)
        self._detail.update(Syntax(view.text, "json", word_wrap=False))
