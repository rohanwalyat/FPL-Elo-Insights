# Draft League Data Organization

This folder contains FPL Draft League data organized for easy access and historical tracking.

## Folder Structure

```
draft_league/
├── latest/                    # Symlinks to most recent data files
│   ├── league_info.json      # Current league information
│   ├── managers.csv          # Current managers/teams
│   ├── picks.csv             # Current player picks/ownership
│   ├── players.csv           # Current player data
│   ├── standings.csv         # Current league standings
│   └── teams.csv             # Current team data
├── archive/                   # Historical data organized by date
│   ├── 2025-08-11/           # Data from August 11th
│   ├── 2025-08-16/           # Data from August 16th
│   └── YYYY-MM-DD/           # Future updates...
└── README.md                 # This file
```

## File Descriptions

### Core Data Files
- **league_info.json**: Basic league metadata (name, ID, draft status, etc.)
- **managers.csv**: Team managers and their information
- **picks.csv**: Player ownership/draft picks for each manager
- **players.csv**: Complete player database with stats and info
- **standings.csv**: Current league standings and records
- **teams.csv**: Premier League team information

### Usage Patterns

**For Scripts & Analysis**: Always use files in `latest/` directory
```sql
-- SQL scripts reference latest data
\copy managers FROM 'data/draft_league/latest/managers.csv'
```

**For Historical Analysis**: Use specific dated folders in `archive/`
```python
# Compare data across dates
aug_11_data = pd.read_csv('archive/2025-08-11/standings_20250811_224812.csv')
aug_16_data = pd.read_csv('archive/2025-08-16/standings_20250816_112340.csv')
```

## Data Updates

When the draft league data is updated:
1. New timestamped files are saved to `archive/YYYY-MM-DD/`
2. Symlinks in `latest/` are automatically updated to point to newest files
3. Scripts and databases always use the latest data seamlessly

## Benefits

✅ **Always Current**: Scripts use latest data without manual path updates  
✅ **Historical Tracking**: All previous versions preserved in archive  
✅ **Easy Access**: Simple paths for both current and historical data  
✅ **Automated**: Symlinks update automatically when new data arrives  

## Scripts

- **Update Data**: `python3 scripts/simple_draft_fetch.py`
- **Import to Database**: `psql -f sql/import_draft_data_clean.sql`