"""Plays like eqbot, then its 'time bank runs out' at hand 300 and the judge
auto-plays it (check when free, fold otherwise) for the rest of the half."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eqbot  # noqa: E402
from game import default_action  # noqa: E402


def new_half(config, memory):
    eqbot.new_half(config, memory)


def choose_action(obs, memory):
    if obs.hand_index >= 300:
        return default_action(obs.to_call)
    return eqbot.choose_action(obs, memory)


def on_hand_end(result, memory):
    pass
