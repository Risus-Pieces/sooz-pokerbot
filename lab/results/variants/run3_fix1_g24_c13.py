"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.81108, 0.08981, 0.77684, 0.34228, 0.26276, 0.62447, 0.60961, 0.99771, 0.51974, 0.859, 0.99996, 0.3001, 0.94389, 0.75258, 0.91957, 0.05853, 0.85044, 0.56159, 0.00388, 0.16834, 0.079, 0.81759, 0.21916, 0.94067, 0.73146, 1e-05, 0.07035, 0.03441, 0.20921, 0.14805, 0.60049, 0.24154, 0.43605, 0.59874, 0.32025, 0.23445, 0.55958, 0.94184, 0.40528, 0.79147, 0.85523, 0.52977, 0.81692, 0.0406, 0.9621, 0.34262, 0.35681])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
