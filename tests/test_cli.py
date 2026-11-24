from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent_anvil.cli import main
from agent_anvil.loader import load_scenarios, write_scenarios

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_invalid_run_counts_are_rejected_before_creating_artifacts(self) -> None:
        for option, value in [
            ("--repetitions", "0"),
            ("--repetitions", "-1"),
            ("--limit", "0"),
            ("--limit", "-1"),
            ("--max-steps", "0"),
            ("--max-retries", "-1"),
        ]:
            with self.subTest(option=option, value=value), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "artifacts"
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    main([
                        "run", "--scenarios", str(ROOT / "scenarios/smoke.yaml"),
                        "--agent", "scripted", "--output", str(output),
                        "--ci-gate", option, value,
                    ])
                self.assertEqual(error.exception.code, 2)
                self.assertFalse(output.exists())

    def test_empty_scenario_file_cannot_pass_validation_or_a_ci_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.yaml"
            output = Path(tmp) / "artifacts"
            path.write_text("scenarios: []\n", encoding="utf-8")
            commands = [
                ["validate", str(path)],
                ["run", "--scenarios", str(path), "--agent", "scripted",
                 "--output", str(output), "--ci-gate"],
            ]
            for command in commands:
                with self.subTest(command=command[0]), self.assertRaisesRegex(ValueError, "at least one"):
                    main(command)
            self.assertFalse(output.exists())

    def test_ci_gate_returns_failure_and_retains_diagnostics(self) -> None:
        scenario = load_scenarios(ROOT / "scenarios/smoke.yaml")[0].model_copy(deep=True)
        scenario.scripted_actions = [{"type": "final_response", "content": "Done."}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.yaml"
            output = Path(tmp) / "artifacts"
            write_scenarios(path, [scenario])
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["run", "--scenarios", str(path), "--agent", "scripted",
                             "--output", str(output), "--ci-gate"])
            self.assertEqual(code, 1)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["runs"], 1)
            self.assertEqual(summary["views"]["hybrid_pass"]["failed"], 1)
            self.assertTrue(json.loads((output / "failure_groups.json").read_text()))

    def test_positive_limited_run_and_zero_retries_are_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            code = main(["run", "--scenarios", str(ROOT / "scenarios/smoke.yaml"),
                         "--agent", "scripted", "--output", tmp, "--ci-gate",
                         "--limit", "1", "--repetitions", "2", "--max-retries", "0"])
            self.assertEqual(code, 0)
            summary = json.loads((Path(tmp) / "summary.json").read_text())
            self.assertEqual(summary["runs"], 2)
            self.assertEqual(summary["views"]["hybrid_pass"]["passed"], 2)
