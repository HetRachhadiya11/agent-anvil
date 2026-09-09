# Agent Anvil optional empirical-validation protocol

This protocol is not required to reproduce the software-verification claims in
the SoftwareX article. It freezes a future provider-backed empirical study
before genuine model runs and prevents the benchmark or assertions from being
changed after inspecting model failures.

## 1. Research questions

1. How often does a minimal response-only check accept a run that violates a
   trace or environment-state requirement?
2. What is the incremental detection contribution of each deterministic check
   family?
3. How do response-only, state-only, trace-only, and hybrid views disagree on
   the same executions?
4. What false-positive rate do trace assertions have against independent human
   labels, including valid alternative tool sequences?
5. If a semantic judge is added, what are its agreement, variance, cost, and
   incremental detections beyond deterministic checks?

## 2. Frozen benchmark

- Dataset: `scenarios/benchmark_v1.yaml`
- Size: 100 scenarios, exactly 20 in each of five suites.
- Units: scenario-by-model-by-repetition executions.
- Ground truth: scenario policies and permitted state transitions, not failures
  deliberately injected into an agent.
- Before the first model run, create a tagged release and record the SHA-256 of
  the scenario file. Do not modify version 1 after observing results.

The benchmark contains both positive and negative requests. In negative cases,
a correct agent may refuse or ask for clarification; the assertions constrain
unsafe actions and state changes without requiring one exact wording.

## 3. Agents and repetitions

Minimum design:

- three named model configurations, preferably from at least two providers;
- three independent repetitions per model and scenario (900 runs total);
- identical prompts, tools, states, maximum steps, and evaluator versions;
- record provider, exact model snapshot/identifier, execution date, SDK version,
  decoding parameters, maximum steps, and retry policy.

The model agent—not a deterministic demo program—must select tools and produce
arguments. Provider errors should be retained as protocol failures and reported
separately from behavioral failures.

## 4. Paired baselines

Evaluate every stored run without rerunning the agent:

- response-only existence/error-marker check;
- environment-state assertions;
- deterministic trace assertions;
- hybrid response + state + trace evaluation;
- one independently prompted final-response LLM judge, if budget permits.

Report the complete 2x2 paired disagreement table for each comparison. Use an
exact paired McNemar/sign test for discordant pairs. For interval estimates over
stochastic executions, bootstrap by scenario (not by individual event) and show
model-specific results. Do not attach Wilson intervals to the fixed benchmark as
if the scenarios were a random population sample.

## 5. Per-check ablation

For every check family, report:

- total failed runs;
- runs uniquely failed by that check;
- incremental failures when the check is added to a declared ordering;
- overlap with every other family;
- human-confirmed true positives and false positives.

Policy preconditions are one deterministic check family. They must not be
presented as a separate layer if they were already enabled in an earlier row.

## 6. Independent annotation

Draw a stratified blinded sample containing:

- all response-pass/hybrid-fail disagreements up to 150 runs;
- at least 30 hybrid-pass runs;
- at least 20 runs containing non-canonical but potentially valid sequences;
- representation from every model and suite.

Two annotators independently label final-response correctness, final-state
correctness, trace-policy correctness, and validity of alternative sequences.
They must not see Agent Anvil's pass/fail result during initial annotation.
Report raw agreement and Cohen's kappa per dimension, then adjudicate conflicts.
Against adjudicated labels, report precision, recall, specificity, and false-
positive rate for each evaluator view and check family.

## 7. Semantic-grader validation

Semantic grading is optional and must remain excluded from headline claims until
validated. If enabled:

- freeze grader prompt and exact judge model;
- run each sampled trace three times;
- report agreement with adjudicated human labels and within-trace variance;
- report token usage, monetary cost, and latency;
- report incremental detections beyond deterministic checks.

## 8. Diagnostic grouping

The built-in grouping key is deterministic: assertion ID, suite, normalized tool
name, and argument/state key. Do not call this machine-learned clustering.
Evaluate grouping purity against the adjudicated failure taxonomy and report the
number of mixed-label groups.

## 9. Security evaluation

Seed synthetic credentials, bearer tokens, passwords, and personal-data fields
into a dedicated security test set. Verify that raw secret strings do not appear
in persisted JSON, JSONL, CSV, or Markdown artifacts. Verify owner-only file
permissions on POSIX systems. Document residual risks, retention, and access-
control responsibilities.

## 10. Required release artifacts

- source repository and immutable release tag;
- OSI-approved license;
- versioned schemas and 100-scenario benchmark;
- dependency lock or environment file;
- raw redacted traces and result files;
- analysis code and generated tables/figures;
- annotation codebook, de-identified labels, and adjudication record;
- exact reproduce commands and checksums.

## 11. Stop conditions for empirical claims

Do not publish model-performance, hidden-failure-rate, semantic-grader, or human-
agreement results if the corresponding runs or labels are missing, model
identifiers are absent, or any result was manually invented. Report unavailable
analyses as limitations rather than filling tables with assumptions. These stop
conditions do not prevent release of the software article, whose claims are
limited to the executed implementation checks.
