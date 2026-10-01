import random

import pytest

import benchmark
from maps_io import Scenario


def make_scenarios(bucket_count, per_bucket):
    scenarios = []
    for bucket in range(bucket_count):
        for i in range(per_bucket):
            scenarios.append(Scenario(bucket, "m.map", (0, 0), (1, 1), bucket * 4 + i))
    return scenarios


def test_stratified_sample_covers_short_and_long_paths():
    scenarios = make_scenarios(bucket_count=100, per_bucket=5)
    sample = benchmark.stratified_sample(scenarios, bands=10, per_band=3, rng=random.Random(0))
    assert len(sample) == 30
    # Each band of 10 buckets gives exactly 3 scenarios.
    for band in range(10):
        in_band = [s for s in sample if band * 10 <= s.bucket < (band + 1) * 10]
        assert len(in_band) == 3


def test_stratified_sample_with_fewer_buckets_than_bands():
    scenarios = make_scenarios(bucket_count=4, per_bucket=5)
    sample = benchmark.stratified_sample(scenarios, bands=10, per_band=2, rng=random.Random(0))
    assert len(sample) == 8
    assert sorted({s.bucket for s in sample}) == [0, 1, 2, 3]


def test_check_cost_aborts_on_mismatch():
    benchmark.check_cost("test", "A*", 10.00001, 10.0)   # within 1e-4: fine
    with pytest.raises(RuntimeError):
        benchmark.check_cost("test", "JPS", 10.1, 10.0)
    with pytest.raises(RuntimeError):
        benchmark.check_cost("test", "JPS", None, 10.0)


def row(algorithm, query, nodes, scanned, ms):
    return {"source": "random", "map": "random 10x10", "density": 0.1, "query": query,
            "algorithm": algorithm, "nodes_expanded": nodes, "cells_scanned": scanned,
            "search_time_ms": ms}


def test_summary_uses_per_query_ratios():
    rows = [
        row("A*", 0, 100, 100, 10.0), row("JPS", 0, 10, 50, 5.0),    # speedup 2, ratio 10
        row("A*", 1, 300, 300, 30.0), row("JPS", 1, 100, 200, 10.0),  # speedup 3, ratio 3
        row("A*", 2, 200, 200, 8.0), row("JPS", 2, 50, 80, 8.0),      # speedup 1, ratio 4
    ]
    summary = benchmark.summarise(benchmark.paired_queries(rows))
    assert summary["queries"] == 3
    assert summary["speedup"] == 2.0
    assert summary["expansion_ratio"] == 4.0
    assert summary["astar_nodes"] == 200
    assert summary["jps_scanned"] == 80
