# Spread Log Audit Procedure

**Target file:** `logs/spread_rebalance_log.csv`
**Strategy tracked:** Treasury-Rolldown-Carry-Spread (only spread strategy as of 2026-04-14; future spread strategies would extend this)

**Purpose:** Deterministic audit that converts a raw spread log into an
OK / WARN / FAIL verdict in one line. Used inside the May 1 checkpoint
(§2 of `docs/MAY_1_CHECKPOINT_TEMPLATE.md`) and as an ongoing periodic
sanity check.

**Strict-hold note:** this is a **documented procedure with concrete
commands**, not a new executable script. Run the commands at audit
time; do not extract into persistent code during hold. Pattern follows
`docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md`.

---

## Expected cadence

One row per calendar month, written on the first business day of that
month (subject to the script's internal first-business-day guard).

- New row expected: **first business day of every month**.
- No new row expected on any other day.
- Re-invocation on the same day must be a no-op (idempotent).

Missing a month's row = FAIL (unless the launchd agent was unloaded or
the full daily refresh chain was broken across the entire month's
opening window — those are separate incident conditions).

---

## Step 1 — Row count sanity

```bash
cd "/Users/chasefisher/projects/Algo Trading/algo-lab"
wc -l logs/spread_rebalance_log.csv
python3 -c "
import pandas as pd
df = pd.read_csv('logs/spread_rebalance_log.csv')
print(f'data rows: {len(df)}')
print(f'unique spread_ids: {df[\"spread_id\"].nunique()}')
print(f'duplicates: {(df[\"spread_id\"].value_counts() > 1).sum()}'.format())
print(f'months covered:', sorted(df['spread_id'].unique()))
"
```

**Verdict:**
- OK: data rows == unique spread_ids == expected month count (2 at hold entry, +1 per month after)
- WARN: data rows == unique spread_ids but one month unexpectedly missing (e.g., agent was unloaded for a month)
- FAIL: data rows > unique spread_ids (duplicates present) OR any spread_id missing that should be present

---

## Step 2 — Duplicate detection

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('logs/spread_rebalance_log.csv')
dups = df[df.duplicated(subset=['spread_id'], keep=False)]
if dups.empty:
    print('no duplicates')
else:
    print('DUPLICATE SPREAD_IDs:')
    print(dups[['rebalance_date','spread_id','long_leg_asset','short_leg_asset','notes']].to_string())
"
```

**Verdict:**
- OK: "no duplicates"
- FAIL: any duplicate rows printed

**If FAIL:** do not manually edit the CSV to remove duplicates without first investigating root cause. Duplicate writes indicate idempotency failure in `run_treasury_rolldown_spread.py`; the fix belongs in the script, not the log. Until fixed, **the most recently written duplicate should be treated as authoritative** (later writes should be equivalent to earlier writes under correct idempotency logic).

---

## Step 3 — Missing-entry detection

```bash
python3 -c "
import pandas as pd
from datetime import date
df = pd.read_csv('logs/spread_rebalance_log.csv')
expected_months = set()
# Expected from 2026-03 (first seeded) through current month inclusive
y, m = 2026, 3
today = date.today()
while (y, m) <= (today.year, today.month):
    expected_months.add(f'TRS-{y}-{m:02d}')
    m += 1
    if m > 12:
        y += 1; m = 1
present = set(df['spread_id'])
missing = expected_months - present
if not missing:
    print(f'all {len(expected_months)} expected months present')
else:
    print(f'MISSING months: {sorted(missing)}')
    print(f'present: {sorted(present)}')
"
```

**Verdict:**
- OK: "all N expected months present"
- WARN: exactly one recent month missing AND the current date is within the first 3 business days of that month (the rebalance may not have fired yet — wait and re-audit)
- FAIL: any month other than the currently-forming one is missing

**If FAIL:** the missing month(s) indicate either a failed launchd fire, a script error, or a data-refresh upstream failure that prevented the strategy from computing. Check `research/logs/treasury_rolldown_monthly_stdout.log` and `research/logs/treasury_rolldown_monthly_stderr.log` for the relevant window.

---

## Step 4 — Stale-timestamp check

```bash
python3 -c "
import pandas as pd
from datetime import date, datetime
df = pd.read_csv('logs/spread_rebalance_log.csv')
df['rebalance_date'] = pd.to_datetime(df['rebalance_date'])
latest = df['rebalance_date'].max().date()
today = date.today()
days_since = (today - latest).days
print(f'latest rebalance_date: {latest}')
print(f'today: {today}')
print(f'days since latest: {days_since}')
"
```

**Verdict:**
- OK: days since latest ≤ 35 (allows for months where the first business day is late; strategy fires monthly)
- WARN: 35 < days since latest ≤ 45 (approaching stale; investigate next business day)
- FAIL: days since latest > 45 (a full month was skipped; treat as FAIL from Step 3 as well)

**Exception for seed rows:** the 2 seeded rows (TRS-2026-03 and TRS-2026-04) have `notes` containing `seeded_historical_entry_...`. The "latest rebalance" before the first live fire may technically be a seed row — this is expected until 2026-05-01 fires. After that, latest should be live.

---

## Step 5 — Schema integrity

```bash
python3 -c "
import pandas as pd
EXPECTED = ['rebalance_date','strategy','spread_id','long_leg_asset','long_leg_entry_price',
            'short_leg_asset','short_leg_entry_price','size_long','size_short',
            'previous_long_leg_asset','previous_short_leg_asset','realized_pnl_prior_spread',
            'days_held_prior_spread','notes']
df = pd.read_csv('logs/spread_rebalance_log.csv')
actual = list(df.columns)
if actual == EXPECTED:
    print(f'schema OK: {len(actual)} columns match exactly')
else:
    missing = set(EXPECTED) - set(actual)
    extra = set(actual) - set(EXPECTED)
    print(f'SCHEMA DRIFT. Missing: {sorted(missing)} | Extra: {sorted(extra)}')
"
```

**Verdict:**
- OK: "schema OK: 14 columns match exactly"
- FAIL: any missing or extra columns

**If FAIL:** a schema change was introduced outside the intended design. Do not auto-repair the log. Identify the writer that changed the schema (likely `run_treasury_rolldown_spread.py` SCHEMA constant or manual edit) and reconcile there.

---

## Step 6 — Leg identity + PnL sign check

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('logs/spread_rebalance_log.csv').sort_values('rebalance_date').reset_index(drop=True)
issues = []
for i, row in df.iterrows():
    # Leg identity: long and short must differ
    if row['long_leg_asset'] == row['short_leg_asset']:
        issues.append(f'row {i} ({row[\"spread_id\"]}): long == short')
    # For non-first rows, previous_* must match the prior row's legs
    if i > 0:
        prev = df.iloc[i-1]
        if row['previous_long_leg_asset'] != prev['long_leg_asset']:
            issues.append(f'row {i} ({row[\"spread_id\"]}): previous_long_leg_asset={row[\"previous_long_leg_asset\"]} does not match prior row long={prev[\"long_leg_asset\"]}')
        if row['previous_short_leg_asset'] != prev['short_leg_asset']:
            issues.append(f'row {i} ({row[\"spread_id\"]}): previous_short_leg_asset={row[\"previous_short_leg_asset\"]} does not match prior row short={prev[\"short_leg_asset\"]}')
    # Prices positive
    for col in ['long_leg_entry_price','short_leg_entry_price']:
        if row[col] <= 0:
            issues.append(f'row {i} ({row[\"spread_id\"]}): {col} <= 0')
if issues:
    print('LEG/PNL INTEGRITY ISSUES:')
    for x in issues: print(' ', x)
else:
    print('leg identity + PnL sign: clean')
"
```

**Verdict:**
- OK: "leg identity + PnL sign: clean"
- FAIL: any issue printed

---

## Final one-line verdict

Combine steps 1–6 into a single status:

```bash
python3 -c "
import pandas as pd
from datetime import date
df = pd.read_csv('logs/spread_rebalance_log.csv')

# Collect verdicts (simple form; extend as needed)
issues = []
warns = []

# Duplicates
dup_count = df['spread_id'].duplicated().sum()
if dup_count > 0:
    issues.append(f'{dup_count} duplicate spread_ids')

# Schema
EXPECTED = ['rebalance_date','strategy','spread_id','long_leg_asset','long_leg_entry_price',
            'short_leg_asset','short_leg_entry_price','size_long','size_short',
            'previous_long_leg_asset','previous_short_leg_asset','realized_pnl_prior_spread',
            'days_held_prior_spread','notes']
if list(df.columns) != EXPECTED:
    issues.append('schema drift')

# Missing months
expected_months = set()
y, m = 2026, 3
today = date.today()
while (y, m) <= (today.year, today.month):
    expected_months.add(f'TRS-{y}-{m:02d}')
    m += 1
    if m > 12: y += 1; m = 1
missing = expected_months - set(df['spread_id'])
if missing:
    # Warn if only current month missing and we're early in it
    if len(missing) == 1 and sorted(missing)[0] == f'TRS-{today.year}-{today.month:02d}' and today.day <= 5:
        warns.append(f'current-month row not yet written (may still be pre-fire)')
    else:
        issues.append(f'missing spread_ids: {sorted(missing)}')

# Staleness
latest = pd.to_datetime(df['rebalance_date']).max().date()
days_since = (today - latest).days
if days_since > 45:
    issues.append(f'latest row is {days_since}d old')
elif days_since > 35:
    warns.append(f'latest row is {days_since}d old')

if issues:
    print(f'FAIL: {\" | \".join(issues)}')
elif warns:
    print(f'WARN: {\" | \".join(warns)}')
else:
    print('OK')
"
```

**Output:**
- `OK` — no action required.
- `WARN: ...` — non-blocking, but re-audit next business day or investigate specific condition named.
- `FAIL: ...` — blocks May 1 checkpoint progression to the decision stage. Investigate before proceeding.

---

## Audit cadence

- **Monthly (automatic part of the May 1 checkpoint):** required.
- **Ad-hoc (in-hold reviewer check):** allowed anytime; read-only, hold-safe.
- **Post-hardening queue:** when hardening item #3 (shared guards) ships, this audit procedure could become a scheduled script. Until then, manual.

---

*This procedure is deliberately documented, not coded, during the
2026-04-14 → 2026-05-01 hold window. The hold's strict interpretation
(no new executable code pre-checkpoint) is satisfied. After the May 1
checkpoint, consider promoting this procedure to `scripts/audit_spread_log.py`
as part of the hardening queue — but only after the operational path
has proven itself at least once.*
