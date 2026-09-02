"""Lightweight request-phase timing for performance diagnosis."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RequestTimer:
    """Accumulate named phase durations in milliseconds."""

    _started_at: float = field(default_factory=time.perf_counter)
    _phases: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str, ms: float) -> None:
        self._phases[name] = round(ms, 1)

    async def phase(self, name: str, coro):
        """Time an awaitable and record its duration."""
        start = time.perf_counter()
        try:
            return await coro
        finally:
            self.mark(name, (time.perf_counter() - start) * 1000)

    def phase_sync(self, name: str, fn, *args, **kwargs):
        """Time a synchronous callable and record its duration."""
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            self.mark(name, (time.perf_counter() - start) * 1000)

    @property
    def total_ms(self) -> float:
        return round((time.perf_counter() - self._started_at) * 1000, 1)

    def as_dict(self) -> dict[str, float]:
        out = dict(self._phases)
        out["total"] = self.total_ms
        return out

    def server_timing_header(self) -> str:
        """RFC 6797 Server-Timing header value."""
        parts = [f"{name};dur={ms}" for name, ms in self._phases.items()]
        parts.append(f"total;dur={self.total_ms}")
        return ", ".join(parts)
