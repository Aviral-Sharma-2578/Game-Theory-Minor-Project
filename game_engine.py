"""
game_engine.py — Core Game Engine for the Asymmetric Escalation Game

Models the Asymmetric Escalation Game from Kilgour & Zagare (2007),
"Explaining Limited Conflicts", based on Perfect Deterrence Theory
(Zagare & Kilgour, 2000).

Game Tree (sequential):
    Node 1  — Challenger decides: C (Status Quo) or D (Initiate Conflict)
    Node 2  — Defender decides:   C (Capitulate), D (Respond-in-kind), or E (Escalate)
    Node 3a — If Defender chose D: Challenger decides D (Limited Conflict) or E (Escalate)
    Node 3b — If Defender chose E: Challenger decides D (Concede) or E (All-Out Conflict)
    Node 4  — If Challenger escalated at 3a: Defender decides D (Concede) or E (All-Out Conflict)

Outcomes:
    SQ  — Status Quo (Challenger cooperates at Node 1)
    DC  — Defender Concedes (Challenger defects, Defender capitulates)
    DD  — Limited Conflict (both stick with D)
    ED  — Challenger Wins (Challenger escalates, Defender backs down)
    DE  — Defender Wins (Defender escalates, Challenger concedes)
    EE  — All-Out Conflict (both escalate)

TYPE-DEPENDENT PAYOFFS (key feature from the paper):
    Hard types have higher payoffs at EE (prefer escalation to losing),
    Soft types have lower payoffs at EE (prefer backing down to mutual destruction).

    Challenger: EE+ = 25 (Hard), EE- = 0 (Soft)
    Defender:   EE+ = 30 (Hard), EE- = 0 (Soft)
    Defender:   DD+ = 60 (Tact. Hard), DD- = 40 (Tact. Soft)

Players are labelled "Challenger" (maps to Iran) and "Defender" (maps to USA).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Player(Enum):
    """The two players in the Asymmetric Escalation Game."""
    DEFENDER = "USA"       # Defender (status-quo power)
    CHALLENGER = "Iran"    # Challenger (revisionist power)


# Keep backward-compatible references
Player.USA = Player.DEFENDER
Player.IRAN = Player.CHALLENGER


class Action(Enum):
    """Available actions across all nodes."""
    COOPERATE = "C"   # Node 1: maintain status quo / Node 2: capitulate
    DEFECT = "D"      # Initiate conflict / respond-in-kind / back down
    ESCALATE = "E"    # Escalate to a higher level of conflict


class Outcome(Enum):
    """The six possible outcomes of the Asymmetric Escalation Game."""
    SQ = "SQ"    # Status Quo — Challenger cooperates
    DC = "DC"    # Defender Concedes — Challenger defects, Defender capitulates
    DD = "DD"    # Limited Conflict — both respond-in-kind
    ED = "ED"    # Challenger Wins — Challenger escalates, Defender backs down
    DE = "DE"    # Defender Wins — Defender escalates, Challenger concedes
    EE = "EE"    # All-Out Conflict — both escalate


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class GameConfig:
    """All tunable parameters for a single game instance.

    Preference orderings (from the paper, Kilgour & Zagare 2007):
        Challenger: DC > SQ > ED > DD > EE+ > DE > EE-
        Defender:   SQ > DE > DD+ > DC > DD- > EE+ > ED > EE-

    Type-dependent payoffs (the paper's key feature):
        At EE: Hard types get EE+ payoff, Soft types get EE-
        At DD: Tactically Hard Defender gets DD+, Soft gets DD-

    The model uses the paper's numerical example:
        Challenger: DC=100, SQ=60, ED=45, DD=40, EE+=25, DE=20, EE-=0
        Defender:   SQ=100, DE=90, DD+=60, DC=50, DD-=40, EE+=30, ED=20, EE-=0
    """

    # --- Challenger (Iran) payoffs per outcome ---
    chal_SQ: float = 60.0     # Status Quo
    chal_DC: float = 100.0    # Defender Concedes (best for Challenger)
    chal_DD: float = 40.0     # Limited Conflict
    chal_ED: float = 45.0     # Challenger Wins (escalates, Defender backs down)
    chal_DE: float = 20.0     # Defender Wins (Defender escalates)
    chal_EE_hard: float = 25.0  # All-Out Conflict — Hard Challenger (prefers EE to DE)
    chal_EE_soft: float = 0.0   # All-Out Conflict — Soft Challenger (prefers DE to EE)

    # --- Defender (USA) payoffs per outcome ---
    def_SQ: float = 100.0     # Status Quo (best for Defender)
    def_DC: float = 50.0      # Defender Concedes / capitulates
    def_DD_hard: float = 60.0  # Limited Conflict — Tactically Hard Defender
    def_DD_soft: float = 40.0  # Limited Conflict — Tactically Soft Defender
    def_ED: float = 20.0      # Challenger Wins → Defender loses at escalation level
    def_DE: float = 90.0      # Defender Wins (escalates successfully)
    def_EE_hard: float = 30.0  # All-Out Conflict — Hard Defender (prefers EE to ED)
    def_EE_soft: float = 0.0   # All-Out Conflict — Soft Defender (prefers ED to EE)

    # --- Credibility parameters ---
    # pCh: probability Challenger is "Hard" (prefers EE to DE)
    credibility_challenger: float = 0.5
    # p: Defender credibility parameter (determines all four Defender types)
    #    pTac = pStr = p  (using the paper's single-parameter simplification)
    credibility_defender: float = 0.5

    # --- Capability flags ---
    defender_can_escalate: bool = True
    challenger_can_escalate: bool = True

    # --- First-strike bonus ---
    first_strike_bonus: float = 0.0

    # --- Audience costs (hand-tying) ---
    audience_cost_defender: float = 0.0
    audience_cost_challenger: float = 0.0

    # --- Sunk costs (pre-game investments) ---
    sunk_cost_defender: float = 0.0
    sunk_cost_challenger: float = 0.0

    # ---- Backward compatibility aliases ----
    @property
    def credibility_usa(self) -> float:
        return self.credibility_defender

    @credibility_usa.setter
    def credibility_usa(self, val: float):
        self.credibility_defender = val

    @property
    def credibility_iran(self) -> float:
        return self.credibility_challenger

    @credibility_iran.setter
    def credibility_iran(self, val: float):
        self.credibility_challenger = val

    @property
    def iran_has_nuclear(self) -> bool:
        return self.challenger_can_escalate

    @iran_has_nuclear.setter
    def iran_has_nuclear(self, val: bool):
        self.challenger_can_escalate = val


# ---------------------------------------------------------------------------
# Payoff helpers
# ---------------------------------------------------------------------------

def get_challenger_payoff(config: GameConfig, outcome: str, is_hard: bool = True) -> float:
    """Get Challenger's payoff for a given outcome and type.

    Parameters
    ----------
    outcome : str
        One of 'SQ', 'DC', 'DD', 'ED', 'DE', 'EE'.
    is_hard : bool
        True for Hard Challenger, False for Soft.
    """
    pay = {
        "SQ": config.chal_SQ,
        "DC": config.chal_DC,
        "DD": config.chal_DD,
        "ED": config.chal_ED,
        "DE": config.chal_DE,
        "EE": config.chal_EE_hard if is_hard else config.chal_EE_soft,
    }[outcome]

    # Apply modifiers
    if outcome == "ED":
        pay += config.first_strike_bonus + config.sunk_cost_challenger
    if outcome == "SQ":
        pay -= config.audience_cost_challenger
    if outcome == "DE":
        pay -= config.audience_cost_challenger

    # Capability: if Challenger can't escalate, ED is unreachable → map to DD
    if outcome == "ED" and not config.challenger_can_escalate:
        return get_challenger_payoff(config, "DD", is_hard)
    if outcome == "EE" and not config.challenger_can_escalate:
        return get_challenger_payoff(config, "DE", is_hard)

    return pay


def get_defender_payoff(config: GameConfig, outcome: str,
                        is_tac_hard: bool = True, is_str_hard: bool = True) -> float:
    """Get Defender's payoff for a given outcome and type.

    Parameters
    ----------
    outcome : str
        One of 'SQ', 'DC', 'DD', 'ED', 'DE', 'EE'.
    is_tac_hard : bool
        True for Tactically Hard Defender, False for Soft.
    is_str_hard : bool
        True for Strategically Hard Defender, False for Soft.
    """
    if outcome == "DD":
        pay = config.def_DD_hard if is_tac_hard else config.def_DD_soft
    elif outcome == "EE":
        pay = config.def_EE_hard if is_str_hard else config.def_EE_soft
    else:
        pay = {
            "SQ": config.def_SQ,
            "DC": config.def_DC,
            "ED": config.def_ED,
            "DE": config.def_DE,
        }[outcome]

    # Apply modifiers
    if outcome == "DE":
        pay += config.first_strike_bonus + config.sunk_cost_defender
    if outcome == "DC":
        pay -= config.audience_cost_defender
    if outcome == "ED":
        pay -= config.audience_cost_defender

    # Capability: if Defender can't escalate, DE is unreachable
    if outcome == "DE" and not config.defender_can_escalate:
        return get_defender_payoff(config, "DD", is_tac_hard, is_str_hard)
    if outcome == "EE" and not config.defender_can_escalate:
        return get_defender_payoff(config, "ED", is_tac_hard, is_str_hard)

    return pay


def get_outcome_payoffs(config: GameConfig, outcome: str) -> Tuple[float, float]:
    """Return averaged (defender_payoff, challenger_payoff) for display purposes.

    Uses expected payoffs over types for EE and DD outcomes.
    """
    p = config.credibility_defender
    pCh = config.credibility_challenger

    if outcome == "EE":
        # Average over all type combinations
        d_pay = p * config.def_EE_hard + (1 - p) * config.def_EE_soft
        c_pay = pCh * config.chal_EE_hard + (1 - pCh) * config.chal_EE_soft
    elif outcome == "DD":
        d_pay = p * config.def_DD_hard + (1 - p) * config.def_DD_soft
        c_pay = config.chal_DD
    else:
        d_pay = get_defender_payoff(config, outcome)
        c_pay = get_challenger_payoff(config, outcome)

    return d_pay, c_pay


def get_all_outcomes(config: GameConfig) -> Dict[str, Tuple[float, float]]:
    """Return a mapping of every outcome to its (defender, challenger) payoff tuple."""
    outcomes: Dict[str, Tuple[float, float]] = {}
    for name in ("SQ", "DC", "DD", "ED", "DE", "EE"):
        outcomes[name] = get_outcome_payoffs(config, name)
    return outcomes


def print_payoff_table(config: GameConfig) -> None:
    """Pretty-print the full payoff table to stdout, showing type-dependent payoffs."""
    print("\n+==============================================================================+")
    print("|            PAYOFF TABLE  (Defender=USA, Challenger=Iran)                      |")
    print("|            Type-dependent payoffs marked with +/- suffixes                    |")
    print("+==============================================================================+")
    print("|  Outcome     | Description                           |   Payoffs (Def, Chal)  |")
    print("+==============================================================================+")

    p = config.credibility_defender
    pCh = config.credibility_challenger

    rows = [
        ("SQ",  "Status Quo (Challenger cooperates)",
         f"({config.def_SQ:>5.0f}, {config.chal_SQ:>5.0f})"),
        ("DC",  "Defender Concedes (capitulates)",
         f"({config.def_DC:>5.0f}, {config.chal_DC:>5.0f})"),
        ("DD+", "Limited Conflict (Tac Hard Defender)",
         f"({config.def_DD_hard:>5.0f}, {config.chal_DD:>5.0f})"),
        ("DD-", "Limited Conflict (Tac Soft Defender)",
         f"({config.def_DD_soft:>5.0f}, {config.chal_DD:>5.0f})"),
        ("ED",  "Challenger Wins (escalates, Def backs down)",
         f"({config.def_ED:>5.0f}, {config.chal_ED:>5.0f})"),
        ("DE",  "Defender Wins (escalates, Chal concedes)",
         f"({config.def_DE:>5.0f}, {config.chal_DE:>5.0f})"),
        ("EE+", "All-Out Conflict (Hard types)",
         f"({config.def_EE_hard:>5.0f}, {config.chal_EE_hard:>5.0f})"),
        ("EE-", "All-Out Conflict (Soft types)",
         f"({config.def_EE_soft:>5.0f}, {config.chal_EE_soft:>5.0f})"),
    ]

    for name, desc, payoffs in rows:
        print(f"|  {name:<12} | {desc:<37} |  {payoffs:<20} |")

    print("+==============================================================================+")
    print(f"|  Defender credibility p = {p:.2f}  (pTac = pStr = p)")
    print(f"|  Challenger credibility pCh = {pCh:.2f}")
    print(f"|  Defender types: HH={p**2:.2f}, HS={p*(1-p):.2f}, "
          f"SH={p*(1-p):.2f}, SS={(1-p)**2:.2f}")
    print("+==============================================================================+\n")
