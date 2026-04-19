# Two-Stage Strategic Deterrence Game — Complete Walkthrough

## Overview

This project is a **Python simulation of a two-player, two-stage nuclear deterrence game** between the USA and Iran, based on the academic models of:
- **Zagare (1992)** — Perfect Deterrence Theory
- **Kraig (1999)** — Extended Deterrence and the nuclear shadow

The simulation models real-world strategic questions: *When does a nuclear threat deter aggression? When is it "called a bluff"? Does acquiring nuclear weapons stabilize or destabilize a conflict?*

---

## Project Architecture

```
Game Theory/
├── game_engine.py   — Core data model, payoff functions
├── scenarios.py     — Backward-induction solver + 4 canonical scenarios
├── signaling.py     — Commitment mechanisms (audience costs, sunk costs)
├── main.py          — Orchestrator: runs all 5 analysis phases
└── output.txt       — Full simulation output (with stability_map.png)
```

---

## Game Theory Concepts

### 1. Extensive-Form Game (Two Stages)

This is an **extensive-form game** — players move sequentially, and earlier decisions constrain later ones.

| Stage | Decision | Actions |
|-------|----------|---------|
| Stage 1 | Conventional | C (Cooperate) or D (Defect/Strike) |
| Stage 2 | Nuclear | E (Escalate) or D (Back down) |

Stage 2 only becomes relevant if Stage 1 ends in conventional conflict (DD). A player that was exploited in Stage 1 can then threaten nuclear retaliation.

### 2. Preference Orderings (Prisoner's Dilemma Structure)

Each player has a **rank-ordered preference** over Stage 1 outcomes:

| Outcome | USA Payoff | Iran Payoff | Meaning |
|---------|-----------|------------|---------|
| DC (USA defects, Iran cooperates) | **4** | **1** | USA's temptation / Iran's sucker |
| CC (mutual cooperation) | **3** | **3** | Status quo |
| DD (mutual defection) | **2** | **2** | Conventional war |
| CD (USA cooperates, Iran defects) | **1** | **4** | Iran's temptation / USA's sucker |

> This is the classic **Prisoner's Dilemma** — each player is tempted to defect, but mutual defection is worse than mutual cooperation.

### 3. Nuclear Payoffs

From [output.txt](file:///d:/Projects/Game%20Theory/output.txt), the default nuclear payoffs are:

| Outcome | USA | Iran | Meaning |
|---------|-----|------|---------|
| EE (mutual escalation) | **-9** | **-9** | MAD (Mutually Assured Destruction) |
| ED (USA escalates, Iran backs down) | **5** | **-4** | USA first-strike win |
| DE (Iran escalates, USA backs down) | **-4** | **5** | Iran first-strike win |
| DD_nuc (both back down) | **2** | **2** | Reverts to conventional DD |

Nuclear war (EE) is the **worst possible outcome** for both — this is the deterrence engine.

### 4. Credibility

**Credibility** (`credibility_usa`, `credibility_iran`) is the probability [0,1] that a player's nuclear threat is genuine. This is the central engine of deterrence:

- **High credibility** → opponent is deterred from defecting → Cooperation (CC)
- **Low credibility** → opponent calls the bluff and defects → Conflict (CD or DC)

---

## Module-by-Module Breakdown

### [game_engine.py](file:///d:/Projects/Game%20Theory/game_engine.py) — The Core Engine

Defines three key components:

**[GameConfig](file:///d:/Projects/Game%20Theory/game_engine.py#39-86) dataclass** — all tunable parameters:
```python
credibility_usa: float = 0.5     # Probability USA retaliates
credibility_iran: float = 0.5    # Probability Iran retaliates
nuc_penalty: float = 10.0        # Cost of nuclear war
audience_cost_usa: float = 0.0   # Hand-tying penalty
sunk_cost_usa: float = 0.0       # Pre-game investment
iran_has_nuclear: bool = True     # Capability flag
```

**Payoff functions:**

- [get_conventional_payoffs()](file:///d:/Projects/Game%20Theory/game_engine.py#98-120) — Stage 1 payoffs, modified by audience cost penalties when a player backs down
- [get_nuclear_payoffs()](file:///d:/Projects/Game%20Theory/game_engine.py#122-162) — Stage 2 payoffs, including first-strike bonus and sunk-cost modifiers
- [get_payoffs()](file:///d:/Projects/Game%20Theory/game_engine.py#164-175) — Unified dispatcher

---

### [scenarios.py](file:///d:/Projects/Game%20Theory/scenarios.py) — The Solver and Four Scenarios

#### Backward-Induction Solver

**Backward induction** is the gold-standard solution concept for sequential games. It works by *solving backwards*: figure out what happens at Stage 2 first, then use that to inform Stage 1 decisions.

**Step 1 — Solve the nuclear sub-game ([_solve_nuclear_subgame](file:///d:/Projects/Game%20Theory/scenarios.py#54-89)):**

For each player, compute the **Expected Value** of escalating vs. backing down:

```
USA EV(Escalate) = P(Iran escalates) × EE_payoff + P(Iran backs down) × ED_payoff
USA EV(Defect)   = P(Iran escalates) × DE_payoff + P(Iran backs down) × DD_payoff
```

USA escalates if `EV(Escalate) > EV(Defect)`.

**Step 2 — Solve Stage 1 ([backward_induction](file:///d:/Projects/Game%20Theory/scenarios.py#91-212)):**

Each player computes the expected payoff of defecting vs. cooperating, now *knowing* what the nuclear sub-game outcome would be:

```
Iran EV(Defect) = (1 - cred_usa) × CD_payoff    ← USA bluffs, Iran exploits
                + cred_usa       × DD_nuclear_eff ← USA retaliates → nuclear risk
Iran EV(Cooperate) = CC_payoff = 3.0
```

Iran defects if `EV(Defect) > EV(Cooperate)`.

#### The Four Canonical Scenarios

| Scenario | Setup | Equilibrium (from output) | What it demonstrates |
|---|---|---|---|
| **Called Bluff** | USA cred=0.1, Iran cred=0.9 | **(C, D)** | Iran exploits USA's non-credible threat |
| **Rational Irrationality** | Iran cred=0.95, USA cred=0.3 | **(C, D)** | Iran's "madman" posture deters USA |
| **Asymmetric - Non-Nuclear** | Iran has no nukes | **(D, C)** | USA enjoys escalation dominance |
| **Asymmetric - Nuclear** | Matched cred=0.7 | **(C, C)** | Symmetric nukes → mutual deterrence |
| **First-Strike Advantage** | Bonus=3.0, cred=0.6 | **(C, C)** | High mutual risk still deters |

**Key takeaway from the "Asymmetric" pair:** The most striking result — Iran *gaining* nuclear weapons actually **stabilizes** the game (from DC → CC). This is the core prediction of **Mutual Assured Destruction (MAD)** theory.

---

### [signaling.py](file:///d:/Projects/Game%20Theory/signaling.py) — Commitment Mechanisms

This module implements **Schelling (1966)** and **Fearon (1994)** commitment mechanisms — ways a player can credibly pre-commit to a threat.

#### Audience Costs (Hand-Tying)

A player makes a **public statement** committing to retaliate. Backing down from that statement costs them politically (domestic audience turns against them).

- Effect: Penalizes `C` (cooperation/backing-down) action payoffs
- Credibility boost: `+0.10` per unit of cost

From the output — USA audience costs at cost=0.5 (`cred_usa` jumps from 0.50 → 0.55) immediately shifts the equilibrium from **(C,C) → (D,C)**: USA suddenly becomes threatening enough to exploit Iran.

#### Sunk Costs (Pre-game Investment)

A player makes **pre-game investments** (missile defense, troop deployments) that make following through on a threat cheaper.

- Effect: Increases payoff for winning the nuclear escalation
- Credibility boost: `+0.08` per unit of investment (weaker than audience costs)
- Transition happens later: `cred_usa` must reach ~0.70 before equilibrium shifts

This models the real-world intuition that *deploying troops to the Gulf* is more credible than just *threatening to*.

---

### [main.py](file:///d:/Projects/Game%20Theory/main.py) — The Orchestrator

Runs five analysis phases in order:

1. **Payoff Table** — print all 8 outcomes
2. **Scenario Analysis** — run the 4 canonical scenarios
3. **Sensitivity Analysis** — sweep credibility 0.0→1.0 for both players (11×11 grid)
4. **Stability Map** — generate a 51×51 heatmap PNG saved to `stability_map.png`
5. **Signaling Analysis** — sweep commitment costs for both players / both mechanisms

---

## Reading the Sensitivity Analysis (output.txt, lines 97–113)

```
              Iran=0.0  Iran=0.1  ...  Iran=0.4  Iran=0.5  ...  Iran=1.0
USA=0.0    D->E,D->E  D->E,D->E  ...    C,D       C,D     ...    C,D
USA=0.5       D,C       D,C      ...    D,C       C,C     ...    C,C
USA=1.0       D,C       D,C      ...    D,C       C,C     ...    C,C
```

This reveals **three equilibrium zones**:
- 🔴 **Top-left** (`D->E,D->E`): Both credibilities very low → mutual nuclear posturing (both threaten but don't believe each other)
- 🟡 **Bottom-left / top-right** (`D,C` or `C,D`): One side dominates conventionally
- 🟢 **Center-right and beyond** (`C,C`): Mutual deterrence — both threats credible, no one moves first

The **phase transition** happens around credibility ≈ 0.5 for the dominated player — below that threshold, they get exploited; above it, mutual cooperation emerges.

---

## The Stability Map

The `stability_map.png` file (generated at 51×51 resolution) color-codes these same zones:

| Color | Zone | Meaning |
|-------|------|---------|
| 🟢 Green | Mutual Deterrence (CC) | Both threats credible → peace |
| 🟡 Gold | Conventional Conflict | One side exploits the other |  
| 🔴 Red | Nuclear Conflict | Low credibility on both sides → nuclear brinkmanship |

---

## Summary of Key Game Theory Concepts Used

| Concept | Where Used | Academic Source |
|---|---|---|
| Prisoner's Dilemma | Base payoff structure | Classical |
| Extensive-Form Game | Two-stage sequential model | Game Theory |
| Backward Induction | [_solve_nuclear_subgame](file:///d:/Projects/Game%20Theory/scenarios.py#54-89) + [backward_induction](file:///d:/Projects/Game%20Theory/scenarios.py#91-212) | Zagare 1992 |
| Nash Equilibrium | All scenario outputs | Nash 1950 |
| Credibility / Resolve | `credibility_usa/iran` parameters | Zagare / Kraig |
| Audience Costs | [apply_audience_costs()](file:///d:/Projects/Game%20Theory/signaling.py#44-73) | Fearon 1994 |
| Sunk Costs | [apply_sunk_costs()](file:///d:/Projects/Game%20Theory/signaling.py#79-108) | Schelling 1966 |
| Rational Irrationality (Madman Theory) | [rational_irrationality()](file:///d:/Projects/Game%20Theory/scenarios.py#241-258) scenario | Nixon / Kraig 1999 |
| MAD (Mutually Assured Destruction) | Asymmetric capability comparison | Cold War doctrine |
| First-Strike Stability | [first_strike_advantage()](file:///d:/Projects/Game%20Theory/scenarios.py#303-320) scenario | Strategic stability lit. |
