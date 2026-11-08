"""Second blueprint bot for checkpoint-vs-checkpoint matches: like bp_bot.py but
reads its strategy from env BP_PATH_B (and BP_MINP_B). Underscore = not in the field."""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location("_bp_bot_base_b", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bp_bot.py"))
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def new_half(config, memory):
    _base.new_half(config, memory)
    memory["bp"] = _base._get_bp(os.environ["BP_PATH_B"])
    memory["minp"] = float(os.environ.get("BP_MINP_B", "0") or 0)


choose_action = _base.choose_action
on_hand_end = _base.on_hand_end
