"""
game_engine.py — Core Game Engine for the Two-Stage Strategic Deterrence Game

Models a two-stage extensive-form game between the USA (Nuclear Superpower)
and Iran (Emerging Nuclear State), based on Zagare (1992) and Kraig (1999).

Stage 1: Conventional warfare (Cooperate vs. Defect)
Stage 2: Nuclear escalation (Escalate vs. Defect)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Player(Enum):
    """The two players in the deterrence game."""
    USA = "USA"
    IRAN = "Iran"


class Action(Enum):
    """Available actions across both stages."""
    COOPERATE = "C"   # Stage 1: cooperate (status quo)
    DEFECT = "D"      # Stage 1: defect (conventional aggression)
    ESCALATE = "E"    # Stage 2: nuclear escalation


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class GameConfig:
    """All tunable parameters for a single game instance.

    Preference orderings (conventional stage):
        USA : CD > CC > DD > DC   →  payoffs 4, 3, 2, 1
        Iran: DC > CC > DD > CD   →  payoffs 4, 3, 2, 1
    """

    # --- Base conventional payoffs (rank 1-4) ---
    # 1st index = USA, 2nd index = Iran
    # Keys: (usa_action, iran_action) for stage-1 conventional outcomes
    usa_payoffs: Dict[Tuple[str, str], float] = field(default_factory=lambda: {
        ("D", "C"): 4.0,   # USA defects, Iran cooperates -> temptation (best for USA)
        ("C", "C"): 3.0,   # Mutual cooperation
        ("D", "D"): 2.0,   # Mutual defection
        ("C", "D"): 1.0,   # USA cooperates, Iran defects -> sucker (worst for USA)
    })

    iran_payoffs: Dict[Tuple[str, str], float] = field(default_factory=lambda: {
        ("C", "D"): 4.0,   # USA cooperates, Iran defects -> temptation (best for Iran)
        ("C", "C"): 3.0,   # Mutual cooperation
        ("D", "D"): 2.0,   # Mutual defection
        ("D", "C"): 1.0,   # USA defects, Iran cooperates -> sucker (worst for Iran)
    })

    # --- Nuclear penalty ---
    # Ensures EE (mutual nuclear exchange) is below all conventional outcomes.
    nuc_penalty: float = 10.0

    # --- Credibility (probability that a nuclear threat is carried out) ---
    credibility_usa: float = 0.5
    credibility_iran: float = 0.5

    # --- First-strike bonus ---
    first_strike_bonus: float = 0.0

    # --- Audience costs (hand-tying) ---
    audience_cost_usa: float = 0.0
    audience_cost_iran: float = 0.0

    # --- Sunk costs (pre-game investments) ---
    sunk_cost_usa: float = 0.0
    sunk_cost_iran: float = 0.0

    # --- Capability flag ---
    iran_has_nuclear: bool = True


# ---------------------------------------------------------------------------
# Payoff helpers
# ---------------------------------------------------------------------------

def _min_conventional(config: GameConfig) -> float:
    """Return the minimum conventional payoff across both players."""
    all_vals = list(config.usa_payoffs.values()) + list(config.iran_payoffs.values())
    return min(all_vals)


def get_conventional_payoffs(
    config: GameConfig, usa_action: str, iran_action: str
) -> Tuple[float, float]:
    """Return (usa_payoff, iran_payoff) for a conventional-stage action pair.

    Parameters
    ----------
    usa_action, iran_action : str
        One of 'C' (Cooperate) or 'D' (Defect).
    """
    key = (usa_action, iran_action)
    usa_pay = config.usa_payoffs[key]
    iran_pay = config.iran_payoffs[key]

    # Apply audience-cost penalty when a player cooperates (backs down)
    # after presumably having made a public threat.
    if usa_action == "C":
        usa_pay -= config.audience_cost_usa
    if iran_action == "C":
        iran_pay -= config.audience_cost_iran

    return usa_pay, iran_pay


def get_nuclear_payoffs(
    config: GameConfig, usa_action: str, iran_action: str
) -> Tuple[float, float]:
    """Return (usa_payoff, iran_payoff) for the nuclear-escalation stage.

    Parameters
    ----------
    usa_action, iran_action : str
        One of 'E' (Escalate) or 'D' (Defect / back down).
    """
    floor = _min_conventional(config)
    
    # Calculate the max conventional payoff to ensure U(ED) > max conventional
    all_vals = list(config.usa_payoffs.values()) + list(config.iran_payoffs.values())
    ceiling = max(all_vals)

    if usa_action == "E" and iran_action == "E":
        # Mutual nuclear destruction — worst possible outcome
        pay = floor - config.nuc_penalty
        return pay, pay

    if usa_action == "E" and iran_action == "D":
        # USA escalates, Iran backs down → first-strike advantage for USA
        # Escalation win must be > conventional DD (2.0) and CC (3.0)
        usa_pay = ceiling + 1.0 + config.first_strike_bonus + config.sunk_cost_usa
        iran_pay = floor - config.nuc_penalty / 2  # severe but not mutual
        return usa_pay, iran_pay

    if usa_action == "D" and iran_action == "E":
        # Iran escalates, USA backs down
        if not config.iran_has_nuclear:
            # Iran cannot escalate without nuclear capability
            # Falls back to conventional mutual defection payoff
            return get_conventional_payoffs(config, "D", "D")
        iran_pay = ceiling + 1.0 + config.first_strike_bonus + config.sunk_cost_iran
        usa_pay = floor - config.nuc_penalty / 2
        return usa_pay, iran_pay

    # Both defect in nuclear stage → revert to conventional DD
    return get_conventional_payoffs(config, "D", "D")


def get_payoffs(
    config: GameConfig, usa_action: str, iran_action: str
) -> Tuple[float, float]:
    """Unified dispatcher — works for both conventional and nuclear actions.

    Conventional actions: 'C', 'D'
    Nuclear actions: 'E' (only valid in stage 2)
    """
    if usa_action in ("C", "D") and iran_action in ("C", "D"):
        return get_conventional_payoffs(config, usa_action, iran_action)
    return get_nuclear_payoffs(config, usa_action, iran_action)


def get_all_outcomes(config: GameConfig) -> Dict[Tuple[str, str], Tuple[float, float]]:
    """Return a mapping of every action pair to its payoff tuple.

    Includes conventional pairs (CC, CD, DC, DD) and nuclear pairs (EE, ED, DE, DD-nuc).
    """
    outcomes: Dict[Tuple[str, str], Tuple[float, float]] = {}

    # Conventional outcomes
    for a_usa in ("C", "D"):
        for a_iran in ("C", "D"):
            outcomes[(a_usa, a_iran)] = get_conventional_payoffs(config, a_usa, a_iran)

    # Nuclear outcomes
    for a_usa in ("E", "D"):
        for a_iran in ("E", "D"):
            key = (a_usa, a_iran)
            if key == ("D", "D"):
                key = ("D_nuc", "D_nuc")  # distinguish from conventional DD
            outcomes[key] = get_nuclear_payoffs(config, a_usa, a_iran)

    return outcomes


def print_payoff_table(config: GameConfig) -> None:
    """Pretty-print the full payoff table to stdout."""
    outcomes = get_all_outcomes(config)

    print("\n+==========================================================+")
    print("|            PAYOFF TABLE  (USA, Iran)                     |")
    print("+==========================================================+")
    print("|  Stage   |  USA Action  | Iran Action |   Payoffs        |")
    print("+==========================================================+")

    labels = {
        ("C", "C"): ("Conv.", "Cooperate", "Cooperate"),
        ("C", "D"): ("Conv.", "Cooperate", "Defect"),
        ("D", "C"): ("Conv.", "Defect", "Cooperate"),
        ("D", "D"): ("Conv.", "Defect", "Defect"),
        ("E", "E"): ("Nucl.", "Escalate", "Escalate"),
        ("E", "D"): ("Nucl.", "Escalate", "Defect"),
        ("D", "E"): ("Nucl.", "Defect", "Escalate"),
        ("D_nuc", "D_nuc"): ("Nucl.", "Defect", "Defect"),
    }

    for key, (stage, usa_lbl, iran_lbl) in labels.items():
        if key in outcomes:
            usa_p, iran_p = outcomes[key]
            print(f"|  {stage:<6} |  {usa_lbl:<10} | {iran_lbl:<11}|  ({usa_p:>6.2f}, {iran_p:>6.2f}) |")

    print("+==========================================================+\n")
