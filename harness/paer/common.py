"""Shared policy model, enforcement designs, and metrics.

Policy model
------------
Every document carries a tenant label and a clearance label.  A principal is a
(tenant, role) pair.  The policy is deliberately simple so that every result is
attributable to enforcement placement rather than to policy expressiveness:

* a principal may read a document only if the tenant labels match (T1 boundary)
* clearance "general"    is readable by analysts and managers
* clearance "restricted" is readable by managers only

Enforcement designs
-------------------
D0  unfiltered            rank the whole corpus, return top-k
D1  post-filter (top-k)   rank the whole corpus, drop unauthorized from top-k
D2  post-filter (m x k)   rank the whole corpus, take top m*k, drop unauthorized, keep k
D3  pre-filter            restrict the candidate set to authorized docs, then rank
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

ROLES = ("analyst", "manager")
CLEARANCES = ("general", "restricted")


@dataclass(frozen=True)
class Principal:
    tenant: int
    role: str


@dataclass
class Doc:
    doc_id: int
    tenant: int
    clearance: str
    text: str
    title: str = ""
    canary: str = ""


class Policy:
    """Live policy store.  Supports synchronous revocation of a single doc."""

    def __init__(self, docs: Sequence[Doc]):
        self.tenant = np.array([d.tenant for d in docs], dtype=np.int32)
        self.restricted = np.array([d.clearance == "restricted" for d in docs], dtype=bool)
        # per-document explicit denies (doc_id -> set of roles denied), for revocation tests
        self.denied: Dict[int, set] = {}
        self.version = 0

    def allowed_mask(self, p: Principal) -> np.ndarray:
        mask = self.tenant == p.tenant
        if p.role == "analyst":
            mask &= ~self.restricted
        if self.denied:
            for doc_id, roles in self.denied.items():
                if p.role in roles:
                    mask[doc_id] = False
        return mask

    def allowed(self, p: Principal, doc_id: int) -> bool:
        if self.tenant[doc_id] != p.tenant:
            return False
        if p.role == "analyst" and self.restricted[doc_id]:
            return False
        if doc_id in self.denied and p.role in self.denied[doc_id]:
            return False
        return True

    def revoke(self, doc_id: int, role: str) -> None:
        self.denied.setdefault(doc_id, set()).add(role)
        self.version += 1


# --------------------------------------------------------------------------- #
# Retrieval interface
# --------------------------------------------------------------------------- #
class Retriever:
    """A retriever exposes ranked candidate lists, optionally over a subset."""

    def rank(self, query_idx: int, k: int, candidate_mask: Optional[np.ndarray] = None) -> np.ndarray:
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Designs
# --------------------------------------------------------------------------- #
@dataclass
class RetrievalResult:
    context: List[int]              # doc ids that entered the context
    candidates: List[int]           # doc ids in the candidate list before any post-filter
    returned_count: int             # number of docs the system returned (observable to the user)


def run_design(design: str, retriever: Retriever, policy: Policy, p: Principal, query_idx: int,
               k: int, overfetch: int = 1) -> RetrievalResult:
    if design == "unfiltered":
        cands = retriever.rank(query_idx, k)
        ctx = list(cands)
        return RetrievalResult(ctx, list(cands), len(ctx))
    if design == "postfilter":
        cands = retriever.rank(query_idx, k * overfetch)
        ctx = [d for d in cands if policy.allowed(p, int(d))][:k]
        return RetrievalResult(ctx, list(cands), len(ctx))
    if design == "prefilter":
        mask = policy.allowed_mask(p)
        cands = retriever.rank(query_idx, k, candidate_mask=mask)
        ctx = list(cands)
        return RetrievalResult(ctx, list(cands), len(ctx))
    raise ValueError(design)


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
@dataclass
class Tally:
    n_queries: int = 0
    ctx_docs: int = 0
    ctx_unauth: int = 0
    q_exposed: int = 0
    cand_docs: int = 0
    cand_unauth: int = 0
    target_hit: int = 0
    e4_failures: int = 0            # context re-check failures (should be 0 for filtered designs)
    returned_counts: List[int] = field(default_factory=list)

    def add(self, res: RetrievalResult, policy: Policy, p: Principal, target: Optional[int]):
        self.n_queries += 1
        unauth = [d for d in res.context if not policy.allowed(p, int(d))]
        self.ctx_docs += len(res.context)
        self.ctx_unauth += len(unauth)
        self.q_exposed += 1 if unauth else 0
        self.cand_docs += len(res.candidates)
        self.cand_unauth += sum(1 for d in res.candidates if not policy.allowed(p, int(d)))
        if target is not None and target in res.context:
            self.target_hit += 1
        self.returned_counts.append(res.returned_count)

    def summary(self) -> Dict[str, float]:
        n = max(self.n_queries, 1)
        return {
            "queries": self.n_queries,
            "unauthorized_context_rate": self.ctx_unauth / max(self.ctx_docs, 1),
            "query_exposure_rate": self.q_exposed / n,
            "candidate_unauthorized_rate": self.cand_unauth / max(self.cand_docs, 1),
            "target_recall": self.target_hit / n,
            "mean_context_docs": self.ctx_docs / n,
            "provenance_fidelity": 1.0 - self.ctx_unauth / max(self.ctx_docs, 1),
            "e4_failures": self.e4_failures,
        }


def auc_from_scores(pos: Sequence[float], neg: Sequence[float]) -> float:
    """Mann-Whitney AUC: probability that a random positive scores above a random negative."""
    pos = np.asarray(pos, dtype=float)
    neg = np.asarray(neg, dtype=float)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    # rank-based computation with tie handling
    allv = np.concatenate([pos, neg])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv), dtype=float)
    sorted_vals = allv[order]
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    r_pos = ranks[: len(pos)].sum()
    n1, n2 = len(pos), len(neg)
    return float((r_pos - n1 * (n1 + 1) / 2.0) / (n1 * n2))


def percentile_summary(xs: Iterable[float]) -> Dict[str, float]:
    a = np.asarray(list(xs), dtype=float)
    return {
        "median": float(np.median(a)),
        "p95": float(np.percentile(a, 95)),
        "q1": float(np.percentile(a, 25)),
        "q3": float(np.percentile(a, 75)),
        "mean": float(a.mean()),
    }
