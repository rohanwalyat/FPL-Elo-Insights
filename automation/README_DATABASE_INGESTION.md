# FPL Database Ingestion Automation

This automation system automatically imports FPL data from your local data folder into PostgreSQL database.

## Overview

The database ingestion automation handles:
- **2025-2026 season data** (By Gameweek format)
- **Main season data**: players, teams, matches, playermatchstats
- **Draft league data**: managers, picks, leagues
- **Intelligent column mapping** for schema compatibility
- **Data type conversion** and null value handling
- **Incremental updates** without data loss

## Components

### 1. `database_ingestion.py`
Main Python script that:
- Automatically detects latest season data (finds highest gameweek with complete data)
- Handles both main season and draft league data
- Performs intelligent column mapping between CSV and database schemas
- Converts data types and handles null values properly
- Provides detailed logging and import summaries

### 2. `run_database_ingestion.sh`
Shell wrapper script that:
- Checks all prerequisites (PostgreSQL, Python, data files)
- Activates virtual environment automatically
- Installs missing dependencies
- Runs the ingestion with proper logging
- Provides database summary after completion

## Quick Usage

### Run Database Ingestion Once
```bash
cd automation
./run_database_ingestion.sh
```

### Run Python Script Directly
```bash
# From project root
source fpl-venv/bin/activate
python automation/database_ingestion.py
```

## Data Detection Logic

The script automatically finds:

### Season Data (2025-2026)
- **Teams**: `data/2025-2026/teams.csv`
- **Players**: `data/2025-2026/players.csv`
- **Latest Gameweek**: Highest numbered `data/2025-2026/By Gameweek/GW*/`
  - `matches.csv` - Match results and statistics
  - `playermatchstats.csv` - Player performance data

### Draft League Data
- **Latest Draft Data**: `data/draft_league/latest/`
  - `managers.csv` - Draft league managers
  - `picks.csv` - Player ownership in draft league
  - `players.csv`, `teams.csv`, `standings.csv` (additional context)

## Database Schema Compatibility

The script handles differences between CSV data and database schema:

### Column Mapping
- Maps new CSV columns to existing database columns
- Skips columns that don't exist in database (e.g., new distance tracking data)
- Adds default values for missing columns

### Data Type Conversion
- **Decimal fields**: `xg`, `xa`, `xgot`, `xgot_faced`, `goals_prevented`
- **Integer fields**: All other numeric columns
- **Boolean fields**: `finished` in matches table
- **Percentage fields**: Converted from float percentages to integers

### Null Value Handling
- Replaces null values with appropriate defaults (0 for numbers, None for optional fields)
- Handles empty strings and NaN values properly

## Prerequisites

1. **PostgreSQL Database**
   - Database named `fpl_elo` must exist
   - Tables must be created (teams, players, matches, playermatchstats, draft_*)
   - Connection credentials in `.env` file

2. **Environment Setup**
   - Virtual environment with required packages
   - Environment variables in `.env` file:
     ```
     PGHOST=localhost
     PGPORT=5432
     PGDATABASE=fpl_elo
     PGUSER=postgres
     PGPASSWORD=your_password
     ```

3. **Data Files**
   - FPL season data in correct folder structure
   - Draft league data (if applicable)

## Automation Options

### Manual Execution
```bash
./automation/run_database_ingestion.sh
```

### Scheduled Execution (Cron)
Add to crontab for automatic updates:
```bash
# Run every 6 hours during active season
0 */6 * * * cd /path/to/fpl-elo-insights && ./automation/run_database_ingestion.sh

# Run daily at 8 AM during off-season
0 8 * * * cd /path/to/fpl-elo-insights && ./automation/run_database_ingestion.sh
```

### Integration with Data Updates
Combine with data fetching scripts:
```bash
# Update draft league data then import to database
python scripts/simple_draft_fetch.py
./automation/run_database_ingestion.sh
```

## Logging and Monitoring

### Log Files
- **Location**: `logs/database_ingestion.log`
- **Format**: Timestamped messages with levels (INFO, ERROR)
- **Content**: Prerequisites checks, data detection, import progress, errors

### Import Summary
After each run, the script provides:
- Records imported per table
- Total records processed
- Any errors encountered
- Database summary (final counts)

## Troubleshooting

### Database Connection Issues
```bash
# Test connection manually
psql -U postgres -d fpl_elo

# Check if PostgreSQL is running
ps aux | grep postgres
```

### Missing Data Files
```bash
# Check data structure
ls -la data/2025-2026/
ls -la data/2025-2026/By\ Gameweek/
ls -la data/draft_league/latest/
```

### Python Environment Issues
```bash
# Activate virtual environment
source fpl-venv/bin/activate

# Install missing packages
pip install pandas psycopg2-binary python-dotenv
```

### Data Type Errors
- Check CSV files for unexpected values
- Look for very large numbers that exceed integer limits
- Verify percentage fields are reasonable (0-100)

## Advanced Usage

### Custom Data Paths
Modify `database_ingestion.py` to change data paths:
```python
# Change season folder
season_folders = ['2025-2026', '2024-2025', 'your-custom-season']

# Change draft league path
draft_path = self.data_path / "your_draft_folder" / "latest"
```

### Schema Changes
When database schema changes:
1. Update column lists in the script
2. Add new data type handling if needed
3. Test with sample data first

### Selective Import
To import only specific data types, modify the `run_ingestion()` method:
```python
# Only import season data
if season_data:
    self.import_season_data(season_data)

# Skip draft data import
# if draft_data:
#     self.import_draft_data(draft_data)
```

## Integration with Existing Automation

This script complements the existing GitHub-based automation:

1. **GitHub Update**: `./automation/run_github_update.sh`
   - Pulls latest data from your fork
   - Updates CSV files

2. **Database Ingestion**: `./automation/run_database_ingestion.sh`
   - Imports updated CSV files to database
   - Handles new data format

3. **Combined Workflow**:
   ```bash
   # Full update sequence
   ./automation/run_github_update.sh
   ./automation/run_database_ingestion.sh
   ```

## Benefits

- ✅ **Automatic data detection** - Finds latest gameweek data
- ✅ **Schema compatibility** - Handles column differences gracefully  
- ✅ **Robust data handling** - Converts types and handles nulls
- ✅ **Comprehensive logging** - Full visibility into import process
- ✅ **Draft league support** - Imports fantasy draft data
- ✅ **Error recovery** - Continues on non-critical errors
- ✅ **Database safety** - Uses transactions and proper error handling