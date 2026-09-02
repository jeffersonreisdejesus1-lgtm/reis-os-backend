# Notion → Obsidian mirror

This automation keeps a derived Markdown mirror of the REIS OS Evolution Cores in `obsidian-mirror/`.

## Authority boundary

- Notion remains canonical.
- GitHub/Markdown/Obsidian are derived, noncanonical mirrors.
- The job never writes back to Notion.
- The job does not alter OCS authority, Constitution, state root, or Evolution Core records.

## Pages mirrored

The configuration in `config/notion_obsidian_pages.json` contains the ten OCS Evolution Cores plus the Institutional Evolution Core.

## Required GitHub secret

Create one Actions repository secret named `NOTION_TOKEN` containing a Notion integration token that has read access to the configured Evolution Core pages.

## Schedule

`.github/workflows/notion-obsidian-mirror.yml` runs once per hour and can also be run manually with `workflow_dispatch`.

When Markdown changes, the workflow commits only `obsidian-mirror/`. If nothing changed in Notion, it creates no commit.

## Obsidian

Point the Android/desktop vault synchronization mechanism at the repository or copy/sync the `obsidian-mirror/` directory into the vault. `REIS OS.md` is the central graph note and links to all ten OCS notes.
