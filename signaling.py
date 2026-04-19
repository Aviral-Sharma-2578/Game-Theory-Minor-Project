"""
signaling.py — Commitment & Signaling Engine

Models two commitment mechanisms from deterrence theory:

    1. Hand-Tying (Audience Costs): Public statements that make backing
       down costly, thereby increasing threat credibility.
    2. Sunk Costs: Pre-game investments (e.g., missile defense, troop
       mobilization) that reduce the cost of retaliation.

Updated for the Asymmetric Escalation Game (Kilgour & Zagare, 2007).

References: Fearon (1994), Schelling (1966).
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import List, Optional, Tuple

from game_engine import GameConfig, Player
from scenarios import ScenarioResult, backward_induction


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class SignalingResult:
    """One data-point in a signaling sweep."""
    mechanism: str           # "audience_cost" or "sunk_cost"
    player: Player
    cost_value: float
    equilibrium: Tuple[str, ...]
    outcome: str
    payoffs: Tuple[float, float]
    credibility_defender: float
    credibility_challenger: float


# ---------------------------------------------------------------------------
# Audience Costs (Hand-Tying)
# ---------------------------------------------------------------------------

def apply_audience_costs(
    config: GameConfig,
    player: Player,
    cost: float,
) -> GameConfig:
    """Return a new config with audience costs applied to *player*.

    Audience costs penalize a player for cooperating (backing down)
    after a public commitment to defect/escalate.  Higher costs make
    the threat more credible.

    Parameters
    ----------
    config : GameConfig
        Base configuration to modify.
    player : Player
        Which player makes the public commitment.
    cost : float
        The penalty for backing down.
    """
    cfg = deepcopy(config)
    if player == Player.DEFENDER or player == Player.USA:
        cfg.audience_cost_defender = cost
        # Higher audience cost → higher perceived credibility
        cfg.credibility_defender = min(1.0, config.credibility_defender + cost * 0.1)
    else:
        cfg.audience_cost_challenger = cost
        cfg.credibility_challenger = min(1.0, config.credibility_challenger + cost * 0.1)
    return cfg


# ---------------------------------------------------------------------------
# Sunk Costs (Pre-game Investments)
# ---------------------------------------------------------------------------

def apply_sunk_costs(
    config: GameConfig,
    player: Player,
    investment: float,
) -> GameConfig:
    """Return a new config with sunk costs applied to *player*.

    Sunk costs model pre-game investments that reduce the cost of
    retaliation (e.g., missile-defense systems, forward-deployed troops).
    These increase the payoff for retaliatory escalation and thus
    enhance credibility.

    Parameters
    ----------
    config : GameConfig
        Base configuration to modify.
    player : Player
        Which player makes the investment.
    investment : float
        Size of the pre-game investment.
    """
    cfg = deepcopy(config)
    if player == Player.DEFENDER or player == Player.USA:
        cfg.sunk_cost_defender = investment
        cfg.credibility_defender = min(1.0, config.credibility_defender + investment * 0.08)
    else:
        cfg.sunk_cost_challenger = investment
        cfg.credibility_challenger = min(1.0, config.credibility_challenger + investment * 0.08)
    return cfg


# ---------------------------------------------------------------------------
# Signaling Sweep
# ---------------------------------------------------------------------------

def analyze_signaling_effect(
    base_config: Optional[GameConfig],
    player: Player,
    cost_range: Optional[List[float]] = None,
    mechanism: str = "audience_cost",
) -> List[SignalingResult]:
    """Iterate over a range of commitment costs and record equilibria.

    Parameters
    ----------
    base_config : GameConfig or None
        Starting config. Uses default if None.
    player : Player
        Which player's commitment is varied.
    cost_range : list of float, optional
        Values to sweep. Defaults to [0.0, 0.5, 1.0, …, 5.0].
    mechanism : str
        Either ``"audience_cost"`` or ``"sunk_cost"``.

    Returns
    -------
    list of SignalingResult
    """
    cfg = base_config if base_config else GameConfig()
    if cost_range is None:
        cost_range = [round(x * 0.5, 1) for x in range(11)]  # 0.0 … 5.0

    apply_fn = apply_audience_costs if mechanism == "audience_cost" else apply_sunk_costs

    results: List[SignalingResult] = []
    for cost in cost_range:
        modified_cfg = apply_fn(cfg, player, cost)
        eq = backward_induction(modified_cfg)
        results.append(
            SignalingResult(
                mechanism=mechanism,
                player=player,
                cost_value=cost,
                equilibrium=eq.equilibrium,
                outcome=eq.outcome,
                payoffs=eq.payoffs,
                credibility_defender=modified_cfg.credibility_defender,
                credibility_challenger=modified_cfg.credibility_challenger,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Pretty-printing
# ---------------------------------------------------------------------------

def print_signaling_analysis(results: List[SignalingResult]) -> None:
    """Print a formatted table of signaling sweep results."""
    if not results:
        return

    mechanism_label = (
        "Audience Costs" if results[0].mechanism == "audience_cost"
        else "Sunk Costs"
    )
    player_label = results[0].player.value

    divider = "-" * 90
    print(f"\n+{divider}+")
    print(f"|{'SIGNALING ANALYSIS':^90}|")
    print(f"|  Mechanism : {mechanism_label:<20}  Player : {player_label:<42}|")
    print(f"+{divider}+")
    print(f"|  {'Cost':>6}  |  {'Cred(Def)':>9}  |  {'Cred(Chal)':>10}  |"
          f"  {'Equilibrium':^20}  |  {'Outcome':^8}  |  {'Payoffs':^14}  |")
    print(f"+{divider}+")

    for r in results:
        eq_str = f"({r.equilibrium[0]}, {r.equilibrium[1]})"
        pay_str = f"({r.payoffs[0]:>6.2f}, {r.payoffs[1]:>6.2f})"
        print(f"|  {r.cost_value:>6.1f}  |  {r.credibility_defender:>9.2f}  |"
              f"  {r.credibility_challenger:>10.2f}  |  {eq_str:^20}  |  {r.outcome:^8}  |  {pay_str:^14}  |")

    print(f"+{divider}+\n")
