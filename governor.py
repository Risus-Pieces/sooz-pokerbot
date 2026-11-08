"""
governor.py - keeps our thinking time inside the judge's time bank.

The judge charges every request max(0, wall - 1 ms) against a per-half bank
(8 s for 1000 hands). We estimate what we have been charged as
    C = 1.2 * (sum of our hook wall time) + 0.4 ms * requests
(deliberately pessimistic: it also covers JSON/HTTP work we cannot see) and
compare it with an allowance that grows through the half and ends at 75% of
the bank. The further we are over budget, the cheaper the tier:

    T0  full simulation (n = hunter_n)
    T1  n = 64
    T2  n = 32
    T3  n = 16
    T4  no simulation: made-hand rules postflop, preflop table
    T5  check / fold (never expected)
"""

from __future__ import annotations

import os

DET = os.environ.get("SOOZ_DET") == "1"   # lab mode: pin T0 so A/B runs are reproducible

A_WALL = 1.2
B_REQ = 0.0004
ROUTE_MULT = 1.4      # route timing misses parsing and scheduling delay outside our handler
ROUTE_REQ = 0.0005


class Gov:
    def __init__(self, bank: float, num_hands: int, hunter_n: int) -> None:
        self.bank = max(0.01, float(bank))
        self.n_hands = max(1, int(num_hands))
        self.hunter_n = hunter_n
        self.wall = 0.0
        self.requests = 0
        self.route = 0.0        # whole-request wall time measured by the server routes
        self.route_req = 0

    def charge(self, seconds: float, request: bool) -> None:
        self.wall += seconds
        if request:
            self.requests += 1

    def reconcile(self, route_seconds: float) -> None:
        """Server mode: wall time of a whole /act request (JSON, model, hooks)."""
        self.route += route_seconds
        self.route_req += 1

    def charged(self) -> float:
        hooks = A_WALL * self.wall + B_REQ * self.requests
        routes = ROUTE_MULT * self.route + ROUTE_REQ * self.route_req
        return max(hooks, routes)

    def tier(self, hand_index: int) -> int:
        if DET:
            return 0
        c = self.charged()
        b = self.bank
        if c >= 0.94 * b:
            return 5
        if c >= 0.81 * b:
            return 4
        allow = b * (0.075 + 0.675 * (hand_index + 1) / self.n_hands)
        r = c / allow
        if r >= 1.3 or c >= 0.72 * b:
            return 3
        if r >= 1.0 or c >= 0.66 * b:
            return 2
        if r >= 0.8 or c >= 0.60 * b:
            return 1
        return 0

    def samples(self, tier: int) -> int:
        return {0: self.hunter_n, 1: 64, 2: 32, 3: 16}.get(tier, 0)
