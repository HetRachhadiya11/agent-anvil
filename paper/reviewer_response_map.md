# ICTAI feedback to SoftwareX revision map

| Reviewer concern | Change in version 0.2.0 | Remaining evidence |
|---|---|---|
| Constructed 100% to 30% headline | Removed from the SoftwareX claims and results; retained only as rejected methodology in the discussion | None for removal |
| No genuine LLM agent | Added an executable OpenAI Responses API function-calling adapter and a frozen multi-model protocol | Optional empirical extension; no model-performance claim is made in the software article |
| Weak response-only baseline | Added an isolated structured LLM response judge and environment-state and hybrid views | Human calibration is required before any judge-quality claim |
| Degenerate ablation | Replaced layer ablation with per-check counts, sole detections, and overlap matrices | Populated only when an empirical model study is run |
| Policy-count inconsistency | Eliminated old injected category percentages and assigned every rule a stable identifier | None for the software-verification claims |
| Wilson intervals on fixed fixtures | Removed; added exact paired McNemar testing and scenario-clustered bootstrap intervals for stochastic repetitions | Used only for a future stochastic study |
| Valid alternative sequences | Allowed bounded read-only retries and independent-check reorderings; annotation guide includes alternative-sequence labels | Dual annotation is required before a false-positive-rate claim |
| Semantic grader unvalidated | Isolated response judge from trace/state and added human-validation metrics | No semantic-grader result is claimed in the software article |
| No privacy controls | Added recursive redaction, owner-only directories/files, security documentation, and a persistence test | Organizational deployment review |
| Failure clustering unclear | Defined deterministic grouping key; stopped calling it learned clustering | Human taxonomy validation if a quality claim is desired |
| Trace schema unspecified | Exported complete `anvil.trace.v1` and `anvil.scenario.v1` JSON Schemas and conformance tests | Public release URL |
| Thin related work and novelty | Repositioned against observability platforms, evaluation libraries, and trajectory benchmarks; no claim that trace evaluation is new | Completed citation verification for cited primary papers and official documentation |
| No repository URL | Prepared licensed release with README, CI, schemas, scenarios, tests, and citation metadata | Publish the tagged public repository |
| Presentation defects | Rewritten as a SoftwareX original software article; removed broken figures, percentage restatements, and citation stuffing | Completed in Elsevier's current `elsarticle` class and SoftwareX section structure |
