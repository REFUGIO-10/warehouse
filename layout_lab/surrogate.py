"""STUB: cheap analytic layout score to prefilter candidates before benching.

Idea (NOT yet implemented): score a layout WITHOUT running the simulator, e.g.
  sum over shelf pickup-cells of distance to nearest base   (travel proxy)
  + a congestion proxy from aisle width / local shelf density.
Rank thousands of candidates by it, then bench only the top-K. Build this only
once the grid sweep is the bottleneck (WHCA* ~2 s/seed x 20 seeds ~ 40 s per
candidate). Until then prefilter() is an identity passthrough so search.py can
call it unconditionally.
"""
from __future__ import annotations


def prefilter(candidates, top_k=None):
    """No-op until implemented: return candidates unchanged."""
    return list(candidates)
