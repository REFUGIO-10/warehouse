"""Multi-seed local benchmark — the team's scoring oracle (RAMA C / infra).

The official leaderboard scores 3 hidden seeds. Three seeds is noisy. A seed
only permutes which shelves get requested (robot start cells are fixed, demand
is uniform over your 960 shelves), so running MORE seeds gives a lower-variance
estimate of the hidden-seed score *without* overfitting to round-0/1/2.

Run from refugio-starter-kit/:
  python tools/benchmark.py submissions/submission.py
  python tools/benchmark.py submissions/layout_dev.py --count 30
  python tools/benchmark.py submissions/policy_dev.py --seeds round-0,round-1,round-2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import mean, pstdev

# Make `warehouse` importable even if a teammate skipped `pip install -e .`.
_KIT_ROOT = Path(__file__).resolve().parent.parent
if str(_KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(_KIT_ROOT))

from warehouse.evaluation import DEFAULT_EVAL_TICKS  # noqa: E402
from warehouse.local_runner import run_local  # noqa: E402

OFFICIAL_SEED_COUNT = 3
BUDGET_SECONDS = 180.0


def benchmark(submission: Path, seeds: list[str], ticks: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for seed in seeds:
        # Budget disabled here: we measure act()/setup time ourselves and project
        # it onto the official 3-seed window below, instead of starving an N-seed run.
        result = run_local(submission, seeds=(seed,), ticks=ticks, policy_budget_seconds=None)
        setup_s = float(result.get("layout_time_seconds", 0.0))
        # run_local folds setup time into policy_time_seconds; subtract it back out.
        act_s = max(0.0, float(result.get("policy_time_seconds", 0.0)) - setup_s)
        rows.append(
            {
                "seed": seed,
                "deliveries": result["score"],
                "act_s": act_s,
                "setup_s": setup_s,
                "status": result["status"],
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-seed REFUGIO benchmark.")
    parser.add_argument("submission", type=Path)
    parser.add_argument("--count", type=int, default=10, help="Generated seeds bench-0..bench-{N-1}.")
    parser.add_argument("--seeds", default=None, help="Explicit comma-separated seeds (overrides --count).")
    parser.add_argument("--ticks", type=int, default=DEFAULT_EVAL_TICKS)
    args = parser.parse_args()

    if args.seeds:
        seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
    else:
        seeds = [f"bench-{i}" for i in range(args.count)]

    submission = args.submission.resolve()
    rows = benchmark(submission, seeds, args.ticks)

    dels = [r["deliveries"] for r in rows]
    setup_s = rows[0]["setup_s"] if rows else 0.0
    act_per_seed = mean(r["act_s"] for r in rows) if rows else 0.0
    proj_act_3 = act_per_seed * OFFICIAL_SEED_COUNT
    failed = [r for r in rows if r["status"] != "succeeded"]

    print(f"submission : {submission.name}")
    print(f"seeds      : {len(seeds)}   ticks: {args.ticks}")
    for r in rows:
        print(f"  {str(r['seed']):>10}  deliveries={r['deliveries']:>5}  act={r['act_s']:.2f}s  {r['status']}")
    print("-" * 52)
    if dels:
        print(f"mean/seed  : {mean(dels):.1f}  (sd {pstdev(dels):.1f}, min {min(dels)}, max {max(dels)})")
        print(f"PROJECTED OFFICIAL (mean x3) : {mean(dels) * OFFICIAL_SEED_COUNT:.0f}")
    print(f"setup time : {setup_s:.2f}s         (budget {BUDGET_SECONDS:.0f}s)")
    print(f"act time   : {act_per_seed:.3f}s/seed -> ~{proj_act_3:.1f}s for 3 seeds (budget {BUDGET_SECONDS:.0f}s)")
    if proj_act_3 > BUDGET_SECONDS:
        print("  WARNING: projected act() time exceeds the official 180s budget.")
    if failed:
        print(f"  WARNING: {len(failed)} seed(s) did not succeed (status != succeeded).")


if __name__ == "__main__":
    main()
