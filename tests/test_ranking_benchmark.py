from __future__ import annotations

import ranking_benchmark


def test_ranking_pressure_reports_every_known_priority() -> None:
    # Report only. The shipped scoring must not be tuned to these keys: that is what moving
    # the gate to make a change pass looks like, and B1's golden file forbids it.
    result = ranking_benchmark.run()
    assert result["candidates"] >= 50 > result["top"]
    assert set(result["positions"]) == {
        "ci.release-automation",
        "ci.schedule",
        "hygiene.issue-templates",
        "hygiene.pr-template",
        "tests.coverage",
    }


def test_rank_gate_detects_scoring_regressions() -> None:
    # Losing a candidate and ranking it below the cutoff are different failures. The
    # regression keeps every producer active, but reverses the category priorities.
    result = ranking_benchmark.run(scoring={"categories": {"ci": 0, "hygiene": 0, "tests": 0}})
    assert result["candidates"] >= 50
    assert result["missed"] and not result["passed"]


def test_ranking_is_repeatable() -> None:
    assert ranking_benchmark.run() == ranking_benchmark.run()
