"""Unit tests for Resend open-event classification (machine prefetch vs human read)."""

from datetime import datetime, timedelta

from api.v1.routes.webhooks import _MACHINE_OPEN_WINDOW_SECONDS, _is_machine_open, _parse_event_time

_DELIVERED = datetime(2026, 8, 21, 10, 27, 28)


def test_open_at_delivery_is_machine() -> None:
    """A pixel fetch at delivery time is a machine prefetch, not a human read."""
    assert _is_machine_open(_DELIVERED, _DELIVERED) is True


def test_open_at_window_edge_is_machine() -> None:
    """An open exactly at the window edge still counts as machine."""
    edge = _DELIVERED + timedelta(seconds=_MACHINE_OPEN_WINDOW_SECONDS)
    assert _is_machine_open(edge, _DELIVERED) is True


def test_open_just_after_window_is_human() -> None:
    """One second past the window, the open is treated as a human read."""
    after = _DELIVERED + timedelta(seconds=_MACHINE_OPEN_WINDOW_SECONDS + 1)
    assert _is_machine_open(after, _DELIVERED) is False


def test_open_hours_later_is_human() -> None:
    """A read hours after delivery is unambiguously human."""
    assert _is_machine_open(_DELIVERED + timedelta(hours=1), _DELIVERED) is False


def test_open_before_delivery_is_machine() -> None:
    """A pre-delivery pixel fetch (scanner) can never be a human read."""
    assert _is_machine_open(_DELIVERED - timedelta(seconds=5), _DELIVERED) is True


def test_no_baseline_defaults_to_human() -> None:
    """Without a delivery/send time, keep the open rather than drop a real one."""
    assert _is_machine_open(_DELIVERED, None) is False


def test_parse_event_time_prefers_data_created_at() -> None:
    """The event's own timestamp (data.created_at) wins over the webhook envelope time."""
    payload = {"created_at": "2026-08-21T09:00:00.000Z"}
    data = {"created_at": "2026-08-21T10:27:28.531Z"}
    parsed = _parse_event_time(payload, data)
    assert parsed == datetime(2026, 8, 21, 10, 27, 28, 531000)
    assert parsed.tzinfo is None


def test_parse_event_time_falls_back_on_garbage() -> None:
    """An unparseable timestamp yields a naive-UTC datetime rather than raising."""
    parsed = _parse_event_time({}, {"created_at": "not-a-date"})
    assert isinstance(parsed, datetime)
    assert parsed.tzinfo is None
