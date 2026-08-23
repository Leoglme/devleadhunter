"""
Unit tests for the send-policy slot scheduler.

These assert structural invariants (window, weekdays, spacing, daily cap) in
policy-local time, so they hold whether or not the timezone database is present.
"""

import itertools
from datetime import datetime

from services.send_policy_service import ResolvedPolicy, _to_local, send_policy_service


def _local(dt: datetime) -> datetime:
    """Convert a returned naive-UTC slot to policy-local time for assertions."""
    return _to_local(dt)


def _policy() -> ResolvedPolicy:
    """A Mon–Fri, 07:00–18:00, 1/20min, 20/day policy."""
    return ResolvedPolicy(
        daily_cap=20,
        days_of_week=[0, 1, 2, 3, 4],
        window_start_hour=7,
        window_end_hour=18,
        spacing_minutes=20,
        follow_up_delay_days=5,
    )


def test_count_and_order() -> None:
    """It returns exactly ``count`` ascending slots."""
    slots = send_policy_service.next_send_slots(_policy(), 50)
    assert len(slots) == 50
    assert slots == sorted(slots)


def test_slots_stay_in_window_and_weekdays() -> None:
    """Every slot falls on an allowed weekday inside the hour window."""
    policy = _policy()
    slots = send_policy_service.next_send_slots(policy, 60)
    for slot in slots:
        local = _local(slot)
        assert local.weekday() in policy.days_of_week
        assert policy.window_start_hour <= local.hour < policy.window_end_hour


def test_daily_cap_respected() -> None:
    """No local calendar day exceeds the daily cap."""
    policy = ResolvedPolicy(5, [0, 1, 2, 3, 4], 7, 18, 20, 5)
    slots = send_policy_service.next_send_slots(policy, 23)
    per_day: dict[object, int] = {}
    for slot in slots:
        day = _local(slot).date()
        per_day[day] = per_day.get(day, 0) + 1
    assert max(per_day.values()) <= 5
    # 23 items at 5/day → spread over at least 5 days.
    assert len(per_day) >= 5


def test_spacing_within_day() -> None:
    """Two slots on the same local day are at least ``spacing_minutes`` apart."""
    policy = _policy()
    slots = send_policy_service.next_send_slots(policy, 10)
    for earlier, later in itertools.pairwise(slots):
        le, ll = _local(earlier), _local(later)
        if le.date() == ll.date():
            assert (ll - le).total_seconds() >= policy.spacing_minutes * 60 - 1


def test_seed_counts_pushes_to_next_day() -> None:
    """A day already at the cap gets no new slots."""
    policy = ResolvedPolicy(3, [0, 1, 2, 3, 4], 7, 18, 20, 5)
    start = datetime(2026, 7, 13, 6, 0, 0)  # Monday, before the window (UTC)
    first_local_day = _to_local(start).date()
    slots = send_policy_service.next_send_slots(policy, 3, start_utc=start, seed_counts={first_local_day: 3})
    assert all(_local(s).date() != first_local_day for s in slots)


def test_per_campaign_cap_limits_slots_per_day() -> None:
    """A per-campaign cap of 1 spreads the campaign at one send per day, below the global cap."""
    slots = send_policy_service.next_send_slots(_policy(), 5, per_campaign_cap=1)
    per_day: dict[object, int] = {}
    for slot in slots:
        day = _local(slot).date()
        per_day[day] = per_day.get(day, 0) + 1
    assert len(slots) == 5
    assert max(per_day.values()) == 1
    assert len(per_day) == 5


def test_campaign_seed_counts_pushes_to_next_day() -> None:
    """A day where this campaign already used its cap gets no new slot."""
    start = datetime(2026, 8, 24, 5, 0, 0)  # Monday
    first_local_day = _to_local(start).date()
    slots = send_policy_service.next_send_slots(
        _policy(), 2, start_utc=start, per_campaign_cap=1, campaign_seed_counts={first_local_day: 1}
    )
    assert all(_local(s).date() != first_local_day for s in slots)


def test_occupied_slots_are_skipped() -> None:
    """Instants already taken by other pending emails are never reused."""
    policy = _policy()
    start = datetime(2026, 8, 24, 5, 0, 0)  # Monday
    first = send_policy_service.next_send_slots(policy, 3, start_utc=start)
    second = send_policy_service.next_send_slots(policy, 3, start_utc=start, occupied=set(first))
    assert set(first).isdisjoint(second)


def test_two_campaigns_interleave_one_per_day() -> None:
    """Two 1/day campaigns launched together land one of each on the same days, at distinct instants."""
    policy = _policy()  # global cap 20
    start = datetime(2026, 8, 24, 5, 0, 0)  # Monday

    campaign_a = send_policy_service.next_send_slots(policy, 3, start_utc=start, per_campaign_cap=1)

    seed_counts: dict[object, int] = {}
    occupied: set[datetime] = set()
    for slot in campaign_a:
        seed_counts[_local(slot).date()] = seed_counts.get(_local(slot).date(), 0) + 1
        occupied.add(slot)

    campaign_b = send_policy_service.next_send_slots(
        policy, 3, start_utc=start, seed_counts=seed_counts, occupied=occupied, per_campaign_cap=1
    )

    days_a = [_local(s).date() for s in campaign_a]
    days_b = [_local(s).date() for s in campaign_b]
    assert days_a == days_b  # both campaigns cover the same three days
    assert set(campaign_a).isdisjoint(campaign_b)  # spaced, never the same instant
