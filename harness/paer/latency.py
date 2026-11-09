"""Experiment E: enforcement cost on real vector indexes.

Compares, at 10k to 250k vectors, the per-query cost and effective recall of

* exact search (FAISS IndexFlatIP):      full scan + post-filter (m = 1, 5, 20) vs. ID-selector pre-filter
* graph ANN (FAISS IndexHNSWFlat):       full search + post-filter (m = 1, 5, 20) vs. ID-selector pre-filter
* partitioned indexes:                   one exact index per (tenant, clearance) partition; search permitted partitions
* Qdrant (local in-memory client):       payload-filtered search vs. unfiltered search + client-side post-filter

Vectors are WordLlama embeddings of Reuters-21578 documents, augmented to the
target size with jittered copies (Gaussian noise, sigma = 0.05, renormalised) so
that the score distribution stays realistic.  Ground truth for recall is the
exact pre-filtered top-k.
"""

from __future__ import annotations

import time
from typing import Dict, List

import numpy as np

from .common import percentile_summary


def augment(vecs: np.ndarray, n_target: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    reps = int(np.ceil(n_target / vecs.shape[0]))
    out = [vecs]
    for r in range(1, reps):
        noisy = vecs + rng.normal(0, 0.05, vecs.shape).astype(np.float32)
        noisy /= np.linalg.norm(noisy, axis=1, keepdims=True)
        out.append(noisy)
    X = np.vstack(out)[:n_target]
    return np.ascontiguousarray(X.astype(np.float32))


def labels_for(n: int, n_tenants: int, restricted_frac: float, seed: int):
    rng = np.random.default_rng(seed + 5)
    tenant = rng.integers(0, n_tenants, n)
    restricted = rng.random(n) < restricted_frac
    return tenant, restricted


def _recall(pred: np.ndarray, truth: np.ndarray) -> float:
    if len(truth) == 0:
        return 1.0
    return len(set(pred.tolist()) & set(truth.tolist())) / len(truth)


def run_faiss(X: np.ndarray, Q: np.ndarray, allowed: np.ndarray, k: int, overfetch: List[int],
              hnsw_M: int = 32, ef_search: int = 128) -> Dict:
    import faiss, os
    d = X.shape[1]
    allowed_ids = np.flatnonzero(allowed).astype(np.int64)
    sel = faiss.IDSelectorBatch(allowed_ids)
    out: Dict = {"selectivity": float(allowed.mean())}

    # exact ground truth: pre-filtered flat search
    flat = faiss.IndexFlatIP(d); flat.add(X)
    truths = []
    times = []
    for q in Q:
        t0 = time.perf_counter()
        _, I = flat.search(q[None, :], k, params=faiss.SearchParameters(sel=sel))
        times.append((time.perf_counter() - t0) * 1000)
        truths.append(I[0][I[0] >= 0])
    out["flat_prefilter"] = {"timing_ms": percentile_summary(times), "recall": 1.0, "mean_ctx": float(np.mean([len(t) for t in truths]))}

    for m in overfetch:
        times, recs, ctxs = [], [], []
        for q, truth in zip(Q, truths):
            t0 = time.perf_counter()
            _, I = flat.search(q[None, :], k * m)
            ids = I[0][I[0] >= 0]
            ctx = ids[allowed[ids]][:k]
            times.append((time.perf_counter() - t0) * 1000)
            recs.append(_recall(ctx, truth)); ctxs.append(len(ctx))
        out[f"flat_postfilter_x{m}"] = {"timing_ms": percentile_summary(times), "recall": float(np.mean(recs)), "mean_ctx": float(np.mean(ctxs))}

    # HNSW
    hnsw = faiss.IndexHNSWFlat(d, hnsw_M, faiss.METRIC_INNER_PRODUCT)
    hnsw.hnsw.efConstruction = 200
    t0 = time.perf_counter(); hnsw.add(X); build_s = time.perf_counter() - t0
    hnsw.hnsw.efSearch = ef_search
    out["hnsw_build_s"] = build_s
    times, recs, ctxs = [], [], []
    params = faiss.SearchParametersHNSW(sel=sel, efSearch=ef_search)
    for q, truth in zip(Q, truths):
        t0 = time.perf_counter()
        _, I = hnsw.search(q[None, :], k, params=params)
        times.append((time.perf_counter() - t0) * 1000)
        ids = I[0][I[0] >= 0]
        recs.append(_recall(ids, truth)); ctxs.append(len(ids))
    out["hnsw_prefilter"] = {"timing_ms": percentile_summary(times), "recall": float(np.mean(recs)), "mean_ctx": float(np.mean(ctxs))}
    for m in overfetch:
        times, recs, ctxs = [], [], []
        for q, truth in zip(Q, truths):
            t0 = time.perf_counter()
            _, I = hnsw.search(q[None, :], k * m)
            ids = I[0][I[0] >= 0]
            ctx = ids[allowed[ids]][:k]
            times.append((time.perf_counter() - t0) * 1000)
            recs.append(_recall(ctx, truth)); ctxs.append(len(ctx))
        out[f"hnsw_postfilter_x{m}"] = {"timing_ms": percentile_summary(times), "recall": float(np.mean(recs)), "mean_ctx": float(np.mean(ctxs))}
    return out


def run_partitioned(X: np.ndarray, Q: np.ndarray, tenant: np.ndarray, restricted: np.ndarray,
                    principal_tenant: int, principal_role: str, k: int, truths_fn) -> Dict:
    """One exact index per (tenant, clearance) partition; a principal searches only permitted partitions."""
    import faiss
    d = X.shape[1]
    parts = {}
    for t in np.unique(tenant):
        for r in (False, True):
            ids = np.flatnonzero((tenant == t) & (restricted == r)).astype(np.int64)
            idx = faiss.IndexIDMap(faiss.IndexFlatIP(d))
            idx.add_with_ids(X[ids], ids)
            parts[(int(t), bool(r))] = idx
    permitted = [(principal_tenant, False)] + ([(principal_tenant, True)] if principal_role == "manager" else [])
    times, recs = [], []
    for q in Q:
        t0 = time.perf_counter()
        cand = []
        for key in permitted:
            D, I = parts[key].search(q[None, :], k)
            cand.extend(zip(D[0], I[0]))
        cand.sort(key=lambda x: -x[0])
        ids = np.asarray([i for _, i in cand[:k]], dtype=np.int64)
        times.append((time.perf_counter() - t0) * 1000)
        recs.append(_recall(ids, truths_fn(q)))
    return {"timing_ms": percentile_summary(times), "recall": float(np.mean(recs))}


def run_qdrant(X: np.ndarray, Q: np.ndarray, tenant: np.ndarray, restricted: np.ndarray,
               principal_tenant: int, principal_role: str, k: int, overfetch: List[int], truths: List[np.ndarray]) -> Dict:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams
    client = QdrantClient(":memory:")
    client.create_collection("docs", vectors_config=VectorParams(size=X.shape[1], distance=Distance.COSINE))
    bs = 2048
    t0 = time.perf_counter()
    for i in range(0, len(X), bs):
        pts = [PointStruct(id=int(j), vector=X[j].tolist(),
                           payload={"tenant": int(tenant[j]), "clearance": "restricted" if restricted[j] else "general"})
               for j in range(i, min(i + bs, len(X)))]
        client.upsert("docs", pts)
    load_s = time.perf_counter() - t0
    must = [FieldCondition(key="tenant", match=MatchValue(value=principal_tenant))]
    if principal_role == "analyst":
        must.append(FieldCondition(key="clearance", match=MatchValue(value="general")))
    flt = Filter(must=must)
    allowed = (tenant == principal_tenant) & (~restricted if principal_role == "analyst" else np.ones(len(X), bool))
    out = {"load_s": load_s}
    times, recs = [], []
    for q, truth in zip(Q, truths):
        t0 = time.perf_counter()
        res = client.query_points("docs", query=q.tolist(), limit=k, query_filter=flt).points
        times.append((time.perf_counter() - t0) * 1000)
        recs.append(_recall(np.asarray([p.id for p in res]), truth))
    out["qdrant_payload_prefilter"] = {"timing_ms": percentile_summary(times), "recall": float(np.mean(recs))}
    for m in overfetch:
        times, recs, ctxs = [], [], []
        for q, truth in zip(Q, truths):
            t0 = time.perf_counter()
            res = client.query_points("docs", query=q.tolist(), limit=k * m).points
            ids = np.asarray([p.id for p in res], dtype=np.int64)
            ctx = ids[allowed[ids]][:k]
            times.append((time.perf_counter() - t0) * 1000)
            recs.append(_recall(ctx, truth)); ctxs.append(len(ctx))
        out[f"qdrant_postfilter_x{m}"] = {"timing_ms": percentile_summary(times), "recall": float(np.mean(recs)), "mean_ctx": float(np.mean(ctxs))}
    return out
