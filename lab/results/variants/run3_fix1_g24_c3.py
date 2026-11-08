"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.82842, 0.12877, 0.47177, 0.62758, 0.0674, 0.59365, 0.368, 0.98747, 0.79232, 0.96999, 0.73332, 0.23048, 0.97865, 0.32477, 0.99435, 0.26228, 0.9247, 0.30589, 0.04118, 0.11427, 0.26851, 0.79476, 0.39227, 0.99616, 0.13744, 0.1862, 0.09636, 0.12419, 0.38435, 0.19787, 0.18081, 0.11019, 0.37678, 0.53366, 0.58305, 0.07409, 0.25275, 0.81721, 0.2174, 0.86345, 0.91432, 0.6126, 0.83832, 0.11071, 0.93774, 0.537, 0.53977])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
