"""Driver for Experiment E: enforcement cost on real vector indexes."""

from __future__ import annotations

import os
# Single-query latency is the quantity of interest, so OpenMP is limited to one thread for the
# whole process. Setting it before any numeric library loads also avoids OpenMP runtime conflicts
# that crash FAISS on some macOS installations.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import faulthandler
faulthandler.enable()

import argparse
import json
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paer.reuters import SEED, QueryGenerator, embed_texts, load_reuters  # noqa: E402
from paer.latency import augment, labels_for, run_faiss, run_partitioned, run_qdrant  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sizes", default="10000,50000,100000,250000")
    ap.add_argument("--qdrant_max", type=int, default=50000)
    args = ap.parse_args()
    docs = load_reuters(args.root)
    base = embed_texts([d.title + ". " + d.text for d in docs])
    qgen = QueryGenerator(docs, SEED, "headline")
    rng = np.random.default_rng(SEED)
    qids = rng.choice(len(docs), 200, replace=False)
    Q = embed_texts([qgen.query_for(docs[i], i) for i in qids])
    k, overfetch = 5, [1, 5, 20]
    results = []
    for n in [int(s) for s in args.sizes.split(",")]:
        X = augment(base, n, SEED)
        for n_tenants in [3, 10]:
            tenant, restricted = labels_for(n, n_tenants, 1 / 3, SEED)
            for role in ["analyst", "manager"]:
                allowed = (tenant == 0) & (~restricted if role == "analyst" else np.ones(n, bool))
                t0 = time.perf_counter()
                rec = {"n": n, "n_tenants": n_tenants, "principal": f"t0_{role}", "selectivity": float(allowed.mean())}
                rec.update(run_faiss(X, Q, allowed, k, overfetch))
                # exact truths for partitioned / qdrant recall
                import faiss
                flat = faiss.IndexFlatIP(X.shape[1]); flat.add(X)
                sel = faiss.IDSelectorBatch(np.flatnonzero(allowed).astype(np.int64))
                truths = [flat.search(q[None, :], k, params=faiss.SearchParameters(sel=sel))[1][0] for q in Q]
                truth_map = {i: truths[i] for i in range(len(Q))}
                qi = {q.tobytes(): i for i, q in enumerate(Q)}
                rec["partitioned"] = run_partitioned(X, Q, tenant, restricted, 0, role, k, lambda q: truth_map[qi[q.tobytes()]])
                if n <= args.qdrant_max:
                    rec["qdrant"] = run_qdrant(X, Q, tenant, restricted, 0, role, k, overfetch, truths)
                rec["seconds"] = time.perf_counter() - t0
                results.append(rec)
                fp = rec["flat_prefilter"]["timing_ms"]["median"]; fpx1 = rec["flat_postfilter_x1"]
                hp = rec["hnsw_prefilter"]; hx1 = rec["hnsw_postfilter_x1"]; hx20 = rec["hnsw_postfilter_x20"]
                print(f"n={n} T={n_tenants} {role:7s} sel={allowed.mean():.2f} | flat pre {fp:.2f}ms | flat post x1 {fpx1['timing_ms']['median']:.2f}ms R={fpx1['recall']:.2f} "
                      f"| hnsw pre {hp['timing_ms']['median']:.2f}ms R={hp['recall']:.2f} | hnsw post x1 {hx1['timing_ms']['median']:.2f}ms R={hx1['recall']:.2f} ctx={hx1['mean_ctx']:.1f} "
                      f"| hnsw post x20 {hx20['timing_ms']['median']:.2f}ms R={hx20['recall']:.2f} | part {rec['partitioned']['timing_ms']['median']:.2f}ms", flush=True)
        os.makedirs(args.out, exist_ok=True)
        json.dump(results, open(os.path.join(args.out, "expE_latency.json"), "w"), indent=2)
    print("done")


if __name__ == "__main__":
    main()
