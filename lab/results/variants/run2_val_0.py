"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.45823, 0.04971, 0.0, 0.8408, 0.27465, 1.0, 0.41747, 0.0, 0.92864, 0.30148, 0.80266, 0.0, 1.0, 0.05333, 0.0, 0.64315, 0.61555, 0.0, 0.0, 0.0, 0.39711, 0.95366, 0.0, 0.26474, 0.73944, 0.0, 0.0, 0.31217, 0.54414, 0.0, 0.49426, 0.43953, 0.45894, 0.25053, 0.0, 0.03174, 0.0, 0.75987, 0.74648, 0.42, 0.46255, 0.66121, 0.94843, 0.60668, 1.0, 0.57225])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
