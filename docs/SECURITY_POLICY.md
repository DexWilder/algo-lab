# FQL Security & Sharing Policy

*Rules for handling FQL intellectual property and credentials.*
*Last updated: 2026-03-16*

---

## Classification

### GREEN — Share freely

- High-level architecture and roadmap
- Generic strategy family descriptions (e.g., "breakout," "mean reversion")
- Public-source research notes and references
- Result summaries (e.g., "PF 1.58 on 6J")
- Workflow plans, prompts, operating rhythm
- Non-sensitive documentation structure

### YELLOW — Share carefully, minimum necessary

- Exact strategy entry/exit rules
- Parameter values and thresholds
- Portfolio construction and allocation logic
- Validation battery thresholds and criteria
- Registry contents and strategy metadata
- Source code fragments
- Controller scoring weights and config

Only share when the specific task requires it.
Prefer summaries over full dumps.
Redact file paths and account-specific details when possible.

### RED — Never share in chat tools

- API keys (Databento, FMP, broker)
- Broker credentials and account IDs
- Exchange logins
- SSH keys and private repo tokens
- `.env` file contents
- Anything that grants data access, trading access, or repo cloning

---

## Operating Rules

1. **Secrets stay local.** `.env`, credentials, and keys never leave the machine.
2. **Share minimum context.** Paste the needed function, not the whole file.
3. **Redact before pasting.** Remove paths, account IDs, and sensitive thresholds.
4. **Repo is the source of truth.** Chat is a workspace, not a vault.
5. **No full IP dumps.** Don't paste entire strategy libraries unless the task requires it.
6. **Treat chats as ephemeral.** Anything pasted into ChatGPT, Claude, or any LLM should be assumed non-private.

---

## For AI Assistant Usage

Use AI tools as:
- Reasoning and architecture layer
- Code review and debugging
- Spec writing and documentation
- Research analysis

Not as:
- Secret storage
- Full IP warehouse
- Place to dump entire private repos

---

## Credential Locations

| Secret | Location | Backed Up? |
|--------|----------|-----------|
| Databento API key | `.env` (gitignored) | No — regenerable from Databento dashboard |
| FMP API key | `.env` (gitignored) | No — regenerable |
| GitHub token | System keychain | N/A |
| Broker credentials | Not yet configured | N/A |

---

## Incident Response

If a credential is accidentally exposed:
1. Rotate the key immediately (regenerate from provider dashboard)
2. Update `.env` locally
3. Check git history — if committed, use `git filter-branch` or BFG to purge
4. Verify the exposed key is revoked
