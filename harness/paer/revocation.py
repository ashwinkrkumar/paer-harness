"""Experiment D: revocation lag replay.

Permission labels copied into an index are a snapshot.  When a source
repository withdraws a document (reclassification, legal hold, deletion), the
index keeps serving it until the next reconciliation.  This experiment replays
a query stream against a real retriever (BM25 over Reuters-21578) while source
revocations arrive, and measures how many queries are served stale under

* E2 reconciliation interval  Delta  in {1 min, 15 min, 60 min, 24 h}
* E4 context re-check         none | cached policy with TTL tau | live policy

Time is simulated; arrivals are Poisson.  Revoked documents are drawn from the
documents that the query stream actually targets, so that revocations are
observable rather than vacuous.
"""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

import numpy as np

from .common import Policy, Principal, Doc


def simulate(retriever, policy: Policy, docs: List[Doc], workload_pairs: List[Tuple[Principal, int]],
             q_index: Dict[int, int], k: int, horizon_h: float, query_rate_h: float, revoke_rate_h: float,
             recon_interval_min: float, e4_mode: str, e4_ttl_min: float = 5.0, seed: int = 20261014) -> Dict:
    rng = random.Random(seed)
    n = len(docs)
    # event times
    n_q = np.random.default_rng(seed).poisson(query_rate_h * horizon_h)
    n_r = np.random.default_rng(seed + 1).poisson(revoke_rate_h * horizon_h)
    q_times = np.sort(np.random.default_rng(seed + 2).uniform(0, horizon_h * 60.0, n_q))     # minutes
    r_times = np.sort(np.random.default_rng(seed + 3).uniform(0, horizon_h * 60.0, n_r))
    targets = sorted({t for _, t in workload_pairs})
    revoked_docs = rng.sample(targets, min(n_r, len(targets)))
    r_times = r_times[: len(revoked_docs)]
    source_revoked_at = np.full(n, np.inf)
    for d, t in zip(revoked_docs, r_times):
        source_revoked_at[d] = t

    base_mask_cache: Dict[Principal, np.ndarray] = {}

    def base_mask(p: Principal) -> np.ndarray:
        if p not in base_mask_cache:
            base_mask_cache[p] = policy.allowed_mask(p)
        return base_mask_cache[p]

    # index labels: reflect revocations only at reconciliation boundaries
    def index_revoked(t_min: float) -> np.ndarray:
        last_recon = (t_min // recon_interval_min) * recon_interval_min
        return source_revoked_at <= last_recon

    # E4 policy view
    def e4_revoked(t_min: float) -> np.ndarray:
        if e4_mode == "live":
            return source_revoked_at <= t_min
        if e4_mode == "cached":
            last_refresh = (t_min // e4_ttl_min) * e4_ttl_min
            return source_revoked_at <= last_refresh
        return np.zeros(n, dtype=bool)

    stale_queries = 0
    stale_docs = 0
    served_docs = 0
    queries_touching_revoked = 0
    lag_samples = []
    for t in q_times:
        p, target = workload_pairs[rng.randrange(len(workload_pairs))]
        idx_rev = index_revoked(t)
        mask = base_mask(p) & ~idx_rev
        ctx = retriever.rank(q_index[target], k, candidate_mask=mask)
        if e4_mode != "none":
            e4 = e4_revoked(t)
            ctx = np.asarray([d for d in ctx if not e4[d]], dtype=np.int64)
        served_docs += len(ctx)
        stale = [d for d in ctx if source_revoked_at[d] <= t]
        if stale:
            stale_queries += 1
            stale_docs += len(stale)
            lag_samples.extend(float(t - source_revoked_at[d]) for d in stale)
        if any(source_revoked_at[d] <= t for d in ctx) or (source_revoked_at[target] <= t):
            queries_touching_revoked += 1
    # index-level revocation lag: time until the index reflects a revocation
    index_lag = [(((t // recon_interval_min) + 1) * recon_interval_min) - t for t in r_times]
    return {
        "recon_interval_min": recon_interval_min, "e4_mode": e4_mode, "e4_ttl_min": e4_ttl_min,
        "queries": int(n_q), "revocations": len(revoked_docs),
        "stale_query_rate": stale_queries / max(n_q, 1),
        "stale_queries": stale_queries, "stale_docs_served": stale_docs,
        "stale_docs_per_10k_queries": 10000.0 * stale_docs / max(n_q, 1),
        "queries_whose_target_or_context_was_revoked": queries_touching_revoked,
        "mean_index_lag_min": float(np.mean(index_lag)) if index_lag else 0.0,
        "p95_index_lag_min": float(np.percentile(index_lag, 95)) if index_lag else 0.0,
        "mean_stale_age_min": float(np.mean(lag_samples)) if lag_samples else 0.0,
        "max_stale_age_min": float(np.max(lag_samples)) if lag_samples else 0.0,
    }
