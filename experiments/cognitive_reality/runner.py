from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


DEFAULT_ROLES = {
    "architect": "Analyze structure, assumptions, dependencies, and simplifications.",
    "engineer": "Analyze executability, implementation constraints, and failure modes.",
    "skeptic": "Try to falsify claims, detect overclaim, missing evidence, and hidden assumptions.",
    "verifier": "Define what evidence would prove or disprove each material claim.",
}


class ModelClient(Protocol):
    def complete(
        self,
        *,
        instructions: str,
        prompt: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        ...


class OpenAIResponsesClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(
        self,
        *,
        instructions: str,
        prompt: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        body = json.dumps(
            {
                "model": self.model,
                "instructions": instructions,
                "input": prompt,
                "metadata": {str(k): str(v) for k, v in metadata.items()},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail}") from exc

        return {
            "id": payload.get("id"),
            "text": _extract_output_text(payload),
            "usage": payload.get("usage", {}),
            "raw_status": payload.get("status"),
        }


def _extract_output_text(payload: dict[str, Any]) -> str:
    text_parts: list[str] = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") in {"output_text", "text"}:
                text = part.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
    return "\n".join(text_parts).strip()


@dataclass(frozen=True)
class SpanResult:
    span_id: str
    agent_instance_id: str
    role: str
    text: str
    response_id: str | None
    usage: dict[str, Any]
    started_at: float
    ended_at: float


class TraceWriter:
    def __init__(self, path: Path, trace_id: str) -> None:
        self.path = path
        self.trace_id = trace_id
        path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, event_type: str, **fields: Any) -> None:
        row = {
            "trace_id": self.trace_id,
            "event_type": event_type,
            "ts": time.time(),
            **fields,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


class ExperimentRunner:
    def __init__(self, client: ModelClient, trace: TraceWriter) -> None:
        self.client = client
        self.trace = trace

    def _call(
        self,
        *,
        role: str,
        instructions: str,
        prompt: str,
        parent_span_id: str | None = None,
        links: list[str] | None = None,
    ) -> SpanResult:
        span_id = uuid.uuid4().hex
        agent_instance_id = uuid.uuid4().hex
        started = time.time()
        self.trace.event(
            "span_start",
            span_id=span_id,
            parent_span_id=parent_span_id,
            links=links or [],
            agent_instance_id=agent_instance_id,
            role=role,
        )
        response = self.client.complete(
            instructions=instructions,
            prompt=prompt,
            metadata={
                "trace_id": self.trace.trace_id,
                "span_id": span_id,
                "agent_instance_id": agent_instance_id,
                "role": role,
            },
        )
        ended = time.time()
        result = SpanResult(
            span_id=span_id,
            agent_instance_id=agent_instance_id,
            role=role,
            text=str(response.get("text", "")),
            response_id=response.get("id"),
            usage=dict(response.get("usage", {})),
            started_at=started,
            ended_at=ended,
        )
        self.trace.event(
            "span_end",
            span_id=span_id,
            parent_span_id=parent_span_id,
            links=links or [],
            agent_instance_id=agent_instance_id,
            role=role,
            response_id=result.response_id,
            usage=result.usage,
            duration_s=ended - started,
            output=result.text,
        )
        return result

    def mono(self, task: str) -> str:
        return self._call(
            role="mono",
            instructions=(
                "Solve the task directly. Separate evidence from inference and avoid "
                "overclaim."
            ),
            prompt=task,
        ).text

    def sham(self, task: str) -> str:
        roles = ", ".join(DEFAULT_ROLES)
        return self._call(
            role="sham_single_model",
            instructions=(
                "You are one model simulating several internal roles. Do not claim they "
                "are separate agents. "
                f"Simulate these perspectives: {roles}; then synthesize one answer."
            ),
            prompt=task,
        ).text

    def multi_isolated(self, task: str) -> str:
        opinions: list[SpanResult] = []
        for role, instructions in DEFAULT_ROLES.items():
            opinions.append(
                self._call(role=role, instructions=instructions, prompt=task)
            )
        joined = _join_outputs(opinions)
        return self._call(
            role="synthesizer",
            instructions=(
                "Synthesize independent analyses. Preserve disagreements and do not "
                "invent consensus."
            ),
            prompt=f"TASK:\n{task}\n\nINDEPENDENT ANALYSES:\n{joined}",
            links=[item.span_id for item in opinions],
        ).text

    def mesh(self, task: str) -> str:
        return self._mesh_with_roles(task, DEFAULT_ROLES)

    def mesh_ablation(self, task: str, removed_role: str) -> str:
        if removed_role not in DEFAULT_ROLES:
            raise ValueError(f"Unknown ablation role: {removed_role}")
        roles = {
            name: instructions
            for name, instructions in DEFAULT_ROLES.items()
            if name != removed_role
        }
        self.trace.event("ablation", component="mesh_role", removed=removed_role)
        return self._mesh_with_roles(task, roles)

    def _mesh_with_roles(self, task: str, roles: dict[str, str]) -> str:
        first_round: list[SpanResult] = []
        for role, instructions in roles.items():
            first_round.append(
                self._call(role=role, instructions=instructions, prompt=task)
            )

        peer_context = _join_outputs(first_round)
        second_round: list[SpanResult] = []
        for role, instructions in roles.items():
            own = next(item for item in first_round if item.role == role)
            second_round.append(
                self._call(
                    role=f"{role}_revision",
                    instructions=(
                        instructions
                        + " Review peer outputs, revise only when warranted, and "
                        "explicitly identify what changed."
                    ),
                    prompt=f"TASK:\n{task}\n\nPEER ROUND:\n{peer_context}",
                    parent_span_id=own.span_id,
                    links=[
                        item.span_id
                        for item in first_round
                        if item.span_id != own.span_id
                    ],
                )
            )
        return self._call(
            role="mesh_synthesizer",
            instructions=(
                "Synthesize the revised mesh. Preserve unresolved contradictions and "
                "cite which roles support each claim."
            ),
            prompt=f"TASK:\n{task}\n\nREVISED MESH:\n{_join_outputs(second_round)}",
            links=[item.span_id for item in second_round],
        ).text

    def population(self, task: str, max_agents: int = 6) -> str:
        planner = self._call(
            role="population_planner",
            instructions=(
                "Design a temporary population of specialist roles for the task. Return "
                "strict JSON only: "
                '{"roles":[{"name":"...","instructions":"..."}]}. Use 2 to 6 roles.'
            ),
            prompt=task,
        )
        roles = _parse_population_roles(planner.text, max_agents=max_agents)
        workers: list[SpanResult] = []
        for role in roles:
            workers.append(
                self._call(
                    role=role["name"],
                    instructions=role["instructions"],
                    prompt=task,
                    parent_span_id=planner.span_id,
                )
            )
        critic = self._call(
            role="population_critic",
            instructions=(
                "Evaluate the temporary population outputs, identify contradictions, "
                "weak claims, and missing evidence."
            ),
            prompt=f"TASK:\n{task}\n\nPOPULATION OUTPUTS:\n{_join_outputs(workers)}",
            links=[item.span_id for item in workers],
        )
        return self._call(
            role="population_synthesizer",
            instructions=(
                "Produce the final answer using population outputs and critic. Do not "
                "hide uncertainty or disagreement."
            ),
            prompt=(
                f"TASK:\n{task}\n\nPOPULATION OUTPUTS:\n{_join_outputs(workers)}"
                f"\n\nCRITIC:\n{critic.text}"
            ),
            links=[item.span_id for item in workers] + [critic.span_id],
        ).text

    def run_condition(self, condition: str, task: str) -> str:
        mapping = {
            "mono": self.mono,
            "sham": self.sham,
            "multi_isolated": self.multi_isolated,
            "mesh": self.mesh,
            "population": self.population,
        }
        self.trace.event("condition_start", condition=condition)
        if condition.startswith("mesh_without_"):
            result = self.mesh_ablation(
                task,
                condition.removeprefix("mesh_without_"),
            )
        else:
            try:
                fn = mapping[condition]
            except KeyError as exc:
                raise ValueError(f"Unknown condition: {condition}") from exc
            result = fn(task)
        self.trace.event("condition_end", condition=condition, output=result)
        return result


def _join_outputs(items: list[SpanResult]) -> str:
    return "\n\n".join(f"[{item.role}]\n{item.text}" for item in items)


def _parse_population_roles(text: str, max_agents: int) -> list[dict[str, str]]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return [
            {"name": name, "instructions": instructions}
            for name, instructions in list(DEFAULT_ROLES.items())[:max_agents]
        ]
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        payload = {}
    raw_roles = payload.get("roles", [])
    roles: list[dict[str, str]] = []
    for item in raw_roles[:max_agents]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        instructions = str(item.get("instructions", "")).strip()
        if name and instructions:
            roles.append({"name": name, "instructions": instructions})
    if len(roles) < 2:
        return [
            {"name": name, "instructions": instructions}
            for name, instructions in list(DEFAULT_ROLES.items())[:max_agents]
        ]
    return roles


def load_tasks(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")
    return [dict(item) for item in tasks]


def main() -> int:
    parser = argparse.ArgumentParser(description="REIS OS Cognitive Reality Test")
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/cognitive-reality"),
    )
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=["mono", "sham", "multi_isolated", "mesh", "population"],
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--include-ablations", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for live execution")
    model = os.environ.get("COG_TEST_MODEL", "gpt-5-mini")
    if args.include_ablations:
        args.conditions.extend(
            f"mesh_without_{role}" for role in DEFAULT_ROLES
        )
    tasks = load_tasks(args.tasks)
    if args.limit > 0:
        tasks = tasks[: args.limit]

    args.out.mkdir(parents=True, exist_ok=True)
    results_path = args.out / "results.jsonl"
    for task in tasks:
        task_id = str(task["id"])
        prompt = str(task["prompt"])
        for condition in args.conditions:
            trace_id = f"{task_id}-{condition}-{uuid.uuid4().hex[:12]}"
            trace_path = args.out / "traces" / f"{trace_id}.jsonl"
            runner = ExperimentRunner(
                OpenAIResponsesClient(api_key, model),
                TraceWriter(trace_path, trace_id),
            )
            started = time.time()
            try:
                output = runner.run_condition(condition, prompt)
                error = None
            except Exception as exc:  # noqa: BLE001
                output = ""
                error = f"{type(exc).__name__}: {exc}"
            row = {
                "task_id": task_id,
                "category": task.get("category"),
                "condition": condition,
                "trace_id": trace_id,
                "trace_path": str(trace_path),
                "model": model,
                "duration_s": time.time() - started,
                "output": output,
                "error": error,
            }
            with results_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
