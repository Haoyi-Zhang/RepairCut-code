# Literature boundary and full-paper calibration

## Screening result

The retained research question is deliberately narrower than browser execution,
transaction processing, or general program repair: it asks how an explicit
observer and the time at which a repair mask is committed change minimum repair
for a private deterministic cached DAG. The comparison supports that bounded
formulation; it does **not** support a universal “first,” “general,” browser-safe,
or performance claim.

The completed calibration is recorded row by row in
`literature-calibration.csv`:

| Required set | Completed | Counting rule |
|---|---:|---|
| Full TPDS papers | 12/12 | Same venue; each paper’s problem, mechanism, proof/performance argument, evaluation, limits, narrative, bibliography scale, and display roles inspected |
| Influential full papers | 5/5 | Canonical methods for optimistic execution, rollback, dataflow, and change propagation; no award status invented |
| Adjacent-venue full papers | 5/5 | Web dependency tracking, symbolic prefetching, safe speculation, QBF debugging, and hyperproperty repair |
| Additional direct/closest comparisons | 7 | CAV 2024 hyperproperty repair, OSDI 2025 Mako, the RCC preprint, Build Systems à la Carte, MRFR, MemoRepair, and dependency-guided rollback; not double-counted above |

The matrix contains 29 unique rows: the required 12+5+5 calibration plus seven non-counted direct/closest comparisons. A paper is counted once in the 12+5+5
calibration even when it is also discussed in the manuscript. Abstract-only
records, search snippets, and venue-rule pages are not counted as full papers.
Third-party PDFs are not redistributed in this repository.

## Closest technical distinctions

### Dependency-directed web execution

**Polaris** records fine-grained object dependencies and schedules page-load
work. Its explicit missing-dependency boundary motivates declaring the modeled
language, but it does not define a repair mask chosen after a prediction is
revealed, an observation projection, or pointwise/adaptive/uniform repair costs.

**Oblique** symbolically explores client/server logic to prefetch resources that
depend on client state. Its symbolic paths, timeouts, native-code boundary, and
page-load evidence concern prediction of future requests. The present model has
no network requests, secrets, browser, page-load latency, or symbolic server
execution.

### Incremental rebuilding and graph-constrained replay

**Build Systems à la Carte** is a materially closer formal comparison than a
generic scheduling paper. It separates task semantics, scheduling, and rebuilding;
states full-store and shallow/target-oriented correctness obligations; and
formalizes minimal rebuilding and early cutoff. The present work does not claim
those ideas. Its remaining delta is a cached mixed execution with an explicit
repair mask, a single input-revelation barrier, terminal versus complete-prefix
observers under identical semantics, and pointwise/adaptive/uniform budget
classification with two tight factor-\(p\) bounds.

Three 2026 preprints sharpen the repair boundary. **MRFR** recovers all
inclusion-minimal singleton/pair event interventions in a declared graph-feasible
replay domain. **MemoRepair** withdraws an invalidated memory cascade and selects
validated predecessor-closed successors through a maximum-closure/min-cut
formulation. **Dependency-Guided Rollback Repair** uses typed provenance,
independent support, and selective replay to recover persistent agent state and
affected actions. They are not treated as peer-reviewed venue publications.
They operate on richer intervention contents, persistent state, provenance and
empirical recovery outcomes; none states the cached-slot observer/commitment
classification or the two tight worst-case ratios proved here. Conversely, this
toy Boolean-DAG work supplies no evidence about their agent workloads or model
behavior.

### Safety, rollback, and transaction systems

**Safe Programmable Speculative Parallelism** already provides operational
safety conditions and distinguishes observations. This prevents claiming that
“observation matters to speculation” is new. Its result is a sufficient static
condition for programmable parallel execution; the present result instead fixes
one cached-prefix semantics and characterizes the repair-choice families after
a single reveal.

**Virtual Time**, optimistic concurrency control, transactional memory, **Mako**,
and **RCC** establish rich rollback, conflict, durability, and concurrency
mechanisms. They are strictly richer systems models. Their use of “bounded” or
“speculative” does not imply the node-cardinality theorems here, while the toy
DAG cannot inherit their deployment or performance claims.

### Diagnosis and repair

Classical diagnosis searches for inconsistent components. **Using QBF to
Increase the Accuracy of SAT-Based Debugging** already uses quantifier order to
require a candidate repair to work across inputs. **Program Repair for
Hyperproperties** and its CAV 2024 syntax-guided extension study multi-trace
requirements and richer transition/program repairs. Therefore quantifier
alternation, QBF encodings, and repair complexity are prior art. The bounded
delta retained here is the combination of:

1. one-pass mixed execution of a cached DAG;
2. terminal versus complete-prefix observation under exactly the same semantics;
3. the principal mismatch-set family exposed by complete-state observation;
4. a sound dependency-descendant baseline with a tight factor-p semantic
   over-repair gap; and
5. a tight factor-p price for committing one repair mask before revelation.

No reviewed paper was found to state that exact package. This is a scoped
literature conclusion, not proof of universal priority; a future reviewer may
identify additional work.

## What the TPDS calibration changed

The twelve TPDS papers were used to calibrate exposition and evidence rather
than to manufacture citations. Recurring patterns carried into the manuscript
are:

- define the systems object and cost model before stating the theorem;
- keep correctness and performance/work cost separate;
- compare a conservative implementable baseline with the semantic optimum;
- make generated-graph scope and failure modes explicit;
- combine formal arguments with deterministic executable checks without calling
  those checks proofs of unbounded theorems; and
- use diagrams and tables to carry mechanism, assumptions, and exact counts.

The calibration also ruled out a false practical narrative. The artifact has no
browser implementation, real site, timing benchmark, distributed service, or
native effect model, so the paper reports a boundary theorem and oracle rather
than page-load or throughput improvement.

## Source and metadata controls

Bibliographic records were reconciled against publisher, DOI, proceedings, or
author-hosted records. In particular, the checkpointing paper is TPDS volume 30,
number 4, pages 897--909 (2019), DOI 10.1109/TPDS.2018.2871135; Chandy--Lamport is
an ACM TOCS journal article, volume 3, number 1, pages 63--75. The main bibliography contains 39 entries, every one cited in the manuscript;
`paper/references.bib` contains no unused calibration-only records.
`reference-verification.csv` records a primary/persistent source, inspection
level, manuscript role, access date, and reconciliation status for all 39. The
four TPDS papers used only for venue calibration remain in the literature matrix
and external-resource ledger but are intentionally absent from the manuscript
bibliography.

The live TPDS author-information page exposed only a dynamic shell in this
environment, while the IEEE template selector front page was reachable but not
its complete interactive selection flow. The package therefore follows the
supplied IEEEtran submission assets and the task’s fixed 12-page contract. This
is recorded as an external-submission rule-recheck hold, not a scientific gap.


## Bibliography separation

The final manuscript has 39 references, all actually cited and each mapped in `reference-verification.csv`. The 12+5+5 calibration requirement is tracked separately from seven extra direct/closest comparisons; calibration-only papers do not enter the bibliography merely to increase its size.
