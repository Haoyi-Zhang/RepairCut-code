# Bounded repair of speculative DAGs: reproducible artifact

## Scope

This standalone repository implements the model studied in **Observation and
Commitment Boundaries in Bounded Repair of Speculative DAGs**: a private,
deterministic Boolean single-assignment DAG with a cached prefix, one complete
input-revelation barrier, one topological repair pass, and atomic observation.
Repair cost is the number of selected cached nodes.

It contains:

- complete prose proofs in `proofs/theory.md`;
- an exact bit-vector evaluator and a separately implemented trace replay;
- graph constructors for quantified reductions, complete-state padding, tight
  gaps, composition, and descendant invalidation;
- explicit adaptive/uniform certificates containing pointwise replay rows, and a verifier;
- seven deterministic validation suites, fifteen unit tests, and 24 negative
  controls;
- raw CSV/JSON results, a claim-evidence ledger, a 12+5+5 full-paper
  calibration plus seven direct/closest comparisons, and a row-level verification
  table for every cited reference.

It does **not** implement a browser, JavaScript, a network, mutable state,
concurrency, failures, native effects, a scheduler, or a performance optimizer.
The proofs are mathematical prose, not a proof-assistant development. Finite
checks are bounded implementation evidence, not general proofs or workload data.

## One-command clean reproduction

Use Python 3.10 or newer on Linux. No pip package, dataset, network access, GPU,
model API, credential, or parent project directory is required.

```sh
python reproduce.py --output /tmp/speculation-reproduction
```

The output directory must not exist. The runner executes unit tests and all
seven suites in separate one-worker child processes, then compares every
regenerated CSV row and every declared scientific count with `results/validation/`.
Timing and memory observations are reported but are not equality targets.
Each child attempt retains its command, exit/timeout result, stdout, and stderr;
nonzero exits, timeouts, CSV mismatches, and count mismatches remain failures.
The standalone repository's scientific workflow runs this command from the flat
artifact root on Ubuntu 24.04, with a 300-second whole-command timeout and
always-uploaded raw outputs. Source syntax checks remain a separate check.

## Individual commands

```sh
python -m unittest discover -s tests -v
python -m speculation.validate relations --output /tmp/speculation-relations
python -m speculation.validate padding --output /tmp/speculation-padding
python -m speculation.validate circuits --output /tmp/speculation-circuits
python -m speculation.validate general --output /tmp/speculation-general
python -m speculation.validate gaps --output /tmp/speculation-gaps
python -m speculation.validate baselines --output /tmp/speculation-baselines
python -m speculation.validate negatives --output /tmp/speculation-negatives
```

The graph/certificate interface can be exercised independently:

```sh
python -m speculation analyze cases/active-input-gap.json
python -m speculation verify cases/active-input-gap.json cases/active-input-gap-certificate.json
python -m speculation certify cases/active-input-gap.json --mode uniform --output /tmp/speculation-certificate.json
python -m speculation verify cases/active-input-gap.json /tmp/speculation-certificate.json
```

Generated directories and certificates must not already exist.

Certificate rows contain exactly `environment`, `selected`, `cache`, `trace`, and
`output`. Verification replays those fields and recomputes the reference output;
there is no stored reference-output field.

## Recorded campaign

| Evidence family | Retained count |
|---|---:|
| Relation graph views | 1,056 |
| Complete-state padding graphs | 510 |
| Translated random circuits | 128 |
| General-DAG observer views | 256 |
| Independent success-predicate comparisons | 75,776 |
| Monotonicity environment/extension edges | 526,336 |
| Descendant-invalidation soundness rows | 2,072 |
| Observation-refinement environment rows | 1,024 |
| Fixed-seed random baseline DAGs | 128 |
| Tight invalidation instances | 12 |
| Adaptive/uniform gap instances | 8 |
| Exhaustive gap-family mask/environment pairs (p=1,2,3) | 168 |
| Negative controls detected | 24/24 |
| Original campaign unit tests | 13 |

The current test suite has 15 tests. Two added regressions require the relation
and circuit oracles to reject incorrect zero-cost reports that preserve budget
thresholds. These oracles now check exact pointwise, adaptive, and uniform costs:
zero on the `d=0` branch and `m` or `m+1` on the `d=1` branch, with the escape
giving the latter upper bound. The retained seven-suite CSVs and scientific counts
are unchanged. A bounded Windows-adapted local rerun matched them and passed all
15 tests; it is separate from the historical Linux resource measurements and
does not establish native Linux reproduction of the edited sources.

Reference provenance is separate from scientific result counts.
`reference-verification.csv` covers all 39 manuscript citations;
`literature-calibration.csv` contains 29 full-paper rows (12 TPDS, five
influential, five adjacent, and seven non-counted direct/closest comparisons),
and `external_resources.csv` records all scholarly and workflow inputs.

The random-baseline distribution is retained in `results/validation/baselines.csv`.
The syntactic and semantic cost columns yield 53 strict gaps, 120 positive
optima, maximum positive ratio 4, and exact positive-ratio mean 187/144. A
positive optimum uses `syntactic_cost / optimal_cost`; a zero optimum is marked
`undefined`, including the three positive-invalidation/zero-optimum cases. The
Table IV cost frequencies are asserted by the validation code.

## Resource guards

Each suite runs in one child process with one CPU, a 3 GiB virtual-address cap,
35 CPU seconds, and a 40-second wall timeout. The exact evaluator rejects cases
above 2^25 environment/repair rows or a conservative 2 GiB bit-vector payload.
A timeout or admission rejection is a failure, never a scientific answer.

The retained original seven-suite record reports 5.275391517 CPU seconds,
5.290027825999914 wall seconds, and 94,508 KiB maximum child RSS; the circuits
suite reports 2.74431932 CPU seconds. Clean reproduction has a separate timing
record. Scientific equality uses CSV rows and declared counts, not timing or RSS.

## Evidence map

- `claim_evidence_ledger.csv`: each manuscript claim mapped to proof/checker,
  family, display, raw result, maturity, recheck, and limitation.
- `literature-calibration.csv`: 12 TPDS + 5 influential + 5 adjacent full-paper
  calibration rows, plus seven non-counted direct/closest comparisons.
- `external_resources.csv`: exact scholarly/official source records and
  integration boundaries.
- `results/validation-summary.md`: definitions and reconciled counts.
- `results/clean-reproduction.json`: historical clean-extraction outcome.

The artifact is self-contained and redistributes no third-party research PDF or
external code. License terms for the repository are in `LICENSE`; source notices
are in `licenses/THIRD-PARTY-NOTICES.md`.
