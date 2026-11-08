"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.96862, 0.07073, 0.74861, 0.62815, 0.41784, 0.91992, 0.62875, 0.89835, 0.74125, 0.8847, 0.95446, 0.40158, 0.94227, 0.58219, 0.85401, 0.38286, 0.9805, 0.21214, 0.24007, 0.00506, 0.07068, 0.91012, 0.05012, 0.62187, 0.76943, 0.35826, 0.05878, 0.33781, 0.06834, 0.00319, 0.27495, 0.17076, 0.2815, 0.48978, 0.36138, 0.10363, 0.39003, 0.86589, 0.26185, 0.8738, 0.79151, 0.75253, 0.82864, 0.4098, 0.84251, 0.38482, 0.45539])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
