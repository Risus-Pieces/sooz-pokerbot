"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.41852, 0.10306, 0.15224, 0.88403, 0.33071, 0.89939, 0.31104, 0.15256, 0.98807, 0.24039, 0.71747, 0.06009, 0.90288, 0.08204, 0.08136, 0.6874, 0.4846, 0.14664, 0.01951, 0.01638, 0.33773, 0.96944, 0.10632, 0.26459, 0.86197, 0.16636, 0.00533, 0.26626, 0.60406, 0.03934, 0.42482, 0.37118, 0.47024, 0.42509, 0.11974, 0.0531, 0.4084, 0.66531, 0.77395, 0.39288, 0.32542, 0.69422, 0.99189, 0.70161, 0.87216, 0.55026])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
