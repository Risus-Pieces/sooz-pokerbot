"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.78552, 0.01185, 0.3301, 0.57031, 0.13201, 0.59865, 0.42989, 0.93252, 0.23928, 0.86293, 0.92139, 0.00239, 0.99728, 0.55112, 0.60092, 0.33573, 0.98269, 0.2774, 0.14161, 0.2395, 0.00426, 0.69949, 0.47167, 0.94833, 0.44126, 0.16842, 0.19787, 0.05571, 0.08523, 0.44257, 0.25756, 0.31125, 0.39296, 0.45949, 0.3521, 0.33749, 0.73622, 0.99437, 0.32864, 0.61597, 0.90088, 0.67342, 0.74242, 0.00282, 0.68538, 0.56204, 0.68136])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
