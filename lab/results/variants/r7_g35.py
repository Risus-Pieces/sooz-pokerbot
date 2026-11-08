"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.30393, 0.00658, 0.58418, 0.80854, 0.98219, 0.7538, 0.46417, 0.228, 0.38862, 0.99965, 0.9993, 0.2013, 0.13207, 0.85708, 0.74335, 0.95691, 0.29068, 0.2197, 0.00437, 0.59322, 0.28825, 0.69676, 0.43083, 0.34788, 0.00109, 0.26708, 0.32739, 0.04716, 0.55798, 0.24572, 0.97297, 0.92686, 0.94132, 0.09299, 0.77179, 0.35313, 0.14592, 0.82433, 0.19119, 0.90315, 0.68434, 0.39249, 0.6635, 0.23185, 0.53473, 1.0, 0.10195])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
