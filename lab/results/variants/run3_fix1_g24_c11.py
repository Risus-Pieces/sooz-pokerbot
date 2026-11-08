"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.91404, 0.00624, 1.0, 0.70086, 0.43875, 0.39889, 0.56436, 0.99883, 0.63955, 0.69383, 0.77354, 0.02346, 0.8763, 0.49799, 0.96769, 0.42141, 0.93364, 0.13429, 0.21709, 0.02092, 0.07231, 0.91063, 0.51449, 0.81663, 0.95313, 0.37435, 0.16083, 0.21318, 0.01711, 0.2419, 0.43931, 0.18101, 0.0543, 0.29985, 0.15915, 0.09927, 0.40698, 0.99497, 0.65847, 0.41039, 0.66825, 0.79755, 0.94645, 0.13737, 0.8785, 0.54717, 0.29048])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
