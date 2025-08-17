# Complete FPL Data Automation System

This is the **master automation system** that handles the complete end-to-end workflow for keeping your FPL database up to date.

## 🎯 What It Does

The complete automation system orchestrates everything automatically:

1. **📦 Checks GitHub Fork** - Monitors your forked repository for updates
2. **⬇️ Pulls Latest Data** - Downloads new FPL data when available
3. **🏆 Updates Draft League** - Fetches latest draft league data from FPL API (if configured)
4. **🗄️ Updates Database** - Imports all data into PostgreSQL with intelligent mapping
5. **📊 Provides Summary** - Shows what was updated and current database state

## 🚀 Quick Start

### One Command to Rule Them All
```bash
./automation/run_full_update.sh
```

That's it! This single command handles everything automatically.

## 📋 What Gets Automated

### Data Sources
- ✅ **GitHub Repository Updates** - Your forked FPL-Elo-Insights repo
- ✅ **Season Data** - Teams, players, matches, player match stats (2025-2026 format)
- ✅ **Draft League Data** - Managers, picks, standings (if configured)

### Intelligent Processing
- ✅ **Update Detection** - Only processes when new data is available
- ✅ **Schema Compatibility** - Handles differences between CSV and database
- ✅ **Data Type Conversion** - Converts strings, integers, decimals correctly
- ✅ **Error Recovery** - Continues on non-critical errors
- ✅ **Comprehensive Logging** - Full audit trail of all operations

### Database Management
- ✅ **Automatic Ingestion** - Imports all data with proper relationships
- ✅ **Conflict Resolution** - Handles duplicate data gracefully
- ✅ **Transaction Safety** - Uses database transactions for consistency
- ✅ **Performance Optimization** - Efficient bulk operations

## 🛠️ Components

### Core Scripts

1. **`run_full_update.sh`** - Master shell wrapper
   - Checks all prerequisites 
   - Sets up environment
   - Orchestrates the complete workflow
   - Provides comprehensive logging

2. **`full_update_automation.py`** - Python automation engine
   - Handles GitHub updates
   - Manages draft league data
   - Controls database ingestion
   - Provides detailed progress reporting

### Supporting Scripts
- `database_ingestion.py` - Database import engine
- `run_database_ingestion.sh` - Database-only automation
- `update_from_github.py` - GitHub-only updates (legacy)

## 📈 Scheduling Options

### Manual Execution
```bash
# Run complete update once
./automation/run_full_update.sh
```

### Automated Scheduling (Cron)
```bash
# Edit crontab
crontab -e

# Add one of these schedules:

# Every 6 hours during active season
0 */6 * * * cd /path/to/fpl-elo-insights && ./automation/run_full_update.sh

# Daily at 8 AM during off-season  
0 8 * * * cd /path/to/fpl-elo-insights && ./automation/run_full_update.sh

# Every 2 hours during active period
0 */2 * * * cd /path/to/fpl-elo-insights && ./automation/run_full_update.sh
```

### macOS Launchd (Alternative to Cron)
Create `~/Library/LaunchAgents/com.fpl.automation.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fpl.automation</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/fpl-elo-insights/automation/run_full_update.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>21600</integer> <!-- 6 hours -->
    <key>WorkingDirectory</key>
    <string>/path/to/fpl-elo-insights</string>
</dict>
</plist>
```

## 📊 Monitoring and Logs

### Log Files
- **Location**: `logs/full_update_automation.log`
- **Format**: Timestamped with levels (INFO, ERROR, WARNING)
- **Rotation**: Automatic (keeps growing, manual cleanup needed)

### Real-time Monitoring
```bash
# Watch log in real-time
tail -f logs/full_update_automation.log

# Check last run
tail -n 50 logs/full_update_automation.log
```

### Status Checking
```bash
# Quick database check
psql -U postgres -d fpl_elo -c "
    SELECT 'Teams' as table_name, COUNT(*) as count FROM teams
    UNION ALL
    SELECT 'Players', COUNT(*) FROM players  
    UNION ALL
    SELECT 'Matches', COUNT(*) FROM matches;"

# Check git status
git status

# Check last update time
ls -la logs/
```

## 🔧 Configuration

### Prerequisites
1. **PostgreSQL Database**
   - Running and accessible
   - Database `fpl_elo` exists
   - Proper tables created

2. **Environment Configuration**
   - `.env` file with database credentials
   - Git repository configured
   - Virtual environment set up (optional but recommended)

3. **Data Sources**
   - Forked FPL-Elo-Insights repository
   - Draft league ID (if using draft features)

### Environment File (`.env`)
```bash
# Database Configuration
PGHOST=localhost
PGPORT=5432
PGDATABASE=fpl_elo
PGUSER=postgres
PGPASSWORD=your_password

# Draft League (Optional)
DRAFT_LEAGUE_ID=your_league_id
```

## 🎛️ Automation Behavior

### When Updates Are Available
1. ✅ Pulls latest changes from GitHub
2. ✅ Updates draft league data
3. ✅ Imports all new data to database
4. ✅ Provides detailed summary

### When No Updates Available
1. ✅ Checks for updates (confirms up-to-date)
2. ✅ Skips unnecessary processing
3. ✅ Optionally refreshes draft league data
4. ✅ Provides status confirmation

### Error Handling
- **GitHub Issues**: Reports connection/permission problems
- **Database Issues**: Shows connection/query errors
- **Data Issues**: Handles malformed CSV files gracefully
- **Draft League Issues**: Continues without failing entire process

## 🚨 Troubleshooting

### Common Issues

#### "Database connection failed"
```bash
# Check if PostgreSQL is running
ps aux | grep postgres

# Test connection manually
psql -U postgres -d fpl_elo

# Check .env file
cat .env
```

#### "Git repository not found"
```bash
# Check if you're in the right directory
pwd
ls -la .git

# Check remote configuration
git remote -v
```

#### "No updates available"
```bash
# Check if upstream has updates
git fetch origin
git status

# Force check for updates
git pull origin main
```

#### "Python packages missing"
```bash
# Install required packages
pip install pandas psycopg2-binary python-dotenv requests

# Or use virtual environment
source fpl-venv/bin/activate
pip install -r requirements.txt
```

### Debug Mode
For detailed debugging, run components individually:
```bash
# Test GitHub updates only
python automation/update_from_github.py

# Test database ingestion only
./automation/run_database_ingestion.sh

# Test draft league updates only
python scripts/simple_draft_fetch.py
```

## 📈 Performance

### Typical Runtime
- **With Updates**: 30-60 seconds
- **Without Updates**: 5-10 seconds
- **Initial Load**: 1-2 minutes

### Resource Usage
- **CPU**: Low (brief spikes during data processing)
- **Memory**: ~100-200MB during peak processing
- **Disk**: Minimal (CSV files are small)
- **Network**: Light (only when pulling updates)

## 🔐 Security Considerations

### Database Credentials
- Store in `.env` file (not in git)
- Use strong passwords
- Consider using PostgreSQL roles with limited permissions

### Git Repository
- Use SSH keys for private repositories
- Keep local repository clean
- Avoid committing sensitive data

### Draft League API
- FPL API is public but rate-limited
- Script includes reasonable delays
- No authentication required for public leagues

## 🎉 Benefits

- ✅ **Fully Automated** - Set it and forget it
- ✅ **Intelligent Updates** - Only processes when needed
- ✅ **Error Resilient** - Handles failures gracefully
- ✅ **Comprehensive Logging** - Full audit trail
- ✅ **Database Safe** - Uses transactions and proper error handling
- ✅ **Flexible Scheduling** - Works with cron, launchd, or manual execution
- ✅ **Multi-Source** - Handles GitHub, FPL API, and local data
- ✅ **Schema Evolution** - Adapts to data format changes

## 🔄 Integration with Other Tools

### Metabase Dashboards
After automation runs, your Metabase dashboards automatically have fresh data.

### Analysis Notebooks
Jupyter notebooks in the `analysis/` folder can access updated data immediately.

### Custom Scripts
Your custom analysis scripts can rely on the database being up-to-date.

## 📞 Support

### Documentation
- `automation/README_DATABASE_INGESTION.md` - Database details
- `automation/README_automation.md` - Legacy GitHub automation
- Project README.md - General project info

### Logs and Debugging
- Check `logs/full_update_automation.log` for detailed execution logs
- Enable debug mode by running individual components
- Use PostgreSQL logs for database-specific issues

### Community
- Report issues on the project's GitHub repository
- Check existing issues for similar problems
- Contribute improvements via pull requests

---

## 🏁 Ready to Automate?

```bash
# Test the complete automation now
./automation/run_full_update.sh

# Schedule it to run automatically
crontab -e
# Add: 0 */6 * * * cd /path/to/fpl-elo-insights && ./automation/run_full_update.sh

# Monitor the logs
tail -f logs/full_update_automation.log
```

Your FPL data will now stay automatically updated! 🎉