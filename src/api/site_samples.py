"""
Per-site cache of logged inverter samples, loaded incrementally.

Insights, alerts and the live plan all read a site's recent samples on every page view. The first read
loads the site's window (up to `window`); later reads fetch only what arrived since, re-reading a short
overlap so a sample committed just after the previous read is not lost. Sites are kept LRU.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
import uuid

from src.forecast.live_forecast import TelemetrySample

LoadSiteSamples = Callable[[uuid.UUID, datetime, datetime], list[TelemetrySample]]

# Longer than any write takes to commit after its poll; re-read samples are de-duplicated by time.
_OVERLAP = timedelta(minutes=5)


@dataclass
class _Entry:
    samples: list[TelemetrySample] = field(default_factory=list)
    times: list[datetime] = field(default_factory=list)
    loaded_until: datetime | None = None


class SiteSampleCache:
    def __init__(
        self,
        load: LoadSiteSamples,
        clock: Callable[[], datetime],
        window: timedelta = timedelta(days=400),
        max_sites: int = 256,
    ) -> None:
        self._load = load
        self._clock = clock
        self._window = window
        self._max_sites = max_sites
        self._entries: OrderedDict[uuid.UUID, _Entry] = OrderedDict()
        self._lock = threading.Lock()

    def samples(self, site_id: uuid.UUID, start: datetime, end: datetime) -> list[TelemetrySample]:
        """The site's samples with start <= recorded_at <= end, oldest first. Blocking (call off the event loop)."""
        now = self._clock()
        with self._lock:
            entry = self._entries.pop(site_id, None) or _Entry()
            self._entries[site_id] = entry
            if len(self._entries) > self._max_sites:
                self._entries.popitem(last=False)
            self._refresh(site_id, entry, now)
            return entry.samples[bisect_left(entry.times, start) : bisect_right(entry.times, end)]

    def _refresh(self, site_id: uuid.UUID, entry: _Entry, now: datetime) -> None:
        horizon = now - self._window
        since = horizon if entry.loaded_until is None else max(horizon, entry.loaded_until - _OVERLAP)
        known = set(entry.times[bisect_left(entry.times, since) :])
        fresh = [s for s in self._load(site_id, since, now) if s.recorded_at not in known]
        if fresh:
            merged = sorted(entry.samples + fresh, key=lambda s: s.recorded_at)
            entry.samples = merged
            entry.times = [s.recorded_at for s in merged]
        cut = bisect_left(entry.times, horizon)
        if cut:
            del entry.samples[:cut]
            del entry.times[:cut]
        entry.loaded_until = now
