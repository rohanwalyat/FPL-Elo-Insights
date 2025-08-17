# FPL Data Automation System

Complete automation system for keeping your FPL database synchronized with the latest data from the upstream fork.

## 🎯 Overview

This automation system orchestrates the complete end-to-end workflow:

1. **📦 Monitors Upstream Fork** - Checks olbauday/FPL-Elo-Insights for updates
2. **⬇️ Pulls Latest Data** - Downloads new FPL data when available
3. **🏆 Updates Draft League** - Fetches your draft league data from FPL API
4. **🗄️ Database Ingestion** - Imports all data into PostgreSQL
5. **📊 Metabase Resync** - Updates dashboards with new data
6. **🕐 Scheduled Jobs** - Runs automatically at 5:00 AM & 5:00 PM UTC

## 🚀 Quick Start

### 1. Prerequisites

- PostgreSQL database running with `fpl_elo` database
- Python environment with required packages
- Draft League ID configured in `.env` file

### 2. Configure Draft League

```bash
# Quick setup
python scripts/setup_draft_league.py

# Or manually add to .env file
DRAFT_LEAGUE_ID=your_league_id
```

### 3. Run Full Automation

```bash
# One-time full update
python automation/full_update_automation.py

# Set up scheduled jobs (5:00 AM & 5:00 PM UTC)
./automation/install_cron_jobs.sh
```

## 📁 Key Files

### Core Automation
- `full_update_automation.py` - Master automation script
- `database_ingestion.py` - Database import logic
- `run_scheduled_update.sh` - Scheduled update wrapper
- `install_cron_jobs.sh` - Cron job installation

### Helper Scripts
- `../scripts/setup_draft_league.py` - Configure draft league ID
- `../scripts/simple_draft_fetch.py` - Manual draft data fetch
- `metabase_resync.py` - Metabase database sync

## 🗄️ Database Ingestion

### What Gets Imported

**Main FPL Data:**
- `players.csv` → `players` table
- `teams.csv` → `teams` table  
- `fixtures.csv` → `matches` table
- `playermatchstats.csv` → `playermatchstats` table

**Draft League Data:**
- `managers.csv` → `draft_managers` table
- `picks.csv` → `draft_picks` table
- League info → `draft_leagues` table

### Data Processing

1. **Latest Data Detection** - Finds newest CSV files in data folder
2. **Schema Validation** - Ensures proper column mapping
3. **Data Cleaning** - Handles missing values and type conversion
4. **Bulk Import** - Efficient PostgreSQL COPY operations
5. **Constraint Handling** - Manages foreign keys and duplicates

### Manual Database Import

```bash
python automation/database_ingestion.py
```

## 📊 Metabase Integration

### Automatic Resync

After database updates, Metabase needs to refresh its schema:

1. **Detects Metabase** - Checks if running on localhost:3000
2. **Triggers Resync** - Updates database schema via API
3. **Verifies Success** - Confirms new data is available

### Manual Metabase Resync

```bash
# Using automation script
python automation/metabase_resync.py

# Using shell script
./scripts/metabase_resync.sh
```

### Metabase Setup

If Metabase isn't configured:

1. **Start Metabase**: `metabase`
2. **Configure Database**: Add PostgreSQL connection
   - Host: `localhost`
   - Port: `5432`
   - Database: `fpl_elo`
   - Username: `postgres`
3. **Create Dashboards**: Build charts from FPL tables

## 🔧 Configuration

### Environment Variables (.env)

```bash
# PostgreSQL Configuration
PGHOST=localhost
PGPORT=5432
PGDATABASE=fpl_elo
PGUSER=postgres
PGPASSWORD=your_password

# FPL Draft League Configuration
DRAFT_LEAGUE_ID=your_league_id
```

### Git Configuration

Ensure upstream remote is configured:
```bash
git remote add upstream https://github.com/olbauday/FPL-Elo-Insights.git
```

## 📊 Monitoring & Logs

### Log Locations
- `logs/full_update_automation.log` - Main automation logs
- `logs/scheduled_update_*.log` - Scheduled run logs
- `logs/database_ingestion.log` - Database import logs

### Health Checks

```bash
# Check last automation run
tail -50 logs/full_update_automation.log

# Check database state
python -c "
import psycopg2
from dotenv import load_dotenv
import os
load_dotenv()
conn = psycopg2.connect(host=os.getenv('PGHOST'), database=os.getenv('PGDATABASE'), user=os.getenv('PGUSER'), password=os.getenv('PGPASSWORD'))
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM players;')
print(f'Players: {cur.fetchone()[0]}')
"
```

## 🕐 Scheduled Jobs

For automatic updates at 5:00 AM & 5:00 PM UTC, see [README_SCHEDULED_JOBS.md](README_SCHEDULED_JOBS.md).

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running: `brew services list | grep postgresql`
   - Verify credentials in `.env` file
   - Test connection: `psql -U postgres -d fpl_elo`

2. **No Updates Found**
   - Check upstream remote: `git remote -v`
   - Fetch manually: `git fetch upstream`
   - Check for new commits: `git log HEAD..upstream/main --oneline`

3. **Draft League Fetch Failed**
   - Verify league ID in `.env` file
   - Test manual fetch: `python scripts/simple_draft_fetch.py`
   - Check FPL API status

4. **Virtual Environment Issues**
   - Install packages: `pip install -r requirements.txt`
   - Create new venv: `python -m venv fpl-venv`
   - Activate: `source fpl-venv/bin/activate`

### Manual Recovery

If automation fails, run components individually:

```bash
# 1. Pull latest data
git fetch upstream && git merge upstream/main

# 2. Update draft league
python scripts/simple_draft_fetch.py

# 3. Import to database
python automation/database_ingestion.py

# 4. Resync Metabase
python automation/metabase_resync.py
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Upstream      │    │   Your Repo     │    │   PostgreSQL    │
│   Fork          │───▶│   (Local)       │───▶│   Database      │
│   (Data Source) │    │                 │    │   (fpl_elo)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   FPL API       │    │   Metabase      │
                       │   (Draft Data)  │    │   (Dashboards)  │
                       └─────────────────┘    └─────────────────┘
```

## 📈 Performance

- **Data Sync**: ~2-5 minutes for full update
- **Database Import**: ~30 seconds for season data
- **Draft League**: ~5 seconds per league
- **Metabase Resync**: ~10-30 seconds

## 🔒 Security

- `.env` file is gitignored (contains database credentials)
- FPL API uses read-only public endpoints
- Database credentials should use limited permissions
- Cron jobs run with user privileges

## 🤝 Contributing

1. Test changes on sample data first
2. Check logs for any errors
3. Verify database integrity after updates
4. Update documentation if adding features

---

For scheduled automation setup, see [README_SCHEDULED_JOBS.md](README_SCHEDULED_JOBS.md).