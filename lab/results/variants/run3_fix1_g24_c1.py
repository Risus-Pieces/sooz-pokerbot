"""Generated parambot variant."""
import os, sys
sys.path.insert(0, '/Users/risus_zhao/Library/Application Support/Claude/scratch-workspaces/d82b556b-c149-442b-8339-d48c04d82e85/e90dcb7b-bd59-43d3-9b35-0472a6754bcc/scratch-2026-10-28-67941e/pokerbot/lab')
import parambot as _pb
P = _pb.decode([0.9733, 0.04405, 0.53335, 0.53799, 0.41399, 0.43463, 0.56347, 0.9547, 0.76789, 0.99499, 0.92692, 0.0785, 0.94782, 0.82071, 0.94206, 0.10354, 0.85587, 0.26984, 0.23579, 0.16108, 0.21562, 0.89608, 0.37, 0.69298, 0.2616, 0.27456, 0.05109, 0.32682, 0.19589, 0.12698, 0.27124, 0.38616, 0.43346, 0.67953, 0.38296, 0.00456, 0.45281, 0.98414, 0.39697, 0.40706, 0.99381, 0.98384, 0.62807, 0.20799, 0.85728, 0.59811, 0.33368])


def new_half(config, memory):
    _pb.new_half(config, memory, P)


choose_action = _pb.choose_action
on_hand_end = _pb.on_hand_end
