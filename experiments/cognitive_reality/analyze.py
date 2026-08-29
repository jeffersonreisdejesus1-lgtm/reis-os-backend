from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def trace_stats(path: Path) -> dict[str, Any]:
    events = read_jsonl(path)
    spans = [event for event in events if event.get("event_type") == "span_end"]
    usage = defaultdict(int)
    roles: set[str] = set()
    links = 0
    for span in spans:
        roles.add(str(span.get("role")))
        links += len(span.get("links", []))
        for key, value in dict(span.get("usage", {})).items():
            if isinstance(value, int):
                usage[key] += value
    return {
        "span_count": len(spans),
        "distinct_roles": len(roles),
        "link_count": links,
        "usage": dict(usage),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    rows = read_jsonl(args.results)

    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_condition[str(row["condition"])].append(row)

    report: dict[str, Any] = {"conditions": {}}
    for condition, items in sorted(by_condition.items()):
        successful = [item for item in items if not item.get("error")]
        stats = [trace_stats(Path(item["trace_path"])) for item in successful]
        report["conditions"][condition] = {
            "runs": len(items),
            "successes": len(successful),
            "mean_duration_s": (
                sum(float(item["duration_s"]) for item in successful) / len(successful)
                if successful
                else None
            ),
            "mean_spans": (
                sum(int(item["span_count"]) for item in stats) / len(stats)
                if stats
                else None
            ),
            "mean_distinct_roles": (
                sum(int(item["distinct_roles"]) for item in stats) / len(stats)
                if stats
                else None
            ),
            "mean_links": (
                sum(int(item["link_count"]) for item in stats) / len(stats)
                if stats
                else None
            ),
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
