"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.52646, 0.18112, 0.43597, 0.95839, 1.0, 0.50242, 0.24551, 0.0, 0.16556, 1.0, 0.74825, 0.43578, 0.33005, 0.0, 0.40859, 0.33369, 1.0, 0.14506, 0.0, 0.56331, 0.0, 0.91162, 0.24837, 0.08522, 0.0, 0.0, 0.47071, 1.0, 0.20607, 0.99976, 1.0, 0.53474, 0.61202, 0.0, 1.0, 1.0, 0.47521, 0.91011, 0.0, 0.29323, 1.0, 0.39464, 1.0, 0.40867, 0.0, 1.0, 0.0])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
