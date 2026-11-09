"""Experiment B and C: non-mirrored real corpus (Reuters-21578), two retrievers.

Documents from Reuters-21578 (ModApte split as distributed with NLTK) are
assigned to tenants and clearance levels with a seeded RNG.  Known-item queries
are generated from each target document.  Two retrievers are evaluated:

* BM25 (Okapi, k1 = 1.5, b = 0.75) implemented over a sparse term matrix
* a dense retriever using WordLlama l2_supercat 256-d static embeddings
  (Llama-3-derived token embeddings trained with a contrastive objective),
  indexed exactly with FAISS IndexFlatIP on unit-normalised vectors

Experiment C measures the result-count existence oracle created by post-filtering.
"""

from __future__ import annotations

import glob
import math
import os
import random
import re
import time
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import scipy.sparse as sp

from .common import Doc, Policy, Principal, Retriever, Tally, run_design, auc_from_scores, percentile_summary

SEED = 20261014
STOP = set("""a an the of to in and or for on at by with from as is are was were be been being this that these those
it its into over under about after before between during without within than then there their they them we our you your
he she his her has have had do does did not no but if so such which who whom whose what when where why how will would can
could should may might must also said says say pct mln dlrs vs cts shr net loss profit qtr year billion million reuter
u s inc corp co ltd lt gt""".split())


def _tokens(s: str) -> List[str]:
    return [t for t in re.findall(r"[a-z][a-z0-9'-]+", s.lower()) if t not in STOP and len(t) > 2]


def load_reuters(root: str) -> List[Doc]:
    """Load Reuters-21578 from the NLTK distribution layout (training/, test/)."""
    docs: List[Doc] = []
    files = sorted(glob.glob(os.path.join(root, "training", "*")) + glob.glob(os.path.join(root, "test", "*")),
                   key=lambda f: (os.path.basename(os.path.dirname(f)), int(os.path.basename(f))))
    for f in files:
        with open(f, "r", encoding="latin-1") as fh:
            raw = fh.read().strip()
        if not raw:
            continue
        lines = raw.split("\n")
        title = lines[0].strip()
        body = " ".join(l.strip() for l in lines[1:]).strip()
        if len(_tokens(body)) < 10 or len(_tokens(title)) < 1:
            continue
        docs.append(Doc(doc_id=len(docs), tenant=-1, clearance="general", text=body, title=title))
    return docs


def assign_policy(docs: List[Doc], n_tenants: int, restricted_frac: float, seed: int = SEED) -> None:
    rng = random.Random(seed + 7)
    for d in docs:
        d.tenant = rng.randrange(n_tenants)
        d.clearance = "restricted" if rng.random() < restricted_frac else "general"
        d.canary = f"CANARY-{d.doc_id:05d}-{rng.randrange(10**6):06d}"


# --------------------------------------------------------------------------- #
# Query generation
# --------------------------------------------------------------------------- #
class QueryGenerator:
    """Known-item queries.

    mode = "headline": the document's headline words (up to 8 content tokens).  This
        emulates a user who asks for a document by subject, as in the mirrored
        benchmark where queries name topic and type but not tenant.  Headlines in
        Reuters-21578 are short and frequently near-duplicated across documents,
        so the target competes with similar documents from every tenant.
    mode = "sentence": content words of one body sentence other than the lead,
        emulating a user who remembers a passage rather than the subject.
    """

    def __init__(self, docs: Sequence[Doc], seed: int = SEED, mode: str = "headline"):
        self.docs = docs
        self.mode = mode
        self.rng = random.Random(seed + 11)
        self._cache: Dict[int, str] = {}

    def query_for(self, doc: Doc, idx: int) -> str:
        if idx in self._cache:
            return self._cache[idx]
        title_toks = _tokens(doc.title)[:8]
        body_toks = _tokens(doc.text)
        if self.mode == "headline":
            q = " ".join(title_toks) if len(title_toks) >= 2 else " ".join(title_toks + body_toks[:4])
        else:
            sents = [s for s in re.split(r"(?<=[.;])\s+", doc.text) if len(_tokens(s)) >= 5]
            s = self.rng.choice(sents[1:]) if len(sents) > 1 else (sents[0] if sents else doc.text)
            st = [t for t in _tokens(s) if t not in title_toks][:8]
            q = " ".join(st) if st else " ".join(body_toks[:8])
        self._cache[idx] = q
        return q


# --------------------------------------------------------------------------- #
# Retrievers
# --------------------------------------------------------------------------- #
class BM25Retriever(Retriever):
    def __init__(self, docs: Sequence[Doc], queries: Sequence[str], k1: float = 1.5, b: float = 0.75):
        vocab: Dict[str, int] = {}
        rows, cols, vals = [], [], []
        lengths = []
        for i, d in enumerate(docs):
            toks = _tokens(d.text)
            lengths.append(len(toks))
            for t, c in Counter(toks).items():
                j = vocab.setdefault(t, len(vocab))
                rows.append(i); cols.append(j); vals.append(c)
        n, V = len(docs), len(vocab)
        tf = sp.csr_matrix((vals, (rows, cols)), shape=(n, V), dtype=np.float32)
        dl = np.asarray(lengths, dtype=np.float32)
        avgdl = dl.mean()
        df = np.asarray((tf > 0).sum(axis=0)).ravel()
        idf = np.log(1.0 + (n - df + 0.5) / (df + 0.5)).astype(np.float32)
        # BM25 term weight for each (doc, term)
        tf = tf.tocoo()
        denom = tf.data + k1 * (1.0 - b + b * dl[tf.row] / avgdl)
        w = idf[tf.col] * tf.data * (k1 + 1.0) / denom
        self.W = sp.csr_matrix((w, (tf.row, tf.col)), shape=(n, V)).tocsc()
        self.vocab = vocab
        self.ids = np.arange(n)
        self.query_terms = [[vocab[t] for t in set(_tokens(q)) if t in vocab] for q in queries]

    def scores(self, query_idx: int) -> np.ndarray:
        terms = self.query_terms[query_idx]
        if not terms:
            return np.zeros(self.W.shape[0], dtype=np.float32)
        return np.asarray(self.W[:, terms].sum(axis=1)).ravel()

    def rank(self, query_idx: int, k: int, candidate_mask: Optional[np.ndarray] = None) -> np.ndarray:
        s = self.scores(query_idx)
        if candidate_mask is not None:
            idx = self.ids[candidate_mask]
            s = s[candidate_mask]
        else:
            idx = self.ids
        k = min(k, len(idx))
        part = np.argpartition(-s, k - 1)[:k]
        order = np.lexsort((idx[part], -s[part]))
        return idx[part[order]]


class DenseRetriever(Retriever):
    """Exact inner-product search over unit vectors with FAISS; pre-filter via IDSelector."""

    def __init__(self, doc_vecs: np.ndarray, query_vecs: np.ndarray):
        import faiss
        self.faiss = faiss
        self.dim = doc_vecs.shape[1]
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(np.ascontiguousarray(doc_vecs.astype(np.float32)))
        self.Q = np.ascontiguousarray(query_vecs.astype(np.float32))
        self.n = doc_vecs.shape[0]

    def rank(self, query_idx: int, k: int, candidate_mask: Optional[np.ndarray] = None) -> np.ndarray:
        q = self.Q[query_idx:query_idx + 1]
        if candidate_mask is None:
            _, I = self.index.search(q, min(k, self.n))
            return I[0][I[0] >= 0]
        ids = np.flatnonzero(candidate_mask).astype(np.int64)
        sel = self.faiss.IDSelectorBatch(ids)
        params = self.faiss.SearchParameters(sel=sel)
        _, I = self.index.search(q, min(k, len(ids)), params=params)
        return I[0][I[0] >= 0]


def load_wordllama():
    """Load the bundled 256-d l2_supercat model without network access.

    wordllama 0.4.0 ships its tokenizer under wordllama/tokenizers/ but looks for it under
    wordllama/tokenizer/; when that happens, create the missing alias and retry. As a last
    resort, allow the library to download the file (requires network access).
    """
    import os, shutil
    import wordllama
    from wordllama import WordLlama
    try:
        return WordLlama.load(dim=256, disable_download=True)
    except FileNotFoundError:
        pkg = os.path.dirname(wordllama.__file__)
        src, dst = os.path.join(pkg, "tokenizers"), os.path.join(pkg, "tokenizer")
        if os.path.isdir(src) and not os.path.exists(dst):
            try:
                os.symlink(src, dst)
            except OSError:
                shutil.copytree(src, dst)
            try:
                return WordLlama.load(dim=256, disable_download=True)
            except FileNotFoundError:
                pass
        return WordLlama.load(dim=256)


def embed_texts(texts: Sequence[str]) -> np.ndarray:
    wl = load_wordllama()
    out = []
    bs = 1024
    for i in range(0, len(texts), bs):
        out.append(np.asarray(wl.embed(list(texts[i:i + bs]), norm=True), dtype=np.float32))
    return np.vstack(out)


# --------------------------------------------------------------------------- #
# Workload
# --------------------------------------------------------------------------- #
@dataclass
class Workload:
    authorized: List[Tuple[Principal, int]]     # (principal, target doc id)
    probes: List[Tuple[Principal, int]]         # (principal, forbidden target doc id)
    queries: List[str]                          # query text per target, indexed by position
    q_index: Dict[int, int]                     # doc id -> query index


def build_workload(docs: List[Doc], policy: Policy, qgen: QueryGenerator, n_tenants: int,
                   per_principal: int, probes_per_tenant: int, seed: int = SEED) -> Workload:
    rng = random.Random(seed + 23)
    queries: List[str] = []
    q_index: Dict[int, int] = {}

    def q_for(doc_id: int) -> int:
        if doc_id not in q_index:
            q_index[doc_id] = len(queries)
            queries.append(qgen.query_for(docs[doc_id], doc_id))
        return q_index[doc_id]

    authorized, probes = [], []
    for t in range(n_tenants):
        for role in ("analyst", "manager"):
            p = Principal(t, role)
            allowed = np.flatnonzero(policy.allowed_mask(p)).tolist()
            for doc_id in rng.sample(allowed, min(per_principal, len(allowed))):
                q_for(doc_id)
                authorized.append((p, doc_id))
        p = Principal(t, "analyst")
        forbidden = np.flatnonzero(~policy.allowed_mask(p)).tolist()
        for doc_id in rng.sample(forbidden, min(probes_per_tenant, len(forbidden))):
            q_for(doc_id)
            probes.append((p, doc_id))
    return Workload(authorized, probes, queries, q_index)


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
DESIGNS = [("unfiltered", "unfiltered", 1), ("postfilter_topk", "postfilter", 1),
           ("postfilter_x2", "postfilter", 2), ("postfilter_x5", "postfilter", 5),
           ("postfilter_x10", "postfilter", 10), ("postfilter_x20", "postfilter", 20),
           ("postfilter_x50", "postfilter", 50), ("prefilter", "prefilter", 1)]


def evaluate(retriever: Retriever, policy: Policy, wl: Workload, k: int,
             designs=DESIGNS, timing: bool = False) -> Dict:
    out = {}
    for name, design, of in designs:
        ta, tp = Tally(), Tally()
        reached = 0
        times = []
        for p, target in wl.authorized:
            qi = wl.q_index[target]
            t0 = time.perf_counter()
            res = run_design(design, retriever, policy, p, qi, k, of)
            times.append((time.perf_counter() - t0) * 1000.0)
            ta.add(res, policy, p, target)
        for p, target in wl.probes:
            res = run_design(design, retriever, policy, p, wl.q_index[target], k, of)
            tp.add(res, policy, p, None)
            reached += 1 if target in res.context else 0
        s = ta.summary()
        sp_ = tp.summary()
        sp_["foreign_target_reached_rate"] = reached / max(len(wl.probes), 1)
        rec = {"authorized": s, "probes": sp_}
        if timing:
            rec["timing_ms"] = percentile_summary(times)
        out[name] = rec
    return out


def existence_oracle(retriever: Retriever, policy: Policy, attacker: Principal,
                     pos_query_idx: Sequence[int], neg_query_idx: Sequence[int], k: int,
                     designs=DESIGNS) -> Dict:
    """Result-count existence oracle.

    The attacker issues a known-item query for a document and observes only the
    number of results returned.  Positives are queries for documents that exist
    in the index but are forbidden to the attacker; negatives are queries for
    held-out documents that are not in the index at all.  Score = k - returned.
    AUC = 0.5 means the count reveals nothing; AUC = 1.0 means it reveals
    existence perfectly.
    """
    out = {}
    for name, design, of in designs:
        pos_scores, neg_scores = [], []
        for qi in pos_query_idx:
            res = run_design(design, retriever, policy, attacker, qi, k, of)
            pos_scores.append(k - res.returned_count)
        for qi in neg_query_idx:
            res = run_design(design, retriever, policy, attacker, qi, k, of)
            neg_scores.append(k - res.returned_count)
        out[name] = {"auc": auc_from_scores(pos_scores, neg_scores),
                     "mean_missing_pos": float(np.mean(pos_scores)),
                     "mean_missing_neg": float(np.mean(neg_scores)),
                     "short_list_rate_pos": float(np.mean(np.asarray(pos_scores) > 0)),
                     "short_list_rate_neg": float(np.mean(np.asarray(neg_scores) > 0)),
                     "n_pos": len(pos_scores), "n_neg": len(neg_scores)}
    return out
