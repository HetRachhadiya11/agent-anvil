# Changelog

## 0.2.1 — 2026-11-24

- Reject empty scenario files and non-positive repetitions, limits and step counts,
  preventing CI success without scenario execution. Negative retry counts are also rejected.
- Add four CLI regression tests covering invalid inputs, empty suites, failed gates
  with retained diagnostics and valid limited runs.
- Measure coverage across the application package, excluding tests and including the CLI.
- Add a runnable valid-versus-invalid refund example and run it in CI.
- Add publication references, contribution case studies and an updated verification record.
- Clarify manuscript status, historical checksums and software citation metadata.

## 0.2.0 — 2026-09-08

Implementation changes dated 8 September; verification and citation release date
are 9 September 2026.

- Added executable trace and scenario models with exported JSON Schemas.
- Added 100 policy-bearing scenarios across five stateful tool domains.
- Added response-only, state-only, trace-only, hybrid, and optional LLM-judge views.
- Added an OpenAI Responses API function-calling adapter and deterministic smoke adapter.
- Added per-check failure accounting, deterministic diagnostic grouping, paired tests,
  clustered bootstrap intervals, and human-annotation metrics.
- Added recursive credential redaction and restrictive artifact permissions.
- Added tests, CI, research protocol, annotation guide, and release metadata.
