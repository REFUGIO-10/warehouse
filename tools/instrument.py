"""Tally where robot-ticks go for a submission, to find the lever with headroom.

  python tools/instrument.py SUBMISSION.py --seed bench-0 [--layout-json L.json]

Counts, across all robots x ticks: deliveries, productive MOVEs, PICKUP, DROP,
voluntary WAIT (asked to wait), and BLOCKED moves by reason (vertex/edge/static).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

_KIT = Path(__file__).resolve().parent.parent / "refugio-starter-kit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from warehouse.actions import Action  # noqa: E402
from warehouse.layout import load_submitted_layout  # noqa: E402
from warehouse.simulation import run_simulation  # noqa: E402
from warehouse.submission_loader import (  # noqa: E402
    load_submission,
    load_submission_with_layout,
    sanitized_submission_argv,
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("submission", type=Path)
    p.add_argument("--seed", default="bench-0")
    p.add_argument("--layout-json", type=Path, default=None)
    p.add_argument("--ticks", type=int, default=300)
    args = p.parse_args()

    with sanitized_submission_argv(args.submission):
        if args.layout_json is None:
            loaded = load_submission_with_layout(args.submission, setup_budget_seconds=None)
            policy, layout = loaded.act, loaded.layout
        else:
            policy = load_submission(args.submission)
            layout = load_submitted_layout(args.layout_json)

        sim = run_simulation(args.seed, policy, ticks=args.ticks, layout=layout,
                             record_ticks=True)

    c: Counter[str] = Counter()
    total = 0
    for tr in sim.tick_results:
        for rid, res in tr.action_results.items():
            total += 1
            act = res.action
            if res.blocked:
                if act in (Action.PICKUP, Action.DROP):
                    c[f"blocked_{act.value}_{res.reason}"] += 1
                else:
                    c[f"revert_{res.reason}"] += 1
            elif act == Action.WAIT:
                c["wait_voluntary"] += 1
            elif act in (Action.PICKUP, Action.DROP):
                c[act.value] += 1
            else:
                c["move"] += 1

    deliveries = sum(r.deliveries for r in sim.final_robots)
    print(f"seed={args.seed}  deliveries={deliveries}  robot-ticks={total}")
    print("-" * 50)
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<34} {v:>7}  ({100*v/total:4.1f}%)")


if __name__ == "__main__":
    main()
