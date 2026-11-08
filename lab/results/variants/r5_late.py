"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([1.0, 0.45971, 0.91695, 0.97586, 0.8189, 0.89818, 0.0, 0.25812, 0.74412, 1.0, 0.60347, 0.0, 0.9686, 0.69285, 0.0, 0.0, 0.0, 0.47815, 0.05263, 0.50735, 0.0, 0.72922, 0.4352, 0.0, 0.97069, 0.0, 0.00596, 0.0, 0.58465, 1.0, 0.13875, 0.01331, 0.0, 0.2501, 1.0, 0.0, 0.0, 1.0, 0.03338, 1.0, 0.95023, 1.0, 0.40883, 0.97512, 0.81707, 0.0, 0.0])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
