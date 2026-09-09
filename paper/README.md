# Manuscript source

This directory contains the SoftwareX manuscript source. It uses Elsevier's
`elsarticle` class (version 3.5, 9 January 2026) and a numeric reference list.

Build from this directory with:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error softwarex_submission.tex
```

The bundled `elsarticle.cls` and `elsarticle-num.bst` are distributed under the
LaTeX Project Public License as part of Elsevier's official `elsarticle` bundle.
They are included so Editorial Manager and minimal TeX installations can compile
the submission source reproducibly.
