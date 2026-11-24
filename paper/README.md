# Manuscript source

This directory contains manuscript materials prepared for SoftwareX, describing
Agent Anvil **0.2.0**. Submission or acceptance is not established by these files;
see [research status](../SUBMISSION_STATUS.md). The current software verification
is in [VERIFICATION.md](../VERIFICATION.md).

The manuscript uses Elsevier's
`elsarticle` class (version 3.5, 9 January 2026) and a numeric reference list.

Build from this directory with:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error softwarex_submission.tex
```

The bundled `elsarticle.cls` and `elsarticle-num.bst` are distributed under the
LaTeX Project Public License as part of Elsevier's official `elsarticle` bundle.
They are included so Editorial Manager and minimal TeX installations can compile
the submission source reproducibly.
