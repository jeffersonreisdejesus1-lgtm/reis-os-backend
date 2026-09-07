from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments.cognitive_reality.runner import (
    ExperimentRunner,
    TraceWriter,
    _parse_population_roles,
)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        instructions: str,
        prompt: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(
            {"instructions": instructions, "prompt": prompt, "metadata": metadata}
        )
        role = str(metadata["role"])
        if role == "population_planner":
            return {
                "id": "planner",
                "text": (
                    '{"roles":[{"name":"a","instructions":"A"},'
                    '{"name":"b","instructions":"B"}]}'
                ),
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        return {
            "id": role,
            "text": f"output:{role}",
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }


def _events(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def test_mono_is_single_model_call(tmp_path: Path) -> None:
    client = FakeClient()
    trace_path = tmp_path / "mono.jsonl"
    runner = ExperimentRunner(client, TraceWriter(trace_path, "t1"))
    assert runner.mono("task") == "output:mono"
    assert len(client.calls) == 1


def test_multi_isolated_uses_distinct_agents(tmp_path: Path) -> None:
    client = FakeClient()
    trace_path = tmp_path / "multi.jsonl"
    runner = ExperimentRunner(client, TraceWriter(trace_path, "t2"))
    runner.multi_isolated("task")
    roles = [call["metadata"]["role"] for call in client.calls]
    assert roles == ["architect", "engineer", "skeptic", "verifier", "synthesizer"]
    ids = [call["metadata"]["agent_instance_id"] for call in client.calls]
    assert len(set(ids)) == len(ids)


def test_mesh_records_links_between_agents(tmp_path: Path) -> None:
    client = FakeClient()
    trace_path = tmp_path / "mesh.jsonl"
    runner = ExperimentRunner(client, TraceWriter(trace_path, "t3"))
    runner.mesh("task")
    events = _events(trace_path)
    starts = [event for event in events if event["event_type"] == "span_start"]
    revision_starts = [
        event for event in starts if str(event["role"]).endswith("_revision")
    ]
    assert len(revision_starts) == 4
    assert all(len(event["links"]) == 3 for event in revision_starts)


def test_population_creates_runtime_roles(tmp_path: Path) -> None:
    client = FakeClient()
    trace_path = tmp_path / "population.jsonl"
    runner = ExperimentRunner(client, TraceWriter(trace_path, "t4"))
    runner.population("task")
    roles = [call["metadata"]["role"] for call in client.calls]
    assert roles == [
        "population_planner",
        "a",
        "b",
        "population_critic",
        "population_synthesizer",
    ]


def test_population_parser_falls_back() -> None:
    roles = _parse_population_roles("not-json", max_agents=3)
    assert len(roles) == 3


def test_mesh_ablation_removes_role(tmp_path: Path) -> None:
    client = FakeClient()
    trace_path = tmp_path / "ablation.jsonl"
    runner = ExperimentRunner(client, TraceWriter(trace_path, "t5"))
    runner.mesh_ablation("task", "skeptic")
    roles = [call["metadata"]["role"] for call in client.calls]
    assert "skeptic" not in roles
    assert "skeptic_revision" not in roles
    assert "architect" in roles
    events = _events(trace_path)
    assert any(
        event.get("event_type") == "ablation"
        and event.get("removed") == "skeptic"
        for event in events
    )
