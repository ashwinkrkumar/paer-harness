"""Driver for Experiment D: revocation lag replay on Reuters-21578 with BM25."""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paer.common import Policy  # noqa: E402
from paer.reuters import SEED, BM25Retriever, QueryGenerator, assign_policy, build_workload, load_reuters  # noqa: E402
from paer.revocation import simulate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    docs = [copy.copy(d) for d in load_reuters(args.root)]
    assign_policy(docs, 3, 1 / 3, SEED)
    policy = Policy(docs)
    qgen = QueryGenerator(docs, SEED, "headline")
    wl = build_workload(docs, policy, qgen, 3, 400, 0, SEED)
    bm25 = BM25Retriever(docs, wl.queries)

    results = []
    for recon in [1.0, 15.0, 60.0, 1440.0]:
        for e4 in ["none", "cached", "live"]:
            r = simulate(bm25, policy, docs, wl.authorized, wl.q_index, k=5, horizon_h=24.0,
                         query_rate_h=600.0, revoke_rate_h=20.0, recon_interval_min=recon,
                         e4_mode=e4, e4_ttl_min=5.0, seed=SEED)
            results.append(r)
            print(f"recon={recon:7.1f}min e4={e4:7s} stale_q_rate={r['stale_query_rate']:.4f} "
                  f"stale_docs/10k={r['stale_docs_per_10k_queries']:.1f} idx_lag_mean={r['mean_index_lag_min']:.1f}min "
                  f"max_stale_age={r['max_stale_age_min']:.1f}min", flush=True)
    os.makedirs(args.out, exist_ok=True)
    json.dump({"query_rate_h": 600, "revoke_rate_h": 20, "horizon_h": 24, "k": 5, "runs": results},
              open(os.path.join(args.out, "expD_revocation.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
