"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.91689, 0.02286, 0.81136, 0.60895, 0.1906, 0.56935, 0.51464, 0.99998, 0.59813, 0.8179, 0.77515, 0.14568, 0.98837, 0.57561, 0.77318, 0.15069, 0.91364, 0.47479, 0.07527, 0.28212, 0.187, 0.98683, 0.65928, 0.61529, 0.70706, 0.32305, 0.15374, 0.19282, 0.09245, 0.27522, 0.30367, 0.15293, 0.48666, 0.36899, 0.02561, 0.27658, 0.478, 0.52702, 0.46248, 0.26992, 0.92386, 0.93262, 0.36206, 0.35929, 0.99854, 0.19112, 0.4572])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
