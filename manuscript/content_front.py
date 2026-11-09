"""Front matter, Introduction, Related Work."""

from numbers_ import *  # noqa

TITLE = ("Where to Enforce Authorization in Enterprise Retrieval-Augmented Generation: "
         "The PAER Reference Architecture and a Reproducible Evaluation")

AUTHOR = "Ashwin Krishnappa Kumar"
AFFIL = "Tesla, Inc., Austin, TX 78725, USA; ORCID 0009-0007-7020-4227"

ABSTRACT = (
    "Enterprise retrieval-augmented generation (RAG) copies documents out of repositories that enforce access control and into vector "
    "indexes that do not. Where authorization belongs in the retrieval pipeline has been answered in prototypes but rarely measured under one "
    "protocol. This paper specifies the Policy-Aware Enterprise RAG (PAER) reference architecture, with five enforcement points and a threat "
    "model that names enforcement side channels, and evaluates its retrieval-layer choices with a released harness. Six experiments compare "
    "unfiltered retrieval, top-k post-filtering, over-fetch post-filtering, and pre-filtering on a mirrored benchmark and on Reuters-21578 "
    f"({B['config']['corpus_size']:,} documents) with assigned tenant and clearance labels, two retrievers, five seeds, and four sweeps. All filtered designs eliminated exposure, but top-k post-filtering starved the context in proportion to the share of "
    f"the corpus a principal cannot read, filling {f(b('bm25','postfilter_topk','mean_context_docs'))} of 5 slots at three tenants and 1.1 at ten, and losing up to "
    f"{100*(SW['tenants'][4]['dense']['prefilter']['authorized']['target_recall']-SW['tenants'][4]['dense']['postfilter_topk']['authorized']['target_recall']):.0f} recall points against pre-filtering. Post-filtering also leaked document existence through result counts "
    f"(AUC {oracle_sorted()[-1]['bm25_oracle_restricted']['postfilter_topk']['auc']:.2f} for a privileged insider); pre-filtering removed the channel. A live context re-check bounded stale exposure "
    "after revocation independently of index reconciliation. On vector indexes up to 250,000 vectors, enforcement cost was decided by whether the index "
    "implemented the predicate natively rather than by placement alone, and graph indexes with top-k post-filtering returned fewer than two usable documents per query. Every value is "
    "regenerated from a fixed seed."
)

KEYWORDS = ("retrieval-augmented generation; access control; enterprise AI security; authorization; vector databases; "
            "data governance; information leakage; side channels; RBAC; ABAC")

FRONT = [
    ("h1", "1. Introduction"),
    ("p", "Retrieval-augmented generation (RAG) has moved from a research technique to a standard enterprise integration pattern. "
          "Rather than fine-tuning a model on enterprise document stores, a RAG system retrieves relevant passages from an external "
          "corpus and supplies them to the model as context at inference time, so the model weights are never updated by the "
          "retrieval process {Lewis2020}. Surveys of the fast-growing literature document its spread into enterprise assistants, "
          "question answering, and knowledge-intensive workflows {Gao2023,Fan2024,Ni2026,Wu2026}."),
    ("p", "The same architectural shift moves enterprise data across a security boundary that most data-governance programs were "
          "not designed to oversee. Documents leave source repositories, where access control lists, group memberships, and "
          "inheritance rules have been curated for years, and are chunked, embedded, and placed in a vector index that historically "
          "enforces no authorization at all. A similarity search then returns the most relevant chunks to whoever asks {Jeong2025}. "
          "Because the model treats whatever it is given as ground truth, an unauthorized chunk that reaches the context window is "
          "not merely retrieved. It can be paraphrased into a plausible, natural-sounding answer that is harder to detect than an "
          "anomalous database query."),
    ("p", "The security concern is well documented. Research on RAG security addresses unauthorized disclosure {Arzanipour2025}, "
          "indirect prompt injection {Greshake2023,Schulhoff2023}, prompt and data extraction {ZhangCarlini2024}, and knowledge-base "
          "poisoning {Zou2025,Mu2026}. Governance frameworks and standards, including the NIST AI Risk Management Framework and its "
          "Generative AI Profile, OWASP guidance for LLM applications, ISO/IEC 42001, and the EU AI Act, supply principles, controls, "
          "and risk-management processes {Tabassi2023,Autio2024,OWASP2024,ISO2023,EU2024}. None of these, on its own, shows that a "
          "given architecture is secure. Standards define what an organization should manage, not operational metrics that an "
          "engineering team can regression-test against."),
    ("p", "Permission-aware RAG is also not an unsolved engineering problem. Several systems connect retrieval to identity and access "
          "management (IAM) back ends {Jeong2025}, gate multitenant retrieval and tool use with attribute-based policies {Arceo2026}, "
          "encode permissions in the embedding space {Thuillier2026}, or check document permissions before generation in a clinical "
          "setting {Chen2025}. What the literature has not supplied is a matched comparison of where enforcement is placed. Filtering "
          "after ranking is the simplest to retrofit and is what many frameworks do by default. Filtering before ranking requires "
          "predicate support in the index. Over-fetching sits between the two. These choices differ in three ways that matter to a "
          "security engineer: how much authorized recall they preserve, whether they open side channels, and what they cost on a real "
          "vector index. A fourth concern, permission freshness, is orthogonal to all three: labels copied into an index are a snapshot, "
          "and a revoked document stays visible until the index is reconciled."),
    ("p", "Two recent results sharpen the question. Espiritu and Cash show that post-filtering fine-grained access control in relational "
          "and full-text systems leaks the existence of hidden records through result shapes and timing, and that rich query interfaces "
          "turn that leak into full reconstruction {Espiritu2026}. An independent study on Reuters-21578 with dense retrieval found that "
          "post-filtering a global top-k cut known-item recall from 0.61 to 0.37, and that a 16-fold over-fetch recovered only part of the "
          "loss {Nagabathula2026}. Both findings concern the retrieval layer. Neither has been integrated into a reference architecture for "
          "enterprise RAG with metrics that a team can run."),
    ("p", "This paper addresses that gap. It specifies the Policy-Aware Enterprise RAG (PAER) reference architecture and evaluates its "
          "retrieval-layer enforcement choices with a released harness. Four research questions organize the study. RQ1: How much "
          "unauthorized exposure does each enforcement design allow, and how much authorized retrieval quality does it preserve? RQ2: How "
          "do those outcomes change with the principal's authorized share of the corpus, the clearance mix, k, corpus size, retriever, "
          "and query type? RQ3: Which enforcement designs open side channels, and what does enforcement cost on real vector indexes? "
          "RQ4: How should permission revocation be propagated and verified so that stale exposure is bounded?"),
    ("p", "The contributions are as follows."),
    ("bullets", [
        "A reference architecture, PAER, with five enforcement points (ingestion, index and revocation, query-time filtering, context "
        "assembly, output safeguards) on a dual control and data plane, a threat model with five channels that adds enforcement side "
        "channels to the four usually listed, and an explicit traceability chain from threat to enforcement point to metric to governance artifact.",
        "An evaluation protocol with ten retrieval-layer metrics covering authorization correctness, authorized retrieval quality, "
        "context starvation, provenance, side-channel leakage, revocation lag, and enforcement cost, each defined so that it can be computed "
        "without a language model.",
        f"A matched comparison of four enforcement designs on a mirrored synthetic benchmark and on Reuters-21578 with two retrievers, "
        f"{B['config']['authorized_queries']:,} authorized queries, {B['config']['probes']} cross-tenant probes, five seeds, and sweeps over tenants, clearance mix, k, and corpus size.",
        "A measurement of the result-count existence oracle created by post-filtering, showing that its strength grows with the attacker's "
        "authorized share of the corpus and that pre-filtering or a sufficiently large over-fetch removes it.",
        "A revocation replay that quantifies stale exposure as a function of index reconciliation interval and context re-check mode.",
        "A cost study on exact, graph, partitioned, and payload-filtered vector indexes up to 250,000 vectors, with effective recall "
        "measured against exact pre-filtered ground truth.",
        "A released harness, with no dependencies beyond common Python packages, that regenerates every figure and table in this paper from a fixed seed.",
    ]),
    ("p", "The rest of the paper is organized as follows. Section 2 reviews related work and positions PAER against the closest systems. "
          "Section 3 presents the threat model and the reference architecture. Section 4 describes the evaluation protocol, metrics, "
          "and the six experiments. Section 5 reports results. Section 6 discusses design rules for practitioners, the governance mapping, "
          "and threats to validity. Section 7 states limitations and future work, and Section 8 concludes."),

    ("h1", "2. Background and Related Work"),
    ("h2", "2.1. Retrieval-Augmented Generation in the Enterprise"),
    ("p", "RAG couples a parametric language model with a non-parametric retrieval stage. A query is embedded into a vector space, the "
          "nearest documents are fetched from an index, and the retrieved text is injected into the model context so that answers are "
          "grounded in current, sourceable material {Lewis2020}. The design space has diversified quickly, spanning hybrid sparse and dense "
          "retrieval, reranking, corrective and agentic variants, and graph-based designs for corpus-level reasoning {Gao2023,Fan2024,Edge2024,Wu2026}. "
          "Retrieval quality itself is fragile: relevant, irrelevant, and random documents affect generation differently, and position and "
          "noise can change outputs materially {Cuconasu2024}. In enterprise deployments the architecture becomes a data-integration layer "
          "with a flattened security posture. A single index commonly merges sources that each carry their own IAM semantics, and merging "
          "heterogeneous authorization models produces compliance debt and unintended exposure {Jeong2025}."),
    ("h2", "2.2. Access-Control Models and Enforcement Placement"),
    ("p", "The policy vocabulary comes from three decades of access-control research. Role-based access control (RBAC) attaches permissions "
          "to roles {Sandhu1996}; attribute-based access control (ABAC) evaluates policies over subject, resource, action, and environment "
          "attributes {Hu2015}; zero-trust guidance calls for explicit, least-privilege authorization with continuous verification {Rose2020}. "
          "In a RAG pipeline, authorization can be enforced at source or index segregation, at query time before restricted chunks are ranked "
          "or returned, and again at context assembly. Authentication establishes who the requester is; authorization decides what that "
          "principal may access; retrieval filtering applies that decision to candidate chunks; context validation re-checks the assembled "
          "evidence before generation; output safeguards constrain what the generated answer may disclose. A check at any one layer does not "
          "substitute for the others."),
    ("p", "Where the retrieval-layer check sits has consequences that the database and vector-search communities have studied separately. "
          "Filtered approximate nearest neighbor (ANN) search is an active research area precisely because post-filtering a graph index "
          "degrades recall when the filter is selective, and because per-predicate indexes do not scale {Gollapudi2023,Patel2024}. Espiritu "
          "and Cash analyze post-filtering in relational row-level security and full-text document-level security and show that it leaks "
          "existence through result cardinality and timing, with reconstruction attacks under rich predicates; they recommend pre-filtering "
          "or physical partitioning and note that both carry performance or management costs {Espiritu2026}. Graph indexes with integrated "
          "filter support, such as Filtered-DiskANN and ACORN, aim to make pre-filtering efficient at low selectivity {Gollapudi2023,Patel2024}. "
          "These results have not been carried into the RAG security literature, where post-filtering remains the default retrofit."),
    ("p", "A further subtlety concerns permission freshness. The labels copied into an index are a snapshot of source permissions. "
          "Source-side changes leave the index stale until a reconciliation pass runs, opening a revocation window that retrieval-layer "
          "checks cannot see unless they consult the live policy store."),
    ("h2", "2.3. Permission-Aware RAG Systems"),
    ("p", "Direct permission-aware RAG systems exist and are the closest work to this paper. Jeong and Lee connect retrieval to each "
          "resource provider's native IAM end points so that heterogeneous policies are never merged, and validate a prototype on a "
          "multi-hop question-answering benchmark across resource environments {Jeong2025}. Arceo and Narsing extend multitenant access "
          "control from retrieval to agent tool use and conversation state, report zero cross-tenant leakage under ABAC gating in a synthetic "
          "testbed, and observe recall degradation under post-retrieval filtering as corpus size grows without predicate pushdown {Arceo2026}. "
          "Thuillier et al. encode access permissions into key-parametrized embeddings so that enforcement is carried by the vector space "
          "rather than by a metadata filter {Thuillier2026}. Chen et al. link ingested documents to permitted roles in a permissions store "
          "and check retrieved documents against it before generation in a clinical proof of concept {Chen2025}. Byun et al. route "
          "security-sensitive queries away from external retrieval with a fine-tuned confidentiality classifier {Byun2025}. Jayaraman et al. "
          "address the fine-tuning channel with Permissioned LLMs, which segregate parameters per security domain and define an access "
          "advantage metric for auditing; their formalism extends to RAG in an appendix without a retrieval-layer evaluation {Jayaraman2025}. "
          "Bhatt et al. argue for participant-aware access control and demonstrate exfiltration through the surrounding application even "
          "when retrieval-time filters exist {Bhatt2025}."),
    ("p", "Two community artifacts are also relevant. Nagabathula releases a study on Reuters-21578 with dense retrieval and BM25 that "
          "measures recall loss under post-filtering, an existence oracle through result counts, leakage through shared BM25 statistics, "
          "and leakage through semantic answer caches {Nagabathula2026}. Hussain preregisters a benchmark of permission enforcement across "
          "vector stores and authorization engines, with results pending at the time of writing {Hussain2026}. PAER is complementary to both: "
          "it situates the same enforcement designs inside a reference architecture, adds revocation and context re-check, and measures "
          "side-channel strength as a function of attacker privilege."),
    ("h2", "2.4. RAG Security, Privacy, and Information Leakage"),
    ("p", "Security research on RAG spans ingestion, retrieval, context construction, and generation. PoisonedRAG studies knowledge-corruption "
          "attacks against RAG knowledge bases {Zou2025}; Greshake et al. analyze indirect prompt injection in LLM-integrated applications "
          "{Greshake2023}; HackAPrompt documents prompt-injection behavior at scale {Schulhoff2023}; prompt-extraction work shows that model "
          "outputs can disclose hidden instructions and context {ZhangCarlini2024}. Privacy-oriented research explores differential privacy for "
          "RAG outputs, privacy-aware decoding, and layered output gating {Koga2024,Wang2025,Yang2026}, and Zhang et al. propose a dedicated "
          "evaluation framework for RAG privacy leakage {ZhangWu2026}. Burnat shows that per-account differential privacy understates "
          "leakage when accounts collude against a tenant index {Burnat2026}. Systematizations and surveys organize risks and defenses across "
          "the pipeline {Zhou2024,Arzanipour2025,Mu2026,Ni2026,Bodea2026,Xu2026,Palanisamy2026,Tran2026}. Together these sources justify a "
          "layered threat model and imply two cautions that shape this paper. A retrieval-layer access check by itself does not prevent every "
          "downstream form of leakage, because the model and the surrounding application form additional disclosure channels. And retrieval "
          "provenance, meaning that context records carry known permitted source identifiers, is not the same as claim-level citation accuracy "
          "in generated answers."),
    ("h2", "2.5. Evaluation of RAG: Quality Without Authorization"),
    ("p", "RAGAS provides automated reference-free metrics for RAG {Es2024}; ARES evaluates RAG systems with automated judges {SaadFalcon2024}; "
          "RAGTruth supplies hallucination annotations grounded in retrieved evidence {Niu2024}; BEIR supports heterogeneous zero-shot retrieval "
          "evaluation {Thakur2021}. These resources address quality dimensions orthogonal to authorization. None is designed as a test suite "
          "for enterprise access control, and none reports context starvation, side-channel leakage, or revocation lag."),
    ("h2", "2.6. AI Governance and Standards"),
    ("p", "Governance standards provide a scaffold for accountability. The NIST AI Risk Management Framework organizes risk management around "
          "the Govern, Map, Measure, and Manage functions, and its Generative AI Profile adapts that guidance to generative systems "
          "{Tabassi2023,Autio2024}. The OWASP Top 10 for LLM Applications lists prompt injection and sensitive-information disclosure as its "
          "first two entries {OWASP2024}. ISO/IEC 42001 frames AI management systems, and the EU AI Act imposes documentation and "
          "data-governance obligations within its scope {ISO2023,EU2024}. Recent work in this journal maps adversarial techniques to "
          "architectural layers of generative AI systems and compares governance regimes {Kanabar2026}, proposes incident-response "
          "playbooks for generative AI traced to NIST and OWASP controls {Tuscano2026}, and specifies risk-driven deployment and forensic "
          "readiness for AI-enabled security operations {Torstensson2026}. These materials supply normative context. Alignment with them "
          "does not by itself prove that a technical design is compliant or secure, which is why PAER pairs each governance artifact with a "
          "measurable test."),
    ("h2", "2.7. Positioning"),
    ("p", "Table 1 summarizes what the closest studies measured. Read across rows, they evaluate different constructs under different "
          "workloads: retrieval and answer quality under IAM filtering, cross-tenant leakage in an agentic testbed, access control carried by "
          "embedding geometry, privacy leakage in generated output, or existence leakage in relational and full-text systems. The reviewed "
          "set contains no shared protocol that reports authorization correctness together with authorized retrieval quality, context "
          "starvation, side channels, revocation behavior, and index cost under comparable conditions. PAER proposes such a protocol and "
          "executes its retrieval-layer part. Generation-level properties remain future work, as Section 7 states."),
]
