"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.80388, 0.12938, 0.53585, 0.62883, 1.0, 1.0, 0.61549, 0.0, 0.43177, 0.44469, 0.58133, 0.43372, 0.32894, 0.27312, 0.0, 0.88398, 0.28523, 0.0, 0.0, 0.72728, 0.0, 0.99009, 0.0, 0.73822, 0.5495, 0.13185, 0.0, 0.68725, 0.63117, 0.09964, 0.0, 1.0, 1.0, 0.46694, 0.0, 1.0, 0.0, 0.5909, 0.35042, 0.5068, 0.9015, 0.82657, 1.0, 0.69144, 0.04746, 0.0483, 0.04033])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
