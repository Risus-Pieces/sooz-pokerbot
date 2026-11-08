"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.91759, 0.14715, 0.96208, 0.70767, 0.31319, 0.59857, 0.47769, 0.88097, 0.56277, 0.98949, 0.99828, 0.03272, 0.94373, 0.68656, 0.99506, 0.00157, 0.96514, 0.10844, 0.0569, 0.3528, 0.50631, 0.83894, 0.13401, 0.60229, 0.97618, 0.3382, 0.00429, 0.54624, 0.04337, 0.17718, 0.5653, 0.20549, 0.40351, 0.59386, 1e-05, 0.00342, 0.46224, 0.94168, 0.15388, 0.35946, 0.87982, 0.99952, 0.58655, 0.40037, 0.90507, 0.39531, 0.29031])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
