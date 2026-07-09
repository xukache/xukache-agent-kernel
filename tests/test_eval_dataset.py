import json
from collections import Counter
from pathlib import Path


def test_eval_dataset_has_required_mvp_coverage():
    rows = [
        json.loads(line)
        for line in Path("data/eval/eval_cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    counts = Counter(row["category"] for row in rows)

    assert len(rows) >= 30
    assert counts["work_injury_recognition"] >= 10
    assert counts["labor_capacity"] >= 8
    assert counts["payment_calculation"] >= 8
    assert counts["composite"] >= 4
    assert all("expected_intent" in row for row in rows)
    assert all("expect_contains" in row for row in rows)
