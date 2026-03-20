# FQL Self-Healing Recovery Layer

*Automatic recovery from reboot, sleep/wake, and silent service death.*
*Effective: 2026-03-20*

---

## Architecture

```
launchd (macOS)
├── ai.openclaw.gateway        — KeepAlive + RunAtLoad (always on)
├── com.fql.claw-control-loop  — RunAtLoad + StartInterval 30m
├── com.fql.watchdog           — RunAtLoad + StartInterval 5m ← NEW
├── com.fql.daily-research     — StartCalendarInterval (weekdays 17:30)
├── com.fql.twice-weekly-research — StartCalendarInterval (Tue/Thu 18:00)
└── com.fql.weekly-research    — StartCalendarInterval (Fri 18:30)
```

The **watchdog** is the recovery coordinator. It runs every 5 minutes
and at login. It checks all other services, restarts failed ones, and
catches up missed scheduled jobs.

---

## Recovery Scenarios

### Scenario 1: Machine Reboots

| Event | Recovery |
|-------|----------|
| macOS starts | launchd loads all agents at login |
| `ai.openclaw.gateway` | `KeepAlive=true` + `RunAtLoad=true` — starts immediately |
| `com.fql.claw-control-loop` | `RunAtLoad=true` — fires immediately, then every 30m |
| `com.fql.watchdog` | `RunAtLoad=true` — fires immediately, validates everything |
| Scheduled jobs (daily, etc.) | `StartCalendarInterval` jobs fire on next schedule hit. If time was missed, watchdog catches up |

### Scenario 2: Machine Sleeps and Wakes

| Event | Recovery |
|-------|----------|
| Wake from sleep | `StartInterval` timers fire if interval has elapsed during sleep |
| Watchdog fires | Checks claw loop log freshness — if stale, kickstarts |
| Scheduled jobs | `StartCalendarInterval` fires only on next matching time. Watchdog detects missed runs and catches up |

### Scenario 3: Gateway Silently Dies

| Event | Recovery |
|-------|----------|
| Gateway process exits | `KeepAlive=true` — launchd restarts immediately (ThrottleInterval=1s) |
| If launchd restart fails | Watchdog detects health endpoint down within 5 minutes |
| Watchdog action | `launchctl kickstart -k` the gateway, verify health |
| If repeated failures | Exponential backoff: 1m, 2m, 4m, 8m, 16m. Stops at 5 consecutive failures. |

### Scenario 4: Claw Control Loop Hangs or Fails

| Event | Recovery |
|-------|----------|
| Loop exits with error | launchd refires at next 30m interval |
| Loop hangs (no exit) | Lock file prevents duplicate runs. Watchdog detects stale logs after 45m. |
| Watchdog action | Kickstarts claw-control-loop, verifies fresh log appears |

### Scenario 5: Scheduled Research Job Missed

| Event | Recovery |
|-------|----------|
| Daily job missed (machine was asleep at 17:30) | Watchdog checks after 18:30: if no daily log today, fires catch-up |
| Twice-weekly job missed | Same pattern: watchdog checks after 19:00 on Tue/Thu |
| Weekly job missed | Same pattern: watchdog checks after 20:00 on Friday |

---

## Backoff Logic

Prevents restart thrashing when a service is genuinely broken (bad
config, missing dependency, corrupt state).

```
Failure 1 → retry immediately
Failure 2 → wait 1 minute
Failure 3 → wait 2 minutes
Failure 4 → wait 4 minutes
Failure 5 → EXHAUSTED — stop retrying, log for manual attention
```

State tracked in `research/logs/.watchdog_state.json`. Resets to zero
on any successful recovery.

---

## Services

### Watchdog (NEW)

| Field | Value |
|-------|-------|
| Label | `com.fql.watchdog` |
| Plist | `~/Library/LaunchAgents/com.fql.watchdog.plist` |
| Script | `scripts/fql_watchdog.sh` |
| Schedule | Every 5 minutes + RunAtLoad |
| Logs | `research/logs/watchdog_YYYYMMDD.log` (daily rotation, 14-day retention) |
| Recovery audit trail | `research/logs/recovery_actions.log` (persistent, auto-truncated at 1MB) |

### Claw Control Loop (UPDATED)

| Field | Value |
|-------|-------|
| Label | `com.fql.claw-control-loop` |
| Change | Added `RunAtLoad=true` — fires immediately on boot/login |

### OpenClaw Gateway (UNCHANGED)

Already has `KeepAlive=true` and `RunAtLoad=true`. No changes needed.
ThrottleInterval=1s provides near-instant restart.

---

## Watchdog Checks

| Check | Threshold | Action on Failure |
|-------|-----------|-------------------|
| Gateway process exists | PID in `launchctl list` | `kickstart -k` |
| Gateway health endpoint | `GET /health` returns `{"ok":true}` within 5s | `kickstart -k` |
| Claw loop log freshness | Most recent `claw_loop_*.log` < 45 minutes old | `kickstart` |
| EOD audit freshness | Most recent `brief_*.md` or `audit_*.md` < 26 hours old | Informational only |
| Daily research (weekdays) | Log exists for today after 18:30 | `kickstart` daily research |
| Twice-weekly (Tue/Thu) | Log exists for today after 19:00 | `kickstart` twice-weekly |
| Weekly (Fri) | Log exists for today after 20:00 | `kickstart` weekly |

---

## Log Files

| File | Purpose | Retention |
|------|---------|-----------|
| `research/logs/watchdog_YYYYMMDD.log` | Per-run check results | 14 days |
| `research/logs/recovery_actions.log` | Persistent recovery audit trail | Auto-truncated at 1MB |
| `research/logs/.watchdog_state.json` | Backoff state (failures per component) | Persistent, auto-clears on success |
| `research/logs/launchd_watchdog_stdout.log` | launchd stdout capture | Grows until truncated |
| `research/logs/launchd_watchdog_stderr.log` | launchd stderr capture | Grows until truncated |

---

## Manual Test Plan

### Test 1: Simulate Reboot

```bash
# Unload all FQL services
for label in com.fql.watchdog com.fql.claw-control-loop com.fql.daily-research com.fql.twice-weekly-research com.fql.weekly-research; do
    launchctl bootout gui/$(id -u)/$label 2>/dev/null
done

# Verify all stopped
launchctl list | grep fql

# Reload all (simulates login)
for plist in ~/Library/LaunchAgents/com.fql.*.plist; do
    launchctl bootstrap gui/$(id -u) "$plist"
done

# Check: claw-control-loop should fire immediately (RunAtLoad)
sleep 10
ls -lt ~/projects/Algo\ Trading/algo-lab/research/logs/claw_loop_*.log | head -1

# Check: watchdog should fire and report all healthy
cat ~/projects/Algo\ Trading/algo-lab/research/logs/watchdog_$(date +%Y%m%d).log
```

### Test 2: Simulate Gateway Death

```bash
# Kill the gateway process
kill $(launchctl list | grep ai.openclaw.gateway | awk '{print $1}')

# Wait for KeepAlive restart (should be immediate)
sleep 3
curl -s http://localhost:18789/health
# Expected: {"ok":true,"status":"live"}

# If KeepAlive didn't restart it, wait for watchdog (up to 5 minutes)
# Or manually trigger watchdog:
bash ~/projects/Algo\ Trading/algo-lab/scripts/fql_watchdog.sh
cat ~/projects/Algo\ Trading/algo-lab/research/logs/watchdog_$(date +%Y%m%d).log | tail -20
```

### Test 3: Simulate Stale Claw Loop

```bash
# Touch an old claw loop log to make it look stale (don't do this if real loop is running)
# Instead, just wait 45+ minutes without the loop running, then:
bash ~/projects/Algo\ Trading/algo-lab/scripts/fql_watchdog.sh
# Expected: detects stale loop, kickstarts it, verifies fresh log

# Check recovery log
cat ~/projects/Algo\ Trading/algo-lab/research/logs/recovery_actions.log
```

### Test 4: Simulate Missed Daily Research

```bash
# On a weekday after 18:30, if daily_run log doesn't exist for today:
bash ~/projects/Algo\ Trading/algo-lab/scripts/fql_watchdog.sh
# Expected: detects missing daily run, fires catch-up
```

### Test 5: Verify Backoff Prevents Thrashing

```bash
# Temporarily break the gateway (e.g., wrong port in health check)
# Run watchdog 6 times rapidly:
for i in $(seq 6); do
    bash ~/projects/Algo\ Trading/algo-lab/scripts/fql_watchdog.sh
    sleep 2
done
# Expected: first few attempts retry, then backoff kicks in, then EXHAUSTED

# Check backoff state
cat ~/projects/Algo\ Trading/algo-lab/research/logs/.watchdog_state.json | python3 -m json.tool

# Reset backoff state to recover
rm ~/projects/Algo\ Trading/algo-lab/research/logs/.watchdog_state.json
```

### Test 6: Verify Sleep/Wake Recovery

```bash
# Put machine to sleep for 35+ minutes (past one claw loop interval)
# On wake:
#   1. claw-control-loop should fire (StartInterval elapsed during sleep)
#   2. watchdog should fire within 5 minutes and verify everything
# Check:
tail -20 ~/projects/Algo\ Trading/algo-lab/research/logs/watchdog_$(date +%Y%m%d).log
ls -lt ~/projects/Algo\ Trading/algo-lab/research/logs/claw_loop_*.log | head -3
```

---

## Operational Notes

- **The watchdog does not replace launchd.** launchd's `KeepAlive` and
  `StartInterval` are the primary recovery mechanism. The watchdog is a
  second layer that catches cases launchd misses (health check failures,
  stale logs, missed calendar jobs after sleep).

- **The watchdog is read-only for strategy state.** It never modifies the
  registry, account state, or strategy files. It only restarts services
  and logs recovery actions.

- **Backoff state auto-clears.** When a service recovers successfully,
  its failure counter resets to zero. You only need to manually clear
  `.watchdog_state.json` if a service was genuinely broken and you've
  fixed the underlying issue.

- **Recovery actions are auditable.** `research/logs/recovery_actions.log`
  is a persistent, append-only trail of every automated recovery. Review
  this during weekly Friday reviews to identify systemic reliability
  issues.
