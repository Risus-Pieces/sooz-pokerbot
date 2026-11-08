"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.78317, 0.00087, 0.93546, 0.6443, 0.06093, 0.99959, 0.37278, 0.83528, 0.79864, 0.72257, 0.95096, 0.24758, 0.99859, 0.25218, 0.88891, 0.41292, 0.63583, 0.48855, 0.22453, 0.29663, 0.14134, 0.86376, 0.18523, 0.4832, 0.55036, 0.55705, 0.15763, 0.05027, 0.06209, 0.12968, 0.00159, 0.20917, 0.01759, 0.60499, 0.22227, 0.24679, 0.57713, 0.92074, 0.51306, 0.68986, 0.88176, 0.81284, 0.71119, 0.00652, 0.76458, 0.34919, 0.35942])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
