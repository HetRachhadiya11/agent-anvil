# Usage and evaluation

[Quick start](../README.md#quick-start) · [Demonstration](DEMO.md) ·
[Verification](../VERIFICATION.md) · [Contributing](../CONTRIBUTING.md)

Reports from people who try Agent Anvil help improve installation, scenario
design and regression checks. Successful runs, partial results and failures
are all useful.

## Current evidence

As of **24 November 2026**, the [verification record](../VERIFICATION.md)
documents maintainer-run tests, controlled scenarios and package checks.
Independent external adoption has not yet been established by the evidence
published in this repository.

The [workplace case studies](CASE_STUDIES.md) describe
separate analytics work. They are not evidence that those organisations use
Agent Anvil.

## Share a result

Use the [reproduction or usage report](https://github.com/HetRachhadiya11/agent-anvil/issues/new?template=usage_report.yml)
to record your version, environment, steps, observed result and any safe
supporting evidence. A short failed installation report is as welcome as a
successful integration report. For a specific defect, use the
[bug report](https://github.com/HetRachhadiya11/agent-anvil/issues/new?template=bug_report.yml).

Issues are public. Use synthetic examples and remove credentials, personal
data and confidential traces. See the [security policy](../SECURITY.md) for
private vulnerability reporting.

## How evidence is interpreted

| Evidence | What it can establish | What else is needed |
| --- | --- | --- |
| A dated report with version, commands and results | A reported reproduction attempt in a stated environment | A maintainer reproduction or inspectable artifacts to check the result |
| Repeated use or an integration described by an external user | Use beyond a one-off demonstration | Observation dates, purpose, frequency and the reporter's relationship to the project |
| A measured improvement | A result for a defined workflow and sample | Comparable baseline, metric definition, raw totals, observation period and limitations |

A submitted issue is a user report, not an automatic verification. Summaries
should link to the original report, preserve unsuccessful results and state
whether the maintainer reproduced them. Disclose collaboration or assistance
when describing a result as independent. Stars, forks and page views are
interest signals and are not counts of active users.

## Measure a useful outcome

Before a comparison, define the workflow, metric and success criterion. Keep
the scenario set, software version and relevant environment settings fixed,
or document what changed. Record:

1. **Scope and period:** who or what was observed, start/end dates, and
   exclusions such as development runs or duplicate reports.
2. **Baseline and result:** raw totals and sample sizes for both conditions.
   For elapsed time, report the same task and timing boundaries; for detection
   rates, report detected failures / known failures and false alarms / valid
   cases separately.
3. **Supporting evidence:** a public report, reproducible synthetic example
   or permissioned record, with the reporter's relationship to the project.
4. **Limits:** missing observations, selection effects, configuration changes
   and whether the result comes from controlled fixtures or a real workflow.

These are reporting requirements for future observations, not measurements
already collected. Real-model evaluation should also follow the
[research protocol](../RESEARCH_PROTOCOL.md).
