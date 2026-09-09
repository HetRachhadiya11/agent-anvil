# Agent Anvil

Agent Anvil is a local, CI-first regression harness for tool-using agents. It
records **observable** model/tool events, evaluates deterministic trace and
environment-state invariants, and writes reproducible JSON, JSONL, CSV, and
Markdown artifacts. It does not request, infer, or store hidden chain-of-thought.

This repository is the research artifact for the Agent Anvil SoftwareX
manuscript. Version `0.2.0` replaces an earlier development-only
"agents-authored-to-fail" demonstration with reproducible software
verification and a preregistered protocol for optional provider-backed studies.

## What is implemented

- versioned `anvil.trace.v1` and `anvil.scenario.v1` schemas;
- YAML scenario loading and validation;
- an in-memory stateful tool environment with auditable side effects;
- deterministic checks for tool use, arguments, ordering, call limits,
  preconditions, results, final responses, and final state;
- response-only, environment-state, trace-only, and hybrid evaluation views;
- deterministic failure grouping;
- redaction of common credentials and restrictive artifact permissions;
- a scripted adapter for tests and an OpenAI Responses API adapter for real runs;
- a 100-scenario benchmark generator and reproducible experiment manifest;
- standard-library unit tests and a CI workflow.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python scripts/build_benchmark.py
python -m agent_anvil.cli validate scenarios/benchmark_v1.yaml
python -m unittest discover -s tests -v
```

Run the deterministic smoke suite:

```bash
python -m agent_anvil.cli run \
  --scenarios scenarios/smoke.yaml \
  --agent scripted \
  --output artifacts/smoke
```

Run genuine model trials after configuring `OPENAI_API_KEY` in the execution
environment (never commit the key):

```bash
python -m pip install -e '.[openai]'
python -m agent_anvil.cli run \
  --scenarios scenarios/benchmark_v1.yaml \
  --agent openai \
  --model MODEL_ID \
  --judge-model JUDGE_MODEL_ID \
  --repetitions 3 \
  --output artifacts/MODEL_ID
```

The adapter uses function tools with strict JSON schemas and feeds tool results
back to the model until a final response or the configured step limit. Every
model request, observable model response, tool call, tool result, protocol
error, final response, and final state snapshot is timestamped.

## Evaluation views

Each completed run is scored four ways over the same execution:

1. **Response-only:** final response is present and contains no explicit runtime
   error marker.
2. **Environment-state:** only final-state assertions are evaluated.
3. **Trace-only:** tool, argument, order, result, and policy assertions are
   evaluated.
4. **Hybrid:** response, state, and trace assertions must all pass.

These are paired views, not independent samples. The analysis script reports
paired disagreements and per-check unique/incremental detections rather than
misusing confidence intervals on a fixed deterministic fixture set.

## Evidence and research scope

The SoftwareX article reports functional verification of the software: 14
automated tests with 81% combined statement/branch coverage, five end-to-end
smoke scenarios, schema validation of 100 balanced scenarios, and one
deliberately invalid trace. It does not estimate
real-agent failure incidence or rank models. `RESEARCH_PROTOCOL.md` freezes a
separate optional protocol for a future provider-backed empirical study, so
model outcomes and human labels cannot be invented or retrofitted after results
are observed.

Reproduce the branch-aware coverage result with:

```bash
python -m coverage run --branch -m unittest discover -s tests -v
python -m coverage report --fail-under=80
```

## Security

Trace artifacts can contain sensitive content. Agent Anvil redacts common secret
patterns before persistence and creates files with owner-only permissions by
default. This is a baseline control, not a substitute for an organizational
data-classification, access-control, and retention policy. See `SECURITY.md`.

## License

Apache License 2.0. See `LICENSE`.
