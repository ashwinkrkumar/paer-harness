"""Section 3 (threat model and architecture) and Section 4 (evaluation protocol)."""

from numbers_ import *  # noqa

TABLE1 = {
    "caption": "Table 1. Closest studies and the constructs each one measures. Filled circle: measured; open circle: discussed but not measured; blank: not addressed.",
    "header": ["Study", "Authorization", "Authorized recall", "Context starvation", "Side channels", "Revocation", "Index cost", "Generation leakage"],
    "rows": [
        ["Jeong and Lee {Jeong2025}", "●", "●", "", "", "○", "○", ""],
        ["Arceo and Narsing {Arceo2026}", "●", "●", "○", "", "", "○", "○"],
        ["Thuillier et al. {Thuillier2026}", "●", "●", "", "", "", "", ""],
        ["Chen et al. {Chen2025}", "●", "●", "", "", "", "", "○"],
        ["Jayaraman et al. {Jayaraman2025}", "● (fine-tuning)", "●", "", "", "", "", "●"],
        ["Espiritu and Cash {Espiritu2026}", "●", "", "", "● (RLS, DLS)", "", "●", ""],
        ["Nagabathula {Nagabathula2026}", "●", "●", "○", "●", "", "", ""],
        ["Zhang et al. {ZhangWu2026}", "", "●", "", "", "", "", "●"],
        ["Bhatt et al. {Bhatt2025}", "○", "", "", "", "", "", "●"],
        ["PAER (this paper)", "●", "●", "●", "●", "●", "●", "○ (future work)"],
    ],
    "widths": [4.2, 2.0, 2.0, 1.6, 1.8, 1.6, 1.4, 2.0],
}

TABLE2 = {
    "caption": "Table 2. Traceability chain from threat channel to enforcement point, metric, and governance artifact. NIST AI RMF functions in parentheses.",
    "header": ["Threat", "Enforcement point(s)", "Metric(s) in this paper", "Governance artifact (NIST function)"],
    "rows": [
        ["T1 Unauthorized retrieval, cross-tenant access", "E3, E4", "Unauthorized context rate; query exposure rate; foreign-target reach; provenance fidelity", "Access-policy test report with allowed, denied, and probe cases (Measure)"],
        ["T2 Knowledge-base poisoning", "E1, E4", "Metadata completeness; E4 re-check failures (integrity checks outside scope)", "Ingestion integrity log and source attestation (Map, Manage)"],
        ["T3 Indirect prompt injection via retrieved content", "E4, E5", "Not measured here; see Section 7", "Content-sanitization and tool-permission policy (Govern, Manage)"],
        ["T4 Output-side disclosure", "E5", "Canary-echo leak rate after output gate (self-consistency only)", "Output-gate configuration and test evidence (Measure)"],
        ["T5 Enforcement side channels", "E3 (design choice), E2", "Existence-oracle AUC; stale documents per 10,000 queries; revocation lag", "Enforcement-design record; revocation objective and reconciliation SLA (Govern, Manage)"],
    ],
    "widths": [3.6, 2.2, 5.2, 5.4],
}

TABLE3 = {
    "caption": "Table 3. Metrics computed by the harness. All are retrieval-layer measures and require no language model.",
    "header": ["Metric", "Definition", "Threat / property"],
    "rows": [
        ["Unauthorized context rate", "Unauthorized documents entering the context divided by all context documents", "T1 confidentiality"],
        ["Query exposure rate", "Share of queries whose context holds at least one unauthorized document", "T1 confidentiality"],
        ["Candidate-stage unauthorized rate", "Unauthorized records in the candidate list before any post-filter", "Diagnostic for D1, D2"],
        ["Authorized-target Recall@k", "Share of authorized queries whose known permitted target appears in the final context", "Utility"],
        ["Mean context documents", "Average number of documents in the final context (k at most)", "Context starvation"],
        ["Foreign-target reach", "Share of cross-tenant probes in which the requested forbidden document entered the context", "T1 cross-tenant"],
        ["Provenance fidelity", "Share of context documents whose identifier resolves to a record the requester may read", "Provenance"],
        ["Existence-oracle AUC", "Mann-Whitney AUC of the result count as a detector of a forbidden document's existence", "T5 side channel"],
        ["Stale documents per 10,000 queries", "Revoked documents served in context, normalized by query volume, in the revocation replay", "T5 stale labels; E2, E4"],
        ["Per-query latency and effective recall", "Median and p95 latency; recall against exact pre-filtered top-k on the same index", "Cost; utility"],
    ],
    "widths": [4.0, 8.4, 4.0],
}

METHOD = [
    ("h1", "3. Threat Model and the PAER Reference Architecture"),
    ("h2", "3.1. Assets and Trust Boundaries"),
    ("p", "Three asset properties are protected. Confidentiality: only permitted evidence is retrieved and disclosed. Integrity: "
          "retrieved evidence is not maliciously manipulated. Provenance: claims can be traced to permitted source chunks. The enterprise "
          "trust boundary contains users and agents, source repositories with native access control, the vector index, and the PAER data "
          "plane. The model provider, whether hosted externally or operated internally as a separate service, sits outside that boundary "
          "and receives only the assembled context (Figure 1)."),
    ("h2", "3.2. Threat Channels"),
    ("p", "Four channels are standard in the RAG security literature {Greshake2023,ZhangCarlini2024,Koga2024,Arzanipour2025,Zou2025,Mu2026,Bhatt2025}: "
          "unauthorized retrieval across tenant or role boundaries (T1), knowledge-base poisoning (T2), indirect prompt injection through "
          "retrieved content (T3), and output-side disclosure by paraphrase or extraction (T4). This paper adds a fifth channel, enforcement "
          "side channels (T5), which groups leaks created by the enforcement mechanism itself rather than by the content: the number of "
          "results returned after a post-filter, scores or ranks that reflect hidden documents, and stale permission labels in the index. "
          "T5 follows directly from the analysis of Espiritu and Cash for relational and full-text systems {Espiritu2026}; this paper measures "
          "its result-count form for vector and lexical retrieval."),
    ("figure", {"path": "fig1_threat_model.png", "width_cm": 15.5,
                "caption": "Figure 1. PAER threat model and trust boundaries. T1 to T4 are the channels usually listed; T5 groups side channels created by the enforcement mechanism itself."}),
    ("h2", "3.3. Enforcement Points"),
    ("p", "PAER is a dual-plane reference design (Figure 2). The control plane manages identity context, policy decisions and versions, "
          "revocation and reconciliation, and audit evidence. The data plane executes retrieval and generation and applies authorization at "
          "five points."),
    ("bullets", [
        "E1, ingestion. Every indexed chunk carries the tenant, clearance, and document labels inherited from its source, and the pipeline "
        "rejects records whose labels are missing or malformed.",
        "E2, index and revocation. Permission changes at the source propagate into the index, either synchronously or through periodic "
        "reconciliation, and the reconciliation interval is a declared, measured quantity rather than an accident of the batch schedule.",
        "E3, query-time filtering. Authorization is applied before restricted candidates enter ranking (pre-filtering), or a candidate pool "
        "large enough to refill the context is retrieved and then filtered (over-fetching). Filtering a truncated top-k list is treated as a "
        "known failure mode.",
        "E4, context assembly. Authorization and provenance are re-checked against the live policy store for every document about to enter "
        "the prompt. This catches stale index labels and bugs in E3, and it is the point at which revocation becomes effective regardless of E2.",
        "E5, output safeguards. Disclosure checks and a bounded, rule-based refusal apply at generation time. A deterministic policy gate is "
        "not the same as a language model's learned refusal behavior; the latter requires its own evaluation.",
    ]),
    ("figure", {"path": "fig2_architecture.png", "width_cm": 15.5,
                "caption": "Figure 2. The PAER reference architecture. The control plane supplies identity, policy, and audit context; the data plane enforces access at ingestion, index and revocation, query-time filtering, context assembly, and output."}),
    ("h2", "3.4. Traceability Chain"),
    ("p", "Table 2 links each threat channel to the enforcement points that address it, to the metrics this paper computes, and to the "
          "governance artifact that a compliance program would keep. The mapping to the NIST AI RMF functions is a design proposal: policy "
          "ownership and change control align with Govern, threat identification with Map, metrics and test evidence with Measure, and "
          "remediation and revocation with Manage {Tabassi2023,Autio2024}. Alignment with a governance framework does not prove compliance or "
          "security effectiveness. Its value is that every governance artifact in the table has a test behind it."),
    ("table", TABLE2),
    ("h2", "3.5. Design Propositions"),
    ("p", "Four propositions structure the experiments. They are hypotheses, and Section 6 states which were supported. P1: enforcement "
          "before context construction reduces exposure of unauthorized chunks relative to filtering a truncated top-k list, and preserves "
          "authorized recall that top-k post-filtering loses. P2: the recall cost of top-k post-filtering, and the over-fetch factor needed to "
          "recover it, are governed primarily by the principal's authorized share of the corpus and only secondarily by corpus size. P3: post-filtering creates a "
          "result-count existence oracle whose strength grows with the attacker's authorized share, and pre-filtering removes it. P4: a live "
          "context re-check at E4 bounds stale exposure independently of the E2 reconciliation interval."),

    ("h1", "4. Materials and Methods"),
    ("h2", "4.1. Policy Model and Principals"),
    ("p", "The harness uses a deliberately simple policy so that every result is attributable to enforcement placement rather than to policy "
          "expressiveness. Every document carries a tenant label and a clearance label, general or restricted. A principal is a tenant and "
          "role pair. A principal may read a document only if the tenant labels match; general documents are readable by analysts and "
          "managers; restricted documents are readable by managers only. Revocation is modelled as an explicit deny on a document for a role, "
          "or as withdrawal of a document from its tenant. The policy store is the single source of truth, and the index holds a copy of its "
          "labels."),
    ("h2", "4.2. Enforcement Designs"),
    ("p", "Four designs are compared throughout. D0, unfiltered: rank the whole corpus and return the top k. D1, post-filter on the truncated "
          "list: rank the whole corpus, remove unauthorized items from the top k, and return what remains. D2, post-filter with over-fetch: "
          "rank the whole corpus, take the top m × k candidates, remove unauthorized items, and keep up to k. D3, pre-filter: restrict the "
          "candidate set to documents the principal may read, then rank. D1 is the simplest retrofit and is what a framework does when it "
          "filters a retriever's default output. D2 is common production practice. D3 requires predicate support in the index. In all filtered "
          "designs, E4 re-checks every context document against the policy store and E5 applies an output gate."),
    ("h2", "4.3. Metrics"),
    ("p", "Table 3 defines the metrics. All are computed at the retrieval layer and require no language model. The existence-oracle AUC is a "
          "Mann-Whitney statistic: 0.5 means the observable carries no information about whether a forbidden document exists, and 1.0 means it "
          "identifies existence perfectly. Latency is reported as the median and 95th percentile of per-query wall-clock time with intra-query "
          "parallelism disabled, so that the numbers reflect single-query cost rather than thread scheduling."),
    ("table", TABLE3),
    ("h2", "4.4. Experiment A: Mirrored Synthetic Benchmark"),
    ("p", "Experiment A reproduces the closed-form failure mode of D1. The corpus contains 270 synthetic documents: three tenants, 30 topics, "
          "and three documents per topic in each tenant (an overview, a procedure, and an escalation document). Overview and procedure documents "
          "are general; escalation documents are restricted. The three tenants are mirror images that differ only in labels and in a unique "
          "canary string per document. The workload has 900 authorized queries (five for each tenant, topic, and role combination), each with a "
          "known permitted target, and 90 cross-tenant probes that request a document in another tenant. Queries name topic and document type "
          "but not tenant. Retrieval is lexical token overlap with deterministic tie-breaking on document identifier and k = 2. The seed is 20261014. "
          "Because the three copies of any document score identically, whole-corpus ranking at k = 2 always holds two of the three copies, and "
          "the requester's own copy is among them for two tenants out of three. The recurring value of two thirds in the results is a property of "
          "the construction. The benchmark is kept because it isolates the mechanism; Experiment B measures the magnitude on a real corpus. "
          "Experiment A also runs the self-consistency checks for E1 (label completeness on every record), E2 (synchronous revocation of one "
          "target followed by a re-query), E4 (zero re-check failures), and E5 (canary strings in a deterministic echo of the context before and "
          "after an ACL output gate)."),
    ("h2", "4.5. Experiment B: Non-Mirrored Real Corpus, Two Retrievers"),
    ("p", f"Experiment B uses Reuters-21578 {{Lewis1997}} in the distribution shipped with NLTK {{Bird2009}}. Documents with fewer than ten content "
          f"tokens in the body or without a headline are dropped, leaving 8,451 documents, of which 400 are held out as never-indexed negatives for "
          f"Experiment C and {B['config']['corpus_size']:,} are indexed. Each indexed document is assigned to one of T tenants uniformly at random and "
          f"marked restricted with probability p, using a seeded generator; the main configuration is T = 3 and p = 1/3, which gives an analyst "
          f"in tenant 0 access to {pct(B['authorized_fraction']['t0_analyst'],0)}% of the corpus and a manager to {pct(B['authorized_fraction']['t0_manager'],0)}%. "
          "Two query types are generated for each target document. Headline queries use the document's headline words (up to eight content "
          "tokens) and emulate a user who asks for a document by subject; Reuters headlines are short and frequently near-duplicated across "
          "documents, so the target competes with similar documents from every tenant. Sentence queries use the content words of one body "
          "sentence other than the lead and emulate a user who remembers a passage. Known-item queries with a single permitted target were chosen "
          "because they make authorized recall unambiguous."),
    ("p", f"For each tenant and role, {B['config']['authorized_queries']//6} permitted targets are sampled, giving {B['config']['authorized_queries']:,} authorized "
          f"queries, and {B['config']['probes']//3} forbidden targets per tenant are sampled for an analyst principal, giving {B['config']['probes']} cross-tenant and "
          "cross-clearance probes. Two retrievers are evaluated. BM25 (Okapi, k1 = 1.5, b = 0.75) is implemented over a sparse term matrix "
          "{Robertson2009}. The dense retriever uses WordLlama l2_supercat embeddings, 256-dimensional static token embeddings recycled from a "
          "Llama-3 model and trained with a contrastive objective, averaged and unit-normalised {Miller2024}, indexed exactly with FAISS IndexFlatIP "
          "{Douze2024}; pre-filtering uses a FAISS ID selector. A static-embedding retriever was chosen so that the harness runs offline without "
          "model downloads; Section 7 discusses the consequences. The main configuration uses k = 5 and over-fetch factors m in {2, 5, 10, 20, 50}. "
          "Sweeps vary T in {1, 2, 3, 5, 10}, p in {0.10, 0.33, 0.50, 0.70}, k in {2, 5, 10}, and indexed corpus size in {1,000, 2,500, 5,000, all}. "
          "The main configuration is repeated with five seeds."),
    ("h2", "4.6. Experiment C: Result-Count Existence Oracle"),
    ("p", "Experiment C measures T5 in its simplest form. The attacker is an analyst in tenant 0 who issues a known-item query for a document "
          "and observes only how many results the system returns. Positives are queries for documents that exist in the index but are forbidden "
          "to the attacker (restricted documents in tenant 0, or documents in another tenant). Negatives are queries for the 400 held-out documents, "
          "which are not in the index at all. The attacker's score is k minus the returned count. Under D1 a forbidden document that outranks "
          "permitted ones leaves an empty slot; under D2 the slot is refilled unless the over-fetch pool is exhausted; under D3 the count is "
          "always k. The AUC is reported per design and retriever for twelve configurations of T in {1, 2, 3, 5} and p in {0.10, 0.33, 0.50}, "
          "which vary the attacker's authorized share of the corpus from about 10% to 90%."),
    ("h2", "4.7. Experiment D: Revocation Lag Replay"),
    ("p", f"Experiment D replays a query stream against the BM25 retriever on the main configuration while source revocations arrive. Queries "
          f"arrive as a Poisson process at {D['query_rate_h']} per hour and revocations at {D['revoke_rate_h']} per hour over a {D['horizon_h']:.0f}-hour horizon, with revoked "
          "documents drawn from the documents the query stream actually targets so that revocations are observable. A revoked document is "
          "withdrawn from its tenant at the source. The index reflects the revocation only at the next E2 reconciliation, with intervals of "
          "1, 15, and 60 minutes and 24 hours. Three E4 modes are compared: no re-check, a re-check against a cached policy snapshot with a "
          "five-minute time to live, and a re-check against the live policy store. The outcome is the number of revoked documents served in "
          "context per 10,000 queries, the share of queries served stale, and the maximum age of stale content. Absolute values scale with the "
          "revocation rate; the ordering and the bounding behavior are the findings."),
    ("h2", "4.8. Experiment E: Enforcement Cost on Vector Indexes"),
    ("p", "Experiment E measures what enforcement placement costs on real vector indexes and how much effective recall each design keeps. "
          "Vectors are the WordLlama embeddings of the Reuters documents, augmented to 10,000, 50,000, 100,000, and 250,000 vectors with jittered "
          "copies (Gaussian noise with standard deviation 0.05, renormalised) so that the score distribution stays realistic. Labels are "
          "assigned as in Experiment B for T in {3, 10}; the principal is an analyst or a manager in tenant 0, which gives selectivities between "
          "about 7% and 34%. Four index arrangements are compared on 200 real headline queries with k = 5: an exact FAISS flat index with "
          "full-scan post-filtering (m in {1, 5, 20}) or ID-selector pre-filtering; a FAISS HNSW graph index (M = 32, efConstruction = 200, "
          "efSearch = 128) {Malkov2020,Douze2024} with the same two options; partitioned exact indexes, one per tenant and clearance, searched "
          "only for permitted partitions; and Qdrant's in-memory client with payload-filtered search versus unfiltered search with client-side "
          "post-filtering {Qdrant2026}, at 10,000 and 50,000 vectors. Ground truth for effective recall is the exact pre-filtered top-k."),
    ("h2", "4.9. Reproducibility and Environment"),
    ("p", f"The harness is written in Python, was run with {python_sentence()}, and depends on {package_sentence()}. "
          "It downloads nothing at run time beyond the public Reuters-21578 archive. Every experiment is seeded, and "
          f"every number, table, and figure in this paper is regenerated by the released scripts. Timing figures were recorded on {environment_sentence()} "
          "with OpenMP limited to one thread, so that they reflect single-query cost; they order the designs within the harness and should not be "
          "read as production latencies. Experiment A reproduces exactly across platforms. Experiments B to D depend on floating-point score ties "
          "and, between an x86-64 Linux machine and an Apple M2 machine, differed by at most 0.3 recall points, 0.01 AUC, 0.05 context documents, "
          "and 0.7 stale documents per 10,000 queries; no conclusion in this paper rests on differences of that size. All data are public or "
          "synthetic; no personal, customer, or enterprise data were used."),
]
