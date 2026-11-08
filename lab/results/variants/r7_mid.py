"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.41563, 0.25781, 0.62069, 0.67936, 0.98627, 1.0, 0.22702, 0.00179, 0.64392, 0.62694, 1.0, 0.1817, 0.16342, 0.58189, 0.0, 0.99484, 0.00578, 0.0, 0.0, 0.53683, 0.0, 1.0, 0.0, 0.55551, 0.24151, 0.14962, 0.48668, 0.59133, 0.56954, 0.24131, 0.0, 1.0, 0.8967, 0.38251, 0.0, 1.0, 0.0, 0.62834, 0.0412, 0.90879, 0.69985, 0.72397, 0.99137, 0.16884, 0.28137, 0.0, 0.02887])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
