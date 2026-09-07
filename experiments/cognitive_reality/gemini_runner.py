from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from experiments.cognitive_reality.runner import (
    DEFAULT_ROLES,
    ExperimentRunner,
    TraceWriter,
    load_tasks,
)


class GeminiGenerateContentClient:
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
        del metadata
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": instructions}]},
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
            }
        ).encode("utf-8")
        model = urllib.parse.quote(self.model, safe="")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc

        return {
            "id": payload.get("responseId"),
            "text": _extract_output_text(payload),
            "usage": payload.get("usageMetadata", {}),
            "raw_status": _extract_status(payload),
        }


def _extract_output_text(payload: dict[str, Any]) -> str:
    text_parts: list[str] = []
    for candidate in payload.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if isinstance(text, str):
                text_parts.append(text)
    return "\n".join(text_parts).strip()


def _extract_status(payload: dict[str, Any]) -> str | None:
    candidates = payload.get("candidates", [])
    if candidates:
        finish_reason = candidates[0].get("finishReason")
        if finish_reason is not None:
            return str(finish_reason)
    prompt_feedback = payload.get("promptFeedback", {})
    block_reason = prompt_feedback.get("blockReason")
    return str(block_reason) if block_reason is not None else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="REIS OS Cognitive Reality Test — Gemini"
    )
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/cognitive-reality-gemini"),
    )
    parser.add_argument(
        "--conditions",
        nargs="+",
        default=["mono", "sham", "multi_isolated", "mesh", "population"],
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--include-ablations", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is required for live execution")
    model = os.environ.get("COG_TEST_MODEL", "gemini-2.5-flash")
    if args.include_ablations:
        args.conditions.extend(f"mesh_without_{role}" for role in DEFAULT_ROLES)
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
                GeminiGenerateContentClient(api_key, model),
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
                "provider": "gemini",
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
