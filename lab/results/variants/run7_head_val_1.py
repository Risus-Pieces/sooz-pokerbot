"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.3894, 0.17583, 0.60177, 0.75386, 1.0, 1.0, 0.37543, 0.04381, 0.4562, 0.85117, 1.0, 0.22172, 0.15002, 0.65179, 0.0, 0.97456, 0.0, 0.0, 0.13622, 0.46714, 0.0, 1.0, 0.0, 0.27751, 0.1968, 0.17888, 0.60984, 0.35252, 0.46563, 0.45372, 0.0, 1.0, 0.9049, 0.21314, 0.0, 1.0, 0.0, 0.80627, 0.00971, 0.83922, 0.8265, 0.38829, 0.82981, 0.29528, 0.27912, 0.0, 0.0])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
