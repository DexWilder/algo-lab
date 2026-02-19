# Data Contract

## Input Data Format

All strategy and engine code expects OHLCV data as a pandas DataFrame with the following schema:

| Column   | Type              | Description                        |
|----------|-------------------|------------------------------------|
| datetime | datetime64[ns]    | Bar timestamp (bar close time)     |
| open     | float64           | Opening price                      |
| high     | float64           | High price                         |
| low      | float64           | Low price                          |
| close    | float64           | Closing price                      |
| volume   | int64 / float64   | Volume traded                      |

### Rules

1. **Index**: DataFrame must use a default integer index (not datetime index)
2. **Sorting**: Rows must be sorted ascending by `datetime` (oldest first)
3. **No NaN in OHLC**: `open`, `high`, `low`, `close` must not contain NaN values
4. **Column names**: Must be lowercase exactly as shown above
5. **Timezone**: All timestamps should be in US/Eastern (exchange time)

## CSV File Format

When stored as CSV (e.g., `data/MES_5m.csv`):

```csv
datetime,open,high,low,close,volume
2025-01-02 09:30:00,5020.25,5022.50,5019.00,5021.75,1234
2025-01-02 09:35:00,5021.75,5025.00,5021.00,5024.50,987
```

- Date format: `YYYY-MM-DD HH:MM:SS`
- No index column in CSV
- Header row required

## Validation

`engine.io.load_data()` validates all of the above on load and raises `ValueError` with a descriptive message if any check fails.
