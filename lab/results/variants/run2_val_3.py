"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.56254, 0.21842, 0.40284, 0.95611, 0.34554, 0.84777, 0.9874, 0.01047, 0.48023, 0.03356, 0.82445, 0.13707, 0.96395, 0.19831, 0.07325, 0.56713, 0.79349, 0.04501, 0.00242, 6e-05, 0.62718, 0.63435, 0.02018, 0.21928, 0.51596, 0.15892, 0.22338, 0.1193, 0.53395, 0.01574, 0.39603, 0.63538, 0.62013, 0.07805, 0.08064, 0.44966, 0.00797, 0.47514, 0.95334, 0.68688, 0.42755, 0.50094, 0.6673, 0.76231, 0.81577, 0.55252])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
