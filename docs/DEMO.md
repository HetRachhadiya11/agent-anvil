# See a trace failure that a plausible answer hides

This local demonstration compares two scripted executions of the same refund
workflow. It uses synthetic in-memory data and makes no external API calls.

After the [installation steps](../README.md#quick-start), run:

```bash
python examples/compare_refund.py
```

Expected output:

| Scenario | Response-only | State | Trace | Hybrid |
| --- | --- | --- | --- | --- |
| valid-refund | PASS | PASS | PASS | PASS |
| invalid-refund | PASS | FAIL | FAIL | FAIL |

The valid execution looks up the order, checks eligibility and refunds that
order. The deliberately invalid execution substitutes an order identifier
that is absent from the environment, while keeping a plausible final message.

The response-only check only tests response presence and runtime-error markers.
The trace and state checks expose the invalid action. The example returns exit
code `0` when this expected contrast is reproduced, and `1` otherwise.

## Inspect the evidence

The command creates `artifacts/refund-example/`:

- `report.md`: summary of the two executions.
- `results.json`: assertion outcomes and diagnostics.
- `failure_groups.json`: failed checks grouped by cause.
- `traces/`: observable events and state snapshots.

[Example source](../examples/compare_refund.py) ·
[Related regression tests](../tests/test_core.py) ·
[Architecture](ARCHITECTURE.md).

This is a deliberately constructed software demonstration. It illustrates
what the checks do; it does not measure the error rate of a real model.
