"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.55124, 0.07043, 0.0, 0.70712, 0.3116, 1.0, 0.46299, 0.0, 0.95731, 0.16269, 1.0, 0.02681, 1.0, 0.08881, 0.00181, 0.80646, 0.82338, 0.0, 0.0, 0.0, 0.44309, 1.0, 0.0, 0.41258, 0.76197, 0.0, 0.03371, 0.13498, 0.50385, 0.0, 0.69677, 0.49592, 0.46318, 0.42351, 0.0, 0.13834, 0.0, 0.59773, 0.76972, 0.39573, 0.46269, 0.85934, 0.95479, 0.70138, 1.0, 0.52246])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
