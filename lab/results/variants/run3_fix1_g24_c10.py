"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.59474, 0.29451, 0.60289, 0.49261, 0.33495, 0.59906, 0.58264, 0.99949, 0.32474, 0.93648, 0.85843, 0.21789, 0.81426, 0.69697, 0.97075, 0.17532, 0.99734, 0.17787, 0.00349, 0.15416, 0.03927, 0.70358, 0.14632, 0.9843, 0.7507, 0.40892, 0.02811, 0.14563, 0.17283, 0.18746, 0.61264, 0.56115, 0.29561, 0.40032, 0.11427, 0.04048, 0.49075, 0.93646, 0.35199, 0.5556, 0.99994, 0.98909, 0.60425, 0.16123, 0.88113, 0.26694, 0.4728])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
