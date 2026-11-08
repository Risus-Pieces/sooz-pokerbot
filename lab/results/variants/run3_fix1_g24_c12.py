"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.87499, 0.0, 0.75041, 0.60655, 0.21959, 0.82092, 0.82925, 0.87171, 0.6619, 0.96837, 0.92741, 0.01488, 0.84238, 0.5637, 0.99599, 0.37655, 0.90444, 0.60957, 0.05202, 0.17289, 0.28128, 0.94348, 0.29438, 0.89498, 0.99256, 0.48898, 0.04427, 0.00379, 0.13222, 0.19222, 0.55749, 0.57448, 0.2886, 0.13733, 0.29835, 0.00051, 0.50109, 0.98893, 0.23552, 0.51702, 0.60462, 0.84864, 0.3826, 0.04674, 0.90556, 0.37709, 0.34662])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
