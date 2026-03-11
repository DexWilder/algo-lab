# Algo Lab — Claude Instructions

## Auto-Commit & Push

After completing any phase, task, or meaningful unit of work:
1. `git add` all new and modified files (be specific, no `git add .`)
2. `git commit` with a clear message summarizing what was done
3. `git push origin main`
4. Verify clean working tree with `git status`

Do this automatically — never wait for the user to ask.

## Milestone Snapshots

In addition to normal commits, create milestone tags at major checkpoints.

**When to create a milestone tag:**
- A strategy is promoted to parent
- Portfolio structure materially changes (strategies added/removed, weighting changed)
- A numbered research phase completes
- Deployment infrastructure changes materially
- Risk/weighting/prop simulation logic materially changes

**How:**
```bash
./scripts/create_milestone.sh "v<major>.<minor>-phase<N>-<short-name>" "Description"
```

**Tag format:** `v<major>.<minor>-phase<N>-<short-name>` (e.g., `v0.15-phase15-gold-snapback-parent`)

See `docs/release_workflow.md` for full details.

## General

- Always read files before editing them
- Prefer editing existing files over creating new ones
- Follow existing code patterns and conventions in the repo
