# REIS OS Cognitive Reality Test v0

Purpose: falsify or validate claims about PIs, multi-agent operation, cognitive meshes, dynamic populations, and the broader OCS physiology.

## Conditions

- `mono`: one model call solves the task directly.
- `sham`: one model call simulates several roles internally. This is the placebo/control for role-play.
- `multi_isolated`: several distinct model calls receive the same task independently; a distinct synthesizer aggregates them.
- `mesh`: distinct agents produce a first round, receive peer outputs through explicit graph links, revise, then a distinct synthesizer aggregates.
- `population`: a planner creates temporary specialist roles at runtime; workers execute, a critic challenges them, and a synthesizer closes.

## Epistemic levels

- `E0 CLAIM`: documented or asserted only.
- `E1 MATERIALIZED`: code/configuration can instantiate the component.
- `E2 OBSERVED`: runtime traces prove that it executed.
- `E3 CAUSAL`: ablation shows that removing it changes outcomes.
- `E4 REPLICATED`: the effect repeats across tasks/runs/cold starts.
- `E5 OPERATIONALLY_VALIDATED`: benefit survives real use, including cost, latency, failures, and governance constraints.

No claim is promoted solely because a prompt contains the words PI, mesh, population, physiology, or civilization.

## Instrumentation

Every model call gets a unique `trace_id`, `span_id`, `agent_instance_id`, role, timestamps, links to peers/parents, response id, token usage, duration, and output. A mesh is only E2 if the trace contains distinct agent instances and explicit cross-agent links. A population is only E2 if roles are created at runtime and executed as distinct calls.

## Pilot battery

`tasks.json` contains 20 self-contained tasks across architecture, authority, evidence, engineering, contradiction, product, recovery, and synthesis. They intentionally avoid using prior answers as ground truth.

## Live run

```bash
export OPENAI_API_KEY=...
export COG_TEST_MODEL=gpt-5-mini
python experiments/cognitive_reality/runner.py \
  --tasks experiments/cognitive_reality/tasks.json \
  --out artifacts/cognitive-reality
python experiments/cognitive_reality/analyze.py artifacts/cognitive-reality/results.jsonl
```

The live runner uses the OpenAI Responses API and standard-library HTTP only. It does not mutate Notion, GitHub, Railway, or other institutional sources.

## Interpretation rule

If a named component cannot be seen in trace data, it is not `E2 OBSERVED`. If removing or disconnecting it does not measurably change results across replicated runs, it is not `E3 CAUSAL`. If `mono` or `sham` performs equivalently at lower cost/latency, the more complex architecture is not justified for that task class.
