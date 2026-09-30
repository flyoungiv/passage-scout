"""Process-local accounting, reset on restart; never an account balance."""

import threading
from collections import defaultdict
from datetime import datetime, timezone

from .config import settings


class BudgetExceeded(Exception):
    pass


class Usage:
    def __init__(self):
        self.lock = threading.Lock()
        self.counts = defaultdict(float)
        self.headers = {}
        self.started = datetime.now(timezone.utc).isoformat()

    def windows(self):
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m"), now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%dT%H:%M")

    def reserve(self, token_ceiling: int):
        s = settings()
        month, day, minute = self.windows()
        increments = [
            ("credits", month, 2, s.tavily_monthly_credits),
            ("requests", day, 1, s.groq_requests_per_day),
            ("requests", minute, 1, s.groq_requests_per_minute),
            ("tokens", day, token_ceiling, s.groq_tokens_per_day),
            ("tokens", minute, token_ceiling, s.groq_tokens_per_minute),
        ]
        with self.lock:
            if any(self.counts[(kind, window)] + n > cap for kind, window, n, cap in increments):
                raise BudgetExceeded(
                    "App-tracked budget reached. Wait for the window to reset or use Demo."
                )
            for kind, window, n, _ in increments:
                self.counts[(kind, window)] += n
            # Keep bounded history; current reservations carry their original keys.
            for key in list(self.counts):
                if key[1] not in {month, day, minute}:
                    del self.counts[key]
        return increments

    def settle(self, reservation, actual_tokens: int | None):
        # Failed/ambiguous requests retain the conservative reservation.
        if actual_tokens is None:
            return
        with self.lock:
            for kind, window, ceiling, _ in reservation:
                if kind == "tokens" and (kind, window) in self.counts:
                    self.counts[(kind, window)] += actual_tokens - ceiling

    def snapshot(self):
        s = settings()
        month, day, minute = self.windows()
        with self.lock:
            return {
                "scope": "App-tracked, one server process; resets on restart. Not account-wide balances.",
                "started_at": self.started,
                "timezone": "UTC",
                "tavily": {
                    "month": month,
                    "credits_reserved": self.counts[("credits", month)],
                    "configured_monthly_credits": s.tavily_monthly_credits,
                },
                "groq": {
                    "day": day,
                    "minute": minute,
                    "requests_today": self.counts[("requests", day)],
                    "requests_this_minute": self.counts[("requests", minute)],
                    "tokens_today": self.counts[("tokens", day)],
                    "tokens_this_minute": self.counts[("tokens", minute)],
                    "configured_rpd": s.groq_requests_per_day,
                    "configured_rpm": s.groq_requests_per_minute,
                    "configured_tpd": s.groq_tokens_per_day,
                    "configured_tpm": s.groq_tokens_per_minute,
                    "last_provider_headers": dict(self.headers),
                },
            }


usage = Usage()
