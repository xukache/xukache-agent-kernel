import json
from collections import Counter
from pathlib import Path


SMOKE_CASES = Path("data/eval/real_smoke_cases.jsonl")


def _rows() -> list[dict]:
    return [
        json.loads(line)
        for line in SMOKE_CASES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_real_smoke_dataset_has_expert_scenario_coverage():
    rows = _rows()
    counts = Counter(row["category"] for row in rows)

    assert len(rows) == 8
    assert counts["work_injury_recognition"] >= 2
    assert counts["labor_capacity"] >= 2
    assert counts["payment_calculation"] >= 2
    assert counts["composite"] >= 1
    assert all(row["evaluation_kind"] == "real_smoke" for row in rows)
    assert all(row["trusted_jurisdiction"]["province"] == "四川省" for row in rows)
    assert all(row["expected_intent"] for row in rows)
    assert all(row["expect_contains"] for row in rows)


def test_real_smoke_dataset_case_ids_are_unique_and_have_risk_focus():
    rows = _rows()

    assert len({row["id"] for row in rows}) == len(rows)
    assert all(row["risk_focus"] for row in rows)
    assert all(row["expert_scenario"] for row in rows)
