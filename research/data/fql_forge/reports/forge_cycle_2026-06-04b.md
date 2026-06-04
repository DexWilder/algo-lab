# Forge Cycle — 2026-06-04

Authority T1 / Lane B / report-only.

## NFP screens (96 events, canonical 1st-Fri)

| Candidate | n | PF | Median | Max-Yr | Verdict |
|---|---:|---:|---:|---:|---|
| EVT-NFP-MES-Long-30min | 84 | 1.003 | $-0.61 | 4432.7% | KILL (median negative) |
| EVT-NFP-MES-Long-2h | 84 | 0.855 | $13.13 | 0.0% | KILL (PF < 1.15) |
| EVT-NFP-MES-Short-30min | 84 | 0.686 | $-6.87 | 0.0% | KILL (median negative) |
| EVT-NFP-MES-Short-2h | 84 | 1.014 | $-20.61 | 851.8% | KILL (median negative) |
| EVT-NFP-MNQ-Long-30min | 84 | 0.989 | $-2.49 | 0.0% | KILL (median negative) |
| EVT-NFP-MNQ-Long-2h | 84 | 0.866 | $14.01 | 0.0% | KILL (PF < 1.15) |
| EVT-NFP-MNQ-Short-30min | 84 | 0.887 | $-1.99 | 0.0% | KILL (median negative) |
| EVT-NFP-MNQ-Short-2h | 84 | 1.101 | $-18.49 | 151.1% | KILL (median negative) |
| EVT-NFP-ZN-Long-30min | 84 | 0.446 | $-81.22 | 0.0% | KILL (median negative) |
| EVT-NFP-ZN-Long-2h | 84 | 0.872 | $-49.98 | 0.0% | KILL (median negative) |
| EVT-NFP-ZN-Short-30min | 84 | 0.859 | $12.52 | 0.0% | KILL (PF < 1.15) |
| EVT-NFP-ZN-Short-2h | 84 | 0.641 | $-18.73 | 0.0% | KILL (median negative) |
| EVT-NFP-MGC-Long-30min | 84 | 1.279 | $3.76 | 85.5% | ARCHITECTURAL_REJECT (losing era) |
| EVT-NFP-MGC-Long-2h | 84 | 2.321 | $21.76 | 27.2% | WATCH_FOR_DEEP_SCREEN |
| EVT-NFP-MGC-Short-30min | 84 | 0.706 | $-10.24 | 0.0% | KILL (median negative) |
| EVT-NFP-MGC-Short-2h | 84 | 0.407 | $-28.24 | 0.0% | KILL (median negative) |

## CPI screens (96 events, APPROX 13th-bday)

| Candidate | n | PF | Median | Max-Yr | Verdict |
|---|---:|---:|---:|---:|---|
| EVT-CPI-MES-Long-30min | 84 | 0.462 | $-7.49 | 0.0% | KILL (median negative) |
| EVT-CPI-MES-Long-2h | 84 | 0.732 | $-11.24 | 0.0% | KILL (median negative) |
| EVT-CPI-MES-Short-30min | 84 | 1.210 | $0.01 | 102.7% | ARCHITECTURAL_REJECT (losing era) |
| EVT-CPI-MES-Short-2h | 84 | 1.135 | $3.76 | 174.4% | KILL (PF < 1.15) |
| EVT-CPI-MNQ-Long-30min | 84 | 0.680 | $-6.24 | 0.0% | KILL (median negative) |
| EVT-CPI-MNQ-Long-2h | 84 | 0.815 | $-17.99 | 0.0% | KILL (median negative) |
| EVT-CPI-MNQ-Short-30min | 84 | 1.223 | $1.76 | 108.0% | ARCHITECTURAL_REJECT (losing era) |
| EVT-CPI-MNQ-Short-2h | 84 | 1.157 | $13.51 | 90.9% | ARCHITECTURAL_REJECT (losing era) |
| EVT-CPI-ZN-Long-30min | 84 | 0.502 | $-34.35 | 0.0% | KILL (median negative) |
| EVT-CPI-ZN-Long-2h | 84 | 0.470 | $-81.22 | 0.0% | KILL (median negative) |
| EVT-CPI-ZN-Short-30min | 84 | 0.660 | $-34.35 | 0.0% | KILL (median negative) |
| EVT-CPI-ZN-Short-2h | 84 | 1.133 | $12.52 | 143.8% | KILL (PF < 1.15) |
| EVT-CPI-MGC-Long-30min | 84 | 1.218 | $-1.24 | 86.1% | KILL (median negative) |
| EVT-CPI-MGC-Long-2h | 84 | 1.209 | $13.76 | 71.2% | ARCHITECTURAL_REJECT (losing era) |
| EVT-CPI-MGC-Short-30min | 84 | 0.729 | $-5.24 | 0.0% | KILL (median negative) |
| EVT-CPI-MGC-Short-2h | 84 | 0.777 | $-20.24 | 0.0% | KILL (median negative) |

## VOL-expansion screens

| Candidate | n | PF | Median | Max-Yr | Verdict |
|---|---:|---:|---:|---:|---|
| XB-VX-EMA-Ladder-MGC | 210 | 1.204 | $-4.24 | 120.6% | KILL (median negative) |
| XB-VX-EMA-Ladder-MES | 87 | 0.635 | $-9.99 | 0.0% | KILL (median negative) |
| XB-VX-EMA-Ladder-MNQ | 59 | 0.894 | $-9.24 | 0.0% | KILL (median negative) |
| XB-VX-EMA-Ladder-ZN | 71 | 0.311 | $-34.35 | 0.0% | KILL (median negative) |

## MES/ZN half-life retest validation

- baseline signals: 16
- after HL gate: 3
- HL summary: {'median': 35.45117869681181, 'frac_under_24mo': 0.2777777777777778}
- verdict: **GATED_VALIDATED**
