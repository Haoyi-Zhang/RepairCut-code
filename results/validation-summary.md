# Deterministic validation summary

All seven suites and all thirteen unit tests pass. The checks are finite
implementation evidence, not a representative workload study, a formal proof
assistant, or independent peer review.

## Reconciled counts and meanings

| Suite | Exact retained obligation |
|---|---|
| Relations | 1,056 graph views; 2,048 success-predicate replay pairs in the designated small family; 526,336 environment/repair-extension monotonicity edges |
| Complete-state padding | 510 graphs; 4,080 mismatch-repair replay rows; direct UNSAT-threshold oracle |
| Translated circuits | 128 graphs; 40,960 success-predicate replay pairs; seed 1729 |
| General DAGs | 256 observer-specific graph views; 32,768 success-predicate replay pairs; seed 65537 |
| Adaptive/uniform gaps | 8 tight sizes; every environment and mask at p=1,2,3 (168 pairs); shared-input composition has joint A=1, separate maxima sum=2, U=2 |
| Baselines | 12 tight invalidation sizes; 128 random DAGs; 2,072 soundness rows; 1,024 refinement rows; seed 104729 |
| Negative controls | 24/24 intended faults detected |

The independent implementation total is
2,048 + 40,960 + 32,768 = **75,776**. Each comparison concerns the Boolean
success predicate for one mask/environment pair. It is not a claim that the two
implementations store identical internal traces. Padding, monotonicity, and the
direct relation threshold oracle are separate obligations and are not folded
into that total.

For the gap construction, exhaustive checks at p=1,2,3 confirm the exact
piecewise family: every repair succeeds when d=0 or the selector vector is all
zero; otherwise success requires the repair to hit an active slot. The full
range p=1,...,8 retains A=1 and U=p, and every nonzero unit-vector environment
forces its corresponding slot.

## Baseline distribution and ratios

For the 128 fixed-seed random complete-state DAGs, descendant invalidation is
strictly larger than the semantic optimum in 53 cases and equal in 75. There are
120 positive-optimum cases. Their maximum ratio is 4 and their exact mean ratio
is 187/144 = 1.2986111111111112. Eight cases have zero optimum; five also have
zero syntactic cost and three have positive syntactic cost. Every zero
denominator is recorded as `undefined`, not as zero.

The two retained cost columns determine these ratios directly. Their values and
the Table IV frequencies are:

| Pair | Count |
|---|---:|
| (0, 0) | 5 |
| (1, 1) | 20 |
| (2, 0) | 2 |
| (2, 1) | 10 |
| (2, 2) | 17 |
| (3, 0) | 1 |
| (3, 1) | 3 |
| (3, 2) | 17 |
| (3, 3) | 21 |
| (4, 1) | 1 |
| (4, 2) | 3 |
| (4, 3) | 16 |
| (4, 4) | 12 |

Mean syntactic and semantic costs over all 128 graphs are 2.59375 and
2.0859375. These deterministic values describe the retained generator output;
they are not estimates of an application distribution.

## Certificate boundary

Each certificate row stores exactly `environment`, `selected`, `cache`, `trace`,
and `output`. The verifier replays the mixed execution and compares the stored
cache, trace, and output with that replay. It recomputes the reference output
itself and checks equality; no reference-output field is stored.

## Resource observations

The retained original seven-suite record reports 5.275391517 CPU seconds and
5.290027825999914 wall seconds in aggregate, with maximum child-reported RSS of
94,508 KiB. The circuits suite accounts for 2.74431932 CPU seconds. These values
come from the retained suite JSON and `cpu-accounting.json` and describe that
specific run only.

A clean-extraction reproduction records its own parent/child timing and memory.
It is a separate run. Neither timing record is an equality target for the other
or for another platform; equality is defined by scientific CSV rows and declared
counts. Each child uses one CPU with the documented virtual-address-space,
CPU-time, wall-time, and row-admission guards.

## Controls and interpretation

The 24 negative controls cover graph schema, certificate canonicality and domain
coverage, trace/cache/output mutation, non-prefix repair, unsupported effects,
cycle/topology violations, the escape-chain off-by-one error, adaptive/uniform
quantifier swapping, and an unsafe union-of-adaptive-masks shortcut. They are
owned benign toy mutations, not offensive testing.

A passing campaign shows that the delivered implementation satisfies the listed
finite obligations under the documented interpreter. It does not show browser
correctness, representative performance, or the truth of the unbounded prose
proofs by itself.
