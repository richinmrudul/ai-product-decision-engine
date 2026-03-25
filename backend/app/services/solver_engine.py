"""Deterministic minimal-change solver for closing the gap to the next decision tier."""

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


def _next_tier_and_gap(decision: str, overall_score: float) -> tuple[str, float | None]:
    if decision == "BUY":
        return "NONE", None
    if decision == "AVOID":
        return "WATCH", round(max(0.0, 55.0 - overall_score), 2)
    return "BUY", round(max(0.0, 75.0 - overall_score), 2)


def _headroom_int(features: dict, factor: str) -> int:
    current = features[FACTOR_SCORE_KEYS[factor]]
    return max(0, min(100, int(math.floor(100.0 - current + 1e-9))))


def _make_path(
    factors: list[str],
    changes: dict[str, float],
    weighted_gain: float,
    summary: str,
) -> dict:
    total = round(sum(changes.values()), 2)
    return {
        "factors": factors,
        "factor_score_changes": {k: round(v, 2) for k, v in changes.items()},
        "total_score_change": total,
        "estimated_weighted_gain": round(weighted_gain, 2),
        "solution_summary": summary,
    }


def _solve_single_factor(factor: str, gap: float, features: dict) -> dict | None:
    w = WEIGHTS[factor]
    h = _headroom_int(features, factor)
    for d in range(0, h + 1):
        gain = w * d
        if gain >= gap - 1e-6:
            label = FACTOR_LABELS[factor]
            return _make_path(
                [factor],
                {factor: float(d)},
                gain,
                f"Raise {label} by {d} point(s) (~{gain:.2f} weighted overall gain) to cover the gap.",
            )
    return None


def _solve_pair(fa: str, fb: str, gap: float, features: dict) -> dict | None:
    wa, wb = WEIGHTS[fa], WEIGHTS[fb]
    ha, hb = _headroom_int(features, fa), _headroom_int(features, fb)
    best_da: int | None = None
    best_db: int | None = None
    best_total = 10**9

    for da in range(0, ha + 1):
        for db in range(0, hb + 1):
            gain = wa * da + wb * db
            if gain < gap - 1e-6:
                continue
            total = da + db
            if total < best_total:
                best_total = total
                best_da, best_db = da, db
            elif total == best_total and best_da is not None:
                if da < best_da or (da == best_da and db < best_db):
                    best_da, best_db = da, db

    if best_da is None:
        return None

    la, lb = FACTOR_LABELS[fa], FACTOR_LABELS[fb]
    gain = wa * best_da + wb * best_db
    return _make_path(
        [fa, fb],
        {fa: float(best_da), fb: float(best_db)},
        gain,
        f"Raise {la} by {best_da} and {lb} by {best_db} point(s) "
        f"(~{gain:.2f} weighted overall gain) to cover the gap.",
    )


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

    single_total = best_single["total_score_change"] if best_single else 10**9
    pair_total = best_pair["total_score_change"] if best_pair else 10**9

    substantial = (gap > 12) or (
        min(single_total, pair_total) > 18 if best_single or best_pair else False
    )
    difficulty = (
        " This path requires substantial movement, so the upgrade remains difficult."
        if substantial
        else ""
    )

    if best_single is not None and (best_pair is None or single_total <= pair_total):
        return (
            f"The smallest successful path found is a single-factor lift: "
            f"{best_single['solution_summary']}{difficulty}"
        )

    assert best_pair is not None
    prefix = (
        "No single-factor solution exists within remaining headroom at 1-point steps; "
        if best_single is None
        else ""
    )
    return (
        f"{prefix}"
        f"The smallest successful path found is a combined improvement across "
        f"{FACTOR_LABELS[best_pair['factors'][0]]} and {FACTOR_LABELS[best_pair['factors'][1]]}: "
        f"{best_pair['solution_summary']}{difficulty}"
    )


def run_solver_analysis(features: dict, decision_result: dict) -> dict:
    decision = decision_result["decision"]
    overall = decision_result["overall_score"]
    next_tier, gap = _next_tier_and_gap(decision, overall)

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
        cand = _solve_single_factor(factor, gap, features)
        if cand is None:
            continue
        if best_single is None or cand["total_score_change"] < best_single["total_score_change"]:
            best_single = cand
        elif (
            cand["total_score_change"] == best_single["total_score_change"]
            and cand["factors"][0] < best_single["factors"][0]
        ):
            best_single = cand

    best_pair: dict | None = None
    for fa, fb in PAIR_ORDER:
        cand = _solve_pair(fa, fb, gap, features)
        if cand is None:
            continue
        if best_pair is None or cand["total_score_change"] < best_pair["total_score_change"]:
            best_pair = cand
        elif cand["total_score_change"] == best_pair["total_score_change"]:
            if (fa, fb) < tuple(best_pair["factors"]):
                best_pair = cand

    summary = _minimum_change_summary(next_tier, gap, best_single, best_pair)

    return {
        "next_tier": next_tier,
        "gap_overall_points": gap,
        "best_single_factor_solution": best_single,
        "best_two_factor_solution": best_pair,
        "minimum_change_summary": summary,
    }
