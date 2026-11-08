"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.40716, 0.01033, 0.00995, 0.87017, 0.49418, 0.84171, 0.57725, 0.01276, 0.76415, 0.28065, 0.94046, 0.01681, 0.91875, 0.00509, 0.13369, 0.56036, 0.56859, 0.11925, 0.00056, 0.00576, 0.79539, 0.89476, 0.26221, 0.35048, 0.7373, 0.01442, 0.04773, 0.33052, 0.23183, 0.15387, 0.77782, 0.77135, 0.29333, 0.51191, 0.01692, 0.02457, 0.22491, 0.42002, 0.92565, 0.6416, 0.55729, 0.62284, 0.80725, 0.6512, 0.98879, 0.47337])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
