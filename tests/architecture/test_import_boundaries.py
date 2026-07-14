"""用 AST 检查 Kernel 的静态导入边界。

测试只读取 Kernel 源码的导入声明，不执行被检查模块，避免把架构规则
建立在运行时副作用或简单的关键词全文匹配上。
"""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KERNEL_ROOT = PROJECT_ROOT / "src" / "agent_kernel"
ADAPTER_ROOT = PROJECT_ROOT / "src" / "adapters"

FORBIDDEN_TOP_LEVEL_MODULES = frozenset(
    {
        "applications",
        "interfaces",
        "adapters",
        "providers",
        "workflow",
        "sqlalchemy",
        "redis",
        "chromadb",
        "openai",
    }
)


def _imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".", maxsplit=1)[0])

    return imported


def test_kernel_source_does_not_import_outer_layers_or_providers() -> None:
    """Kernel 不能反向依赖 Application、Interface、Adapter 或具体 SDK。"""
    violations: dict[str, set[str]] = {}

    for path in KERNEL_ROOT.rglob("*.py"):
        forbidden = _imported_top_level_modules(path) & FORBIDDEN_TOP_LEVEL_MODULES
        if forbidden:
            violations[str(path.relative_to(PROJECT_ROOT))] = forbidden

    assert violations == {}


def test_kernel_has_no_parallel_core_package() -> None:
    """六原语之外的平行 core/kernel 包不能混入新工程。"""
    src_root = PROJECT_ROOT / "src"
    parallel_packages = {
        path.name
        for path in src_root.iterdir()
        if path.is_dir() and path.name in {"core", "kernel"}
    }

    assert parallel_packages == set()


def test_adapters_do_not_import_application_or_interface_layers() -> None:
    """Adapter 可以依赖外部 SDK，但不能反向依赖业务和外部入口。"""
    violations: dict[str, set[str]] = {}
    forbidden = {"applications", "interfaces"}

    for path in ADAPTER_ROOT.rglob("*.py"):
        imported = _imported_top_level_modules(path) & forbidden
        if imported:
            violations[str(path.relative_to(PROJECT_ROOT))] = imported

    assert violations == {}
