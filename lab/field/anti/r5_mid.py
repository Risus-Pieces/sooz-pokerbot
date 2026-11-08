"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([1.0, 0.0, 0.97533, 1.0, 0.65489, 1.0, 0.3195, 0.45748, 0.29033, 0.94395, 0.89398, 0.0047, 1.0, 0.65286, 0.0, 0.0, 0.01784, 0.48771, 0.0, 0.63715, 0.0, 0.88048, 0.32287, 0.02948, 1.0, 0.09425, 0.11091, 0.0, 0.62671, 0.98192, 0.0, 0.05469, 0.0, 0.0, 0.98234, 0.0, 0.0, 1.0, 0.10632, 1.0, 0.99963, 1.0, 0.71469, 0.71588, 0.73942, 0.0, 0.05741])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
