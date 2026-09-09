# Contributing

Contributions should include tests, documentation, and a clear explanation of
the behavioral contract being changed. Do not add benchmark assertions after
reviewing model results without creating a new benchmark version and documenting
the change.

Run before proposing a change:

```bash
python scripts/build_benchmark.py
python scripts/export_schemas.py
python -m unittest discover -s tests -v
```

Never include credentials, personal data, or unredacted production traces in a
commit, issue, or pull request.
