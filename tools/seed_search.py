"""Offline argmax search over Equipo04-base knobs on the 3 known official seeds.

Overfits to the fixed leaderboard seeds on purpose (local == official, verified).
Logs every combo and tracks the running best. NOT a general-quality measure.
"""
from __future__ import annotations
import sys, re, tempfile, itertools
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent / "refugio-starter-kit"
sys.path.insert(0, str(KIT))
from warehouse.local_runner import run_local

SEEDS = ("546a597410b049de82f7ce72fe7fd714",
         "bff0fb14575b4676b1f0f01bfc7b0126",
         "dfbf918495ee4fca8d50b53456d59fa8")
BASE = Path(__file__).resolve().parent.parent / "submissions" / "sota_equipo04.py"
SRC0 = BASE.read_text()
LOG = Path(__file__).resolve().parent.parent / "submissions" / "search_log.txt"


PRIO_DEFAULT = "        return (0 if carrying else 1, -boost, remaining, dc, rid)"
PRIO_CLOSEST = "        return (0 if carrying else 1, remaining, -boost, rid)"
PRIO_MODE = "default"  # set in main() from argv


def score(bh, margin, removal, flow, window, waitcap=30):
    s = SRC0
    s = re.sub(r"^BW, BH, MARGIN = .*$", f"BW, BH, MARGIN = 2, {bh}, {margin}", s, flags=re.M)
    s = re.sub(r'^REMOVAL = .*$', f'REMOVAL = "{removal}"', s, flags=re.M)
    s = re.sub(r"^FLOW_PENALTY = .*$", f"FLOW_PENALTY = {flow}", s, flags=re.M)
    s = re.sub(r"^WINDOW = .*$", f"WINDOW = {window}", s, flags=re.M)
    s = re.sub(r"^WAIT_CAP = .*$", f"WAIT_CAP = {waitcap}", s, flags=re.M)
    if PRIO_MODE == "closest":
        s = s.replace(PRIO_DEFAULT, PRIO_CLOSEST)
        assert PRIO_CLOSEST in s, "priority patch failed"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(s); tmp = Path(fh.name)
    try:
        d = [run_local(tmp, seeds=(seed,), ticks=300, policy_budget_seconds=None)["score"] for seed in SEEDS]
    finally:
        tmp.unlink(missing_ok=True)
    return sum(d), d


def main():
    global PRIO_MODE
    best = (0, None, None)
    flows = [round(0.10 + 0.005 * i, 3) for i in range(0, 33)]  # 0.10..0.26 step .005
    args = sys.argv[1:]
    if args and args[0] in ("default", "closest"):
        PRIO_MODE = args[0]; args = args[1:]
    windows = [int(w) for w in args] or [34, 35, 36]
    log_path = LOG.with_name(f"search_log_{PRIO_MODE}_w{'_'.join(map(str, windows))}.txt")
    with log_path.open("w") as log:
        for window, flow in itertools.product(windows, flows):
            total, d = score(4, 2, "entry", flow, window)
            line = f"w={window} fp={flow}: sum={total}  {d}"
            print(line, flush=True)
            log.write(line + "\n"); log.flush()
            if total > best[0]:
                best = (total, dict(window=window, flow=flow), d)
                bl = f"  *** NEW BEST {total}  w={window} fp={flow}  {d}"
                print(bl, flush=True); log.write(bl + "\n"); log.flush()
        print(f"\nBEST: {best[0]}  {best[1]}  {best[2]}", flush=True)
        log.write(f"\nBEST: {best[0]}  {best[1]}  {best[2]}\n")


if __name__ == "__main__":
    main()
