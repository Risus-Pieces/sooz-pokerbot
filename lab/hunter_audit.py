"""
hunter_audit.py - instrumented duplicate matches vs hunter, with per-spot chip
accounting from hunter's point of view.

    python lab/hunter_audit.py lab/field/anti/barrel.py [--hunter lab/field/hunter_v2.py]
           [--deals 1000] [--seeds 2] [--workers 4] [--json out.json]

Every hand's net for hunter is split exactly by street:
    net = sum_s  W * opp_in[s] - (1 - W) * hunter_in[s]
(W = 1 hunter wins the pot, 0 loses, 0.5 split), so 'chips by street' adds
up to the total. Each street's share is also keyed by the action line on
that street (H = hunter, O = opponent; x check, c call, h half-pot raise,
p pot raise, f fold), and every hunter fold / call is checked against the
full board ("would hunter's hand have won at showdown?").

Hunter's internal model is snapshotted at each of its decisions (estimated
betting range 'top' and fold-rate estimate 'f') by wrapping its choose().
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lab"))

from evaluator import omaha_score  # noqa: E402
from game import (BIG_BLIND, AgentConfig, Game, Street, button_for_deal,  # noqa: E402
                  default_action, make_deal)
from sim import load_bot  # noqa: E402

HUNTER = str(ROOT / "lab" / "field" / "hunter_v2.py")
LETTER = {0: "f", 1: "c", 2: "h", 3: "p"}
SNAMES = ["pre", "flop", "turn", "river"]


def _wrap_hunter(mod, log):
    """Record hunter's model state at each decision (if it is a hunter-like bot)."""
    if not hasattr(mod, "choose"):
        return
    orig = mod.choose

    def choose(obs, memory, params):
        a = orig(obs, memory, params)
        st = memory.get("stats")
        if st is not None:
            g = 0 if obs.street == Street.PREFLOP else 1
            log.append({
                "hand": obs.hand_index, "street": int(obs.street),
                "top": st.bet_range(obs.street, params["prior_weight"]),
                "f0": st.fold_rate(obs.street, 0), "f1": st.fold_rate(obs.street, 1),
                "aggr": st.aggr_rate(obs.street), "shown_n": st.shown[g][1],
                "think": memory.get("think", 0.0),
            })
        return a
    mod.choose = choose


def play_half_logged(path_bot, path_hunter, seed, deals, half):
    bot, hunter = load_bot(path_bot), load_bot(path_hunter)
    log: list = []
    _wrap_hunter(hunter, log)
    b_seat = 0 if half == 1 else 1
    h_seat = 1 - b_seat
    seat_bot = {b_seat: bot, h_seat: hunter}
    mem = {0: {}, 1: {}}
    cfg = AgentConfig()
    for s in (0, 1):
        seat_bot[s].new_half(cfg, mem[s])
    hands = []
    for d in range(deals):
        deal = make_deal(seed, d)
        g = Game(deal, button_for_deal(d), hand_index=d)
        while not g.is_terminal:
            s = g.to_act
            obs = g.observation(s)
            try:
                act = seat_bot[s].choose_action(obs, mem[s])
                if act not in obs.legal_actions:
                    act = default_action(obs.to_call)
            except Exception:  # noqa: BLE001
                act = default_action(obs.to_call)
            g.apply(act)
        for s in (0, 1):
            try:
                seat_bot[s].on_hand_end(g.hand_result(s), mem[s])
            except Exception:  # noqa: BLE001
                pass
        res = g.result()
        hs = omaha_score(deal.hole_cards[h_seat], deal.board)
        os_ = omaha_score(deal.hole_cards[b_seat], deal.board)
        would = 1.0 if hs > os_ else 0.0 if hs < os_ else 0.5
        hist = [("H" if r.seat == h_seat else "O", int(r.street), int(r.action), r.amount) for r in res.history]
        hands.append({
            "d": d, "half": half, "h_btn": g.button_seat == h_seat,
            "net": res.nets[h_seat], "sd": res.went_to_showdown,
            "W": 1.0 if res.winner_seat == h_seat else 0.0 if res.winner_seat is not None else 0.5,
            "would": would, "hist": hist,
        })
    return hands, log


def _job(args):
    return play_half_logged(*args)


def run(path_bot, path_hunter, seeds, deals, workers):
    jobs = [(path_bot, path_hunter, s, deals, h) for s in seeds for h in (1, 2)]
    with ProcessPoolExecutor(workers) as ex:
        out = list(ex.map(_job, jobs))
    hands, logs = [], []
    for (s, h), (hd, lg) in zip([(s, h) for s in seeds for h in (1, 2)], out):
        for x in hd:
            x["seed"] = s
        hands += hd
        logs += [dict(l, seed=s, half=h) for l in lg]
    return hands, logs


def street_parts(h):
    """Per street: (hunter chips in, opp chips in, line string)."""
    h_btn = h["h_btn"]
    hin = [0] * 4
    oin = [0] * 4
    # blinds: button posts SB
    hin[0] += 1 if h_btn else 2
    oin[0] += 2 if h_btn else 1
    lines = [""] * 4
    for who, st, a, amt in h["hist"]:
        if who == "H":
            hin[st] += amt
        else:
            oin[st] += amt
        letter = LETTER[a]
        if a == 1 and amt == 0:
            letter = "x"
        lines[st] += who + letter
    return hin, oin, lines


def first_action_key(h, street):
    """'flop: unopened bet-half' / 'turn: facing-pot call' ... for hunter's first action on a street."""
    facing = None
    pre_blind = street == 0
    for who, st, a, amt in h["hist"]:
        if st != street:
            continue
        if who == "O":
            facing = {2: "half", 3: "pot"}.get(a, facing if a != 1 else None)
            continue
        name = {0: "fold", 1: "call" if (facing or (pre_blind and amt > 0)) else "check",
                2: "raise-half" if facing else "bet-half", 3: "raise-pot" if facing else "bet-pot"}[a]
        ctx = f"facing-{facing}" if facing else ("vs-blind" if pre_blind and h["h_btn"] else "unopened")
        return f"{SNAMES[street]}: {ctx} {name}"
    return None


def analyse(hands, logs):
    out = {}
    n = len(hands)
    tot = sum(h["net"] for h in hands)
    out["hands"] = n
    out["hunter_bb_per_hand"] = tot / n / BIG_BLIND
    by_street = [0.0] * 4
    by_line = defaultdict(lambda: [0, 0.0])
    by_first = defaultdict(lambda: [0, 0.0])
    end = defaultdict(lambda: [0, 0.0, 0.0])   # count, net, would-win sum
    for h in hands:
        hin, oin, lines = street_parts(h)
        W = h["W"]
        last = max(st for _, st, _, _ in h["hist"]) if h["hist"] else 0
        for s in range(4):
            if not lines[s] and s > 0:
                continue
            v = W * oin[s] - (1 - W) * hin[s]
            by_street[s] += v
            k = f"{SNAMES[s]}:{lines[s]}"
            by_line[k][0] += 1
            by_line[k][1] += v
            fk = first_action_key(h, s)
            if fk:
                by_first[fk][0] += 1
                by_first[fk][1] += v
        if h["sd"]:
            key = "showdown"
        else:
            folder = h["hist"][-1][0]
            key = f"{'H' if folder == 'H' else 'O'} folds {SNAMES[last]}"
        e = end[key]
        e[0] += 1
        e[1] += h["net"]
        e[2] += h["would"]
    out["by_hunter_first_action"] = {k: {"n": c, "bb_per_hand_total": v / n / BIG_BLIND, "bb_per_occurrence": v / c / BIG_BLIND}
                                     for k, (c, v) in sorted(by_first.items(), key=lambda kv: kv[1][1])}
    out["by_street_bb_per_hand"] = {SNAMES[s]: by_street[s] / n / BIG_BLIND for s in range(4)}
    out["by_end"] = {k: {"n": v[0], "bb_per_hand_total": v[1] / n / BIG_BLIND,
                         "hunter_would_win": v[2] / max(1, v[0])} for k, v in sorted(end.items())}
    lines = sorted(by_line.items(), key=lambda kv: kv[1][1])
    out["worst_lines"] = [{"line": k, "n": c, "bb_per_hand_total": v / n / BIG_BLIND, "bb_per_occurrence": v / c / BIG_BLIND}
                          for k, (c, v) in lines[:14]]
    out["best_lines"] = [{"line": k, "n": c, "bb_per_hand_total": v / n / BIG_BLIND, "bb_per_occurrence": v / c / BIG_BLIND}
                         for k, (c, v) in lines[-10:][::-1]]
    # hunter decisions facing a bet: action vs would-win
    fac = defaultdict(lambda: [0, 0.0])
    for h in hands:
        to_call_pending = False
        for who, st, a, amt in h["hist"]:
            if who == "O":
                to_call_pending = a in (2, 3)
            else:
                if to_call_pending:
                    k = f"{SNAMES[st]} H-{ {0: 'fold', 1: 'call', 2: 'raise-half', 3: 'raise-pot'}[a] }"
                    fac[k][0] += 1
                    fac[k][1] += h["would"]
                to_call_pending = False
    out["hunter_facing_bet"] = {k: {"n": c, "would_win": w / c} for k, (c, w) in sorted(fac.items())}
    # hunter's own unopened actions (nobody bet yet this street): size tells
    own = defaultdict(lambda: [0, 0.0])
    for h in hands:
        cur, bet_seen = -1, False
        for who, st, a, amt in h["hist"]:
            if st != cur:
                cur, bet_seen = st, False
            if who == "H" and not bet_seen and st > 0:
                k = f"{SNAMES[st]} H-{ {1: 'check', 2: 'bet-half', 3: 'bet-pot'}.get(a, 'fold') }"
                own[k][0] += 1
                own[k][1] += h["would"]
            if a in (2, 3):
                bet_seen = True
    out["hunter_unopened"] = {k: {"n": c, "would_win": w / c} for k, (c, w) in sorted(own.items())}
    # time profile: hunter net by hand-index bucket
    buckets = defaultdict(lambda: [0, 0.0])
    for h in hands:
        b = h["d"] // 200
        buckets[b][0] += 1
        buckets[b][1] += h["net"]
    out["by_phase_bb_per_hand"] = {f"{b * 200}-{b * 200 + 199}": v / c / BIG_BLIND for b, (c, v) in sorted(buckets.items())}
    # model snapshots
    if logs:
        ms = defaultdict(lambda: defaultdict(list))
        for l in logs:
            b = l["hand"] // 200
            g = "pre" if l["street"] == 0 else "post"
            for key in ("top", "f0", "f1", "aggr"):
                ms[f"{g}:{key}"][b].append(l[key])
        out["hunter_model"] = {k: {f"{b * 200}+": round(sum(v) / len(v), 3) for b, v in sorted(d.items())}
                               for k, d in sorted(ms.items())}
        out["hunter_think_max"] = max(l["think"] for l in logs)
    return out


def fmt(out) -> str:
    L = [f"hands {out['hands']}  hunter {out['hunter_bb_per_hand']:+.3f} bb/hand"]
    L.append("by street: " + "  ".join(f"{k} {v:+.3f}" for k, v in out["by_street_bb_per_hand"].items()))
    L.append("by phase:  " + "  ".join(f"{k} {v:+.2f}" for k, v in out["by_phase_bb_per_hand"].items()))
    L.append("chips by hunter's FIRST action on each street (n, bb/hand contribution, bb/occurrence):")
    for k, v in out["by_hunter_first_action"].items():
        L.append(f"   {k:34} n={v['n']:5d} {v['bb_per_hand_total']:+.3f} {v['bb_per_occurrence']:+.2f}")
    L.append("end of hand (n, bb/hand contribution, hunter would-win@showdown):")
    for k, v in out["by_end"].items():
        L.append(f"   {k:16} n={v['n']:5d} {v['bb_per_hand_total']:+.3f}  ww={v['hunter_would_win']:.2f}")
    L.append("hunter facing opponent bet/raise (would-win share):")
    for k, v in out["hunter_facing_bet"].items():
        L.append(f"   {k:16} n={v['n']:5d} ww={v['would_win']:.2f}")
    L.append("hunter unopened postflop actions (would-win share):")
    for k, v in out.get("hunter_unopened", {}).items():
        L.append(f"   {k:16} n={v['n']:5d} ww={v['would_win']:.2f}")
    L.append("worst lines for hunter (street:line  n  bb/hand-total  bb/occurrence):")
    for x in out["worst_lines"]:
        L.append(f"   {x['line']:24} {x['n']:5d} {x['bb_per_hand_total']:+.3f} {x['bb_per_occurrence']:+.2f}")
    L.append("best lines for hunter:")
    for x in out["best_lines"]:
        L.append(f"   {x['line']:24} {x['n']:5d} {x['bb_per_hand_total']:+.3f} {x['bb_per_occurrence']:+.2f}")
    if "hunter_model" in out:
        L.append("hunter model (mean by 200-hand bucket):")
        for k, v in out["hunter_model"].items():
            L.append(f"   {k:10} " + " ".join(f"{x:.2f}" for x in v.values()))
        L.append(f"   hunter think max {out['hunter_think_max']:.2f}s")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bot")
    ap.add_argument("--hunter", default=HUNTER)
    ap.add_argument("--deals", type=int, default=1000)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--seed0", type=int, default=500)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    seeds = [f"au{a.seed0 + k}" for k in range(a.seeds)]
    hands, logs = run(a.bot, a.hunter, seeds, a.deals, a.workers)
    out = analyse(hands, logs)
    out["bot"] = a.bot
    print(f"== {Path(a.bot).stem} vs {Path(a.hunter).stem}")
    print(fmt(out))
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
