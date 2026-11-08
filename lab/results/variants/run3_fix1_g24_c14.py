"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.91742, 0.0002, 0.82614, 0.49094, 0.27879, 0.60945, 0.30171, 0.86363, 0.46191, 0.57842, 0.73102, 0.02801, 0.97642, 0.51459, 0.96139, 0.43471, 0.85341, 0.55171, 0.26078, 0.13807, 8e-05, 0.89499, 0.18586, 0.84403, 0.93918, 0.4888, 0.07736, 0.16815, 0.00643, 0.15235, 0.38218, 0.23919, 0.58873, 0.80174, 0.13658, 0.023, 0.40487, 0.63651, 0.64886, 0.74134, 0.83643, 0.98752, 0.57436, 0.43018, 0.84865, 0.21788, 0.3063])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
