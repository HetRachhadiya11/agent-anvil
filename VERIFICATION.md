# Verification record for Agent Anvil 0.2.1

Verification date: **24 November 2026**.

## Environment and scope

Linux; Python 3.12.14; Pydantic 2.14.4; PyYAML 6.0.4;
Coverage.py 7.17.4; Ruff 0.17.6; Build 1.6.1.

The checks below use synthetic local scenarios. The provider adapter and
response judge are tested with injected fake clients. No paid API call,
provider-model experiment or independent human annotation is represented by
these results.

## Executed checks

| Check | Result |
| --- | --- |
| `python -m ruff check agent_anvil scripts tests examples` | Pass |
| `python -m coverage run -m unittest discover -s tests -v` | 18/18 tests pass |
| `python -m coverage report` | 80% combined statement/branch coverage; 80% gate passes |
| `python -m agent_anvil.cli validate scenarios/benchmark_v1.yaml` | 100 scenarios across 5 suites |
| Scripted smoke run with `--ci-gate` | 5/5 hybrid pass |
| `python examples/compare_refund.py` | Valid trace passes; deliberately invalid trace fails state, trace and hybrid checks |
| Invalid CLI counts and empty scenario set | Rejected before artifacts are created |
| Failing scenario through the CLI | Exit code 1 with diagnostics retained |
| Wheel and source-distribution build | Pass |
| Wheel installation outside the checkout | Version 0.2.1 imports and smoke run passes |

The [coverage configuration](.coveragerc) measures the entire `agent_anvil`
package, including the CLI, and excludes test code. This differs from the
historical 0.2.0 measurement below, which included executed test modules.
Coverage is a check of exercised code paths, not a security or correctness guarantee.

## Reproduce

Use the commands in [CONTRIBUTING.md](CONTRIBUTING.md).
The [GitHub Actions workflow](.github/workflows/test.yml) runs the checks on
Python 3.10, 3.11 and 3.12. The dated local results above are from Python 3.12.14;
the live workflow is the source for results on other versions.

The smoke suite verifies five known-valid executions. The
[refund demonstration](docs/DEMO.md) deliberately creates one invalid trace
and checks that it is rejected. Neither is a model-performance benchmark.

---

# Historical verification: version 0.2.0

Verification date: 9 September 2026

Environment:

- Linux 6.18.35
- Python 3.12.13
- Pydantic 2.13.4
- PyYAML 6.0.3
- OpenAI SDK 2.54.0
- Coverage.py 7.16.0

Executed checks:

| Check | Result |
| --- | --- |
| `python -m ruff check agent_anvil scripts tests` | Pass |
| `python -m coverage run --branch -m unittest discover -s tests -v` | 14/14 pass |
| `python -m coverage report --fail-under=80` | Pass; 81% combined coverage |
| `python scripts/build_benchmark.py` | 100 benchmark and 5 smoke scenarios generated |
| `python -m agent_anvil.cli validate scenarios/benchmark_v1.yaml` | Valid; 100 scenarios; 5 suites |
| Scripted end-to-end smoke run with `--ci-gate` | 5/5 hybrid pass |
| `python -m build` | Wheel and source distribution built |
| Wheel force-installed outside the repository and benchmark validated | Pass |
| SoftwareX manuscript compiled with `latexmk` | Pass |

The scripted smoke adapter is a deterministic implementation check. These
results are not estimates of provider-model accuracy or hidden-failure
incidence. No provider-model result or human annotation was fabricated.

Historical artifact hashes are recorded in `SHA256SUMS.txt`. They refer to
version 0.2.0, not the current build; see [the artifact guide](SUBMISSION_README.txt).
