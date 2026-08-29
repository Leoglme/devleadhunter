"""Unit tests for cumulative email log stats helpers."""

from services.email_log_stats import EmailEngagementRates, EmailLogCounts, compute_engagement_rates


def test_open_rate_capped_at_100() -> None:
    """Open rate never exceeds 100 % even if counters were inconsistent."""
    rates = compute_engagement_rates(
        EmailLogCounts(sent=10, delivered=1, opened=2, clicked=0, replied=0, bounced=0, failed=0)
    )
    assert rates.open_rate == 100.0


def test_cumulative_funnel_rates() -> None:
    """Standard funnel: 10 sent, 8 delivered, 4 opened, 2 clicked, 1 replied."""
    rates = compute_engagement_rates(
        EmailLogCounts(sent=10, delivered=8, opened=4, clicked=2, replied=1, bounced=1, failed=1)
    )
    assert rates == EmailEngagementRates(delivery_rate=80.0, open_rate=50.0, click_rate=50.0, reply_rate=12.5)


def test_zero_denominator_returns_zero_rates() -> None:
    rates = compute_engagement_rates(
        EmailLogCounts(sent=0, delivered=0, opened=0, clicked=0, replied=0, bounced=0, failed=0)
    )
    assert rates.delivery_rate == 0.0
    assert rates.open_rate == 0.0
    assert rates.click_rate == 0.0
    assert rates.reply_rate == 0.0
