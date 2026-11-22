# Contributing to Agent Anvil

Contributions can improve the regression engine, adapters, scenario coverage
or documentation. Describe the observable behaviour you want to change and
include a minimal, reproducible example where relevant.

## Development setup

Use Python 3.10 or newer in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

On Windows PowerShell, use `.\.venv\Scripts\Activate.ps1` to activate it.

## Validate a change

The following commands mirror the repository's CI checks:

```bash
python -m ruff check agent_anvil scripts tests
python scripts/build_benchmark.py
python scripts/export_schemas.py
python -m agent_anvil.cli validate scenarios/benchmark_v1.yaml
python -m coverage run --branch -m unittest discover -s tests -v
python -m coverage report --fail-under=80
python -m agent_anvil.cli run --scenarios scenarios/smoke.yaml --agent scripted --output artifacts/ci --ci-gate
python -m build
```

For documentation changes, verify the examples and links you changed. New
behaviour should include a focused regression test. Avoid unrelated generated
files, local environments and runtime artifacts in your commit.

## Scenario and schema changes

- Explain the contract a scenario is intended to check.
- Keep scenario identifiers unique and validate the YAML before committing.
- Document schema compatibility changes and update generated schemas when needed.
- If assertions change after inspecting model outcomes, introduce a new
  benchmark version and explain the change. Preserve the original study protocol.
- Keep scripted implementation checks separate from provider-model results.

See [RESEARCH_PROTOCOL.md](RESEARCH_PROTOCOL.md) for study and annotation rules.

## Pull requests

Keep each change focused. Describe the problem, resulting behaviour and checks
run. Link an existing issue when relevant. For visible documentation changes,
check GitHub's Markdown preview as well as the source text.

## Sensitive data

Never include credentials, personal data or unredacted production traces in a
commit, issue or pull request. Report vulnerabilities through the private
contact listed in [SECURITY.md](SECURITY.md).
