"""Reliable measurement for layout candidates: CRN bench + paired CI.

Fixes the failure recorded in STRATEGY.md (bench projected 910, official 866):
at few seeds the +-22 between layouts is noise. Here every candidate is measured
on the SAME seeds (Common Random Numbers) and compared to the baseline with a
PAIRED delta + 95% CI, so a real +N emerges even when absolute spread is large.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev

# Engine lives in refugio-starter-kit/.
_KIT = Path(__file__).resolve().parent.parent / "refugio-starter-kit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from warehouse.layout import LayoutValidationError, validate_submitted_layout  # noqa: E402
from warehouse.local_runner import run_local  # noqa: E402

DEFAULT_TICKS = 300
CALIBRATION = 0.95   # official ~= 0.95 x bench projection (904->882, 782->759)


@dataclass
class Measurement:
    name: str
    shelves: int
    valid: bool
    per_seed: dict[str, float] = field(default_factory=dict)
    note: str = "ok"

    @property
    def mean_per_seed(self) -> float:
        return mean(self.per_seed.values()) if self.per_seed else 0.0

    @property
    def projected(self) -> float:
        return self.mean_per_seed * 3

    @property
    def calibrated(self) -> float:
        return self.projected * CALIBRATION


@dataclass
class Delta:
    mean_diff: float     # paired mean of (candidate - baseline) per seed
    ci_low: float
    ci_high: float

    @property
    def verdict(self) -> str:
        if self.ci_low > 0:
            return "SIGNAL+"
        if self.ci_high < 0:
            return "SIGNAL-"
        return "NOISE"


def make_seeds(count: int) -> list[str]:
    return [f"lab-{i}" for i in range(count)]


def bench(name: str, shelves: list[list[int]], policy_path, seeds: list[str],
          ticks: int = DEFAULT_TICKS) -> Measurement:
    """Validate then score `shelves` under `policy_path` on each seed (CRN)."""
    try:
        validate_submitted_layout({"schema_version": 1, "shelves": shelves})
    except LayoutValidationError as exc:
        return Measurement(name, len(shelves), valid=False, note=f"INVALID: {exc}")

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"schema_version": 1, "shelves": shelves}, fh)
        layout_path = Path(fh.name)
    try:
        per_seed = {
            s: float(run_local(Path(policy_path), layout_path=layout_path,
                               seeds=(s,), ticks=ticks,
                               policy_budget_seconds=None)["score"])
            for s in seeds
        }
    finally:
        layout_path.unlink(missing_ok=True)
    return Measurement(name, len(shelves), valid=True, per_seed=per_seed)


def compare(candidate: Measurement, baseline: Measurement) -> Delta:
    """Paired delta over the seeds both measurements share (CRN)."""
    common = [s for s in candidate.per_seed if s in baseline.per_seed]
    diffs = [candidate.per_seed[s] - baseline.per_seed[s] for s in common]
    if not diffs:
        return Delta(0.0, 0.0, 0.0)
    m = mean(diffs)
    n = len(diffs)
    if n < 2:
        return Delta(m, m, m)
    half = 1.96 * stdev(diffs) / math.sqrt(n)
    return Delta(m, m - half, m + half)
