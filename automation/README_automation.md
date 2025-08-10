# FPL Data Update Automation

This automation system keeps your PostgreSQL database synchronized with the latest FPL data from your GitHub repository.

## How It Works

The system automatically:
1. **Checks your forked fpl-elo-insights repository** for updates
2. **Pulls latest data** when changes are detected
3. **Updates PostgreSQL database** with fresh CSV data
4. **Only runs when needed** - no unnecessary updates

## Components

1. **`update_from_github.py`** - Main Python script that:
   - Checks for updates in your GitHub repository
   - Pulls latest changes when available
   - Updates PostgreSQL tables with fresh CSV data
   - Handles data conflicts and incremental updates

2. **`run_github_update.sh`** - Shell wrapper script that:
   - Checks if PostgreSQL is running
   - Verifies git repository is available
   - Runs the Python update script
   - Logs all activity to `logs/github_update.log`

3. **`setup_github_automation.sh`** - Interactive setup script for scheduling

## Quick Setup

1. **Test the update script manually:**
   ```bash
   cd "/Users/rohanwalyat/Library/Mobile Documents/com~apple~CloudDocs/football-analytics/fpl-elo-insights/automation"
   ./run_github_update.sh
   ```

2. **Set up automated scheduling:**
   ```bash
   cd "/Users/rohanwalyat/Library/Mobile Documents/com~apple~CloudDocs/football-analytics/fpl-elo-insights/automation"
   ./setup_github_automation.sh
   ```
   Choose from preset schedules or create a custom one.

## Recommended Schedules

- **During active periods**: Every 2-6 hours
- **During off-season**: Once daily (8 AM or 6 PM)
- **For testing**: Every 2 hours

## Prerequisites

- PostgreSQL must be running and accessible
- fpl-elo-insights must be a git repository (forked from original)
- Git must be configured and able to pull from remote
- Python 3 must be available

## Data Flow

```
Original Repo Updates → Your Fork → Git Pull → CSV Files → PostgreSQL → Metabase
```

## Monitoring

- **Check logs**: `tail -f ../logs/github_update.log`
- **View cron jobs**: `crontab -l`
- **Test database**: `psql -U postgres -d fpl_elo -c "SELECT COUNT(*) FROM matches;"`
- **Check repo status**: `cd fpl-elo-insights && git status`

## Troubleshooting

**Script fails to run:**
- Check PostgreSQL is running: `ps aux | grep postgres`
- Verify git repository: `cd fpl-elo-insights && git remote -v`
- Test database connection: `psql -U postgres -d fpl_elo`

**Git issues:**
- Check if repo is a git repository: `ls -la fpl-elo-insights/.git`
- Verify remote connection: `cd fpl-elo-insights && git fetch`
- Check for uncommitted changes: `git status`

**Database connection issues:**
- Ensure PostgreSQL is running: `brew services list | grep postgresql`
- Test manual connection: `psql -U postgres -d fpl_elo`
- Check if tables exist: `\dt` in psql

**No updates detected:**
- Check if upstream has new commits: `cd fpl-elo-insights && git fetch && git status`
- Manually pull updates: `git pull origin main` (or `master`)
- Verify CSV files are updating: `ls -la data/*/`

## Manual Operations

**Run update once:**
```bash
cd automation && ./run_github_update.sh
```

**Check for updates without pulling:**
```bash
cd fpl-elo-insights && git fetch && git status
```

**Force pull latest changes:**
```bash
cd fpl-elo-insights && git pull origin main
```

**View current cron jobs:**
```bash
crontab -l
```

**Remove automation:**
```bash
cd automation && ./setup_github_automation.sh  # Choose option 7
```

## Benefits

- ✅ **No external API keys needed** (no Supabase credentials)
- ✅ **Only updates when data changes** (efficient)
- ✅ **Uses your existing GitHub workflow**
- ✅ **Simple and reliable**
- ✅ **Full logging and monitoring**
- ✅ **Easy to set up and maintain**