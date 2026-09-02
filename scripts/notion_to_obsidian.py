from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

NOTION_VERSION = "2022-06-28"
API_ROOT = "https://api.notion.com/v1"


def notion_get(path: str, token: str) -> dict[str, Any]:
    req = Request(
        f"{API_ROOT}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=30) as response:  # noqa: S310 - fixed trusted API root
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Notion API {exc.code} for {path}: {body}") from exc


def plain_rich_text(items: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for item in items:
        text = item.get("plain_text", "")
        href = item.get("href")
        chunks.append(f"[{text}]({href})" if href else text)
    return "".join(chunks)


def page_title(page: dict[str, Any], fallback: str) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            title = plain_rich_text(prop.get("title", []))
            if title:
                return title
    return fallback


def list_children(block_id: str, token: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        suffix = f"?page_size=100{f'&start_cursor={cursor}' if cursor else ''}"
        data = notion_get(f"/blocks/{block_id}/children{suffix}", token)
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            return results
        cursor = data.get("next_cursor")
        if not cursor:
            return results


def render_block(block: dict[str, Any], token: str, depth: int = 0) -> list[str]:
    block_type = block.get("type", "")
    payload = block.get(block_type, {}) if isinstance(block.get(block_type), dict) else {}
    rich = plain_rich_text(payload.get("rich_text", []))
    indent = "  " * depth
    lines: list[str] = []

    if block_type == "paragraph":
        lines.append(f"{indent}{rich}" if rich else "")
    elif block_type == "heading_1":
        lines.append(f"{indent}# {rich}")
    elif block_type == "heading_2":
        lines.append(f"{indent}## {rich}")
    elif block_type == "heading_3":
        lines.append(f"{indent}### {rich}")
    elif block_type == "bulleted_list_item":
        lines.append(f"{indent}- {rich}")
    elif block_type == "numbered_list_item":
        lines.append(f"{indent}1. {rich}")
    elif block_type == "to_do":
        mark = "x" if payload.get("checked") else " "
        lines.append(f"{indent}- [{mark}] {rich}")
    elif block_type == "quote":
        lines.append(f"{indent}> {rich}")
    elif block_type == "code":
        language = payload.get("language", "text")
        lines.extend([f"{indent}```{language}", rich, f"{indent}```"])
    elif block_type == "divider":
        lines.append(f"{indent}---")
    elif block_type == "callout":
        lines.append(f"{indent}> {rich}")
    elif block_type == "toggle":
        lines.append(f"{indent}- {rich}")
    elif block_type == "child_page":
        title = payload.get("title", "Untitled")
        lines.append(f"{indent}- [[{title}]]")
    elif block_type == "child_database":
        title = payload.get("title", "Database")
        lines.append(f"{indent}- **Database:** {title}")
    elif block_type in {"bookmark", "link_preview"}:
        url = payload.get("url", "")
        if url:
            lines.append(f"{indent}{url}")
    elif block_type == "equation":
        expression = payload.get("expression", "")
        if expression:
            lines.append(f"{indent}$$ {expression} $$")
    elif rich:
        lines.append(f"{indent}{rich}")

    if block.get("has_children"):
        for child in list_children(block["id"], token):
            lines.extend(render_block(child, token, depth + 1))
    return lines


def render_page(page_cfg: dict[str, Any], token: str) -> str:
    page_id = page_cfg["page_id"]
    page = notion_get(f"/pages/{page_id}", token)
    title = page_title(page, page_cfg["name"])
    body: list[str] = []
    for block in list_children(page_id, token):
        body.extend(render_block(block, token))

    source_url = page.get("url", "")
    last_edited = page.get("last_edited_time", "")
    frontmatter = [
        "---",
        "reis_os_mirror: true",
        "canonical_source: Notion",
        "mirror_authority: derived_noncanonical",
        f"notion_page_id: {page_id}",
        f"notion_last_edited_time: {last_edited}",
        f"notion_url: {source_url}",
        "---",
        "",
        f"# {title}",
        "",
        "[[REIS OS]]",
        "",
        "> Espelho derivado para navegação/visualização. O estado canônico permanece no Notion.",
        "",
    ]
    compact: list[str] = []
    blank = False
    for line in frontmatter + body:
        if line.strip():
            compact.append(line.rstrip())
            blank = False
        elif not blank:
            compact.append("")
            blank = True
    return "\n".join(compact).rstrip() + "\n"


def central_note(config: dict[str, Any]) -> str:
    ocs_pages = [p for p in config["pages"] if p.get("ocs")]
    lines = [
        "---",
        "reis_os_mirror: true",
        "canonical_source: Notion",
        "mirror_authority: derived_noncanonical",
        "---",
        "",
        "# REIS OS",
        "",
        "> Índice derivado. O estado canônico permanece nos Evolution Cores do Notion.",
        "",
        "## OCS",
        "",
    ]
    lines.extend(f"- [[{p['name']}]]" for p in ocs_pages)
    lines.extend(["", "## Institucional", "", "- [[_Institucional]]", ""])
    return "\n".join(lines)


def status_note(successes: list[str], failures: list[tuple[str, str]]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "---",
        "reis_os_mirror: true",
        "canonical_source: Notion",
        "mirror_authority: derived_noncanonical",
        "---",
        "",
        "# Mirror Sync Status",
        "",
        f"Last attempt (UTC): {now}",
        "",
        f"Successful pages: {len(successes)}",
        f"Failed pages: {len(failures)}",
        "",
    ]
    if successes:
        lines.extend(["## Success", ""])
        lines.extend(f"- {name}" for name in successes)
        lines.append("")
    if failures:
        lines.extend(["## Failures", ""])
        for name, error in failures:
            safe = error.replace("\n", " ")[:800]
            lines.append(f"- **{name}**: `{safe}`")
        lines.append("")
    return "\n".join(lines)


def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        print("NOTION_TOKEN is required", file=sys.stderr)
        return 2

    config_path = Path(os.getenv("NOTION_OBSIDIAN_CONFIG", "config/notion_obsidian_pages.json"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir = Path(config.get("output_dir", "obsidian-mirror"))

    changed = 0
    successes: list[str] = []
    failures: list[tuple[str, str]] = []

    for page_cfg in config["pages"]:
        try:
            content = render_page(page_cfg, token)
            successes.append(page_cfg["name"])
            if write_if_changed(output_dir / page_cfg["file"], content):
                changed += 1
                print(f"updated: {page_cfg['file']}")
            else:
                print(f"unchanged: {page_cfg['file']}")
        except Exception as exc:  # diagnostic mirror must leave an auditable status file
            failures.append((page_cfg["name"], str(exc)))
            print(f"failed: {page_cfg['name']}: {exc}", file=sys.stderr)

    if write_if_changed(output_dir / config.get("central_note", "REIS OS.md"), central_note(config)):
        changed += 1
        print("updated: central note")

    if write_if_changed(output_dir / "_SYNC_STATUS.md", status_note(successes, failures)):
        changed += 1
        print("updated: sync status")

    print(f"mirror complete; changed_files={changed}; successes={len(successes)}; failures={len(failures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
