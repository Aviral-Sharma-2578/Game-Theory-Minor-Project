"""
main.py — Analysis Driver for the Asymmetric Escalation Game
Kilgour & Zagare (2007), "Explaining Limited Conflicts"

Orchestrates:
    1. Payoff table display
    2. Strategic scenario analysis (6 scenarios)
    3. Sensitivity analysis (credibility sweep)
    4. Stability map (4-zone heatmap + escalation risk overlay)
    5. Signaling analysis (audience costs & sunk costs)
"""

from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

from game_engine import GameConfig, Player, print_payoff_table
from scenarios import backward_induction, run_all_scenarios, print_scenario_results
from signaling import analyze_signaling_effect, print_signaling_analysis


# ===========================================================================
# 1. Sensitivity Analysis
# ===========================================================================

def sensitivity_analysis(steps: int = 11) -> np.ndarray:
    cred_values = [round(i / (steps - 1), 2) for i in range(steps)]
    grid = np.empty((steps, steps), dtype=object)
    for i, cd in enumerate(cred_values):
        for j, cc in enumerate(cred_values):
            r = backward_induction(GameConfig(credibility_defender=cd, credibility_challenger=cc))
            grid[i, j] = r.outcome

    col_w = 10
    header = f"{'':>{col_w}}" + "".join(f"{'Ch=' + str(c):^{col_w}}" for c in cred_values)
    div = "-" * len(header)
    print(f"\n{'SENSITIVITY ANALYSIS — Asymmetric Escalation Game':^{len(header)}}")
    print(f"{'(Defender Credibility × Challenger Credibility)':^{len(header)}}")
    print(div)
    print(header)
    print(div)
    for i, cd in enumerate(cred_values):
        cells = "".join(f"{grid[i, j]:^{col_w}}" for j in range(steps))
        print(f"{'Def=' + str(cd):>{col_w}}{cells}")
    print(div)
    return grid


# ===========================================================================
# 2. Stability Map — computes escalation risk per cell
# ===========================================================================

def _get_zone_and_esc_risk(config: GameConfig):
    """Compute the equilibrium zone and escalation risk for a credibility pair.

    Returns (zone_code, escalation_risk):
        zone 0 = SQ (Deterrence)
        zone 1 = DC (No Response)
        zone 2 = DD (Limited Conflict)
        zone 3 = DE/ED/EE (Escalatory)
        escalation_risk = probability mass on E-path outcomes
    """
    r = backward_induction(config)
    p = config.credibility_defender
    pCh = config.credibility_challenger

    if r.outcome == "SQ":
        # Even in SQ, compute what WOULD happen if Challenger initiated
        # This shows the deterrence mechanism
        pHH = p * p; pHS = p * (1-p); pSH = p * (1-p); pSS = (1-p)**2

        from game_engine import get_defender_payoff, get_challenger_payoff
        # Node 3b escalation
        ee_hard_c = get_challenger_payoff(config, "EE", True)
        de_c = get_challenger_payoff(config, "DE")
        prob_chal_esc_3b = pCh if ee_hard_c > de_c else 0
        ee_soft_c = get_challenger_payoff(config, "EE", False)
        if ee_soft_c > de_c:
            prob_chal_esc_3b += (1 - pCh)

        # E-path decisions at Node 2
        ee_hard_d = get_defender_payoff(config, "EE", is_str_hard=True)
        ee_soft_d = get_defender_payoff(config, "EE", is_str_hard=False)
        ed_d = get_defender_payoff(config, "ED")
        de_d = get_defender_payoff(config, "DE")
        dd_hard = get_defender_payoff(config, "DD", is_tac_hard=True)

        e_hh = prob_chal_esc_3b * ee_hard_d + (1-prob_chal_esc_3b) * de_d
        e_hs = prob_chal_esc_3b * ee_soft_d + (1-prob_chal_esc_3b) * de_d
        prob_E = (pHH if e_hh > dd_hard else 0) + (pHS if e_hs > dd_hard else 0)
        esc_risk = prob_E * prob_chal_esc_3b  # prob of EE given initiation
        return 0, esc_risk

    # For non-SQ outcomes, parse the reasoning for probabilities
    # Use the outcome directly
    if r.outcome == "DC":
        # Extract E probability from reasoning
        for line in r.reasoning.split("\n"):
            if "N2 probs" in line:
                parts = line.split("E=")
                if len(parts) > 1:
                    prob_e = float(parts[-1].strip())
                    return 1, prob_e
        return 1, 0.0
    elif r.outcome == "DD":
        return 2, 0.0
    else:
        return 3, 1.0


def generate_stability_map(steps=51, output_path="stability_map.png"):
    """Generate a rich stability map with 4 zones + escalation risk overlay."""
    cred_values = np.linspace(0, 1, steps)
    zone_grid = np.zeros((steps, steps), dtype=int)
    risk_grid = np.zeros((steps, steps), dtype=float)

    for i, cd in enumerate(cred_values):
        for j, cc in enumerate(cred_values):
            cfg = GameConfig(credibility_defender=float(cd), credibility_challenger=float(cc))
            zone, risk = _get_zone_and_esc_risk(cfg)
            zone_grid[i, j] = zone
            risk_grid[i, j] = risk

    # --- Plot 1: Zone map ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    cmap = ListedColormap(["#2ecc71", "#f39c12", "#3498db", "#e74c3c"])
    norm = BoundaryNorm([0, 1, 2, 3, 4], cmap.N)
    ax1.imshow(zone_grid, origin="lower", extent=[0,1,0,1], aspect="auto",
               cmap=cmap, norm=norm, interpolation="nearest")
    ax1.set_xlabel("Challenger (USA) Credibility pCh", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Defender (Iran) Credibility p", fontsize=12, fontweight="bold")
    ax1.set_title("Equilibrium Zones\n(Kilgour & Zagare, 2007)", fontsize=14, fontweight="bold")
    legend = [
        Patch(facecolor="#2ecc71", edgecolor="k", label="Deterrence (SQ)"),
        Patch(facecolor="#f39c12", edgecolor="k", label="No Response (DC)"),
        Patch(facecolor="#3498db", edgecolor="k", label="Limited Conflict (DD)"),
        Patch(facecolor="#e74c3c", edgecolor="k", label="Escalatory (DE/ED/EE)"),
    ]
    ax1.legend(handles=legend, loc="upper left", fontsize=10, framealpha=0.9)

    # --- Plot 2: Escalation risk heatmap ---
    im = ax2.imshow(risk_grid, origin="lower", extent=[0,1,0,1], aspect="auto",
                    cmap="YlOrRd", vmin=0, vmax=1, interpolation="bilinear")
    ax2.set_xlabel("Challenger (USA) Credibility pCh", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Defender (Iran) Credibility p", fontsize=12, fontweight="bold")
    ax2.set_title("Escalation Risk\n(Prob. of E-path outcomes)", fontsize=14, fontweight="bold")
    fig.colorbar(im, ax=ax2, label="Escalation Risk", shrink=0.8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    print(f"\n[OK] Stability map saved to: {output_path}")


# ===========================================================================
# 3. Main entry-point
# ===========================================================================

def main() -> None:
    print("=" * 75)
    print("  ASYMMETRIC ESCALATION GAME — STRATEGIC DETERRENCE SIMULATION")
    print("  Based on Kilgour & Zagare (2007), Perfect Deterrence Theory")
    print("=" * 75)

    base = GameConfig()
    print("\n[1/5] PAYOFF TABLE")
    print_payoff_table(base)

    print("[2/5] STRATEGIC SCENARIO ANALYSIS")
    results = run_all_scenarios(base)
    print_scenario_results(results)

    print("[3/5] SENSITIVITY ANALYSIS")
    sensitivity_analysis(steps=11)

    print("\n[4/5] GENERATING STABILITY MAP ...")
    generate_stability_map(steps=51, output_path="stability_map.png")

    print("\n[5/5] SIGNALING ANALYSIS")
    for player, label in [(Player.DEFENDER, "USA"), (Player.CHALLENGER, "Iran")]:
        for mech in ["audience_cost", "sunk_cost"]:
            results = analyze_signaling_effect(base, player, mechanism=mech)
            print_signaling_analysis(results)

    print("\n" + "=" * 75)
    print("  SIMULATION COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()
