"""
scenarios.py — Backward-Induction Solver for the Asymmetric Escalation Game
Kilgour & Zagare (2007), "Explaining Limited Conflicts"

Key fix: Each Defender type (HH, HS, SH, SS) independently evaluates
C/D/E at Node 2 using its OWN type-specific EE and DD payoffs.
"""

from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from typing import List, Tuple
from game_engine import (
    GameConfig, Player,
    get_challenger_payoff, get_defender_payoff, get_outcome_payoffs,
)


@dataclass
class ScenarioResult:
    name: str
    description: str
    config: GameConfig
    equilibrium: Tuple[str, ...]
    outcome: str
    payoffs: Tuple[float, float]
    reasoning: str = ""


def backward_induction(config: GameConfig) -> ScenarioResult:
    """Full backward-induction solver with per-type decisions."""
    p = config.credibility_defender
    pCh = config.credibility_challenger

    # Defender type probabilities (paper's single-parameter model)
    pHH = p * p
    pHS = p * (1 - p)
    pSH = p * (1 - p)
    pSS = (1 - p) ** 2

    # ===== Node 3b: Challenger decides E or D after Defender chose E =====
    # Hard Chal: EE_hard_c vs DE_c
    # Soft Chal: EE_soft_c vs DE_c
    de_c = get_challenger_payoff(config, "DE")
    ee_hard_c = get_challenger_payoff(config, "EE", is_hard=True)
    ee_soft_c = get_challenger_payoff(config, "EE", is_hard=False)
    hard_chal_esc_3b = ee_hard_c > de_c   # True with defaults: 25 > 20
    soft_chal_esc_3b = ee_soft_c > de_c   # False with defaults: 0 < 20
    prob_chal_esc_3b = (pCh if hard_chal_esc_3b else 0) + ((1-pCh) if soft_chal_esc_3b else 0)

    # ===== Node 2 E-path: per-Defender-type expected payoffs =====
    de_d = get_defender_payoff(config, "DE")

    def e_path_ev_def(is_str_hard):
        """E-path expected payoff for a specific Defender type."""
        ee_d = get_defender_payoff(config, "EE", is_str_hard=is_str_hard)
        return prob_chal_esc_3b * ee_d + (1 - prob_chal_esc_3b) * de_d

    e_path_HH = e_path_ev_def(is_str_hard=True)   # HH Defender's E-path EV
    e_path_HS = e_path_ev_def(is_str_hard=False)   # HS Defender's E-path EV
    e_path_SH = e_path_ev_def(is_str_hard=True)    # SH: strat hard
    e_path_SS = e_path_ev_def(is_str_hard=False)   # SS: strat soft

    # E-path expected payoff for Challenger (same regardless of Def type)
    e_path_chal = prob_chal_esc_3b * (pCh * ee_hard_c + (1-pCh) * ee_soft_c) + \
                  (1 - prob_chal_esc_3b) * de_c

    # ===== Node 4: Defender decides E or D after Challenger escalated at 3a =====
    ed_d = get_defender_payoff(config, "ED")
    ee_hard_d_n4 = get_defender_payoff(config, "EE", is_str_hard=True)
    ee_soft_d_n4 = get_defender_payoff(config, "EE", is_str_hard=False)
    # At Node 4, Defender is known to be Tact Hard (chose D at Node 2)
    # Among Tact Hard: HH with conditional prob p, HS with prob (1-p)
    # (conditional on being Tact Hard: pHH/(pHH+pHS) = p²/(p²+p(1-p)) = p)
    prob_def_esc_n4 = p if ee_hard_d_n4 > ed_d else 0  # only HH escalates if EE_hard > ED
    if ee_soft_d_n4 > ed_d:
        prob_def_esc_n4 += (1 - p)  # HS also escalates

    # ===== Node 3a: Challenger decides E or D after Defender responded-in-kind =====
    dd_c = get_challenger_payoff(config, "DD")
    ed_c = get_challenger_payoff(config, "ED")

    # Hard Chal at Node 3a: EV(E) = prob_def_esc_n4 * EE_hard_c + (1-prob)*ED_c vs DD_c
    hard_chal_ev_esc_3a = prob_def_esc_n4 * ee_hard_c + (1 - prob_def_esc_n4) * ed_c
    hard_chal_esc_3a = hard_chal_ev_esc_3a > dd_c

    soft_chal_ev_esc_3a = prob_def_esc_n4 * ee_soft_c + (1 - prob_def_esc_n4) * ed_c
    soft_chal_esc_3a = soft_chal_ev_esc_3a > dd_c

    prob_chal_esc_3a = (pCh if hard_chal_esc_3a else 0) + ((1-pCh) if soft_chal_esc_3a else 0)

    # ===== Node 2 D-path: per-Defender-type expected payoffs =====
    dd_hard_d = get_defender_payoff(config, "DD", is_tac_hard=True)

    # If Chal escalates at 3a → Node 4
    # Node 4 EV for HH Def: EE_hard(30) if escalates, ED(20) if not
    n4_ev_HH = ee_hard_d_n4 if ee_hard_d_n4 > ed_d else ed_d
    n4_ev_HS = ee_soft_d_n4 if ee_soft_d_n4 > ed_d else ed_d

    d_path_HH = prob_chal_esc_3a * n4_ev_HH + (1 - prob_chal_esc_3a) * dd_hard_d
    d_path_HS = prob_chal_esc_3a * n4_ev_HS + (1 - prob_chal_esc_3a) * dd_hard_d

    # D-path expected payoff for Challenger
    n4_chal_ev = prob_def_esc_n4 * (pCh*ee_hard_c+(1-pCh)*ee_soft_c) + \
                 (1 - prob_def_esc_n4) * ed_c
    d_path_chal = prob_chal_esc_3a * n4_chal_ev + (1 - prob_chal_esc_3a) * dd_c

    # ===== Node 2: Each Defender type decides independently =====
    dc_d = get_defender_payoff(config, "DC")
    dc_c = get_challenger_payoff(config, "DC")

    # Tactically Soft types (SH, SS) always capitulate → C
    # Tactically Hard types (HH, HS) choose best of {D, E}
    # (They never choose C because DD_hard(60) > DC(50) and DE(90) > DC(50))

    if not config.defender_can_escalate:
        hh_action = "D"
        hs_action = "D"
    else:
        hh_action = "E" if e_path_HH > d_path_HH else "D"
        hs_action = "E" if e_path_HS > d_path_HS else "D"

    # Aggregate: probability of each action at Node 2
    prob_C = pSS + pSH   # = (1-p)
    prob_D = (pHH if hh_action == "D" else 0) + (pHS if hs_action == "D" else 0)
    prob_E = (pHH if hh_action == "E" else 0) + (pHS if hs_action == "E" else 0)

    # Expected payoff for Challenger at Node 2
    chal_ev_node2 = prob_C * dc_c + prob_D * d_path_chal + prob_E * e_path_chal
    # Expected payoff for Defender at Node 2
    def_ev_node2 = prob_C * dc_d + \
                   (pHH if hh_action == "D" else 0) * d_path_HH + \
                   (pHS if hs_action == "D" else 0) * d_path_HS + \
                   (pHH if hh_action == "E" else 0) * e_path_HH + \
                   (pHS if hs_action == "E" else 0) * e_path_HS

    # ===== Node 1: Challenger decides C or D =====
    sq_c = get_challenger_payoff(config, "SQ")
    sq_d = get_defender_payoff(config, "SQ")
    chal_action = "D" if chal_ev_node2 > sq_c else "C"

    # Determine outcome by computing probability of each terminal outcome
    if chal_action == "C":
        outcome = "SQ"
        eq_pay = (sq_d, sq_c)
    else:
        eq_pay = (def_ev_node2, chal_ev_node2)

        # Probability of each terminal outcome given Challenger initiates:
        # DC: Defender capitulates (Tac Soft types)
        p_DC = prob_C
        # D-path outcomes (Tac Hard types that choose D)
        p_DD = prob_D * (1 - prob_chal_esc_3a)
        p_ED = prob_D * prob_chal_esc_3a * (1 - prob_def_esc_n4)
        p_EE_via_D = prob_D * prob_chal_esc_3a * prob_def_esc_n4
        # E-path outcomes (Tac Hard types that choose E)
        p_DE = prob_E * (1 - prob_chal_esc_3b)
        p_EE_via_E = prob_E * prob_chal_esc_3b
        p_EE = p_EE_via_D + p_EE_via_E

        # Pick the most probable outcome
        outcome_probs = {"DC": p_DC, "DD": p_DD, "ED": p_ED, "DE": p_DE, "EE": p_EE}
        outcome = max(outcome_probs, key=outcome_probs.get)

    # Strategy labels
    if chal_action == "C":
        c_strat, d_strat = "C", "-"
    else:
        # Defender's most likely action
        if prob_E > prob_D and prob_E > prob_C:
            d_strat = "E"
            c_strat = f"D→{'E' if prob_chal_esc_3b > 0.5 else 'D'}"
        elif prob_D > prob_C:
            d_strat = "D"
            c_strat = f"D→{'E' if prob_chal_esc_3a > 0.5 else 'D'}"
        else:
            d_strat = "C"
            c_strat = "D"

    reasoning = (
        f"Path → {outcome}\n"
        f"  Types: HH={pHH:.2f} HS={pHS:.2f} SH={pSH:.2f} SS={pSS:.2f}\n"
        f"  N3b: Chal esc prob={prob_chal_esc_3b:.2f} (Hard EE+={ee_hard_c:.0f} vs DE={de_c:.0f})\n"
        f"  N4: Def esc prob={prob_def_esc_n4:.2f} (Hard EE+={ee_hard_d_n4:.0f} vs ED={ed_d:.0f})\n"
        f"  N3a: Chal esc prob={prob_chal_esc_3a:.2f} (Hard EV={hard_chal_ev_esc_3a:.1f} vs DD={dd_c:.0f})\n"
        f"  N2 HH: D={d_path_HH:.1f} E={e_path_HH:.1f} →{hh_action}\n"
        f"  N2 HS: D={d_path_HS:.1f} E={e_path_HS:.1f} →{hs_action}\n"
        f"  N2 probs: C={prob_C:.2f} D={prob_D:.2f} E={prob_E:.2f}\n"
        f"  N1: EV(D)={chal_ev_node2:.2f} EV(C)={sq_c:.2f} →{chal_action}"
    )

    return ScenarioResult(
        name="Backward Induction", description="Asymmetric Escalation Game.",
        config=config, equilibrium=(c_strat, d_strat),
        outcome=outcome, payoffs=eq_pay, reasoning=reasoning,
    )


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def called_bluff(base_config=None) -> ScenarioResult:
    cfg = deepcopy(base_config) if base_config else GameConfig()
    cfg.credibility_defender = 0.1
    cfg.credibility_challenger = 0.9
    r = backward_induction(cfg)
    r.name = "Called Bluff"
    r.description = "Defender's threat not credible (p=0.1). Challenger initiates."
    return r

def rational_irrationality(base_config=None) -> ScenarioResult:
    cfg = deepcopy(base_config) if base_config else GameConfig()
    cfg.credibility_challenger = 0.95
    cfg.credibility_defender = 0.3
    r = backward_induction(cfg)
    r.name = "Rational Irrationality"
    r.description = "Challenger projects near-certain willingness to escalate (pCh=0.95)."
    return r

def asymmetric_capability(base_config=None) -> Tuple[ScenarioResult, ScenarioResult]:
    cfg_a = deepcopy(base_config) if base_config else GameConfig()
    cfg_a.challenger_can_escalate = False
    cfg_a.credibility_defender = 0.7
    cfg_a.credibility_challenger = 0.3
    a = backward_induction(cfg_a)
    a.name = "Asymmetric - Non-Nuclear"
    a.description = "Challenger lacks nuclear capability. Defender has escalation dominance."

    cfg_b = deepcopy(base_config) if base_config else GameConfig()
    cfg_b.credibility_defender = 0.7
    cfg_b.credibility_challenger = 0.7
    b = backward_induction(cfg_b)
    b.name = "Asymmetric - Nuclear"
    b.description = "Challenger acquires nukes with matched credibility."
    return a, b

def first_strike_advantage(base_config=None) -> ScenarioResult:
    cfg = deepcopy(base_config) if base_config else GameConfig()
    cfg.first_strike_bonus = 30.0
    cfg.credibility_defender = 0.6
    cfg.credibility_challenger = 0.6
    r = backward_induction(cfg)
    r.name = "First-Strike Advantage"
    r.description = f"First-strike bonus={cfg.first_strike_bonus}. Preemption incentive."
    return r

def limited_conflict_scenario(base_config=None) -> ScenarioResult:
    cfg = deepcopy(base_config) if base_config else GameConfig()
    cfg.credibility_defender = 0.55
    cfg.credibility_challenger = 0.4
    r = backward_induction(cfg)
    r.name = "Limited Conflict Emergence"
    r.description = "Constrained Limited-Response Equilibrium (Kilgour & Zagare)."
    return r

def run_all_scenarios(base_config=None) -> List[ScenarioResult]:
    results = [called_bluff(base_config), rational_irrationality(base_config)]
    a, b = asymmetric_capability(base_config)
    results.extend([a, b, first_strike_advantage(base_config),
                    limited_conflict_scenario(base_config)])
    return results

def print_scenario_results(results: List[ScenarioResult]) -> None:
    div = "=" * 72
    print(f"\n+{div}+")
    print(f"|{'STRATEGIC SCENARIO ANALYSIS — Asymmetric Escalation Game':^72}|")
    print(f"|{'(Kilgour & Zagare, 2007)':^72}|")
    print(f"+{div}+")
    for r in results:
        print(f"|  Scenario : {r.name:<58}|")
        desc = r.description
        while desc:
            print(f"|  {desc[:68]:<70}|")
            desc = desc[68:]
        eq = f"Chal={r.equilibrium[0]}, Def={r.equilibrium[1]}"
        print(f"|  Equilibrium : {eq:<56}|")
        print(f"|  Outcome     : {r.outcome:<56}|")
        print(f"|  Payoffs     : Def={r.payoffs[0]:>7.2f}  Chal={r.payoffs[1]:>7.2f}{'':>26}|")
        print(f"|  Credibility : Def={r.config.credibility_defender:.2f}  "
              f"Chal={r.config.credibility_challenger:.2f}{'':>34}|")
        print(f"|  Reasoning   :{'':>57}|")
        for line in r.reasoning.split("\n"):
            print(f"|    {line[:68]:<68}|")
        print(f"+{div}+")
    print()
