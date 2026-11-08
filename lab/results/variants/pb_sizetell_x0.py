"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.5, 0.0, 0.5, 0.82857, 0.56667, 1.0, 0.875, 0.0, 0.4, 0.4, 0.4, 0.4, 0.43333, 0.5, 0.0, 0.6, 0.56, 0.0, 0.0, 0.14, 0.5, 0.5, 0.0, 0.6, 0.64, 0.0, 0.0, 0.2, 0.56667, 0.0, 0.0, 0.7, 0.72, 0.0, 0.0, 0.6, 0.0, 0.5, 0.5, 0.5, 0.5, 0.75, 0.65, 0.55, 0.85, 0.25])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
