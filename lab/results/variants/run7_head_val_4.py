"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.3409, 0.19339, 0.24029, 0.10111, 0.9687, 0.87184, 0.32124, 0.13027, 0.88382, 0.55503, 0.80532, 0.40723, 0.05661, 0.86215, 0.48635, 0.98832, 0.14093, 0.12623, 0.40656, 0.59789, 0.15744, 0.66523, 0.5465, 0.92815, 0.40159, 0.29681, 0.25093, 0.32159, 0.65044, 0.11908, 0.20782, 0.97146, 0.99102, 0.68717, 0.31165, 0.59694, 0.32824, 0.77402, 0.17863, 0.65664, 0.81423, 0.37079, 0.96657, 0.46735, 0.03639, 0.60404, 0.37027])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
