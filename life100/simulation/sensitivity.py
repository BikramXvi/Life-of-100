"""Sensitivity analysis — find a genuine tipping point, not a manufactured one.

The reframing this answers: "sweep a disaster's severity and look for a
point where the society's response changes disproportionately, not just
proportionally." This module does exactly that and nothing more — every
value in a sweep comes from a real, independent branch-and-run of the
simulation (via `alternate_history.branch_simulation`, the same mechanism
`experiments.py` uses), never a lookup table or an interpolated guess.

Methodology (written out explicitly, because the project's own standing
rule is "don't invent a flattering number" — the detection logic below must
be checkable, not just trusted):

1. Sweep the requested parameter values (ascending). Branch the SAME base
   state once per value so every run is identical except for that one
   parameter — a controlled experiment, not a comparison across different
   starting conditions.
2. For each output metric, compute the discrete slope between every pair of
   ADJACENT swept values: slope_i = (metric[i+1] - metric[i]) / (value[i+1]
   - value[i]).
3. A step is flagged as a tipping-point CANDIDATE only if its |slope| is
   both the sweep's maximum AND at least TIPPING_RATIO times the median
   |slope| of every OTHER step. This specifically tests for a
   disproportionate jump — not merely "the biggest of several similar
   changes," which a smooth, purely linear response would also have one of.
4. If no step clears that ratio, the metric is reported as having NO
   detected tipping point. A smooth or monotonic response across the swept
   range is a valid, honest finding — it is not converted into a forced
   "tipping point" just because a maximum slope always technically exists.
5. When a candidate IS found, one refinement pass re-sweeps
   REFINEMENT_POINTS additional values strictly inside that bracket (a real
   second batch of simulation runs, not interpolation) and re-applies the
   identical slope test to narrow the located range.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Callable

from life100.events.schemas import EventType
from life100.simulation import disasters
from life100.simulation.alternate_history import branch_simulation
from life100.simulation.economy import run_tick
from life100.simulation.engine import SimulationEngine
from life100.simulation.experiments import _metrics as _compute_metrics

TIPPING_RATIO = 3.0
"""A step's |slope| must be at least this many times the median |slope| of
every other step to count as disproportionate. Chosen and disclosed up
front, not tuned after seeing results, so the number can't quietly become
whatever produces a headline finding."""

REFINEMENT_POINTS = 5
"""Extra sample points run inside a detected bracket during refinement."""

SWEEPABLE_METRICS = (
    "unemployment_rate",
    "business_failures",
    "avg_household_stress",
    "food_price_index",
    "health_incidents",
    "avg_household_wealth",
)


def _end_disaster_if_active(world: SimulationEngine, name: str) -> None:
    """A sensitivity sweep needs to trigger a FRESH drought on each branch,
    but the base simulation it branches from may itself already have one
    active (e.g. the caller is mid-experiment in the What If Lab) --
    `trigger_drought` refuses to double-trigger. Since `world` is a
    throwaway branch, it's safe to end its copy of that disaster first via
    the normal DISASTER_ENDED event (CLAUDE.md rule 4: still only through
    the event system, never by touching `active_disasters` directly)."""
    if name in world.active_disasters:
        world.emit(
            EventType.DISASTER_ENDED,
            source_entity=name,
            source_type="disaster",
            payload={"disaster_type": name},
        )


def _sweep_drought_severity(
    base_engine: SimulationEngine, values: list[float], disaster_duration: int, ticks: int, tag: str
) -> list[dict]:
    results = []
    for i, v in enumerate(values):
        world = branch_simulation(base_engine, f"{base_engine.simulation_id}_sens_{tag}_{i}")
        _end_disaster_if_active(world, "drought")
        disasters.trigger_drought(world, duration_ticks=disaster_duration, severity=v)
        for _ in range(ticks):
            run_tick(world)
        results.append(_compute_metrics(world))
    return results


PARAMETER_SWEEPS: dict[str, Callable] = {
    "drought_severity": _sweep_drought_severity,
}
DEFAULT_SWEEP_VALUES = {
    "drought_severity": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5],
}


@dataclass
class TippingPoint:
    metric: str
    bracket: tuple[float, float]
    refined_bracket: tuple[float, float] | None
    slope: float
    typical_slope: float
    ratio: float


def _slopes(values: list[float], series: list[float]) -> list[tuple[float, float, float]]:
    out = []
    for i in range(len(values) - 1):
        dv = values[i + 1] - values[i]
        if dv == 0:
            continue
        out.append((values[i], values[i + 1], (series[i + 1] - series[i]) / dv))
    return out


def _detect_tipping_point(metric: str, values: list[float], series: list[float]) -> TippingPoint | None:
    steps = _slopes(values, series)
    if len(steps) < 3:
        return None  # too few steps to tell a jump apart from noise

    abs_slopes = [abs(s) for _, _, s in steps]
    max_idx = abs_slopes.index(max(abs_slopes))
    biggest = abs_slopes[max_idx]
    others = abs_slopes[:max_idx] + abs_slopes[max_idx + 1 :]
    typical = median(others) if others else 0.0

    if biggest <= 1e-9:
        return None  # nothing moved at all

    if typical <= 1e-9:
        ratio = 999.0  # every other step was flat; cap for JSON-safety, still clearly "disproportionate"
    else:
        ratio = biggest / typical

    if ratio < TIPPING_RATIO:
        return None

    lo, hi, slope = steps[max_idx]
    return TippingPoint(
        metric=metric,
        bracket=(lo, hi),
        refined_bracket=None,
        slope=round(slope, 6),
        typical_slope=round(typical, 6),
        ratio=round(min(ratio, 999.0), 3),
    )


def run_sensitivity_sweep(
    base_engine: SimulationEngine,
    parameter: str = "drought_severity",
    values: list[float] | None = None,
    disaster_duration: int = 30,
    ticks: int = 15,
    refine: bool = True,
) -> dict:
    """Sweeps `parameter` over `values` (or a sensible default range),
    branching from `base_engine`'s CURRENT state each time, and looks for a
    genuine tipping point per metric. Returns a JSON-safe summary: the raw
    per-value metrics (so the caller can plot the whole curve, not just the
    verdict) plus, per metric, either a located tipping-point bracket or
    `None` if the response was smooth across this range.

    `ticks=15` is the default deliberately, not 30: at 30 ticks food_price_index
    and avg_household_stress both saturate at their caps for EVERY severity in
    the default range (verified empirically), which erases the very
    differentiation a sensitivity sweep is trying to find. At 15 ticks the
    underlying mechanism is still visible: `economy._update_businesses`
    lays a business off/fails it only once `business.cash < 0` -- a hard
    per-business threshold sitting on top of a smooth, linear function of
    severity (`demand_multiplier`/`cost_multiplier`). That is exactly why a
    real tipping point shows up in `business_failures` (and the metrics that
    follow from it, like `avg_household_wealth`) even though nothing in the
    code hardcodes a "tipping severity" -- it falls out of a continuous cash
    balance crossing zero within a fixed number of days.

    Only "drought_severity" is implemented for now (CLAUDE.md rule 10: don't
    invent scope beyond what's asked — noted in PROGRESS.md as the current
    assumption; extending PARAMETER_SWEEPS to other levers is a small,
    isolated addition when needed).
    """
    if parameter not in PARAMETER_SWEEPS:
        raise ValueError(f"unsupported sweep parameter '{parameter}' (supported: {sorted(PARAMETER_SWEEPS)})")

    sweep_values = sorted(values) if values else list(DEFAULT_SWEEP_VALUES[parameter])
    if len(sweep_values) < 4:
        raise ValueError("need at least 4 values to sweep (fewer can't distinguish a jump from noise)")

    sweep_fn = PARAMETER_SWEEPS[parameter]
    coarse_metrics = sweep_fn(base_engine, sweep_values, disaster_duration, ticks, "coarse")

    refinement_cache: dict[tuple[float, float], tuple[list[float], list[dict]]] = {}

    def _refined(lo: float, hi: float) -> tuple[list[float], list[dict]]:
        key = (round(lo, 6), round(hi, 6))
        if key not in refinement_cache:
            inner = [lo + (hi - lo) * i / (REFINEMENT_POINTS + 1) for i in range(1, REFINEMENT_POINTS + 1)]
            refined_values = sorted({lo, hi, *inner})
            refinement_cache[key] = (
                refined_values,
                sweep_fn(base_engine, refined_values, disaster_duration, ticks, f"refine_{lo}_{hi}"),
            )
        return refinement_cache[key]

    tipping_points: dict[str, dict | None] = {}
    for metric in SWEEPABLE_METRICS:
        series = [m[metric] for m in coarse_metrics]
        tp = _detect_tipping_point(metric, sweep_values, series)
        if tp is None:
            tipping_points[metric] = None
            continue

        if refine:
            lo, hi = tp.bracket
            refined_values, refined_metrics = _refined(lo, hi)
            refined_series = [m[metric] for m in refined_metrics]
            refined_tp = _detect_tipping_point(metric, refined_values, refined_series)
            if refined_tp is not None:
                tp.refined_bracket = refined_tp.bracket

        tipping_points[metric] = {
            "bracket": list(tp.bracket),
            "refined_bracket": list(tp.refined_bracket) if tp.refined_bracket else None,
            "slope": tp.slope,
            "typical_slope": tp.typical_slope,
            "ratio": tp.ratio,
        }

    return {
        "parameter": parameter,
        "values": sweep_values,
        "ticks": ticks,
        "disaster_duration": disaster_duration,
        "metrics_by_value": coarse_metrics,
        "tipping_points": tipping_points,
        "methodology": (
            f"A step is flagged as a tipping point only when its |slope| is the sweep's maximum "
            f"AND at least {TIPPING_RATIO}x the median |slope| of every other step -- a "
            f"disproportionate jump, not just the largest of several similar changes. A metric "
            f"with no such step is reported as having no detected tipping point (a smooth "
            f"response), never forced to show one."
        ),
    }
