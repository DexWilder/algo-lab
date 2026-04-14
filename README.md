# algo-lab

> **`CLAUDE.md` is the authoritative operating document for this repo.**
> For current system state, active probation strategies, automation, and
> operating rhythm, read `CLAUDE.md` first. This README covers only
> quick-start setup and repo layout and is not kept in sync with live
> operational state.

Algo factory: TradingView Pine scripts → Python strategies → backtesting + prop firm evaluation.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API key
cp .env.example .env
# Edit .env with your FMP API key

# Fetch data
python data/fetch_fmp.py --symbol MES --days 30

# Run pipeline
python run_all.py
```

## Project Structure

```
strategies/         Strategy directories (Pine + Python + meta.json)
engine/             Core engine modules (backtest, metrics, scoring)
data/               Market data (CSV) + fetcher script
results/            Pipeline output (master.csv, ranked.csv)
docs/               Contracts, templates, roadmap
prompts/            LLM prompt templates for Pine→Python conversion
```

## Adding a Strategy

1. Create `strategies/<name>/` with `strategy.pine`, `strategy.py`, `meta.json`
2. Follow the contract in `docs/strategy_python_contract.md`
3. Use `prompts/pine_to_python_prompt.md` as the LLM conversion template
4. Run `python run_all.py --strategy <name>` to test

## Current Status

See `CLAUDE.md` — the authoritative operating document. This README does
not track live system state.
