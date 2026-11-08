"""Tests for the blueprint runtime: tree walk, card buckets, legality.

    python -m pytest tests/test_blueprint.py -q
"""
import dataclasses
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lab"))

import cardabs  # noqa: E402
from blueprint import Blueprint, sample  # noqa: E402
from brain import canonical_key  # noqa: E402
from fasteval import best_scores  # noqa: E402
from game import Action, Game, make_deal  # noqa: E402


def _fake_strategy(path, seed=0):
    """Random strategy file with the right shapes (legal actions only)."""
    z = np.load(ROOT / "data" / "tree.npz")
    t = z["tree"]
    nb = np.load(ROOT / "data" / "abs.npz")["nb"].astype(np.int32)
    rng = np.random.default_rng(seed)
    arrs = {}
    for s in range(4):
        rows = t[(t[:, 1] >= 0) & (t[:, 0] == s)]
        legal = (rows[:, 6:10] >= 0)[:, None, :]
        x = rng.integers(1, 255, size=(len(rows), int(nb[s]), 4)) * legal
        arrs[f"s{s}"] = x.astype(np.uint8)
    np.savez(path, nb=nb, meta=np.array("fake"), **arrs)
    return path


@pytest.fixture(scope="module")
def bp(tmp_path_factory):
    p = _fake_strategy(tmp_path_factory.mktemp("bp") / "fake.npz")
    b = Blueprint()
    assert b.load(p)
    return b


def _random_games(n, seed):
    rng = np.random.default_rng(seed)
    for g_i in range(n):
        g = Game(make_deal(f"t{seed}", g_i), button_seat=g_i % 2, hand_index=g_i)
        while not g.is_terminal:
            obs = g.observation(g.to_act)
            yield g, obs
            legal = g.legal_actions()
            # bias toward raises so deep raise sequences and all-ins are covered
            w = np.array([1.0 if a < 2 else 1.5 for a in legal])
            g.apply(legal[rng.choice(len(legal), p=w / w.sum())])


def test_walk_matches_tree(bp):
    T = bp.tree
    n_dec = 0
    for g, obs in _random_games(1500, 1):
        node = bp.walk(obs)
        assert node is not None
        assert bp.check(node, obs), (obs, T[node])
        role = 0 if obs.is_button else 1
        assert T[node][1] == role and T[node][0] == int(obs.street)
        n_dec += 1
    assert n_dec > 5000


def test_incremental_walk_cache(bp):
    cache = {}
    for g, obs in _random_games(100, 2):
        if cache.get("bph") != obs.hand_index:
            cache.clear()
            cache["bph"] = obs.hand_index
        assert bp.walk(obs, cache) == bp.walk(obs, None)


def test_policy_legal_and_normalized(bp):
    rng = np.random.default_rng(3)
    cache = {}
    for g, obs in _random_games(150, 3):
        p = bp.policy(obs, cache, rng)
        assert p is not None
        assert set(p) == set(obs.legal_actions)
        assert abs(sum(p.values()) - 1.0) < 1e-9
        assert sample(p, rng) in obs.legal_actions
        assert sample(p, rng, 0.2) in obs.legal_actions


def test_mismatch_returns_none(bp):
    for g, obs in _random_games(5, 4):
        bad = dataclasses.replace(obs, pot=obs.pot + 2)
        assert bp.policy(bad, {}, None) is None
        bad2 = dataclasses.replace(obs, is_button=not obs.is_button)
        assert bp.policy(bad2, {}, None) is None
    # unloaded blueprint never raises
    assert Blueprint().policy(obs, {}, None) is None


def test_preflop_bucket_is_class():
    keys = np.load(ROOT / "data" / "preflop.npz")["keys"]
    rng = np.random.default_rng(5)
    for _ in range(500):
        h = rng.choice(36, 5, replace=False)
        assert keys[cardabs.bucket(h, ())] == canonical_key(h)


def _brute(hole, board, rng, n=20000):
    hole, board = np.asarray(hole), np.asarray(board)
    used = np.zeros(36, bool)
    used[hole] = True
    used[board] = True
    rem = np.flatnonzero(~used)
    need = 5 - len(board)
    d = rem[np.argsort(rng.random((n, len(rem))), axis=1)[:, :5 + need]]
    full = np.concatenate([np.broadcast_to(board, (n, len(board))), d[:, 5:]], 1)
    a = best_scores(np.broadcast_to(hole, (n, 5)), full)
    b = best_scores(d[:, :5], full)
    ehs = ((a > b) + 0.5 * (a == b)).mean()
    a2 = best_scores(hole[None], board[None])[0]
    b2 = best_scores(d[:, :5], np.broadcast_to(board, (n, len(board))))
    return ehs, ((a2 > b2) + 0.5 * (a2 == b2)).mean()


def test_features_match_monte_carlo():
    rng = np.random.default_rng(6)
    diffs = {3: [], 4: [], 5: []}
    for _ in range(12):
        c = rng.choice(36, 10, replace=False)
        for nb in (3, 4, 5):
            f = cardabs.features(c[:5], c[5:5 + nb])
            g = _brute(c[:5], c[5:5 + nb], rng)
            diffs[nb].append((f[0] - g[0], f[1] - g[1]))
    tol = {3: 0.06, 4: 0.04, 5: 0.04}           # ~4 SE of the runtime estimators
    for nb, d in diffs.items():
        d = np.array(d)
        assert np.abs(d).max() < tol[nb], (nb, d)
        assert abs(d.mean()) < tol[nb] / 3, (nb, d.mean(0))


def test_bucket_function_matches_bucketize():
    import bucketize
    A = bucketize.load_abs()
    cardabs.load()
    rng = np.random.default_rng(7)
    e, h = rng.random(3000).astype(np.float32), rng.random(3000).astype(np.float32)
    # include exact edge values
    e[:30] = A["flop_e"][:30]
    for st, name in ((1, "flop"), (2, "turn")):
        ref = bucketize.bucket_2d(e, h, A[f"{name}_e"], A[f"{name}_h"])
        got = [cardabs.bucket_from_features(st, float(x), float(y)) for x, y in zip(e, h)]
        assert np.array_equal(ref, got)
    ref = bucketize.bucket_1d(h, A["river"])
    got = [cardabs.bucket_from_features(3, 0.0, float(y)) for y in h]
    assert np.array_equal(ref, got)


def test_buckets_in_range():
    cardabs.load()
    nb = cardabs._A["nb"]
    rng = np.random.default_rng(8)
    for _ in range(100):
        c = rng.choice(36, 10, replace=False)
        for st, n in ((0, 0), (1, 3), (2, 4), (3, 5)):
            assert 0 <= cardabs.bucket(c[:5], c[5:5 + n]) < nb[st]


def test_bp_bot_plays_legal(tmp_path):
    p = _fake_strategy(tmp_path / "fake.npz", seed=1)
    os.environ["BP_PATH"] = str(p)
    try:
        spec = importlib.util.spec_from_file_location("bp_bot_t", ROOT / "lab" / "field" / "bp_bot.py")
        bot = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bot)
        mem = {}
        bot.new_half(None, mem)
        rng = np.random.default_rng(9)
        for i in range(150):
            g = Game(make_deal("bot", i), button_seat=i % 2, hand_index=i)
            while not g.is_terminal:
                obs = g.observation(g.to_act)
                if g.to_act == 0:
                    a = bot.choose_action(obs, mem)
                else:
                    legal = g.legal_actions()
                    a = legal[rng.integers(len(legal))]
                assert a in obs.legal_actions
                g.apply(a)
            bot.on_hand_end(g.hand_result(0), mem)
        assert mem["fallbacks"] == 0
    finally:
        os.environ.pop("BP_PATH", None)
