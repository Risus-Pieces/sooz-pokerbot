# Blueprint evaluation

bp_bot = lab/field/bp_bot.py playing the MCCFR blueprint (lab/export_bp.py checkpoint). Duplicate matches via lab/sim.py; bb/deal from bp_bot's side.

### ckpt 30 min (0.88e9 it)  (minp=0, 2 seeds x 1000 deals, 04:17, 66s)

| opponent | bb/deal | 95% CI | per-seed means | points | errors | max think s/half |
|---|---|---|---|---|---|---|
| always_half | +2.775 | [+1.625, +3.925] | +3.345 +2.204 | 2.0/2 | 0 | 2.70 |
| always_pot | +2.446 | [+1.255, +3.638] | +2.349 +2.543 | 2.0/2 | 0 | 1.62 |
| checkfold | +1.208 | [+1.182, +1.235] | +1.218 +1.200 | 2.0/2 | 0 | 0.62 |
| eqbot | +0.943 | [+0.505, +1.380] | +1.052 +0.833 | 2.0/2 | 0 | 4.40 |
| hunter_v1 | +0.681 | [-0.235, +1.597] | +0.861 +0.502 | 1.0/2 | 0 | 2.67 |
| hunter_v2 | +0.264 | [-0.594, +1.123] | -0.544 +1.073 | 1.0/2 | 0 | 2.97 |
| lag | +2.141 | [+1.253, +3.030] | +2.188 +2.095 | 2.0/2 | 0 | 4.39 |
| madehand | +2.417 | [+1.574, +3.260] | +2.505 +2.329 | 2.0/2 | 0 | 4.80 |
| nit | +0.668 | [+0.433, +0.904] | +0.825 +0.511 | 2.0/2 | 0 | 1.71 |
| random_bot | +3.821 | [+2.965, +4.677] | +3.467 +4.176 | 2.0/2 | 0 | 2.68 |
| station | +2.163 | [+1.699, +2.627] | +2.357 +1.969 | 2.0/2 | 0 | 5.69 |
| timeout_bot | +1.244 | [+0.993, +1.495] | +1.256 +1.232 | 2.0/2 | 0 | 1.97 |

points 22.0/24


### ckpt 30 min, purified  (minp=0.05, 2 seeds x 1000 deals, 04:27, 70s)

| opponent | bb/deal | 95% CI | per-seed means | points | errors | max think s/half |
|---|---|---|---|---|---|---|
| always_half | +4.099 | [+2.961, +5.238] | +4.388 +3.811 | 2.0/2 | 0 | 2.98 |
| always_pot | +2.238 | [+1.036, +3.439] | +2.007 +2.468 | 2.0/2 | 0 | 1.66 |
| checkfold | +1.207 | [+1.180, +1.234] | +1.222 +1.192 | 2.0/2 | 0 | 0.65 |
| eqbot | +0.714 | [+0.254, +1.175] | +0.766 +0.662 | 2.0/2 | 0 | 5.01 |
| hunter_v1 | +0.521 | [-0.387, +1.428] | +0.297 +0.745 | 1.0/2 | 0 | 2.83 |
| hunter_v2 | +1.054 | [+0.182, +1.926] | +1.323 +0.784 | 1.5/2 | 0 | 3.36 |
| lag | +1.758 | [+0.887, +2.630] | +2.151 +1.365 | 2.0/2 | 0 | 4.55 |
| madehand | +2.143 | [+1.293, +2.993] | +2.159 +2.127 | 2.0/2 | 0 | 4.85 |
| nit | +0.606 | [+0.368, +0.844] | +0.561 +0.650 | 2.0/2 | 0 | 1.76 |
| random_bot | +3.099 | [+2.287, +3.912] | +2.686 +3.513 | 2.0/2 | 0 | 2.62 |
| station | +2.113 | [+1.654, +2.571] | +2.152 +2.073 | 2.0/2 | 0 | 6.40 |
| timeout_bot | +1.150 | [+0.910, +1.390] | +1.262 +1.038 | 2.0/2 | 0 | 2.16 |

points 22.5/24


### ckpt 60 min (1.74e9 it)  (minp=0, 2 seeds x 1000 deals, 04:47, 66s)

| opponent | bb/deal | 95% CI | per-seed means | points | errors | max think s/half |
|---|---|---|---|---|---|---|
| always_half | +4.178 | [+3.043, +5.312] | +4.301 +4.054 | 2.0/2 | 0 | 3.15 |
| always_pot | +2.881 | [+1.697, +4.066] | +3.638 +2.126 | 2.0/2 | 0 | 1.82 |
| checkfold | +1.212 | [+1.185, +1.239] | +1.216 +1.208 | 2.0/2 | 0 | 0.78 |
| eqbot | +0.936 | [+0.465, +1.407] | +0.899 +0.972 | 2.0/2 | 0 | 4.75 |
| hunter_v1 | +1.290 | [+0.382, +2.198] | +1.385 +1.194 | 1.5/2 | 0 | 2.94 |
| hunter_v2 | +0.393 | [-0.484, +1.270] | +0.621 +0.166 | 1.0/2 | 0 | 2.98 |
| lag | +2.582 | [+1.687, +3.477] | +2.548 +2.616 | 2.0/2 | 0 | 4.22 |
| madehand | +2.368 | [+1.532, +3.204] | +2.224 +2.512 | 2.0/2 | 0 | 4.43 |
| nit | +0.595 | [+0.346, +0.844] | +0.572 +0.619 | 2.0/2 | 0 | 1.65 |
| random_bot | +3.563 | [+2.718, +4.408] | +3.483 +3.643 | 2.0/2 | 0 | 2.41 |
| station | +2.179 | [+1.712, +2.645] | +2.124 +2.233 | 2.0/2 | 0 | 5.58 |
| timeout_bot | +1.224 | [+0.953, +1.494] | +1.230 +1.217 | 2.0/2 | 0 | 1.90 |

points 22.5/24


### Checkpoint vs checkpoint (bp_bot BP_PATH=A vs lab/field/_bp_bot_b.py BP_PATH_B=B, 4 seeds x 1000 deals)

| A vs B | per-seed bb/deal | mean |
|---|---|---|
| m060 vs m030 | -0.034 +0.024 -0.452 -0.362 | -0.206 (n.s., each seed CI ~ +-0.73) |

### ckpt 90 min (2.82e9 it)  (minp=0, 2 seeds x 1000 deals, 05:17, 74s)

| opponent | bb/deal | 95% CI | per-seed means | points | errors | max think s/half |
|---|---|---|---|---|---|---|
| always_half | +3.348 | [+2.204, +4.491] | +3.396 +3.300 | 2.0/2 | 0 | 3.08 |
| always_pot | +2.446 | [+1.284, +3.609] | +2.018 +2.875 | 2.0/2 | 0 | 1.92 |
| checkfold | +1.212 | [+1.185, +1.239] | +1.225 +1.198 | 2.0/2 | 0 | 0.72 |
| eqbot | +0.709 | [+0.251, +1.167] | +0.749 +0.669 | 1.5/2 | 0 | 5.93 |
| hunter_v1 | +1.241 | [+0.351, +2.131] | +1.742 +0.740 | 1.5/2 | 0 | 2.89 |
| hunter_v2 | +0.513 | [-0.372, +1.399] | +1.038 -0.012 | 1.0/2 | 0 | 3.50 |
| lag | +2.340 | [+1.465, +3.214] | +2.596 +2.083 | 2.0/2 | 0 | 4.85 |
| madehand | +1.714 | [+0.871, +2.557] | +1.869 +1.560 | 2.0/2 | 0 | 5.10 |
| nit | +0.500 | [+0.265, +0.736] | +0.419 +0.582 | 2.0/2 | 0 | 2.06 |
| random_bot | +2.775 | [+1.935, +3.614] | +1.965 +3.584 | 2.0/2 | 0 | 2.74 |
| station | +2.318 | [+1.869, +2.767] | +2.204 +2.433 | 2.0/2 | 0 | 6.70 |
| timeout_bot | +1.086 | [+0.821, +1.351] | +1.157 +1.016 | 2.0/2 | 0 | 2.32 |

points 22.0/24

| m090 vs m030 | +0.154 -0.315 +0.172 +0.450 | +0.115 (n.s.) |

Notes:
- Purification (BP_MINP=0.05) on m030: no measurable effect (22.5/24 vs 22.0/24 points; hunter_v2 +1.05 vs +0.26, both within noise). Default stays minp=0.
- "max think s/half" is bp_bot's thinking per 1000 hands on this Mac while it was heavily oversubscribed
  (load average 18-33 on 16 cores: solver 8 threads + other agents' sims + 4 eval workers). It is highest
  vs station/eqbot (many hands reach the turn/river).
- New checkpoints are exported and evaluated automatically by lab/bp_watch.py (sections below are appended as they land).
