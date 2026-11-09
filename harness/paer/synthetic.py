"""Experiment A: the controlled mirrored-tenant benchmark.

Three tenants hold mirror-image copies of the same 30 topics (overview,
procedure, escalation documents).  Retrieval is lexical token overlap with
deterministic tie-breaking on document id, top-k = 2.  The construction makes
the failure mode of top-k-only post-filtering visible in closed form; the
numbers are properties of the construction, not estimates for deployed systems.
"""

from __future__ import annotations

import random
import re
import time
from typing import Dict, List, Tuple

import numpy as np

from .common import Doc, Policy, Principal, Retriever, Tally, run_design, percentile_summary

SEED = 20261014
N_TENANTS = 3
N_TOPICS = 30
DOC_TYPES = ("overview", "procedure", "escalation")
TOP_K = 2

TOPIC_WORDS = [
    "vendor onboarding", "incident response", "payroll processing", "access review", "data retention",
    "change management", "backup restore", "patch deployment", "network segmentation", "key rotation",
    "customer refund", "contract renewal", "travel reimbursement", "device enrollment", "phishing report",
    "quality audit", "supplier scorecard", "warehouse receiving", "asset disposal", "budget approval",
    "hiring requisition", "performance review", "vulnerability triage", "log retention", "firewall exception",
    "disaster recovery", "privacy request", "export compliance", "safety inspection", "release freeze",
]

FILLER = ("this document describes the standard practice and the responsible team "
          "it lists the required inputs the expected outputs and the owner of each step").split()


def _tokens(s: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def build_corpus(seed: int = SEED) -> List[Doc]:
    rng = random.Random(seed)
    docs: List[Doc] = []
    doc_id = 0
    for t in range(N_TENANTS):
        for topic_idx, topic in enumerate(TOPIC_WORDS):
            for dtype in DOC_TYPES:
                clearance = "restricted" if dtype == "escalation" else "general"
                canary = f"CANARY-T{t}-K{topic_idx:02d}-{dtype[:3].upper()}-{rng.randrange(10**6):06d}"
                body = (f"{topic} {dtype} document for tenant {t}. "
                        f"{' '.join(FILLER)}. reference code {canary}.")
                docs.append(Doc(doc_id=doc_id, tenant=t, clearance=clearance, text=body,
                                title=f"{topic} {dtype}", canary=canary))
                doc_id += 1
    return docs


def build_workload(docs: List[Doc], seed: int = SEED) -> Tuple[List[Tuple[Principal, str, int]], List[Tuple[Principal, str, int]]]:
    """900 authorized queries (5 per tenant x topic x role) and 90 cross-tenant probes."""
    rng = random.Random(seed + 1)
    by_key: Dict[Tuple[int, int, str], Doc] = {}
    for d in docs:
        topic_idx = TOPIC_WORDS.index(d.title.rsplit(" ", 1)[0])
        by_key[(d.tenant, topic_idx, d.title.rsplit(" ", 1)[1])] = d
    phrasings = ["what is the {topic} {dtype}", "show me the {topic} {dtype}", "{topic} {dtype} details",
                 "find {topic} {dtype}", "{dtype} for {topic}"]
    authorized = []
    for t in range(N_TENANTS):
        for topic_idx, topic in enumerate(TOPIC_WORDS):
            for role in ("analyst", "manager"):
                permitted_types = ["overview", "procedure"] if role == "analyst" else list(DOC_TYPES)
                for i in range(5):
                    dtype = permitted_types[i % len(permitted_types)]
                    q = phrasings[i].format(topic=topic, dtype=dtype)
                    authorized.append((Principal(t, role), q, by_key[(t, topic_idx, dtype)].doc_id))
    probes = []
    for t in range(N_TENANTS):
        for topic_idx, topic in enumerate(TOPIC_WORDS):
            other = (t + 1 + rng.randrange(N_TENANTS - 1)) % N_TENANTS
            dtype = rng.choice(["overview", "procedure"])
            q = f"{topic} {dtype} for the other business unit"
            probes.append((Principal(t, "manager"), q, by_key[(other, topic_idx, dtype)].doc_id))
    return authorized, probes


class LexicalOverlapRetriever(Retriever):
    """Score = number of distinct query tokens present in the document; ties broken by doc id."""

    def __init__(self, docs: List[Doc], queries: List[str]):
        vocab: Dict[str, int] = {}
        rows = []
        for d in docs:
            toks = set(_tokens(d.text))
            rows.append(toks)
            for tok in toks:
                vocab.setdefault(tok, len(vocab))
        self.V = len(vocab)
        self.D = np.zeros((len(docs), self.V), dtype=np.int8)
        for i, toks in enumerate(rows):
            for tok in toks:
                self.D[i, vocab[tok]] = 1
        self.Q = np.zeros((len(queries), self.V), dtype=np.int8)
        for i, q in enumerate(queries):
            for tok in set(_tokens(q)):
                if tok in vocab:
                    self.Q[i, vocab[tok]] = 1
        self.ids = np.arange(len(docs))

    def rank(self, query_idx: int, k: int, candidate_mask=None) -> np.ndarray:
        q = self.Q[query_idx].astype(np.int32)
        if candidate_mask is not None:
            # pre-filtering: score only the permitted candidate set
            idx = self.ids[candidate_mask]
            s = self.D[candidate_mask].astype(np.int32) @ q
        else:
            idx = self.ids
            s = self.D.astype(np.int32) @ q
        order = np.lexsort((idx, -s))
        return idx[order[:k]]


def run(seed: int = SEED, timing_repeats: int = 5) -> Dict:
    docs = build_corpus(seed)
    authorized, probes = build_workload(docs, seed)
    policy = Policy(docs)
    all_queries = [q for _, q, _ in authorized] + [q for _, q, _ in probes]
    retriever = LexicalOverlapRetriever(docs, all_queries)
    n_auth = len(authorized)

    designs = [("unfiltered", "unfiltered", 1), ("postfilter_topk", "postfilter", 1),
               ("postfilter_overfetch5", "postfilter", 5), ("prefilter", "prefilter", 1)]

    out: Dict = {"seed": seed, "n_docs": len(docs), "n_authorized": n_auth, "n_probes": len(probes),
                 "top_k": TOP_K, "designs": {}}

    # E1: metadata completeness
    out["e1_metadata_complete"] = all(d.canary and d.title and d.clearance in ("general", "restricted") for d in docs)

    for name, design, of in designs:
        tally_auth, tally_probe = Tally(), Tally()
        canary_leaks = 0
        gated_leaks = 0
        probe_target_reached = 0
        for qi, (p, _, target) in enumerate(authorized):
            res = run_design(design, retriever, policy, p, qi, TOP_K, of)
            # E4 context re-check
            tally_auth.e4_failures += sum(1 for d in res.context if not policy.allowed(p, int(d)) and design != "unfiltered")
            tally_auth.add(res, policy, p, target)
            # E5: canary echo proxy + ACL output gate
            echo = " ".join(docs[d].text for d in res.context)
            restricted_canaries = [docs[d].canary for d in res.context if not policy.allowed(p, int(d))]
            if any(c in echo for c in restricted_canaries):
                canary_leaks += 1
            gated = " ".join(docs[d].text for d in res.context if policy.allowed(p, int(d)))
            if any(c in gated for c in restricted_canaries):
                gated_leaks += 1
        for qi, (p, _, target) in enumerate(probes):
            res = run_design(design, retriever, policy, p, n_auth + qi, TOP_K, of)
            tally_probe.add(res, policy, p, None)
            if target in res.context:
                probe_target_reached += 1
        s = tally_auth.summary()
        s["canary_echo_leak_rate"] = canary_leaks / n_auth
        s["canary_leak_rate_after_output_gate"] = gated_leaks / n_auth
        sp = tally_probe.summary()
        sp["foreign_target_reached_rate"] = probe_target_reached / len(probes)
        out["designs"][name] = {"authorized": s, "probes": sp}

    # E2: synchronous revocation smoke test
    p0, q0, target0 = authorized[0]
    before = {}
    for name, design, of in designs[1:]:
        before[name] = target0 in run_design(design, retriever, policy, p0, 0, TOP_K, of).context
    policy.revoke(target0, "analyst")
    after = {}
    for name, design, of in designs[1:]:
        after[name] = target0 in run_design(design, retriever, policy, p0, 0, TOP_K, of).context
    policy.denied.clear()
    out["e2_revocation"] = {"present_before": before, "present_after": after,
                            "passed": all(before.values()) and not any(after.values())}

    # timing microbenchmark
    timing = {}
    for name, design, of in designs:
        per_query = []
        for _ in range(timing_repeats):
            for qi, (p, _, _) in enumerate(authorized):
                t0 = time.perf_counter()
                run_design(design, retriever, policy, p, qi, TOP_K, of)
                per_query.append((time.perf_counter() - t0) * 1000.0)
        timing[name] = percentile_summary(per_query)
    out["timing_ms"] = timing
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
