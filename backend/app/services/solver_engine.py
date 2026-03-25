"""Deterministic upgrade solver: caps, diminishing returns, and realism-aware ranking."""

import math

from app.services.decision_engine import WEIGHTS

FACTOR_SCORE_KEYS = {
    "profitability": "profitability_score",
    "demand": "demand_score",
    "competition": "competition_score",
    "reviews": "review_score",
}

FACTOR_LABELS = {
    "profitability": "profitability",
    "demand": "demand",
    "competition": "competition",
    "reviews": "reviews",
}

MAX_FEASIBLE_IMPROVEMENT = {
    "profitability": 35,
    "demand": 30,
    "competition": 40,
    "reviews": 25,
}

# Raw diminishing penalty (for reference / narratives).
REALISTIC_PENALTY_CEILING = 120.0
STRETCHED_PENALTY_CEILING = 180.0
HARD_PENALTY_DISCARD = 280.0

PAIR_ORDER = [
    ("profitability", "demand"),
    ("profitability", "competition"),
    ("profitability", "reviews"),
    ("demand", "competition"),
    ("demand", "reviews"),
    ("competition", "reviews"),
]

ORDERED_FACTORS = ["profitability", "demand", "competition", "reviews"]

SENSITIVITY_IMPORTANCE = {
    "HIGH": 1.5,
    "MEDIUM": 1.0,
    "LOW": 0.7,
    "UNTESTED": 1.0,
}

# Real-world effort to move a factor's sub-score (higher = harder).
FACTOR_DIFFICULTY = {
    "profitability": 1.0,
    "demand": 1.2,
    "reviews": 1.3,
    "competition": 1.6,
}

# Tiering on difficulty-weighted burden: sum(penalized_delta * difficulty).
REALISTIC_DIFFICULTY_BURDEN = 150.0
STRETCHED_DIFFICULTY_BURDEN = 230.0
HARD_DIFFICULTY_BURDEN = 400.0


def _factor_from_scenario_id(scenario_id: str) -> str:
    if scenario_id.startswith("cost_"):
        return "profitability"
    if scenario_id.startswith("demand_"):
        return "demand"
    if scenario_id.startswith("competition_"):
        return "competition"
    if scenario_id.startswith("review_") or scenario_id.startswith("average_rating_"):
        return "reviews"
    return "reviews"


def _next_tier_and_gap(decision: str, overall_score: float) -> tuple[str, float | None]:
    if decision == "BUY":
        return "NONE", None
    if decision == "AVOID":
        return "WATCH", round(max(0.0, 55.0 - overall_score), 2)
    return "BUY", round(max(0.0, 75.0 - overall_score), 2)


def _headroom_int(features: dict, factor: str) -> int:
    current = features[FACTOR_SCORE_KEYS[factor]]
    return max(0, min(100, int(math.floor(100.0 - current + 1e-9))))


def _feasible_headroom_int(features: dict, factor: str) -> int:
    """Clamp search to remaining score headroom and per-factor realism caps."""
    return min(_headroom_int(features, factor), MAX_FEASIBLE_IMPROVEMENT[factor])


def _diminishing_penalty(delta: float) -> float:
    """First 20 pts at 1x; 20–40 at 1.5x; beyond 40 at 2x."""
    d = max(0.0, float(delta))
    if d <= 20.0:
        return d
    if d <= 40.0:
        return 20.0 + (d - 20.0) * 1.5
    return 20.0 + 20.0 * 1.5 + (d - 40.0) * 2.0


def _effective_cost_adjusted(
    changes: dict[str, float], importance: dict[str, float]
) -> tuple[float, float, float]:
    """
    penalized = diminishing_penalty(delta)
    adjusted_cost = penalized * difficulty_weight
    effective_cost = sum( adjusted_cost / importance_f )

    Returns (effective_cost, raw_penalty_sum, difficulty_weighted_burden).
    """
    penalty_sum = 0.0
    burden = 0.0
    cost = 0.0
    for f, delta in changes.items():
        p = _diminishing_penalty(delta)
        penalty_sum += p
        adjusted = p * FACTOR_DIFFICULTY[f]
        burden += adjusted
        cost += adjusted / importance[f]
    return round(cost, 4), round(penalty_sum, 2), round(burden, 2)


def _execution_tier(difficulty_burden: float) -> int:
    if difficulty_burden <= REALISTIC_DIFFICULTY_BURDEN:
        return 0
    if difficulty_burden <= STRETCHED_DIFFICULTY_BURDEN:
        return 1
    return 2


def _importance_by_factor(intelligence: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in intelligence["factor_sensitivity"]:
        level = row["sensitivity_level"]
        out[row["factor"]] = SENSITIVITY_IMPORTANCE.get(level, 1.0)
    for f in ORDERED_FACTORS:
        out.setdefault(f, 1.0)
    return out


def _sensitivity_level_map(intelligence: dict) -> dict[str, str]:
    return {row["factor"]: row["sensitivity_level"] for row in intelligence["factor_sensitivity"]}


def _weakest_factor_set(features: dict) -> set[str]:
    scored = [(f, features[FACTOR_SCORE_KEYS[f]]) for f in ORDERED_FACTORS]
    scored.sort(key=lambda x: x[1])
    return {scored[0][0], scored[1][0]}


def _decision_changing_factors(sensitivity: dict) -> set[str]:
    factors: set[str] = set()
    for s in sensitivity["scenarios"]:
        if s["decision_changed"]:
            factors.add(_factor_from_scenario_id(s["scenario_id"]))
    return factors


def _strategic_score(
    factors: list[str],
    level_map: dict[str, str],
    weakest: set[str],
    decision_factors: set[str],
) -> float:
    score = 0.0
    for f in factors:
        lvl = level_map.get(f, "UNTESTED")
        if lvl == "HIGH":
            score += 3.0
        elif lvl == "MEDIUM":
            score += 1.0
        elif lvl == "LOW":
            score += 0.0
        else:
            score += 0.5
        if f in weakest:
            score += 2.0
        if f in decision_factors:
            score += 2.0
    return score


def _narrative_summary(
    factors: list[str],
    changes: dict[str, float],
    next_tier: str,
    total_change: float,
    adjusted_penalty_sum: float,
    difficulty_burden: float,
    realism_stretched: bool,
    level_map: dict[str, str],
) -> str:
    labels = [FACTOR_LABELS[f] for f in factors]
    if len(labels) == 1:
        joint = labels[0]
    else:
        joint = f"{labels[0]} and {labels[1]}"
    tier_label = "BUY" if next_tier == "BUY" else "WATCH"
    fs = set(factors)

    # Difficulty-aware: mixing easier levers with harder ones.
    if (
        len(fs) == 2
        and "profitability" in fs
        and "competition" in fs
        and changes.get("profitability", 0) > 0
        and changes.get("competition", 0) > 0
    ):
        return (
            "Although competition is a high-impact factor, it is also difficult to improve, so the selected path "
            f"balances profitability gains with competitive improvements toward {tier_label}."
        )
    if (
        len(fs) == 2
        and "demand" in fs
        and "competition" in fs
        and changes.get("demand", 0) > 0
        and changes.get("competition", 0) > 0
    ):
        return (
            "Demand moves faster than repositioning against competitors; this path pairs demand traction with "
            f"competitive improvements, acknowledging the higher difficulty of the latter toward {tier_label}."
        )

    near_max: list[str] = []
    for f in factors:
        d = changes[f]
        cap = MAX_FEASIBLE_IMPROVEMENT[f]
        if cap > 0 and d >= cap * 0.85:
            near_max.append(FACTOR_LABELS[f])

    if near_max and (
        realism_stretched or difficulty_burden > STRETCHED_DIFFICULTY_BURDEN
    ):
        joined = " and ".join(near_max)
        return (
            f"Even under optimistic assumptions, this path requires near-maximum improvement in {joined}, "
            f"making it difficult to execute in practice once difficulty weighting is applied."
        )

    if realism_stretched or difficulty_burden > REALISTIC_DIFFICULTY_BURDEN:
        hard = [FACTOR_LABELS[f] for f in factors if FACTOR_DIFFICULTY.get(f, 1.0) >= 1.5]
        hard_note = (
            f" The path leans on harder-to-move areas ({', '.join(hard)})."
            if hard
            else ""
        )
        return (
            f"Closing the gap to {tier_label} implies heavy execution lift on {joint}: "
            f"diminishing returns plus factor difficulty raise the true cost of this upgrade.{hard_note}"
        )

    if (
        len(factors) == 1
        and factors[0] == "competition"
        and level_map.get("competition") == "HIGH"
    ):
        return (
            f"Competition is both sensitive and difficult to improve; expect outsized execution effort to reach {tier_label}."
        )

    if total_change <= 8:
        return (
            f"A focused push on {joint} could realistically edge this opportunity toward {tier_label}."
        )
    if total_change <= 18:
        return (
            f"Meaningful upgrades across {joint} would be needed to reach {tier_label} with confidence."
        )
    return (
        f"A substantial improvement in {joint} would be required to reach {tier_label}, "
        f"but it remains within the modeled feasibility caps."
    )


def _make_path(
    factors: list[str],
    changes: dict[str, float],
    weighted_gain: float,
    next_tier: str,
    importance: dict[str, float],
    level_map: dict[str, str],
    weakest: set[str],
    decision_factors: set[str],
) -> dict:
    total = round(sum(changes.values()), 2)
    eff, penalty_sum, diff_burden = _effective_cost_adjusted(changes, importance)
    strat = _strategic_score(factors, level_map, weakest, decision_factors)
    realism_stretched = diff_burden > REALISTIC_DIFFICULTY_BURDEN
    summary = _narrative_summary(
        factors,
        changes,
        next_tier,
        total,
        penalty_sum,
        diff_burden,
        realism_stretched,
        level_map,
    )
    return {
        "factors": factors,
        "factor_score_changes": {k: round(v, 2) for k, v in changes.items()},
        "total_score_change": total,
        "estimated_weighted_gain": round(weighted_gain, 2),
        "effective_cost": eff,
        "adjusted_penalty_sum": penalty_sum,
        "difficulty_weighted_penalty_sum": diff_burden,
        "realism_stretched": realism_stretched,
        "strategic_score": round(strat, 2),
        "solution_summary": summary,
    }


def _solve_single_factor(
    factor: str,
    gap: float,
    features: dict,
    next_tier: str,
    importance: dict[str, float],
    level_map: dict[str, str],
    weakest: set[str],
    decision_factors: set[str],
) -> dict | None:
    w = WEIGHTS[factor]
    h = _feasible_headroom_int(features, factor)
    for d in range(0, h + 1):
        gain = w * d
        if gain < gap - 1e-6:
            continue
        changes = {factor: float(d)}
        _, penalty_sum, diff_burden = _effective_cost_adjusted(changes, importance)
        if penalty_sum > HARD_PENALTY_DISCARD or diff_burden > HARD_DIFFICULTY_BURDEN:
            continue
        return _make_path(
            [factor],
            changes,
            gain,
            next_tier,
            importance,
            level_map,
            weakest,
            decision_factors,
        )
    return None


def _solve_pair(
    fa: str,
    fb: str,
    gap: float,
    features: dict,
    next_tier: str,
    importance: dict[str, float],
    level_map: dict[str, str],
    weakest: set[str],
    decision_factors: set[str],
) -> dict | None:
    wa, wb = WEIGHTS[fa], WEIGHTS[fb]
    ha, hb = _feasible_headroom_int(features, fa), _feasible_headroom_int(features, fb)
    best_path: dict | None = None
    best_key: tuple | None = None

    for da in range(0, ha + 1):
        for db in range(0, hb + 1):
            gain = wa * da + wb * db
            if gain < gap - 1e-6:
                continue
            changes = {fa: float(da), fb: float(db)}
            eff, penalty_sum, diff_burden = _effective_cost_adjusted(changes, importance)
            if penalty_sum > HARD_PENALTY_DISCARD or diff_burden > HARD_DIFFICULTY_BURDEN:
                continue
            tier = _execution_tier(diff_burden)
            strat = _strategic_score([fa, fb], level_map, weakest, decision_factors)
            key = (tier, eff, -strat, da + db, da, db)
            if best_key is None or key < best_key:
                best_key = key
                best_path = _make_path(
                    [fa, fb],
                    changes,
                    gain,
                    next_tier,
                    importance,
                    level_map,
                    weakest,
                    decision_factors,
                )

    return best_path


def _better_solution(a: dict | None, b: dict | None) -> dict | None:
    if a is None:
        return b
    if b is None:
        return a
    tier_a = _execution_tier(a["difficulty_weighted_penalty_sum"])
    tier_b = _execution_tier(b["difficulty_weighted_penalty_sum"])
    key_a = (
        tier_a,
        a["effective_cost"],
        -a["strategic_score"],
        a["total_score_change"],
        tuple(a["factors"]),
    )
    key_b = (
        tier_b,
        b["effective_cost"],
        -b["strategic_score"],
        b["total_score_change"],
        tuple(b["factors"]),
    )
    return a if key_a < key_b else b


def _minimum_change_summary(
    next_tier: str,
    gap: float | None,
    best_single: dict | None,
    best_pair: dict | None,
) -> str:
    if next_tier == "NONE":
        return "No upgrade solve applies; decision is already BUY."

    if gap is None or gap <= 0:
        return "Baseline already meets the next tier threshold; no factor changes are required."

    if best_single is None and best_pair is None:
        return (
            "No feasible upgrade path exists within per-factor caps and diminishing-return limits "
            "at 1-point steps (or all candidates exceeded hard penalty bounds)."
        )

    global_best = _better_solution(best_single, best_pair)
    assert global_best is not None

    substantial = (gap > 12) or (global_best["total_score_change"] > 18)
    penalty_note = ""
    if global_best.get("realism_stretched"):
        penalty_note = (
            " Execution remains heavy once diminishing returns and factor difficulty are applied."
        )
    difficulty = (
        " The upgrade still demands substantial movement, so execution risk stays elevated."
        if substantial
        else ""
    )

    prefer_single = best_single is not None and (
        best_pair is None or global_best is best_single
    )

    if prefer_single and best_single is not None:
        return (
            f"The most realistic preferred path is a single-factor lift on {FACTOR_LABELS[best_single['factors'][0]]} "
            f"(effective cost {best_single['effective_cost']:.2f} after difficulty weighting; "
            f"raw penalty {best_single['adjusted_penalty_sum']:.2f}, difficulty burden {best_single['difficulty_weighted_penalty_sum']:.2f}): "
            f"{best_single['solution_summary']}{penalty_note}{difficulty}"
        )

    assert best_pair is not None
    prefix = (
        "No single-factor path wins under realism ranking within caps; "
        if best_single is None
        else ""
    )
    return (
        f"{prefix}"
        f"The most realistic preferred path pairs {FACTOR_LABELS[best_pair['factors'][0]]} and "
        f"{FACTOR_LABELS[best_pair['factors'][1]]} (effective cost {best_pair['effective_cost']:.2f}; "
        f"difficulty burden {best_pair['difficulty_weighted_penalty_sum']:.2f}): "
        f"{best_pair['solution_summary']}{penalty_note}{difficulty}"
    )


def run_solver_analysis(
    features: dict,
    decision_result: dict,
    sensitivity: dict,
    intelligence: dict,
) -> dict:
    decision = decision_result["decision"]
    overall = decision_result["overall_score"]
    next_tier, gap = _next_tier_and_gap(decision, overall)

    importance = _importance_by_factor(intelligence)
    level_map = _sensitivity_level_map(intelligence)
    weakest = _weakest_factor_set(features)
    decision_factors = _decision_changing_factors(sensitivity)

    if gap is None or gap <= 0:
        return {
            "next_tier": next_tier,
            "gap_overall_points": gap,
            "best_single_factor_solution": None,
            "best_two_factor_solution": None,
            "minimum_change_summary": _minimum_change_summary(next_tier, gap, None, None),
        }

    best_single: dict | None = None
    for factor in ORDERED_FACTORS:
        cand = _solve_single_factor(
            factor,
            gap,
            features,
            next_tier,
            importance,
            level_map,
            weakest,
            decision_factors,
        )
        if cand is None:
            continue
        best_single = _better_solution(best_single, cand)

    best_pair: dict | None = None
    for fa, fb in PAIR_ORDER:
        cand = _solve_pair(
            fa,
            fb,
            gap,
            features,
            next_tier,
            importance,
            level_map,
            weakest,
            decision_factors,
        )
        if cand is None:
            continue
        best_pair = _better_solution(best_pair, cand)

    summary = _minimum_change_summary(next_tier, gap, best_single, best_pair)

    return {
        "next_tier": next_tier,
        "gap_overall_points": gap,
        "best_single_factor_solution": best_single,
        "best_two_factor_solution": best_pair,
        "minimum_change_summary": summary,
    }
