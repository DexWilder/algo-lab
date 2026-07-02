# Databento Transient-Failure Retry Policy (2026-07-02)

> Provider flakiness (504 gateway timeout / connection reset) is NOT `DATA_BLOCKED` and NOT "I'll be notified." It is a
> durable, tracked state. State machine: RUN_NOW → (fail) → `RUN_NOW_PENDING_PROVIDER_HEALTH` → (N fails) →
> `PROVIDER_UNSTABLE_RETRY_LATER`. Never hammer the provider; never idle waiting — bypass to the next unblocked lane.

## Request scope (avoid the timeout in the first place)
- **Max scope per request:** 1 parent symbol × 1 month (statistics) or 1 quarter (definition). Larger 504s.
- Pull `definition` per-parent per-month (not multi-month); filter `statistics` to the needed `stat_type` on ingest.
- **Persist partial successes** immediately (append per-parent-per-month); dedup on save.

## Retry policy
1. Per (parent, month): up to **4 attempts**, exponential-ish backoff (sleep 2→4→8s).
2. If a chunk still fails after 4 attempts → skip it, log to `provider_retry_state.json`, continue other chunks.
3. If **>50% of chunks fail** → classify the whole pull `PROVIDER_UNSTABLE_RETRY_LATER`, stop, do NOT re-hammer.
4. Retry the failed slices in the **next healthy-gateway window** (next cycle), not in a tight loop.
5. Fallback: narrow to single-parent/single-week slices before giving up.

## On every landed file
- `validate_data_file` (rows>0, dates parse, expected columns);
- record path/schema/row-count/cost/date-range to `data_budget.json` pulls[];
- update `data_sources.json` status;
- update the queue item to RUN_NOW (runnable).

## Do-not-idle rule
While a pull is `RUN_NOW_PENDING_PROVIDER_HEALTH`, the runner MUST execute the next unblocked RUN_NOW lane
(spreadMR_GC exec-realism / event-surprise inventory / forced-flow source packet / T4-T5 local tests). No waiting on the shell.

## Classification (never conflate)
- `TRANSIENT_PROVIDER_FAILURE_RETRY_QUEUED` — some chunks failed, retry queued.
- `RUN_NOW_PENDING_PROVIDER_HEALTH` — queue item needs data that's mid-retry.
- `PROVIDER_UNSTABLE_RETRY_LATER` — repeated failure; defer to next window.
- NONE of these are `DATA_BLOCKED` (that requires a certificate proving data is unavailable/paid).
