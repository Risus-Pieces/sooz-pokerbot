"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.48661, 0.13012, 0.00037, 0.84533, 0.27519, 1.0, 0.43721, 0.0, 0.93429, 0.23436, 0.92235, 0.01679, 1.0, 0.05966, 0.00018, 0.69327, 0.73437, 0.0, 0.00429, 0.0, 0.41754, 0.99311, 0.0, 0.27873, 0.79234, 0.0, 0.01141, 0.30921, 0.54372, 0.0, 0.6299, 0.43983, 0.36392, 0.36228, 0.0, 0.08865, 0.0, 0.62504, 0.7151, 0.42937, 0.45792, 0.80337, 0.96993, 0.6629, 1.0, 0.58468])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
