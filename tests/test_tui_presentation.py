from __future__ import annotations

from ananhu_agent.cli.tui.presentation import aggregate_usage, format_usage_line
from ananhu_agent.ports.model_gateway import ModelResult, ModelUsage


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
