"""Deterministic upgrade solver: importance-weighted effective cost and strategic ranking."""

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


def _effective_cost(changes: dict[str, float], importance: dict[str, float]) -> float:
    return sum(changes[f] / importance[f] for f in changes)


def _narrative_summary(
    factors: list[str],
    changes: dict[str, float],
    next_tier: str,
    total_change: float,
) -> str:
    labels = [FACTOR_LABELS[f] for f in factors]
    if len(labels) == 1:
        joint = labels[0]
    else:
        joint = f"{labels[0]} and {labels[1]}"
    tier_label = "BUY" if next_tier == "BUY" else "WATCH"

    if total_change <= 8:
        return (
            f"A focused push on {joint} could realistically edge this opportunity toward {tier_label}."
        )
    if total_change <= 18:
        return (
            f"Meaningful upgrades across {joint} would be needed to reach {tier_label} with confidence."
        )
    return (
        f"A substantial improvement in {joint} would be required to reach {tier_label}."
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
    eff = round(_effective_cost(changes, importance), 2)
    strat = _strategic_score(factors, level_map, weakest, decision_factors)
    summary = _narrative_summary(factors, changes, next_tier, total)
    return {
        "factors": factors,
        "factor_score_changes": {k: round(v, 2) for k, v in changes.items()},
        "total_score_change": total,
        "estimated_weighted_gain": round(weighted_gain, 2),
        "effective_cost": eff,
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
    h = _headroom_int(features, factor)
    for d in range(0, h + 1):
        gain = w * d
        if gain >= gap - 1e-6:
            changes = {factor: float(d)}
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
    ha, hb = _headroom_int(features, fa), _headroom_int(features, fb)
    best_path: dict | None = None
    best_key: tuple | None = None

    for da in range(0, ha + 1):
        for db in range(0, hb + 1):
            gain = wa * da + wb * db
            if gain < gap - 1e-6:
                continue
            changes = {fa: float(da), fb: float(db)}
            eff = round(_effective_cost(changes, importance), 4)
            strat = _strategic_score([fa, fb], level_map, weakest, decision_factors)
            key = (eff, -strat, da + db, da, db)
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
    key_a = (
        a["effective_cost"],
        -a["strategic_score"],
        a["total_score_change"],
        tuple(a["factors"]),
    )
    key_b = (
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
        return "No single-factor or two-factor solution exists within remaining headroom at 1-point steps."

    global_best = _better_solution(best_single, best_pair)
    assert global_best is not None

    substantial = (gap > 12) or (global_best["total_score_change"] > 18)
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
            f"The strategically preferred path is a single-factor lift on {FACTOR_LABELS[best_single['factors'][0]]} "
            f"(effective cost {best_single['effective_cost']:.2f} vs raw change {best_single['total_score_change']:.0f}): "
            f"{best_single['solution_summary']}{difficulty}"
        )

    assert best_pair is not None
    prefix = (
        "No single-factor path wins on effective cost and strategic fit within headroom; "
        if best_single is None
        else ""
    )
    return (
        f"{prefix}"
        f"The strategically preferred path pairs {FACTOR_LABELS[best_pair['factors'][0]]} and "
        f"{FACTOR_LABELS[best_pair['factors'][1]]} (effective cost {best_pair['effective_cost']:.2f}): "
        f"{best_pair['solution_summary']}{difficulty}"
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
