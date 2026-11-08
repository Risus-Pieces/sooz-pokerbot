"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.68226, 0.00654, 0.51123, 1.0, 0.0, 0.88458, 0.44065, 0.57036, 0.64803, 0.82364, 0.93189, 0.04014, 1.0, 0.5506, 0.0, 0.51622, 0.85272, 0.23859, 0.06316, 0.22946, 0.08593, 1.0, 0.15425, 0.0, 0.86649, 0.0, 0.0, 0.0, 0.42379, 0.29229, 0.33144, 0.08568, 0.0, 0.31392, 0.0, 0.053, 0.0, 0.94629, 1.0, 0.60402, 1.0, 0.87452, 1.0, 0.08891, 1.0, 0.41402, 0.18937])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
