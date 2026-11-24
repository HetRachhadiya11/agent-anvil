AGENT ANVIL — MANUSCRIPT ARTIFACT GUIDE

The paper/ directory contains materials prepared for a SoftwareX original
software article describing version 0.2.0. These files do not establish that
the manuscript was submitted, accepted or published.

PUBLIC SOFTWARE
https://github.com/HetRachhadiya11/agent-anvil

Version 0.2.0 source snapshot used by the manuscript:
https://github.com/HetRachhadiya11/agent-anvil/tree/03cae537e93c317048f2afccd70d6fe73253869e

Current software version: 0.2.1. See CHANGELOG.md and VERIFICATION.md for the
maintenance changes and the separately dated verification results.

ARTIFACTS IN THIS REPOSITORY
- paper/softwarex_submission.pdf: version 0.2.0 manuscript
- paper/softwarex_submission.tex: editable manuscript source
- paper/highlights.txt: manuscript highlights
- paper/cover_letter.md: draft submission cover letter
- paper/reviewer_response_map.md: methodological revision history
- CITATION.cff: citation metadata for the current software version
- RESEARCH_PROTOCOL.md: protocol for future provider-backed evaluation

BUILD THE MANUSCRIPT
From paper/, run:
latexmk -pdf -interaction=nonstopmode -halt-on-error softwarex_submission.tex

REPRODUCE THE SOFTWARE
Follow README.md for installation and CONTRIBUTING.md for validation.
The default scripted checks use synthetic local fixtures and need no API key.
Model-backed experiments are optional and are not established by those checks.

HISTORICAL CHECKSUMS
SHA256SUMS.txt records the September 2026 version 0.2.0 artifacts. The wheel
and source archive named there are not bundled with a normal Git checkout.
Those hashes are historical, not hashes of the current 0.2.1 build.

RESEARCH STATUS
See SUBMISSION_STATUS.md for the distinction between the software, manuscript
materials, and the further evaluation required for empirical model claims.
