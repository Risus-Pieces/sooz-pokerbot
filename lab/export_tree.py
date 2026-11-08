"""
export_tree.py - export the EXACT betting tree of game.py (cards don't affect
betting) so the solver (C++) and the runtime bot share one node numbering.

Players are named by role, not seat: 0 = button (small blind, acts first
preflop), 1 = big blind. Nodes are numbered in depth-first preorder from the
root (blinds posted, button to act). Writes data/tree.npz and data/tree.bin.

tree.bin layout (little-endian int32): N, then for each node:
    street, actor(-1 terminal), term(0 decision / 1 fold / 2 showdown),
    fold_winner(-1 unless fold), contrib_button, contrib_bb,
    child[FOLD], child[CHECK_CALL], child[RAISE_HALF], child[RAISE_POT]   (-1 = illegal)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game import Action, Deal, Game  # noqa: E402

FIELDS = 10


def build():
    deal = Deal(hole_cards=((0, 1, 2, 3, 4), (5, 6, 7, 8, 9)), board=(10, 11, 12, 13, 14))
    rows: list[list[int]] = []

    def walk(g: Game) -> int:
        idx = len(rows)
        row = [int(g.street), -1, 0, -1, g.contributed[0], g.contributed[1], -1, -1, -1, -1]
        rows.append(row)
        if g.is_terminal:
            r = g.result()
            row[0] = int(g.street)
            if r.went_to_showdown:
                row[2] = 2
            else:
                row[2] = 1
                row[3] = r.winner_seat  # seat 0 is the button in this export
            return idx
        row[1] = g.to_act
        for a in g.legal_actions():
            c = g.clone()
            c.apply(a)
            row[6 + int(a)] = walk(c)
        return idx

    walk(Game(deal, button_seat=0))
    return np.array(rows, dtype=np.int32)


def main() -> None:
    t = build()
    (ROOT / "data").mkdir(exist_ok=True)
    dec = t[:, 1] >= 0
    # decision-node index within each street (for infoset tables)
    dindex = np.full(len(t), -1, dtype=np.int32)
    counts = []
    for s in range(4):
        m = dec & (t[:, 0] == s)
        dindex[m] = np.arange(m.sum(), dtype=np.int32)
        counts.append(int(m.sum()))
    np.savez_compressed(ROOT / "data" / "tree.npz", tree=t, dindex=dindex)
    with open(ROOT / "data" / "tree.bin", "wb") as f:
        np.array([len(t)], dtype="<i4").tofile(f)
        t.astype("<i4").tofile(f)
    print(f"nodes {len(t)}  decision per street {counts}  terminals {(~dec).sum()}")


if __name__ == "__main__":
    main()
