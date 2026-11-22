# Agent Anvil architecture

Agent Anvil separates the scenario contract, agent execution, trace recording
and evaluation. This makes it possible to score the same execution in several
ways while preserving the events and state used to reach each result.

## Execution flow

1. The CLI loads a YAML scenario set and validates each scenario.
2. For each run, the runner creates a fresh local tool environment and recorder.
3. An adapter executes the scenario against that environment and records
   observable events.
4. The recorder finalises the trace with the resulting environment state.
5. The evaluator checks the trace and state against the scenario assertions.
6. The reporting layer writes per-run results, summaries and grouped failures.
   The CLI also writes a run manifest and applies the requested CI gate.

An execution error is recorded as a protocol error. The default runner still
finalises the trace so the failed run can be examined.

## Module map

| Module | Responsibility |
| --- | --- |
| [`models.py`](../agent_anvil/models.py) | Versioned scenario, trace and event models |
| [`loader.py`](../agent_anvil/loader.py) | YAML loading, model validation and unique scenario IDs |
| [`environment.py`](../agent_anvil/environment.py) | Stateful local tools and observable side effects |
| [`adapters/`](../agent_anvil/adapters/) | Scripted execution and optional provider integration |
| [`recorder.py`](../agent_anvil/recorder.py) | Event recording and trace persistence |
| [`runner.py`](../agent_anvil/runner.py) | Isolated scenario execution and evaluation orchestration |
| [`evaluator.py`](../agent_anvil/evaluator.py) | Assertions and the four paired evaluation views |
| [`reporting.py`](../agent_anvil/reporting.py) | JSON, CSV and Markdown reports and failure grouping |
| [`cli.py`](../agent_anvil/cli.py) | Validation, run configuration, manifests and exit codes |
| [`redaction.py`](../agent_anvil/redaction.py) | Recursive redaction of common sensitive patterns |

## Contracts and outputs

The JSON Schemas in [`agent_anvil/schemas/`](../agent_anvil/schemas/) describe
`anvil.scenario.v1` and `anvil.trace.v1`. The scenario defines the initial
state, available tools and assertions; the trace preserves the observable
events and final state from an execution.

The four evaluation views are response-only, environment-state, trace-only
and hybrid. Each view uses the same execution, so comparisons are paired.
The response-only view is a basic response-presence/runtime-error check;
it is not a general measure of answer quality. An optional model judge is
recorded separately.

## Extension points

- Add a new adapter by implementing the contract in
  [`adapters/base.py`](../agent_anvil/adapters/base.py).
- Add scenario coverage in the benchmark generator and validate the generated
  YAML. Keep intentional changes to research benchmarks versioned.
- Add new assertions with focused tests covering both valid and invalid cases.

Review [CONTRIBUTING.md](../CONTRIBUTING.md) before changing public contracts.

## Boundaries

The included environment is local and in memory. The scripted adapter is for
repeatable software verification. Provider-backed experiments require their
own model configuration, usage budget and interpretation of results.

Redaction and restrictive artifact permissions are baseline safeguards; they
do not guarantee that traces contain no sensitive data. See
[SECURITY.md](../SECURITY.md) and [RESEARCH_PROTOCOL.md](../RESEARCH_PROTOCOL.md).
