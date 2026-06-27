"""Experiment driver: patch a base policy's constants and/or override its layout,
then bench N seeds. One-stop oracle for the optimization sprint.

  python tools/exp.py BASE.py --label foo --window 24 --flow 0.2 --stayer 4 --count 24
  python tools/exp.py BASE.py --label L --layout-json cand.json --count 24
  python tools/exp.py BASE.py --seeds round-0,round-1,round-2   # official seeds

Prints one line: LABEL  mean/seed  proj(x3)  sd  act_s.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from statistics import mean, pstdev

_KIT = Path(__file__).resolve().parent.parent / "refugio-starter-kit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from warehouse.local_runner import run_local  # noqa: E402


def patch_source(src: str, window, node_cap, flow, stayer, waitcap) -> str:
    if window is not None:
        src = re.sub(r"^WINDOW\s*=\s*\d+", f"WINDOW = {window}", src, flags=re.M)
    if node_cap is not None:
        src = re.sub(r"^NODE_CAP\s*=\s*\d+", f"NODE_CAP = {node_cap}", src, flags=re.M)
    if flow is not None:
        src = re.sub(r"^FLOW_PENALTY\s*=\s*[\d.]+", f"FLOW_PENALTY = {flow}", src, flags=re.M)
    if waitcap is not None:
        src = re.sub(r"^WAIT_CAP\s*=\s*\d+", f"WAIT_CAP = {waitcap}", src, flags=re.M)
    if stayer is not None:
        # Stayers reserve their cell for range(WINDOW + 1); cap that horizon.
        src = src.replace(
            "        for t in range(WINDOW + 1):\n            cell_res[(t, n)] = rid",
            f"        for t in range(min({stayer}, WINDOW) + 1):\n            cell_res[(t, n)] = rid",
        )
    return src


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("base", type=Path)
    p.add_argument("--label", default="exp")
    p.add_argument("--window", type=int, default=None)
    p.add_argument("--node-cap", type=int, default=None)
    p.add_argument("--flow", type=float, default=None)
    p.add_argument("--stayer", type=int, default=None)
    p.add_argument("--waitcap", type=int, default=None)
    p.add_argument("--layout-json", type=Path, default=None)
    p.add_argument("--count", type=int, default=24)
    p.add_argument("--seeds", default=None)
    p.add_argument("--ticks", type=int, default=300)
    args = p.parse_args()

    src = patch_source(
        args.base.read_text(encoding="utf-8"),
        args.window, args.node_cap, args.flow, args.stayer, args.waitcap,
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
        fh.write(src)
        tmp = Path(fh.name)

    seeds = ([s.strip() for s in args.seeds.split(",") if s.strip()]
             if args.seeds else [f"bench-{i}" for i in range(args.count)])

    try:
        dels, acts = [], []
        for s in seeds:
            r = run_local(tmp, layout_path=args.layout_json, seeds=(s,),
                          ticks=args.ticks, policy_budget_seconds=None)
            dels.append(r["score"])
            setup = float(r.get("layout_time_seconds", 0.0))
            acts.append(max(0.0, float(r.get("policy_time_seconds", 0.0)) - setup))
    finally:
        tmp.unlink(missing_ok=True)

    m = mean(dels)
    print(f"{args.label:<24} mean={m:6.1f}  proj={m*3:5.0f}  sd={pstdev(dels):4.1f}  "
          f"act={mean(acts):.2f}s  n={len(seeds)}")


if __name__ == "__main__":
    main()
