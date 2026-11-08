"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.86178, 0.03138, 0.70751, 1.0, 0.0, 0.75391, 0.52749, 0.91774, 0.60213, 1.0, 1.0, 0.0, 1.0, 0.60147, 0.0, 0.25866, 0.86555, 0.38844, 0.01276, 0.14086, 0.08891, 1.0, 0.25728, 0.0, 0.70925, 0.0, 0.00748, 0.0, 0.26643, 0.18368, 0.39133, 0.19124, 0.0, 0.4558, 0.15163, 0.1091, 0.0, 0.97214, 1.0, 0.67607, 1.0, 0.91803, 1.0, 0.0, 1.0, 0.39549, 0.39312])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
