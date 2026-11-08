"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.99559, 0.26477, 0.84228, 0.59721, 0.29651, 0.69677, 0.3631, 0.83289, 0.65719, 0.86927, 0.98452, 0.03992, 0.57859, 0.74543, 0.74823, 0.04953, 0.91734, 0.20885, 0.01711, 0.2689, 0.46385, 0.99982, 0.42577, 0.55095, 0.9949, 0.16342, 0.08835, 0.14891, 0.44087, 0.09683, 0.24221, 0.03561, 0.46272, 0.54476, 0.34716, 0.00014, 0.64407, 0.92284, 0.804, 0.9747, 0.92858, 0.98633, 0.60515, 0.46456, 0.94972, 0.63234, 0.42399])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
