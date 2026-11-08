"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.93001, 0.18139, 0.71208, 1.0, 0.0, 0.65946, 0.67094, 0.85386, 0.61161, 0.92792, 0.97813, 0.04841, 1.0, 0.77468, 0.0, 0.16335, 0.95693, 0.45082, 0.0, 0.33849, 0.25968, 1.0, 0.27164, 0.0, 0.83515, 0.0, 0.21474, 0.0, 0.4553, 0.26428, 0.3765, 0.2583, 0.0, 0.58025, 0.18079, 0.0085, 0.0, 0.96384, 1.0, 0.85025, 1.0, 1.0, 1.0, 0.0, 0.988, 0.63283, 0.5018])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
