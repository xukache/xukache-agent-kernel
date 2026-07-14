"""工程基座的最小确定性测试。"""

import importlib


def test_agent_kernel_package_is_importable() -> None:
    """安装后的公开包入口必须可以被 Python 导入。"""
    module = importlib.import_module("agent_kernel")

    assert module.__all__ == ()
