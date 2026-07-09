from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class JsonlStore:
    """本地 JSONL 存储基础设施。

    该类只负责“追加写入”和“完整读回”两个原子能力；运行证据的业务语义由
    runtime_stores.py 中的专用 Store 封装，避免底层存储层理解 trace/report 等概念。
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, row: BaseModel | dict[str, Any]) -> None:
        """追加一行 UTF-8 JSON，保留中文原文便于人工回放和排查。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = row.model_dump() if isinstance(row, BaseModel) else row
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        """读取全部非空 JSONL 行；文件不存在时返回空列表。"""
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
