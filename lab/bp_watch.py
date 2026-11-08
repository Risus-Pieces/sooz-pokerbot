"""
bp_watch.py - follow a running solver/mccfr2 job: export every new checkpoint and evaluate it.

    nohup python lab/bp_watch.py RUN_DIR EXPORT_DIR [--until-min 500] > watch.log 2>&1 &

For each new RUN_DIR/ckpt_<min>/ (strat files complete): lab/export_bp.py ->
EXPORT_DIR/m<min>.npz, copy to data/bp/latest.npz (atomic), then lab/bp_eval.py
(field incl. hunter_v2, 2 seeds x 1000 deals, 4 workers) which appends to
lab/results/blueprint_eval.md. Exits when ckpt >= --until-min is processed or
the solver process is gone and nothing new remains.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("export_dir")
    ap.add_argument("--until-min", type=int, default=495)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--skip", type=int, nargs="*", default=[], help="checkpoint minutes already handled")
    a = ap.parse_args()
    run, exp = Path(a.run), Path(a.export_dir)
    exp.mkdir(parents=True, exist_ok=True)
    done = set(a.skip)
    py = sys.executable
    while True:
        cks = sorted((int(p.name.split("_")[1]), p) for p in run.glob("ckpt_*") if p.is_dir())
        new = [(m, p) for m, p in cks if m not in done and (p / "meta.txt").exists()]
        for m, p in new:
            time.sleep(10)                       # let the writer finish the files
            out = exp / f"m{m:03d}.npz"
            r = subprocess.run([py, str(ROOT / "lab" / "export_bp.py"), str(p), str(out), "--latest"],
                               capture_output=True, text=True)
            print(time.strftime("%H:%M:%S"), "export", m, r.returncode, r.stdout.strip(), r.stderr.strip()[-500:], flush=True)
            done.add(m)
            if r.returncode != 0:
                continue
            iters = ""
            for line in (p / "meta.txt").read_text().splitlines():
                if line.startswith("iterations"):
                    iters = f"{int(line.split()[1]) / 1e9:.2f}e9 it"
            r = subprocess.run([py, str(ROOT / "lab" / "bp_eval.py"), str(out), "--label",
                                f"ckpt {m} min ({iters})", "--workers", str(a.workers)],
                               capture_output=True, text=True)
            print(time.strftime("%H:%M:%S"), "eval", m, r.returncode, r.stdout.strip()[-3000:], r.stderr.strip()[-500:], flush=True)
            if m >= a.until_min:
                return
        alive = subprocess.run(["pgrep", "-f", "solver/mccfr2"], capture_output=True).returncode == 0
        if not alive and not new:
            print("solver gone, exiting", flush=True)
            return
        time.sleep(30)


if __name__ == "__main__":
    main()
