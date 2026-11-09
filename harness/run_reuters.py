"""Driver for Experiments B (enforcement placement on a real corpus) and C (existence oracle).

Usage: python run_reuters.py --root <reuters dir> --out <results dir> [--quick]
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paer.common import Policy, Principal  # noqa: E402
from paer.reuters import (SEED, DESIGNS, BM25Retriever, DenseRetriever, QueryGenerator, assign_policy,
                          build_workload, embed_texts, evaluate, existence_oracle, load_reuters)  # noqa: E402

HELDOUT = 400


def run_config(all_docs, doc_vecs_all, n_tenants, restricted_frac, k, corpus_size, per_principal,
               probes_per_tenant, seed, do_oracle, timing, mode="headline"):
    rng = random.Random(seed + 101)
    idx = list(range(len(all_docs)))
    rng.shuffle(idx)
    heldout_idx = idx[:HELDOUT]            # never indexed; negatives for the existence oracle
    pool = idx[HELDOUT:]
    if corpus_size is not None:
        pool = pool[:corpus_size]
    pool.sort()
    docs = [copy.copy(all_docs[i]) for i in pool]
    for new_id, d in enumerate(docs):
        d.doc_id = new_id
    assign_policy(docs, n_tenants, restricted_frac, seed)
    policy = Policy(docs)
    qgen = QueryGenerator(docs, seed, mode)
    wl = build_workload(docs, policy, qgen, n_tenants, per_principal, probes_per_tenant, seed)

    attacker = Principal(0, "analyst")
    restricted_t0 = [d.doc_id for d in docs if d.tenant == 0 and d.clearance == "restricted"]
    other_tenant = [d.doc_id for d in docs if d.tenant != 0] if n_tenants > 1 else []
    rng2 = random.Random(seed + 131)
    pos_restricted = rng2.sample(restricted_t0, min(300, len(restricted_t0)))
    pos_cross = rng2.sample(other_tenant, min(300, len(other_tenant))) if other_tenant else []
    queries = list(wl.queries)
    q_index = dict(wl.q_index)

    def q_for(doc_id):
        if doc_id not in q_index:
            q_index[doc_id] = len(queries)
            queries.append(qgen.query_for(docs[doc_id], doc_id))
        return q_index[doc_id]

    pos_restricted_q = [q_for(d) for d in pos_restricted]
    pos_cross_q = [q_for(d) for d in pos_cross]
    heldout_docs = [all_docs[i] for i in heldout_idx]
    hq = QueryGenerator(heldout_docs, seed, mode)
    neg_offset = len(queries)
    for j, d in enumerate(heldout_docs):
        queries.append(hq.query_for(d, j))
    neg_q = list(range(neg_offset, len(queries)))
    wl.queries, wl.q_index = queries, q_index

    results = {"config": {"n_tenants": n_tenants, "restricted_frac": restricted_frac, "k": k,
                          "corpus_size": len(docs), "authorized_queries": len(wl.authorized),
                          "probes": len(wl.probes), "heldout": HELDOUT, "query_mode": mode, "seed": seed},
               "authorized_fraction": {}}
    for t in range(n_tenants):
        for role in ("analyst", "manager"):
            results["authorized_fraction"][f"t{t}_{role}"] = float(policy.allowed_mask(Principal(t, role)).mean())
    results["attacker_authorized_fraction"] = float(policy.allowed_mask(attacker).mean())

    t0 = time.perf_counter()
    bm25 = BM25Retriever(docs, queries)
    results["bm25"] = evaluate(bm25, policy, wl, k, timing=timing)
    if do_oracle:
        results["bm25_oracle_restricted"] = existence_oracle(bm25, policy, attacker, pos_restricted_q, neg_q, k)
        if pos_cross_q:
            results["bm25_oracle_cross_tenant"] = existence_oracle(bm25, policy, attacker, pos_cross_q, neg_q, k)
    results["bm25_seconds"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    doc_vecs = doc_vecs_all[pool]
    q_vecs = embed_texts(queries)
    dense = DenseRetriever(doc_vecs, q_vecs)
    results["dense"] = evaluate(dense, policy, wl, k, timing=timing)
    if do_oracle:
        results["dense_oracle_restricted"] = existence_oracle(dense, policy, attacker, pos_restricted_q, neg_q, k)
        if pos_cross_q:
            results["dense_oracle_cross_tenant"] = existence_oracle(dense, policy, attacker, pos_cross_q, neg_q, k)
    results["dense_seconds"] = time.perf_counter() - t0
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    all_docs = load_reuters(args.root)
    print(f"loaded {len(all_docs)} documents", flush=True)
    t0 = time.perf_counter()
    doc_vecs_all = embed_texts([d.title + ". " + d.text for d in all_docs])
    print(f"embedded corpus in {time.perf_counter()-t0:.1f}s", flush=True)

    pp = 150 if args.quick else 300
    ppt = 150 if args.quick else 300

    def dump(obj, name):
        json.dump(obj, open(os.path.join(args.out, name), "w"), indent=2)

    # B1: main configuration, headline queries, with timing and oracle
    main_cfg = run_config(all_docs, doc_vecs_all, 3, 1 / 3, 5, None, pp, ppt, SEED, True, True, "headline")
    dump(main_cfg, "expB_main.json"); print("main done", flush=True)

    # B2: secondary workload, sentence queries
    sent_cfg = run_config(all_docs, doc_vecs_all, 3, 1 / 3, 5, None, pp, ppt, SEED, False, False, "sentence")
    dump(sent_cfg, "expB_sentence.json"); print("sentence done", flush=True)

    # B3: sweeps
    sweeps = {"tenants": [], "restricted": [], "k": [], "corpus": []}
    for T in [1, 2, 3, 5, 10]:
        sweeps["tenants"].append(run_config(all_docs, doc_vecs_all, T, 1 / 3, 5, None, pp, ppt, SEED, False, False))
        print(f"tenants={T}", flush=True)
    for p in [0.1, 1 / 3, 0.5, 0.7]:
        sweeps["restricted"].append(run_config(all_docs, doc_vecs_all, 3, p, 5, None, pp, ppt, SEED, False, False))
        print(f"restricted={p:.2f}", flush=True)
    for k in [2, 5, 10]:
        sweeps["k"].append(run_config(all_docs, doc_vecs_all, 3, 1 / 3, k, None, pp, ppt, SEED, False, False))
        print(f"k={k}", flush=True)
    for n in [1000, 2500, 5000, None]:
        sweeps["corpus"].append(run_config(all_docs, doc_vecs_all, 3, 1 / 3, 5, n, pp, ppt, SEED, False, False))
        print(f"corpus={n}", flush=True)
    dump(sweeps, "expB_sweeps.json")

    # B4: seed robustness
    seeds = [run_config(all_docs, doc_vecs_all, 3, 1 / 3, 5, None, pp, ppt, s, False, False)
             for s in [SEED, SEED + 1, SEED + 2, SEED + 3, SEED + 4]]
    dump(seeds, "expB_seeds.json"); print("seeds done", flush=True)

    # C: existence oracle across attacker privilege levels (tenants x restricted fraction)
    oracle = []
    for T in [1, 2, 3, 5]:
        for p in [0.1, 1 / 3, 0.5]:
            r = run_config(all_docs, doc_vecs_all, T, p, 5, None, 50, 50, SEED, True, False)
            oracle.append({"config": r["config"], "attacker_authorized_fraction": r["attacker_authorized_fraction"],
                           **{key: r[key] for key in r if "oracle" in key}})
            print(f"oracle T={T} p={p:.2f}", flush=True)
    dump(oracle, "expC_oracle.json")
    print("all done", flush=True)


if __name__ == "__main__":
    main()
