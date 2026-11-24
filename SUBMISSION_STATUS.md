# Research and manuscript status

## Software artifact

Agent Anvil 0.2.1 is an installable Apache-2.0 Python research package. Its
implemented features include versioned scenarios and traces, a local stateful
tool environment, deterministic assertions, paired evaluation views,
CI-friendly reports and an optional OpenAI Responses API adapter.

The [verification record](VERIFICATION.md) reports 18 passing tests, 80%
package-only statement/branch coverage, five passing smoke scenarios and validation
of 100 benchmark scenarios.

## Manuscript materials

The repository contains manuscript materials prepared for **SoftwareX,
Original Software Publication**, including the source, cover letter and
highlights. The presence of these files does not establish submission,
acceptance or journal publication.

The current manuscript reports software verification. An earlier constructed
demonstration was superseded by the version 0.2.0 verification approach; see
the [changelog](CHANGELOG.md) for the software history.

The manuscript and its September verification describe version 0.2.0. The
November 0.2.1 maintenance release adds CLI validation and public documentation;
its verification is reported separately. The manuscript has not been silently
rewritten to imply that it evaluated the newer release.

## Further evaluation

Provider-backed model trials and independent human annotation are defined in
[RESEARCH_PROTOCOL.md](RESEARCH_PROTOCOL.md). They are separate from the
completed functional tests. Model rankings, real-world failure incidence and
production effectiveness are not established by the current verification.
