# Agent Instructions

This repository develops and ships the **commons** agent skill for [Commons](https://ac.gnrl.se). These instructions are for agents *working on this repo*. They are not part of the skill.

## What ships, and what doesn't

| Path | Audience | Ships? |
| --- | --- | --- |
| `skills/commons/` | Agents that install the skill | **Yes**. Installed on its own, without the rest of the repo |
| Everything else (`.beads/`, `tools/`, this file, `CLAUDE.md`) | Contributors to this repo | No |

Rules for anything under `skills/`:

- Keep each skill self-contained. Its links must resolve inside its own directory, and it must not depend on repo-level files.
- Never mention our development tooling: no beads, `bd`, `AGENTS.md` or `CLAUDE.md`. Users of the skill may not use any of it.
- No local absolute paths.
- Repo-wide tooling goes in `tools/`, not in a skill's `scripts/`. A skill's `scripts/` ships to users.

`tools/check_skill_isolation.py` enforces these rules. It runs in the pre-commit hook, and you can also run it directly:

```bash
python3 tools/check_skill_isolation.py
```

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
2. **Run quality gates** (if code changed) - `python3 tools/check_skill_isolation.py`, plus the skill's own scripts against fixtures. If you change the task-summary style guide in SKILL.md, rerun `tools/summary_eval/run.py` (its docstring covers setup)
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
