"""
scenarios.py — Strategic Scenarios & Backward-Induction Solver

Implements a two-stage backward-induction solver and four canonical
strategic scenarios from the deterrence literature:

    1. Called Bluff
    2. Rational Irrationality (Madman Theory)
    3. Asymmetric Capability
    4. First-Strike Advantage

Game Model (Zagare 1992 / Kraig 1999):
    Stage 1: Each player chooses Cooperate (C) or Defect (D).
    Stage 2: If a player is exploited (opponent defects), the exploited
             player may threaten nuclear Escalation (E).  The credibility
             of that threat determines whether the defector backs down.

    - A player defects only if they believe the opponent's retaliatory
      nuclear threat is NOT credible enough to deter them.
    - High credibility of Player X → opponent is deterred from defecting
      against X → Cooperation (CC).
    - Low credibility → opponent defects → Conventional or Nuclear
      conflict.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Tuple

from game_engine import Action, GameConfig, Player, get_payoffs


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    """Container for a single scenario analysis."""
    name: str
    description: str
    config: GameConfig
    equilibrium: Tuple[str, str]          # (usa_strategy, iran_strategy)
    payoffs: Tuple[float, float]          # (usa_payoff, iran_payoff)
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Backward-Induction Solver
# ---------------------------------------------------------------------------

def _solve_nuclear_subgame(config: GameConfig) -> Tuple[str, str, float, float]:
    """Stage 2: solve the nuclear escalation sub-game.

    Each player decides whether to Escalate (E) or Defect (D) in the
    nuclear stage.  A player escalates only if the expected payoff of
    escalation (weighted by opponent's credibility) exceeds defection.

    Returns
    -------
    (usa_nuc_action, iran_nuc_action, usa_payoff, iran_payoff)
    """
    ee = get_payoffs(config, "E", "E")
    ed = get_payoffs(config, "E", "D")
    de = get_payoffs(config, "D", "E")
    dd = get_payoffs(config, "D", "D")

    # USA's nuclear decision
    usa_esc_ev = (config.credibility_iran * ee[0]
                  + (1 - config.credibility_iran) * ed[0])
    usa_def_ev = (config.credibility_iran * de[0]
                  + (1 - config.credibility_iran) * dd[0])
    usa_nuc = "E" if usa_esc_ev > usa_def_ev else "D"

    # Iran's nuclear decision
    if not config.iran_has_nuclear:
        iran_nuc = "D"
    else:
        iran_esc_ev = (config.credibility_usa * ee[1]
                       + (1 - config.credibility_usa) * de[1])
        iran_def_ev = (config.credibility_usa * ed[1]
                       + (1 - config.credibility_usa) * dd[1])
        iran_nuc = "E" if iran_esc_ev > iran_def_ev else "D"

    payoff = get_payoffs(config, usa_nuc, iran_nuc)
    return usa_nuc, iran_nuc, payoff[0], payoff[1]


def backward_induction(config: GameConfig) -> ScenarioResult:
    """Full two-stage backward-induction solver.

    Decision Model:
        Each player must choose whether to Defect (seize the initiative)
        or Cooperate (maintain the status quo).

        Temptation to defect:
            - Iran's best outcome is DC (Iran defects, USA cooperates) = 4
            - USA's best outcome is CD (USA cooperates, Iran defects) = 4
            - But defecting risks triggering the opponent's nuclear threat.

        Expected payoff of defecting for IRAN:
            - With prob (1 - cred_usa): USA's threat is a bluff, Iran gets
              its best outcome DC = 4.
            - With prob (cred_usa): USA retaliates (nuclear subgame).

        Expected payoff of cooperating for IRAN:
            - With prob (1 - cred_iran): USA defects (since Iran's threat
              isn't credible), Iran gets CD = 1.  But Iran is not choosing
              USA's action — we model this as: if Iran cooperates, the
              outcome depends on what USA does independently.

        We solve simultaneously: each player's best response considers
        the expected nuclear consequences of mutual defection.
    """
    # ------ Stage 2: nuclear sub-game ------
    usa_nuc, iran_nuc, nuc_usa_pay, nuc_iran_pay = _solve_nuclear_subgame(config)

    # ------ Stage 1: deterrence calculus ------
    cc = get_payoffs(config, "C", "C")  # (3, 3)
    cd = get_payoffs(config, "C", "D")  # (1, 4)  USA's worst / Iran's best
    dc = get_payoffs(config, "D", "C")  # (4, 1)  USA's best / Iran's worst
    dd = get_payoffs(config, "D", "D")  # (2, 2)  conventional mutual defect

    # Nuclear-escalation expected payoff when both defect (DD → nuclear risk)
    # The probability of nuclear escalation given DD is the product of
    # willingness. We use max(cred_usa, cred_iran) as the escalation risk.
    esc_prob = max(config.credibility_usa, config.credibility_iran)
    dd_eff = (
        (1 - esc_prob) * dd[0] + esc_prob * nuc_usa_pay,
        (1 - esc_prob) * dd[1] + esc_prob * nuc_iran_pay,
    )

    # --- IRAN's decision: Defect or Cooperate ---
    # If Iran defects:
    #   - USA may retaliate (escalate). With prob = cred_usa, USA retaliates
    #     and the outcome is the nuclear subgame payoff for Iran.
    #   - With prob = (1 - cred_usa), USA does NOT retaliate, and Iran
    #     gets its best outcome CD (USA cooperates, Iran defects).
    iran_ev_defect = (
        (1 - config.credibility_usa) * cd[1]    # Iran exploits USA
        + config.credibility_usa * dd_eff[1]      # USA retaliates → nuclear risk
    )
    iran_ev_cooperate = cc[1]   # Mutual cooperation

    iran_action = "D" if iran_ev_defect > iran_ev_cooperate else "C"

    # --- USA's decision: Defect or Cooperate ---
    # If USA defects:
    #   - Iran may retaliate. With prob = cred_iran, Iran retaliates.
    #   - With prob = (1 - cred_iran), Iran backs down, USA gets CD payoff
    #     (but wait: CD = USA cooperates, Iran defects = 4 for USA)
    #     Actually, if USA defects and Iran doesn't retaliate, the outcome
    #     is DC from USA's perspective = 1 (worst for USA).
    #
    # KEY INSIGHT: USA's preference ordering is CD > CC > DD > DC.
    # USA defecting gives DC = 1 (worst) if Iran cooperates!
    # So USA has NO incentive to defect unilaterally under these preferences.
    #
    # The correct interpretation: USA "defects" means it launches a
    # conventional strike. If Iran's nuclear threat is credible, this is
    # dangerous. But USA's temptation to defect arises from foreign policy
    # coercion — not from the payoff structure directly.
    #
    # For the model to work properly, we interpret the actions relative to
    # each player's TEMPTATION payoff structure:
    usa_ev_defect = (
        (1 - config.credibility_iran) * dc[0]    # USA defects, Iran can't retaliate
        + config.credibility_iran * dd_eff[0]      # Iran retaliates → nuclear risk
    )
    usa_ev_cooperate = cc[0]   # Mutual cooperation

    usa_action = "D" if usa_ev_defect > usa_ev_cooperate else "C"

    # --- Build strategy labels ---
    usa_strat = usa_action
    iran_strat = iran_action
    if usa_action == "D" and iran_action == "D":
        usa_strat = f"D->{usa_nuc}"
        iran_strat = f"D->{iran_nuc}"

    # Resolve final payoffs
    if usa_action == "D" and iran_action == "D":
        final_payoffs = dd_eff
    elif usa_action == "D" and iran_action == "C":
        final_payoffs = dc
    elif usa_action == "C" and iran_action == "D":
        final_payoffs = cd
    else:
        final_payoffs = cc

    reasoning = (
        f"Nuclear sub-game: USA={usa_nuc}, Iran={iran_nuc} "
        f"(payoff: {nuc_usa_pay:.2f}, {nuc_iran_pay:.2f})\n"
        f"  DD effective payoff: ({dd_eff[0]:.2f}, {dd_eff[1]:.2f})\n"
        f"  USA: EV(C)={usa_ev_cooperate:.2f}  EV(D)={usa_ev_defect:.2f} "
        f"-> {'D' if usa_ev_defect > usa_ev_cooperate else 'C'}\n"
        f"  Iran: EV(C)={iran_ev_cooperate:.2f}  EV(D)={iran_ev_defect:.2f} "
        f"-> {'D' if iran_ev_defect > iran_ev_cooperate else 'C'}\n"
        f"  -> Equilibrium: ({usa_strat}, {iran_strat})"
    )

    return ScenarioResult(
        name="Backward Induction",
        description="Full two-stage backward-induction equilibrium.",
        config=config,
        equilibrium=(usa_strat, iran_strat),
        payoffs=final_payoffs,
        reasoning=reasoning,
    )


# ---------------------------------------------------------------------------
# Scenario 1 — The Called Bluff
# ---------------------------------------------------------------------------

def called_bluff(base_config: GameConfig | None = None) -> ScenarioResult:
    """One player's nuclear threat lacks credibility, opponent exploits it.

    Sets USA credibility low, so Iran's opponent (USA) has a non-credible
    threat. Iran exploits this by defecting.
    """
    cfg = deepcopy(base_config) if base_config else GameConfig()
    cfg.credibility_usa = 0.1    # USA's nuclear threat is not credible
    cfg.credibility_iran = 0.9   # Iran's threat IS credible

    result = backward_induction(cfg)
    result.name = "Called Bluff"
    result.description = (
        "USA's nuclear threat is not credible (cred=0.1). "
        "Iran calls the bluff and defects, seizing first-mover advantage."
    )
    return result


# ---------------------------------------------------------------------------
# Scenario 2 — Rational Irrationality (Madman Theory)
# ---------------------------------------------------------------------------

def rational_irrationality(base_config: GameConfig | None = None) -> ScenarioResult:
    """Iran appears irrational, making its nuclear threat credible.

    Iran adopts a 'madman' posture with very high apparent credibility,
    deterring USA from aggression.
    """
    cfg = deepcopy(base_config) if base_config else GameConfig()
    cfg.credibility_iran = 0.95   # Iran appears willing to escalate
    cfg.credibility_usa = 0.3     # USA is restrained

    result = backward_induction(cfg)
    result.name = "Rational Irrationality"
    result.description = (
        "Iran projects near-certain willingness to escalate (cred=0.95). "
        "The 'Madman Theory' deters USA from conventional aggression."
    )
    return result


# ---------------------------------------------------------------------------
# Scenario 3 — Asymmetric Capability
# ---------------------------------------------------------------------------

def asymmetric_capability(
    base_config: GameConfig | None = None,
) -> Tuple[ScenarioResult, ScenarioResult]:
    """Model equilibrium shift as Iran gains nuclear capability.

    Returns two results: (non_nuclear_iran, nuclear_iran).
    """
    # Sub-scenario A: Iran is non-nuclear
    cfg_a = deepcopy(base_config) if base_config else GameConfig()
    cfg_a.iran_has_nuclear = False
    cfg_a.credibility_usa = 0.7
    cfg_a.credibility_iran = 0.3

    result_a = backward_induction(cfg_a)
    result_a.name = "Asymmetric - Iran Non-Nuclear"
    result_a.description = (
        "Iran lacks nuclear capability. USA enjoys escalation dominance."
    )

    # Sub-scenario B: Iran acquires nuclear weapons
    cfg_b = deepcopy(base_config) if base_config else GameConfig()
    cfg_b.iran_has_nuclear = True
    cfg_b.credibility_usa = 0.7
    cfg_b.credibility_iran = 0.7

    result_b = backward_induction(cfg_b)
    result_b.name = "Asymmetric - Iran Nuclear"
    result_b.description = (
        "Iran acquires nuclear capability with matched credibility. "
        "Symmetric threats stabilize toward mutual deterrence."
    )

    return result_a, result_b


# ---------------------------------------------------------------------------
# Scenario 4 — First-Strike Advantage
# ---------------------------------------------------------------------------

def first_strike_advantage(base_config: GameConfig | None = None) -> ScenarioResult:
    """A positive first-strike bonus shifts equilibrium toward preemption.

    Introduces a payoff premium for the player who escalates first.
    """
    cfg = deepcopy(base_config) if base_config else GameConfig()
    cfg.first_strike_bonus = 3.0
    cfg.credibility_usa = 0.6
    cfg.credibility_iran = 0.6

    result = backward_induction(cfg)
    result.name = "First-Strike Advantage"
    result.description = (
        f"First-strike bonus = {cfg.first_strike_bonus}. "
        "Increased payoff for the initial attacker creates preemption incentive."
    )
    return result


# ---------------------------------------------------------------------------
# Convenience: run all scenarios
# ---------------------------------------------------------------------------

def run_all_scenarios(
    base_config: GameConfig | None = None,
) -> List[ScenarioResult]:
    """Execute all four canonical scenarios and return results."""
    results: List[ScenarioResult] = []

    results.append(called_bluff(base_config))
    results.append(rational_irrationality(base_config))

    asym_a, asym_b = asymmetric_capability(base_config)
    results.append(asym_a)
    results.append(asym_b)

    results.append(first_strike_advantage(base_config))

    return results


def print_scenario_results(results: List[ScenarioResult]) -> None:
    """Pretty-print scenario results to stdout."""
    divider = "=" * 65

    print(f"\n+{divider}+")
    print(f"|{'STRATEGIC SCENARIO ANALYSIS':^65}|")
    print(f"+{divider}+")

    for r in results:
        print(f"|  Scenario : {r.name:<51}|")

        # Word-wrap description at 61 chars
        desc = r.description
        while desc:
            chunk = desc[:61]
            desc = desc[61:]
            print(f"|  {chunk:<63}|")

        print(f"|  Equilibrium : ({r.equilibrium[0]}, {r.equilibrium[1]})"
              f"{'':>{42 - len(r.equilibrium[0]) - len(r.equilibrium[1])}}|")
        print(f"|  Payoffs     : USA={r.payoffs[0]:>6.2f}  Iran={r.payoffs[1]:>6.2f}"
              f"{'':>24}|")
        print(f"|  Credibility : USA={r.config.credibility_usa:.2f}  "
              f"Iran={r.config.credibility_iran:.2f}"
              f"{'':>26}|")
        print(f"|  Reasoning   :{'':>50}|")
        for line in r.reasoning.split("\n"):
            if len(line) > 63:
                line = line[:60] + "..."
            print(f"|    {line:<61}|")
        print(f"+{divider}+")

    print()
