from __future__ import annotations

import time
from collections import Counter


_counters = Counter()


def inc(name: str, n: int = 1) -> None:
    _counters[name] += n


def timer():
    start = time.perf_counter()

    def _stop(name: str):
        dt = (time.perf_counter() - start) * 1000.0
        _counters[f"{name}_ms_total"] += int(dt)
        _counters[f"{name}_count"] += 1
        return dt

    return _stop


def snapshot() -> dict[str, int]:
    return dict(_counters)
