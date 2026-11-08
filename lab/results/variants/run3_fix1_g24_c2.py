"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.65784, 0.00287, 0.51338, 0.53697, 0.31773, 0.99357, 0.55503, 0.99492, 0.39338, 0.86963, 0.98917, 0.10861, 0.95448, 0.71823, 0.92735, 0.21742, 0.99623, 0.29338, 0.07705, 0.22657, 0.05965, 0.66879, 0.41996, 0.80221, 0.37334, 0.0312, 0.02771, 0.32568, 0.20463, 0.10926, 0.61803, 0.4883, 0.52499, 0.35619, 0.15009, 0.06556, 0.43355, 0.98831, 0.67199, 0.76464, 0.93596, 0.999, 0.6864, 0.02552, 0.76541, 0.44786, 0.31183])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
