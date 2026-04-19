# Asymmetric Escalation Game — Complete Walkthrough

## Overview

This project is a **Python simulation of the Asymmetric Escalation Game** between the USA (Defender) and Iran (Challenger), based on:
- **Kilgour & Zagare (2007)** — *"Explaining Limited Conflicts"*
- **Zagare & Kilgour (2000)** — *Perfect Deterrence Theory*

The game models a critical question in strategic deterrence: *When does conflict remain limited? When does it escalate to all-out war? When does deterrence succeed entirely?*

### Key Innovation: The E Option at Stage 1

Unlike the previous C/D-only model, the Asymmetric Escalation Game gives the **Defender three choices** (C, D, or E) when responding to a challenge. This enables the model to produce **Limited Conflict (DD)** as a distinct outcome from All-Out Conflict (EE) — the paper's central contribution.

---

## Project Architecture

```
Game Theory/
├── game_engine.py   — Core data model, payoff functions, outcome definitions
├── scenarios.py     — Multi-node backward-induction solver + 6 canonical scenarios
├── signaling.py     — Commitment mechanisms (audience costs, sunk costs)
├── main.py          — Orchestrator: runs all 5 analysis phases
└── output.txt       — Full simulation output (with stability_map.png)
```

---

## Game Theory Concepts

### 1. Extensive-Form Game (Asymmetric Escalation Game)

This is an **extensive-form, sequential game** with incomplete information. The game tree has **5 decision nodes**:

```
Node 1 (Challenger): C → SQ (Status Quo)
                     D → Node 2

Node 2 (Defender):   C → DC (Defender Concedes)
                     D → Node 3a (respond-in-kind)
                     E → Node 3b (escalate)          ← KEY ADDITION

Node 3a (Challenger): D → DD (Limited Conflict)      ← Paper's key outcome
                      E → Node 4

Node 3b (Challenger): D → DE (Defender Wins)
                      E → EE (All-Out Conflict)

Node 4 (Defender):    D → ED (Challenger Wins)
                      E → EE (All-Out Conflict)
```

### 2. Six Possible Outcomes

| Outcome | Name | Description |
|---------|------|-------------|
| **SQ** | Status Quo | Challenger cooperates — no conflict |
| **DC** | Defender Concedes | Challenger initiates, Defender capitulates |
| **DD** | Limited Conflict | Both respond-in-kind, conflict stays limited |
| **ED** | Challenger Wins | Challenger escalates, Defender backs down |
| **DE** | Defender Wins | Defender escalates, Challenger concedes |
| **EE** | All-Out Conflict | Both escalate — mutual destruction |

> The distinction between **DD** (limited conflict) and **EE** (all-out conflict) is what makes this model superior to the simple C/D Prisoner's Dilemma model.

### 3. Preference Orderings & Type-Dependent Payoffs

The paper's key innovation is **type-dependent payoffs** at certain outcomes:

**Challenger (Iran):**
```
DC > SQ > ED > DD > EE+ > DE > EE-
(100)  (60)  (45)  (40)  (25)  (20)  (0)
```
- Hard Challenger gets `EE+ = 25` (prefers all-out war to losing: 25 > DE=20)
- Soft Challenger gets `EE- = 0` (prefers backing down: 0 < DE=20)

**Defender (USA):**
```
SQ > DE > DD+ > DC > DD- > EE+ > ED > EE-
(100) (90)  (60)  (50)  (40)  (30)  (20)  (0)
```
- Hard Defender gets `EE+ = 30` (prefers all-out war to losing: 30 > ED=20)
- Soft Defender gets `EE- = 0` (prefers backing down: 0 < ED=20)
- Tac Hard Defender gets `DD+ = 60` (limited conflict is tolerable)
- Tac Soft Defender gets `DD- = 40` (limited conflict is costly)

> **Why this matters**: Without type-dependent EE payoffs, no player ever wants to escalate (since EE=0 < ED=20 and EE=0 < DE=20). With EE+/EE-, Hard types are willing to escalate, creating real escalation risk that drives the entire deterrence calculus.

### 4. Incomplete Information & Credibility

The model uses **incomplete information** (Bayesian game):

| Parameter | Meaning |
|-----------|---------|
| **p (credibility_defender)** | Probability Defender is "Hard" type |
| **pCh (credibility_challenger)** | Probability Challenger is "Hard" type |

**Defender types** (parameterized by single p):
- **Hard/Hard** (prob p²): always responds and always counter-escalates
- **Hard/Soft** (prob p(1-p)): responds-in-kind but won't counter-escalate
- **Soft/Hard** (prob p(1-p)): may escalate but won't respond-in-kind
- **Soft/Soft** (prob (1-p)²): always capitulates

Tactical credibility: pTac = p, Strategic credibility: pStr = p

**Challenger types:**
- **Hard** (prob pCh): prefers EE to DE (willing to counter-escalate)
- **Soft** (prob 1-pCh): prefers DE to EE (backs down from all-out war)

---

## Module-by-Module Breakdown

### [game_engine.py](file:///home/hummingbird/Desktop/Game%20Theory/Game-Theory-Minor-Project/game_engine.py) — The Core Engine

Defines the game structure:

**[GameConfig](file:///home/hummingbird/Desktop/Game%20Theory/Game-Theory-Minor-Project/game_engine.py) dataclass** — all tunable parameters:
```python
credibility_defender: float = 0.5     # p: Defender tactical/strategic credibility
credibility_challenger: float = 0.5   # pCh: Probability Challenger is Hard
defender_can_escalate: bool = True     # Capability flag
challenger_can_escalate: bool = True   # Nuclear capability flag
first_strike_bonus: float = 0.0       # Bonus for initiating escalation
audience_cost_defender: float = 0.0   # Hand-tying penalty
sunk_cost_defender: float = 0.0       # Pre-game investment
```

**Payoff functions:**
- [get_outcome_payoffs()](file:///home/hummingbird/Desktop/Game%20Theory/Game-Theory-Minor-Project/game_engine.py) — Returns (defender, challenger) payoffs for any of the 6 outcomes, applying audience costs, sunk costs, first-strike bonuses, and capability constraints.

---

### [scenarios.py](file:///home/hummingbird/Desktop/Game%20Theory/Game-Theory-Minor-Project/scenarios.py) — The Solver and Six Scenarios

#### Multi-Node Backward-Induction Solver

The solver works backward through 5 decision nodes, computing **expected payoffs under incomplete information** at each:

**Node 4 → Node 3b → Node 3a → Node 2 → Node 1**

At each node, the solver:
1. Computes the expected payoff by weighting Hard-type and Soft-type behavior
2. Determines the most-likely action for labeling purposes
3. Passes the expected values upstream

**Key insight at Node 2**: The Defender has THREE choices (C, D, E):
```
EV at Node 2 = p_tac × (best of D, E payoffs) + (1 - p_tac) × DC payoff
```

This is what creates the **Limited Conflict zone** in the stability map — when Defender is credible enough to respond-in-kind but the expected payoff doesn't fully deter Challenger from initiating.

#### The Six Canonical Scenarios

| Scenario | Setup | Equilibrium | Outcome | What it demonstrates |
|---|---|---|---|---|
| **Called Bluff** | Def cred=0.1, Chal cred=0.9 | (D, C) | **DC** | Challenger exploits non-credible Defender |
| **Rational Irrationality** | Chal cred=0.95, Def cred=0.3 | (D, C) | **DC** | Madman posture → Defender still capitulates |
| **Asymmetric Non-Nuclear** | Challenger can't escalate | (C, -) | **SQ** | Defender's escalation dominance deters |
| **Asymmetric Nuclear** | Both cred=0.7 | (C, -) | **SQ** | Symmetric threats → mutual deterrence |
| **First-Strike Advantage** | Bonus=30, cred=0.6 | (D→D, D) | **DD** | First-strike bonus creates Limited Conflict |
| **Limited Conflict Emergence** | Modified payoffs | varies | **DD** | Constrained Limited-Response Equilibrium |

**Key findings:**
- **DD (Limited Conflict)** emerges in a transitional credibility band — Defender is credible enough to respond but not enough to deter
- The model predicts that **limited conflicts involve miscalculation**: Challenger initiates expecting Defender to capitulate, then is surprised by the in-kind response
- This matches real-world cases: Korea (1950), Cuba (1962), Fashoda (1898)

---

### [signaling.py](file:///home/hummingbird/Desktop/Game%20Theory/Game-Theory-Minor-Project/signaling.py) — Commitment Mechanisms

#### Audience Costs (Hand-Tying)

A player makes a **public statement** committing to retaliate. Backing down costs them politically.

- Effect: Penalizes cooperating/backing-down actions
- Credibility boost: `+0.10` per unit of cost

From the output — Defender audience costs at cost=0.5 (`cred_def` jumps from 0.50 → 0.55) shifts the equilibrium from **DC → DD**: Defender now responds-in-kind instead of capitulating. At cost=2.0, full deterrence is achieved (**SQ**).

**Three-phase transition:** DC → DD → SQ as audience costs increase.

#### Sunk Costs (Pre-game Investment)

A player makes **pre-game investments** that make following through on a threat cheaper.

- Effect: Increases payoff for winning escalation
- Credibility boost: `+0.08` per unit of investment (weaker than audience costs)
- Shows the same DC → DD → SQ transition

---

### [main.py](file:///home/hummingbird/Desktop/Game%20Theory/Game-Theory-Minor-Project/main.py) — The Orchestrator

Runs five analysis phases:

1. **Payoff Table** — print all 6 outcomes with payoffs
2. **Scenario Analysis** — run the 6 canonical scenarios
3. **Sensitivity Analysis** — sweep credibility 0.0→1.0 for both players (11×11 grid)
4. **Stability Map** — generate a 51×51 heatmap PNG with 4 zones
5. **Signaling Analysis** — sweep commitment costs for both players / both mechanisms

---

## Reading the Sensitivity Analysis

```
          Ch=0.0  Ch=0.1  ...  Ch=0.4  Ch=0.5  ...  Ch=1.0
Def=0.0     DC      DC    ...    DC      DC    ...    DC
Def=0.4     DC      DC    ...    DC      DC    ...    DC
Def=0.5     SQ      SQ    ...    SQ      DC    ...    DC
Def=0.6     SQ      SQ    ...    SQ      DD    ...    DD
Def=0.7     SQ      SQ    ...    SQ      SQ    ...    SQ
Def=1.0     SQ      SQ    ...    SQ      SQ    ...    SQ
```

This reveals **three equilibrium zones** (matching the paper's Figure 2):
- 🟡 **DC zone** (low Defender credibility): Defender capitulates → Challenger wins without a fight
- 🔵 **DD zone** (moderate Defender credibility + high Challenger credibility): **Limited Conflict** — both fight at conventional level
- 🟢 **SQ zone** (high Defender credibility): Full deterrence — Challenger doesn't initiate

The **DD zone** is the paper's key contribution — it's the band where conflict occurs but remains limited.

---

## The Stability Map

The `stability_map.png` file (generated at 51×51 resolution) has **two panels**:

### Left Panel — Equilibrium Zones

| Color | Zone | Meaning |
|-------|------|---------|
| 🟢 Green | Deterrence (SQ) | Defender's threats credible → peace |
| 🟡 Gold | No Response (DC) | Defender capitulates → Challenger wins |
| 🔵 Blue | Limited Conflict (DD) | Both respond-in-kind → conflict stays limited |
| 🔴 Red | Escalatory (DE/ED/EE) | Escalation is the modal outcome |

### Right Panel — Escalation Risk Heatmap

Shows the **probability of escalation-path outcomes** (DE, EE) as a continuous gradient. Even within the SQ and DC zones, some credibility combinations carry significant escalation risk because Hard Defender types choose E at Node 2.

> **Key finding from the paper**: *"Conflicts—limited or all-out—are not possible in the Asymmetric Escalation Game with complete information."* Escalatory outcomes (DE, EE) appear as probabilistic paths within the incomplete-information game, but are rarely the single most-likely outcome. The escalation risk heatmap captures this nuance — the orange region (low pCh, moderate p) is where Defender's Hard types choose E, creating real escalation risk even though the modal outcome is SQ or DC.

---

## Comparison with Previous Model

| Feature | Previous (PD-based) | Current (Asymmetric Escalation Game) |
|---|---|---|
| Stage 1 actions | C, D (simultaneous) | C, D, **E** (sequential) |
| Game structure | Symmetric 2×2 | Asymmetric extensive form (5 nodes) |
| Distinct outcomes | 4 (CC, CD, DC, DD) + nuclear | **6** (SQ, DC, DD, ED, DE, EE) |
| Limited Conflict | Not modeled | **DD outcome** — paper's key contribution |
| Information | Complete | **Incomplete** (Bayesian types) |
| Defender's response | Binary (C/D) | **Ternary (C/D/E)** — the key improvement |
| Stability zones | 3 | **4** (SQ, DC, DD, escalatory) |
| Academic basis | Zagare 1992 / Kraig 1999 | **Kilgour & Zagare 2007** |

---

## Summary of Key Game Theory Concepts Used

| Concept | Where Used | Academic Source |
|---|---|---|
| Asymmetric Escalation Game | Entire game structure | Kilgour & Zagare 2007 |
| Perfect Deterrence Theory | Preference orderings & credibility | Zagare & Kilgour 2000 |
| Extensive-Form Game | 5-node sequential model | Game Theory |
| Backward Induction (Bayesian) | Multi-node solver | Zagare & Kilgour 2000 |
| Perfect Bayesian Equilibrium | Equilibrium concept | Game Theory |
| Incomplete Information | Type-dependent behavior | Harsanyi 1967-68 |
| Credibility / Resolve | `credibility_defender/challenger` | Zagare / Kilgour |
| Limited Conflict | DD outcome zone | Kilgour & Zagare 2007 |
| Constrained Limited-Response Eq. | Limited Conflict scenario | Kilgour & Zagare 2007 |
| Audience Costs | `apply_audience_costs()` | Fearon 1994 |
| Sunk Costs | `apply_sunk_costs()` | Schelling 1966 |
| Rational Irrationality (Madman) | Rational Irrationality scenario | Nixon / Kraig 1999 |
| MAD (Mutually Assured Destruction) | Asymmetric capability comparison | Cold War doctrine |
| First-Strike Stability | First-Strike Advantage scenario | Strategic stability lit. |
