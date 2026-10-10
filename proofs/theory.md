# Observation and information boundaries of bounded cache repair

## Status and scope

The arguments below are mathematical proofs in prose, not mechanized proofs. The
executable checks validate finite instances and independently implemented Boolean
semantics; they do not establish the unbounded theorems. Computational complexity
uses polynomial many-one reductions and the usual circuit characterizations of
NP, coNP, Sigma_2^P and Pi_2^P. No separation of these classes is assumed.

Complexity statements range over arbitrarily large finite graph encodings. The
implementation's fixed admission caps bound experiments; they do not restrict
the unbounded family in those statements.

This model is a finite, private, deterministic, Boolean, single-assignment DAG.
It is not a semantics of JavaScript, a browser, network requests, mutable DOMs,
irrevocable effects, concurrency races, failures of physical machines, or timing
side channels. Its application is an explicit boundary for a buffered stage of
an execution graph, not an implementation of a web optimizer.

## 1. Operational definitions

An instance contains a finite list of Boolean inputs, each with domain {0}, {1},
or {0,1}, a Boolean prediction for each input, and a topologically ordered list
of named gates. The primitives are constants, COPY, NOT, AND, OR and XOR with
fan-in at most two. Names are single assignment. The graph is syntactically
dependency-complete: its declared edges are exactly all gate operand edges. This
is a checkable property of the declared language, not an inference about effects
outside that language. A speculative prefix P has p gates. A fresh suffix follows
P in the topological order. The observer O is a nonempty tuple of named inputs
or gate outputs. An environment theta assigns admissible actual values to inputs.
There are q independently varying Boolean inputs and 2^q legal environments.

First evaluate the prefix at the prediction, retaining a value c_v for each v in
P. At one barrier the complete actual environment is revealed. Choose a repair
set R contained in P. Traverse the graph once in its original topological order:
for an unselected prefix gate keep c_v, for a selected prefix gate evaluate its
primitive on the current values of its operands, and always evaluate suffix
gates. The resulting observation is Mix(theta,R). Ref(theta) is the observation
from evaluating every gate afresh on theta. All intermediate values remain
private; the observation tuple is emitted atomically only at the end. Repair
cost is |R|, not execution time. In particular the cost does not include suffix
work, computing a reference, validation, finding R, or publication.

Write G(theta,R) for Mix(theta,R)=Ref(theta), and

  C(theta) = min {|R| : G(theta,R)},
  A = max_theta C(theta),
  U = min {|R| : for every theta, G(theta,R)}.

A is adaptive: the repair may depend on the complete revealed environment. U
is uniform: one repair set is fixed before any environment is revealed. Full
repair P succeeds by a direct topological induction, so all minima exist and
0 <= A <= U <= p. If A=0, the sole cost-zero choice is the empty set, which then
works for all environments, and U=0. The decision questions compare these costs
with a nonnegative integer k. Values k>=p are trivial yes instances.

No compact representation or polynomial-time synthesis of an adaptive policy is
assumed. A table of one repair per environment can have exponentially many rows.

## 2. Terminal observation: an operational quantified-circuit realization

### Main Lemma 1 (budget selection and escape)

Let F(u,x) be an arbitrary Boolean circuit, where u has q bits and x has m>=1
bits. A graph of polynomial size can be constructed with p=3m+1 speculative
gates, all COPY, one terminal observation bit, one uncertain input d used by
the prefix, prediction d=0, and budget k=m, such that:

* for d=0 every repair succeeds;
* for d=1, a repair of cost at most m succeeds exactly when it selects one gate
  of each pair (t_i,f_i), no escape gate, and the assignment x_i=1 iff t_i is
  selected satisfies F(u,x).

Moreover its successful repair sets are upward closed for each environment.

**Construction.** For each i, create speculative t_i=COPY(d) and f_i=COPY(d).
Create an escape chain e_1=COPY(d), e_j=COPY(e_{j-1}) for 2<=j<=m+1. Every prefix
cache is zero. These gates form a tree when the common input root d is included;
this is a restriction on the speculative prefix, NOT on the entire graph.

Translate F to a dual-rail circuit F+ over u, NOT(u), t and f. For each gate of F,
keep a positive and a negative rail. Negation swaps rails; an AND uses AND on
positive rails and OR on negative rails; an OR uses OR on positive rails and
AND on negative rails. Constants have complementary constant rails. The inputs
x_i have rails t_i and f_i. Other Boolean gates can first be expanded into this
basis with constant overhead. This gives linear overhead in the original
circuit size and is monotone in the t and f rails. When f_i=NOT(t_i) for every i,
its positive output F+ equals F(u,t), by induction on F's gates. Universal input
negations are fresh gates, not speculative gates. Define fresh gates

  H = AND_i (t_i OR f_i),
  y = e_(m+1) OR (H AND F+).

Observe only y. All fan-ins can be reduced to two by trees.

**Proof.** If d=0, every copy evaluates to zero whether repaired or cached. The
escape and H are zero, so both mixed and reference outputs are zero. If d=1,
full reference execution sets the whole escape chain to one, giving Ref=1.
The mixed escape output is one iff every escape gate is selected: an omitted
copy retains zero and all later copies can propagate only that zero. Its length
m+1 excludes this option under budget m. Therefore success under that budget
requires H=1 and F+=1. Each conjunct of H requires one of its two independent
COPY gates to be selected. The m pairs exhaust the entire budget. Exactly one
per pair is therefore selected, with none left for the chain. The rails encode
a Boolean assignment and F+=F. Conversely any satisfying x yields exactly this
successful m-gate repair.

For d=1, enlarging a repair can only increase every prefix value: independent
copies are monotone in their selection bits, and each escape output is the AND
of its preceding selection bits. The fresh output is monotone in prefix values
because F+ and H are. Ref=1, so success is upward closed. For d=0 every repair
succeeds. Thus the asserted monotonicity holds in both cases. QED.

**Exact costs for validation.** When d=1, coverage needs at least m selections,
and selecting the escape chain succeeds for every u at cost m+1. Hence C(d=1,u)
is m when some x satisfies F(u,x), and m+1 otherwise; C(d=0,u)=0. It follows that
A is m iff forall u exists x F(u,x), and U is m iff exists x forall u F(u,x).
When the corresponding condition is false, the cost is m+1. These exact values
are properties of this gadget, not of arbitrary graphs.

**Why the escape is necessary.** Full repair agrees with reference by topological
induction, with or without the escape. The escape fixes the reference output at
one for d=1 and supplies an unconditional repair of cost m+1, above budget m.
Without it, a false F could make the reference output zero and admit cheap
repairs, destroying the reduction equivalence rather than the full-repair
invariant. A chain of m rather than m+1 would be affordable, accepting even a
false F. The negative-control test makes precisely that one-gate mutation.

### Main Theorem 4 (terminal-observer complexity)

The pointwise question C(theta)<=k is NP-complete. The adaptive question A<=k
is Pi_2^P-complete. The uniform question U<=k is Sigma_2^P-complete. Hardness
holds with the restrictions and upward-closed successful repair families of
Main Lemma 1.

**Membership.** Given theta and a p-bit selection mask, caching, the mixed
execution, reference execution, and observation equality take time polynomial
in the graph encoding. Guessing a mask proves pointwise NP membership. The
adaptive decision is exactly forall theta exists R: |R|<=k and G(theta,R).
The uniform decision is exactly exists R forall theta: |R|<=k and G(theta,R).
Domains of fixed inputs can be substituted out. These are the circuit
characterizations of the respective second-level classes.

**Hardness.** For the pointwise case, start with circuit SAT F(x), take no u,
and fix the evaluated environment to d=1. Main Lemma 1 is a polynomial reduction.
For the adaptive case start with a quantified circuit forall u exists x F(u,x).
The new universal d=0 branch is automatically true. Its d=1 branch is equivalent
to the original quantified circuit by the lemma. For uniform repair start with
exists x forall u F(u,x). A single mask of cost <=m must choose the same rail in
every pair for every u, so it is exactly one outer existential assignment. Again
d=0 imposes no constraint. The arbitrary circuit formulation avoids assuming
that an inappropriate CNF restriction preserves a quantified hardness result.
An unused existential bit can ensure m>=1 without changing truth. QED.

The quantifier pattern and quantified-circuit hardness sources are established
complexity machinery, not a new theorem about quantifiers. The specific content
here is its realization with this repair semantics, monotone repair feasibility,
a COPY-only tree prefix, and the comparison with complete-state observation below.

## 3. Complete-state observation removes existential repair choice

The observer is complete-state when it includes every prefix slot, possibly
along with any suffix outputs. Let f_v(theta) denote the all-fresh reference
value of prefix gate v, and let

  M(theta) = {v in P : c_v != f_v(theta)}.

### Main Theorem 1 (unique least repair)

For complete-state observation, G(theta,R) iff M(theta) is contained in R.
Consequently M(theta) is the unique least successful repair by inclusion,
C(theta)=|M(theta)|, A=max_theta |M(theta)|, and
U=|union_theta M(theta)|. The union is the unique least uniform repair.

**Necessity.** An omitted v in M retains c_v and is directly observed. Its
reference value differs, so the observation cannot match.

**Sufficiency.** Traverse prefix gates in topological order. Every input already
has its reference value theta. At an unselected v, membership M subset R implies
c_v=f_v. At a selected v, every operand has its reference value by induction, so
re-evaluating the deterministic primitive gives f_v. Thus all prefix slots agree
with reference. The fresh suffix then also agrees by induction. This proves
success for any superset of M, including M itself. The formulas follow by
minimizing a cardinality over these principal upward-closed families. For a
uniform mask, containing every M is equivalent to containing their union. QED.

The induction does not require repairing every syntactic descendant of a changed
input. Some such descendants already have their reference value. Conversely it
does not require that a selected gate's stale inputs would have sufficed: the
induction uses the reference correctness of ALL earlier slots once M is selected.

### Main Theorem 2 (complete-state decision complexity)

The pointwise decision is in P (one prediction/reference comparison pass).
Both A<=k and U<=k are coNP-complete for complete-state observation.

**Membership.** Failure of A<=k has a polynomial certificate: an environment
with more than k mismatches. Failure of U<=k has a polynomial certificate of
k+1 distinct prefix nodes, each accompanied by an environment witnessing that
node's mismatch. There are at most p such nodes, so this certificate has
polynomial size. Different nodes may need different environments. These
certificates and Main Theorem 1 put both decisions in coNP.

**Uniform hardness.** Reduce UNSAT of a Boolean formula F(u). Construct a fully
speculative Boolean circuit for F and z=d AND F. Let N be its number of gates,
including z. Add W=N+1 speculative COPY children of z and observe all gates.
Predict d=0 (the predicted u is arbitrary and valid), so all children cache
zero. Take k=N. If F is unsatisfiable, no child changes in any environment; the
mismatch union is contained in the N base gates and U<=k. If F is satisfiable,
choose d=1 and a satisfying u. Every one of the W children differs, so U>=W>k.
The construction has polynomial size. QED for uniform hardness.

**Adaptive hardness.** Reduce UNSAT of a CNF F with s>=1 clauses. Compute each
clause C_i in the speculative prefix and z_i=d AND C_i. Let N count all these
base gates. For every z_i add W=N+1 speculative COPY children. Observe every
gate, predict d=0, and set k=Ws-1. If F is satisfiable, d=1 at a satisfying u
changes all Ws children, so A>k. If F is unsatisfiable, at most s-1 clauses can
be true in any environment. For d=1 at most W(s-1) children change, plus at most
N base gates. Their total is W(s-1)+N=Ws-1=k. For d=0 no children change. Thus
A<=k exactly for unsatisfiable F. The number of children is O(sN), polynomial
in the formula size. CNF instances with no clauses can be handled separately;
the nonempty subclass already gives UNSAT hardness. QED.

### Main Theorem 3 (observation refinement)

Let two instances share the same graph, cache, environment domain, and repair
semantics, and let observer O_1 be a subsequence of observer O_2. Every repair
successful for O_2 is successful for O_1. Consequently, for every environment,
C_1(theta)<=C_2(theta), A_1<=A_2, and U_1<=U_2.

**Proof.** Equality of the longer observation tuples implies equality after
projection onto O_1. Thus the successful-repair family under O_2 is a subset of
the family under O_1. Taking minima at a fixed environment, then maxima, preserves
the pointwise inequality; minimizing over uniform repairs preserves it as well. QED.

A stronger observer can therefore require more repair while simplifying its
choice structure. Terminal observation has the NP/Pi_2^P/Sigma_2^P classifications
of Main Theorem 4, whereas complete-state observation has the P/coNP classifications
of Main Theorem 2. This juxtaposition does not assert a strict separation between
complexity classes: it says that a monotone increase in the semantic obligation
does not imply a monotone increase in the complexity class of the corresponding
decision problem. The complete-state formula still has exponential environment
enumeration in the supplied general exact implementation.

## 4. Conservative dependency invalidation

For an environment theta, let Delta(theta) be the inputs whose revealed values
differ from their predictions. Let D(theta) be the cached prefix nodes reachable
from Delta(theta) by declared operand edges. This is the standard syntactic
invalidity rule that discards every cached descendant of changed data.

### Main Theorem 5 (soundness and tight over-repair of descendant invalidation)

Repairing D(theta) succeeds for every observer in the declared pure DAG model.
Under complete-state observation, M(theta) is a subset of D(theta). If
C(theta)>0, the policy is a p-approximation, and the factor p is tight. No finite
multiplicative guarantee is possible when C(theta)=0.

**Soundness.** Traverse the cached prefix in topological order. A node outside
D has no changed input ancestor. Induction on its operands therefore shows that
its cached value equals its fresh reference value, so retaining it is safe. A
node in D is selected. Every one of its inputs is an actual input, a retained
clean slot already equal to reference, or an earlier selected slot re-evaluated
to reference. Determinism therefore makes the selected node equal to reference.
Every prefix slot is now correct, and the fresh suffix and any projected observer
are correct by the same induction. For complete-state observation, Main Theorem 1's
necessity immediately gives M subset D.

**Approximation and tightness.** The policy selects at most p nodes, while a
positive optimum selects at least one, so its ratio is at most p. For every p,
use one uncertain input d predicted zero and p independent cached nodes. Let
s_1=COPY(d), and for 2<=i<=p let s_i=XOR(d,d). Observe every cached slot. When
d=1, every s_i is a declared descendant of d, so descendant invalidation selects
all p nodes. Only s_1 changes value; Main Theorem 1 gives C=1. Hence the ratio is p.
If all p nodes instead compute XOR(d,d), the optimum is zero while the policy
still selects p, which rules out a multiplicative bound at zero optimum. QED.

The tight family uses dependency-complete graphs; the inefficiency is semantic
cancellation rather than a missing edge. Thus exact dependency tracking alone
establishes safety of invalidation, not work optimality.

## 5. The maximum price of fixing repairs before revelation

### Main Theorem 6 (tight p-fold gap)

For p>=1 the largest possible ratio U/A among instances with A>0 is p. It is
attained with a COPY-only star prefix and a monotone one-bit terminal observer.

**Construction and proof.** Let s_i=COPY(d), 1<=i<=p, predicted d=0. Let u contain
p independent selector bits, all revealed with d. Observe

  y = OR_i (u_i AND s_i).

Reference output is d AND OR_i u_i. Write J(u)={s_i : u_i=1}. For theta=(d,u),
the exact successful family is

  S_theta = 2^P,                                      if d=0 or J(u)=empty;
  S_theta = {R subseteq P : R intersects J(u)},       if d=1 and J(u) nonempty.

In the first branch both mixed and reference output are zero for every repair.
In the second, the reference is one and the mixed output is one exactly when a
repaired active slot contributes one. Thus every nonzero selector has a one-slot
adaptive repair and some repair is necessary, so A=1. Each nonzero unit-vector
environment forces its corresponding slot. Over the full domain, intersecting
those successful families leaves only P, so U=p. For a restricted legal domain
E', the uniform-success family is exactly intersection_{theta in E'} S_theta;
equivalently its members are the hitting sets of the nonempty J(u) that occur
with d=1. The upper bound follows from U<=p and A>=1. If A=0 then U=0, so division
by zero is not a gap example. QED.

## 6. Composition requires shared-input cost profiles

Suppose components have pairwise disjoint speculative slots and private gates,
no cross-component gate operands, and their outputs are observed separately.
They may share read-only uncertain inputs. Cost is additive over their disjoint
repair sets. For a legal joint environment theta, theta_i is its restriction to
component i. Component domains are exactly the projections of legal joint
environments, rather than supersets that introduce impossible inputs.

### Main Theorem 7 (composition)

  C_joint(theta) = sum_i C_i(theta_i),
  U_joint = sum_i U_i,
  A_joint = max_theta sum_i C_i(theta_i) <= sum_i A_i.

If component environment domains are independent and their joint domain is the
Cartesian product, the last inequality is equality.

**Proof.** Mixed and reference observations factor by component. At a fixed
joint environment, a repair succeeds iff every component restriction succeeds.
Minimizing additive costs of independent repair choices gives the first formula.
A uniform joint repair succeeds iff each component restriction succeeds on every
environment in its projected domain: all of those environments occur in some
legal joint environment. Its independent mask choices and additive cost give
the second formula. Maximizing the first formula gives the third, with the
inequality following termwise. For independent domains a maximizing environment
of every component can occur together, giving equality. QED.

**Counterexample to adding adaptive scalar maxima.** Two components have prefix
slots a=COPY(d), b=COPY(d), both cached zero. They share d,u and observe respectively
u AND a and NOT(u) AND b. Each component alone has adaptive cost one. For every
joint environment at most one component needs repair, so A_joint=1 rather than
2. A uniform mask needs both nodes, giving U_joint=2. Retaining a cost profile
indexed by the shared inputs, rather than only its maximum, is necessary here.

## 7. Nonmonotonicity is possible but is not the source of Main Theorem 4

In a different construction use H=XOR(t,f), two cached-zero COPY(d) selectors,
an escape chain of length two, and output escape OR H. At d=1, both {t} and {f}
succeed, but their union {t,f} fails; repairing the full prefix succeeds. At d=0,
every mask succeeds. Thus each singleton is a successful adaptive policy over
the domain, while their union is not uniform. Success is not generally upward
closed. This
example is separate from the monotone construction in Main Lemma 1: the hardness and
tight adaptive/uniform gap do not depend on nonmonotonic repair behavior.

## 8. Executable certificates and finite verification obligations

Each explicit JSON row stores exactly environment, selected, cache, trace, and
output. The verifier replays the selected mixed execution and compares the stored
cache, complete mixed trace, and output with that replay. It recomputes the
reference output instead of accepting a stored reference field, and requires the
replayed output to equal that reference. An adaptive certificate contains one
row for every legal environment; a uniform certificate additionally uses one
identical selection set in all rows. Such domain enumeration is exponential in
q. Checking a supplied exponentially long certificate is not a compact proof of
the general quantified decision problem, and a successful trace does not by
itself establish minimality.

The artifact checks exact declared operand edges, graph schema, finite tables,
Boolean gates, and all explicitly enumerated environments. It cannot check that
an imported native operation has no unmodeled effects, and it has no native
operation primitive. Missing-edge cases are controlled schema mutations of owned
toy graphs, not discoveries of hidden dependencies on websites. The semantics
contains no outgoing communication and no exploit-oriented testing.

The independent replay implementation does not call the bit evaluator's gate
semantics. It shares the data schema only. Their agreement is useful engineering
evidence, not an independent scientific review. Complete-state characterization,
quantified-relation oracles, monotonic lattice edges, and the escape off-by-one
control attack different potential mistakes in the reductions. None is a
substitute for the proofs above.
