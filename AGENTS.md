# Agent Instructions

This repository develops and ships two agent skills for [Commons](https://ac.gnrl.se): **commons** (the task loop, plus filing feedback) and **commons-maintainer** (triaging feedback about a project). These instructions are for agents *working on this repo*. They are not part of the skills.

## What ships, and what doesn't

| Path | Audience | Ships? |
| --- | --- | --- |
| `plugins/<name>/skills/<name>/` | Agents that install the skill | **Yes**. Each skill is installed on its own, without the rest of the repo |
| `.claude-plugin/`, `.agents/plugins/` | Claude Code and Codex marketplaces | Read by installers, not installed |
| Everything else (`.beads/`, `tools/`, `docs/`, this file, `CLAUDE.md`, `COMMONS.md`) | Contributors and readers of this repo | No |

Rules for anything under `plugins/`:

- Keep each skill self-contained. Its links must resolve inside its own directory, and it must not depend on repo-level files.
- Never mention our development tooling: no beads, `bd`, `AGENTS.md` or `CLAUDE.md`. Users of the skill may not use any of it.
- No local absolute paths, symlinks, executable bits or CRLF line endings. Installers don't preserve the first three consistently, and `scripts/version.py` hashes the skill directory the way git does, so every byte must match the repository.
- A plugin directory contains only `skills/`. Don't add a `plugin.json`: the marketplace entries carry the metadata, and Codex builds a manifest from its entry.
- Repo-wide tooling goes in `tools/`, not in a skill's `scripts/`. A skill's `scripts/` ships to users.

The pre-commit hook runs both checks, and you can also run them directly:

```bash
python3 tools/check_skill_isolation.py   # nothing leaks into a shipped skill
python3 tools/check_packaging.py         # every install route finds every skill; shared copies match
```

## Shared files

Some files exist in both skills, because each skill installs alone and links don't survive installers. The source of truth is `plugins/commons/skills/commons/`. Edit there, then run `python3 tools/sync_shared.py` to copy into the other skills. The list is in that script, and `check_packaging.py` fails if a copy drifts.

## Packaging and releases

Users install from `gnrlse/commons-skills`; README.md has the commands.

- **Layout:** each skill is at `plugins/<name>/skills/<name>/SKILL.md`, the standard plugin layout. Don't go back to a plugin root that is itself the skill. Claude Code loads that layout, but Codex doesn't find it (Commons entry baad75331bba944aab566259ef5b0ea5).
- **Claude Code** reads `.claude-plugin/marketplace.json`. Check it with `claude plugin validate .`.
- **Codex** reads `.agents/plugins/marketplace.json` and ignores the Claude file whenever this one exists. Keep the two files listing the same plugins and sources; `check_packaging.py` compares them.
- **The skills CLI** (`npx skills add`) searches `<source>/skills/` for each local plugin entry in the Claude marketplace file.
- **claude.ai and Claude Desktop:** `tools/build_zip.py` builds `dist/<skill>.zip` for each skill. Pushing a `v*` tag runs `.github/workflows/release.yml`, which attaches the zips to a GitHub release, so the README's `releases/latest/download/<skill>.zip` links always point at the newest ones.
- **Versions:** leave `version` unset in both marketplaces. Claude Code then tracks commits, and Codex reinstalls on `codex plugin marketplace upgrade`.
- **Licenses:** each skill's `LICENSE` duplicates the root LICENSE, because each skill installs without the rest of the repo.

## Maintaining this project on Commons

Feedback about these skills arrives on Commons, labelled `software=https://github.com/gnrlse/commons-skills`. Triage it with the maintainer skill from this checkout:

```bash
python3 plugins/commons-maintainer/skills/commons-maintainer/scripts/inbox.py --software https://github.com/gnrlse/commons-skills
```

Every entry published on the project's behalf goes into `COMMONS.md` under "Maintainer entries", in a commit pushed after publishing. That list is how readers verify a reply came from the maintainers. Publishing still needs the user's approval for each entry. The reasoning behind these conventions is in `docs/feedback-design.md`.

## Issue tracking with beads

We track our own work with **bd** (beads). Issues live in a local Dolt database under `.beads/`. `.beads/issues.jsonl` is a passive export, not the source of truth. Use bd for all task tracking. Do not use markdown TODO lists.

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
bd prime              # Full workflow context and command reference
```

Load beads context into your agent with a user-level setup such as `bd setup claude --global`, not a project-level one. Do not commit bd's per-tool integrations (`.agents/skills/beads/`, `.claude/settings.json`, `.codex/`, `.cursor/`). The `.agents/skills/beads/` skill would be found by installers that scan this repo for skills, and it would ship alongside commons.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - `python3 tools/check_skill_isolation.py` and `python3 tools/check_packaging.py`, plus the skills' own scripts against fixtures. If you change the task-summary style guide in SKILL.md, rerun `tools/summary_eval/run.py` (its docstring covers setup)
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push          # once a Dolt remote is configured
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
