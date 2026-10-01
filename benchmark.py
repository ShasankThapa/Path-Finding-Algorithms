"""Headless benchmark: A* (8-dir) vs JPS, in the spirit of Harabor & Grastien (2011).

Runs both algorithms on the same queries and records nodes expanded, cells scanned,
search time and path cost. No Pygame window is opened.

    python benchmark.py           # full run (a few minutes)
    python benchmark.py --quick   # small sample, for CI

Outputs in results/: benchmark.csv (raw rows), summary.md (tables), and two charts.
"""
import argparse
import csv
import random
import statistics
from pathlib import Path

import numpy as np

from algos.astar import Astar
from algos.base import run_to_completion
from algos.jps import JPS
from grid import Grid
from maps_io import load_movingai_map, load_scenarios

ROOT = Path(__file__).resolve().parent
MAPS_DIR = ROOT / "maps"
RESULTS_DIR = ROOT / "results"

# How many queries to run. Moving AI buckets group scenarios by optimal length / 4.
# A 512x512 map has hundreds of buckets and its long queries take ~1-2 s each in Python,
# so instead of N per bucket we split the buckets into equal bands (short -> long) and
# take a few scenarios from each band.
FULL = {"bands": 10, "per_band": 3, "sizes": [100, 200],
        "densities": [0.0, 0.1, 0.2, 0.3, 0.4], "seeds": 30}
QUICK = {"bands": 3, "per_band": 1, "sizes": [100],
         "densities": [0.0, 0.2, 0.4], "seeds": 2}

COST_TOLERANCE = 1e-4
CSV_COLUMNS = ["source", "map", "map_type", "size", "density", "query", "bucket",
               "optimal_length", "algorithm", "nodes_expanded", "cells_scanned",
               "search_time_ms", "path_cost"]


# The map used for the "effort vs path length" chart.
CHART_MAP = "AR0070SR"


def map_type(name):
    # Which Moving AI set a map comes from, based on its file name.
    if name.startswith("maze"):
        return "maze"
    if "room" in name:
        return "room"
    if name.startswith("AR"):
        return "Baldur's Gate II"
    return "Dragon Age"


def check_cost(where, algorithm, cost, expected):
    # Abort loudly: a benchmark of a wrong answer is worthless.
    if cost is None or abs(cost - expected) > COST_TOLERANCE:
        raise RuntimeError(f"COST MISMATCH in {where}: {algorithm} returned {cost}, expected {expected}")


def run_both(grid, start, goal):
    # Same query for both algorithms. Returns {"A*": stats, "JPS": stats}.
    results = {}
    for name, algo in [("A*", Astar(8)), ("JPS", JPS())]:
        run_to_completion(algo, start, goal, grid)
        results[name] = dict(algo.stats)
    return results


def stratified_sample(scenarios, bands, per_band, rng):
    # Split the sorted bucket numbers into `bands` equal slices (short paths -> long paths)
    # and pick `per_band` random scenarios from each slice.
    buckets = sorted({s.bucket for s in scenarios})
    bands = min(bands, len(buckets))
    sample = []
    for band in range(bands):
        first = band * len(buckets) // bands
        last = (band + 1) * len(buckets) // bands
        band_buckets = set(buckets[first:last])
        candidates = [s for s in scenarios if s.bucket in band_buckets]
        sample += rng.sample(candidates, min(per_band, len(candidates)))
    return sample


def make_row(source, name, kind, size, density, query, bucket, optimal, algorithm, stats):
    return {
        "source": source, "map": name, "map_type": kind, "size": size, "density": density,
        "query": query, "bucket": bucket, "optimal_length": optimal, "algorithm": algorithm,
        "nodes_expanded": stats["nodes_expanded"], "cells_scanned": stats["cells_scanned"],
        "search_time_ms": stats["search_time_ms"], "path_cost": stats["path_cost"],
    }


def random_pairs(grid, count, rng):
    # For a map without a .scen file: seeded random start/goal pairs on free cells.
    free = np.argwhere(~np.isinf(grid.grid))
    pairs = []
    for i in range(count):
        a, b = rng.choice(len(free), size=2, replace=False)
        pairs.append(((int(free[a][0]), int(free[a][1])), (int(free[b][0]), int(free[b][1]))))
    return pairs


def benchmark_map_without_scenarios(name, grid, config, rows):
    # No official optimal lengths, so check JPS against A* (verified on the other maps).
    count = config["bands"] * config["per_band"]
    print(f"  {name}: {count} random pairs (no .scen file, so checked against A*, not official)")
    for query, (start, goal) in enumerate(random_pairs(grid, count, np.random.default_rng(0))):
        results = run_both(grid, start, goal)
        optimal = results["A*"]["path_cost"]
        if optimal is None:
            continue
        check_cost(f"{name} random pair {query}", "JPS", results["JPS"]["path_cost"], optimal)
        for algorithm, stats in results.items():
            rows.append(make_row("movingai-random-pairs", name, map_type(name), grid.width, None,
                                 query, None, optimal, algorithm, stats))


def benchmark_movingai(config, rows):
    for map_path in sorted(MAPS_DIR.glob("*.map")):
        name = map_path.stem
        grid = load_movingai_map(map_path)
        scenario_path = map_path.with_name(map_path.name + ".scen")
        if not scenario_path.exists():
            benchmark_map_without_scenarios(name, grid, config, rows)
            continue
        sample = stratified_sample(load_scenarios(scenario_path), config["bands"],
                                   config["per_band"], random.Random(0))
        print(f"  {name}: {len(sample)} scenarios")
        for query, scenario in enumerate(sample):
            results = run_both(grid, scenario.start, scenario.goal)
            for algorithm, stats in results.items():
                check_cost(f"{name} bucket {scenario.bucket}", algorithm,
                           stats["path_cost"], scenario.optimal_length)
                rows.append(make_row("movingai", name, map_type(name), grid.width, None, query,
                                     scenario.bucket, scenario.optimal_length, algorithm, stats))


def random_grid(size, density, rng):
    grid = Grid(size, size, 1)
    walls = rng.random((size, size)) < density
    grid.grid[walls] = np.inf
    return grid


def benchmark_random(config, rows):
    for size in config["sizes"]:
        for density in config["densities"]:
            for seed in range(config["seeds"]):
                rng = np.random.default_rng([size, int(density * 100), seed])
                grid = random_grid(size, density, rng)
                free = np.argwhere(~np.isinf(grid.grid))
                # Pick start/goal pairs until one is reachable (dense grids split into islands).
                for attempt in range(100):
                    i, j = rng.choice(len(free), size=2, replace=False)
                    start = (int(free[i][0]), int(free[i][1]))
                    goal = (int(free[j][0]), int(free[j][1]))
                    results = run_both(grid, start, goal)
                    if results["A*"]["path_cost"] is not None:
                        break
                else:
                    raise RuntimeError(f"no reachable pair on {size}x{size} at {density:.0%} walls, seed {seed}")
                # No official answer here: A* is verified against Moving AI above, so JPS must match it.
                optimal = results["A*"]["path_cost"]
                check_cost(f"random {size}x{size} {density:.0%} seed {seed}", "JPS",
                           results["JPS"]["path_cost"], optimal)
                for algorithm, stats in results.items():
                    rows.append(make_row("random", f"random {size}x{size}", "random", size, density,
                                         seed, None, optimal, algorithm, stats))
        print(f"  random {size}x{size}: done")


# ---------- Summaries ----------

def paired_queries(rows):
    # Group rows into (A* row, JPS row) pairs for the same query.
    by_query = {}
    for row in rows:
        key = (row["map"], row["density"], row["query"])
        by_query.setdefault(key, {})[row["algorithm"]] = row
    return [(pair["A*"], pair["JPS"]) for pair in by_query.values()]


def summarise(pairs):
    # Medians over queries. Speedup and expansion ratio are computed per query, then the
    # median taken, so one very long query can't dominate.
    return {
        "queries": len(pairs),
        "astar_nodes": statistics.median(a["nodes_expanded"] for a, j in pairs),
        "jps_nodes": statistics.median(j["nodes_expanded"] for a, j in pairs),
        "jps_scanned": statistics.median(j["cells_scanned"] for a, j in pairs),
        "astar_ms": statistics.median(a["search_time_ms"] for a, j in pairs),
        "jps_ms": statistics.median(j["search_time_ms"] for a, j in pairs),
        "speedup": statistics.median(a["search_time_ms"] / j["search_time_ms"] for a, j in pairs),
        "expansion_ratio": statistics.median(a["nodes_expanded"] / j["nodes_expanded"] for a, j in pairs),
    }


def group_summaries(rows):
    # One group per Moving AI map, and one per random-grid density (sizes pooled).
    groups = {}
    for a, j in paired_queries(rows):
        if a["source"] == "movingai":
            label = f"{a['map']} ({a['map_type']})"
        elif a["source"] == "movingai-random-pairs":
            label = f"{a['map']} ({a['map_type']}, random pairs)"
        else:
            label = f"random, {a['density']:.0%} walls"
        groups.setdefault(label, []).append((a, j))
    return {label: summarise(pairs) for label, pairs in groups.items()}


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(summaries, mode, path):
    lines = [
        "# A* (8-dir) vs JPS benchmark",
        "",
        f"Mode: {mode}. Every JPS and A* cost matched the official Moving AI optimal length.",
        "Exceptions, checked JPS against A* instead: random grids, and maps marked 'random pairs'",
        "(no .scen file, so no official answers).",
        "Medians over queries. Speedup = A* time / JPS time and expansion ratio = A* nodes / JPS nodes,",
        "each computed per query before taking the median. Times are Python wall-clock search time.",
        "",
        "| Group | Queries | A* nodes | JPS nodes | JPS cells scanned | A* ms | JPS ms | Speedup | Expansion ratio |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for label, s in summaries.items():
        lines.append(f"| {label} | {s['queries']} | {s['astar_nodes']:.0f} | {s['jps_nodes']:.0f} | "
                     f"{s['jps_scanned']:.0f} | {s['astar_ms']:.1f} | {s['jps_ms']:.1f} | "
                     f"{s['speedup']:.2f}x | {s['expansion_ratio']:.1f}x |")
    path.write_text("\n".join(lines) + "\n")


# ---------- Charts ----------

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID_COLOUR = "#e4e3df"
BLUE = "#2a78d6"     # A*
ORANGE = "#eb6834"   # JPS nodes expanded
AQUA = "#1baf7a"     # JPS cells scanned


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(TEXT_SECONDARY)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=11)
    ax.xaxis.label.set_color(TEXT_SECONDARY)
    ax.yaxis.label.set_color(TEXT_SECONDARY)


def chart_speedup(summaries, path, plt):
    labels = list(summaries.keys())
    speedups = [summaries[label]["speedup"] for label in labels]

    fig, ax = plt.subplots(figsize=(9, 0.5 * len(labels) + 1.8), facecolor=SURFACE)
    style_axes(ax)
    positions = list(range(len(labels)))[::-1]   # first group at the top
    ax.barh(positions, speedups, height=0.6, color=BLUE)
    ax.set_yticks(positions)
    ax.set_yticklabels(labels, color=TEXT_PRIMARY)
    for y, value in zip(positions, speedups):
        ax.text(value, y, f"  {value:.2f}x", va="center", fontsize=11, color=TEXT_PRIMARY)

    ax.axvline(1, color=TEXT_SECONDARY, linestyle="--", linewidth=1.2)
    ax.text(1, len(labels) - 0.4, " A* = 1x", color=TEXT_SECONDARY, fontsize=10, va="bottom")
    ax.set_xlim(0, max(speedups) * 1.2)
    ax.set_xlabel("Median speedup of JPS over A* (A* search time / JPS search time)")
    ax.xaxis.grid(True, color=GRID_COLOUR)
    ax.set_axisbelow(True)
    ax.set_title("JPS speedup over A* (8-dir): median per map", loc="left", fontsize=14, color=TEXT_PRIMARY, pad=12)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def chart_nodes_vs_length(rows, map_name, path, plt):
    pairs = [(a, j) for a, j in paired_queries(rows) if a["map"] == map_name]
    lengths = [a["optimal_length"] for a, j in pairs]

    fig, ax = plt.subplots(figsize=(9, 5.5), facecolor=SURFACE)
    style_axes(ax)
    # The last number is a vertical nudge (in points) for the direct label, because
    # A* nodes and JPS cells scanned can end up at almost the same height.
    series = [
        ("A* nodes expanded", [a["nodes_expanded"] for a, j in pairs], BLUE, "o", -9),
        ("JPS cells scanned", [j["cells_scanned"] for a, j in pairs], AQUA, "s", 9),
        ("JPS nodes expanded", [j["nodes_expanded"] for a, j in pairs], ORANGE, "^", 0),
    ]
    for label, values, colour, marker, nudge in series:
        ax.scatter(lengths, values, s=42, color=colour, marker=marker, edgecolors=SURFACE,
                   linewidths=1.5, label=label, zorder=3)
        # Direct label beside the longest query of each series.
        far = max(range(len(lengths)), key=lambda i: lengths[i])
        ax.annotate(label, (lengths[far], values[far]), xytext=(8, nudge), textcoords="offset points",
                    va="center", fontsize=10, color=TEXT_PRIMARY)

    ax.set_yscale("log")
    ax.set_xlabel("Optimal path length (octile distance, in cells)")
    ax.set_ylabel("Count per query (log scale)")
    ax.yaxis.grid(True, color=GRID_COLOUR, which="major")
    ax.set_axisbelow(True)
    ax.set_xlim(0, max(lengths) * 1.25)
    ax.legend(frameon=False, fontsize=10, loc="lower right", labelcolor=TEXT_PRIMARY)
    ax.set_title(f"Search effort vs path length on {map_name}", loc="left", fontsize=14,
                 color=TEXT_PRIMARY, pad=12)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def print_findings(summaries):
    by_speedup = sorted(summaries.items(), key=lambda item: item[1]["speedup"])
    slowest_label, slowest = by_speedup[0]
    fastest_label, fastest = by_speedup[-1]
    print()
    print("Findings")
    print("- Every cost matched the official optimum, or A* where there is no official answer.")
    print(f"- JPS's advantage was biggest on {fastest_label}: {fastest['speedup']:.2f}x faster.")
    print(f"  A* expanded {fastest['astar_nodes']:.0f} nodes (median), JPS {fastest['jps_nodes']:.0f}.")
    print(f"- It was smallest on {slowest_label}: {slowest['speedup']:.2f}x.")
    print(f"  A* expanded {slowest['astar_nodes']:.0f} nodes, JPS {slowest['jps_nodes']:.0f}, but JPS "
          f"scanned {slowest['jps_scanned']:.0f} cells.")
    print("- Why: JPS saves work by skipping symmetric paths, the many equal-cost ways through")
    print("  open space that A* would otherwise expand cell by cell. It pays off when A* is forced")
    print("  to flood large open regions: wide corridors and open areas where walls make the heuristic")
    print("  misleading. Where A*'s heuristic already leads almost straight to the goal (an empty")
    print("  grid), A* expands few nodes and there is nothing to skip, so JPS's row and column")
    print("  scans are pure overhead. In clutter (random walls) and 1-wide corridors every few")
    print("  cells is a jump point, so jumps are short and the saving is small.")
    print("- Expanding fewer nodes is not the same as doing less work: compare 'JPS cells scanned'")
    print("  with 'A* nodes'. In Python a scan step costs closer to a heap operation than in C++,")
    print("  so these time speedups are smaller than the ones reported in the paper.")


def main():
    parser = argparse.ArgumentParser(description="Benchmark A* (8-dir) against JPS.")
    parser.add_argument("--quick", action="store_true", help="run a much smaller sample (for CI)")
    args = parser.parse_args()
    config = QUICK if args.quick else FULL
    mode = "quick" if args.quick else "full"

    rows = []
    print(f"Moving AI maps ({mode}):")
    benchmark_movingai(config, rows)
    print(f"Random uniform-cost grids ({mode}):")
    benchmark_random(config, rows)

    RESULTS_DIR.mkdir(exist_ok=True)
    write_csv(rows, RESULTS_DIR / "benchmark.csv")
    summaries = group_summaries(rows)
    write_summary(summaries, mode, RESULTS_DIR / "summary.md")

    # Import matplotlib only now, with a backend that never opens a window.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    chart_speedup(summaries, RESULTS_DIR / "speedup_by_map.png", plt)
    map_names = sorted({row["map"] for row in rows if row["source"].startswith("movingai")})
    if map_names:
        chosen = CHART_MAP if CHART_MAP in map_names else map_names[0]
        chart_nodes_vs_length(rows, chosen, RESULTS_DIR / "nodes_vs_length.png", plt)

    print(f"\nWrote {len(rows)} rows to results/benchmark.csv, plus summary.md and charts.")
    print_findings(summaries)


if __name__ == "__main__":
    main()
