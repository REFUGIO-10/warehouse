"""Sweep WHCA* parameters (WINDOW, NODE_CAP) dynamically on the bench.

This script helps optimize parameters to exqueeze the remaining 99.25% of the
computation budget (60s/seed limit).

Run from the repo root (warehouse/):
  python tools/sweep_params.py submissions/submission.py --count 5
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from statistics import mean

# Engine lives in refugio-starter-kit/.
_KIT = Path(__file__).resolve().parent.parent / "refugio-starter-kit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from warehouse.local_runner import run_local


def sweep_params(policy_path: Path, window: int, node_cap: int, seeds: list[str], ticks: int):
    # Read the original source
    source = policy_path.read_text(encoding="utf-8")

    # Modify WINDOW and NODE_CAP
    source = re.sub(r"^WINDOW\s*=\s*\d+", f"WINDOW = {window}", source, flags=re.MULTILINE)
    source = re.sub(r"^NODE_CAP\s*=\s*\d+", f"NODE_CAP = {node_cap}", source, flags=re.MULTILINE)

    # Write to temp file
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
        fh.write(source)
        temp_path = Path(fh.name)

    try:
        scores = []
        act_times = []
        for s in seeds:
            result = run_local(temp_path, seeds=(s,), ticks=ticks, policy_budget_seconds=None)
            scores.append(result["score"])
            setup_s = float(result.get("layout_time_seconds", 0.0))
            act_s = max(0.0, float(result.get("policy_time_seconds", 0.0)) - setup_s)
            act_times.append(act_s)
    finally:
        temp_path.unlink(missing_ok=True)

    return mean(scores), mean(act_times)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep WHCA* parameters.")
    parser.add_argument("policy", type=Path, help="Path to policy file (e.g. submissions/submission.py)")
    parser.add_argument("--count", type=int, default=3, help="Number of seeds to run per test.")
    parser.add_argument("--ticks", type=int, default=300)
    parser.add_argument("--windows", default="12,16,24,32", help="Comma-separated WINDOW values to sweep.")
    parser.add_argument("--node-caps", default="1200,4000,8000", help="Comma-separated NODE_CAP values to sweep.")
    args = parser.parse_args()

    policy_path = args.policy.resolve()
    seeds = [f"bench-{i}" for i in range(args.count)]
    windows = [int(w.strip()) for w in args.windows.split(",")]
    node_caps = [int(n.strip()) for n in args.node_caps.split(",")]

    print(f"Sweeping parameters for {policy_path.name} against {len(seeds)} seeds...")
    print(f"Windows: {windows}")
    print(f"Node caps: {node_caps}\n")
    print(f"{'WINDOW':>8} | {'NODE_CAP':>8} | {'MEAN SCORE':>10} | {'PROJ SCORE':>10} | {'MEAN TIME':>10}")
    print("-" * 56)

    results = []
    for window in windows:
        for cap in node_caps:
            score, avg_time = sweep_params(policy_path, window, cap, seeds, args.ticks)
            proj = score * 3
            print(f"{window:>8} | {cap:>8} | {score:>10.1f} | {proj:>10.0f} | {avg_time:>9.3f}s")
            results.append((window, cap, score, proj, avg_time))

    print("\n--- Summary of Results (Sorted by Projected Score) ---")
    results.sort(key=lambda r: -r[2])
    for window, cap, score, proj, avg_time in results:
        print(f"WINDOW={window:<3} NODE_CAP={cap:<6} -> Score: {score:.1f} (Proj: {proj:.0f}), Avg Time: {avg_time:.3f}s")


if __name__ == "__main__":
    main()
