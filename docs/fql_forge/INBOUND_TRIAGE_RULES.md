# Inbound Triage Rules (2026-07-01)

> How every inbound item is classified the moment it lands. Defaults are FAIL-CLOSED: an item stays in its "not done yet"
> state (and the guardrail keeps nagging) until the specific completion condition is met. Source of truth:
> `research/data/inbound_research_ledger.json`. Capture: `research/capture_inbound.py`. Enforced by `forge_system_guardrails.py`.

| Inbound type | Default status | Completion condition (moves it forward) |
|---|---|---|
| **operator directive** | P0/P1, NEW → not "operationalized" | operationalized = linked to a control/queue/packet. Guardrail flags directives with none. |
| **data feed** | INVENTORIED_UNUSED | attached to a packet lane (status ACTIVE_PACKET_LANE + linked_packet). Guardrail flags unused feeds. |
| **bug / mistake** | CONTROL_REQUIRED | a durable control exists (linked_control: guardrail/test/checklist/status-correction). "No durable control = not fixed." |
| **validation failure** | RETEST_REQUIRED / CONTROL_REQUIRED | retest under truth-gated harness, or a control that prevents recurrence. |
| **strategy idea** | PACKET_REQUIRED | has mechanism + family + required_data + required_harness + kill criteria (then PROMOTED_TO_PACKET). |
| **source note** (book/podcast/video/article/Reddit) | NEW | produces ≥1 mechanism packet (PROMOTED_TO_PACKET) OR is archived. A source note that does neither is useless — guardrail flags it. |
| **DATA_BLOCKED claim** | DATA_STATUS_UNPROVEN | a Data Blocker Certificate exists (else it is NOT blocked, just unproven). |
| **paid-data idea** | DATA_STATUS_UNPROVEN | local + provider-access inventory complete AND cost checked; >$5 => operator $ gate. |
| **old WATCH/PASS/KILL** | RETEST_REQUIRED | already truth-gated under current controls, else must be re-run. |
| **guardrail finding** | CONTROL_REQUIRED | machine check added/confirmed (linked_control). |

## Status vocabulary
NEW · TRIAGED · QUEUED · ACTIVE_PACKET_LANE · DATA_STATUS_UNPROVEN · CERTIFIED_BLOCKED · NEEDS_BESPOKE_HARNESS ·
RETEST_REQUIRED · CLEAN_KILL · ARCHIVED_LOW_PRIORITY · PROMOTED_TO_PACKET · INVENTORIED_UNUSED · CONTROL_REQUIRED · PACKET_REQUIRED.

## Operating law
If it is not in the inbound ledger, the queue, the dashboard, or the control map (or explicitly archived), **the system does not know it.** No terminal-only discoveries.

## Flow
inbound ledger → triage → queue → run → report → control map (if mistake) → dashboard → commit/push.
