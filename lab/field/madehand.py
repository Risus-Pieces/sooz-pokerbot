"""Rule-based on the made hand only (no simulation): a common simple approach."""
from evaluator import category_of
from fasteval import score_one
from game import Action, Street


def new_half(config, memory):
    pass


def choose_action(obs, memory):
    legal = obs.legal_actions
    if obs.street == Street.PREFLOP:
        ranks = [c >> 2 for c in obs.hole_cards]
        pairs = len(ranks) - len(set(ranks))
        suits = [c & 3 for c in obs.hole_cards]
        suited = max(suits.count(s) for s in set(suits)) >= 2
        strong = pairs >= 1 and max(ranks) >= 6 and suited
        if strong and Action.RAISE_HALF in legal:
            return Action.RAISE_HALF
        if obs.to_call <= 4 or pairs >= 1:
            return Action.CHECK_CALL
        return Action.FOLD
    cat = category_of(score_one(obs.hole_cards, obs.board))
    if cat >= 4 and Action.RAISE_POT in legal:   # trips or better
        return Action.RAISE_POT
    if cat >= 2 or obs.to_call == 0:              # two pair or better
        return Action.CHECK_CALL
    if cat == 1 and obs.to_call <= obs.pot // 3:
        return Action.CHECK_CALL
    return Action.FOLD


def on_hand_end(result, memory):
    pass
