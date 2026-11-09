"""Sections 5 to 8 and back matter."""

from numbers_ import *  # noqa


def _tableA():
    rows = []
    for key, label in A_DESIGNS:
        a = A["designs"][key]["authorized"]; p = A["designs"][key]["probes"]
        rows.append([label, pct(a["target_recall"]), pct(a["unauthorized_context_rate"]), pct(a["query_exposure_rate"]),
                     pct(a["candidate_unauthorized_rate"]), f(a["mean_context_docs"]), pct(a["provenance_fidelity"]),
                     pct(p["foreign_target_reached_rate"]), pct(a["canary_echo_leak_rate"], 0) + " / " + pct(a["canary_leak_rate_after_output_gate"], 0),
                     f(A["timing_ms"][key]["median"], 3)])
    return {"caption": "Table 4. Experiment A, mirrored synthetic benchmark (270 documents, 900 authorized queries, 90 cross-tenant probes, k = 2). Percentages unless stated. Canary column: leak rate before / after the E5 output gate.",
            "header": ["Design", "Recall@2", "Unauth. context", "Query exposure", "Candidate-stage unauth.", "Mean context docs", "Provenance fidelity", "Probe: foreign target reached", "Canary echo leak", "Median ms"],
            "rows": rows, "widths": [3.4, 1.4, 1.5, 1.5, 1.7, 1.5, 1.6, 1.8, 1.5, 1.3], "font": 7.5}


def _tableB():
    rows = []
    for retr, rlabel in [("bm25", "BM25"), ("dense", "Dense")]:
        for key, label, _ in B_KEYS:
            a = B[retr][key]["authorized"]; p = B[retr][key]["probes"]
            rows.append([rlabel, label, pct(a["target_recall"]), pct(a["unauthorized_context_rate"]), pct(a["query_exposure_rate"]),
                         pct(a["candidate_unauthorized_rate"]), f(a["mean_context_docs"]), pct(p["foreign_target_reached_rate"]),
                         f(B[retr][key]["timing_ms"]["median"], 3)])
    return {"caption": f"Table 5. Experiment B, main configuration: Reuters-21578, {B['config']['corpus_size']:,} indexed documents, three tenants, one third restricted, headline queries, k = 5, {B['config']['authorized_queries']:,} authorized queries and {B['config']['probes']} probes. Percentages unless stated.",
            "header": ["Retriever", "Design", "Recall@5", "Unauth. context", "Query exposure", "Candidate-stage unauth.", "Mean context docs", "Probe: foreign target reached", "Median ms"],
            "rows": rows, "widths": [1.5, 3.0, 1.5, 1.5, 1.5, 1.8, 1.6, 2.0, 1.4], "font": 7.5}


def _tableSweep():
    rows = []
    for c in SW["tenants"]:
        T = c["config"]["n_tenants"]; af = c["authorized_fraction"]["t0_analyst"]
        for retr, rl in [("bm25", "BM25"), ("dense", "Dense")]:
            g = lambda k: c[retr][k]["authorized"]["target_recall"]
            rows.append([str(T), pct(af, 0), rl, pct(g("unfiltered")), pct(g("postfilter_topk")), f(c[retr]["postfilter_topk"]["authorized"]["mean_context_docs"]),
                         pct(g("postfilter_x2")), pct(g("postfilter_x5")), pct(g("postfilter_x10")), pct(g("postfilter_x20")), pct(g("prefilter"))])
    return {"caption": "Table 6. Tenant sweep (p = 1/3, k = 5, headline queries). Authorized share is the fraction of the indexed corpus an analyst in tenant 0 may read. Recall@5 in percent; context size in documents for D1.",
            "header": ["Tenants", "Authorized share", "Retriever", "D0 recall", "D1 recall", "D1 context docs", "D2 m=2", "D2 m=5", "D2 m=10", "D2 m=20", "D3 recall"],
            "rows": rows, "widths": [1.2, 1.5, 1.4, 1.4, 1.4, 1.5, 1.3, 1.3, 1.3, 1.3, 1.4], "font": 7.5}


def _tableOracle():
    rows = []
    for r in oracle_sorted():
        c = r["config"]
        bo = r["bm25_oracle_restricted"]; do = r["dense_oracle_restricted"]
        rows.append([str(c["n_tenants"]), f"{c['restricted_frac']:.2f}", pct(r["attacker_authorized_fraction"], 0),
                     f(bo["postfilter_topk"]["auc"]), f(bo["postfilter_x2"]["auc"]), f(bo["postfilter_x5"]["auc"]), f(bo["postfilter_x20"]["auc"]), f(bo["prefilter"]["auc"]),
                     f(do["postfilter_topk"]["auc"]), f(do["postfilter_x2"]["auc"]), f(do["postfilter_x5"]["auc"]), f(do["postfilter_x20"]["auc"]), f(do["prefilter"]["auc"])])
    return {"caption": "Table 7. Experiment C, result-count existence oracle. AUC of the returned-result count as a detector that a forbidden document exists in the index (positives: restricted documents in the attacker's tenant; negatives: 400 held-out documents). 0.50 means no leakage.",
            "header": ["Tenants", "Restricted p", "Attacker share", "BM25 D1", "BM25 m=2", "BM25 m=5", "BM25 m=20", "BM25 D3", "Dense D1", "Dense m=2", "Dense m=5", "Dense m=20", "Dense D3"],
            "rows": rows, "widths": [1.1, 1.2, 1.3, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2], "font": 7.3}


def _tableRevocation():
    rows = []
    for rc, lab in [(1.0, "1 min"), (15.0, "15 min"), (60.0, "60 min"), (1440.0, "24 h")]:
        for mode, ml in [("none", "none"), ("cached", "cached, TTL 5 min"), ("live", "live")]:
            r = d_run(rc, mode)
            rows.append([lab, ml, f(r["mean_index_lag_min"], 1), f(r["stale_docs_per_10k_queries"], 1), pct(r["stale_query_rate"], 2), f(r["max_stale_age_min"], 1)])
    q = D["runs"][0]
    return {"caption": f"Table 8. Experiment D, revocation lag replay ({q['queries']:,} queries and {q['revocations']} revocations over 24 simulated hours, BM25, k = 5). Index lag is the mean time from a source revocation to the next reconciliation.",
            "header": ["E2 reconciliation", "E4 re-check", "Mean index lag (min)", "Stale docs per 10,000 queries", "Stale query rate (%)", "Max stale age (min)"],
            "rows": rows, "widths": [2.4, 3.0, 2.6, 3.0, 2.6, 2.6], "font": 8}


def _tableLatency():
    if E is None:
        return None
    rows = []
    for T in (3, 10):
        for r in e_rows(T, "t0_analyst"):
            def t(k): return f(r[k]["timing_ms"]["median"], 2)
            def rc(k): return pct(r[k]["recall"], 0)
            qd = r.get("qdrant")
            rows.append([str(T), f"{r['n']:,}", pct(r["selectivity"], 0),
                         t("flat_prefilter"), t("flat_postfilter_x1") + " / " + rc("flat_postfilter_x1"), t("flat_postfilter_x20") + " / " + rc("flat_postfilter_x20"),
                         t("hnsw_prefilter") + " / " + rc("hnsw_prefilter"), t("hnsw_postfilter_x1") + " / " + rc("hnsw_postfilter_x1"), t("hnsw_postfilter_x20") + " / " + rc("hnsw_postfilter_x20"),
                         t("partitioned") + " / " + rc("partitioned"),
                         (f(qd["qdrant_payload_prefilter"]["timing_ms"]["median"], 1) + " / " + f(qd["qdrant_postfilter_x20"]["timing_ms"]["median"], 1)) if qd else "n/a"])
    return {"caption": "Table 9. Experiment E, enforcement cost on vector indexes for an analyst in tenant 0 with three tenants (about 22% selectivity) and ten tenants (about 7%). Cells give median latency in milliseconds and, after the slash, effective recall in percent against the exact pre-filtered top-5. Qdrant column: payload-filtered search / unfiltered search with 20x over-fetch and client-side filtering (in-memory client).",
            "header": ["Tenants", "Vectors", "Select. (%)", "Exact pre-filter", "Exact post-filter m=1", "Exact post-filter m=20", "HNSW pre-filter", "HNSW post-filter m=1", "HNSW post-filter m=20", "Partition", "Qdrant pre / post"],
            "rows": rows, "widths": [1.1, 1.3, 1.3, 1.4, 1.7, 1.7, 1.6, 1.7, 1.7, 1.6, 1.7], "font": 7.0}


def _gap(retr, key="postfilter_topk", src=None):
    src = src or B
    return 100 * (src[retr]["prefilter"]["authorized"]["target_recall"] - src[retr][key]["authorized"]["target_recall"])



def _rng(vals, fmt):
    lo, hi = min(vals), max(vals)
    return fmt(lo) if fmt(lo) == fmt(hi) else f"{fmt(lo)} to {fmt(hi)}"


def _compare_flat(rows):
    """Classify ID-selector pre-filter vs full-scan post-filter per index size on the exact index."""
    cheaper, similar, dearer = [], [], []
    for r in rows:
        pre = r["flat_prefilter"]["timing_ms"]["median"]; post = r["flat_postfilter_x1"]["timing_ms"]["median"]
        (cheaper if pre < 0.9 * post else dearer if pre > 1.1 * post else similar).append(r)
    return cheaper, similar, dearer


def _sizes(rs):
    ns = [f"{r['n']:,}" for r in rs]
    return ns[0] if len(ns) == 1 else ", ".join(ns[:-1]) + " and " + ns[-1]


def _pair(r):
    return f"{r['flat_prefilter']['timing_ms']['median']:.2f} against {r['flat_postfilter_x1']['timing_ms']['median']:.2f} ms at {r['n']:,} vectors"


def _flat_sentence(rows, label):
    cheaper, similar, dearer = _compare_flat(rows)
    if len(cheaper) == len(rows):
        return (f"At {label} selectivity the ID-selector pre-filter was cheaper than a full-scan post-filter at every size "
                f"({_pair(rows[0])}; {_pair(rows[-1])}).")
    short = lambda r: f"{r['flat_prefilter']['timing_ms']['median']:.2f} against {r['flat_postfilter_x1']['timing_ms']['median']:.2f} ms"
    parts = []
    if cheaper:
        parts.append(f"cheaper than a full-scan post-filter at {_sizes(cheaper)} vectors ({short(cheaper[0])} at {cheaper[0]['n']:,})")
    if similar:
        parts.append(f"about equal at {_sizes(similar)} ({short(similar[0])})")
    if dearer:
        parts.append(f"more expensive at {_sizes(dearer)} ({short(dearer[-1])})")
    joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + ", and " + parts[-1]
    return f"At {label} selectivity the ID-selector pre-filter was " + joined + "."


def _expE_text(rows, rows10):
    r10, rmax = rows[0], rows[-1]
    ms = lambda v: f"{v:.2f}"
    pc = lambda v: f"{100*v:.0f}%"
    hx1 = [r["hnsw_postfilter_x1"] for r in rows]
    qd = r10.get("qdrant")
    all_cheaper = len(_compare_flat(rows)[0]) == len(rows) and len(_compare_flat(rows10)[0]) == len(rows10)
    txt = (f"Table 9 and Figure 8 report cost and effective recall for an analyst in tenant 0 at two selectivities, about {pct(r10['selectivity'],0)}% (three tenants) "
           f"and {pct(rows10[0]['selectivity'],0)}% (ten tenants). "
           + _flat_sentence(rows, f"{pct(r10['selectivity'],0)}%") + " " + _flat_sentence(rows10, f"{pct(rows10[0]['selectivity'],0)}%") + " ")
    if all_cheaper:
        txt += ("The selector skips the distance computations for excluded vectors, which is what makes it cheaper here, but it is still a per-vector "
                "membership test rather than native predicate pushdown, and its advantage shrinks as selectivity rises. ")
    else:
        txt += ("The pattern follows from how an ID selector works: it skips the distance computation for excluded vectors but adds a membership test "
                "for every vector, and it forgoes the batched linear-algebra path that a full scan uses, so its advantage grows as selectivity falls and "
                "shrinks as the index grows. An ID selector is a filter applied inside the scan, not native predicate pushdown. ")
    txt += (f"Full-scan post-filtering with m = 1 kept an effective recall equal to the selectivity ({_rng([r['flat_postfilter_x1']['recall'] for r in rows], pc)}), the exact-index form of the starvation seen in Experiment B. "
            f"On the HNSW graph index, top-k-only post-filtering returned {_rng([h['mean_ctx'] for h in hx1], lambda v: f'{v:.1f}')} usable documents of five with effective recall {_rng([h['recall'] for h in hx1], pc)}. "
            f"Over-fetching 20x on HNSW restored effective recall to {_rng([r['hnsw_postfilter_x20']['recall'] for r in rows], pc)} at a median cost of {_rng([r['hnsw_postfilter_x20']['timing_ms']['median'] for r in rows], ms)} ms, "
            f"and HNSW with an ID selector reached {_rng([r['hnsw_prefilter']['recall'] for r in rows], pc)} at {_rng([r['hnsw_prefilter']['timing_ms']['median'] for r in rows], ms)} ms; "
            f"at ten tenants its recall fell to {pct(min(r['hnsw_prefilter']['recall'] for r in rows10),0)}%, the known weakness of post-hoc selectors on graph indexes at low selectivity that filter-aware graph designs address {{Gollapudi2023,Patel2024}}. "
            f"Partitioned exact indexes were the cheapest exact arrangement at every size and selectivity ({_rng([r['partitioned']['timing_ms']['median'] for r in rows], ms)} ms at {pct(r10['selectivity'],0)}%) and are exact by construction, at the cost of one index per tenant and clearance. ")
    if qd:
        txt += (f"In Qdrant's in-memory client, payload-filtered search cost {ms(qd['qdrant_payload_prefilter']['timing_ms']['median'])} ms at {r10['n']:,} vectors against {ms(qd['qdrant_postfilter_x20']['timing_ms']['median'])} ms for unfiltered search with 20x over-fetch and client-side filtering, "
                "because the local client evaluates payload predicates in Python for every point. This is a property of the in-memory client rather than of the Qdrant server, whose filterable graph index is built for this case. "
                "Together with the exact-index result it makes the general point: the cost of pre-filtering is decided by whether the index implements the predicate natively, not by the placement decision alone.")
    return txt


def results_blocks():
    tA = _tableA(); tB = _tableB(); tS = _tableSweep(); tO = _tableOracle(); tR = _tableRevocation(); tL = _tableLatency()
    o = oracle_sorted()
    top = o[-1]; mid = [r for r in o if abs(r["attacker_authorized_fraction"] - B["authorized_fraction"]["t0_analyst"]) < 0.03]
    mid = mid[0] if mid else o[len(o) // 2]
    sw10 = SW["tenants"][4]; sw1 = SW["tenants"][0]
    mb, sb = seed_stats("bm25", "prefilter"); mb1, sb1 = seed_stats("bm25", "postfilter_topk")
    md, sd = seed_stats("dense", "prefilter"); md1, sd1 = seed_stats("dense", "postfilter_topk")
    rev_none_24 = d_run(1440.0, "none"); rev_cached_24 = d_run(1440.0, "cached"); rev_none_60 = d_run(60.0, "none"); rev_cached_60 = d_run(60.0, "cached")
    blocks = [
        ("h1", "5. Results"),
        ("h2", "5.1. Experiment A: The Failure Mode in Closed Form"),
        ("p", f"Table 4 and Figure 3 report the mirrored benchmark. Unfiltered retrieval placed unauthorized documents in the context of every "
              f"authorized query: the unauthorized context rate was {pct(a_row('unfiltered')['unauthorized_context_rate'])}%, query exposure was "
              f"{pct(a_row('unfiltered')['query_exposure_rate'],0)}%, and the requested foreign document reached the context in {pct(A['designs']['unfiltered']['probes']['foreign_target_reached_rate'])}% of cross-tenant probes. "
              f"All three filtered designs reduced unauthorized context, query exposure, and foreign-target reach to zero and raised provenance fidelity to 100%. "
              f"They differ in what they do to authorized retrieval. Filtering only the top two candidates kept restricted content out but could not replace it: "
              f"the context averaged {f(a_row('postfilter_topk')['mean_context_docs'])} documents per query and Recall@2 stayed at {pct(a_row('postfilter_topk')['target_recall'])}%, the same as the "
              f"unfiltered baseline. Over-fetching ten candidates before filtering restored Recall@2 to {pct(a_row('postfilter_overfetch5')['target_recall'],0)}% with a full context, as did pre-filtering. "
              f"The candidate-stage unauthorized rate under over-fetching was {pct(a_row('postfilter_overfetch5')['candidate_unauthorized_rate'])}%, higher than the {pct(a_row('unfiltered')['candidate_unauthorized_rate'])}% of "
              "the top-2 designs, because the larger pool admits more same-topic documents from other tenants before the filter removes them; that is the over-fetch design working as intended."),
        ("p", f"The self-consistency checks passed. All 270 records carried complete labels (E1). The synchronous revocation test withdrew the analyst role's "
              f"permission on one target and the document, present in the context of all three filtered designs before the change, was absent from all three on the next query (E2). "
              f"The E4 re-check recorded zero failures in every design. The canary echo exposed a restricted canary in {pct(a_row('unfiltered')['canary_echo_leak_rate'],0)}% of unfiltered queries and "
              f"{pct(a_row('postfilter_topk')['canary_echo_leak_rate'],0)}% under every filtered design, and the E5 output gate reduced the unfiltered leak to {pct(a_row('unfiltered')['canary_leak_rate_after_output_gate'],0)}% (E5). "
              "Because the gate applies the same ACL that labelled the corpus, these outcomes confirm that the harness behaves as specified and nothing more. "
              f"Pre-filtering was the cheapest design in this benchmark (median {f(A['timing_ms']['prefilter']['median'],3)} ms per query against {f(A['timing_ms']['unfiltered']['median'],3)} to {f(A['timing_ms']['postfilter_overfetch5']['median'],3)} ms) because it scores one third of the corpus."),
        ("table", tA),
        ("figure", {"path": "fig3_mirrored.png", "width_cm": 14.5,
                    "caption": "Figure 3. Experiment A. Authorized-target Recall@2 and unauthorized context rate across the four designs on the mirrored benchmark. Values are properties of the construction and demonstrate the mechanism; Experiment B measures magnitudes on a real corpus."}),
        ("h2", "5.2. Experiment B: Enforcement Placement on a Real Corpus"),
        ("p", f"Table 5 reports the main configuration. On Reuters-21578 with three tenants and one third of documents restricted, unfiltered retrieval placed unauthorized "
              f"documents in {pct(b('bm25','unfiltered','unauthorized_context_rate'))}% (BM25) and {pct(b('dense','unfiltered','unauthorized_context_rate'))}% (dense) of context slots and exposed "
              f"{pct(b('bm25','unfiltered','query_exposure_rate'))}% and {pct(b('dense','unfiltered','query_exposure_rate'))}% of authorized queries. The requested forbidden document reached the context in "
              f"{pct(b('bm25','unfiltered','foreign_target_reached_rate',part='probes'))}% and {pct(b('dense','unfiltered','foreign_target_reached_rate',part='probes'))}% of probes. "
              "All filtered designs reduced every exposure measure to zero for both retrievers, so the comparison among them is about utility."),
        ("p", f"Top-k post-filtering (D1) starved the context. With analysts able to read {pct(B['authorized_fraction']['t0_analyst'],0)}% of the corpus and managers {pct(B['authorized_fraction']['t0_manager'],0)}%, the final context averaged "
              f"{f(b('bm25','postfilter_topk','mean_context_docs'))} (BM25) and {f(b('dense','postfilter_topk','mean_context_docs'))} (dense) of five documents. Its Recall@5 equals the unfiltered value by construction, "
              f"{pct(b('bm25','postfilter_topk','target_recall'))}% and {pct(b('dense','postfilter_topk','target_recall'))}%, because a permitted target that was in the top five is kept and one that was not is still absent. "
              f"Pre-filtering (D3) raised Recall@5 to {pct(b('bm25','prefilter','target_recall'))}% and {pct(b('dense','prefilter','target_recall'))}%, a gain of {_gap('bm25'):.1f} and {_gap('dense'):.1f} points, "
              "because removing unauthorized competitors before ranking frees slots for the permitted target. Over-fetching (D2) recovered that gain progressively (Figure 4): "
              f"m = 2 recovered {pct(b('bm25','postfilter_x2','target_recall'))}% and {pct(b('dense','postfilter_x2','target_recall'))}%, m = 5 recovered {pct(b('bm25','postfilter_x5','target_recall'))}% and {pct(b('dense','postfilter_x5','target_recall'))}%, "
              f"and m = 10 matched pre-filtering for both retrievers. On sentence queries the pattern was the same but the magnitude depended on the retriever: BM25 lost "
              f"{_gap('bm25', src=BS):.1f} points under D1 because exact body words make the target rank first for almost every query, whereas the dense retriever lost {_gap('dense', src=BS):.1f} points "
              f"({pct(b('dense','postfilter_topk','target_recall',src=BS))}% against {pct(b('dense','prefilter','target_recall',src=BS))}%) and needed m = 10 to recover."),
        ("table", tB),
        ("figure", {"path": "fig4_overfetch.png", "width_cm": 15.5,
                    "caption": "Figure 4. Experiment B. Authorized-target Recall@5 of post-filtering as a function of the over-fetch factor m, with pre-filter recall as a dashed reference, for headline queries (left) and sentence queries (right). m = 1 is top-k-only post-filtering."}),
        ("p", f"The sweeps (Table 6, Figure 5) answer RQ2. The number of tenants, and with it the share of the corpus a principal may read, governed both the starvation and the recall gap. "
              f"With one tenant an analyst reads {pct(sw1['authorized_fraction']['t0_analyst'],0)}% of the corpus; D1 filled {f(sw1['bm25']['postfilter_topk']['authorized']['mean_context_docs'])} of five slots and lost "
              f"{100*(sw1['bm25']['prefilter']['authorized']['target_recall']-sw1['bm25']['postfilter_topk']['authorized']['target_recall']):.1f} (BM25) and {100*(sw1['dense']['prefilter']['authorized']['target_recall']-sw1['dense']['postfilter_topk']['authorized']['target_recall']):.1f} (dense) recall points, and m = 2 recovered the loss. "
              f"With ten tenants an analyst reads {pct(sw10['authorized_fraction']['t0_analyst'],0)}% of the corpus; D1 filled {f(sw10['bm25']['postfilter_topk']['authorized']['mean_context_docs'])} slots and lost "
              f"{100*(sw10['bm25']['prefilter']['authorized']['target_recall']-sw10['bm25']['postfilter_topk']['authorized']['target_recall']):.1f} and {100*(sw10['dense']['prefilter']['authorized']['target_recall']-sw10['dense']['postfilter_topk']['authorized']['target_recall']):.1f} points, and m = 20 was needed to match pre-filtering for both retrievers (m = 10 left the dense retriever "
              f"{100*(sw10['dense']['prefilter']['authorized']['target_recall']-sw10['dense']['postfilter_x10']['authorized']['target_recall']):.1f} points short). Raising the restricted fraction from 0.10 to 0.70 at three tenants moved D1's context from "
              f"{f(SW['restricted'][0]['bm25']['postfilter_topk']['authorized']['mean_context_docs'])} to {f(SW['restricted'][3]['bm25']['postfilter_topk']['authorized']['mean_context_docs'])} documents; the recall gap stayed between {min(_gap('bm25', src=c) for c in SW['restricted']):.1f} and {max(_gap('bm25', src=c) for c in SW['restricted']):.1f} points (BM25) and {min(_gap('dense', src=c) for c in SW['restricted']):.1f} and {max(_gap('dense', src=c) for c in SW['restricted']):.1f} points (dense) without a monotone trend, because raising the restricted fraction lowers the analyst's authorized share but leaves the manager's unchanged, and the two roles contribute equally to the workload. "
              f"Smaller k made the loss larger in relative terms: at k = 2, D1 returned {f(SW['k'][0]['bm25']['postfilter_topk']['authorized']['mean_context_docs'])} documents on average and lost "
              f"{100*(SW['k'][0]['bm25']['prefilter']['authorized']['target_recall']-SW['k'][0]['bm25']['postfilter_topk']['authorized']['target_recall']):.1f} (BM25) and {100*(SW['k'][0]['dense']['prefilter']['authorized']['target_recall']-SW['k'][0]['dense']['postfilter_topk']['authorized']['target_recall']):.1f} (dense) points. "
              f"Indexed corpus size changed the absolute recall of every design, from {pct(SW['corpus'][0]['bm25']['prefilter']['authorized']['target_recall'])}% at 1,000 documents to {pct(SW['corpus'][3]['bm25']['prefilter']['authorized']['target_recall'])}% at {SW['corpus'][3]['config']['corpus_size']:,} for BM25 pre-filtering, "
              f"but left D1's context size near two documents at every size, while the D1-to-D3 gap grew only modestly, from {_gap('bm25', src=SW['corpus'][0]):.1f} to {_gap('bm25', src=SW['corpus'][3]):.1f} points for BM25 and from {_gap('dense', src=SW['corpus'][0]):.1f} to {_gap('dense', src=SW['corpus'][3]):.1f} points for the dense retriever, as more competitors entered the ranking. "
              "Starvation is a function of authorized share, not of corpus size, and the recall gap is governed primarily by authorized share and secondarily by corpus size, which supports P2."),
        ("table", tS),
        ("figure", {"path": "fig5_tenants.png", "width_cm": 15.5,
                    "caption": "Figure 5. Tenant sweep. Left: mean context documents under top-k-only post-filtering as the number of tenants grows (k = 5). Right: Recall@5 lost against pre-filtering for top-k-only post-filtering and for over-fetch 5x."}),
        ("p", f"Across five seeds of the main configuration, BM25 pre-filter Recall@5 was {100*mb:.1f} ± {100*sb:.1f}% and D1 was {100*mb1:.1f} ± {100*sb1:.1f}%; the dense retriever gave "
              f"{100*md:.1f} ± {100*sd:.1f}% and {100*md1:.1f} ± {100*sd1:.1f}% (mean ± standard deviation). The gaps reported above are therefore several standard deviations wide and "
              "do not depend on the particular tenant assignment."),
        ("h2", "5.3. Experiment C: Post-Filtering Leaks Existence Through Result Counts"),
        ("p", f"Table 7 and Figure 6 report the existence oracle. Under top-k-only post-filtering the returned count identified whether a forbidden document existed with AUC "
              f"{top['bm25_oracle_restricted']['postfilter_topk']['auc']:.2f} (BM25) and {top['dense_oracle_restricted']['postfilter_topk']['auc']:.2f} (dense) when the attacker could read {pct(top['attacker_authorized_fraction'],0)}% of the corpus, "
              f"the situation of a privileged insider probing for the few documents withheld from them. The signal weakened as the attacker's authorized share shrank, to about "
              f"{mid['bm25_oracle_restricted']['postfilter_topk']['auc']:.2f} and {mid['dense_oracle_restricted']['postfilter_topk']['auc']:.2f} at {pct(mid['attacker_authorized_fraction'],0)}%, because the count is then dominated by the many unauthorized documents that occupy the top k on every query, "
              "whether or not the probed document exists. Over-fetching reduced the leak only once the factor was large enough to keep the returned count constant: at m = 2 the AUC was still "
              f"{mid['bm25_oracle_restricted']['postfilter_x2']['auc']:.2f} and {mid['dense_oracle_restricted']['postfilter_x2']['auc']:.2f} at the main configuration, and in several low-share configurations m = 2 or m = 5 leaked slightly more than m = 1 because a saturated short list carries less information than a partially refilled one. "
              f"At m = 20 and under pre-filtering the AUC was {min(min(r[k]['postfilter_x20']['auc'], r[k]['prefilter']['auc']) for r in o for k in ('bm25_oracle_restricted','dense_oracle_restricted')):.2f} to {max(max(r[k]['postfilter_x20']['auc'], r[k]['prefilter']['auc']) for r in o for k in ('bm25_oracle_restricted','dense_oracle_restricted')):.2f} in every configuration and for both retrievers, which is chance. "
              "The cross-tenant variant of the oracle, in which the positives are documents in another tenant, behaved the same way. This supports P3 and gives the result-count channel described for relational and full-text systems {Espiritu2026} a measured counterpart in lexical and vector retrieval."),
        ("table", tO),
        ("figure", {"path": "fig6_oracle.png", "width_cm": 15.5,
                    "caption": "Figure 6. Experiment C. AUC of the result-count existence oracle against the share of the corpus the attacker may read, for BM25 (left) and the dense retriever (right). The dashed line is chance."}),
        ("h2", "5.4. Experiment D: Revocation Lag"),
        ("p", f"Table 8 and Figure 7 report the replay. Without an E4 re-check, stale exposure scaled with the reconciliation interval: {f(d_run(1.0,'none')['stale_docs_per_10k_queries'],1)} revoked documents per 10,000 queries at one minute, "
              f"{f(rev_none_60['stale_docs_per_10k_queries'],0)} at one hour, and {f(rev_none_24['stale_docs_per_10k_queries'],0)} with daily reconciliation, when {pct(rev_none_24['stale_query_rate'])}% of all queries over the day served revoked content and the oldest stale document was "
              f"{rev_none_24['max_stale_age_min']/60:.1f} hours past its revocation. A re-check against a cached policy with a five-minute time to live bounded stale exposure at roughly {f(rev_cached_60['stale_docs_per_10k_queries'],0)} documents per 10,000 queries "
              f"and a maximum age of {f(rev_cached_24['max_stale_age_min'],1)} minutes regardless of the reconciliation interval. A re-check against the live policy store served no stale document in any configuration. "
              "The absolute values depend on the revocation rate chosen for the replay; the structure does not. E2 determines how long the index is wrong, E4 determines whether the user sees it, and the two are independent controls. This supports P4."),
        ("table", tR),
        ("figure", {"path": "fig7_revocation.png", "width_cm": 14.0,
                    "caption": "Figure 7. Experiment D. Revoked documents served per 10,000 queries (log scale) by E2 reconciliation interval and E4 re-check mode."}),
    ]
    if tL is not None:
        rows = e_rows(3, "t0_analyst")
        r10, r250 = rows[0], rows[-1]
        rows10 = e_rows(10, "t0_analyst")
        hx1 = [r["hnsw_postfilter_x1"] for r in rows]
        blocks += [
            ("h2", "5.5. Experiment E: Enforcement Cost on Vector Indexes"),
            ("p", _expE_text(rows, rows10)),
            ("table", tL),
            ("figure", {"path": "fig8_latency.png", "width_cm": 15.5,
                        "caption": "Figure 8. Experiment E. Left: median per-query latency by index arrangement and enforcement design as the index grows (analyst, three tenants). Right: effective recall against the exact pre-filtered top-5 for HNSW designs."}),
        ]
    return blocks


DISCUSSION = [
    ("h1", "6. Discussion"),
    ("h2", "6.1. Answers to the Research Questions"),
    ("p", "RQ1. Every filtered design eliminated unauthorized exposure on both corpora and both retrievers, so authorization correctness does not "
          "separate them. Utility does. Top-k-only post-filtering preserved exactly the unfiltered recall and discarded most of the context; "
          "pre-filtering raised recall by freeing slots that unauthorized competitors had occupied; over-fetching recovered the same recall once the "
          "factor was large enough. P1 is supported in a specific form: enforcement before ranking is sufficient, and post-ranking enforcement is "
          "equivalent only when the candidate pool is sized to the principal's authorized share."),
    ("p", "RQ2. The principal's authorized share of the corpus is the governing variable. Context starvation under top-k post-filtering tracked that "
          "share almost exactly, the recall gap grew as the share shrank, and the over-fetch factor needed to close the gap grew from 2 at one tenant "
          "to 20 at ten. An eightfold increase in corpus size shifted absolute recall for every design and widened the gap only modestly. The retriever changed the magnitude: the dense retriever, "
          "which ranks the target lower on average, lost more under D1 than BM25 and needed a larger factor to recover. P2 is supported."),
    ("p", "RQ3. Post-filtering created a measurable existence oracle through result counts, strongest for privileged insiders, and small over-fetch "
          "factors did not remove it. Pre-filtering and over-fetch factors large enough to keep the count constant did. Enforcement cost was governed by "
          "whether the index implemented the predicate natively: an ID selector on an exact index paid off only at low selectivity or small size, partitioned "
          "exact indexes were the cheapest correct arrangement throughout, and on graph indexes top-k post-filtering was both the cheapest and the least useful. P3 is supported."),
    ("p", "RQ4. Stale exposure is the product of two independent controls. The reconciliation interval sets how long the index is wrong; the E4 "
          "re-check sets whether a user sees it. A live re-check served nothing stale at any interval; a cached re-check bounded stale age to its time "
          "to live. P4 is supported."),
    ("h2", "6.2. Design Rules for Practitioners"),
    ("p", "The results translate into rules that an engineering team can apply and test."),
    ("bullets", [
        "Never filter a truncated list. If the retriever returns k candidates and the filter runs afterwards, the design is D1, and its context will shrink in proportion to the share of the corpus the user cannot read.",
        "Prefer pre-filtering when the index can push the predicate into the search, and measure whether it does. An ID selector on an exact index is a per-vector membership test, not native pushdown; in Experiment E it beat a full scan only at low selectivity or small index size. Partitioned exact indexes and filter-aware graph indexes are the designs that make pre-filtering cheap. On graph indexes, measure effective recall at the lowest selectivity the deployment will see, because post-hoc selectors degrade there.",
        "If post-filtering is unavoidable, size the over-fetch factor to the authorized share. A factor of roughly 1.5 to 2 times the inverse of the smallest authorized share closed the gap in every configuration here (m = 2 at a 67% share, m = 5 at 34%, m = 10 at 22% and 13%, m = 20 at 7%). Treat the factor as a per-principal parameter, not a constant.",
        "Always return exactly k results or an explicit empty answer. A variable result count is an existence oracle. Over-fetching only removes the channel when the pool is large enough that the count never varies.",
        "Re-check at context assembly against the live policy store. This is the control that makes revocation effective and catches index drift and E3 bugs; its cost is one policy lookup per context document.",
        "Declare and measure a revocation objective. Choose the reconciliation interval from the stale-exposure budget, and report stale documents per 10,000 queries as a regression metric.",
        "Keep partitioning in the design space. One exact index per tenant and clearance was the cheapest exact arrangement measured and removes the result-count and score channels by construction, at the cost of index management.",
    ]),
    ("h2", "6.3. Governance Mapping"),
    ("p", "Table 2 gives each governance artifact a measurable test. An access-policy test report with allowed, denied, and probe cases is the "
          "evidence behind the Measure function for T1; the enforcement-design record, which states whether the deployment uses D2 or D3 and how the "
          "over-fetch factor was chosen, is the Govern artifact for T5; the revocation objective and its measured lag are the Manage artifact for "
          "stale labels. These artifacts are the kind of operational evidence that the NIST Generative AI Profile and ISO/IEC 42001 call for "
          "without specifying {Autio2024,ISO2023}, and they complement the incident-response and deployment frameworks recently proposed in this "
          "journal {Tuscano2026,Torstensson2026}. None of them demonstrates compliance by itself. Each shows that a specific control was tested and what the result was."),
    ("h2", "6.4. Relation to the Closest Studies"),
    ("p", "The results agree in direction with Arceo and Narsing, who observed recall degradation under post-retrieval filtering without predicate "
          "pushdown {Arceo2026}, and with Nagabathula, who measured a recall drop from 0.61 to 0.37 under post-filtering on Reuters-21578 with dense "
          "retrieval and partial recovery at 16-fold over-fetch {Nagabathula2026}. The magnitudes differ because the permission assignments, "
          "retrievers, and query generators differ; the present study adds the finding that the authorized share, not corpus size, predicts the loss "
          "and the required factor. The result-count oracle gives the analysis of Espiritu and Cash {Espiritu2026} a measured counterpart in retrieval "
          "for RAG and shows that the channel is strongest for the insider case that enterprise deployments should worry about most. PAER does not "
          "claim novelty for IAM-aware retrieval {Jeong2025}, embedding-level access control {Thuillier2026}, or permission checks before generation "
          "{Chen2025}; its contribution is the matched protocol in which those designs can be compared and the architectural placement of the "
          "controls that the measurements favor."),
    ("h2", "6.5. Threats to Validity"),
    ("p", "Construct validity. Known-item queries make authorized recall unambiguous but understate the ambiguity of natural enterprise queries; "
          "headline and sentence queries bracket two realistic cases and agree in direction. The existence oracle uses the simplest observable, the "
          "result count, and therefore gives a lower bound on T5; scores, ranks, timing, and shared statistics are further channels. Internal "
          "validity. Tenant and clearance labels are assigned at random, so the corpus has no topical correlation with tenancy; in enterprises tenants "
          "differ in topic, which would make cross-tenant competition weaker for some queries and stronger for near-duplicate documents. The five-seed "
          "repetition shows that the gaps are stable under random re-assignment. External validity. One corpus, two retrievers, and one static "
          "embedding model were evaluated; the direction of every effect follows from the mechanism, but magnitudes for transformer encoders and "
          "domain corpora must be measured. Timing figures come from one small machine and an in-memory Qdrant client, and they order designs rather than predict production latency."),

    ("h1", "7. Limitations and Future Work"),
    ("p", "This study has four main limitations. First, it evaluates the retrieval layer only. Real-LLM leakage under paraphrase, natural-language "
          "refusal quality, claim-level citation accuracy, and resistance to indirect prompt injection (T3) are untested here and are the natural next "
          "experiments; the harness exposes the assembled context for each query so that a generation stage can be attached without changing the "
          "retrieval protocol. Second, the dense retriever is a static-embedding model chosen so that the harness runs offline. Transformer encoders "
          "rank targets higher on average, which Experiment B suggests would narrow the D1 gap for easy queries and leave it unchanged for ambiguous "
          "ones; this should be measured rather than assumed. Third, the revocation replay models reconciliation as periodic and the policy store as "
          "consistent; distributed policy caches, event-driven propagation, and partial failures are not modelled. Fourth, the vector-index "
          "experiment uses FAISS and the in-memory Qdrant client on a single machine; server-side filterable indexes, concurrency, and throughput "
          "at production scale remain to be measured, and filter-aware graph indexes should be included as a design. No claim of security guarantee, "
          "production readiness, or superiority over existing systems is made."),

    ("h1", "8. Conclusions"),
    ("p", "Enterprise RAG must preserve the authorization regimes of the repositories it indexes, and permission-aware retrieval is an established "
          "engineering direction. What has been missing is a matched measurement of where enforcement belongs. This paper specified the PAER "
          "reference architecture, with five enforcement points and a threat model that names enforcement side channels explicitly, and evaluated "
          "its retrieval-layer choices with a released harness across a mirrored benchmark, a real corpus, two retrievers, five seeds, four sweeps, "
          "a side-channel measurement, a revocation replay, and four vector-index arrangements. Three results stand out. Filtering a truncated top-k "
          "list is safe and starves the context in proportion to the share of the corpus the user cannot read; pre-filtering, or over-fetching sized "
          "to that share, recovers the loss. Post-filtering leaks document existence through result counts, most strongly for privileged insiders, "
          "and pre-filtering removes the channel. A live re-check at context assembly bounds stale exposure independently of how often the index is "
          "reconciled. The practical rule is short: authorize before ranking or over-fetch to the authorized share, return a constant number of "
          "results, re-verify against live policy at context assembly, and measure revocation lag. Future work will attach a generation stage, "
          "evaluate transformer encoders and filter-aware graph indexes, and extend the protocol to distributed policy propagation."),
]

BACK = [
    ("h1", "Funding"),
    ("p", "This research received no external funding."),
    ("h1", "Data Availability Statement"),
    ("p", "The harness source code, the generated mirrored corpus and workloads, the Reuters-21578 preparation script, the per-configuration result files for every "
          "experiment, the figure-generation script, and the exact package versions are available at [REPOSITORY URL AND ZENODO DOI TO BE INSERTED BY THE AUTHOR BEFORE SUBMISSION]. "
          "Reuters-21578 is public {Lewis1997}. Every value in this paper is regenerated from the stated seeds."),
    ("h1", "Acknowledgments"),
    ("p", "Generative AI tools (Claude, Anthropic; ChatGPT, OpenAI) were used to assist with experiment code, structuring, language editing, and reference formatting. "
          "The author designed the study, verified every result, and takes full responsibility for the content."),
    ("h1", "Conflicts of Interest"),
    ("p", "The author is employed by Tesla, Inc. This work was conducted independently of that employment, uses no Tesla data or systems, and does not represent the views of Tesla, Inc. "
          "The author declares no other conflicts of interest."),
    ("h1", "Abbreviations"),
    ("p", "ABAC, attribute-based access control; ACL, access control list; ANN, approximate nearest neighbor; AUC, area under the receiver operating characteristic curve; "
          "BM25, Okapi best-match ranking function; HNSW, hierarchical navigable small world; IAM, identity and access management; LLM, large language model; "
          "PAER, Policy-Aware Enterprise RAG; RAG, retrieval-augmented generation; RBAC, role-based access control; TTL, time to live."),
]
