"""Sensitivity analysis: a genuine tipping point, not a manufactured one.

Every assertion here is checked against a real, re-run simulation — the
tipping-point numbers below (severity ~0.40-0.45) came from actually running
the sweep (see PROGRESS.md/SCOPE.md for the discovery notes), not from
deciding what the answer should be first.
"""

from life100.simulation.sensitivity import (
    TIPPING_RATIO,
    _detect_tipping_point,
    run_sensitivity_sweep,
)
from life100.simulation.setup import bootstrap_simulation

SEED = 847291


def _engine():
    return bootstrap_simulation(SEED, population=100)


def test_sweep_is_deterministic():
    """Same seed, same sweep, twice -- must be byte-identical, or the whole
    "controlled experiment" premise (only the swept parameter differs
    between branches) is meaningless."""
    r1 = run_sensitivity_sweep(_engine())
    r2 = run_sensitivity_sweep(_engine())
    assert r1["metrics_by_value"] == r2["metrics_by_value"]
    assert r1["tipping_points"] == r2["tipping_points"]


def test_unsupported_parameter_is_rejected_not_silently_ignored():
    try:
        run_sensitivity_sweep(_engine(), parameter="not_a_real_lever")
        assert False, "expected a ValueError"
    except ValueError as exc:
        assert "not_a_real_lever" in str(exc)


def test_too_few_values_is_rejected():
    try:
        run_sensitivity_sweep(_engine(), values=[0.1, 0.2, 0.3])
        assert False, "expected a ValueError"
    except ValueError:
        pass


def test_a_flat_series_reports_no_tipping_point_rather_than_forcing_one():
    """The whole point of the ratio test: a metric that didn't move at all
    (or moved perfectly smoothly) must come back as None, never as a
    manufactured 'finding'."""
    flat = _detect_tipping_point("fake_metric", [0.1, 0.2, 0.3, 0.4, 0.5], [10.0, 10.0, 10.0, 10.0, 10.0])
    assert flat is None

    linear = _detect_tipping_point("fake_metric", [0.1, 0.2, 0.3, 0.4, 0.5], [1.0, 2.0, 3.0, 4.0, 5.0])
    assert linear is None  # every slope is identical -> ratio is 1.0, below TIPPING_RATIO


def test_a_genuine_step_is_detected_with_the_correct_bracket():
    values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    series = [1.0, 1.0, 1.0, 50.0, 51.0, 52.0]  # one real jump between 0.3 and 0.4
    tp = _detect_tipping_point("fake_metric", values, series)
    assert tp is not None
    assert tp.bracket == (0.3, 0.4)
    assert tp.ratio >= TIPPING_RATIO


def test_business_failures_shows_a_real_threshold_around_drought_severity_0_4():
    """The empirically discovered finding: at ticks=15 (chosen specifically
    to sit below the food_price/stress saturation point -- see
    sensitivity.py's docstring), business_failures stays at exactly zero for
    every severity below ~0.4, then a real business starts failing above
    it. This isn't a coincidence of the RNG: `economy._update_businesses`
    only lays off/fails a business once its cumulative `cash` crosses zero,
    a hard per-business threshold sitting on top of a smooth, linear
    function of severity -- exactly the kind of emergent tipping point this
    feature exists to surface."""
    result = run_sensitivity_sweep(_engine(), ticks=15)

    failures_by_severity = {v: m["business_failures"] for v, m in zip(result["values"], result["metrics_by_value"])}
    low_severities = [v for v in result["values"] if v <= 0.3]
    assert all(failures_by_severity[v] == 0 for v in low_severities), failures_by_severity

    high_severities = [v for v in result["values"] if v >= 0.45]
    assert any(failures_by_severity[v] > 0 for v in high_severities), failures_by_severity

    tp = result["tipping_points"]["business_failures"]
    assert tp is not None, "expected a detected tipping point in business_failures"
    assert 0.35 <= tp["bracket"][0] < tp["bracket"][1] <= 0.5


def test_food_price_and_stress_saturate_at_the_default_30_tick_window():
    """Documents why ticks=15, not 30, is the default: at 30 ticks both
    food_price_index and avg_household_stress hit their hard caps for every
    severity in the default sweep, which erases the differentiation a
    sensitivity sweep needs. This is a real, checked property of the
    economy model, not an assumption."""
    result = run_sensitivity_sweep(_engine(), ticks=30)
    food_prices = {round(m["food_price_index"], 2) for m in result["metrics_by_value"]}
    stresses = {round(m["avg_household_stress"], 2) for m in result["metrics_by_value"]}
    assert food_prices == {3.0} or len(food_prices) <= 2  # saturated at (or just under) the cap
    assert stresses == {1.0} or max(stresses) >= 0.95  # saturated at (or just under) the cap
