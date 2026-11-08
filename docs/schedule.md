All times are CST, Nov 8. Now is 03:25. The final SHA is due at 14:30 and the deadline is about 16:00.

03:25-03:50 Lead
- Freeze the v3 spec.
- WI-00 Stage -1: renice the stray pool job now and decide kill/keep at 03:50; send the human the approvals and contact-window request; build .venv312; start the watchdog and caffeinate.
- Spawn wave 1 (≤ 7 sub-agents): WI-06, WI-01, WI-03a, WI-15, WI-07, WI-03b, WI-09.

04:00
- Run0 pool: existing solver/pool, 1M x 200 samples, 4 threads.
- Start WI-08 (persona batches of 3) and WI-02 (against a stub sdf.hpp) as sub-agent slots free up.

04:15
- WI-15 tree2 done; WI-04 starts.

05:00
- mccfr2 ready (WI-03a).
- Run0 trains 05:00-05:35; BRs 05:35-05:50.
- WI-03b Run0 verdict by 06:15; float 30 min to the M start.

05:15
- WI-01 M1 done; WI-02 finalises 05:15-05:45.

05:30
- WI-06 v2.1 and WI-07 ready.
- SHIP-1 gate 05:30-06:30; Docker window 05:30-06:15.
- WI-13 and WI-11 (ParamBot build) start.

05:45-06:30
- Stage 0 (WI-10): pool2 32M on 10 threads, edges, bucketize, gate GA, throughput re-plan.

06:30
- SHIP-1 (v2.1) pushed; human notified with the SHA and rollback SHA.
- WI-05 M1 (minimal policy) 06:30-07:15.

06:45
- M starts (8 threads, to 12:00, virtual minute 315).
- S starts (3 threads, 90 min).
- R0x runs on 2 threads to 07:45.

07:00-08:30
- WI-11 round 1 CMA-ES vs v2.1 on 4 workers.
- WI-01 M2 (static .so, ASan fuzz, glibc check) in the 07:00-07:30 Docker window.
- WI-05 M2 controller 07:15-09:00.
- WI-13 power check by 07:00.

07:15
- S30 export; integration smoke with the minimal policy.

07:30-12:00
- WI-12 hunter v3 flags (improvement Loop A), gated continuously.

08:15
- S final; BR(S) 30 min on 3 threads; nodefreq; vendored proxy_bpS.

08:45
- M@2h export; Tier A.
- D1 decision on resource priority: blueprint vs hunter v3.

09:00-10:15
- WI-14 calibrates the controller priors.
- Gate {hybrid-S, v3-early} vs v2.1; Docker window 09:15-10:05.
- SHIP-2 about 10:15.

10:45
- M@4h export; Tier A; league B-only; nodefreq.

11:00
- WI-11 round 2 vs the leading candidate.

11:00-11:45
- Gate hybrid-M4 or v3.
- Optional SHIP-3 about 12:00; Docker window 11:15-11:45.

12:00 Structural freeze
- M final (avg + cur); Tier A.
- BR(M-final) 12:00-12:30 on 6 threads.

12:30 Knob freeze
- Final selection 12:30-13:20 on 14 threads: ≤ 3 finalists x full league + holdout x 16 f-seeds (about 23k CPU-s), plus guard X and G5.

13:20-14:00
- Tier C in the Docker window (tournament mode, cpus 1 and 0.5, stress-ng, cold cache).
- Worktree build, fresh-clone build, status and glibc checks.

14:00 Code freeze.

14:30
- SHIP-4: final SHA to the human.

14:30-16:00
- Buffer: watch the build and smoke; revert to the last green SHA only.

Critical path and float
- Blueprint path: WI-01 M1 (→05:15) → WI-02 (→05:45) → Stage 0 (→06:30) → M start 06:45. Float is 45 min to the 07:30 halve-dims rule and 1 h 45 min to the 08:30 cancel rule.
- Trainer validation: WI-03a (→05:00) → Run0 (→05:50) → verdict (→06:15). Float is 30 min to the M start. If late, M starts anyway and can be stopped by 07:15.
- SHIP-1: unlimited float, because v2 stays live.
- Final: M final 12:00 → selection 12:30-13:20 → Tier C 13:20-14:00. Float is 30 min to 14:30. If M-final is late, M@4h is the hybrid finalist.
- If no hybrid has passed confirmation by 12:30, the finalists are hunter-only (F6).