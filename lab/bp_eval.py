"""
bp_eval.py - evaluate a blueprint checkpoint with lab/sim.py and append a
markdown section to lab/results/blueprint_eval.md.

    python lab/bp_eval.py data/bp/m30.npz --label "ckpt 30 min" [--deals 1000 --seeds 2 --workers 4]

Runs bp_bot (BP_PATH=<npz>) against every field bot (sim.py --field set) and
against hunter_v2, 2 seeds x 1000 deals each (duplicate, both halves).
Per-opponent pooled mean over seeds with 95% CI = mean +- 1.96*sqrt(sum se^2)/k.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lab"))
sys.path.insert(0, str(ROOT))

import sim  # noqa: E402

OUT = ROOT / "lab" / "results" / "blueprint_eval.md"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("bp")
    ap.add_argument("--label", default="")
    ap.add_argument("--deals", type=int, default=1000)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--seed0", type=int, default=100)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--minp", default="0")
    ap.add_argument("--only", nargs="*", default=None, help="opponent stems to run (default: field)")
    a = ap.parse_args()
    os.environ["BP_PATH"] = str(Path(a.bp).resolve())
    os.environ["BP_MINP"] = a.minp
    bot = str(ROOT / "lab" / "field" / "bp_bot.py")
    opps = [p for p in sim.field_paths() if Path(p).stem != "bp_bot"]
    if a.only:
        opps = [p for p in opps if Path(p).stem in a.only]
    jobs = [(bot, o, f"s{a.seed0 + k}", a.deals) for o in opps for k in range(a.seeds)]
    t = time.time()
    res = sim.run_many(jobs, a.workers)
    by = {}
    for r in res:
        by.setdefault(Path(r["b"]).stem, []).append(r)
    lines = [f"\n### {a.label or a.bp}  (minp={a.minp}, {a.seeds} seeds x {a.deals} deals, "
             f"{time.strftime('%H:%M')}, {time.time() - t:.0f}s)\n",
             "| opponent | bb/deal | 95% CI | per-seed means | points | errors | max think s/half |",
             "|---|---|---|---|---|---|---|"]
    tot_pts, n = 0.0, 0
    for name, rs in sorted(by.items()):
        k = len(rs)
        m = sum(r["mean"] for r in rs) / k
        se = math.sqrt(sum(r["se"] ** 2 for r in rs)) / k
        pts = sum(r["points"] for r in rs)
        tot_pts += pts
        n += k
        lines.append(f"| {name} | {m:+.3f} | [{m - 1.96 * se:+.3f}, {m + 1.96 * se:+.3f}] | "
                     + " ".join(f"{r['mean']:+.3f}" for r in rs)
                     + f" | {pts:.1f}/{k} | {sum(r['err_a'] for r in rs)} | {max(r['think_a'] for r in rs):.2f} |")
    lines.append(f"\npoints {tot_pts:.1f}/{n}\n")
    text = "\n".join(lines)
    print(text)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUT.exists():
        OUT.write_text("# Blueprint evaluation\n\nbp_bot = lab/field/bp_bot.py playing the MCCFR blueprint "
                       "(lab/export_bp.py checkpoint). Duplicate matches via lab/sim.py; bb/deal from bp_bot's side.\n")
    with OUT.open("a") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
