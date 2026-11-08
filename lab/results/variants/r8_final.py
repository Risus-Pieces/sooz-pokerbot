"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.6094, 0.16351, 0.4651, 0.97705, 1.0, 0.49616, 0.30915, 0.0, 0.2253, 1.0, 0.68833, 0.47154, 0.27933, 0.0, 0.39469, 0.25008, 1.0, 0.23293, 0.0, 0.60415, 0.0, 0.95321, 0.24884, 0.05662, 0.0, 0.0, 0.47986, 1.0, 0.24678, 0.99976, 1.0, 0.52778, 0.55563, 0.0, 1.0, 1.0, 0.45658, 0.87438, 0.0, 0.28657, 1.0, 0.39242, 1.0, 0.45666, 0.0, 1.0, 0.0])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
