#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is not configured. Set it in the execution environment; never commit it." >&2
  exit 2
fi

if [[ "$#" -lt 2 ]]; then
  echo "Usage: $0 JUDGE_MODEL AGENT_MODEL [AGENT_MODEL ...]" >&2
  exit 2
fi

judge_model="$1"
shift
run_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
result_files=()

python scripts/build_benchmark.py
python scripts/export_schemas.py
python -m unittest discover -s tests -v
python -m agent_anvil.cli validate scenarios/benchmark_v1.yaml

for agent_model in "$@"; do
  model_slug="$(printf '%s' "$agent_model" | tr -c 'A-Za-z0-9_.-' '-')"
  output_dir="artifacts/real_${run_stamp}_${model_slug}"
  python -m agent_anvil.cli run \
    --scenarios scenarios/benchmark_v1.yaml \
    --agent openai \
    --model "$agent_model" \
    --judge-model "$judge_model" \
    --repetitions 3 \
    --output "$output_dir"
  result_files+=("$output_dir/results.json")
done

analysis_path="artifacts/journal_analysis_${run_stamp}.json"
python scripts/analyze_results.py \
  "${result_files[@]}" \
  --iterations 10000 \
  --output "$analysis_path"

echo "Completed paired real-agent experiment. Analysis: $analysis_path"
