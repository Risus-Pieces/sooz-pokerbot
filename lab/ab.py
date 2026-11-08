"""
ab.py - paired A/B test of two strategy parameter sets against the field
(lab/field minus trivial bots) plus the red-team bots (lab/field/anti).

    SOOZ_DET=1 python lab/ab.py '{}' '{"postflop_pot_only": true}' --seeds 2
"""
import argparse
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lab"))
import sim  # noqa: E402
import tune  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--deals", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--skip", default="checkfold,timeout")
    ap.add_argument("--seed0", type=int, default=0)
    args = ap.parse_args()
    os.environ["SOOZ_DET"] = "1"
    A = tune.variant("ab_a", json.loads(args.a))
    B = tune.variant("ab_b", json.loads(args.b))
    skip = args.skip.split(",")
    opps = [p for p in sim.field_paths() if not any(x in p for x in skip)]
    opps += sorted(str(p) for p in Path(ROOT / "lab/field/anti").glob("*.py"))
    jobs = [(v, o, f"ab{args.seed0 + s}", args.deals) for v in (A, B) for o in opps for s in range(args.seeds)]
    res = sim.run_many(jobs, args.workers)
    by = {}
    for r in res:
        by.setdefault((r["a"], r["b"]), []).append(r)
    print(f"{'opponent':20}{'A bb':>8}{'B bb':>8}{'B-A':>8}{'zA':>7}{'zB':>7}")
    tot, ep = [0.0, 0.0], [0.0, 0.0]
    for o in opps:
        row = []
        for k, v in enumerate((A, B)):
            rs = by[(v, o)]
            m = sum(r["mean"] for r in rs) / len(rs)
            z = sum(r["mean"] / r["se"] for r in rs) / len(rs)
            tot[k] += m
            ep[k] += sim.expected_points(z)
            row += [m, z]
        print(f"{Path(o).stem:20}{row[0]:8.2f}{row[2]:8.2f}{row[2] - row[0]:8.2f}{row[1]:7.1f}{row[3]:7.1f}")
    print(f"{'TOTAL':20}{tot[0]:8.2f}{tot[1]:8.2f}{tot[1] - tot[0]:8.2f}   expected points A {ep[0]:.2f}  B {ep[1]:.2f}  of {len(opps)}")


if __name__ == "__main__":
    main()
