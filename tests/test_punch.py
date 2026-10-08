"""Punch rules that need no database: who decides IN / OUT, and the 100 m distance.

Run from ``backend/``: ``uv run pytest``.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from punch.domain import EntryType
from punch.domain.services.distance_calculator import DistanceCalculator
from punch.domain.services.entry_type_resolver import EntryTypeResolver

NOW = datetime(2026, 10, 7, 17, 0, tzinfo=UTC)


def entry(entry_type, hours_ago):
    return SimpleNamespace(entry_type=entry_type, occured_at=NOW - timedelta(hours=hours_ago))


def test_the_server_alternates_in_and_out():
    assert EntryTypeResolver.resolve(None, NOW) == EntryType.IN  # first punch ever
    assert EntryTypeResolver.resolve(entry(EntryType.IN, 9), NOW) == EntryType.OUT  # end of the day
    assert EntryTypeResolver.resolve(entry(EntryType.OUT, 15), NOW) == EntryType.IN  # next morning


def test_a_forgotten_out_does_not_flip_the_next_day():
    # IN yesterday morning, no OUT: today's first punch is an IN, not an OUT.
    assert EntryTypeResolver.resolve(entry(EntryType.IN, 33), NOW) == EntryType.IN


def test_distance_counts_north_south_as_much_as_east_west():
    cotonou = (6.3654, 2.4183)
    north = DistanceCalculator.calculate(*cotonou, cotonou[0] + 0.001, cotonou[1])
    east = DistanceCalculator.calculate(*cotonou, cotonou[0], cotonou[1] + 0.001)
    assert 105 < north < 115  # ~111 m: over the 100 m limit
    assert 105 < east < 115
