"""
main.py — Analysis Driver for the Two-Stage Strategic Deterrence Game

Orchestrates:
    1. Payoff table display
    2. Strategic scenario analysis (4 scenarios)
    3. Sensitivity analysis (credibility sweep 0.0–1.0)
    4. Stability map (matplotlib heatmap)
    5. Signaling analysis (audience costs & sunk costs)

Usage:
    python main.py
"""

from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")                    # non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

from game_engine import GameConfig, Player, print_payoff_table
from scenarios import (
    backward_induction,
    run_all_scenarios,
    print_scenario_results,
)
from signaling import (
    analyze_signaling_effect,
    print_signaling_analysis,
)


# ===========================================================================
# 1. Sensitivity Analysis
# ===========================================================================

def sensitivity_analysis(
    steps: int = 11,
) -> np.ndarray:
    """Sweep USA and Iran credibility from 0.0 to 1.0.

    Returns an (steps × steps) array of equilibrium labels.
    Also prints a formatted ASCII table.
    """
    cred_values = [round(i / (steps - 1), 2) for i in range(steps)]
    grid = np.empty((steps, steps), dtype=object)

    for i, cred_usa in enumerate(cred_values):
        for j, cred_iran in enumerate(cred_values):
            cfg = GameConfig(
                credibility_usa=cred_usa,
                credibility_iran=cred_iran,
            )
            result = backward_induction(cfg)
            label = f"{result.equilibrium[0]},{result.equilibrium[1]}"
            grid[i, j] = label

    # --- Pretty-print table ---
    col_w = 12
    header = f"{'':>{col_w}}" + "".join(f"{'Iran=' + str(c):^{col_w}}" for c in cred_values)
    divider = "-" * len(header)

    print(f"\n{'SENSITIVITY ANALYSIS - Nash Equilibria':^{len(header)}}")
    print(f"{'(USA Credibility x Iran Credibility)':^{len(header)}}")
    print(divider)
    print(header)
    print(divider)

    for i, cred_usa in enumerate(cred_values):
        row_label = f"USA={cred_usa:<5}"
        cells = "".join(f"{grid[i, j]:^{col_w}}" for j in range(steps))
        print(f"{row_label:>{col_w}}{cells}")

    print(divider)
    return grid


# ===========================================================================
# 2. Stability Map (matplotlib)
# ===========================================================================

def _classify_outcome(label: str) -> int:
    """Map equilibrium label → zone code for the heatmap.

    0 = Mutual Deterrence (CC)
    1 = Conventional Conflict (CD / DC / DD without nuclear)
    2 = Nuclear Conflict (contains E)
    """
    if label == "C,C":
        return 0
    if "E" in label:
        return 2
    return 1


def generate_stability_map(
    steps: int = 51,
    output_path: str = "stability_map.png",
) -> None:
    """Generate and save a colour-coded stability heatmap.

    Axes: Iran credibility (x) vs USA credibility (y).
    Zones:
        Green  — Mutual Deterrence (CC)
        Gold   — Conventional Conflict
        Red    — Nuclear Conflict
    """
    cred_values = np.linspace(0, 1, steps)
    zone_grid = np.zeros((steps, steps), dtype=int)

    for i, cred_usa in enumerate(cred_values):
        for j, cred_iran in enumerate(cred_values):
            cfg = GameConfig(
                credibility_usa=float(cred_usa),
                credibility_iran=float(cred_iran),
            )
            result = backward_induction(cfg)
            label = f"{result.equilibrium[0]},{result.equilibrium[1]}"
            zone_grid[i, j] = _classify_outcome(label)

    # --- Plotting ---
    fig, ax = plt.subplots(figsize=(10, 8))

    cmap = ListedColormap(["#2ecc71", "#f39c12", "#e74c3c"])
    norm = BoundaryNorm([0, 1, 2, 3], cmap.N)

    im = ax.imshow(
        zone_grid,
        origin="lower",
        extent=[0, 1, 0, 1],
        aspect="auto",
        cmap=cmap,
        norm=norm,
        interpolation="nearest",
    )

    ax.set_xlabel("Iran Credibility", fontsize=13, fontweight="bold")
    ax.set_ylabel("USA Credibility", fontsize=13, fontweight="bold")
    ax.set_title(
        "Stability Map - Two-Stage Deterrence Game\n"
        "(Zagare 1992 / Kraig 1999)",
        fontsize=15,
        fontweight="bold",
        pad=14,
    )
    ax.tick_params(labelsize=11)

    legend_elements = [
        Patch(facecolor="#2ecc71", edgecolor="black", label="Mutual Deterrence (CC)"),
        Patch(facecolor="#f39c12", edgecolor="black", label="Conventional Conflict"),
        Patch(facecolor="#e74c3c", edgecolor="black", label="Nuclear Conflict"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="upper left",
        fontsize=11,
        framealpha=0.9,
        edgecolor="black",
    )

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    print(f"\n[OK] Stability map saved to: {output_path}")


# ===========================================================================
# 3. Main entry-point
# ===========================================================================

def main() -> None:
    print("=" * 70)
    print("  TWO-STAGE STRATEGIC DETERRENCE GAME SIMULATION")
    print("  Based on Zagare (1992) & Kraig (1999)")
    print("=" * 70)

    base = GameConfig()

    # --- Payoff table ---
    print("\n[1/5] PAYOFF TABLE")
    print_payoff_table(base)

    # --- Strategic scenarios ---
    print("[2/5] STRATEGIC SCENARIO ANALYSIS")
    results = run_all_scenarios(base)
    print_scenario_results(results)

    # --- Sensitivity analysis ---
    print("[3/5] SENSITIVITY ANALYSIS")
    sensitivity_analysis(steps=11)

    # --- Stability map ---
    print("\n[4/5] GENERATING STABILITY MAP ...")
    generate_stability_map(steps=51, output_path="stability_map.png")

    # --- Signaling analysis ---
    print("\n[5/5] SIGNALING ANALYSIS")

    # Audience costs — USA
    ac_usa = analyze_signaling_effect(
        base, Player.USA, mechanism="audience_cost"
    )
    print_signaling_analysis(ac_usa)

    # Audience costs — Iran
    ac_iran = analyze_signaling_effect(
        base, Player.IRAN, mechanism="audience_cost"
    )
    print_signaling_analysis(ac_iran)

    # Sunk costs — USA
    sc_usa = analyze_signaling_effect(
        base, Player.USA, mechanism="sunk_cost"
    )
    print_signaling_analysis(sc_usa)

    # Sunk costs — Iran
    sc_iran = analyze_signaling_effect(
        base, Player.IRAN, mechanism="sunk_cost"
    )
    print_signaling_analysis(sc_iran)

    print("\n" + "=" * 70)
    print("  SIMULATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
