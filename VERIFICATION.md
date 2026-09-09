# Verification record for Agent Anvil 0.2.0

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

Cryptographic hashes of the final release files are recorded in
`SHA256SUMS.txt`.
