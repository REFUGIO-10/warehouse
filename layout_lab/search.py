"""Grid sweep + hill-climb over layout families, ranked by paired CRN bench.

Run from the repo root (warehouse/):
  python3 layout_lab/search.py                              # grid+hill, 20 seeds, submission.py policy
  python3 layout_lab/search.py --count 30 --phase grid
  python3 layout_lab/search.py --only blocks_2x2,blocks_2x3 --count 20
Writes layout_lab/results/{rankings.json,best_layout.json,REPORT.md}.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from dataclasses import asdict, replace
from itertools import product
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))  # repo root -> `import layout_lab...`

from layout_lab import families, harness  # noqa: E402

Row = tuple[str, "harness.Measurement", "harness.Delta | None"]

GRID: dict[str, list] = {
    "block_w": [2],
    "block_h": [2, 3, 4],
    "aisle": [1, 2],
    "gradient": ["none", "dense_edges", "dense_center"],
    "symmetric": [False, True],
}

DEFAULT_POLICY = _HERE.parent / "submissions" / "submission.py"
RESULTS_DIR = _HERE / "results"


def param_name(p: families.LayoutParams) -> str:
    base = f"w{p.block_w}h{p.block_h}a{p.aisle}_{p.gradient}"
    return base + "_sym" if p.symmetric else base


def iter_grid(grid: dict[str, list] = GRID) -> Iterator[families.LayoutParams]:
    keys = list(grid)
    for combo in product(*(grid[k] for k in keys)):
        yield families.LayoutParams(**dict(zip(keys, combo)))


def grid_search(policy_path, seeds, ticks, params_list) -> tuple["harness.Measurement", list[Row]]:
    baseline_m = harness.bench("baseline", families.canonical_baseline(), policy_path, seeds, ticks)
    rows: list[Row] = [("baseline", baseline_m, None)]
    for p in params_list:
        name = param_name(p)
        m = harness.bench(name, families.generate(p), policy_path, seeds, ticks)
        d = harness.compare(m, baseline_m) if m.valid else None
        rows.append((name, m, d))
    return baseline_m, rows


def _neighbors(p: families.LayoutParams) -> list[families.LayoutParams]:
    out: list[families.LayoutParams] = []
    for bh in (p.block_h - 1, p.block_h + 1):
        if 2 <= bh <= 4:
            out.append(replace(p, block_h=bh))
    for a in (p.aisle - 1, p.aisle + 1):
        if 1 <= a <= 2:
            out.append(replace(p, aisle=a))
    for g in ("none", "dense_edges", "dense_center"):
        if g != p.gradient:
            out.append(replace(p, gradient=g))
    out.append(replace(p, symmetric=not p.symmetric))
    return out


def hill_climb(policy_path, seeds, ticks, start, baseline_m) -> tuple[families.LayoutParams, "harness.Measurement"]:
    current = start
    current_m = harness.bench(param_name(current), families.generate(current), policy_path, seeds, ticks)
    improved = True
    while improved:
        improved = False
        for neighbor in _neighbors(current):
            m = harness.bench(param_name(neighbor), families.generate(neighbor), policy_path, seeds, ticks)
            if not m.valid:
                continue
            if harness.compare(m, current_m).verdict == "SIGNAL+":
                current, current_m = neighbor, m
                improved = True
                break  # greedy: take first significant improvement, re-expand
    return current, current_m


def _layout_snippet(shelves: list[list[int]]) -> str:
    return (
        "def create_layout():\n"
        f"    shelves = {shelves!r}\n"
        '    return {"schema_version": 1, "shelves": shelves}\n'
    )


def write_results(out_dir: Path, baseline_m, rows: list[Row], best_params, best_m) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    ranked = sorted(
        (r for r in rows if r[1].valid),
        key=lambda r: -r[1].mean_per_seed,
    )
    rankings = [
        {
            "name": name,
            "valid": m.valid,
            "shelves": m.shelves,
            "mean_per_seed": round(m.mean_per_seed, 2),
            "projected": round(m.projected, 1),
            "calibrated": round(m.calibrated, 1),
            "delta_vs_baseline": None if d is None else round(d.mean_diff, 2),
            "ci": None if d is None else [round(d.ci_low, 2), round(d.ci_high, 2)],
            "verdict": None if d is None else d.verdict,
        }
        for (name, m, d) in ranked
    ]
    (out_dir / "rankings.json").write_text(json.dumps(rankings, indent=2))

    best_shelves = families.generate(best_params)
    (out_dir / "best_layout.json").write_text(json.dumps({
        "params": asdict(best_params),
        "mean_per_seed": round(best_m.mean_per_seed, 2),
        "projected": round(best_m.projected, 1),
        "calibrated": round(best_m.calibrated, 1),
        "create_layout": _layout_snippet(best_shelves),
        "shelves": best_shelves,
    }, indent=2))

    lines = [
        "# layout_lab — results",
        "",
        f"Baseline (canonical): {baseline_m.mean_per_seed:.1f}/seed "
        f"-> proj {baseline_m.projected:.0f} (calibrated {baseline_m.calibrated:.0f}).",
        "",
        "| layout | /seed | proj | calib | delta | CI | verdict |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rankings:
        ci = "" if r["ci"] is None else f'[{r["ci"][0]}, {r["ci"][1]}]'
        delta = "" if r["delta_vs_baseline"] is None else f'{r["delta_vs_baseline"]:+}'
        lines.append(
            f'| {r["name"]} | {r["mean_per_seed"]} | {r["projected"]} | '
            f'{r["calibrated"]} | {delta} | {ci} | {r["verdict"] or ""} |'
        )
    lines += [
        "",
        f"**Best:** `{param_name(best_params)}` — proj {best_m.projected:.0f} "
        f"(calibrated {best_m.calibrated:.0f}). `create_layout()` in `best_layout.json`.",
        "",
        "> Regenerable output — do not edit by hand; re-run `layout_lab/search.py`.",
    ]
    (out_dir / "REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Search layouts, ranked by paired CRN bench.")
    ap.add_argument("--count", type=int, default=20, help="Number of CRN seeds lab-0..lab-{N-1}.")
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY,
                    help="Submission whose act() measures layouts (its layout is overridden).")
    ap.add_argument("--ticks", type=int, default=300)
    ap.add_argument("--phase", choices=["grid", "hill", "all"], default="all")
    ap.add_argument("--only", default=None,
                    help="Comma-separated REGISTRY names instead of the full grid.")
    args = ap.parse_args()

    seeds = harness.make_seeds(args.count)
    policy = args.policy.resolve()
    print(f"policy={policy.name}  seeds={len(seeds)}  ticks={args.ticks}  phase={args.phase}\n")

    if args.only:
        names = [n.strip() for n in args.only.split(",")]
        # REGISTRY entries are concrete shelf-lists; wrap them as pseudo-params via baseline grid.
        baseline_m = harness.bench("baseline", families.canonical_baseline(), policy, seeds, args.ticks)
        rows: list[Row] = [("baseline", baseline_m, None)]
        for n in names:
            m = harness.bench(n, families.REGISTRY[n](), policy, seeds, args.ticks)
            d = harness.compare(m, baseline_m) if m.valid else None
            rows.append((n, m, d))
    else:
        params_list = list(iter_grid())
        baseline_m, rows = grid_search(policy, seeds, args.ticks, params_list)

    for name, m, d in rows:
        if not m.valid:
            print(f"  {name:>22}  {m.note}")
        else:
            v = "" if d is None else f"  [{d.verdict} {d.mean_diff:+.1f}]"
            print(f"  {name:>22}  {m.mean_per_seed:6.1f}/seed -> proj {m.projected:.0f}{v}")

    valid_cand = [(n, m) for (n, m, _d) in rows if m.valid and n != "baseline"]
    best_name, best_m = max(valid_cand, key=lambda t: t[1].mean_per_seed) if valid_cand else ("baseline", baseline_m)

    best_params = families.LayoutParams(2, 2, 1, "none", False)
    if not args.only:
        for p in params_list:
            if param_name(p) == best_name:
                best_params = p
                break
        if args.phase in ("hill", "all"):
            best_params, best_m = hill_climb(policy, seeds, args.ticks, best_params, baseline_m)
            print(f"\nhill-climb best: {param_name(best_params)} -> proj {best_m.projected:.0f}")
    else:
        _registry_params = {
            "blocks_2x2": families.LayoutParams(2, 2, 1, "none", False),
            "blocks_2x3": families.LayoutParams(2, 3, 1, "none", False),
        }
        best_params = _registry_params.get(best_name, best_params)

    write_results(RESULTS_DIR, baseline_m, rows, best_params, best_m)
    print(f"\nwrote {RESULTS_DIR}/rankings.json, best_layout.json, REPORT.md")


if __name__ == "__main__":
    main()
