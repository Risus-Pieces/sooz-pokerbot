"""
export_bp.py - pack a solver/mccfr2 checkpoint into a compact blueprint .npz.

    python lab/export_bp.py CKPT_DIR data/bp/<name>.npz [--latest]

Reads CKPT_DIR/strat_{0..3}.bin (uint8[dnodes_s][B_s][4], x255) and meta.txt,
checks the shapes against data/tree.npz and data/abs.npz, and writes an
uncompressed npz (fast to load) with s0..s3, nb and meta. --latest also copies
it (atomically) to data/bp/latest.npz in the repo (the default for blueprint.py / lab/field/bp_bot.py).
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ckpt")
    ap.add_argument("out")
    ap.add_argument("--latest", action="store_true")
    a = ap.parse_args()
    ck = Path(a.ckpt)
    meta = (ck / "meta.txt").read_text()
    kv = {}
    for line in meta.splitlines():
        parts = line.split()
        kv[parts[0]] = parts[1:]
    nb = np.array([int(x) for x in kv["buckets"]], dtype=np.int32)
    nd = [int(x) for x in kv["decision_nodes"]]
    t = np.load(ROOT / "data" / "tree.npz")["tree"]
    dec = t[:, 1] >= 0
    for s in range(4):
        assert nd[s] == int((dec & (t[:, 0] == s)).sum()), "tree mismatch"
    absnb = np.load(ROOT / "data" / "abs.npz")["nb"]
    assert list(absnb) == list(nb), f"abs.npz nb {absnb} != checkpoint {nb}"
    arrs = {}
    for s in range(4):
        x = np.fromfile(ck / f"strat_{s}.bin", dtype=np.uint8)
        assert x.size == nd[s] * nb[s] * 4, f"street {s} size {x.size}"
        arrs[f"s{s}"] = x.reshape(nd[s], nb[s], 4)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".tmp.npz")
    np.savez(tmp, nb=nb, meta=np.array(meta.replace("\n", "; ") + f"src {ck}"), **arrs)
    tmp.replace(out)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB): {meta.strip().replace(chr(10), '; ')}")
    if a.latest:
        dst = ROOT / "data" / "bp" / "latest.npz"
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp2 = dst.with_name("latest.tmp.npz")
        shutil.copyfile(out, tmp2)
        tmp2.replace(dst)                       # atomic swap for readers
        print(f"copied to {dst}")


if __name__ == "__main__":
    main()
