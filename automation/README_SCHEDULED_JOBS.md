# FPL Data Scheduled Updates

Automated system to check for and pull new FPL data from the upstream fork at scheduled times.

## Overview

The olbauday/FPL-Elo-Insights fork typically updates with new FPL data at:
- **5:00 AM UTC** - Morning updates
- **5:00 PM UTC** - Evening updates

This automation system runs at these times to automatically:
1. Check for new data from the upstream fork
2. Pull and merge any updates
3. Update draft league data from FPL API
4. Ingest new data into PostgreSQL database
5. Trigger Metabase resync

## Files

### Core Scripts
- `run_scheduled_update.sh` - Main scheduled update script that runs the automation
- `install_cron_jobs.sh` - Sets up cron jobs for automatic scheduling
- `full_update_automation.py` - The core automation logic

### Installation

1. **Install the cron jobs:**
   ```bash
   ./automation/install_cron_jobs.sh
   ```

2. **Verify installation:**
   ```bash
   crontab -l
   ```

### Manual Execution

To test the scheduled update manually:
```bash
./automation/run_scheduled_update.sh
```

## Cron Schedule

```bash
# 5:00 AM UTC (when fork typically updates)
0 5 * * * /path/to/repo/automation/run_scheduled_update.sh

# 5:00 PM UTC (when fork typically updates)  
0 17 * * * /path/to/repo/automation/run_scheduled_update.sh
```

## Logs

All scheduled runs create timestamped log files in `logs/`:
- `logs/scheduled_update_YYYYMMDD_HHMMSS.log`
- Old logs are automatically cleaned up (30 day retention)

## Monitoring

### Check if cron jobs are running:
```bash
# View cron logs (macOS)
log show --predicate 'subsystem == "com.apple.cron"' --last 1d

# Check for recent log files
ls -la logs/scheduled_update_*.log
```

### View latest run:
```bash
tail -f logs/scheduled_update_*.log | head -50
```

## Troubleshooting

### Common Issues

1. **Cron job not running:**
   - Check if cron service is running
   - Verify file permissions (script must be executable)
   - Check cron logs for errors

2. **Database connection fails:**
   - Ensure PostgreSQL is running
   - Check `.env` file exists with correct credentials
   - Verify database `fpl_elo` exists

3. **Virtual environment issues:**
   - Script will fall back to system Python if `fpl-venv` not found
   - Ensure required packages are installed

### Manual Debugging

Run the automation manually to debug:
```bash
cd /path/to/repo
python3 automation/full_update_automation.py
```

## Removing Scheduled Jobs

To remove the cron jobs:
```bash
crontab -l | grep -v "FPL Data Update" | crontab -
```

## Environment Requirements

- PostgreSQL database running
- Required Python packages (see requirements.txt)
- Git repository with upstream remote configured
- Optional: Virtual environment in `fpl-venv/`

## Fork Update Schedule

The upstream fork (olbauday/FPL-Elo-Insights) typically updates:
- **Gameweek data:** Shortly after matches complete
- **Regular updates:** 5:00 AM and 5:00 PM UTC daily
- **Special events:** During transfer windows, cup matches, etc.

## Success Indicators

A successful run will:
- ✅ Fetch from upstream fork
- ✅ Merge any new data
- ✅ Update draft league data
- ✅ Ingest data into database
- ✅ Trigger Metabase resync
- ✅ Create timestamped log file

The automation is designed to be safe and will only update when new data is actually available.