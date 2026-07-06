# `layout_lab/` — layout search (isolated)

Self-contained lab to find better shelf layouts **reliably**. It exists because
the bench lied once: `WHCA* + locked + blocks_2x2` projected 910 (6 seeds) but
scored **866** official (< 888). At few seeds the +-22 between layouts is noise.
This lab measures with **Common Random Numbers** (same seeds for every
candidate) and reports a **paired delta + 95% CI** with a SIGNAL/NOISE verdict,
then searches a parametrized layout space.

> Touches nothing outside this folder. Reads the engine (`refugio-starter-kit/`)
> and a policy file; writes only to `layout_lab/results/`. When it finds a
> winner it emits a pasteable `create_layout()` — a human decides if/when to
> wire it into `submissions/`.

## Run (from the repo root, `warehouse/`)

```bash
python3 layout_lab/search.py                       # full grid + hill-climb, 20 CRN seeds
python3 layout_lab/search.py --count 30 --phase grid
python3 layout_lab/search.py --only blocks_2x2,blocks_2x3 --count 20
python3 layout_lab/search.py --policy submissions/sota_equipo02.py   # measure vs another policy
```

Default policy is `submissions/submission.py` (its own layout is overridden, only
its `act()` is used). Pure stdlib — no install. ~40 s/candidate with a heavy
policy at 20 seeds, so the full 36-combo grid is ~20 min; use `--only` or a
smaller `--count` to iterate fast.

## Read the results (`layout_lab/results/`, regenerable — don't edit)

- `REPORT.md` — ranked table: `/seed`, projection (×3), **calibrated** (×0.95 ≈
  official), paired delta vs baseline, CI, and **verdict**. Trust SIGNAL+, ignore
  NOISE.
- `rankings.json` — same data as JSON.
- `best_layout.json` — winning params, scores, the 960 shelves, and a pasteable
  `create_layout()`.

## Files

| File | Responsibility |
|---|---|
| `families.py` | `LayoutParams` + `generate()` (block shape / aisle / gradient / symmetry); `REGISTRY` of named layouts. |
| `harness.py` | `bench()` (validate + score on CRN seeds), `compare()` (paired delta + CI), `Measurement`/`Delta`. |
| `search.py` | grid sweep + hill-climb; writes `results/`. CLI entry point. |
| `surrogate.py` | **stub**: future analytic prefilter (score without the sim). |

## Design space (what the search varies)

- `block_w` (≤2; wider traps inner cells = invalid), `block_h ∈ {2,3,4}`.
- `aisle ∈ {1,2}` between blocks, both directions (cross-aisle on every edge).
- `gradient ∈ {none, dense_edges, dense_center}` — the distance↔congestion knob.
- `symmetric` — 4-fold symmetry with a central cross-aisle.

Confirmed lever: thin blocks with a cross-aisle on every edge (Equipo 03, +38).
Long rows regress; over-density collapses. The lab quantifies which combo wins.
