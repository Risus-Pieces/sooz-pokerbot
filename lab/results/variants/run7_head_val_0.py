"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.51924, 0.04812, 0.50383, 0.79, 1.0, 1.0, 0.55956, 0.08914, 0.37714, 0.98572, 1.0, 0.31073, 0.20299, 0.69366, 0.0, 0.93036, 0.0, 0.0, 0.38686, 0.28285, 0.0, 1.0, 0.0, 0.2285, 0.13966, 0.31089, 0.57963, 0.19209, 0.54981, 0.54657, 0.0, 1.0, 1.0, 0.19916, 0.0, 1.0, 0.0, 0.92149, 0.0, 0.80697, 0.95249, 0.17793, 0.75287, 0.40215, 0.33022, 0.0, 0.0])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
