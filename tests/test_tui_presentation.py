from __future__ import annotations

import json
import secrets

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Tree

from ananhu_agent.cli.tui.presentation import (
    inspector_model,
    json_view,
)
from ananhu_agent.cli.tui.widgets.run_inspector import RunInspector
from ananhu_agent.cli.tui.presentation import aggregate_usage, format_usage_line
from ananhu_agent.ports.model_gateway import ModelResult, ModelUsage
from ananhu_agent.ports.run_event_sink import (
    ModelFinishedEvent,
    ModelFinishedPayload,
    NodeFinishedEvent,
    NodeFinishedPayload,
    NodeStartedEvent,
    NodeStartedPayload,
    RunTransientPayload,
)


def _provider_result(
    input_tokens: int,
    output_tokens: int,
    *,
    reported: bool = True,
    latency_ms: int = 0,
    cache_tokens: int = 0,
    total_tokens: int | None = None,
) -> ModelResult:
    return ModelResult(
        output={"intent": "other"},
        provider="openai_compatible",
        model="provider-model",
        profile="intent_fast",
        usage=ModelUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_tokens=cache_tokens,
            total_tokens=(
                input_tokens + output_tokens
                if total_tokens is None
                else total_tokens
            ),
            usage_source="provider",
            reported=reported,
        ),
        latency_ms=latency_ms,
    )


def _fake_result() -> ModelResult:
    return ModelResult(
        output={"intent": "other"},
        provider="fake",
        model="deterministic-intent",
        profile="intent_fast",
        usage=ModelUsage(usage_source="fake", reported=False),
    )


def _event_fields() -> dict[str, str]:
    return {
        "run_id": "run_tui",
        "request_id": "req_tui",
        "session_id": "sess_tui",
        "node_id": "understand",
    }


def _sample_run_events():
    return [
        NodeStartedEvent(
            **_event_fields(),
            sequence_no=1,
            public_payload=NodeStartedPayload(
                phase="understand",
                input_summary={"query": "四川十级工伤"},
            ),
        ),
        NodeFinishedEvent(
            **_event_fields(),
            sequence_no=2,
            public_payload=NodeFinishedPayload(
                phase="understand",
                patch_summary={"intent": "payment_calculation"},
            ),
        ),
    ]


def test_single_reported_provider_usage_status_line() -> None:
    line = format_usage_line([_provider_result(100, 20, reported=True, latency_ms=1000)], 6100)

    assert "Σ 120 tokens" in line
    assert "20.0 tok/s" in line


def test_multiple_reported_model_results_are_summed() -> None:
    results = [
        _provider_result(100, 20, reported=True),
        _provider_result(50, 10, reported=True),
    ]

    assert "Σ 180 tokens" in format_usage_line(results, 6100)


def test_mixed_unreported_provider_usage_is_unknown() -> None:
    results = [
        _provider_result(100, 20, reported=True),
        _provider_result(0, 0, reported=False),
    ]
    line = format_usage_line(results, 6100)

    assert "tokens unknown" in line
    assert "⚡ --" in line


def test_fake_usage_has_explicit_fake_zero_state() -> None:
    assert "fake · 0 tokens" in format_usage_line([_fake_result()], 10)


def test_cache_tokens_are_shown_in_model_detail() -> None:
    summary = aggregate_usage([
        _provider_result(100, 20, reported=True, cache_tokens=25),
    ])

    assert summary.details[0].cache_tokens == 25
    assert "cache 25" in format_usage_line(summary, 6100)


def test_failed_attempt_without_result_is_not_counted() -> None:
    summary = aggregate_usage([])

    assert summary.calls == 0
    assert summary.total_tokens == 0


def test_successful_retry_results_are_each_counted() -> None:
    summary = aggregate_usage([
        _provider_result(10, 2, reported=True),
        _provider_result(20, 3, reported=True),
    ])

    assert summary.calls == 2
    assert summary.total_tokens == 35


def test_inconsistent_provider_total_is_preserved_and_marked() -> None:
    summary = aggregate_usage([
        _provider_result(100, 20, reported=True, total_tokens=999),
    ])

    assert summary.total_tokens == 999
    assert summary.inconsistent is True
    assert "inconsistent" in format_usage_line(summary, 6100)


def test_expanding_one_tree_item_does_not_change_siblings() -> None:
    model = inspector_model(_sample_run_events())

    model.toggle("understand.input")

    assert model.item("understand.input").expanded is True
    assert model.item("understand.output").expanded is False


def test_mouse_and_keyboard_toggle_the_same_item() -> None:
    model = inspector_model(_sample_run_events())

    model.toggle_from_mouse("understand.input")
    assert model.item("understand.input").expanded is True
    model.toggle_from_keyboard("understand.input")

    assert model.item("understand.input").expanded is False


def test_raw_json_toggle_only_changes_selected_item() -> None:
    model = inspector_model(_sample_run_events())

    model.toggle_raw_json("understand.input")

    assert model.item("understand.input").show_raw_json is True
    assert model.item("understand.output").show_raw_json is False


def test_long_json_is_truncated_with_original_length() -> None:
    view = json_view({"content": "x" * 20_000}, max_chars=2_000)

    assert view.truncated is True
    assert view.original_chars > len(view.text)


def test_json_detail_scrolls_inside_fixed_region() -> None:
    assert "height: 12;" in RunInspector.DEFAULT_CSS
    assert "overflow: auto;" in RunInspector.DEFAULT_CSS


def test_reasoning_node_is_absent_when_provider_returns_none() -> None:
    events = _sample_run_events() + [
        ModelFinishedEvent(
            **_event_fields(),
            logical_call_id="model_1",
            sequence_no=3,
            public_payload=ModelFinishedPayload(
                profile="intent_fast",
                provider="provider",
                model="provider-model",
            ),
            transient_payload=RunTransientPayload(reasoning_content=None),
        ),
    ]

    model = inspector_model(events)

    assert not any(item.kind == "reasoning" for item in model.items())


def test_inspector_masks_configured_secret_in_transient_reasoning() -> None:
    canary = secrets.token_urlsafe(24)
    events = _sample_run_events() + [
        ModelFinishedEvent(
            **_event_fields(),
            logical_call_id="model_1",
            sequence_no=3,
            public_payload=ModelFinishedPayload(
                profile="intent_fast",
                provider="provider",
                model="provider-model",
            ),
            transient_payload=RunTransientPayload(reasoning_content=f"reasoning {canary}"),
        ),
    ]

    model = inspector_model(events, configured_secrets={canary})

    assert canary not in json.dumps([item.value for item in model.items()])


def test_running_node_is_expanded_by_default() -> None:
    model = inspector_model(_sample_run_events()[:1])

    assert model.item("understand").expanded is True


@pytest.mark.asyncio
async def test_run_inspector_mounts_one_tree_and_uses_model_toggle_state() -> None:
    model = inspector_model(_sample_run_events())

    class InspectorApp(App[None]):
        def compose(self) -> ComposeResult:
            yield RunInspector(model)

    app = InspectorApp()
    async with app.run_test(size=(80, 24)) as pilot:
        tree = app.query_one(Tree)
        assert len(app.query(Tree)) == 1
        tree.select_node(tree.root.children[0])
        await pilot.pause()

    assert model.item("understand").expanded is True
