"""Deterministic search-style upgrade paths: single-factor and pairwise factor analysis."""

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


def _next_tier_and_gap(decision: str, overall_score: float) -> tuple[str, float | None]:
    if decision == "BUY":
        return "NONE", None
    if decision == "AVOID":
        return "WATCH", round(max(0.0, 55.0 - overall_score), 2)
    return "BUY", round(max(0.0, 75.0 - overall_score), 2)


def _single_factor_paths(features: dict, gap: float | None) -> list[dict]:
    paths: list[dict] = []
    for factor in ["profitability", "demand", "competition", "reviews"]:
        key = FACTOR_SCORE_KEYS[factor]
        current = round(features[key], 2)
        headroom = round(max(0.0, 100.0 - current), 2)
        weight = WEIGHTS[factor]
        if gap is None or gap <= 0:
            req = 0.0
            reachable = False
        else:
            req = round(gap / weight, 2)
            reachable = req <= headroom + 1e-6
        paths.append(
            {
                "factor": factor,
                "current_score": current,
                "remaining_headroom": headroom,
                "required_score_increase": req,
                "reachable_within_bounds": reachable,
            }
        )
    return paths


def _multi_factor_paths(features: dict, gap: float | None) -> list[dict]:
    out: list[dict] = []
    for a, b in PAIR_ORDER:
        wa, wb = WEIGHTS[a], WEIGHTS[b]
        ha = max(0.0, 100.0 - features[FACTOR_SCORE_KEYS[a]])
        hb = max(0.0, 100.0 - features[FACTOR_SCORE_KEYS[b]])
        combined = round(wa * ha + wb * hb, 2)
        la, lb = FACTOR_LABELS[a], FACTOR_LABELS[b]
        if gap is None or gap <= 0:
            reachable = False
            summary = f"{la.capitalize()} + {lb}: no gap to close at the current tier."
        else:
            reachable = combined >= gap - 1e-6
            if reachable:
                summary = (
                    f"{la.capitalize()} and {lb} together can supply up to {combined:.2f} weighted "
                    f"overall points versus a {gap:.2f}-point gap."
                )
            else:
                summary = (
                    f"{la.capitalize()} and {lb} together cap out at {combined:.2f} weighted points, "
                    f"below the {gap:.2f}-point gap."
                )
        out.append(
            {
                "factors": [a, b],
                "combined_remaining_headroom": combined,
                "reachable": reachable,
                "path_summary": summary,
            }
        )
    return out


def _best_path_summary(
    decision: str,
    gap: float | None,
    single_paths: list[dict],
    multi_paths: list[dict],
) -> str:
    if decision == "BUY":
        return "Already at the highest decision tier; no upgrade search applies."

    if gap is None or gap <= 0:
        return f"Baseline score already meets the next tier; no positive gap remains."

    reachable_singles = [p for p in single_paths if p["reachable_within_bounds"]]
    if reachable_singles:
        best = min(reachable_singles, key=lambda p: p["required_score_increase"])
        label = FACTOR_LABELS[best["factor"]]
        return (
            f"{label.capitalize()} can close the {gap:.2f}-point gap alone: it needs about "
            f"{best['required_score_increase']:.2f} sub-score points with "
            f"{best['remaining_headroom']:.2f} headroom available."
        )

    strongest = max(single_paths, key=lambda p: p["remaining_headroom"] - p["required_score_increase"])
    sl = FACTOR_LABELS[strongest["factor"]]
    if strongest["required_score_increase"] > strongest["remaining_headroom"]:
        single_line = (
            f"{sl.capitalize()} is the strongest single lever by headroom vs need, but still insufficient alone."
        )
    else:
        single_line = "No single factor can realistically close the gap within 0–100 sub-score bounds."

    reachable_pairs = [m for m in multi_paths if m["reachable"]]
    if reachable_pairs:
        best_pair = max(
            reachable_pairs,
            key=lambda m: m["combined_remaining_headroom"] - gap,
        )
        fa, fb = best_pair["factors"]
        fa_l, fb_l = FACTOR_LABELS[fa], FACTOR_LABELS[fb]
        return (
            f"{single_line} A combined improvement across {fa_l} and {fb_l} appears to be the most realistic path "
            f"(up to {best_pair['combined_remaining_headroom']:.2f} weighted points vs {gap:.2f} needed)."
        )

    return (
        f"{single_line} No evaluated two-factor combination closes the gap within remaining headroom; "
        f"broaden improvements beyond these pairs or revisit inputs."
    )


def run_search_analysis(features: dict, decision_result: dict) -> dict:
    decision = decision_result["decision"]
    overall = decision_result["overall_score"]
    next_tier, gap = _next_tier_and_gap(decision, overall)

    single_factor_paths = _single_factor_paths(features, gap)
    multi_factor_paths = _multi_factor_paths(features, gap)
    best_path_summary = _best_path_summary(decision, gap, single_factor_paths, multi_factor_paths)

    return {
        "next_tier": next_tier,
        "gap_overall_points": gap,
        "single_factor_paths": single_factor_paths,
        "multi_factor_paths": multi_factor_paths,
        "best_path_summary": best_path_summary,
    }
