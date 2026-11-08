# FINAL DESIGN v3 (post-review): "Sooz Hybrid" heads-up Short-Deck PLO5 bot

**Status:** binding spec for builder agents. Revised at 03:25 CST on Nov 8, after review. The deadline is about 16:00 CST and the final SHA is due at 14:30.

**Repo:** `pokerbot/`.
- `game.py`, `evaluator.py` and `judge_engine.py` are official and read-only.
- `strategy.py` is frozen as the hunter v2 reference. The runtime hunter becomes `hunter.py` (§3.9).

**Live submission:** the hunter v2 SHA stays live until a gated candidate replaces it.

**Verified facts this revision relies on (read from the repo):**
- The Dockerfile runs `CMD ["python", "agent.py"]`, so an `if __name__ == "__main__":` block runs only in the server.
- `judge_engine.start_half` forfeits the half if `/new-half` returns None. That happens on HTTP 500 or on a timeout longer than 1 s.
- `HandResult` has no action history, so a fold is never visible in `action_history`.
- `strategy._n_samples` hardcodes `/1000` and `6.5`.
- `AgentConfig` carries `time_bank_seconds` and `num_hands`, and game.py labels its constants PROVISIONAL.
- uvicorn's default keep-alive is 5 s.
- The disk has 17 GiB free.
- A stray `./solver/pool … 3000000 600 12` job has been running since 02:45 at ≈1,200% CPU.

---

## 0. Decisions in one page

**Thesis, inverted from v2 of this spec: hunter is the default, and the blueprint is a hedge arm.**
- Hunter v2 beats every lab bot, most at z ≫ 4. Exploitation wins both the points and the tie-break bb.
- An equilibrium blueprint is worth something only against the few opponents that hunter does not beat: strong CFR/RL teams, or bots that happen to exploit hunter.
- That value has to be **measured**, both in the lab (WI-11, independent proxies) and in every half (arm A/B). It is not assumed.

**The pieces:**
- **Default policy: hunter v2.1** (`hunter.py`), the hardened hunter v2 described in §3.9.
- **Hedge arm: MCCFR blueprint.**
  - It is trained over the exact betting tree, with tree v2 merging twin raise subtrees.
  - Preflop is lossless (19,998 classes). Postflop uses deterministic integer features (SDF v1), which are bit-identical in the C++ trainer, the prebuilt C library and the numpy reference.
  - Training uses the existing pool-based Hogwild external-sampling MCCFR (`mccfr2`).
- **Arm controller** (§3.10):
  - One arm is drawn per hand.
  - p_B is the Thompson probability that μ_B > μ_H given in-half data. The data are all-in-EV-adjusted per-hand nets, and the empirical-Bayes prior favours hunter.
  - Exploration floors run only while the match is "in doubt".
  - A stop-loss pushes toward B when hunter is clearly losing.
  - Degenerate-opponent and AUTOPILOT overrides force hunter or bet-everything.
  - Every half starts with 50 pure-hunter hands.
- **Exploit search against hunter is mandatory and early** (WI-11). CMA-ES ParamBots tuned to beat v2.1 answer "does anything beat hunter, and how?". They feed hunter v3 hardening and the strong-proxy class.
- **Statistics** (§7):
  - Class-pooled intersection-union non-inferiority, with no Holm correction.
  - A per-opponent catastrophic-loss guard.
  - A first-class tie-break (TB) gate.
  - Improvement is measured on the unsaturated "hard set".
  - A controller-regret gate replaces the self-referential exploiter and ε gates.
- **Engineering hygiene:**
  - Explicit disk, RAM and CPU budgets, enforced by a watchdog.
  - A deterministic lab mode, so incumbent results are cached.
  - All per-bot state lives in `memory`.
  - Server-only startup side effects.
  - A protected `new_half`.
  - A hardened native library, with its status shown in `GET /`.

**Grafts:**

| Source | Grafted idea |
|---|---|
| P1 | Exact-EV evaluator `evalbp` (Tier A). Per-decision node/observation consistency check. Golden tests and startup self-test that disable the blueprint on any mismatch. Self-play reference (now per-node conditional frequencies). |
| P3 | Control variate (equity martingale) in the lab. Disjoint seed banks with select-then-confirm. Config/rules guard. Earlier freeze. Stop-loss. |
| P1 (fixed) | Arms are mixed **per hand**, so BR(mixture) ≤ mixture of BRs. |
| P2 | AUTOPILOT detector (revised trigger, fold inference). Persona field with a holdout. Counter-bots. Charged-time accounting. gc and BLAS hygiene. |
| P4 | Colex preflop lookup. Low-visit fallback to hunter. Sampled-BR exploiters (now a guard only). Hedge run S. Startup speed calibration (now a prior only). |
| Review | Hunter-first control. Thompson A/B on all-in EV. Mandatory exploit search. Pooled IUT gates. Resource budgets. Determinism. Protected `new_half`. Raise-alias tree. |

**The original fixes to judged flaws are kept:**
1. A shorter critical path: M is 2048/2048/2048, quantile grids, the trainer is reused, Run0 validates it, and a hedge S run trains alongside.
2. A tolerant trigger, now superseded by the controller.
3. Deterministic features.
4. No numba at runtime.
5. Disjoint seed banks and a never-tuned holdout.
6. Bounded repo size.

**Rejected, with reasons:**

| Idea | Reason |
|---|---|
| Numba at runtime | JIT cost in every fresh process, and it cannot be interrupted. |
| River re-solve | Scope. |
| 10-class classifier / per-class θ (P2) | Overfits our own field. |
| Variance lever (P2) | It needs the paired result. |
| k-means | Quantile grids give the same bit-identity with less code. |
| Inline deal generation | The pool is faster and already exists. |
| **Band flags (style statistics vs a self-play reference) as the control law** | They are contaminated by our own arm mix, use many uncorrected looks, and ratchet. Replaced by a direct arm comparison. A style signal survives only as an optional, arm-mix-invariant prior shift (eqsig). |
| Flop ref-score precompute (33 MB) | The blueprint is now a minority arm. Cheap governor tiers handle time instead. |
| Orphan release branch | At most 3 bp versions keep history under 400 MB. |

**Ship ladder.** Every ship needs gates, a human form update, and a push notification that carries the SHA and the rollback SHA.

| Checkpoint | Time | Candidate |
|---|---|---|
| SHIP-1 | ~06:30 | v2.1 = hunter v2 + hardening + AUTOPILOT (hunter-only) |
| SHIP-2 | ~10:15 | best gated of {hybrid-S, hunter v3 (early flags)} |
| SHIP-3 | ~12:00 | optional: hybrid-M@4h or v3, only if gated and the human is reachable |
| SHIP-4 | 14:30 | final selection |

---

## 1. Objective (the scoring math every gate uses)

**Per match against opponent j:**
- μ_j and σ_j are the mean and SD of paired bb/deal, where paired = (net in half 1 + net in half 2)/BB.
- z_j = μ_j·√1000/σ_j.
- EP(z) = Φ(z−1.96) + 0.5·(1 − Φ(z−1.96) − Φ(−z−1.96)).
- Reference values: EP(0)=0.50, EP(1)=0.58, EP(2)=0.76, EP(3)=0.93, EP(4)=0.99.

**Lab utility:**
- U = Σ_j w_j·EP(ẑ_j), with ẑ_j = μ_adj,j·√1000/σ_raw,j.
- **Hard set H:** opponents where the incumbent's ẑ < 6, recomputed from the incumbent cache at each gate. U_hard is U restricted to H, using renormalised class weights. Where EP is saturated, ΔU is pure noise, so improvement gates use U_hard.
- **Tie-break TB = mean_j μ_raw,j** over league opponents, uniformly weighted. It mirrors the tournament's average bb/deal, which is dominated by weak opponents. TB is **first-class**: every gate checks ΔTB, using μ_adj for power.

**Consequences:**
- Points are decided against medium and strong bots.
- Average bb/deal is decided against weak bots, which make up roughly 60% of the field.
- Forfeits and empty time banks are catastrophic.

---

## 2. Architecture overview

```
agent.py (WI-06)
  module import: env BLAS=1 threads, imports, hook functions (NO side effects beyond immutable tables)
  __main__ only : startup (eval check, self-tests, bp RAM preload, warm, speed prior, gc.freeze/disable),
                  status string for GET /, uvicorn.run(timeout_keep_alive=120)
  hooks: new_half (double try/except), choose_action, on_hand_end — each keeps its own think accounting
     │
     ▼
policy.py (WI-05)  [if policy.available() and not memory['policy_off'] else hunter-only path]
  ├─ governor.py (WI-06)     – charged-time estimate C, tiers as fractions of config bank; single owner of n
  ├─ autopilot.py (WI-06)    – opponent auto check/fold detector (with inferred terminal folds) → bet-everything
  ├─ controller.py (WI-05)   – arm controller (Thompson p_B, doubt gate, floors, stop-loss, degenerate)
  │     ├─ allin_ev.py       – all-in EV adjustment of per-hand nets (in-half variance reduction)
  │     └─ eqsig.py          – optional: opponent per-node frequency distance vs blueprint (prior shift)
  ├─ per-hand arm draw (per-hand RNG): B with prob p_B, else H
  ├─ blueprint.py (WI-04)    – tree2 walk + alias + consistency, buckets, row, purify, sample
  │     ├─ cardabs.py (WI-04) – ctypes libsdf (lib/<plat>/), validated calls, self-test
  │     ├─ abs_buckets.py (WI-02)
  │     └─ data/bp/ship/ (WI-14) – the ONLY tracked bp directory
  └─ hunter.py (WI-06) or hunter_v3.py (WI-12)  – note_raise() on every raise from any path
release_cfg.py (WI-14)       – knob overrides; the only file edited when tuning
```

**Offline:**
- `lab/export_tree2.py` (WI-15) → `solver/sdf.hpp` (WI-01) → `solver/pool2.cpp` (WI-02, streaming, reads `pre_class.u16`)
- → `lab/fit_edges.py` and `lab/bucketize.py` → `lab/check_pool.py` (gate GA)
- → `solver/mccfr2.cpp` (WI-03a: trainer, BR, virtual clock) and `solver/evalbp.cpp` (WI-03b: exact EV, nodefreq)
- → `lab/export_bp.py` → `~/sooz_runs/bp/<tag>` (outside the repo)
- → at ship time only, `tools/ship.sh` copies a tag to `data/bp/ship/`.

**Lab:**
- `lab/evalx.py` (DET mode, hook timing, incumbent cache), `lab/cv.py`, `lab/report.py`, `lab/league.py`, `lab/seeds.py`, `lab/vendor.py` (WI-07)
- `lab/gate.py`, `lab/select_final.py`, `lab/power.py` (WI-13)
- `lab/parambot.py` and `lab/exploit_search.py` (WI-11)
- Field bots (WI-08) and vendored proxies (WI-10)
- Docker/HTTP timing (WI-09)
- `tools/watchdog.sh` (WI-00)

---

## 3. Component specifications

### 3.0 Runtime state and determinism rules (new; binding on every runtime module)

1. **All per-bot state lives in `memory`.** That covers cfg, the Gov object, controller state, autopilot state, the blueprint walk cache, the arm, counters and the trace.
   - Module globals may hold only immutable tables: the eval table, the preflop table, tree arrays, bp arrays and the libsdf handle.
   - `DEFAULTS` is deep-copied into `memory['cfg']` in `new_half`.
2. **Overrides come in through `memory['__overrides__']`,** which a variant wrapper sets before calling `new_half`. They are never module attributes.
3. **Server-only side effects.** `gc.disable()`, `gc.freeze()`, the speed benchmark, self-tests, the blueprint RAM preload and the status string all live in the `__main__` block of `agent.py`. Lab imports of `agent` do none of this. Lab workers call `blueprint.preload(tags, mode='mmap')` in their initializer.
4. **Per-decision RNG.** Every random draw uses `rng_for(memory, hand_index, k, purpose)` = `np.random.default_rng([HALF_SEED, hand_index, k, purpose])`.
   - k = `len(action_history)` for decisions, and 99 for hand-end.
   - purpose ∈ {hunter, bp, arm, learn, allin}.
   - So changing the sample count n cannot shift any later decision.
5. **Deterministic lab mode, `SOOZ_DET=1`.** The governor tier is pinned to T0, n = `cfg.hunter_n`, the speed factor is 1.0 and there is no benchmark. Think time is still measured and reported but never read by decisions.
   - Every statistical lab run and every parity test uses DET.
   - Only timing runs (G1, calibration) are non-DET.
6. **`new_half` does no I/O, hashing, loading or benchmarking.** Its target is ≤ 2 ms.
7. **Isolation test (WI-07):** hybrid vs hybrid with different overrides in one process must make the same decisions as each against a stub in separate processes.

### 3.1 Betting tree (v1 exists; v2 by WI-15)

- `tree` int32[N,10] with columns street, actor (0 button, 1 big blind, −1 terminal), term (0 decision, 1 fold, 2 showdown), fold_winner, cb, co, child[FOLD, CHECK_CALL, RAISE_HALF, RAISE_POT] (−1 = illegal). `dindex` gives the decision index within its street.

**Tree v2 (raise-alias merge).**
- At 4,264 of the 6,384 raise-legal decision nodes, `raise_to(HALF) == raise_to(POT)`. Those twin subtrees are identical game states.
- tree2 expands only RAISE_HALF there, sets child[POT] = −1 in `tree2.bin` (the trainer sees one action), and sets `alias[node]=1` in `tree2.npz`.
- The merge is lossless. It shrinks the tree, the regret tables and RAM, speeds convergence, and reduces low-visit fallbacks.

**Runtime walk (`blueprint.py`):**
- Follow `child[int(a.action)]` for each `ObservedAction`. If the action is POT and `alias[node]`, follow `child[HALF]`.
- **Assert child ≥ 0.** Otherwise mark the hand as mismatched, and hunter plays the rest of that hand.
- Blind posts are skipped if present (WI-04 verifies).
- The walk is cached in `memory['bpw']`, per hand and incrementally.

**Consistency check** at every blueprint decision. Each of the following must hold, otherwise the decision goes to hunter and `bp_mismatch` += 1:
- actor == our role
- street == obs.street
- cb + co == obs.pot
- max(cb,co) − ours == obs.to_call
- (tree-legal ∪ {POT if alias}) == set(obs.legal_actions)

When the blueprint samples HALF at an alias node, we play HALF. The amount is the same.

**Config guard:** the blueprint is enabled only if (stack, BB, SB, cap) == (80, 2, 1, 4) and `num_hands` > 0. Bank and num_hands are handled by the governor (§3.11).

### 3.2 Hand evaluation

- `sd::Eval` in `solver/core.hpp` uses table index 2·Σ5^rank + flush, which is fasteval's table. `best(hole, board, nb)` covers nb ∈ {3,4,5} and must equal `evaluator.omaha_score`.
- Card encoding is `rank_idx*4 + suit`. WI-01 asserts that it matches game.py.
- **Startup eval check (server mode):** on a fixed set of 2,000 hands, check `fasteval.score_one == omaha_score` and `sdf_best == omaha_score`.
  - On a fasteval mismatch, rebuild the table from `evaluator` (≈2 s, free).
  - On an `sdf_best` mismatch, `cardabs.ok = False`.
  - This protects against a stale committed `data/eval_both.npy`.

### 3.3 SDF v1: deterministic integer card features (WI-01; `solver/sdf.hpp`, `sdf_ref.py`)

The math is unchanged from v2 of this spec:

| Constant | Value |
|---|---|
| SDF_VERSION | 1 |
| K_FLOP_RUN | 24 |
| R_RUN | 48 |
| R_NOW | 128 |
| R_RIVER | 1024 |
| NUT_T | 973 |
| TOP_N | 102 |

Salts are SALT_REF = 0x243F6A8885A308D3, SALT_RUN = 0x13198A2E03707344, SALT_NOW = 0xA4093822299F31D0.

**RNG and helpers:**
- splitmix64 with uint64 wraparound.
- `u(n) = (next()>>11) % n`.
- `draw_refs(board, R, salt)` is a partial Fisher-Yates over the ascending complement, seeded with `mask(board)^salt`, with **no reset** between refs.
- HSint(lt,eq,n) = ((2·lt+eq)·1024)//(2·n).

**Flop (H, F) → (E, NUT, NOW, nvalid):**
- 24 splitmix runouts (SALT_RUN); 48 refs per runout on B5 (SALT_REF); a runout is valid if it does not hit H.
- E = Σhs//nvalid; NUT = #{hs≥973}·1024//nvalid; if nvalid = 0, E = 512 and NUT = 0.
- NOW = HSint over 128 refs on the 3-card board (SALT_NOW).

**Turn:** all 32 rivers in ascending order (no RNG); otherwise the same as the flop, with NOW on 4 cards.

**River (H, B5) → (HS, BLK, nvalid, ntop):**
- 1024 refs. HS is over valid refs only (removal-aware); 512 if nvalid = 0.
- thr = the 102nd-largest score over all refs. BLK = #{TOP refs hitting H}·1024//|TOP|.

**C API** (`solver/sdf_c.cpp`, extern "C"):
```
int sdf_version(void);                                   // 1
int sdf_init(const int32_t* eval_both, int64_t n);       // 0 ok; n must be 3906250
int sdf_flop (const int32_t hole[5], const int32_t board[3], int32_t out[4]);
int sdf_turn (const int32_t hole[5], const int32_t board[4], int32_t out[4]);
int sdf_river(const int32_t hole[5], const int32_t board[5], int32_t out[4]);
int sdf_best (const int32_t* hole, const int32_t* board, int nb, int32_t* out);   // new: self-test
double sdf_bench(int iters);
```

**Hardening (new):**
- Every function validates its input: cards in 0..35, all hole and board cards distinct, nb ∈ {3,4,5}, and init done.
- On bad input it returns a negative error code. It never asserts, aborts or exits.
- The only mutable global is the eval pointer.
- Fuzzing: `solver/fuzz_sdf.cpp` runs under `-fsanitize=address,undefined` with 10M valid states (every one of the 7,140 flops at least once) and 1M invalid ones.

**Builds:**
- mac: `clang++ -O2 -shared -fPIC`.
- linux: `-O2 -march=x86-64 -mtune=generic -fPIC -shared -ffp-contract=off -static-libstdc++ -static-libgcc`, built in a throwaway container from the pinned base image with g++ apt-installed.
- `tools/glibc_check.sh` requires the max GLIBC symbol to be ≤ the base image's glibc and requires no NEEDED libstdc++ or libgcc_s.
- The .so must load and pass the golden test in the **pristine** runtime image, without g++.
- No floating point anywhere in the feature path.

`BoardCtx` is header-only. It precomputes per-board ref scores so `pool2` can share work across 64 hole pairs, and it must equal the single-hand API exactly.

**Cost targets (C, laptop, including ctypes):** flop ≤ 1.5 ms, turn ≤ 2.0 ms, river ≤ 1.2 ms. `sdf_ref.py` is about 5 ms per street and is test-only.

### 3.4 Preflop classes (WI-01)

- `data/abs/pre_class.u16` is raw little-endian uint16[376,992].
- Index = colex of the sorted hole (Σ C(c_i, i+1)).
- Value = class id in `data/preflop.npz` order, from `brain.canonical_key`. Lookup takes about 3 µs.
- **`pool2` reads this file and never computes classes itself** (§3.6). `brain.preflop_equity` uses it, with an identical result.

### 3.5 Card abstraction: nested quantile grids (WI-02)

This section is unchanged.
- Preflop bucket = class id (19,998).
- Flop and turn: features (E, NOW, NUT) through nested right-searchsorted edges. River: (HS, BLK).

| Abstraction | Flop | Turn | River |
|---|---|---|---|
| S | (8,8,4) = 256 | (8,8,4) = 256 | (32,8) = 256 |
| M | (32,16,4) = 2048 | (32,16,4) = 2048 | (256,8) = 2048 |

- Re-plan rule: if fewer than 60% of a street's buckets are non-empty, use (64,32,1).
- Files: `data/abs/<S|M>/{flop,turn,river}.npz` and `abs.txt` (sha256 and sdf_version).
- `abs_buckets.py` provides `load_abs`, `Abs.bucket` and `Abs.bucket_batch`, which must be identical. One module is shared by the runtime and the lab.

### 3.6 Pools (WI-02; files in `~/sooz_runs/pools/`, never in the repo)

```
pool2 EVALBIN PRECLASS_U16 OUT N_DEALS HOLES_PER_BOARD THREADS SEED
```

- Each board group: 5 board cards, `BoardCtx`, and 64 disjoint hole pairs.
- 64-byte records (cards[15], showdown, pre_class[2], flop/turn/river features) behind a 64-byte header (SDFPOOL1).
- **Streaming:** each thread writes 64k-record blocks through a bounded queue, so RSS stays ≤ 300 MB.
  - Every fopen, fwrite and fclose is checked. Output goes to `OUT.tmp` and is renamed at the end. On ENOSPC: non-zero exit and no final file.
- **pre_class comes from `pre_class.u16`.**
- Pool A: 32M deals (2.05 GB). S uses the first 16M deals.
- Pool B: 2M deals, different seed.
- `lab/bucketize.py` writes `<prefix>_buckets.bin` (uint16[n][2][4]) and `<prefix>_showdown.bin` (int8[n]).

**Gate GA (`lab/check_pool.py`):**
- (a) 2k deals: pool features == C single-hand API == `sdf_ref`.
- (b) 100k records: `pre_class[i] == pre_class_u16[colex(sorted hole)]` for both seats.
- (c) 10k showdowns == `omaha_score`.
- (d) 2k pool-B deals: the runtime bucket path (pre_class → `cardabs.features` → `Abs.bucket`) == `buckets.bin`, for every street and seat.
- (e) mac dylib == linux .so (in Docker) == `sdf_ref` on 10k golden states.

### 3.7 Trainer, best response, exact evaluator (WI-03a, WI-03b)

**`solver/mccfr2.cpp` (WI-03a)** is derived from `mccfr.cpp`, which stays untouched. It keeps external sampling, the alternating traverser, regret matching, Hogwild threads, opponent-node average accumulation and the `R/S[street][dnode][bucket][4]` float32 layout.

1. **Named flags:**
   ```
   --tree --buckets --showdown --out --nb B0 B1 B2 B3 --threads --minutes --ckpt-min
   --export-at m1,m2,… --export-cur --disc-epoch-min --disc-until-min --prune-after-min
   --resume DIR --freeze-opp BPDIR --seed
   ```
2. **Virtual clock (new).**
   - Every schedule (discount epochs, prune switch, exports, checkpoints, stop) runs on *virtual minutes* = minutes persisted in the checkpoint + minutes of the current run.
   - The checkpoint header stores magic, tree sha, NB, iteration count, virtual minutes, last discount epoch applied, prune state, next export and next checkpoint.
   - `--resume` restores all of them, so no discount is ever applied twice.
3. **Discount:** at the end of epoch e (e ≤ disc_until/disc_epoch), multiply R and S by e/(e+1).
4. **Pruning:** after prune-after-min, in 95% of traverser visits, skip actions with regret < −2e5, except on river nodes and actions whose child is terminal. The regret floor is −3e5.
5. **Visit counter:** uint32 V per infoset.
6. **Exports** go to `OUT/export_<min>/` via a temporary directory and a rename.
   - Each export writes avg `s{st}.npy` (uint8 ×255; illegal = 0; zero-sum rows uniform over legal), `conf{st}.npy` = min(255, ⌊16·log2(1+V)⌋) and `meta.txt`.
   - `cur{st}.npy` is written **only with `--export-cur`** (M final only).
7. **Checkpoints (new policy):**
   - Exactly 1 raw checkpoint plus 1 in-progress `.tmp`, and no `latest` copy.
   - Every fopen, fwrite, fflush, fclose and rename is checked. On failure, delete the `.tmp`, log the error and **continue training**.
   - On resume, validate the header and that file sizes == NDEC×NB×4×4 bytes. A short or corrupt checkpoint is refused and the job stops loudly; it never silently resizes.
8. **`--freeze-opp BPDIR` (best response):**
   - The opponent samples from BPDIR's average strategy. The traverser trains its own regrets, and the roles alternate.
   - **The trained side's *average* strategy is exported** as `exploiter_<tag>`. BR jobs run for 30 min.
9. Throughput, RSS and virtual-minutes log every 60 s.

**`solver/evalbp.cpp` (WI-03b):**
- Exact EV of A vs B over pool-B deals by a full tree walk, with reach pruning below 1e-7, both seatings, and each blueprint using its own buckets file.
- Output, one key=value line per metric: mean paired bb/deal, SE, and per-seat values.
- `--self A --nodefreq OUT.npy` writes the self-play **per-node conditional action frequencies** P(a | node), float16 [nodes,4], averaged over the acting player's card distribution at that node, with aliased POT = 0. This is the reference for `eqsig` (§3.10).
- Requirements: A vs A within 2 SE of 0; A vs B = −(B vs A); agreement within 2 SE with `lab/playout_ref.py`, an independent pure-Python MC playout that reads `buckets.bin` directly and does not depend on `blueprint.py`.
- **Exploitability:** expl(tag) = evalbp(exploiter_tag vs tag), with SE. It is used as a trend and guard only.

### 3.8 Blueprint package and runtime (WI-04; packaging WI-10/WI-14)

**Locations:**
- Exports and exploiters live in `~/sooz_runs/bp/<tag>/`.
- The repo tracks **only `data/bp/ship/`**, a copy of the one shipping tag, made by `tools/ship.sh`.
- `.gitignore` ignores `data/bp/*` except `!data/bp/ship/`. `.dockerignore` allow-lists the runtime files plus `data/bp/ship/`.
- At most 3 bp versions ever enter git history (target ≤ 400 MB).

**Package contents:**
- `meta.txt`: tag, abs, buckets, strategy=avg, iterations, minutes, tree2_sha256, abs_sha256, sdf_version, chunks.
- `s{st}_{k}.npy` and `c{st}_{k}.npy`, uint8, each chunk ≤ 45 MB.
- `nodefreq.npy`.
- `ref.txt`: self-play aggregates, for diagnostics.

**Load modes:**
- **'ram'** (server, at startup): `np.fromfile` reads every chunk fully into RAM, so first-touch page faults never cost time-bank time. It checks sizes and meta hashes and computes a sampled checksum (every 4,096th byte), not a full sha of 170 MB.
- **'mmap'** (lab): pages are shared across worker processes, which keeps lab RAM bounded.

**`BP.act(obs, memory, cfg) -> Action | None`:**
1. Walk and run the consistency check.
2. Bucket: preflop via `pre_class[colex]`; postflop via `cardabs.features` → `Abs.bucket`, cached in `memory['bk'][(hand, street)]`.
3. If conf < c_min, return None.
4. Purify with tau.
5. Sample with `rng_for(…,'bp')`.
6. Return None on any problem.

**`cardabs.py`:**
- Platform-selected ctypes load and `sdf_init`.
- It keeps a module-level reference to fasteval's C-contiguous int32 table and re-checks its pointer and length before every call. A change disables it, without a crash.
- Every nonzero return code → features None → hunter.
- Golden self-test: 200 states, plus 500 `sdf_best` hands. Any failure sets `ok=False`.

### 3.9 Hunter v2.1, agent shell, AUTOPILOT (WI-06)

**`hunter.py`** is a copy of `strategy.py` with exactly these changes. Everything else is identical.
- `choose(obs, memory, params, rng)`:
  - n = `params['n']`, set by the governor. There is no `_n_samples`, so no double throttling.
  - `n == 'mhr'` → `mhr(obs)` (below).
  - It sets `pending` exactly as v2 does.
- `update_model` = v2's `_update_model`. It is idempotent via `memory['seen']`, and a test checks that.
- **`note_raise(obs, memory)`:** sets `memory['pending'] = (street, ctx)`, where ctx = 1 if the opponent raised this street (choose's definition). The policy calls it after **every** raise we make, whichever path chose it (H, B or autopilot).
- `learn_from_hand(result, memory, rng)`:
  - v2's logic with an explicit rng.
  - The fold is inferred as `not went_to_showdown and winner == 'me'` → the opponent folded to our last raise.
- **`mhr(obs)` (made-hand rule, ~30 µs):** one `fasteval` best-hand category, in short-deck order high < pair < two pair < straight < trips < full house < flush < quads < straight flush.
  - Unopened: bet RAISE_HALF if the category is ≥ straight (flop/turn) or ≥ trips (river); otherwise check.
  - Facing a bet: RAISE_POT if ≥ full house; call if ≥ straight, or if two pair and to_call ≤ 0.5·pot; otherwise fold.

**`agent.py` v2.1:**
- At the very top of the file (all modes), set `OMP/OPENBLAS/MKL_NUM_THREADS=1` before numpy is imported.

`new_half`:
```
try:    policy.new_half(config, memory) if POLICY_OK else hunter_init(config, memory)
except: memory.clear()
        try:    hunter_init(config, memory); memory['policy_off'] = True
        except: memory.clear(); memory['dead'] = True
return  # always 200
```
- `hunter_init` sets rng seeds, Stats, think, pending, seen, cfg and Gov. It does no I/O.
- With `memory['dead']`, every action is `CHECK_CALL` if legal, else the first legal action. It never raises.

`choose_action` and `on_hand_end`:
- Both are wrapped in try/except with a legal fallback, as in v2.
- **Each hook times itself**, and `on_hand_end` is included. It adds wall time and request counts to `memory['acct']`. That is the think figure in the lab and in the server alike.
- In server mode the route handlers also time the whole route and pass that to `Gov.reconcile`.

Server mode and status:
- Server-mode `__main__` runs §3.12 and then `uvicorn.run(app, …, timeout_keep_alive=120)`.
- `GET /` returns `agent_name` = `sooz-hunter`, `sooz-hybrid-<tag>-ok` or `sooz-hybrid-fallback`, computed at startup. `tools/status_check.py` and the G6 smoke assert it.

**AUTOPILOT (`autopilot.py`), revised:**
- Opponent decisions come from `action_history` **plus inferred terminal folds**. In `on_hand_end`, if not showdown and winner == 'me', append "fold facing bet".
- The judge's auto-play is `default_action(to_call)`.
- **Activate** when all of these hold:
  - hand ≥ 100;
  - the last **15** opponent decisions all equal `default_action`;
  - at least **6** of them are folds facing a bet;
  - **none** of them is a call or raise facing a bet;
  - the opponent's fold-facing-bet rate before the streak is < 0.6.
- **While active:** RAISE_HALF, else RAISE_POT, else CHECK_CALL.
- **Deactivate** on the first non-default opponent action.
- Late detection costs almost nothing, because an empty bank stays empty for the rest of the half.
- **Requirement:** zero activations in 200 halves against every S, A, guard and holdout bot.

### 3.10 Policy orchestrator and arm controller (WI-05)

**`policy.py`:**
```
available() -> bool                    # cardabs.ok and bp loaded and config guard ok
new_half(config, memory)               # cfg = deepcopy(DEFAULTS) ⊕ release_cfg.OVERRIDES ⊕ memory['__overrides__']
decide(obs, memory) -> Action
on_hand_end(result, memory)
```

**`decide`:**
1. `hunter.update_model(obs, m)`, then `autopilot.observe`, `controller.observe` and `eqsig.observe`. The last walks the opponent node; it is cheap and needs no features.
2. If autopilot is active → `autopilot.action`.
3. On the first decision of a hand: arm = 'B' if `rng_for(…,'arm').random() < controller.p_B(m)`, else 'H'. The arm is fixed for the whole hand.
4. **B arm:** `a = bp.act(...)`. If a is None: `bp_fallback` += 1, and hunter plays only if tier ≤ T1, otherwise `mhr`.
5. **H arm:** `hunter.choose(obs, m, params(n = gov.n()), rng_for(…,'hunter'))`.
6. If a ∈ RAISES and the path was not hunter.choose → `hunter.note_raise(obs, m)`.

**`on_hand_end`:**
- Infer the terminal fold. Run `hunter.learn_from_hand` (rng 'learn').
- Then `autopilot.on_hand_end`.
- Then `controller.on_hand_end`: it records the arm and the adjusted net, where adj = `allin_ev(result, m)` if eligible, else my_net/BB.

**`allin_ev.py`:**
- Eligible if `went_to_showdown` and pot == 2·stack (both all-in; stacks reset every hand).
- The all-in street is the street of our last decision in that hand, which is tracked in memory.
- adj = (eq·pot − stack)/BB, where eq is the exact enumeration over the remaining board cards (turn 22 runouts, flop 253) or 128 sampled boards preflop (rng 'allin'), and ties count ½.
- Unbiased: at the all-in point no further decisions exist, so the remaining board is pure chance.
- Cost ≤ 1.5 ms. It is skipped at tier ≥ T3, where raw net is used.

**`controller.py`, the arm controller.** All state is in `memory['ctl']`.

| Knob | Default | Meaning |
|---|---|---|
| warm_H | 50 | pure-hunter hands at the start of every half |
| update_every | 25 | hands between controller updates |
| prior_mu | −0.30 | prior mean of Δ = μ_B − μ_H in bb/hand (hunter favoured); empirical-Bayes calibrated by WI-14 |
| prior_mu_eq | +0.05 | prior mean when eqsig says "equilibrium-like" (only if eqsig is enabled); calibrated |
| prior_sd | 0.50 | |
| floor_B | 0.15 | exploration floor for B while in doubt |
| cap_B | 0.85 | i.e. floor_H = 0.15, so the A/B always has hunter data |
| doubt_exit_T / doubt_enter_T | 3.0 / 2.0 | hunter's in-half T_H thresholds |
| sd_floor | 3.0 bb/hand | |
| stoploss_T / from / lock / max | −3.0 / 150 / 150 / 2 | |

Update rule at hand h ≥ warm_H, every `update_every` hands:
```
m_X, v_X, n_X over adjusted nets of arm X (v floored at sd_floor²; if n_X < 30 use pooled v)
se² = v_B/n_B + v_H/n_H
if n_B < 10: post = prior
else: prec = 1/prior_sd² + 1/se²;  post_mu = (prior_mu/prior_sd² + (m_B − m_H)/se²)/prec
P = Φ(post_mu·√prec)                       # Thompson = probability matching at hand level
T_H = Σ nets_H / (sd_H·√n_H)
doubt: True at start; False once T_H ≥ 3.0 with n_H ≥ 30; True again if T_H < 2.0
p_B = clip(P, floor_B if doubt else 0, cap_B)
tier caps: T2 → p_B ≤ 0.5;  T3+ → p_B = 0 for new hands
stop-loss: h ≥ 150 and T_H < −3.0 (≤ 2 triggers/half) → p_B = max(p_B, 0.5), locked 150 hands
degenerate (D1–D3 from v2 of this spec) → p_B = 0 locked (hunter crushes these)
```

Why this resolves the "backwards default":
- Hunter plays every hand until hand 50.
- Against opponents hunter is clearly beating (T_H ≥ 3, typically reached by hand 50–150 against weak bots) there is **no** exploration, so the TB cost is ≈ 0.
- B gains share only if the in-half evidence (all-in-adjusted) or the stop-loss says hunter is worse.
- Both arms keep a 15% floor while the match is in doubt, so the A/B always has data.

**`eqsig.py`** (optional, knob K11, default **off** unless calibration passes):
- Opponent decisions are grouped into 12 classes: street × facing-bet × raise-count {0, 1, 2+}.
- Observed counts O[c][a] are compared with expected E[c][a] = Σ over the opponent's visited nodes of `nodefreq[node][a]`.
- `nodefreq` is the blueprint's conditional P(a | node). In a two-player game the opponent's range at a node depends only on the opponent's own actions and the node, so this comparison is **invariant to our arm mix**. That fixes the contamination problem.
- The statistic is the effect size φ = √(χ²/N), not a significance test.
- "EQ-like" means φ < φ0 with N ≥ 150. φ0 is calibrated so that near-equilibrium proxies (bp_S, R0x, exploiters, vendored hybrids) and W/L bots separate with AUC ≥ 0.9 at hand 300.
- It only shifts the prior mean (prior_mu → prior_mu_eq). It never sets p_B directly.

**`memory['trace']`** records (hand, p_B, P, T_H, n_H, n_B, m_H, m_B, doubt, locks, eq φ, tier, autopilot) every 25 hands.

**DEFAULTS (controller and blueprint knobs):** the table above, plus tau = 0.0, c_min = 90, bp_tag = 'ship', hunter_module = 'hunter' and hunter_n = 96.

### 3.11 Governor and time tiers (WI-06; `governor.py`)

All thresholds are fractions of `bank = config.time_bank_seconds` (≥ 0.01). The schedule uses `N = max(1, config.num_hands)`. `Gov` is constructed in `new_half` and stored in memory.

**Charged-time estimate:** `C = a·Σwall + b·s·requests`.
- Σwall is the route wall time in server mode, or the hook wall time in the lab (`on_hand_end` included).
- Defaults are a = 1.2 and b = 0.4 ms. WI-09 `calib_ovh.py` refits them so that C ≥ judge `time_seconds` on ≥ 95% of calibration halves at `--cpus=1` and `0.5` under a contended host, and C ≤ 1.25 × judge time on average.

**Allowance and ratio:** A(h) = bank·(0.075 + 0.675·(h+1)/N), which ends at 0.75·bank (6.0 s at 8 s). r = C/A(h).

| Tier | Condition | Effect |
|---|---|---|
| T0 | r < 0.8 and C < 0.60·bank | hunter n = cfg.hunter_n (96); B allowed |
| T1 | 0.8 ≤ r < 1.0 or C ≥ 0.60·bank | n = 64 |
| T2 | 1.0 ≤ r < 1.3 or C ≥ 0.66·bank | n = 32; p_B ≤ 0.5; low-conf B fallback goes to mhr |
| T3 | r ≥ 1.3 or C ≥ 0.72·bank | n = 16 (~0.3 ms); p_B = 0 for new hands; B hands in progress finish with mhr; all-in EV off |
| T4 | C ≥ 0.81·bank (6.5 s at 8 s) | zero compute: preflop = bp preflop row (lookup) if loaded, else the hunter preflop table; postflop = mhr |
| T5 | C ≥ 0.94·bank | check/fold (never expected) |

**Speed prior:**
- At startup (server only), after a warm-up loop, run ≥ 300 ms of `sdf_bench` plus Rollouts, repeat 5 times, take the median, and divide by the laptop constants to get s.
- s only chooses the **initial** n: s > 1.6 → start at n = 64. It never restricts p_B and never selects T2 or above.
- From hand 50 the tier comes only from C vs A(h).

**DET mode:** the tier is pinned to T0.

Hunter-only mode uses the same tiers, minus the B parts.

### 3.12 Startup sequence (server `__main__` only; free time; `GET /` must answer within 15 s)

1. Env vars (top of the file).
2. Imports.
3. fasteval table: load `data/eval_both.npy` if present, else build it; then the 2,000-hand eval check.
4. `brain.warm()`.
5. `cardabs.init` and self-test.
6. `blueprint.preload(['ship'], mode='ram')`, with checks.
7. One warm decision through every path.
8. Speed prior.
9. Status string.
10. `gc.collect()`, `gc.freeze()`, `gc.disable()`.
11. `uvicorn.run(…, timeout_keep_alive=120)`.

**Budget:**
- Laptop ≤ 3 s.
- `--cpus=0.5` with a cold cache ≤ 8 s (limit 15 s).
- RSS < 700 MB: bp in RAM ≈ 170 MB plus Python and numpy ≈ 250 MB.

Since `gc.disable()` runs only here, `on_hand_end` runs `gc.collect(0)` every 25 hands in server mode only.

---

## 4. Resource budgets (new; enforced from 03:30)

**Stage −1 (WI-00, 03:25–03:50):**
1. **Stray pool job** (`./solver/pool … pool_a.bin 3000000 600 12`, started 02:45 from this session's scratchpad, not in any plan): renice it to +15 now. At 03:50, kill it unless its output file exists. Run0 uses a fresh 1M × 200-sample pool instead.
2. **Human approval request**, one PushNotification:
   - (a) `docker builder prune -af` plus removal of the unrelated images (firecrawl, neo4j, rabbitmq, nbtest; ≈7.2 GB reclaimable).
   - (b) Lower the Docker Desktop VM to 4 GB, and quit Docker outside the Docker windows.
   - (c) The human's contact windows for the SHIP form edits.
   - **Nothing is deleted and no setting is changed without an explicit yes.**
   - With no answer by 05:30: Docker stays as is, the lab is capped at 3 workers and sub-agents at 5 while M runs.
3. Create `~/sooz_runs/{pools,runs,bp,logs,pids}`.
4. `.venv312` pinned to numpy 2.5.4, fastapi 0.156.1 and uvicorn 0.54.0. If no mac wheel exists for numpy 2.5.4, use the nearest version and run golden and parity tests inside the base image. `lab/env_check.py` asserts versions at every gate start.
5. `tools/watchdog.sh` (every 30 s) logs free disk, pageins/s, swap and top RSS:
   - free < 8 GB → SIGSTOP lab workers;
   - free < 5 GB → SIGSTOP trainers;
   - pageins > 400/s for 60 s → SIGSTOP lab workers, then S;
   - SIGCONT when back above threshold + 2 GB.
6. `caffeinate -dimsu`.

**Disk budget (free now 17 GiB).** Gate: ≥ 15 GB free before Stage 0 (target ≥ 25 GB with the approved prunes).

| Item | Size |
|---|---|
| Pool A 32M / Pool B 2M / Run0 pool 1M | 2.05 / 0.13 / 0.07 GB |
| buckets: S (16M deals) / M (32M) / pool-B ×2 / Run0 | 0.26 / 0.51 / 0.06 / 0.02 GB |
| M raw checkpoint 1 + .tmp (≤ 1.2 GB each, less with tree2) | ≤ 2.4 GB |
| S and R0x checkpoints | 0.4 GB |
| Exports: M avg+conf × 3 (≤ 170 MB), S × 3, R0x, cur once | 0.8 GB |
| Exploiters (S, M-final), avg | 0.3 GB |
| Docker image growth (pruned between windows) | ≤ 3 GB |
| git objects + 1 fresh-clone temp dir (deleted after) | 0.8 GB |
| **Total** | **≈ 10.8 GB** |

If < 15 GB is free at 05:45: pool A 16M (shared S/M) and skip R0x checkpoints.

**RAM budget (16 GB host; Docker VM 7.65 GB unless approved down to 4).**

| Process | RSS |
|---|---|
| M trainer (R+S ≤ 1.08 GB, V 0.14, buckets mmap 0.51, showdown) | ≤ 1.8 GB |
| S trainer (R+S 0.17, V, buckets 0.26) | 0.5 GB |
| R0x (128 buckets) | 0.2 GB |
| BR job (S / M-final) | 0.5 / 1.8 GB (M-final only after M stops) |
| pool2 (streaming) | ≤ 0.3 GB |
| Lab worker (bp mmap shared; `maxtasksperchild=50`) | 0.2–0.3 GB each |
| Claude sub-agents | ≈ 0.3 GB each; cap 7 (5 if Docker stays at 7.65 GB) |
| Docker VM (only in windows) | 4 GB (approved) |

**Docker windows** (Docker running only then, if approved): 05:30–06:15 (SHIP-1 G1/G6, `.so` build), 07:00–07:30 (`.so` M2 checks), 09:15–10:05 (SHIP-2), 11:15–11:45 (optional SHIP-3), 13:20–14:00 (final). Each window ends with `docker builder prune -f` for our own cache.

**CPU allocation (16 hyperthreads ≈ 10 effective cores).** Calibration (WI-09 constants, G1) runs only in quiet slots, with M paused (SIGSTOP) for ≤ 10 min, and the host load average is logged alongside.

| Window | M | S / Run0 / R0x / BR | Lab |
|---|---|---|---|
| 03:30–05:00 | — | Run0 pool 4 (04:00–04:20) | build/tests ≈ 8 |
| 05:00–05:45 | — | Run0 4 → BRs 3×2 | SHIP-1 gate 6 |
| 05:45–06:30 | — | pool2 10 (≈15 min), edges, bucketize | 4 |
| 06:45–08:15 | 8 | S 3, R0x 2 (to 07:45) | 3–4 |
| 08:15–12:00 | 8 | BR(S) 3 (08:15–08:45) | 6–7 |
| 12:00–12:30 | — | BR(M-final) 6 | 8 |
| 12:30–14:00 | — | — | 14 |

At D1 (08:45), if the blueprint upside looks small, M drops to 6 threads.

---

## 5. Training loop

**Run0: trainer validation** (WI-03a/03b, 04:00–06:15).
- Pool: the existing `solver/pool`, 1M deals × 200 samples on 4 threads (≈ 10–15 min).
- `lab/run0_buckets.py`: 128/128/128 quantiles plus 19,998 preflop.
- `mccfr2`: 30 virtual minutes on 4 threads, exports at 10/20/30, tree2 if ready (else tree v1, logged).
- Then three 10-min BRs in parallel (2 threads each) and evalbp.
- **Verdict:** expl(30) < expl(10) by > 2 SE (evalbp SE), **and** the BR beats uniform by more than it beats export_30.
- A non-monotone 10→20 alone is not a failure.
- **R0x:** continue Run0 from its checkpoint for +90 min on 2 threads. It is an **independent-abstraction strong proxy** (float features, different buckets) and is never shipped.

**Stage 0** (WI-10, 05:45–06:30):
1. Pools A and B (streamed).
2. Fit S and M edges.
3. Bucketize.
4. **Gate GA (a)–(e)** (§3.6).
5. 5-min M throughput on 8 threads.
6. Re-plan: if < 100k traversals/s, M becomes (32,16,2)/(32,16,2)/(128,8) = 1024.

**Run S** (hedge and proxy): 3 threads, 06:45–08:15 (90 min).
- disc-epoch 5 min until 45; prune after 20; exports at 30/60/90.
- Then BR(S) for 30 min on 3 threads → `exploiter_S` (avg), nodefreq, and vendored proxies (`proxy_bpS`).

**Run M** (main): 8 threads, 06:45–12:00 (315 virtual min).
- disc-epoch 10 min until 150; prune after 60; checkpoint every 30.
- Exports at 120 (08:45), 240 (10:45) and final at 315 (12:00, with `--export-cur`).
- Expected volume: at a measured 175k/s on 4 threads, 8 threads is ≈ 280–320k/s, so ≈ 5.3–6.0e9 traversals. tree2 shrinks the tree further.
- Main-line river infosets ≈ 1e5+ visits.

**After each M export:**
- Tier A: evalbp vs the previous export, vs S and vs R0x.
- League B-only results on 8 g-seeds.
- nodefreq.
- **Checkpoint choice** uses the exploitability trend (BR at M@4h only if RAM allows; BR at M-final) **plus** league B-only and hybrid results. Head-to-head alone never decides.
- **Strategy is always 'avg'.** 'cur' is considered only if it has lower measured expl **and** no worse league U.
- If M@4h loses to S by more than 2 SE in Tier A, that is a bug signal: stop promoting M (F4).

**Abort and kill rules:**
- M cannot start by 07:30 → halve the M dims.
- Cannot start by 08:30 → cancel M; S continues to 12:00 on 6 threads.
- Crash or thermal event → `--resume` from the checkpoint (the virtual clock makes this cheap: ≤ 30 min lost, no double discount).
- ENOSPC → the checkpoint is skipped and the watchdog frees or pauses.

---

## 6. Improvement loops

**Loop A: hunter exploitation and hardening.** This is the main source of points and TB.
1. **MEASURE:** v2.1 against the league, the hard set and the anti bots (DET, cached incumbent).
2. **SEARCH (WI-11, mandatory):**
   - ParamBot has 14 knobs: VPIP threshold, open size, 3-bet frequency, c-bet frequency by street, bluff frequency by street, check-raise frequency, fold thresholds by street × size, slowplay threshold, overbet-shove threshold.
   - Pure-numpy CMA-ES: popsize 16, 15 generations, fitness = mean μ_adj over 6 d-seeds × 300-deal duplicate matches vs the target, 4 workers. That is ≈ 7,200 CPU-s ≈ 35 min.
   - The top 5 are re-evaluated on 8 fresh d-seeds × 1000 deals. The top 3 are frozen as `anti_v21_{1,2,3}`.
3. **DIAGNOSE:** per-street and per-node-class chip-flow attribution of each anti bot vs hunter. Read the genome: which hunter model assumption does it exploit? Examples: Beta prior too sticky, `bet_range` fooled by polarised bettors, fold rates pooled over sizes.
4. **CHANGE:** one `hunter_v3` flag per diagnosed exploit, plus TB flags (size-specific fold rates, value sizing vs stations). See WI-12.
5. **VERIFY:** gates (§7), both as hunter-only and inside the hybrid (K9).
6. **RE-SEARCH:** round 2 of CMA-ES against the leading v3 or hybrid at ~11:00 → `anti_<cand>` guards.

**Decision D1 at 08:45**, with inputs from WI-11 round 1, bp_S and R0x vs v2.1, and M@2h Tier A:
- If no proxy or anti bot beats v2.1 by > 0.3 bb/deal and v2.1 beats bp_S at z > 2, the blueprint's upside is small.
  - M drops to 6 threads, lab priority goes to WI-12, and the hybrid stays eligible only through gates.
- Otherwise the hybrid gets priority, and the controller priors are calibrated from the measured μ_B − μ_H per class.

**Loop B: controller calibration** (WI-14).
- Empirical-Bayes priors: from the lab's hunter-only and blueprint-only results per opponent class, prior_mu = the class-weighted mean of (μ_B − μ_H)/2 per hand, with prior_sd = the across-opponent SD (floored at 0.3).
- prior_mu_eq is the same quantity over EQ-like proxies (only if eqsig passes calibration).
- Audits:
  - p_B traces vs drifting and learning opponents, reported separately;
  - the regret gate G5;
  - exploration TB cost vs W/L.

**Loop C: blueprint quality** (WI-10). Covered by §5's checkpoint and avg/cur rules plus Tier A and the league B-only results. No abstraction or trainer changes after M starts.

**Knob list** (screened on d-seeds with 300-deal DET matches, then gated):

| Knob | Values |
|---|---|
| K1 prior_mu | calibrated / ±0.15 |
| K2 floor_B | 0.10 / 0.15 / 0.20 |
| K3 warm_H | 30 / 50 / 80 |
| K4 doubt_exit_T | 2.5 / 3.0 / 4.0 |
| K5 stoploss_T | −2.5 / −3.0 / off |
| K6 tau | 0 / 0.10 / 1 |
| K7 c_min | 0 / 90 / 140 |
| K8 hunter_n | 64 / 96 / 128 |
| K9 hunter_module | hunter / hunter_v3 + flags |
| K10 bp tag | S / M@4h / M-final |
| K11 eqsig | off / on |
| K12 autopilot | (15,6) / (12,5) |

**Stopping rules:**
- At most 2 attempts per hypothesis.
- Structural freeze 12:00; knob freeze 12:30 (when final selection starts); code freeze 14:00; final SHA 14:30; after 14:30, reverts only.
- If no hybrid passes confirmation by 12:30, the finalists are hunter-only (v2.1 / v3).

---

## 7. Evaluation and final-selection protocol

**League (`lab/league.py`):**

| Class | Weight | Members |
|---|---|---|
| W, weak | 0.40 | random_bot, always_half, always_pot, station, checkfold, nit, lag, madehand, 6 perturbed |
| L, LLM-style | 0.25 | eqbot + 10 persona |
| A, adaptive/medium | 0.15 | hunter_v1, hunter_v2 (frozen), cb1_polar, cb2_switch, bandit_aggr, adaptive_stats |
| S, strong/hard proxies (independent of the candidate) | 0.20 | proxy_R0x, proxy_bpS (when the candidate's bp is M) or proxy_bpM@4h (when the candidate's bp is S), proxy_hybS (vendored hybrid at the SHIP-2 SHA, if shipped), anti_v21_{1..3} (together at most 1/3 of S weight) |

**Not in U:**
- **Mirror:** the bp of the candidate's own tag. Diagnostic only.
- **Guard X:** `exploiter_S`, `exploiter_M`. Used only in the regret gate G5, where the correct response is switching to hunter.
- **Holdout** (never tuned on): 6 persona-holdout, 4 guide-only bots (written from the participant guide only), the official baseline-bots, drifter.
- **anti_<cand>** (round 2).
- **Failure bots:** slowbot, errbot.

All proxies are **vendored at pinned SHAs** (`lab/vendor.py`), never live imports.

**Alternative weightings:** weak-heavy (.6/.2/.1/.1), strong-heavy (.2/.2/.2/.4), and uniform per bot.

**Gate league** (used for the screen and confirm stages of G2/G3 at ship gates): 20 representatives.
- W: station, random, nit, lag, checkfold, 1 perturbed.
- L: eqbot + 4 personas.
- A: hunter_v1, hunter_v2, cb2_switch, bandit_aggr.
- S: 5 members.

The full league plus holdout runs on the final f-seeds.

**Seed banks:** d0.. (dev, unlimited), g0..g399, c0..c399 (25 confirmations of 16), f0..f63. A ledger prevents reuse of c and f seeds.

**Control variate (lab):** equity martingale CV, exactly as in v2 of this spec (cached in `lab/cache/eq_<seed>.npy`, β cross-fit, unbiasedness test). In-half, the bot uses only all-in EV (§3.10).

**DET mode and incumbent cache:** every statistical run is DET. The incumbent's results are cached per (runtime-code hash ⊕ cfg hash, opponent hash, seed, deals). The incumbent's c-seed results are precomputed in idle lab time after every ship.

**Gates (all required for promotion):**

| Gate | Requirement |
|---|---|
| **G0 Safety** | 0 errors, 0 illegal, 0 legal-fallbacks over ≥ 200 halves of the gate runs, plus fuzz vs random_bot/always_pot/station at 300 deals: **500 halves for SHIP-2/3, 2,000 for SHIP-4**. bp_mismatch < 0.1% of B decisions. Max single decision < 50 ms. `new_half` robustness tests pass. ASan fuzz of libsdf passed (WI-01). |
| **G1 Time** | Non-DET. Laptop in-process (hook-timed, `on_hand_end` included) max C ≤ 0.44·bank. Docker HTTP `--cpus=1` judge-charged max ≤ 0.56·bank. `--cpus=0.5` **plus stress-ng --stream 2**: never timed_out and ≤ 0.85·bank. Cold-cache variant (drop_caches before each half) ≤ 0.85·bank. Config variant (bank 4.0, num_hands 2000): never timed_out. Startup ≤ 8 s at 0.5 CPU, cold, read-only rootfs + /tmp tmpfs. Memory < 1 GB. Hunter decisions at n = 96 ≥ 90% at `--cpus=1`. |
| **G2 Non-inferiority** | Intersection-union across the 4 classes (no multiplicity correction; IUT is valid at α). **Class test:** mean_j∈c Δμ_adj,j > −δ_c, one-sided α = 0.05, SE from a paired bootstrap over seeds. δ_W = δ_L = 0.10, δ_A = δ_S = 0.15 bb/deal. **Per-opponent catastrophic guard:** lower 97.5% bound of Δμ_adj,j > −1.0 bb/deal for every league, holdout and guard opponent. **W/L point guard:** Δμ_adj,j ≥ −0.3 for each W/L opponent. Uses all g+c seeds of the candidate (≥ 24). |
| **TB gate** | ΔTB (uniform over league opponents, μ_adj) point ≥ −0.05 **and** lower 90% bound ≥ −0.15 bb/deal. |
| **G3 Improvement (select-then-confirm)** | Primary metric ΔU_hard (hard set H from the incumbent cache); secondary ΔTB. Screen on g-seeds with looks at 4/8/16: early accept-to-confirm at z ≥ 2.8/2.0/1.7 on ΔU_hard, or ΔTB z ≥ same; reject if the upper 99% bound of both < 0. Best candidate confirms on 16 fresh c-seeds. **Pass** if P(ΔU_hard ≤ 0) < 0.05, **or** (ΔU_hard lower 90% > −0.01 **and** ΔTB ≥ +0.10 with lower 90% > 0). |
| **G4 Robustness** | ΔU ≥ −1 SE under all 3 alternative weightings. Holdout: mean ΔEP ≥ −0.01 and mean Δμ ≥ −0.10. Autopilot: 0 activations vs non-slowbot opponents. Hybrids: p_B traces vs drifting/learning opponents reported, and G4 also runs with p_B seeded at 0.5 at hand 50 to show there is no ratchet (p_B returns to ≤ floor vs W bots by hand 300 in ≥ 90% of halves). |
| **G5 Controller regret** (hybrids only) | For each opponent in H ∪ X: μ_hyb ≥ max(μ_H-only, μ_B-only) − (0.35·\|μ_H-only − μ_B-only\| + 0.15) on point estimates (8 seeds). At most 1 failure, and only if within 2 SE. The H-only values are the cached incumbent (v2.1/v3); the B-only values come from the blueprint-only bot of the candidate's tag. |
| **G6 Build** | `tools/worktree_build.sh` (clean `git worktree` at the SHA → `check_build`) and `tools/fresh_clone_build.sh` pass. `status_check.py`: `GET /` agent_name equals the expected mode (fails if a hybrid candidate reports fallback). `glibc_check.sh` passes for `lib/linux_x86_64/libsdf.so`. |

**Power check (`lab/power.py`, run by 07:00 on measured SDs):**
- Per-deal paired Δ SD between different policies ≈ 7–10 bb after CV, so the per-opponent SE at 24 seeds × 1000 deals ≈ 0.045–0.065.
- Class means over 5–14 opponents give SE ≈ 0.02–0.03.
- An equal-strength candidate passes each class test with power ≥ 0.97, and all four with ≥ 0.9.
- If the measured SDs are higher, power.py raises the seed count (cost printed) **before** any gate runs. The gate refuses to run underpowered.
- The v2.1-vs-itself dry run must pass G2 in ≥ 90% of simulated runs and must not promote on G3.

**Compute per ship gate** (DET, cached incumbent; 1000-deal match ≈ 15 CPU-s, 300-deal ≈ 5 CPU-s):

| Part | CPU-s |
|---|---|
| G0 fuzz, 500 halves × 300 deals | 1,250 (2,000 halves: 5,000) |
| Screen: 20 gate opponents × 8 g-seeds | 2,400 |
| Confirm: 20 × 16 c-seeds (candidate only; incumbent precomputed) | 4,800 |
| Holdout + guards: 12 × 8 | 1,440 |
| G5 B-only bot: 10 × 8 | 1,200 |
| **Total** | **≈ 11,100 ≈ 41 min on 4.5 effective lab cores** |

Docker G1/G6 adds ≈ 30 min in parallel, inside the Docker window. That fits the 75-minute SHIP-2 window.

**Tiers:**
- Tier A: evalbp, for blueprint-internal choices.
- Tier B: the lab league.
- Tier C: the real HTTP judge in tournament mode (half 1, restart, half 2) inside the built image; 3 matches at `--cpus=1` and `0.5` + stress-ng, cold cache.
- Parity: sim vs HTTP nets are identical on 3 seeds **in DET mode**.

**Final selection (12:30–13:20, 14 threads after BR(M-final) finishes at 12:30):**
- At most 3 finalists, e.g. best hunter-only (v2.1 or v3), hybrid-best (M-final or M@4h, chosen by §5), and the runner-up.
- Each plays every league and holdout opponent on 16 f-seeds: 3 × 32 × 16 = 1,536 matches ≈ 23,000 CPU-s ≈ 40 min on 10 effective cores.
- Guard X and G5 runs go in parallel.
- Pick the highest posterior-mean U among the finalists that pass G0–G6 and the TB gate.
- If the top two are within 1 SE of ΔU: prefer the higher TB, then the higher worst-case ẑ over S, then the lower think p99. The incumbent wins exact ties.

---

## 8. Runtime time-bank math

**Rules:**
- `bank` per half, by default 8.0 s.
- Each request is charged max(0, wall − 1 ms). `on_hand_end` runs inside `/act` and is charged.
- 1 s cap per request; startup is free.
- About 3,300 of our requests per half: ≈ 1,300 preflop and ≈ 2,000 postflop.

**Laptop per-request costs:**

| Item | Cost |
|---|---|
| Plumbing | ≈ 0.3 ms |
| Preflop (class 3 µs, walk 15 µs, row 20 µs) | < 0.1 ms |
| Per-decision Generator | ≈ 15 µs |
| Flop / turn / river features (B arm, first decision of the street) | 1.3 / 1.8 / 1.1 ms |
| Hunter n = 96 / 64 / 32 / 16 | 1.5 / 1.0 / 0.6 / 0.3 ms |
| mhr | 0.03 ms |
| Showdown learning | ≈ 1 ms |
| All-in EV (≈ 150 all-in hands per half) | ≤ 1.5 ms |
| Controller update every 25 hands, eqsig per opponent decision | negligible |

**Charged per half, laptop:**
- Hunter-only (expected mode against most opponents): ≈ 3–4 s, as measured for v2 over HTTP, plus ≈ 0.2 s for all-in EV and RNG.
- p_B = 1 (only against opponents where B is winning): ≈ 1.3 s.
- Mixed: in between.

**2× slower VM:**
- Hunter-only ≈ 7–8 s without the governor.
- With it, A(h) holds C ≤ 0.75·bank, stepping n 96 → 64 → 32 → 16 and then mhr.
- The reserve is ≥ 0.19·bank before T4 and 0.06·bank before T5.
- T3, T4 and mhr keep the remaining cost at ≈ 0.03 ms per decision. This is real play, not check/fold.

**Margins:**
- G1 requires ≤ 0.44·bank on the laptop.
- Stress-ng and `--cpus=0.5` emulate a contended VM.
- C is calibrated to over-estimate the judge (§3.11).
- The 1 s request cap is more than 20× our maximum decision.

**Startup and memory:**
- bp RAM preload: 170 MB in ≈ 0.2 s warm, or 1–2 s cold at 0.5 CPU. Total startup ≤ 8 s at 0.5 CPU.
- Memory ≈ 450–650 MB RSS.

---

## 9. Timeline (CST), DAG and float

| Time | Work |
|---|---|
| 03:25–03:50 | Lead: freeze this spec. WI-00 Stage −1 (stray job renice/kill decision, approval request to the human, venv312, watchdog, caffeinate). Spawn wave 1 (≤ 7 sub-agents): WI-06, WI-01, WI-03a, WI-15, WI-07, WI-03b, WI-09. |
| 04:00 | Run0 pool (4 threads). WI-08 and WI-02 (against a stub sdf.hpp) start as sub-agent slots free. |
| 04:15 | WI-15 tree2 done → WI-04 starts. |
| 05:00 | mccfr2 ready → Run0 05:00–05:35, BRs 05:35–05:50, verdict by 06:15 (float 30 min to the M start). |
| 05:15 | WI-01 M1 (stage-0-critical) done → WI-02 finalisation 05:15–05:45. |
| 05:30 | WI-06 v2.1 and WI-07 ready → **SHIP-1 gate** 05:30–06:30 (Docker window 05:30–06:15). WI-13 and WI-11 start. |
| 05:45–06:30 | **Stage 0** (pool2, edges, bucketize, GA, throughput). |
| 06:30 | **SHIP-1** push → human notified with SHA and rollback SHA. |
| 06:45 | Start M (8 threads) and S (3 threads); R0x (2 threads, to 07:45). WI-05 M1 (minimal policy) 06:30–07:15. |
| 07:00–08:30 | WI-11 round 1 vs v2.1 (4 workers). WI-01 M2 (static `.so`, fuzz, glibc) in the 07:00 Docker window. WI-05 M2 controller 07:15–09:00. |
| 07:15 | S30 → integration smoke (minimal policy, p_B = 1 and 0.5): fuzz, timing, field smoke. |
| 08:15 | S final → BR(S) 30 min, nodefreq, vendored `proxy_bpS`, make_ref. |
| 08:45 | M@2h export → Tier A. **D1 decision** (§6). |
| 07:30–12:00 | WI-12 hunter v3 flags (Loop A), gating continuously. |
| 09:00–10:15 | Calibrate controller priors (WI-14) → gate {hybrid-S, v3-early} vs v2.1 → **SHIP-2 ~10:15**. |
| 10:45 | M@4h export → Tier A, league B-only, nodefreq. |
| 11:00 | WI-11 round 2 vs the leading candidate. |
| 11:00–11:45 | Gate hybrid-M4 (or v3) → optional **SHIP-3 ~12:00**. |
| 12:00 | **Structural freeze.** M final (avg + cur) → Tier A; BR(M-final) on 6 threads 12:00–12:30. |
| 12:30 | **Knob freeze.** Final selection 12:30–13:20 (14 threads). |
| 13:20–14:00 | Tier C (Docker window), worktree build, fresh-clone build, status/glibc checks. **Code freeze 14:00.** |
| 14:30 | **SHIP-4** final SHA → human submits. |
| 14:30–16:00 | Buffer: watch the build and smoke; revert to the last green SHA only. |

**Critical paths and float:**
- **Blueprint path:** WI-01 M1 (03:30–05:15) → WI-02 (→05:45) → Stage 0 (→06:30) → M start 06:45. Float is 45 min to the 07:30 halve-dims rule and 1 h 45 min to the 08:30 cancel rule.
- **Trainer validation:** WI-03a (→05:00) → Run0 (→05:50) → WI-03b verdict (→06:15). Float is 30 min to the M start. If late, M starts anyway and Run0's verdict can stop it by 07:15 (≤ 30 min lost).
- **SHIP-1:** WI-06 (→05:30) → gate (→06:30). Float is unlimited; v2 stays live.
- **Final:** M final 12:00 → final selection 12:30–13:20 → Tier C 13:20–14:00. Float is 30 min to SHIP-4. If M-final is late, M@4h is the hybrid finalist.

---

## 10. Fallback rules

| ID | Situation | Action |
|---|---|---|
| F1 | Golden or glibc mismatch | Fix flags by 07:30 (`-ffp-contract=off`, generic arch, static libgcc/libstdc++). A runtime self-test failure means hunter, never a wrong blueprint. A numpy-reference-only mismatch is non-blocking. |
| F2 | Throughput < 100k/s | M dims become 1024/1024/1024. |
| F3 | Run0 verdict fails (expl(30) not < expl(10) by 2 SE) or evalbp asymmetry | Fix before M; if M is already running, stop it. If not fixed by 07:30, the blueprint track is abandoned and all effort goes to WI-12 and WI-11. |
| F4 | M@4h loses to S in Tier A by > 2 SE, or fails G2 | Use the S-based hybrid if gated. M becomes a lab proxy only. |
| F5 | Any shipped build errors, times out or regresses in Tier C or smoke | Revert to the last green SHA immediately (one push plus a form edit; the rollback SHA is in every notification). |
| F6 | No hybrid passes confirmation by 12:30 | Finalists are hunter-only (v3 if it passed, else v2.1). |
| F7 | Runtime: `.so` load or self-test fails, config mismatch, missing bp | Hunter for the half (status `-fallback`). A per-decision mismatch sends that hand to hunter. An exception goes to the legal fallback. A `new_half` exception triggers minimal init. |
| F8 | Time | Governor tiers T0→T5 (§3.11). |
| F9 | Repo or GitHub | Any file > 95 MB → re-chunk to ≤ 45 MB. Never commit anything but `data/bp/ship/`. |
| F10 | Disk < 8 GB / < 5 GB | Watchdog pauses lab / trainers. The operator frees our own artifacts (old exports, Run0 pool), then resumes. |
| F11 | Swap thrash (pageins > 400/s) | Pause lab, then S. Lab worker cap −2. |
| F12 | Human unreachable at a ship time | The previous green SHA stays live. Retry the notification at the next contact window. |

---

## 11. Interfaces summary (frozen at 03:45)

- **C API:** `sdf_version`, `sdf_init`, `sdf_flop`, `sdf_turn`, `sdf_river`, `sdf_best`, `sdf_bench` (§3.3). Negative return = error.
- **`sdf_ref.py`:** `flop/turn(hole, board) -> (E, NOW, NUT, nvalid)` and `river -> (HS, BLK, nvalid, ntop)`. The order (E, NOW, NUT) is used everywhere.
- **tree2:** `data/tree2.bin` (trainer format) and `data/tree2.npz` (tree, dindex, alias).
- **Pool record:** 64 bytes. Trainer inputs: `buckets.bin` uint16[n][2][4] and `showdown.bin` int8[n].
- **`mccfr2` flags and checkpoint header** (§3.7). Export dir = blueprint package (§3.8). evalbp prints key=value; `--self --nodefreq`.
- **`blueprint.preload(tags, mode)`, `blueprint.get(tag)`, `BP.act`; `cardabs.ok`, `cardabs.features(street, hole, board)`.**
- **`policy`:** `available` / `new_half` / `decide` / `on_hand_end`; `release_cfg.OVERRIDES`; `memory['__overrides__']`.
- **`controller`:** `observe`, `p_B(mem)`, `on_hand_end(arm, adj_net, mem)`, `trace`. `allin_ev(result, mem) -> float | None`. `eqsig.observe`, `eqsig.phi`.
- **`hunter`:** `update_model`, `choose(obs, mem, params, rng)`, `note_raise`, `learn_from_hand(result, mem, rng)`, `mhr`.
- **`governor`:** `Gov(config, det, speed)`, `.charge(wall, requests)`, `.reconcile(route_wall)`, `.tier(hand)`, `.n()`, `.C`.
- **`autopilot`:** `observe`, `on_hand_end`, `active`, `action`.
- **Lab jsonl, one per match:** `{cand, opp, seed, deals, det, mu_raw, mu_adj, sd_raw, sd_adj, se, z, ep, think_max, think_p99, errors_a, errors_b, bp_mismatch, bp_fallback, p_B_mean, p_B_late, arm_share_H, autopilot_hands, tier_max, git_sha, code_hash, cfg_hash, ts}`.
- **Variant wrapper:** sets `memory['__overrides__']` and delegates to `agent` hooks.
- **Runtime data never uses `.json`** (excluded by `.dockerignore`).

---

## 12. Risks (top)

| Risk | Mitigation |
|---|---|
| Blueprint arm costs points or TB against medium/weak bots | Hunter default; warm_H; doubt gate; TB gate; G5 regret. |
| Nothing measures the strong field | Independent proxies (R0x, bp_S/M, vendored hybrids); mandatory exploit search; D1. |
| Train/serve bucket mismatch | Integer SDF; GA (a)–(e), including pre_class and the end-to-end bucket path; startup self-test. |
| Native crash or ABI | Validated C API, ASan fuzz, static libstdc++/libgcc, glibc check, pristine-image load, status in `GET /`. |
| Forfeit via `new_half` | Double try/except, no I/O, robustness tests. |
| Time bank (slow VM, changed config) | Fraction-based governor, calibrated C, cheap tiers, mhr, stress-ng and cold-cache G1, config-variant test. |
| Disk / RAM exhaustion | Budgets, streaming pool2, 1-checkpoint policy, checked writes, watchdog, Docker windows. |
| Lab ≠ runtime | Memory-only state, DET mode, hook timing incl. `on_hand_end`, vendored proxies, isolation test, pinned venv. |
| Overfitting our league | Guide-only and baseline holdout, learners, disjoint seeds, select-then-confirm, alt weightings. |
| Schedule slip | DAG with float, Run0 in parallel, hedge S, early SHIP-1, F-rules with times. |
| Human form step | Contact windows, notifications carrying the rollback SHA, F12. |

---

## 13. Expected-points argument

Illustrative 40-team field: 24 weak, 11 medium, 5 strong.

**Hunter v2:** ≈ 24 + 11·0.75 + 5·0.3 ≈ 33.8.

**This design:**
- **Weak:** unchanged points (24). TB is preserved because there is no exploration once T_H ≥ 3, and autopilot adds a little.
- **Medium:** hunter v3 hardening and TB flags, plus the stop-loss hedge, give ≈ 0.78–0.8 → +0.4.
- **Strong:** if the measured B > H against strong proxies, the controller captures roughly half the gap in-half, giving EP ≈ 0.4–0.5 instead of 0.3 → +0.5 to +1.0. If B ≤ H, the controller stays on hunter (regret-gated), so the downside is ≈ 0.
- **Total** ≈ 34.7–35.2, with TB at least as high as v2.

**Downside bounds:**
- Nothing replaces the incumbent without passing confirmation on fresh seeds, the TB gate and the regret gate.
- Every runtime failure degrades to hunter v2.1.
- `new_half` can no longer forfeit.

---

## 14. Changes from review

**Critical:**
1. **Default policy was backwards.** Hunter is now the default, with 50 pure-hunter hands per half. B gains share only through a Thompson posterior on μ_B − μ_H with a hunter-favouring empirical-Bayes prior, or through the stop-loss. While in doubt, both arms keep 15% floors, so the A/B always has data. The signal is all-in-EV-adjusted per-hand net, which is unbiased and computable in-half (§3.10).
2. **S-class and gates were self-referential.**
   - The S class now holds independent proxies: R0x (different abstraction and run), the bp of the other abstraction, a vendored hybrid, and anti-hunter ParamBots.
   - Exploiters of our own blueprint are guard class X only, judged by the regret gate G5, where switching to hunter is correct.
   - The ε false-positive gate was removed.
   - WI-11 is mandatory and aimed at v2.1 first. D1 (08:45) reallocates effort if nothing beats hunter.
3. **Disk 98% full.**
   - Stage −1 sets a disk budget (≈ 10.8 GB) with a 15 GB gate (target 25 GB), and asks for human approval before any prune of unrelated images.
   - mccfr2 keeps 1 checkpoint + .tmp with no `latest`, checks every write, aborts the checkpoint rather than the run, and validates sizes and header on resume.
   - pool2 streams with checked writes. Exports are avg+conf (cur only at final).
   - The watchdog pauses at 8 / 5 GB.
4. **No RAM headroom.**
   - A RAM budget table.
   - Docker VM 4 GB and Docker windows, with approval.
   - pool2 streaming (≤ 300 MB). S uses a 16M-deal bucket file. Bucket files are mmapped.
   - Lab bp is mmap-shared, workers recycle, the lab is capped at 3–4 workers while S and M run, and sub-agents are capped at 7 (5).
   - pageins kill rule. BR(M) runs only after M stops.
5. **G2/G5 were unpassable.**
   - G2 is now a class-pooled intersection-union test with no Holm, plus a per-opponent catastrophic guard (−1.0) and a W/L point guard.
   - Seeds come from measured SDs (`power.py`, ≥ 90% power for an equal candidate). The c-bank grows to 400.
   - G5 is relative: hybrid vs max(H-only, B-only) on the hard set and X.
6. **`new_half` forfeit.** A double try/except with minimal hunter init and a 'dead' mode. `new_half` does no I/O. Robustness tests cover corrupted ref, missing release_cfg, num_hands 0, bank 0 and unknown tags.

**Major:**
- **Hunter fold bias on B hands.** `hunter.note_raise` runs after every raise from any path. Terminal folds are inferred in `on_hand_end`. A test checks fold_rate → 1 against a 100% folder on a p_B = 1 half.
- **Holm and flat U.** IUT with no Holm. G3 uses ΔU_hard plus ΔTB.
- **Meta-stat contamination and ratchet** (both reports). Band flags are removed from control. The only style signal left (eqsig) compares the opponent's per-node conditional frequencies with the blueprint's `nodefreq`, which is invariant to our arm mix. It uses an effect size rather than repeated significance tests, and only shifts the prior. G4 also runs with p_B seeded at 0.5 to prove there is no ratchet.
- **TB against weak bots.** TB is a first-class gate (ΔTB ≥ −0.05, lower 90% ≥ −0.15). W/L class δ is 0.10, with a per-opponent point guard of −0.3. Every half starts with 50 hunter hands and there is no exploration once T_H ≥ 3.
- **Lab compute infeasible.** A CPU-second budget per gate is published (≈ 11k CPU-s ≈ 41 min). Incumbent caching (DET) and c-seed precompute. 300-deal screening and a 20-bot gate league. Final selection starts at 12:30 with M-final or M@4h. WI-11 is resourced explicitly (≈ 7,200 CPU-s) rather than "spare workers".
- **Resume clock.** Virtual minutes plus discount, prune and export state are persisted in the checkpoint. The kill -9/resume equivalence test is in WI-03a acceptance.
- **Lab ≠ runtime / module sharing** (two reports). §3.0 rules: memory-only state, overrides via memory, server-only startup/gc/benchmark, hook-level think accounting including `on_hand_end`, vendored proxies, worker recycling, and an isolation test.
- **Wall-clock dependence and determinism** (two reports). Per-decision RNG from (hand, k, purpose). DET mode for every statistical run and for parity. Governor tested with injected time. Calibration in quiet slots with M paused and load logged. The stray pool job is handled in Stage −1.
- **mmap cold-cache I/O** (major and minor). Server mode reads bp fully into RAM at startup. G1 adds a cold-cache variant.
- **Repo bloat.** Exports live in `~/sooz_runs`. Only `data/bp/ship/` is tracked, and WI-06 owns the .gitignore/.dockerignore allow-lists. G6 builds from a clean worktree. At most 3 bp versions in history.
- **Critical path.** A DAG with float (§9). Run0 uses a fresh 1M × 200 pool. The criterion is expl(30) < expl(10) by > 2 SE. WI-03b's `playout_ref` replaces the WI-04 dependency. WI-01 is split into M1 (stage-critical) and M2 (ship-critical). S30 integration uses the minimal policy (WI-05 M1).
- **Folds invisible.** Terminal-fold inference feeds autopilot, hunter Stats and the controller. The AUTOPILOT trigger is revised.
- **No cheap governor tier.** T3 uses n = 16, T4 uses mhr (~30 µs). The B arm is off for new hands at T3+. A low-conf fallback pays for hunter only at ≤ T1. G1 adds stress-ng.
- **Absolute time constants.** All thresholds are fractions of `config.time_bank_seconds`, with the schedule on `config.num_hands`. hunter.py has no `_n_samples`. Test with bank 4.0 and num_hands 2000.
- **Preflop class mapping unchecked.** pool2 reads `pre_class.u16`. GA (b) checks pre_class and GA (d) checks the end-to-end runtime bucket path against `buckets.bin`.
- **Native library.** Validated inputs, pointer/length re-check, ASan/UBSan fuzz on 11M calls, static libstdc++/libgcc, glibc check, pristine-image load, status in `GET /`, and status-asserting smoke in G6.
- **Startup benchmark noise** (major and minor). ≥ 300 ms, median of 5 after warm-up. It sets only the initial n and never restricts p_B. Tiers come from C after hand 50. Tested with an artificially slowed benchmark.

**Minor:**
- **avg vs cur:** always avg; checkpoints chosen by expl trend plus league; BR exports its average after a 30-min run.
- **Holdout authorship:** guide-only bots, the official baseline-bots and learners are added; drifting-opponent traces are reported separately.
- **Double throttling:** the governor is the single owner of n; G1 requires n = 96 on ≥ 90% of decisions.
- **Human windows:** asked at 03:30; notifications carry the rollback SHA; F12.
- **Interpreter:** `.venv312` pinned, and env_check runs at every gate.
- **OVH:** C is calibrated to over-estimate the judge; T4 moves to 0.81·bank; `on_hand_end` is timed in the lab.
- **Tree:** child ≥ 0 is asserted; tree2 merges raise aliases.
- **AUTOPILOT false positives:** 15/6/zero-calls/hand ≥ 100, measured against all S, A, guard and holdout bots.
- **Keep-alive:** `timeout_keep_alive=120`.
- **Eval table:** 2,000-hand startup check with rebuild.
