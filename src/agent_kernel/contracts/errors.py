"""Kernel 运行时错误基类。"""

from __future__ import annotations


class KernelError(Exception):
    """合法运行中的 Kernel 失败传播基类。

    各 Core 可以定义自己的稳定错误类型，但不能把 Provider SDK Exception
    直接暴露到 Kernel 公共调用边界。
    """
